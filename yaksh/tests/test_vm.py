import pytest

from yaksh.tests.utils import vm_output


@pytest.mark.parametrize(
    ('expected', 'expr'),
    (
        ('2', '1 + 1'),
        ('11', '10 + 1'),
        ('4', '8 - (3 + 1)'),
        ('26', '8 + 6 * 3'),
        ('7', '6 * 7 / 6'),
        ('36', '(8 - 4) + (8 * 4)'),
    )
)
def test_arithmetic(expr, expected):
    source = 'print(%s)' % expr
    output = vm_output(source).strip()
    assert output == expected, ('''
=== SOURCE ===
%s
==============

=== EXPECTED ===
%s
================

=== ACTUAL ===
%s
==============''' % (source, expected, output))
