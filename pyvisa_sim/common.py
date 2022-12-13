# -*- coding: utf-8 -*-
"""Common tools.

This code is currently taken from PyVISA-py.
Do not edit here.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import logging
from typing import Callable, Optional, Sequence

from pyvisa import logger

logger = logging.LoggerAdapter(logger, {"backend": "sim"})  # type: ignore


def iter_bytes(data: bytes, mask: Optional[int] = None, send_end: bool = False):
    if send_end and mask is None:
        raise ValueError("send_end requires a valid mask.")

    if mask is None:
        for d in data:
            yield bytes([d])

    else:
        for d in data[:-1]:
            yield bytes([d & ~mask])

        if send_end:
            yield bytes([data[-1] | ~mask])
        else:
            yield bytes([data[-1] & ~mask])


int_to_byte: Callable[[int], bytes] = lambda val: bytes([val])
last_int: Callable[[Sequence[int]], int] = lambda val: val[-1]
