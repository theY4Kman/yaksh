"""
A bytecode compiler for this god-forsaken language.
"""
from contextlib import contextmanager

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


RESERVED_STMTS = {'return_stmt', 'pass_stmt', 'if_stmt'}


class BytecodeAssemblyGenerator(object):
    OP_FUNCS = {
        '+': 'add',
        '-': 'sub',
        '/': 'div',
        '*': 'mult',
    }

    def __init__(self, symbols):
        self.symbols = symbols

        self._bc = StringIO()
        self._locals = None
        self._globals = {}
        self._func_globals = []
        self._funcs = []
        self._func_names = {}

    def _(self, asm):
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
            # TODO: pack float?
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
        self._funcs.append(self._bc.getvalue())
        self.make_function()

        self._bc = bytecode

    #################################
    # SYMBOL TRANSFORMATION METHODS #
    #################################
    def gen_value_stmt(self, value_stmt):
        vals = []
        ops = []
        for v in value_stmt.symbols:
            if v.name in ('value_stmt', 'value'):
                vals.append(v)
            else:
                # Operator
                ops.append(v.symbols[0].text)

        if ops:
            while ops:
                for i in xrange(2):
                    v = vals.pop()
                    if v is None:
                        pass
                    elif v.name == 'value_stmt':
                        self.gen_value_stmt(v)
                    elif v.name == 'value':
                        self.gen_value(v)

                getattr(self, self.OP_FUNCS[ops.pop()])()
                vals.append(None)
        else:
            v = vals.pop()
            if v.name == 'value_stmt':
                self.gen_value_stmt(v)
            elif v.name == 'value':
                self.gen_value(v)
            else:
                raise NotImplementedError('wat?')

    def gen_value(self, value):
        val_sym = value.symbols[0]
        if val_sym.name == 'number':
            number = self._get_number_const(val_sym)
            self.load_const(number)
        elif val_sym.name == 'literal':
            self.load_const("'%s'" % val_sym.symbols[0].text)
        elif val_sym.name == 'var':
            name = val_sym.symbols[0].text
            try:
                self.load_local(self._locals[name])
            except KeyError:
                self.load_global(name)
        elif val_sym.name == 'fcall':
            self.gen_fcall(val_sym)
        else:
            raise NotImplementedError()

    def gen_assign(self, assign):
        value_stmt = assign.symbols[2]
        self.gen_value_stmt(value_stmt)

        name = assign.symbols[0].text
        self._store_var(name)

    def gen_reserved(self, reserved):
        if reserved.name == 'return_stmt':
            if reserved.symbols:
                self.gen_value_stmt(reserved.symbols[0])
            self.retn()
        elif reserved.name == 'pass':
            pass
        else:
            raise NotImplementedError()

    def gen_fcall(self, fcall):
        funcname = fcall.symbols[0].text
        try:
            func_idx = self._func_names[funcname]
        except KeyError:
            raise NameError("name '%s' does not exist" % funcname)

        arglist = fcall.symbols[1]
        for arg in arglist.symbols:
            self.gen_value_stmt(arg)

        self.call(func_idx)

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
        name_sym = fdef.symbols[0]
        funcname = name_sym.symbols[0].text

        with self._define_function(funcname):
            parameters_list = fdef.symbols[1].symbols
            last_param_idx = len(parameters_list) - 1
            for p in parameters_list:
                param = p.text
                self._locals[param] = idx = len(self._locals)
                self.store_var(last_param_idx - idx)

            block = fdef.symbols[2]
            for stmt in block.symbols:
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
        funcs = '\n'.join(self._funcs)
        return '\n'.join((funcs, self._bc.getvalue()))

