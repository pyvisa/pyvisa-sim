from typing import List, Optional

import pytest

from pyvisa_sim import common


@pytest.mark.parametrize(
    "data, data_bits, send_end, want",
    [
        (b"\x01", None, False, b"\x01"),
        (b"hello world!", None, False, b"hello world!"),
        # Ensure clipping works as expected
        (b"\x04", 2, False, b"\x00"),  # 0b0100 --> 0b0000
        (b"\x04", 2, True, b"\x04"),  # 0b0100 --> 0b0100
        (b"\x05", 2, False, b"\x01"),  # 0b0101 --> 0b0001
        (b"\xff", 7, False, b"\x7f"),  # 0b1111_1111 --> 0b0111_1111
        (b"\xff", 7, True, b"\xff"),  # 0b1111_1111 --> 0b1111_1111
        # Clipping with 8 or more bits does nothing, as `data` is bytes
        # which is limited to 8 bits per character.
        (b"\xff", 8, False, b"\xff"),
        (b"\xff", 9, False, b"\xff"),
        # Make sure we're iterating correctly
        (b"\x6d\x5c\x25", 4, False, b"\r\x0c\x05"),
        (b"\x6d\x5c\x25", 4, True, b"\r\x0c\x25"),
        (b"`\xa0", 6, False, b"  "),
    ],
)
def test_iter_bytes(
    data: bytes, data_bits: Optional[int], send_end: bool, want: List[bytes]
) -> None:
    got = b"".join(common.iter_bytes(data, data_bits=data_bits, send_end=send_end))
    assert got == want


def test_iter_bytes_with_send_end_requires_data_bits() -> None:
    with pytest.raises(ValueError):
        # Need to wrap in list otherwise the iterator is never called.
        list(common.iter_bytes(b"", data_bits=None, send_end=True))
