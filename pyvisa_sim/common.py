# -*- coding: utf-8 -*-
"""Common tools.

This code is currently taken from PyVISA-py.
Do not edit here.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import logging
from typing import Callable, Iterator, Optional, Sequence

from pyvisa import logger

logger = logging.LoggerAdapter(logger, {"backend": "sim"})  # type: ignore


def iter_bytes(
    data: bytes, data_bits: Optional[int] = None, send_end: bool = False
) -> Iterator[bytes]:
    """Clip values to the correct number of bits per byte.

    Serial communication may use from 5 to 8 bits.

    Parameters
    ----------
    data : The data to clip as a byte string.
    data_bits : How many bits per byte should be sent. Clip to this many bits.
        For example: data_bits=5: 0xff (0b1111_1111) --> 0x1f (0b0001_1111)
    send_end : If True, send the final byte unclipped (with all 8 bits).

    References
    ----------
    + https://www.ivifoundation.org/downloads/Architecture%20Specifications/vpp43_2022-05-19.pdf,
    + https://www.ni.com/docs/en-US/bundle/ni-visa/page/ni-visa/vi_attr_asrl_data_bits.html,
    + https://www.ni.com/docs/en-US/bundle/ni-visa/page/ni-visa/vi_attr_asrl_end_out.html
    """
    if send_end and data_bits is None:
        raise ValueError("'send_end' requires a valid 'data_bits' value.")

    if data_bits is None:
        for d in data:
            yield bytes([d])
    else:
        # 2**8     = 0b1000_0000
        # 2**8 - 1 = 0b0111_1111
        mask = 2**data_bits - 1

        for d in data[:-1]:
            yield bytes([d & mask])

        if send_end:
            yield bytes([data[-1]])
        else:
            yield bytes([data[-1] & mask])


int_to_byte: Callable[[int], bytes] = lambda val: bytes([val])
last_int: Callable[[Sequence[int]], int] = lambda val: val[-1]
