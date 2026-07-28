# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

"""Simple clock divider example"""

from lib_carotte import *


def main() -> None:
    """Entry point of this example"""
    x = Input(1)
    s: Variable = Reg(Defer(1, lambda: x ^ s))
    r = x & s
    r.set_as_output("r")
