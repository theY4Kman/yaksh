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

Well, after all that planning and research, I _was_ able to jump in and write
something that does some kind of parsing :P



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
argdef: value_stmt

atom: NAME | NUMBER | STRING
"""
from yaksh.lexer import OPERATORS


class Symbol(object):
    def __init__(self, name, children):
        self.name = name
        self.symbols = children

    def __repr__(self):
        return '<Symbol %s, %d children>' % (self.name, len(self.symbols))


LITERAL_TOKENS = (
    'REAL',
    'INTEGER',
    'HEX',
    'BINARY',
    'STRING',
)


symbols = None
symbol_tokens = []
cur_sym = None
cur_idx = None
cur = None
_tokens = []


def _next():
    global cur_idx, cur
    cur_idx += 1
    if cur_idx < len(_tokens):
        cur = _tokens[cur_idx]
    else:
        cur = None


def _getsym():
    symbol_tokens.append(cur)
    _next()


def _accept(token_type, capture=True):
    if cur.type == token_type:
        if capture:
            _getsym()
        else:
            _next()
        return True
    else:
        return False


def _expect(token_type, capture=True):
    if _accept(token_type, capture):
        return True
    else:
        raise ValueError('Expected %s, found %r' % (token_type, cur))


def _term(token_type):
    return _expect(token_type, False)


def _sym(name, symbols=None):
    return Symbol(name, symbols or symbol_tokens)


def _endsym(name):
    global symbol_tokens
    symbol = _sym(name)
    symbol_tokens = []
    return symbol


def _eat_newlines():
    while _accept('NEWLINE', False):
        if not cur:
            break


def name():
    if _accept('NAME'):
        return _endsym('name')


def operator():
    if cur.type in OPERATORS.values():
        _getsym()
        return _endsym('operator')


def value():
    if _accept('NAME') or _accept('NUMBER'):
        return _endsym('value')


def value_stmt():
    symbols = []
    v = value()
    if not v:
        raise ValueError('Expected a value')
    symbols.append(v)
    while True:
        op = operator()
        if op:
            v = value()
            if not v:
                raise ValueError('Expected a value')
            symbols.append(op)
            symbols.append(v)
        else:
            break
    return Symbol('value_stmt', symbols)



def arglist():
    args = []
    while True:
        v = value_stmt()
        if v:
            args.append(v)
        else:
            break
        if not _accept('COMMA', False):
            break
    return Symbol('arglist', args)


def reserved_stmt():
    if _accept('R_RETURN', False):
        r = _endsym('return_stmt')
        return_value = value_stmt()
        if return_value:
            r.symbols = (r,)
        return r


def stmt():
    _eat_newlines()
    if _accept('NAME'):
        if _accept('ASSIGN'):
            assign = _endsym('assign')
            value = value_stmt()
            if not value:
                raise ValueError('Expected a value statement')
            assign.symbols.append(value)
            return assign
        elif _accept('OPEN_PAREN', False):
            fcall = _endsym('fcall')
            args = arglist()
            _term('CLOSE_PAREN')
            fcall.symbols.append(args)
            return fcall
        elif _accept('NEWLINE'):
            return _endsym('name')
        else:
            raise ValueError('Not a valid statement')
    else:
        return reserved_stmt()


def block():
    statements = []
    while True:
        _eat_newlines()
        if not _accept('INDENT'):
            break
        indent = _endsym('indent')
        if _accept('NEWLINE'):
            continue

        s = stmt()
        if s:
            statements.append((indent, s))
        else:
            break
    return Symbol('block', statements)


def parse(tokens):
    if not tokens:
        return []

    global symbols, cur_idx, cur_sym, _tokens, cur
    _tokens = tokens

    symbols = []
    cur_idx = 0
    cur = _tokens[cur_idx]
    num_tokens = len(_tokens)

    while cur_idx < num_tokens:
        _eat_newlines()
        if cur is None:
            # End of input
            break
        if _accept('R_DEF', False):
            func = _sym('fdef')

            _expect('NAME')
            funcname = _endsym('name')

            _term('OPEN_PAREN')

            while _accept('NAME'):
                if not _accept('COMMA', False):
                    break
            parameters = _endsym('parameters')

            _term('CLOSE_PAREN')
            _term('BLOCK_BEGIN')
            _term('NEWLINE')

            func.symbols = (funcname, parameters, block())
            symbols.append(func)
        else:
            s = stmt()
            if s:
                symbols.append(s)
            else:
                print 'Skipping %r' % cur
                _next()

    return symbols

