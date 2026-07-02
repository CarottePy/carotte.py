# SPDX-License-Identifier: MIT
# Copyright (c) 2021 patgolez10, hbens

from assignhooks.transformer import AssignTransformer # type: ignore
from assignhooks.patch import patch_module # type: ignore
import functools
import os
import traceback
import types
import typing

debug = False


__all__ = ['custom_import', 'start', 'stop']


origin_import = __import__

def _is_in_paths(path: typing.Optional[str], paths: list[str]) -> bool:
    """
    Test if at least on element of `paths` is a prefix of `path`
    """
    if path is None:
        return False
    path = os.path.realpath(path)
    return any(
        os.path.commonpath((path, real_prefix := os.path.realpath(prefix))) == real_prefix
        for prefix in paths
    )


def custom_import(allowed_paths: list[str], name: str, *args: typing.Any, **kwargs: typing.Any) -> types.ModuleType:
    module = origin_import(name, *args, **kwargs)
    if not hasattr(module, '__file__') or not _is_in_paths(module.__file__, allowed_paths) or name == "lib_carotte":
        return module
    try:
        patch_module(module, trans=AssignTransformer)
    except Exception:
        if debug:
            traceback.print_exc()
            print('module %s patch by AssignTransformer failed' % module)
        return module
    return module


def start(allowed_paths: list[str]) -> None:
    __builtins__.update(**dict( # type: ignore
        __import__=functools.partial(custom_import, allowed_paths)
    ))


def stop() -> None:
    __builtins__.update(**dict( # type: ignore
        __import__=origin_import
    ))
