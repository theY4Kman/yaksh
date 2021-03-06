"""
A bytecode compiler for this god-forsaken language.
"""
from contextlib import contextmanager

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from yaksh.parser import Symbol


RESERVED_STMTS = {'return_stmt', 'pass_stmt', 'if_chain'}
BUILTINS = (
    'print',
)


class BytecodeAssemblyGenerator(object):
    def __init__(self, symbols):
        self.symbols = symbols

        self._bc = StringIO()
        self._locals = None
        self._globals = {}
        self._func_globals = []
        self._funcs = []
        self._func_names = {}

        self._label = None
        self._label_counters = [0]

    def _(self, asm):
        if self._label:
            self._bc.write(self._label + ': ')
            self._label = None
        self._bc.write(asm)
        self._bc.write('\n')

    ###############################
    # BYTECODE GENERATING METHODS #
    ###############################
    def add(self):
        self._('ADD')

    def sub(self):
        self._('SUB')

    def div(self):
        self._('DIV')

    def mult(self):
        self._('MULT')

    def retn(self):
        self._('RETN')

    def call(self, func_idx):
        self._('CALL %d' % func_idx)

    def store_var(self, local_index):
        self._('STORE_VAR %d' % local_index)

    def store_global(self, global_idx):
        self._('STORE_GLOBAL %d' % global_idx)

    def load_const(self, value):
        self._('LOAD_CONST %s' % value)

    def load_global(self, global_idx):
        self._('LOAD_GLOBAL %d' % global_idx)

    def load_local(self, local_idx):
        self._('LOAD_LOCAL %d' % local_idx)

    def proc(self):
        self._('PROC')

    def make_function(self):
        self._('MAKE_FUNCTION')

    def call_builtin(self, builtin_idx):
        self._('CALL_BUILTIN %d' % builtin_idx)

    def y_pass(self):
        self._('PASS')

    def jz(self, label):
        self._('JZ %s' % label)

    def jnz(self, label):
        self._('JNZ %s' % label)

    def jmp(self, label):
        self._('JMP %s' % label)

    def cmp(self, op):
        self._('CMP %d' % op)

    #############
    # Utilities #
    #############
    def _get_number_const(self, num_sym):
        s_num = num_sym.symbols[0].text
        if s_num[:2] in ('0x', '0h'):
            return int(s_num, 16)
        elif s_num.startswith('0b'):
            return int(s_num[2:], 2)
        elif '.' in s_num:
            return float(s_num)
        else:
            return int(s_num)

    def _store_var(self, name):
        if self._locals:
            if name in self._locals:
                index = self._locals[name]
                if isinstance(index, str):
                    self._store_global(index)
                    return
                else:
                    index = len(self._locals)
                    self._locals[name] = index
                self.store_var(index)
        else:
            self._store_global(name)

    def _store_global(self, name):
        if name in self._globals:
            index = self._globals[name]
        else:
            index = len(self._globals)
            self._globals[name] = index
        self.store_global(index)

    @contextmanager
    def _define_function(self, funcname):
        bytecode = self._bc
        self._bc = StringIO()

        self.proc()
        old_locals = self._locals
        self._locals = {}

        yield

        self._locals = old_locals
        self._func_names[funcname] = len(self._funcs)
        self.make_function()
        self._funcs.append(self._bc.getvalue())

        self._bc = bytecode

    @contextmanager
    def _local_labels(self):
        self._label_counters.append(0)
        yield
        self._label_counters.pop()
        self._label_counters[-1] += 1

    def _get_next_label(self, rel_label):
        # This is not very robust, because a label name like "0_test" would end
        # up jumping to a lower-level test. However, since I'm controlling the
        # output of assembly generator, and thus the name of the labels, I can
        # make the assertion.
        assert not rel_label[0].isdigit()
        depth_unique = '_'.join(str(c) for c in self._label_counters)
        actual_label = '_%s_%s' % (depth_unique, rel_label)
        return actual_label

    def _label_next(self, label):
        self._label = label

    #################################
    # SYMBOL TRANSFORMATION METHODS #
    #################################
    def gen_value_stmt(self, value_stmt):
        vals = []
        ops = []
        for v in value_stmt.symbols:
            if v.name in ('cmp_stmt', 'value_stmt', 'value'):
                vals.append(v)
            else:
                # Operator
                ops.append(v)

        if ops:
            while ops:
                for i in xrange(2):
                    v = vals.pop()
                    if v is None:
                        pass
                    elif v.name == 'cmp_stmt':
                        self.gen_cmp_stmt(v)
                        vals.append(None)
                        continue
                    elif v.name == 'value_stmt':
                        self.gen_value_stmt(v)
                    elif v.name == 'value':
                        self.gen_value(v)

                getattr(self, ops.pop().opfunc)()
                vals.append(None)
        else:
            v = vals.pop()
            if v.name == 'cmp_stmt':
                self.gen_cmp_stmt(v)
            elif v.name == 'value_stmt':
                self.gen_value_stmt(v)
            elif v.name == 'value':
                self.gen_value(v)
            else:
                raise NotImplementedError('wat?')

    def gen_cmp_stmt(self, cmp_stmt):
        self.gen_value_stmt(cmp_stmt.right)
        self.gen_value_stmt(cmp_stmt.left)
        self.cmp(cmp_stmt.op)

    def gen_value(self, value):
        val_sym = value.symbols[0]
        if val_sym.name == 'number':
            self.load_const(val_sym.value)
        elif val_sym.name == 'literal':
            self.load_const("%r" % val_sym)
        elif val_sym.name == 'var':
            name = val_sym.text
            try:
                self.load_local(self._locals[name])
            except (KeyError, TypeError):
                try:
                    self.load_global(self._globals[name])
                except KeyError:
                    raise ValueError("Global or local var '%s' does not "
                                     "exist" % name)
        elif val_sym.name == 'fcall':
            self.gen_fcall(val_sym)
        else:
            raise NotImplementedError()

    def gen_assign(self, assign):
        self.gen_value_stmt(assign.value)
        self._store_var(assign.var)

    def gen_if_chain(self, if_chain):
        with self._local_labels():
            label_idx = 0
            last_test = len(if_chain.symbols) - 1
            for i, test_stmt in enumerate(if_chain.symbols):
                if test_stmt.cond:
                    self.gen_value_stmt(test_stmt.cond)
                    if i != last_test:
                        next_label = self._get_next_label('chain_next%d' % label_idx)
                        label_idx += 1
                    else:
                        next_label = 'chain_out'
                    self.jz(next_label)
                for stmt in test_stmt.block.symbols:
                    self.gen_stmt(stmt)
                if test_stmt.cond and i != last_test:
                    self.jmp('chain_out')
                    self._label_next(next_label)

            self._label_next('chain_out')

    def gen_reserved(self, reserved):
        if reserved.name == 'return_stmt':
            if reserved.value:
                self.gen_value_stmt(reserved.value)
            self.retn()
        elif reserved.name == 'pass_stmt':
            self.y_pass()
        elif reserved.name == 'if_chain':
            self.gen_if_chain(reserved)
        else:
            raise NotImplementedError()

    def gen_fcall(self, fcall):
        try:
            func_idx = BUILTINS.index(fcall.func_name)
            call = self.call_builtin
        except ValueError:
            try:
                func_idx = self._func_names[fcall.func_name]
                call = self.call
            except KeyError:
                raise NameError("name '%s' does not exist" % fcall.func_name)

        for arg in fcall.args:
            self.gen_value_stmt(arg)

        call(func_idx)

    def gen_stmt(self, stmt):
        if stmt.name in RESERVED_STMTS:
            self.gen_reserved(stmt)
        elif stmt.name == 'assign':
            self.gen_assign(stmt)
        elif stmt.name == 'fcall':
            self.gen_fcall(stmt)
        elif stmt.name == 'value_stmt':
            self.gen_value_stmt(stmt)
        else:
            raise NotImplementedError('Symbol type %s' % stmt.name)

    def gen_fdef(self, fdef):
        with self._define_function(fdef.func_name):
            last_param_idx = len(fdef.params) - 1
            for param in fdef.params:
                self._locals[param] = idx = len(self._locals)
                self.store_var(last_param_idx - idx)

            for stmt in fdef.stmts:
                self.gen_stmt(stmt)

    #############
    # Generate! #
    #############
    def generate(self):
        for symbol in self.symbols:
            if symbol.name == 'fdef':
                self.gen_fdef(symbol)
            else:
                self.gen_stmt(symbol)
        if self._label:
            self.gen_stmt(Symbol('pass_stmt', ()))
        funcs = '\n'.join(self._funcs)
        return '\n'.join((funcs, self._bc.getvalue()))

