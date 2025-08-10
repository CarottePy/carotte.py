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

def process(module_file: str, output_filename: str | None, smart_names: bool) -> None:
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

    netlist = lib_carotte.get_netlist()
    if output_filename is None:
        print(netlist, end='')
    else:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(netlist)

def main() -> None:
    '''Entry point for carotte.py'''
    parser = argparse.ArgumentParser(description='carotte.py DSL')
    parser.add_argument("module_file", nargs=1)
    parser.add_argument('-o', '--output-file', help='Netlist output file')
    parser.add_argument('--smart-names', help="Smart variable names in the netlist (on by default)",
                        action=argparse.BooleanOptionalAction)
    parser.set_defaults(smart_names=True)
    args = parser.parse_args()
    process(args.module_file[0], args.output_file, args.smart_names)

if __name__ == "__main__":
    main()
