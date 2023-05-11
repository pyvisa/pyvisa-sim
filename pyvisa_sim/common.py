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


def _create_bitmask(bits: int) -> int:
    """Create a bitmask for the given number of bits."""
    mask = (1 << bits) - 1
    return mask


def iter_bytes(
    data: bytes, data_bits: Optional[int] = None, send_end: Optional[bool] = False
) -> Iterator[bytes]:
    """Clip values to the correct number of bits per byte.

    Serial communication may use from 5 to 8 bits.

    Parameters
    ----------
    data : The data to clip as a byte string.
    data_bits : How many bits per byte should be sent. Clip to this many bits.
        For example: data_bits=5: 0xff (0b1111_1111) --> 0x1f (0b0001_1111).
        Values above 8 will be clipped to 8.
    send_end : If True, send the final byte with the highest bit of data_bits
        set to 1. If False, send the final byte with the highest bit of data_bits
        set to 0. If None, do not adjust the higest bit of data_bits (only
        apply the mask defined by data_bits).

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
        if data_bits <= 0:
            raise ValueError("'data_bits' cannot be zero or negative")
        if data_bits > 8:
            data_bits = 8

        mask = _create_bitmask(data_bits)

        # Send everything but the last byte with the mask applied.
        for d in data[:-1]:
            yield bytes([d & mask])

        last_byte = data[-1]

        # Send the last byte adjusted by `send_end`
        if send_end is None:
            # only apply the mask
            yield bytes([last_byte & mask])
        elif bool(send_end) is True:
            # apply the mask and set highest of data_bits to 1
            highest_bit = 1 << (data_bits - 1)
            yield bytes([(last_byte & mask) | highest_bit])
        elif bool(send_end) is False:
            # apply the mask and set highest of data_bits to 0
            # This is effectively the same has reducing the mask by 1 bit.
            new_mask = _create_bitmask(data_bits - 1)
            yield bytes([last_byte & new_mask])
        else:
            raise ValueError(f"Unknown 'send_end' value '{send_end}'")


int_to_byte: Callable[[int], bytes] = lambda val: bytes([val])
last_int: Callable[[Sequence[int]], int] = lambda val: val[-1]
