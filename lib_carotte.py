# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

'''Carotte library internals'''

import sys
import typing


class FakeColorama:
    '''We define here empty variables for when the colorama package is not available'''
    def __init__(self, depth: int = 0):
        if depth < 1:
            self.Fore = FakeColorama(depth+1)
            self.Fore.YELLOW = '' # type: ignore
            self.Style = FakeColorama(depth+1)
            self.Style.RESET_ALL = '' # type: ignore

try:
    import colorama  # type: ignore
except ModuleNotFoundError:
    print("Warning: Install module 'colorama' for colored errors", file=sys.stderr)
    colorama = FakeColorama() # type: ignore

_equation_counter = 0
_input_list: typing.List['Variable'] = []
_equation_list: typing.List['Variable'] = []
_assertion_list: typing.List['Verif.Assert'] = []
_output_list = []
_name_set = set()
_unevaluated_defer_set = set()
_ALLOW_RIBBON_LOGIC_OPERATIONS = False

def allow_ribbon_logic_operations(enable : bool) -> None:
    '''Enable or disable ribbon logic operations'''
    global _ALLOW_RIBBON_LOGIC_OPERATIONS # pylint: disable=W0603
    _ALLOW_RIBBON_LOGIC_OPERATIONS = enable

def get_and_increment_equation_counter() -> int:
    '''Return the current global equation counter, and increment it'''
    global _equation_counter # pylint: disable=W0603
    old_value = _equation_counter
    _equation_counter += 1
    return old_value

class Variable(typing.Sequence['Variable']):
    '''The basis of carotte.py: netlist variables core'''
    def __init__(self, name: str, bus_size: int, autogen_name: bool, in_netlist: bool):
        assert name not in _name_set
        assert not(in_netlist) or bus_size >= 0
        self._validate_name(name)
        _name_set.add(name)
        self.name = name
        self.autogen_name = autogen_name
        self.bus_size = bus_size
        self.in_netlist = in_netlist # Verification variable are abstract and not wanted in the netlist
    def set_as_output(self, name: typing.Optional[str] = None) -> None:
        '''Sets this variable as a netlist OUTPUT'''
        if not self.in_netlist:
            raise ValueError(f"Cannot set '{name}' as output, as it is an abstract variable.")
        if name is not None:
            self.rename(name)
        _output_list.append(self)
    def get_full_name(self) -> str:
        '''Returns the full name of this variable for the VARIABLE part of the netlist'''
        if self.bus_size == 1:
            return self.name
        return f"{self.name}:{self.bus_size}"

    def _generate_name(self, prefix:str) -> str:
        while True:
            name = prefix + str(get_and_increment_equation_counter())
            if name not in _name_set:
                return name

    def _validate_name(self, name: str) -> None:
        if " " in name:
            raise ValueError("Spaces in variable names are not allowed. Have '{name}'.")
        if "@" in name:
            # Used in STMLIB2 output for previous values in registers
            raise ValueError("'@' in variable names are not allowed. Have '{name}'.")

    def rename(self, new_name: str, autogen_name: bool = False) -> None:
        '''Rename the variable; can fail'''
        if self.name != new_name:
            if new_name in _name_set:
                raise ValueError(f"Rename failed: the variable name '{new_name}' is already used!")
            self._validate_name(new_name)
            _name_set.remove(self.name)
            _name_set.add(new_name)
            self.name = new_name
            self.autogen_name = autogen_name

    def try_rename(self, new_name: str, autogen_name: bool = False) -> bool:
        '''Rename the variable if the new name is available and deemed better than the old one'''
        if not self.autogen_name and autogen_name:
            return False
        try:
            self.rename(new_name, autogen_name)
        except ValueError:
            return False
        return True

    def get_smt2_decl(self, model_depth: int) -> str:
        '''Returns the variable declaration in SMTLIB2 format'''
        return "".join(f"(declare-const {"@"*i}{self.name} (_ BitVec {self.bus_size}))\n" for i in range(model_depth))
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        '''Returns the variable declaration in SMTLIB2 format'''
        raise ValueError("Should be specialized by sub-classes")

    def __assignpre__(self, lhs_name: str, rhs_name: str, rhs: typing.Any) -> typing.Any:
        '''Magic hook for better variables names'''
        if False: # pylint: disable=W0125
            print(f'{colorama.Fore.YELLOW}PRE: assigning {lhs_name} = {rhs_name}  ||| var: {rhs.get_full_name()}')
        return rhs

    def __assignpost__(self, lhs_name: str, rhs_name: str) -> None:
        '''Magic hook for better variables names'''
        if False: # pylint: disable=W0125
            print(f'POST: assigning {lhs_name} = {rhs_name}  ||| var{self.autogen_name}: {self.get_full_name()}')
        if self.autogen_name and (lhs_name is not None):
            new_name = lhs_name
            if new_name in _name_set:
                new_name = '_' + lhs_name + '_' + str(get_and_increment_equation_counter())
            self.try_rename(new_name)

    def __and__(self, rhs: 'Variable') -> 'Variable':
        return And(self, rhs)
    def __or__(self, rhs: 'Variable') -> 'Variable':
        return Or(self, rhs)
    def __xor__(self, rhs: 'Variable') -> 'Variable':
        return Xor(self, rhs)
    def __invert__(self) -> 'Variable':
        return Not(self)
    def __len__(self) -> int:
        return self.bus_size
    def __getitem__(self, index: typing.Union[int, slice]) -> 'Variable':
        if isinstance(index, slice):
            if (index.step is not None) and (index.step != 1):
                raise TypeError(f"Slices must use a step of '1' (have {index.step})")
            start = 0 if index.start is None else index.start
            stop = self.bus_size if index.stop is None else index.stop
            return Slice(start, stop, self)
        if isinstance(index, int):
            return Select(index, self)
        raise TypeError(f"Invalid getitem, index: {index} is neither a slice or an integer")
    def __add__(self, rhs: 'Variable') -> 'Variable':
        return Concat(self, rhs)

class Defer:
    '''For handling loops in variable declarations'''
    def __init__(self, bus_size: int, lazy_val: typing.Callable[[], Variable], in_netlist: bool = True):
        self.val: typing.Optional[Variable] = None
        self.lazy_val = lazy_val
        self.bus_size = bus_size
        self.autogen_name = True
        self.in_netlist = in_netlist
        _unevaluated_defer_set.add(self)
    def get_val(self) -> Variable:
        '''Helper to resolve the variable value once the loop issue has been solved'''
        if self.val is None:
            _unevaluated_defer_set.remove(self)
            self.val = self.lazy_val()
            assert self.val.bus_size == self.bus_size
        return self.val
    @property
    def name(self) -> str:
        '''We want to compute the variable name lazily'''
        return self.get_val().name

VariableOrDefer = typing.Union[Variable, Defer]

def _smt2_name(x: VariableOrDefer | str, depth: int) -> str:
    if not isinstance(x, str):
        x = x.name
    return f"{"@"*depth}{x}"

def _smt2_BV2Bool(x: VariableOrDefer, depth: int) -> str:
    assert x.bus_size == 1
    return f"(ite (= {_smt2_name(x, depth)} #b0) false true)"

class Input(Variable):
    '''A netlist variable of type INPUT'''
    def __init__(self, bus_size: int, name: typing.Optional[str] = None):
        autogen_name = False
        if name is None:
            name = "_input_" + str(get_and_increment_equation_counter())
            autogen_name = True
        if name in _name_set:
            raise ValueError(f"The variable name '{name}' is already used!")
        super().__init__(name, bus_size, autogen_name = autogen_name, in_netlist = True)
        _input_list.append(self)
    def __str__(self) -> str:
        return self.name
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        return "" # Arbitrary value; no constraint

class EquationVariable(Variable):
    '''A standard netlist variable'''
    def __init__(self, bus_size: int, in_netlist: bool):
        name = self._generate_name("_l_" )
        super().__init__(name, bus_size, autogen_name = True, in_netlist = in_netlist)
        _equation_list.append(self)

class Constant(EquationVariable):
    '''Netlist constant'''
    def __init__(self, value: str):
        if len(value) == 0:
            raise ValueError("Defining an empty constant is not allowed")
        for x in value:
            if x not in "01tf":
                raise ValueError(f"The character {x} of the constant {value} is not allowed"
                    + " (it should either be 0, 1, t or f)")
        super().__init__(len(value), in_netlist = True)
        self.value = value
    def __str__(self) -> str:
        return f"{self.name} = {self.value}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        value_cleaned = self.value.replace("t","1").replace("f","0")
        return f"(assert (= {_smt2_name(self, depth)} #b{value_cleaned}))\n"

class Unop(EquationVariable):
    '''Netlist unary operations on variables'''
    unop_name = ""
    upop_name_smtlib2 = ""
    def __init__(self, x: VariableOrDefer):
        if not _ALLOW_RIBBON_LOGIC_OPERATIONS and x.bus_size != 1:
            raise ValueError(f"Unops can only be performed on signals of bus size 1 (have {x.bus_size}). "
                             + "If your simulator handles ribbons logic operations, "
                             + "call `allow_ribbon_logic_operations(True)`")
        super().__init__(x.bus_size, in_netlist = x.in_netlist)
        self.x = x
    def __str__(self) -> str:
        if self.unop_name == "":
            raise ValueError("Invalid unop name")
        return f"{self.name} = {self.unop_name} {self.x.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        if self.unop_name == "REG":
            if depth >= max_depth:
                return ""
            return f"(assert (= {_smt2_name(self, depth)} {_smt2_name(self.x, depth+1)}))\n"
        if self.upop_name_smtlib2 == "":
            raise ValueError("Invalid unnop name for SMTLIB2")
        return f"(assert (= {_smt2_name(self, depth)} ({self.upop_name_smtlib2} {_smt2_name(self.x, depth)})))\n"

class Not(Unop):
    '''Netlist NOT'''
    unop_name = "NOT"
    upop_name_smtlib2 = "bvnot"

class Reg(Unop):
    '''Netlist REG'''
    unop_name = "REG"

class Binop(EquationVariable):
    '''Netlist binary operations on variables'''
    binop_name = ""
    binop_name_smtlib2 = ""
    def __init__(self, lhs: VariableOrDefer, rhs: VariableOrDefer):
        if lhs.bus_size != rhs.bus_size:
            raise ValueError(f"Operands have different bus sizes: {lhs.bus_size} and {rhs.bus_size}")
        if not _ALLOW_RIBBON_LOGIC_OPERATIONS and lhs.bus_size != 1:
            raise ValueError(f"Binops can only be performed on signals of bus size 1 (have {lhs.bus_size}). "
                             + "If your simulator handles ribbons logic operations, "
                             + "call `allow_ribbon_logic_operations(True)`")
        super().__init__(lhs.bus_size, in_netlist = (lhs.in_netlist and rhs.in_netlist))
        self.lhs = lhs
        self.rhs = rhs
    def __str__(self) -> str:
        if self.binop_name == "":
            raise ValueError("Invalid binop name")
        return f"{self.name} = {self.binop_name} {self.lhs.name} {self.rhs.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        if self.binop_name_smtlib2 == "":
            raise ValueError("Invalid binop name for SMTLIB2")
        right = f"({self.binop_name_smtlib2} {_smt2_name(self.lhs, depth)} {_smt2_name(self.rhs, depth)})"
        return f"(assert (= {_smt2_name(self, depth)} {right}))\n"

class And(Binop):
    '''Netlist AND'''
    binop_name = "AND"
    binop_name_smtlib2 = "bvand"
class Nand(Binop):
    '''Netlist NAND'''
    binop_name = "NAND"
    binop_name_smtlib2 = "bvnand"
class Or(Binop):
    '''Netlist OR'''
    binop_name = "OR"
    binop_name_smtlib2 = "bvor"
class Xor(Binop):
    '''Netlist XOR'''
    binop_name = "XOR"
    binop_name_smtlib2 = "bvxor"

class Mux(EquationVariable):
    '''Netlist MUX'''
    def __init__(self, choice: VariableOrDefer, a: VariableOrDefer, b: VariableOrDefer):
        if choice.bus_size != 1:
            raise ValueError(f"MUX choice bus size must be 1, have {choice.bus_size}")
        if a.bus_size != b.bus_size:
            raise ValueError(f"MUX sides must have the same bus size, have {a.bus_size} and {b.bus_size}")
        self.choice = choice
        self.a = a
        self.b = b
        super().__init__(a.bus_size, in_netlist = (choice.in_netlist and a.in_netlist and b.in_netlist))
    def __str__(self) -> str:
        return f"{self.name} = MUX {self.choice.name} {self.a.name} {self.b.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        right = f"(ite (= {self.choice} #b0) {_smt2_name(self.a, depth)} {_smt2_name(self.b, depth)})"
        return f"(assert (= {_smt2_name(self, depth)} {right}))\n"

class ROM(EquationVariable):
    '''Netlist ROM'''
    def __init__(self, addr_size: int, word_size: int, read_addr: VariableOrDefer):
        if read_addr.bus_size != addr_size:
            raise ValueError(f"ROM read address bus size ({read_addr.bus_size}) must be equal "
                + "to addr_size ({addr_size})")
        self.addr_size = addr_size
        self.word_size = word_size
        self.read_addr = read_addr
        self.verif_rom_name = self._generate_name("_ROM_")
        _name_set.add(self.verif_rom_name)
        super().__init__(word_size, in_netlist = read_addr.in_netlist)
    def __str__(self) -> str:
        return f"{self.name} = ROM {self.addr_size} {self.word_size} {self.read_addr.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        r = f"(declare-const {self.verif_rom_name} (Array (_ BitVec {self.addr_size}) (_ BitVec {self.word_size})))\n"
        d = f"(assert (= {_smt2_name(self, depth)} (select {self.verif_rom_name} {_smt2_name(self.read_addr, depth)})))"
        return f"{(r if depth == 0 else "")}{d}\n"

class RAM(EquationVariable):
    '''Netlist RAM'''
    def __init__(self, addr_size: int, word_size: int, read_addr: VariableOrDefer,
                 write_enable: VariableOrDefer, write_addr: VariableOrDefer, write_data: VariableOrDefer):
        if read_addr.bus_size != addr_size:
            raise ValueError(f"RAM read address bus size ({read_addr.bus_size}) must be equal "
                + "to addr_size ({addr_size})")
        if write_enable.bus_size != 1:
            raise ValueError(f"RAM write_enable bus size must be equal to 1, have {write_enable.bus_size}")
        if write_addr.bus_size != addr_size:
            raise ValueError(f"RAM write address bus size ({write_addr.bus_size}) must be equal "
                + "to addr_size ({addr_size})")
        if write_data.bus_size != word_size:
            raise ValueError(f"RAM write data bus size ({write_data.bus_size}) must be equal "
                + "to word_size ({word_size})")
        self.addr_size = addr_size
        self.word_size = word_size
        self.read_addr = read_addr
        self.write_enable = write_enable
        self.write_addr = write_addr
        self.write_data = write_data
        self.verif_ram_name = self._generate_name("_RAM_")
        in_netlist = (
            read_addr.in_netlist and write_enable.in_netlist and write_addr.in_netlist and write_data.in_netlist
        )
        super().__init__(word_size, in_netlist=in_netlist)
    def __str__(self) -> str:
        return (f"{self.name} = RAM {self.addr_size} {self.word_size} {self.read_addr.name} " +
                f"{self.write_enable.name} {self.write_addr.name} {self.write_data.name}")
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        now_ram = f"{_smt2_name(self.verif_ram_name, depth)}"
        decl_ram = f"(declare-const {now_ram} (Array (_ BitVec {self.addr_size}) (_ BitVec {self.word_size})))\n"

        if depth < max_depth:
            pre_ram = f"{_smt2_name(self.verif_ram_name, depth+1)}"
            read = f"(assert (= {_smt2_name(self, depth)} (select {pre_ram} {_smt2_name(self.read_addr, depth)})))"
            write = (
                f"(assert (= {now_ram} (ite {_smt2_BV2Bool(self.write_enable, depth)}"
                f" (store {pre_ram} {_smt2_name(self.write_addr, depth)} {_smt2_name(self.write_data, depth)})"
                f" {pre_ram}"
                ")))"
            )
        else:
            read = ""
            write = (
                f"(assert (ite {_smt2_BV2Bool(self.write_enable, depth)}"
                f"(= {_smt2_name(self.write_data, depth)} (select {now_ram} {_smt2_name(self.write_addr, depth)})) true"
                "))"
            )

        return f"{decl_ram}{read}{write}"

class Concat(EquationVariable):
    '''Netlist CONCAT'''
    def __init__(self, lhs: VariableOrDefer, rhs: VariableOrDefer):
        super().__init__(lhs.bus_size + rhs.bus_size, in_netlist = (lhs.in_netlist and rhs.in_netlist))
        self.lhs = lhs
        self.rhs = rhs
    def __str__(self) -> str:
        return f"{self.name} = CONCAT {self.lhs.name} {self.rhs.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        right = f"(concat {_smt2_name(self.rhs, depth)} {_smt2_name(self.lhs, depth)})"
        return f"(assert (= {_smt2_name(self, depth)} {right}))\n"

class Slice(EquationVariable):
    '''Netlist SLICE'''
    def __init__(self, i1: int, i2: int, x: VariableOrDefer):
        if not 0 <= i1 < i2 <= x.bus_size:
            raise IndexError(f"Slice must satisfy `0 <= i1 < i2 <= bus_size`, i.e. {0} <= {i1} < {i2} <= {x.bus_size}")
        super().__init__(i2-i1, in_netlist = x.in_netlist)
        self.i1 = i1
        self.i2 = i2-1
        self.x = x
        if not x.autogen_name and '_slc_' not in x.name:
            self.try_rename(('' if x.name.startswith('_') else '_') + x.name + '_slc_' +
                            str(self.i1) + '_' + str(self.i2), True)
    def __str__(self) -> str:
        return f"{self.name} = SLICE {self.i1} {self.i2} {self.x.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        return f"(assert (= {_smt2_name(self, depth)} ((_ extract {self.i2} {self.i1}) {_smt2_name(self.x, depth)})))\n"

class Select(EquationVariable):
    '''Netlist SELECT'''
    def __init__(self, i: int, x: VariableOrDefer):
        if not 0 <= i < x.bus_size:
            raise IndexError(f"Select must satisfy `0 <= i < bus_size`, i.e. {0} <= {i} < {x.bus_size}")
        super().__init__(1, in_netlist = x.in_netlist)
        self.i = i
        self.x = x
        if not x.autogen_name:
            self.try_rename(('' if x.name.startswith('_') else '_') + x.name + '_sel_' + str(i), True)
    def __str__(self) -> str:
        return f"{self.name} = SELECT {self.i} {self.x.name}"
    def get_smt2_equation(self, depth: int, max_depth: int) -> str:
        return f"(assert (= {_smt2_name(self, depth)} ((_ extract {self.i} {self.i}) {_smt2_name(self.x, depth)})))\n"

class Verif:
    '''Functions related to verification variables, which have no meaning in terms of netlist.'''

    class _VerifVariable(Variable):
        '''A variable used solely for verification purposes. Allows high-level operations.'''
        def __str__(self) -> str:
            raise ValueError(f"VerifVariable {self.name} should not be put in the netlist")
        def __init__(self, bus_size: int):
            # bus_size == -1 means this is a mathematical integer
            name = self._generate_name("_v_" )
            super().__init__(name, bus_size, autogen_name = True, in_netlist = False)
            _equation_list.append(self)

    class _Unop(_VerifVariable):
        '''SMTLIB2 unary operations on bit-vectors'''
        unop_name_smtlib2 = ""
        def __init__(self, x: VariableOrDefer):
            super().__init__(x.bus_size)
            self.x = x

        def get_smt2_equation(self, depth: int, max_depth: int) -> str:
            if self.unop_name_smtlib2 == "":
                raise ValueError("Invalid unnop name for SMTLIB2")
            if self.unop_name_smtlib2 == "PRE":
                if depth >= max_depth:
                    return ""
                return f"(assert (= {_smt2_name(self, depth)} {_smt2_name(self.x, depth+1)}))\n"
            return f"(assert (= {_smt2_name(self, depth)} ({self.unop_name_smtlib2} {_smt2_name(self.x, depth)})))\n"

    class BVNot(_Unop):
        '''SMTLIB2 bit-vector NOT'''
        unop_name_smtlib2 = "bvnot"
    class BVNeg(_Unop):
        '''SMTLIB2 bit-vector NEG'''
        unop_name_smtlib2 = "bvnet"
    class Pre(_Unop):
        '''Value from the previous clock-cycle'''
        unop_name_smtlib2 = "PRE"

    class _Binop(_VerifVariable):
        '''SMTLIB2 binary operations on bit-vectors'''
        binop_name_smtlib2 = ""
        def __init__(self, lhs: VariableOrDefer, rhs: VariableOrDefer):
            if lhs.bus_size != rhs.bus_size:
                raise ValueError(f"Operands have different bus sizes: {lhs.bus_size} and {rhs.bus_size}")
            if self.binop_name_smtlib2 == "=>":
                if lhs.bus_size != 1:
                    raise ValueError(
                        f"Implication parameters must be boolean-like. '{lhs.name}' has bus size {lhs.bus_size}."
                    )
            match self.binop_name_smtlib2:
                case "=" | "<" | "<=" | ">" | ">=" | "=>":
                    new_size = 1
                    self.recast_bool_to_bitvec = True
                case _:
                    new_size = lhs.bus_size
                    self.recast_bool_to_bitvec = False
            super().__init__(new_size)
            self.lhs = lhs
            self.rhs = rhs
        def get_smt2_equation(self, depth: int, max_depth: int) -> str:
            if self.binop_name_smtlib2 == "":
                raise ValueError("Invalid binop name for SMTLIB2")
            if self.recast_bool_to_bitvec:
                lhs, rhs = self.lhs.name, self.rhs.name
                if self.binop_name_smtlib2 == "=>":
                    lhs, rhs = _smt2_BV2Bool(self.lhs, depth), _smt2_BV2Bool(self.rhs, depth)
                cond = f"({self.binop_name_smtlib2} {lhs} {rhs})"
                return f"(assert (= {_smt2_name(self, depth)} (ite {cond} #b1 #b0)))\n"
            right = f"({self.binop_name_smtlib2} {_smt2_name(self.lhs, depth)} {_smt2_name(self.rhs, depth)})"
            return f"(assert (= {_smt2_name(self, depth)} {right}))\n"

    class BVOr(_Binop):
        '''SMTLIB2 bit-vector OR'''
        binop_name_smtlib2 = "bvor"
    class BVAnd(_Binop):
        '''SMTLIB2 bit-vector AND'''
        binop_name_smtlib2 = "bvand"
    class BVXor(_Binop):
        '''SMTLIB2 bit-vector XOR'''
        binop_name_smtlib2 = "bvxor"
    class BVNor(_Binop):
        '''SMTLIB2 bit-vector NOR'''
        binop_name_smtlib2 = "bvnor"
    class BVNand(_Binop):
        '''SMTLIB2 bit-vector NAND'''
        binop_name_smtlib2 = "bvnand"
    class BVXnor(_Binop):
        '''SMTLIB2 bit-vector XNOR'''
        binop_name_smtlib2 = "bvxnor"

    class BVAdd(_Binop):
        '''SMTLIB2 bit-vector ADD'''
        binop_name_smtlib2 = "bvadd"
    class BVSub(_Binop):
        '''SMTLIB2 bit-vector SUB'''
        binop_name_smtlib2 = "bvsub"
    class BVMul(_Binop):
        '''SMTLIB2 bit-vector MUL'''
        binop_name_smtlib2 = "bvmul"
    class BVShl(_Binop):
        '''SMTLIB2 bit-vector SHL'''
        binop_name_smtlib2 = "bvshl"
    class BVLShr(_Binop):
        '''SMTLIB2 bit-vector LSHR'''
        binop_name_smtlib2 = "bvlshr"
    class BVAShr(_Binop):
        '''SMTLIB2 bit-vector ASHR'''
        binop_name_smtlib2 = "bvashr"

    class BVUle(_Binop):
        '''SMTLIB2 bit-vector unsigned less or equal'''
        binop_name_smtlib2 = "bvule"
    class BVUlt(_Binop):
        '''SMTLIB2 bit-vector unsigned less'''
        binop_name_smtlib2 = "bvult"
    class BVUge(_Binop):
        '''SMTLIB2 bit-vector unsigned greater or equal'''
        binop_name_smtlib2 = "bvuge"
    class BVUgt(_Binop):
        '''SMTLIB2 bit-vector unsigned greater'''
        binop_name_smtlib2 = "bvugt"
    class BVSle(_Binop):
        '''SMTLIB2 bit-vector signed less or equal'''
        binop_name_smtlib2 = "bvsle"
    class BVSlt(_Binop):
        '''SMTLIB2 bit-vector signed less'''
        binop_name_smtlib2 = "bvslt"
    class BVSge(_Binop):
        '''SMTLIB2 bit-vector signed greater or equal'''
        binop_name_smtlib2 = "bvsge"
    class BVSgt(_Binop):
        '''SMTLIB2 bit-vector signed greater'''
        binop_name_smtlib2 = "bvsgt"

    class Equal(_Binop):
        '''SMTLIB2 Equality'''
        binop_name_smtlib2 = "="
    class Lesser(_Binop):
        '''SMTLIB2 integer <'''
        binop_name_smtlib2 = "<"
    class LesserOrEqual(_Binop):
        '''SMTLIB2 integer <='''
        binop_name_smtlib2 = "<="
    class Greater(_Binop):
        '''SMTLIB2 integer >'''
        binop_name_smtlib2 = ">"
    class GreaterOrEqual(_Binop):
        '''SMTLIB2 integer >='''
        binop_name_smtlib2 = ">="
    class Imply(_Binop):
        '''SMTLIB2 Implication'''
        binop_name_smtlib2 = "=>"

    class BVZeroExtend(_VerifVariable):
        '''SMTLIB2 zero-extension on bit-vectors'''
        def __init__(self, x: VariableOrDefer, target_width: int):
            if target_width < x.bus_size:
                raise ValueError(f"Cannot extend variable '{x.name}' of size {x.bus_size} to size {target_width}")
            if x.bus_size < 1:
                raise ValueError(f"Operand '{x.name}' must be a bit-vector variable.")
            super().__init__(target_width)
            self.x = x
            self.extend = target_width - x.bus_size
        def get_smt2_equation(self, depth: int, max_depth: int) -> str:
            right = f"((_ zero_extend {self.extend}) {_smt2_name(self.x, depth)})"
            return f"(assert (= {_smt2_name(self, depth)} {right}))\n"

    class BV2Int(_VerifVariable):
        '''SMTLIB2 bit-vector bit-vector to integer'''
        def __init__(self, x: VariableOrDefer):
            if x.bus_size < 1:
                raise ValueError(f"Operand '{x.name}' must be a bit-vector variable.")
            super().__init__(bus_size=-1)
            self.x = x
        def get_smt2_equation(self, depth: int, max_depth: int) -> str:
            return f"(assert (= {_smt2_name(self, depth)} (bv2int {_smt2_name(self.x, depth)})))\n"

    class Int2BV(_VerifVariable):
        '''SMTLIB2 bit-vector bit-vector to integer'''
        def __init__(self, bus_size: int, x: VariableOrDefer):
            if x.bus_size != -1:
                raise ValueError(f"Operand '{x.name}' must be an integer variable.")
            super().__init__(bus_size)
            self.x = x
        def get_smt2_equation(self, depth: int, max_depth: int) -> str:
            return f"(assert (= {_smt2_name(self, depth)} ((_ int2bv {self.bus_size}) {_smt2_name(self.x, depth)})))\n"

    class Assert:
        '''SMTLIB2 assertions'''
        def __init__(self, x: VariableOrDefer):
            if x.bus_size != 1:
                raise ValueError(f"Assertion variable must be boolean-like. '{x.name}' has bus size {x.bus_size}.")
            self.x = x
            _assertion_list.append(self)
        def get_smt2_assertion(self) -> str:
            '''Returns the assertion in SMTLIB2 format'''
            return (
                "(push)\n"
                + f"(assert (= {self.x.name} #b0)) ; Should fail.\n"
                "(check-sat)\n"
                ";(get-model)\n"
                "(pop)\n"
            )

    @staticmethod
    def AssertEqual(lhs: VariableOrDefer, rhs: VariableOrDefer) -> Assert:
        '''Syntaxic sugar for Assert(Equal(a,b))'''
        return Verif.Assert(Verif.Equal(lhs, rhs))
    @staticmethod
    def _assert_sugar_op(lhs: VariableOrDefer, rhs: VariableOrDefer, signed: bool,
                         fun_int: type[_Binop], fun_svb: type[_Binop], fun_ubv: type[_Binop]) -> Assert:
        if lhs.bus_size == -1:
            if signed:
                raise ValueError("'signed' parameted is only valid for bit-vector variables")
            return Verif.Assert(fun_int(lhs, rhs))
        if signed:
            return Verif.Assert(fun_svb(lhs, rhs))
        return Verif.Assert(fun_ubv(lhs, rhs))
    @staticmethod
    def AssertLesser(lhs: VariableOrDefer, rhs: VariableOrDefer, signed: bool = False) -> Assert:
        '''Syntaxic sugar for Assert(Lesser/BVSlt/BVUlt(a,b))'''
        return Verif._assert_sugar_op(lhs, rhs, signed, Verif.Lesser, Verif.BVSlt, Verif.BVUlt)
    @staticmethod
    def AssertLesserEqual(lhs: VariableOrDefer, rhs: VariableOrDefer, signed: bool = False) -> Assert:
        '''Syntaxic sugar for Assert(LesserOrEqual/BVSle/BVUle(a,b))'''
        return Verif._assert_sugar_op(lhs, rhs, signed, Verif.LesserOrEqual, Verif.BVSle, Verif.BVUle)
    @staticmethod
    def AssertGreater(lhs: VariableOrDefer, rhs: VariableOrDefer, signed: bool = False) -> Assert:
        '''Syntaxic sugar for Assert(Greater/BVSgt/BVUgt(a,b))'''
        return Verif._assert_sugar_op(lhs, rhs, signed, Verif.Greater, Verif.BVSgt, Verif.BVUgt)
    @staticmethod
    def AssertGreaterEqual(lhs: VariableOrDefer, rhs: VariableOrDefer, signed: bool = False) -> Assert:
        '''Syntaxic sugar for Assert(GreaterOrEqual/BVSge/BVUge(a,b))'''
        return Verif._assert_sugar_op(lhs, rhs, signed, Verif.GreaterOrEqual, Verif.BVSge, Verif.BVUge)

def _undefer() -> None:
    '''Handle defered nodes'''
    # The equations might contain Defer nodes that are not yet evaluated,
    # and their evaluation could create new equations.
    # This loop evaluates all Defer nodes (and subsequent Defer nodes that could
    # be created by the evaluation of the previous ones)
    while len(_unevaluated_defer_set) != 0:
        for defer in list(_unevaluated_defer_set):
            defer.get_val()

def get_netlist() -> str:
    '''Get the netlist in string form'''

    _undefer()

    old_lens = (len(_input_list), len(_output_list), len(_equation_list))

    netlist = (
        ""
        + "INPUT " + ", ".join(x.name for x in _input_list) + "\n"
        + "OUTPUT " + ", ".join(x.name for x in _output_list) + "\n"
        + "VAR " + ", ".join(x.get_full_name() for x in _input_list + _equation_list if x.in_netlist) + "\n"
        + "IN" + "\n"
        + "".join(str(x) + "\n" for x in _equation_list if x.in_netlist)
    )

    # Sanity check
    new_lens = (len(_input_list), len(_output_list), len(_equation_list))
    if new_lens != old_lens:
        raise RuntimeError("Internal error: inconsistent lengths, please report a bug")

    return netlist

def get_smtlib2_model(model_depth: int) -> str:
    '''Get the netlist in smtlib2 form.
    The depth corresponds to the number of consecutive clock-cycles put in the model.'''

    _undefer()
    model = (
        "; Netlist model\n"
        + "".join(x.get_smt2_decl(model_depth) for x in _input_list + _equation_list)
        + "".join("".join(x.get_smt2_equation(i, model_depth-1) for x in _equation_list) for i in range(model_depth))
        + "(check-sat) ; Should never fail. The netlist itself should be well-formed.\n"
        + ("; User assertions\n" if len(_assertion_list) > 0 else "")
        + "".join(x.get_smt2_assertion() for x in _assertion_list)
    )

    return model

def reset() -> None:
    '''Reset the netlist'''
    global _equation_counter, _input_list, _equation_list # pylint: disable=W0603
    global _assertion_list, _output_list, _name_set # pylint: disable=W0603
    _equation_counter = 0
    _input_list = []
    _equation_list = []
    _assertion_list = []
    _output_list = []
    _name_set = set()
