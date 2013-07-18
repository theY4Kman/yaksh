COMPARISONS = {
    '!': 'NOTEQUAL',
    '=': 'ISEQUAL',
    '>': 'GTE',
    '<': 'LTE',
}

OPERATORS = {
    '-': 'MINUS',
    '+': 'PLUS',
    '/': 'SLASH',
    '*': 'TIMES',
}

DELIMITERS = {
    '(': 'OPEN_PAREN',
    ')': 'CLOSE_PAREN',
    '{': 'OPEN_BRACE',
    '}': 'CLOSE_BRACE',
    ',': 'COMMA',
    '"': 'DOUBLE_QUOTE',
    "'": 'SINGLE_QUOTE',
    '\n': 'END_STATEMENT',
    ';': 'END_STATEMENT',
    ':': 'BLOCK_BEGIN',
}

NUMBER_TYPES = {
    'b': 'BINARY',
    'x': 'HEX',
    'h': 'HEX',
}


def lex(s):
    tokens = []
    curtype = []
    chars = []
    cur = [0]

    def _cur(assn=None):
        if assn is None:
            return cur[0]
        else:
            cur[0] = assn

    def _peek(abs_offset):
        try:
            return s[_cur() + abs_offset]
        except IndexError:
            return ''
    _peek_behind = lambda rel_offset: _peek(-rel_offset)

    def _skip(offset):
        _cur(_cur() + offset)

    def _len(cmp=None):
        if cmp is None:
            return len(chars)
        else:
            return len(chars) == cmp

    def _is_type(type):
        return curtype and curtype[0] == type

    def _suppress():
        curtype[:] = []
        if chars:
            _end_token()
        chars[:] = []

    def _end_token():
        if curtype:
            assert len(curtype) == 1
            tokens.append((curtype[0], ''.join(chars)))
            curtype[:] = []
        chars[:] = []

    def _single(type, skip=0):
        _end_token()
        _token(type)
        _end_token()
        _skip(skip)

    def _token(type):
        if not curtype:
            curtype.append(type)
        chars.append(c)

    def _change_type(type):
        curtype[:] = [type]
        chars.append(c)

    while _cur() < len(s):
        c = s[_cur()]
        if c.isalpha():
            if (_is_type('INTEGER') and _len(1) and _peek_behind(1) == '0' and
                    _peek(1).isdigit() and c in NUMBER_TYPES):
                _change_type(NUMBER_TYPES[c])
            else:
                _token('IDENTIFIER')
        elif c.isdigit():
            if _is_type('IDENTIFIER'):
                # Allow numbers in identifiers after first digit
                _token('IDENTIFIER')
            else:
                _token('INTEGER')
        elif c == '.':
            if _is_type('INTEGER') and _peek(1).isdigit():
                _change_type('REAL')
            else:
                _single('DOT')
        elif _peek(1) == '=':
            if c in OPERATORS:
                _single(OPERATORS[c] + '_ASSIGN', 1)
            elif c in COMPARISONS:
                _single(COMPARISONS[c], 1)
            else:
                _single('ASSIGN')
        elif c in OPERATORS:
            _single(OPERATORS[c])
        elif c in DELIMITERS:
            _single(DELIMITERS[c])
        elif c in ' ':
            _end_token()
            _suppress()
        else:
            _single('UNKNOWN')
        _skip(1)

    _end_token()
    return tokens


if __name__ == '__main__':
    print lex('''\
def toebag(x, n, *rest):
    result = n * x + 42 - 0x8 + 0.986
    return result
end\
''')
