# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

'''Simple ROM example'''

from lib_carotte import *


def main() -> None:
    '''Entry point of this example'''
    addr_size = 2
    word_size = 4
    read_addr = Input(addr_size)
    o: Variable = ROM(addr_size, word_size, read_addr)
    o.set_as_output("o")
    Verif.Assert(Verif.Imply(Verif.Equal(read_addr, Verif.Pre(read_addr)),
                             Verif.Equal(o, Verif.Pre(o))))
