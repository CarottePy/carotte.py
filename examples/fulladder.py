# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

"""Simple fulladder example"""

from lib_carotte import *


def full_adder(a: Variable, b: Variable, c: Variable) -> typing.Tuple[Variable, Variable]:
    """1-bit full adder implementation"""
    tmp = a ^ b
    return (tmp ^ c, (tmp & c) | (a & b))


def main() -> None:
    """Entry point of this example"""
    a = Input(1)
    b = Input(1)
    c = Input(1)
    (result, out_carry) = full_adder(a, b, c)
    result.set_as_output("r")
    out_carry.set_as_output("out_c")
