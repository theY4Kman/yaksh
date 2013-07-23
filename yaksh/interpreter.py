OPERATOR_FUNCS = {
    '*': lambda r, l: r * l,
    '/': lambda r, l: r / l,
    '-': lambda r, l: r - l,
    '+': lambda r, l: r + l,
}

RESERVED_STMTS = {'return_stmt', 'pass_stmt'}


class Function(object):
    def __init__(self, interp, funcname, parameters, block):
        self.interp = interp
        self.name = funcname
        self.parameters = parameters
        self.block = block
        self.locals = {}

    def __call__(self, *args):
        scope = dict(zip(self.parameters, args))
        self.interp.stack.append(scope)
        rv = None
        for symbol in self.block.symbols:
            if self.interp.should_return:
                break
            self.interp.eval_stmt(symbol)
        self.interp.stack.pop()
        self.interp.should_return = False
        rv, self.interp.return_value = self.interp.return_value, None
        return rv


class StandardFunctions(object):
    def __init__(self, interp):
        self.interp = interp

    def __contains__(self, item):
        return hasattr(self, 'do_' + item)

    def __getitem__(self, item):
        return getattr(self, 'do_' + item)

    def do_print(self, *args):
        for arg in args:
            print arg,
        print


class Interpreter(object):
    def __init__(self, symbols):
        self.symbols = symbols
        self.stack = []
        self.globals = {}
        self.std_functions = StandardFunctions(self)

        self.should_return = False
        self.return_value = None

    def define_function(self, fdef):
        name_sym = fdef.symbols[0]
        funcname = name_sym.symbols[0].text
        parameters_list = fdef.symbols[1].symbols
        parameters = [p.text for p in parameters_list]
        block = fdef.symbols[2]
        func = Function(self, funcname, parameters, block)
        self.globals[funcname] = func

    def eval_assign_statement(self, assign_stmt):
        name = assign_stmt.symbols[0].text
        value_stmt = assign_stmt.symbols[2]
        value = self.eval_value_stmt(value_stmt)
        self.set_var(name, value)

    @property
    def scope(self):
        if self.stack:
            return self.stack[-1]
        else:
            return self.globals

    def eval_value_stmt(self, value_stmt):
        vals = []
        ops = []
        for v in value_stmt.symbols:
            if v.name == 'value_stmt':
                vals.append(self.eval_value_stmt(v))
            elif v.name == 'value':
                vals.append(self.eval_value(v))
            else:
                # Operator
                ops.append(v.symbols[0].text)

        while ops:
            l = vals.pop()
            r = vals.pop()
            op = ops.pop()
            opfunc = OPERATOR_FUNCS[op]
            vals.append(opfunc(r, l))

        return vals[0]

    def eval_value(self, value):
        symbol = value.symbols[0]
        if symbol.name == 'number':
            return self.number(symbol.symbols[0].text)
        elif symbol.name == 'literal':
            return symbol.symbols[0].text
        elif symbol.name == 'var':
            return self.get_var(symbol.symbols[0].text)
        else:
            return self.eval_fcall(symbol)

    def eval_fcall(self, fcall):
        funcname = fcall.symbols[0].text
        if funcname in self.std_functions:
            func_obj = self.std_functions[funcname]
        else:
            func_obj = self.get_var(funcname)
            if not isinstance(func_obj, Function):
                raise TypeError('%s is not a function' % funcname)

        args = self.eval_arglist(fcall.symbols[1])
        if isinstance(func_obj, Function) and len(args) != len(func_obj.parameters):
            raise TypeError('%s() takes %d arguments (%d given)' %
                            (funcname, len(func_obj.parameters), len(args)))

        return func_obj(*args)

    def number(self, text):
        if text[:2] in ('0x', '0h'):
            return int(text, 16)
        elif text.startswith('0b'):
            return int(text[2:], 2)
        elif '.' in text:
            return float(text)
        else:
            return int(text)

    def set_var(self, name, value):
        self.scope[name] = value

    def get_var(self, name):
        try:
            return self.scope[name]
        except KeyError:
            if self.stack:
                return self.globals[name]
            else:
                raise

    def eval_arglist(self, arglist):
        return [self.eval_value_stmt(v) for v in arglist.symbols]

    def eval_reserved_stmt(self, reserved_stmt):
        if reserved_stmt.name == 'return_stmt':
            self.eval_return_stmt(reserved_stmt)

    def run(self):
        for symbol in self.symbols:
            if symbol.name == 'fdef':
                self.define_function(symbol)
            else:
                self.eval_stmt(symbol)

    def eval_stmt(self, stmt):
        if stmt.name in RESERVED_STMTS:
            self.eval_reserved_stmt(stmt)
        elif stmt.name == 'assign':
            self.eval_assign_statement(stmt)
        elif stmt.name == 'fcall':
            self.eval_fcall(stmt)
        elif stmt.name == 'var':
            self.get_var(stmt.symbols[0].text)
        else:
            raise NotImplementedError('Symbol type %s' % stmt.name)

    def eval_return_stmt(self, return_stmt):
        if not self.stack:
            raise SyntaxError('return outside of function')
        self.should_return = True
        if return_stmt.symbols:
            rv_stmt = return_stmt.symbols[0]
            self.return_value = self.eval_value_stmt(rv_stmt)
