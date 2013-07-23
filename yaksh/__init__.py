from yaksh.interpreter import Interpreter
from yaksh.lexer import lex
from yaksh.parser import parse, tuplify_symbols


if __name__ == '__main__':
    from pprint import pprint

    tokens = lex('''
def toebag(x, n, _totes32lame_VAR):
    result = n * x
    return result

t = toebag((1 + 8) * 2, 2, 3)
print(toebag(4.2,9.3,1), t, 'PENIS', "TACO")
''')

    print '### Tokens'
    pprint(tokens)
    print

    tree = parse(tokens)

    print '### Parse tree'
    pprint(tuplify_symbols(tree))

    interp = Interpreter(tree)
    interp.run()
