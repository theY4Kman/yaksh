from yaksh.bytecode import BytecodeGenerator
from yaksh.interpreter import Interpreter
from yaksh.lexer import lex
from yaksh.parser import parse, tuplify_symbols


def _get_symbols(source):
    tokens = lex(source)
    print '### Tokens'
    pprint(tokens)
    print

    tree = parse(tokens)
    print '### Parse tree'

    pprint(tuplify_symbols(tree))
    print

    return tree


def interpreter_example():
    symbols = _get_symbols('''
def toebag(x, n, _totes32lame_VAR):
    result = n * x
    return result

t = toebag((1 + 8) * 2, 2, 3)
print(toebag(4.2,9.3,1), t, 'PENIS', "TACO")
''')

    print "### Interpreter Start"
    interp = Interpreter(symbols)
    interp.run()


def bytecode_example():
    symbols = _get_symbols('''
def test(a, b, c):
    return a + b * c
t = test(1, 2, 3)
f = test(1, 2, 3) + test(4, 5, 6)
''')

    print "### Bytecode Output"
    bytecode = BytecodeGenerator(symbols)
    print bytecode.generate()


if __name__ == '__main__':
    from pprint import pprint

    #interpreter_example()
    bytecode_example()
