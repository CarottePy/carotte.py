# SPDX-License-Identifier: MIT
# Copyright (c) 2021 patgolez10, hbens

# type: ignore

from assignhooks.transformer import AssignTransformer
from assignhooks.patch import patch_module
import traceback

debug = False


__all__ = ['custom_import', 'start', 'stop']


origin_import = __import__


def custom_import(name, *args, **kwargs):
    module = origin_import(name, *args, **kwargs)
    if not hasattr(module, '__file__'):
        return module
    try:
        patch_module(module, trans=AssignTransformer)
    except Exception:
        if debug:
            traceback.print_exc()
            print('module %s patch by AssignTransformer failed' % module)
        return module
    return module


def start():
    __builtins__.update(**dict(
        __import__=custom_import
    ))


def stop():
    __builtins__.update(**dict(
        __import__=origin_import
    ))
