import pytest

from pyvisa_sim import component


@pytest.mark.parametrize(
    "data, want",
    [
        ("abcdefg", b"abcdefg"),
        ("BYTES()", b"BYTES()"),
        ("BYTES(4c)", b"\x4c"),
        ("BYTES(01)BYTES(02)", b"\x01\x02"),
        ("abBYTES(cd)ef", b"ab\xcdef"),
    ],
)
def test_bytes_directive(data: str, want: str):
    got = component.to_bytes(data)
    assert got == want
