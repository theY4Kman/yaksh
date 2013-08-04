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
"""
import re

from yaksh.lexer import OPERATORS, Token


RGX_CAMEL_CASE = re.compile(r'([A-Z][a-z]*)')


def _symbol_cls_name_to_symbol_name(cls_name):
    words = [m.group(1).lower() for m in RGX_CAMEL_CASE.finditer(cls_name)]
    return '_'.join(words)


class _SymbolMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = type.__new__(mcs, name, bases, attrs)
        if name != 'Symbol' and not name.startswith('_'):
            token_name = _symbol_cls_name_to_symbol_name(name)
            Symbol._classes[token_name] = cls
        return cls


class Symbol(object):
    __metaclass__ = _SymbolMeta

    # Registry of specialized Symbol classes
    _classes = {}

    def __new__(cls, name, *args, **kwargs):
        if cls.__name__ == 'Symbol' and name in Symbol._classes:
            return Symbol._classes[name](name, *args)
        else:
            return object.__new__(cls, name, *args)

    def __init__(self, name, children):
        self.name = name
        self.symbols = children

    def __repr__(self):
        return '<%s %s, %d children>' % (self.__class__.__name__, self.name,
                                         len(self.symbols))


class Name(Symbol):
    @property
    def text(self):
        return self.symbols[0].text

    def __repr__(self):
        return '<Name %r>' % self.text

    def __str__(self):
        return self.text


class Number(Symbol):
    def __init__(self, name, children):
        super(Number, self).__init__(name, children)
        self.value = Number.decode(self.symbols[0].text)

    @staticmethod
    def decode(text):
        if text[:2] in ('0x', '0h'):
            return int(text, 16)
        elif text.startswith('0b'):
            return int(text[2:], 2)
        elif '.' in text:
            return float(text)
        else:
            return int(text)

    def __repr__(self):
        return repr(self.value)


class Assign(Symbol):
    @property
    def var(self):
        return self.symbols[0].text

    @property
    def value(self):
        return self.symbols[2]

    def __str__(self):
        return '%s = %s' % (self.var, self.value)


class ReturnStmt(Symbol):
    @property
    def value(self):
        if self.symbols:
            return self.symbols[0]

    def __str__(self):
        return 'return %s' % self.value


class Operator(Symbol):
    OP_FUNCS = {
        'PLUS': 'add',
        'MINUS': 'sub',
        'TIMES': 'mult',
        'SLASH': 'div',
    }

    def __init__(self, *args, **kwargs):
        super(Operator, self).__init__(*args, **kwargs)
        self.text = self.symbols[0].text
        self.opname = OPERATORS[self.text]
        self.opfunc = self.OP_FUNCS[self.opname]

    def __str__(self):
        return self.text


class Value(Symbol):
    def __init__(self, *args, **kwargs):
        super(Value, self).__init__(*args, **kwargs)

    def __str__(self):
        return str(self.symbols[0])


class ValueStmt(Symbol):
    def __str__(self):
        return ' '.join(str(s) for s in self.symbols)


class Literal(Symbol):
    def __init__(self, *args, **kwargs):
        super(Literal, self).__init__(*args, **kwargs)
        self.text = self.symbols[0].text

    def __repr__(self):
        return repr(self.text)


class Fcall(Symbol):
    @property
    def func_name(self):
        return self.symbols[0].text

    @property
    def arglist(self):
        return self.symbols[1]

    @property
    def args(self):
        return self.arglist.symbols

    def __str__(self):
        return '%s(%s)' % (self.func_name, self.arglist)


class Arglist(Symbol):
    def __str__(self):
        return ', '.join(str(s) for s in self.symbols)


class Var(Symbol):
    @property
    def text(self):
        return self.symbols[0].text

    def __str__(self):
        return self.text


class Parameters(Symbol):
    @property
    def names(self):
        return [s.text for s in self.symbols]

    def __str__(self):
        return ', '.join(self.names)


class Fdef(Symbol):
    @property
    def func_name(self):
        return self.symbols[0].text

    @property
    def parameters(self):
        return self.symbols[1]

    @property
    def params(self):
        return self.parameters.names

    @property
    def block(self):
        return self.symbols[2]

    @property
    def stmts(self):
        return self.block.symbols

    def __str__(self):
        return 'def %s(%s):\n%s' % (self.func_name, self.parameters, self.block)


class PassStmt(Symbol):
    def __str__(self):
        return 'pass'


class IfChain(Symbol):
    def __init__(self, *args, **kwargs):
        super(IfChain, self).__init__(*args, **kwargs)
        #: @type: list of _BaseTestStmt
        self.test_stmts = []
        self.else_stmt = None
        for test in self.symbols:
            if self.else_stmt:
                raise SyntaxError('Unexpected %s statement' % test.name)
            if test.name == 'else_stmt':
                self.else_stmt = test
            else:
                self.test_stmts.append(test)

    def __str__(self):
        pieces = [str(t) for t in self.test_stmts]
        if self.else_stmt:
            pieces.append(str(self.else_stmt))
        return '\n'.join(pieces)


class _BaseTestStmt(Symbol):
    def __init__(self, *args, **kwargs):
        super(_BaseTestStmt, self).__init__(*args, **kwargs)
        self.text = self.symbols[0].text


class _BaseCondTestStmt(_BaseTestStmt):
    @property
    def cond(self):
        return self.symbols[1]

    @property
    def block(self):
        return self.symbols[2]

    def __str__(self):
        return '%s %s:\n%s' % (self.text, self.cond, self.block)


class IfStmt(_BaseCondTestStmt):
    pass


class ElifStmt(_BaseCondTestStmt):
    pass


class ElseStmt(_BaseTestStmt):
    cond = None

    @property
    def block(self):
        return self.symbols[1]

    def __str__(self):
        return '%s:\n%s' % (self.text, self.block)


class Block(Symbol):
    INDENT = '    '

    def __str__(self):
        return (self.INDENT +
                (self.INDENT + '    \n').join(str(s) for s in self.symbols))


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
block_indent_level = None


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


def _accept(token_types, capture=True):
    if not isinstance(token_types, tuple):
        token_types = (token_types,)
    if cur and cur.type in token_types:
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
    _name = name()
    if _name:
        if _accept('OPEN_PAREN', False):
            fcall = _endsym('fcall')
            fcall.symbols.insert(0, _name)
            args = arglist()
            _term('CLOSE_PAREN')
            fcall.symbols.append(args)
            return Symbol('value', (fcall,))
        else:
            var = _endsym('var')
            var.symbols.append(_name)
            return _sym('value', (var,))
    else:
        if _accept('NUMBER'):
            number = _endsym('number')
            return _sym('value', (number,))
        elif _accept('LITERAL'):
            literal = _endsym('literal')
            return _sym('value', (literal,))


def cmp_operator():
   return _accept(('NOTEQUAL', 'ISEQUAL', 'GT', 'LT', 'GTE', 'LTE'))


def _expect_value(allow_empty=False):
    v = value()
    if not v:
        if _accept('OPEN_PAREN', False):
            v = value_stmt()
            _expect('CLOSE_PAREN', False)
        elif allow_empty:
            return
        else:
            raise ValueError('Expected a value')
    return v


def value_stmt():
    symbols = []
    v = _expect_value(True)
    if not v:
        return
    symbols.append(v)
    while True:
        op = operator()
        if op:
            v = _expect_value()
            if op.symbols[0].text in '*/':
                # Order of operations
                last_v = symbols.pop()
                sym = Symbol('value_stmt', (last_v, op, v))
                symbols.append(sym)
            else:
                symbols.append(op)
                symbols.append(v)
        else:
            cmp = cmp_operator()
            if cmp:
                v = _expect_value()
                cmp_stmt = _sym('cmp_stmt', (symbols.pop(), cmp, v))
                symbols.append(cmp_stmt)
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

    elif _accept('R_IF'):
        if_pieces = []
        if_piece = _endsym('if_stmt')
        while if_piece:
            cond = value_stmt()
            if not cond:
                raise ValueError('Expected a condition')
            if_piece.symbols.append(cond)

            _expect('BLOCK_BEGIN', False)
            _block = block()
            if not _block:
                raise ValueError('Expected a block')
            if_piece.symbols.append(_block)
            if_pieces.append(if_piece)

            if _accept('R_ELIF'):
                if_piece = _endsym('elif_stmt')
            else:
                break

        if _accept('R_ELSE'):
            else_stmt = _endsym('else_stmt')
            _expect('BLOCK_BEGIN', False)
            _block = block()
            if not _block:
                raise ValueError('Expected a block')
            else_stmt.symbols.append(_block)
            if_pieces.append(else_stmt)

        return _sym('if_chain', if_pieces)

    elif _accept('R_PASS'):
        return _endsym('pass_stmt')


def stmt():
    _eat_newlines()
    _name = name()
    if _name:
        if _accept('ASSIGN'):
            assign = _endsym('assign')
            assign.symbols.insert(0, _name)
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
            fcall.symbols.append(_name)
            args = arglist()
            _term('CLOSE_PAREN')
            fcall.symbols.append(args)
            return fcall
        elif _accept('NEWLINE'):
            var = _endsym('var')
            var.symbols.append(_name)
            return var
        else:
            raise ValueError('Not a valid statement')
    else:
        reserved = reserved_stmt()
        if reserved:
            return reserved
        else:
            return value_stmt()


def block():
    block_indent_level = None
    statements = []
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

            parameters = _endsym('parameters')
            while True:
                _name = name()
                if not _name:
                    break
                parameters.symbols.append(_name)
                if not _accept('COMMA', False):
                    break

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
            if symbol.__class__ == Symbol:
                return symbol.name, tuplify_symbols(symbol.symbols)
            else:
                return symbol
        else:
            return symbol
    tuplified = []
    for symbol in symbols:
        tuplified.append(_symbol_to_list(symbol))
    return tuplified
