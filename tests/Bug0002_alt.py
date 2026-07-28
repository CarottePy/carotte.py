"""Regression test for issue #2"""

from lib_carotte import *


def main() -> None:
    """Regression test for issue #2"""
    reg0 = Reg(Defer(1, lambda: Reg(Defer(1, lambda: c[0]))))
    c = reg0
