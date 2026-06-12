import pytest

from pyvisa_sim import component


@pytest.mark.parametrize(
    "data, want",
    [
        ("abcdefg", b"abcdefg"),
        ("BYTES()", b""),
        ("BYTES())", b")"),
        # "\x29" == ")"
        ("BYTES(\x29\x29)", b"\x29\x29"),
        ("BYTES(\x01)BYTES(\x02)", b"\x01\x02"),
        ("BYTES(\x01\x02\x03\xf0\xe0\xc0)", b"\x01\x02\x03\xf0\xe0\xc0"),
        ("abBYTES(\x01\x02\x03\xf0\xe0\xc0)cd", b"ab\x01\x02\x03\xf0\xe0\xc0cd"),
        ("BYTES(\xaa\x55\x00\x02\x08\x01\xf4)", b"\xaa\x55\x00\x02\x08\x01\xf4"),
    ],
)
def test_bytes_directive(data: str, want: str):
    got = component.to_bytes(data)
    assert got == want
