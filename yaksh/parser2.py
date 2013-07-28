class _AbstractSymbolMeta(type):
    def __new__(S, *more):
        cls = super(_AbstractSymbolMeta, S).__new__(*more)
        cls.name = cls.__name__.lower()


class _Symbol(object):
    __metaclass__ = _AbstractSymbolMeta


class Function(_Symbol):
    def __init__(self, name, parameters, block):
        self.name = name
        self.parameters = parameters
        self.block = block


#def parse2(symbols):
#    for symbol in symbols:
#        if symbol.name == 'fdef':
#            define_function(symbol)
#        else:
#            eval_stmt(symbol)
