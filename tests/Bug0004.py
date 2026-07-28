"""Regression test for issue #4"""

from lib_carotte import *


def main() -> None:
    """Regression test for issue #4"""
    reg0 = Reg(Select(0, Defer(1, lambda: c)))
    c = reg0
