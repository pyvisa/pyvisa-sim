"""Regression coverage for non-UTF-8 bytes in instrument dialogues."""

import pytest

import pyvisa
from pyvisa_sim.channels import Channels
from pyvisa_sim.component import Component
from pyvisa_sim.devices import Device


@pytest.mark.parametrize(
    "response, expected",
    [
        ("BYTES(\xaa\x55\x00\x02\x08\x01\xf4)", b"\xaa\x55\x00\x02\x08\x01\xf4"),
        ("\u6e2c\u5b9a", "\u6e2c\u5b9a".encode("utf-8")),
        ("BYTES(\xff){RANDOM(1, 1, 1):.0f}", b"\xff1"),
    ],
)
def test_dialogue_preserves_binary_and_utf8_responses(response, expected):
    device = Device("binary instrument", b"")
    device.add_dialogue("BYTES(\xaa\x55\x00\x02\x08\x01\xf4)", response)
    assert device._match(b"\xaa\x55\x00\x02\x08\x01\xf4") == expected


@pytest.mark.parametrize("channel", [False, True])
def test_binary_query_does_not_match_text_setter(channel):
    device = Device("binary instrument", b"")
    target = Channels(device, ["1"], True) if channel else Component()
    target.add_property("value", "0", None, ("SET {:d}", "OK", "ERROR"), {})
    assert target._match_setters(b"\xff") is None
    assert target._match_setters(b"SET 1") == b"OK"


@pytest.mark.parametrize("direct", [False, True])
def test_binary_query_reaches_channel_dialogue(direct):
    device = Device("binary instrument", b"")
    channel = Channels(device, ["1"], True)
    channel.add_dialogue("CH {ch_id}:BYTES(\xff)", "BYTES(\xaa)")
    device.add_channels("output", channel)
    match = channel.match if direct else device._match
    assert match(b"CH 1:\xff") == b"\xaa"


def test_binary_query_reaches_later_channel_group():
    device = Device("binary instrument", b"")
    first = Channels(device, ["1"], True)
    first.add_dialogue("FIRST {ch_id}:?", "OK")
    device.add_channels("first", first)
    second = Channels(device, ["1"], True)
    second.add_dialogue("CH {ch_id}:BYTES(\xff)", "BYTES(\xaa)")
    device.add_channels("second", second)
    assert device._match(b"CH 1:\xff") == b"\xaa"


def test_unknown_binary_command_uses_error_response():
    device = Device("binary instrument", b"")
    device.add_eom("TCPIP INSTR", "\n", "\n")
    device.resource_name = "TCPIP0::localhost::INSTR"
    device.add_error_handler("ERROR")
    device.write(b"\xff\n")
    expected = b"ERROR\n"
    response = bytearray()
    for _ in range(len(expected)):
        value, end = device.read()
        response.extend(value)
        if end:
            break
    else:
        pytest.fail("Error response did not end within the expected byte count")
    assert bytes(response) == expected


@pytest.mark.parametrize("resource", ["ASRL1::INSTR", "TCPIP0::localhost::INSTR"])
def test_binary_dialogue_through_pyvisa(tmp_path, resource):
    definition = tmp_path / "binary.yaml"
    definition.write_text(
        r"""spec: "1.0"
devices:
  binary:
    eom:
      ASRL INSTR: {q: "\n", r: "\n"}
      TCPIP INSTR: {q: "\n", r: "\n"}
    error: ERROR
    dialogues:
      - q: "BYTES(\xaa\x55\x00\x02\x08\x01\xf4)"
        r: "BYTES(\xaa\x55\x00\x02\x08\x01\xf4)"
resources:
  ASRL1::INSTR: {device: binary}
  TCPIP0::localhost::INSTR: {device: binary}
""",
        encoding="utf-8",
    )
    packet = b"\xaa\x55\x00\x02\x08\x01\xf4\n"
    manager = pyvisa.ResourceManager(str(definition) + "@sim")
    try:
        with manager.open_resource(resource, timeout=500) as instrument:
            instrument.write_raw(packet)
            assert instrument.read_raw() == packet
    finally:
        manager.close()
