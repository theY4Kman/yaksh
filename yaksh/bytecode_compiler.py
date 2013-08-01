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


class Instr(object):
    ADD         = 1
    SUB         = 2
    DIV         = 3
    MULT        = 4
    RETN        = 5
    CALL        = 6
    STORE_VAR   = 7
    STORE_GLOBAL= 8
    LOAD_CONST  = 9
    LOAD_GLOBAL = 10
    LOAD_LOCAL  = 11
    PROC        = 12
    MAKE_FUNCTION=13

    NO_PARAMS = (
        ADD,
        SUB,
        DIV,
        MULT,
        RETN,
        PROC,
    )

    ONE_PARAM = (
        CALL,
        STORE_VAR,
        STORE_GLOBAL,
        LOAD_CONST,
        LOAD_GLOBAL,
        LOAD_LOCAL,
        MAKE_FUNCTION,
    )


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


def assemble(asm):
    # Note: this assumes function definitions are already at the top of the
    #       assembly. This is unnecessary, but makes the assembler simpler.

    pieces = []
    # List of packed constants
    consts = []
    # Hash table of packed constants, to remove unnecessary duplication
    consts_table = {}

    for line in asm.split('\n'):
        line = line.strip()
        if not line:
            continue

        s_instr, _, arg = line.partition(' ')
        s_instr = s_instr.upper()
        instr = getattr(Instr, s_instr, None)
        if instr is None:
            raise ValueError("Unknown instruction '%s'" % s_instr)

        arg = arg.strip()
        if instr in Instr.NO_PARAMS and arg:
            raise ValueError("Instruction '%s' takes no parameter" % s_instr)
        elif instr in Instr.ONE_PARAM and not arg:
            raise ValueError("Instruction '%s' takes one parameter" % s_instr)

        pieces.append(struct.pack('B', instr))
        if instr in Instr.NO_PARAMS:
            continue

        if instr == Instr.LOAD_CONST:
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
        else:
            try:
                param = int(arg)
            except ValueError:
                raise ValueError('Malformed parameter: %s' % arg)

        pieces.append(struct.pack('B', param))

    p_consts = ''.join(consts)
    p_const_size = struct.pack('I', len(p_consts))
    p_pieces = ''.join(pieces)

    return ''.join((p_const_size, p_consts, p_pieces))
