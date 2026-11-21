# -*- coding: utf-8 -*-
import shutil
from contextlib import closing
from pathlib import Path

import pytest

import pyvisa


def test_reset_devices_preserves_sessions(tmp_path):
    definition = shutil.copy(Path(__file__).parent / "fixtures/channels.yaml", tmp_path)
    settings = {"read_termination": "\n", "write_termination": "\n"}
    with (
        closing(pyvisa.ResourceManager(f"{definition}@sim")) as channels,
        channels.open_resource("GPIB::8::INSTR", **settings) as first,
        channels.open_resource("GPIB::8::INSTR", **settings) as second,
        channels.open_resource("GPIB::9::INSTR", **settings) as other,
    ):
        first.write("I 2;F 5.0")
        assert second.query("F?") == "5.000"
        other.write("CH 1:VOLT:IMM:AMPL 2.0")

        channels.visalib.reset_devices("GPIB::8::INSTR")
        assert first.query("I?") == "1"
        assert second.query("I 2;F?") == "1.000"
        assert other.query("CH 1:VOLT:IMM:AMPL?") == "+2.00000000E+00"

        channels.visalib.reset_devices()
        assert first.query("I?") == "1"
        assert other.query("CH 1:VOLT:IMM:AMPL?") == "+1.00000000E+00"


def assert_instrument_response(device, query, data):
    response = device.query(query)
    assert response == data, "%s, %r == %r" % (device.resource_name, query, data)


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL1::INSTR",
        "GPIB0::8::INSTR",
        "TCPIP0::localhost:1111::inst0::INSTR",
        "USB0::0x1111::0x2222::0x1234::0::INSTR",
    ],
)
def test_instrument_with_channel_preselection(resource, channels):
    inst = channels.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    assert_instrument_response(inst, "I?", "1")
    assert_instrument_response(inst, "F?", "1.000")

    inst.write("F 5.0")
    assert_instrument_response(inst, "F?", "5.000")
    assert_instrument_response(inst, "I 2;F?", "1.000")

    inst.close()


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL2::INSTR",
        "GPIB0::9::INSTR",
        "TCPIP0::localhost:2222::inst0::INSTR",
        "USB0::0x1111::0x2222::0x2468::0::INSTR",
    ],
)
def test_instrument_with_inline_selection(resource, channels):
    inst = channels.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    assert_instrument_response(inst, "CH 1:VOLT:IMM:AMPL?", "+1.00000000E+00")

    inst.write("CH 1:VOLT:IMM:AMPL 2.0")
    assert_instrument_response(inst, "CH 1:VOLT:IMM:AMPL?", "+2.00000000E+00")
    assert_instrument_response(inst, "CH 2:VOLT:IMM:AMPL?", "+1.00000000E+00")
