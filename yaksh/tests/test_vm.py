import pytest

from yaksh.tests.utils import vm_output


def _expected_actual(expected, output, source):
    return ('''
=== SOURCE ===
%s
==============

=== EXPECTED ===
%s
================

=== ACTUAL ===
%s
==============''' % (source, expected, output))


@pytest.mark.parametrize(
    ('expr', 'expected'),
    (
        ('1 + 1', '2'),
        ('10 + 1', '11'),
        ('8 - (3 + 1)', '4'),
        ('8 + 6 * 3', '26'),
        ('6 * 7 / 6', '7'),
        ('(8 - 4) + (8 * 4)', '36'),
    )
)
def test_arithmetic(expr, expected):
    source = 'print(%s)' % expr
    output = vm_output(source).strip()
    assert output == expected, _expected_actual(expected, output, source)


@pytest.mark.parametrize(
    ('source', 'expected'),
    (
        ('''
def print_literal():
    print('test literal')
print_literal()
''', 'test literal'),
        ('''
def print_param_literal(s):
    print(s)
print_param_literal('test param')
''', 'test param'),
        ('''
def print_param_arith(a, b, c):
    print(a + b + c)
print_param_arith(1, 2, 3)''', '6'),
        ('''
def do_arith(a, b, c):
    return a + b + c
print(do_arith(1, 2, 3))''', '6')
    ),
)
def test_functions(source, expected):
    output = vm_output(source).strip()
    assert output == expected, _expected_actual(expected, output, source)


@pytest.mark.parametrize(
    ('source', 'expected'),
    (
        ('''
if 1:
    print("1")''', '1'),
    )
)
def test_if_chain(source, expected):
    output = vm_output(source).strip()
    assert output == expected, _expected_actual(expected, output, source)
