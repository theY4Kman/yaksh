from collections import OrderedDict
import struct
from yaksh.bytecode_asm import BUILTINS
from yaksh.bytecode_compiler import MAGIC, Const, Instr


class Return(Exception):
    pass


class _VirtualMachinePartial(object):
    def _pop(self):
        try:
            return self._stack.pop()
        except IndexError:
            raise RuntimeError('Popped an empty stack.')

    def _push(self, v):
        self._stack.append(v)


class Builtins(_VirtualMachinePartial):
    """Implements built-in functions"""

    def __init__(self, vm):
        self._stack = vm._stack

    def call(self, idx):
        try:
            name = BUILTINS[idx]
        except IndexError:
            raise RuntimeError('Unknown builtin index %d.' % idx)

        try:
            builtin = getattr(self, 'do_' + name)
        except AttributeError:
            raise NotImplementedError('%s builtin not implemented' % name)

        self._push(builtin())

    def do_print(self):
        print self._pop()


class VirtualMachine(_VirtualMachinePartial):
    """Handles the actual execution of instructions"""

    def __init__(self, am):
        self.am = am
        self._stack = []
        self._ctx_stack = []
        self._globals = {}
        self._builtins = Builtins(self)

    def add(self):
        l = self._pop()
        r = self._pop()
        self._push(l + r)

    def sub(self):
        l = self._pop()
        r = self._pop()
        self._push(l - r)

    def div(self):
        l = self._pop()
        r = self._pop()
        self._push(l / r)

    def mult(self):
        l = self._pop()
        r = self._pop()
        self._push(l * r)

    def retn(self):
        raise Return()

    def call(self, idx):
        try:
            func_instr = self.am._funcs[idx]
        except IndexError:
            raise RuntimeError('Function %d does not exist.' % idx)

        self._ctx_stack.append({})
        try:
            self.execute(func_instr)
        except Return:
            pass
        self._ctx_stack.pop()

    def store_var(self, local_idx):
        try:
            self._ctx_stack[-1][local_idx] = self._pop()
        except IndexError:
            raise RuntimeError('Invalid local assignment outside function.')

    def store_global(self, global_idx):
        self._globals[global_idx] = self._pop()

    def load_const(self, const_idx):
        try:
            self._push(self.am._consts[const_idx])
        except IndexError:
            raise RuntimeError('Invalid constant index %d.' % const_idx)

    def load_global(self, global_idx):
        try:
            self._push(self._globals[global_idx])
        except IndexError:
            raise RuntimeError('Invalid global index %d.' % global_idx)

    def load_local(self, local_idx):
        try:
            ctx = self._ctx_stack[-1]
        except IndexError:
            raise RuntimeError('Invalid local read outside function.')

        try:
            self._push(ctx[local_idx])
        except IndexError:
            raise RuntimeError('Invalid local index %d.' % local_idx)

    def proc(self):
        raise RuntimeError('PROC instruction should never be executed.')

    def make_function(self):
        raise RuntimeError('MAKE_FUNCTION instruction should never be executed.')

    def call_builtin(self, builtin_idx):
        self._builtins.call(builtin_idx)

    def y_pass(self):
        pass

    def jz(self, local_ptr):
        if self._pop() == 0:
            # The -1 to counteract the += 1 in execute loop
            self._ip = local_ptr - 1

    def jnz(self, local_ptr):
        if self._pop() != 0:
            # The -1 to counteract the += 1 in execute loop
            self._ip = local_ptr - 1

    def execute(self, instructions):
        self._ip = 0
        while self._ip < len(instructions):
            instr, arg = instructions[self._ip]
            try:
                instr_name = Instr._names[instr]
                f = getattr(self, instr_name)
            except KeyError:
                raise RuntimeError('Unknown instruction type %d' % instr)
            except AttributeError:
                raise NotImplementedError()

            if instr in Instr.NO_PARAMS:
                f()
            else:
                f(arg)

            self._ip += 1


class AbstractMachine(object):
    """Decodes bytecode and bootstraps virtual machines."""

    def __init__(self, bytecode):
        self._bc = buffer(bytecode)

        self._last_read_len = 0
        # Read pointer
        self._rp = 0

        self._funcs = []
        self._consts = []

        self._read_magic()
        self._decode_consts()
        self._read_funcs()
        self._first_instr = self._rp

        self._toplevel = self._decode()

    def _read(self, n=1, advance=True):
        """@rtype: str"""
        self._last_read_len = n
        bytes = self._bc[self._rp:self._rp + n]
        if advance:
            self._advance()
        return bytes

    def _advance(self, n=None):
        if n is None:
            n = self._last_read_len
        self._rp += n

    def _read_magic(self):
        if self._read(4) != MAGIC:
            raise ValueError('Magic constant not found. Invalid bytecode.')

    def _instr(self, advance=True):
        byte = self._read(advance=advance)
        if not byte:
            return None
        else:
            return struct.unpack('B', byte)[0]
    _byte = _instr

    def _short(self):
        short = self._read(2)
        return struct.unpack('H', short)[0]

    def _decode_consts(self):
        table_size, = struct.unpack('I', self._read(4))
        if table_size == 0:
            return

        consts_end = self._rp + table_size
        while self._rp < consts_end:
            typ = self._byte()
            if typ == Const.INT:
                v, = struct.unpack('I', self._read(4))
            elif typ == Const.FLOAT:
                v, = struct.unpack('f', self._read(4))
            elif typ == Const.STRING:
                start = self._bc[self._rp:]
                try:
                    nul = start.index('\0')
                except IndexError:
                    raise ValueError('Unterminated string.')
                v = start[:nul]
                self._advance(nul + 1)
            else:
                raise TypeError('Unknown constant type %d' % typ)

            self._consts.append(v)

    def _read_funcs(self):
        while True:
            proc = self._instr(False)
            if proc != Instr.PROC:
                return
            self._advance()

            func_instr = self._decode(Instr.MAKE_FUNCTION)
            self._funcs.append(func_instr)

    def _decode(self, until=None):
            offs_rps = {}
            repl_offs = []
            instructions = []
            while True:
                offs_rps[self._rp] = len(instructions)
                instr = self._instr()
                if instr == until:
                    break

                if instr in Instr.JUMPS:
                    repl_offs.append(len(instructions))
                    pack = (instr, self._first_instr + self._short())
                elif instr in Instr.ONE_PARAM:
                    pack = (instr, self._byte())
                else:
                    pack = (instr, None)
                instructions.append(pack)
            else:
                if until is not None:
                    raise ValueError('Unexpected end of code')

            for i in repl_offs:
                instr, rp = instructions[i]
                try:
                    instructions[i] = (instr, offs_rps[rp])
                except IndexError:
                    raise ValueError('Invalid jump')

            return instructions

    def run(self):
        vm = VirtualMachine(self)
        vm.execute(self._toplevel)
