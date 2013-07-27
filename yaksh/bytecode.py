"""
A bytecode compiler for this god-forsaken language.
"""

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


RESERVED_STMTS = {'return_stmt', 'pass_stmt', 'if_stmt'}


class BytecodeGenerator(object):
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

    def store_var(self, index):
        self._('STORE_VAR %d' % index)

    def store_global(self, index):
        self._('STORE_GLOBAL %d' % index)

    def load_const(self, value):
        self._('LOAD_CONST %s' % value)

    def load_global(self, index):
        self._('LOAD_GLOBAL %d' % index)

    def load_local(self, index):
        self._('LOAD_LOCAL %d' % index)

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

    def gen_value(self, value):
        val_sym = value.symbols[0]
        if val_sym.name == 'number':
            number = self._get_number_const(val_sym)
            self.load_const(number)
        elif val_sym.name == 'var':
            name = val_sym.symbols[0].text
            try:
                self.load_local(self._locals[name])
            except KeyError:
                self.load_global(name)
        else:
            raise NotImplementedError()

    def gen_assign(self, assign):
        value_stmt = assign.symbols[2]
        self.gen_value_stmt(value_stmt)

        name = assign.symbols[0].text
        self._store_var(name)

    #############
    # Generate! #
    #############
    def generate(self):
        for symbol in self.symbols:
            if symbol.name == 'assign':
                self.gen_assign(symbol)
            if symbol.name == 'value_stmt':
                self.gen_value_stmt(symbol)
        return self._bc.getvalue()

