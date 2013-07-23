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
from yaksh.lexer import OPERATORS, Token


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
    if _accept('NAME'):
        if _accept('OPEN_PAREN', False):
            fcall = _endsym('fcall')
            args = arglist()
            _term('CLOSE_PAREN')
            fcall.symbols.append(args)
            return Symbol('value', (fcall,))
        else:
            var = _endsym('var')
            return _sym('value', (var,))
    else:
        if _accept('NUMBER'):
            number = _endsym('number')
            return _sym('value', (number,))
        elif _accept('LITERAL'):
            literal = _endsym('literal')
            return _sym('value', (literal,))


def value_stmt():
    symbols = []
    v = value()
    if not v:
        if _accept('OPEN_PAREN', False):
            v = value_stmt()
            _expect('CLOSE_PAREN', False)
        else:
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
    if _accept('R_RETURN'):
        r = _endsym('return_stmt')
        return_value = value_stmt()
        if return_value:
            r.symbols = (return_value,)
        return r
    elif _accept('R_PASS'):
        return _endsym('pass_stmt')


def stmt():
    _eat_newlines()
    if _accept('NAME'):
        if _accept('ASSIGN'):
            assign = _endsym('assign')
            value = value_stmt()
            if not value:
                raise ValueError('Expected a value statement')
            if assign.symbols[1].text[0] != '=':
                # Operator assignment, let's add in tokens to simplify interp
                op = assign.symbols[1].text[0]
                optok = Token(OPERATORS[op], op, -1, -1)
                v_sym = (assign.symbols[0], optok, value)
                value = _sym('value_stmt', v_sym)
            assign.symbols.append(value)
            return assign
        elif _accept('OPEN_PAREN', False):
            fcall = _endsym('fcall')
            args = arglist()
            _term('CLOSE_PAREN')
            fcall.symbols.append(args)
            return fcall
        elif _accept('NEWLINE'):
            return _endsym('var')
        else:
            raise ValueError('Not a valid statement')
    else:
        return reserved_stmt()


def block():
    statements = []
    block_indent_level = None
    while True:
        _eat_newlines()
        if not _accept('INDENT'):
            break
        indent = _endsym('indent')
        indent_level = len(indent.symbols[0].text)
        if block_indent_level != indent_level:
            if block_indent_level is None:
                block_indent_level = indent_level
            else:
                raise ValueError('Mixed indentation %r' % indent)

        if _accept('NEWLINE'):
            continue

        s = stmt()
        if s:
            statements.append(s)
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


# God, what a terrible name
def tuplify_symbols(symbols):
    def _symbol_to_list(symbol):
        if isinstance(symbol, Symbol):
            return symbol.name, tuplify_symbols(symbol.symbols)
        else:
            return symbol
    tuplified = []
    for symbol in symbols:
        tuplified.append(_symbol_to_list(symbol))
    return tuplified

