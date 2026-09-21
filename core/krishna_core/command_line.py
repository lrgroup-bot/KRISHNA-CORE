from __future__ import annotations

import ctypes
import os
import shlex
from ctypes import wintypes


def split_command(command, *, empty_message="command is empty"):
    """Split a shell-free command string using the platform's native quoting rules."""
    if not isinstance(command, str):
        args=[str(x) for x in list(command or [])]
        if not args:
            raise ValueError(empty_message)
        return args

    raw=command.strip()
    if not raw:
        raise ValueError(empty_message)
    if os.name!="nt":
        return shlex.split(raw,posix=True)

    argc=ctypes.c_int()
    shell32=ctypes.windll.shell32
    kernel32=ctypes.windll.kernel32
    shell32.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
    shell32.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes=[ctypes.c_void_p]
    kernel32.LocalFree.restype=ctypes.c_void_p
    argv=shell32.CommandLineToArgvW(raw,ctypes.byref(argc))
    if not argv:
        raise ctypes.WinError()
    try:
        return [argv[i] for i in range(argc.value)]
    finally:
        kernel32.LocalFree(ctypes.cast(argv,ctypes.c_void_p))
