#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# carotte.py by Twal, hbens & more

'''Entry point of the carotte.py DSL'''

import argparse
import os
import re
import sys

try:
    if sys.version_info < (3, 13):
        import colored_traceback  # type: ignore
        colored_traceback.add_hook(always=True)
except ModuleNotFoundError:
    print("Warning: Install module 'colored_traceback' for better tracebacks", file=sys.stderr)

try:
    #assignhooks.instrument.debug = True
    #assignhooks.patch.debug = True
    #assignhooks.transformer.debug = True
    import assignhooks  # type: ignore
except ModuleNotFoundError:
    print("Warning: Module 'assignhooks' failed to initialize", file=sys.stderr)
    assignhooks = None # type: ignore

import lib_carotte

MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    print("Python %s.%s or later is required" % MIN_PYTHON, file=sys.stderr) # pylint: disable=C0209
    sys.exit(1)

def process(module_file: str, output_filename: str | None, smart_names: bool,
            smt2_filename: str | None, model_depth: int, prune: bool) -> None:
    '''Process a carotte.py input python file and build its netlist'''
    lib_carotte.reset()
    module_dir, module_name = os.path.split(os.path.abspath(module_file))
    sys.path.append(module_dir)
    module_name = re.sub("\\.py$", "", module_name)
    try:
        module = __import__(module_name)
    except ModuleNotFoundError:
        print(f"Could not load file '{module_file}'", file=sys.stderr)
        sys.exit(1)
    if smart_names and assignhooks is not None:
        assignhooks.patch_module(module) # type: ignore
    module.main() # type: ignore

    netlist = lib_carotte.get_netlist(prune=prune)
    if output_filename is None:
        print(netlist, end='')
    else:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(netlist)

    if smt2_filename is not None:
        model = lib_carotte.get_smtlib2_model(model_depth)
        with open(smt2_filename, 'w', encoding='utf-8') as f:
            f.write(model)

def main() -> None:
    '''Entry point for carotte.py'''
    parser = argparse.ArgumentParser(description='carotte.py DSL')
    parser.add_argument("module_file", nargs=1)
    parser.add_argument('-o', '--output-file', help='Netlist output file')
    parser.add_argument('-s', '--smtlib2-file', help='SMT2 output file')
    parser.add_argument('-d', '--model-depth', help="Depth of the SMT2 model", type=int, default=3)
    parser.add_argument('-p', '--prune', help='Keep only co-accessible variables',
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('--smart-names', help="Smart variable names in the netlist (on by default)",
                        action=argparse.BooleanOptionalAction)
    parser.set_defaults(prune=False)
    parser.set_defaults(smart_names=True)
    args = parser.parse_args()
    process(args.module_file[0], args.output_file, args.smart_names, args.smtlib2_file, args.model_depth, args.prune)

if __name__ == "__main__":
    main()
