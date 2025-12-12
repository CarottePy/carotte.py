# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

'''Simple n-adder example'''

import functools

from examples import fulladder
from lib_carotte import *


def adder(a: Variable, b: Variable, c_in: Variable, i: int | None = None) -> typing.Tuple[Variable, Variable]:
    '''n-bit full-adder implementation'''
    assert a.bus_size == b.bus_size
    if i is None:
        i = a.bus_size-1
    assert 0 <= i < a.bus_size
    if i == 0:
        return fulladder.full_adder(a[i], b[i], c_in)
    (res_rest, c_rest) = adder(a, b, c_in, i-1)
    (res_i, c_out) = fulladder.full_adder(a[i], b[i], c_rest)
    return (res_rest + res_i, c_out)

def adder_alt(a: Variable, b: Variable, c_in: Variable) -> typing.Tuple[Variable, Variable]:
    '''n-bit full-adder alternative implementation'''
    assert a.bus_size == b.bus_size
    return functools.reduce(lambda x, y: (lambda r=fulladder.full_adder(y[0], y[1], x[1]): # type: ignore
                                          (r[0] if x[0] is None else x[0]+r[0], r[1]) # type: ignore
                                         )(), zip(a, b), (None, c_in))

def main() -> None:
    '''Entry point of this example'''
    n = 4
    a = Input(n)
    b = Input(n)
    c = Input(1)
    (result, out_carry) = adder(a, b, c)
    result.set_as_output("result")
    out_carry.set_as_output("out_carry")
    Verif.AssertEqual(result, Verif.BVAdd(a, Verif.BVAdd(b, Verif.BVZeroExtend(c, n))))
    (result_alt, out_carry_alt) = adder_alt(a, b, c)
    Verif.AssertEqual(result, result_alt)
    Verif.AssertEqual(out_carry, out_carry_alt)
