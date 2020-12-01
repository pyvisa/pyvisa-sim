# -*- coding: utf-8 -*-
import pytest


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
