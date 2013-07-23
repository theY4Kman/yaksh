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
    ';': 'END_STATEMENT',
    ':': 'BLOCK_BEGIN',
}

NUMBER_TYPES = {'b', 'x', 'h'}

T_RESERVED = {
    'def',
    'return',
    'if',
    'elif',
    'else',
    'for',
    'in',
    'is',
    'pass',
}


class Token(object):
    def __init__(self, type, text, line_no, char_no):
        self.type = type
        self.text = text
        self.line_no = line_no
        self.char_no = char_no

    def __str__(self):
        return 'Token.%s(%r):%d:%d' % (self.type, self.text,
                                       self.line_no, self.char_no)
    __repr__ = __str__


def lex(s):
    tokens = []
    curtype = []
    chars = []
    cur = [0]
    line_no = 0
    char_no = 0

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

    def _type_is(type):
        return curtype and curtype[0] == type

    def _last_token_is(type, c=None):
        return tokens and tokens[-1].type == type and (c is None or c == tokens[-1].text)

    def _suppress():
        curtype[:] = []
        if chars:
            _end_token()
        chars[:] = []

    def _end_token():
        if curtype:
            assert len(curtype) == 1
            token_type = curtype[0]
            token_text = ''.join(chars)
            if token_type == 'INTEGER':
                token_type = 'NUMBER'
            elif token_type == 'IDENTIFIER':
                token_text = token_text.strip()
                if token_text in T_RESERVED:
                    token_type = 'R_' + token_text.upper()
                else:
                    token_type = 'NAME'
            t = Token(token_type, token_text, line_no, char_no - len(chars))
            tokens.append(t)
            curtype[:] = []
        chars[:] = []

    def _single(type, skip=0):
        _end_token()
        _token(type)
        _end_token()
        _skip(skip)

    def _token(type):
        if type != 'INDENT' and _type_is('INDENT'):
            _end_token()
        if not curtype:
            curtype.append(type)
        chars.append(c)

    def _change_type(type):
        curtype[:] = [type]
        chars.append(c)

    while _cur() < len(s):
        c = s[_cur()]
        if c.isalpha():
            if (_type_is('INTEGER') and _len(1) and _peek_behind(1) == '0' and
                    _peek(1).isdigit() and c in NUMBER_TYPES):
                _token('NUMBER')
            else:
                _token('IDENTIFIER')
        elif c.isdigit():
            if _type_is('IDENTIFIER'):
                # Allow numbers in identifiers after first digit
                _token('IDENTIFIER')
            else:
                _token('NUMBER')
        elif c == '.':
            if _type_is('NUMBER') and _peek(1).isdigit():
                _token('NUMBER')
            else:
                _single('DOT')
        elif c == '_':
            _token('IDENTIFIER')
        elif c == '=':
            if _peek(1) == '=':
                if c in OPERATORS:
                    _single(OPERATORS[c] + '_ASSIGN', 1)
                elif c in COMPARISONS:
                    _single(COMPARISONS[c], 1)
                else:
                    _single('UNKNOWN')
            else:
                _single('ASSIGN')
        elif c in ('"', "'"):
            q = c
            _skip(1)
            c = s[_cur()]
            while c != q:
                _token('LITERAL')
                _skip(1)
                c = s[_cur()]
                if c is None:
                    raise SyntaxError('Unterminated literal')
            _end_token()
        elif c in OPERATORS:
            _single(OPERATORS[c])
        elif c in DELIMITERS:
            _single(DELIMITERS[c])
        elif c == '\n':
            if tokens:
                _single('NEWLINE')
            else:
                # Eat whitespace at beginning of file
                _suppress()
            line_no += 1
            char_no = -1
        elif c in ' \t':
            if _last_token_is('NEWLINE') or _type_is('INDENT'):
                _token('INDENT')
            else:
                _end_token()
                _suppress()
        else:
            _single('UNKNOWN')

        _skip(1)
        char_no += 1

    _end_token()
    return tokens


if __name__ == '__main__':
    from pprint import pprint
    pprint(lex('''
def toebag(x, n, *rest):
    result = n * x
    return result

print(toebag(1, 2, 3))
'''))
