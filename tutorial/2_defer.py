# SPDX-License-Identifier: CC0-1.0
# carotte.py by TWal, hbens & more

from lib_carotte import *

def main():
    # Imagine the following netlist
    # o = REG c
    # c = NOT o

    # It gives the following output:
    # +------+---+---+
    # | Step | o | c |
    # +------+---+---+
    # |  0   | 0 | 1 |
    # |  1   | 1 | 0 |
    # |  2   | 0 | 1 |
    # |  3   | 1 | 0 |
    # +------+---+---+

    # How do we write it in carotte.py?
    # We could try:

    # o = Reg(c)
    # c = ~o

    # Unfortunately we get the following error:
    # UnboundLocalError: local variable 'c' referenced before assignment

    # This is because we have a cycle in the definitions (which do not result in a cycle in the netlist, thanks to REG!)
    # We have to tell carotte.py that c will be defined later. This is done with the Defer class, like this:

    o = Reg(Defer(1, lambda: c)) # 1 is the bus size that c will have
    c = ~o

    o.set_as_output("o")
    c.set_as_output("c")

# Expected output:
# INPUT
# OUTPUT o, c
# VAR o, c
# IN
# o = REG c
# c = NOT o
