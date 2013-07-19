from yaksh.lexer import tokenize, lex
from yaksh.parser import parse


if __name__ == '__main__':
    from pprint import pprint

    tokens = tokenize(lex('''
def toebag(x, n):
    result = n * x
    return result

print(toebag(1, 2, 3))
'''))

    print '### Tokens'
    pprint(tokens)
    print

    tree = parse(tokens)

    print '### Parse tree'
    pprint(tree)
