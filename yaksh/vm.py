import struct
from yaksh.bytecode_compiler import MAGIC, Const, Instr


class Return(Exception):
    pass


class VirtualMachine(object):
    """Handles the actual execution of instructions"""

    def __init__(self, am):
        self.am = am
        self._stack = []
        self._ctx_stack = []
        self._globals = {}

    def _pop(self):
        return self._stack.pop()

    def _push(self, v):
        self._stack.append(v)

    def add(self):
        r = self._pop()
        l = self._pop()
        self._push(r + l)

    def sub(self):
        r = self._pop()
        l = self._pop()
        self._push(r - l)

    def div(self):
        r = self._pop()
        l = self._pop()
        self._push(r / l)

    def mult(self):
        r = self._pop()
        l = self._pop()
        self._push(r * l)

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

    def execute(self, instructions):
        for instr, arg in instructions:
            try:
                f = getattr(self, Instr._names[instr])
            except KeyError:
                raise RuntimeError('Unknown instruction type %d' % instr)
            except AttributeError:
                raise NotImplementedError()

            if instr in Instr.NO_PARAMS:
                f()
            else:
                f(arg)


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
            instructions = []
            while True:
                instr = self._instr()
                if instr == until:
                    return instructions

                if instr in Instr.ONE_PARAM:
                    instructions.append((instr, self._byte()))
                else:
                    instructions.append((instr, None))
            else:
                if until is not None:
                    raise ValueError('Unexpected end of code')
                return instructions

    def run(self):
        vm = VirtualMachine(self)
        vm.execute(self._toplevel)
