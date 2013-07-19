"""
I tried to jump right in and write the parser, like I did the lexer. But it
turns out I have a much more natural understanding of how to lex in my mind
(go figure) than how to turn those tokens into logical blocks. Lexing to tokens
kinda just felt like blocks falling into place, whereas parsing explodes with
complexity at every turn.

I've decided to write a grammar. I _am_ gonna fall into learning how to write a
grammar, because planning the grammar will teach me what's necessary to explain
a language (or teach me what I take for granted). Just wanted to warn if you
take for granted I know how grammars are usually written (logically or by
format). I've used the following links as research/guidance:
 - https://en.wikipedia.org/wiki/Parsing#Programming_languages
 - https://en.wikipedia.org/wiki/Parse_tree
 - https://en.wikipedia.org/wiki/Abstract_syntax_tree
 - http://docs.python.org/2/reference/grammar.html

Assumptions I've made and thought were notable while writing the grammar:
 - * denotes zero or more (like RegEx)
 - Single quoted literals denote token text (e.g. 'break' denotes a RESERVED
   token [with no regard to the grammar, though] with the text 'break')
 - CAPITALIZED items refer to token types (usually used to denote obvious groups
   of lexemes/token types, such as NUMBER, which, while it denotes hex, real,
   integer, and binary numbers, they all mean the same, so that complexity is
   obvious enough to hide in the lexer -- I say all this because it's opposed to
   single-quoted items, which are obvious enough as just characters, like ')')



script: (NEWLINE | stmt)*

stmt: simple_stmt | compound_stmt
simple_stmt: reserved_stmt | assign_stmt | value_stmt
value_stmt: fcall_stmt | atom
reserved_stmt: return_stmt | 'continue' | 'break'

return_stmt: 'return' value_stmt

fdef: 'def' NAME parameters
parameters: '(' + paramdef* ')'
paramdef: (NAME ',') | NAME

fcall_stmt: NAME arguments
arguments: '(' + argdef* ')'
argdef: (value_stmt ',') | value_stmt

atom: NAME | NUMBER | STRING
"""
import functools


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
        return _token()

    def _token(index=None):
        if index is None:
            index = _cur()
        if index >= len(tokens):
            return None
        return tokens[index]

    def _next():
        _skip()
        return _token()

    def _peek(offset=1):
        return _token(_cur() + offset)

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

    def _expect(*types):
        """Expect one of *types, eat if correct, error if not"""
        next_token = _peek()
        if next_token is None:
            raise SyntaxError('Unexpected end of input.')
        for type in types:
            if callable(type):
                try:
                    val = type()
                except SyntaxError:
                    pass
                else:
                    if val is not None:
                        return val
            else:
                if next_token.type == type:
                    _skip()
                    return next_token
        else:
            type_names = []
            for type in types:
                if callable(type):
                    type_names.append(type.__name__)
                else:
                    type_names.append(type)
            raise SyntaxError('Unexpected token %s. Expected one of [%s]' %
                              (next_token, ', '.join(type_names)))

    def _allow(*types):
        """Expect one of *types, eat if correct, ignore if not"""
        try:
            return _expect(*types)
        except SyntaxError:
            pass

    def defn(fn):
        defn_name = fn.__name__.lstrip('_')
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            token = fn(*args, **kwargs)
            if token is not None:
                return (defn_name, token)
            else:
                return None
        return inner

    def _zero_or_more(fn):
        or_more = []
        while True:
            ret = _allow(fn)
            if ret is None:
                break
            else:
                or_more.append(ret)
        return or_more

    @defn
    def _atom():
        return _expect('NAME', 'NUMBER', 'STRING')

    @defn
    def _value_stmt():
        return _expect(_fcall_stmt, _atom)

    @defn
    def _fcall_stmt():
        return _expect('NAME'), _expect(_arguments)

    @defn
    def _arguments():
        _expect('OPEN_PAREN')
        args = _zero_or_more(_argdef)
        _expect('CLOSE_PAREN')
        return args

    @defn
    def _argdef():
        value_stmt = _expect(_value_stmt)
        _allow('COMMA')
        return value_stmt

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
