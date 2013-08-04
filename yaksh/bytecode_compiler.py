"""
# .ysh file format

-----------------
 CONSTANTS
-----------------
 FUNCTIONS
-----------------
 TOP-LEVEL CODE
-----------------

The constants table begins with a 32-bit unsigned integer denoting the size of
the table. Each constant is comprised of a 1-byte type identifier (see Const
class), and a variable number of bytes depending on the type. Floats and
integers use a fixed 4-byte word. Strings are variable-length and
null-terminated.

The functions section is comprised of function definitions, each delimited by
a PROC and MAKE_FUNCTION. The end of the section is the last MAKE_FUNCTION call
preceded by a PROC.

The top-level code section is comprised of pure instructions to be run.

Every instruction begins with 1 byte denoting the instruction type. Depending
on the type, there may be a 1-byte parameter which follows.


Extra notes:
 - The LOAD_CONST instruction accepts a string parameter in assembly. This
   value is packed and placed in the constants table. In the generated
   bytecode, the parameter is replaced with an index into the constants table.
"""
import struct
from collections import defaultdict
from os import SEEK_SET, SEEK_END

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


MAGIC = '\x42YAK'
PYTHON_RESERVED = ('pass',)


class _InstrMeta(type):
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        names = {}
        for name, value in attrs.iteritems():
            if isinstance(value, int):
                name = name.lower()
                if name in PYTHON_RESERVED:
                    name = 'y_' + name
                names[value] = name
        cls._names = names
        return cls


class Instr(object):
    __metaclass__ = _InstrMeta

    ADD             = 1
    SUB             = 2
    DIV             = 3
    MULT            = 4
    RETN            = 5
    CALL            = 6
    STORE_VAR       = 7
    STORE_GLOBAL    = 8
    LOAD_CONST      = 9
    LOAD_GLOBAL     = 10
    LOAD_LOCAL      = 11
    PROC            = 12
    MAKE_FUNCTION   = 13
    CALL_BUILTIN    = 14
    PASS            = 15
    JZ              = 16
    JNZ             = 17
    JMP             = 18
    CMP             = 19

    NO_PARAMS = (
        ADD,
        SUB,
        DIV,
        MULT,
        RETN,
        PROC,
        MAKE_FUNCTION,
        PASS,
    )

    JUMPS = {
        JZ,
        JNZ,
        JMP,
    }

    ONE_PARAM = {
        CALL,
        STORE_VAR,
        STORE_GLOBAL,
        LOAD_CONST,
        LOAD_GLOBAL,
        LOAD_LOCAL,
        CALL_BUILTIN,
        CMP,
    }.union(JUMPS)


class Const(object):
    INT     = 0
    FLOAT   = 1
    STRING  = 2

    @staticmethod
    def pack(v):
        if isinstance(v, int):
            v_p = struct.pack('i', v)
            t = Const.INT
        elif isinstance(v, float):
            v_p = struct.pack('f', v)
            t = Const.FLOAT
        elif isinstance(v, str):
            v_p = v + '\0'
            t = Const.STRING
        else:
            raise NotImplementedError()

        return struct.pack('B', t) + v_p


class _CompareMeta(type):
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        names = {}
        for name, value in attrs.iteritems():
            if isinstance(value, int):
                names[name] = value
        cls._names = names
        return cls


class Compare(object):
    __metaclass__ = _CompareMeta

    ISEQUAL     = 0
    NOTEQUAL    = 1
    GT          = 2
    GTE         = 3
    LT          = 4
    LTE         = 5

    _cmp = {
        ISEQUAL: lambda r, l: r == l,
        NOTEQUAL: lambda r, l: r != l,
        GT: lambda r, l: r > l,
        GTE: lambda r, l: r >= l,
        LT: lambda r, l: r < l,
        LTE: lambda r, l: r <= l,
    }

    @staticmethod
    def cmp(op, r, l):
        try:
            return Compare._cmp[op](r, l)
        except KeyError:
            raise NotImplementedError('Unknown comparison op %d' % op)


def assemble(asm):
    # Note: this assumes function definitions are already at the top of the
    #       assembly. This is unnecessary, but makes the assembler simpler.

    out = StringIO()
    # List of packed constants
    consts = []
    # Hash table of packed constants, to remove unnecessary duplication
    consts_table = {}
    # Map of labels to `out` indices
    labels = [{}]
    # Label locations in `out` to replace with pointers
    label_rplc = [defaultdict(list)]

    def _replace_labels():
        for label, rpl_locs in label_rplc[-1].iteritems():
            if label not in labels[-1]:
                raise ValueError("Unknown label '%s'" % label)
            for loc in rpl_locs:
                local_offs = labels[-1][label]
                out.seek(loc, SEEK_SET)
                out.write(struct.pack('H', local_offs))
                out.seek(0, SEEK_END)

    def _pop_labels():
        labels.pop()
        label_rplc.pop()

    def _push_labels():
        labels.append({})
        label_rplc.append(defaultdict(list))

    for line in asm.split('\n'):
        line = line.strip()
        if not line:
            continue

        s_instr, _, arg = line.partition(' ')
        if s_instr.endswith(':'):
            if not s_instr[0].isalpha():
                if len(s_instr) == 1:
                    raise ValueError('Empty label')
                elif not s_instr[0] == '_':
                    raise ValueError("Invalid label name '%s'" % s_instr[:-1])
            label_name = s_instr[:-1]
            if label_name in labels:
                raise ValueError("Label '%s' already exists" % label_name)
            labels[-1][label_name] = out.tell()

            # Redo the partition on the rest of the line
            s_instr, _, arg = arg.lstrip().partition(' ')

        s_instr = s_instr.upper()
        instr = getattr(Instr, s_instr, None)
        if instr is None:
            raise ValueError("Unknown instruction '%s'" % s_instr)

        arg = arg.strip()
        if instr in Instr.NO_PARAMS and arg:
            raise ValueError("Instruction '%s' takes no parameter" % s_instr)
        elif instr in Instr.ONE_PARAM and not arg:
            raise ValueError("Instruction '%s' takes one parameter" % s_instr)

        out.write(struct.pack('B', instr))
        if instr in Instr.NO_PARAMS:
            if instr == Instr.MAKE_FUNCTION:
                _replace_labels()
                _pop_labels()
            elif instr == Instr.PROC:
                _push_labels()
            continue
        elif instr == Instr.LOAD_CONST:
            if arg[0] in ('"', "'"):
                if len(arg) == 1 or arg[-1] != arg[0]:
                    raise ValueError('Malformed string constant: %s' % arg)
                v = arg[1:-1]
            elif '.' in arg:
                try:
                    v = float(arg)
                except ValueError:
                    raise ValueError('Malformed float constant: %s' % arg)
            else:
                try:
                    v = int(arg)
                except ValueError:
                    raise ValueError('Malformed int constant: %s' % arg)

            packed = Const.pack(v)
            if packed in consts_table:
                idx = consts_table[packed]
            else:
                idx = len(consts)
                consts.append(packed)
                consts_table[packed] = idx
            param = idx
        elif instr in Instr.JUMPS:
            label_rplc[-1][arg].append(out.tell())
            out.write(struct.pack('H', 0))
            continue
        else:
            try:
                param = int(arg)
            except ValueError:
                raise ValueError('Malformed parameter: %s' % arg)

        out.write(struct.pack('B', param))

    _replace_labels()

    p_consts = ''.join(consts)
    p_const_size = struct.pack('I', len(p_consts))
    p_pieces = out.getvalue()

    return ''.join((MAGIC, p_const_size, p_consts, p_pieces))
