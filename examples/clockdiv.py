# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

"""Simple clock divider example"""
from lib_carotte import *


def main() -> None:
    """Entry point of this example"""
    o = Reg(Defer(1, lambda: c))
    c: Variable = ~Reg(o)
    o.set_as_output("o")
