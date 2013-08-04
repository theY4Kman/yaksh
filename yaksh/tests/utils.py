import sys
from contextlib import contextmanager

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from yaksh.bytecode_asm import BytecodeAssemblyGenerator
from yaksh.bytecode_compiler import assemble
from yaksh.lexer import lex
from yaksh.parser import parse
from yaksh.vm import AbstractMachine

@contextmanager
def capture_stdout():
    _old_stdout = sys.stdout
    sys.stdout = StringIO()
    yield sys.stdout
    sys.stdout = _old_stdout


def vm_output(s):
    tokens = lex(s)
    symbols = parse(tokens)
    bc_gen = BytecodeAssemblyGenerator(symbols)
    bc_asm = bc_gen.generate()
    bytecode = assemble(bc_asm)
    vm = AbstractMachine(bytecode)
    with capture_stdout() as output:
        vm.run()
    return output.getvalue()
