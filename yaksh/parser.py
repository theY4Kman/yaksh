class Statement(object):
    def __repr__(self):
        return str(self)


class Block(list):
    """A collection of statements at the same level of indentation"""


class Function(object):
    """A label with an arguments list and one statement/block"""


class FunctionDefinition(Statement):
    def __init__(self, funcname, args):
        self.funcname = funcname
        self.args = args

    def __str__(self):
        return 'def %s(%s):' % (self.funcname.text,
                                ', '.join(t.text for t in self.args))


LITERAL_TOKENS = (
    'REAL',
    'INTEGER',
    'HEX',
    'BINARY',
    'STRING',
)


def parse(tokens):
    statements = []
    cur = [0]

    def _cur(assn=None):
        if assn is None:
            return cur[0]
        else:
            cur[0] = assn

    def _skip(offset=1):
        _cur(_cur() + offset)

    def _token(index=None):
        if index is None:
            index = _cur()
        if index >= len(tokens):
            return None
        return tokens[index]

    def _next():
        _skip()
        return _token()

    def _eat(*types):
        t = _next()
        if t.type in types:
            return t
        else:
            raise SyntaxError('Unexpected %s. Was expecting token %s.' %
                              (t, types))

    def _eat_until(delims=None, *types):
        """Expects a token of type in *types, and advances the cursor if so.
        Completes successfully when one of delims is found. Otherwise, gives a
        syntax error."""
        if isinstance(delims, str):
            delims = (delims,)
        elif delims is None:
            delims = ('NEWLINE',)
        def _error(message):
            raise SyntaxError('%s. Was expecting a delimiter %s or token %s' %
                              (message, delims, types))
        while _cur() < len(tokens):
            t = tokens[_cur()]
            if t.type in delims:
                return
            elif t.type in types:
                yield t
            else:
                _error('Unexpected %s' % t)
            _skip()
        else:
            _error('Unexpected end of input')

    while _cur() < len(tokens):
        t = tokens[_cur()]

        if t.type == 'RESERVED':
            if t.text == 'def':
                funcname = _eat('IDENTIFIER')

                # Begin argument list
                _eat('OPEN_PAREN')
                args = []
                _iter = lambda: _eat('CLOSE_PAREN', 'IDENTIFIER')
                arg = _iter()
                while arg.type != 'CLOSE_PAREN':
                    args.append(arg)
                    next = _eat('CLOSE_PAREN', 'COMMA')
                    if next.type == 'CLOSE_PAREN':
                        break
                    arg = _iter()

                # Begin block
                _eat('BLOCK_BEGIN')

                defn = FunctionDefinition(funcname, args)
                statements.append(defn)

        _skip()

    return statements
