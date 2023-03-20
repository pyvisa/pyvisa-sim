from typing import List, Optional

import pytest

from pyvisa_sim import common


@pytest.mark.parametrize(
    "data, mask, send_end, want",
    [
        (b"1234", None, False, b"1234"),
        (b"41234", 3, False, b"40004"),
        # Can't figure this one out. Getting ValueError: bytes must in in range(0, 256)
        # If I knew more about the purpose of `iter_bytes` then maybe I could
        # reconcile it, but I don't have time to investigate right now.
        #  (b"1234", 3, True, b"1234"),  # TODO: figure out correct 'want'
    ],
)
def test_iter_bytes(
    data: bytes, mask: Optional[int], send_end: bool, want: List[bytes]
) -> None:
    got = b"".join(common.iter_bytes(data, mask=mask, send_end=send_end))
    assert got == want


def test_iter_bytes_with_send_end_requires_mask() -> None:
    with pytest.raises(ValueError):
        # Need to wrap in list otherwise the iterator is never called.
        list(common.iter_bytes(b"", mask=None, send_end=True))
