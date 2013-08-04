from yaksh.bytecode_asm import BytecodeAssemblyGenerator
from yaksh.bytecode_compiler import assemble
from yaksh.interpreter import Interpreter
from yaksh.lexer import lex
from yaksh.parser import parse, tuplify_symbols
from yaksh.vm import AbstractMachine

TEST_PROGRAM = '''
def test(a, b, c):
    return a + b * c
def pass_text():
    pass
t = test(1, 2, 3)
print(t)
f = test(1, 2, 3) + test(4, 5, 6)
print(f)

print('')
print('# Testing arithmetic')
print(8 / 2)
print(4 - 8 / 2)
print(4 - 4 / 2)
print((4 - 4) / 2)

if 1 + 1:
    print('taco')

def test_if(a, r, l):
    if a == 1:
        return r - l
    else:
        return r + l

print(test_if(0, 1, 1))
print(test_if(1, 1, 1))
'''


def _get_symbols(source):
    tokens = lex(source)
    print '### Tokens'
    pprint(tokens)
    print

    tree = parse(tokens)
    print '### Parse tree'

    print '\n'.join(str(s) for s in tree)
    print

    return tree


def interpreter_example():
    symbols = _get_symbols(TEST_PROGRAM)

    print "### Interpreter Start"
    interp = Interpreter(symbols)
    interp.run()


def bytecode_example(program=TEST_PROGRAM):
    symbols = _get_symbols(program)

    print "### Bytecode Assembly"
    bc_gen = BytecodeAssemblyGenerator(symbols)
    bc_asm = bc_gen.generate()
    print bc_asm
    print

    print '### Bytecode'
    bytecode = assemble(bc_asm)
    print repr(bytecode)
    print

    print '### VM Start'
    vm = AbstractMachine(bytecode)
    vm.run()


if __name__ == '__main__':
    from pprint import pprint

    # symbols = _get_symbols(TEST_PROGRAM)
    # interpreter_example()
    # print
    # print '############### END INTERPRETER EXAMPLE ###############'
    # print
    cmps = (
        '1 == 1',
        '1 != 1', '1 != 2',
        '1 >= 1', '1 >= 2', '1 >= 3',
        '1 <= 2',
        '1 < 2',
        '1 > 2',
    )
    instrs = ('print(%r)\nprint(%s)\nprint("")' % (s, s) for s in cmps)
    bytecode_example('\n'.join(instrs))
