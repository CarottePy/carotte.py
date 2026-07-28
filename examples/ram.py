# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

"""Simple RAM example"""

import functools
import typing

from lib_carotte import *


def or_n(a: Variable, b: Variable) -> Variable:
    """n-bit logical OR implementation"""
    assert a.bus_size == b.bus_size
    if a.bus_size == 1:
        return a | b
    return (a[0] | b[0]) + or_n(a[1:], b[1:])


def or_n_alt(a: Variable, b: Variable) -> Variable:
    """n-bit logical OR alternative implementation"""
    assert a.bus_size == b.bus_size
    return functools.reduce(lambda x, y: x + y, [x | y for x, y in zip(a, b)])


def or_n_alt2(a: Variable, b: Variable) -> Variable:
    """n-bit logical OR alternative implementation"""
    assert a.bus_size == b.bus_size
    c: typing.Optional[Variable] = None
    for x, y in zip(a, b):
        c = x | y if c is None else c + (x | y)
    assert c
    return c


def main() -> None:
    """Entry point of this example"""
    addr_size = 2
    word_size = 4
    read_addr = Input(addr_size)
    write_enable = Input(1)
    write_addr = Input(addr_size)
    input_write_data = Input(word_size)
    o: Variable = RAM(
        addr_size, word_size, read_addr, write_enable, write_addr, Defer(word_size, lambda: or_n(input_write_data, o))
    )
    o.set_as_output("o")
