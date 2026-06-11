# -*- coding: utf-8 -*-
import pytest

import pyvisa
from pyvisa_sim.sessions import serial

serial.SerialInstrumentSession


def test_serial_write_with_termination_last_bit(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )

    # Ensure that we test the `asrl_end` block of serial.SerialInstrumentSession.write
    instr.set_visa_attribute(
        pyvisa.constants.ResourceAttribute.asrl_end_out,
        pyvisa.constants.SerialTermination.last_bit,
    )

    instr.set_visa_attribute(
        pyvisa.constants.ResourceAttribute.send_end_enabled,
        pyvisa.constants.VI_FALSE,
    )

    instr.write("*IDN?")
    assert instr.read() == "SCPI,MOCK,VERSION_1.0"


@pytest.mark.parametrize(
    "writes, wanted_response, wanted_input_buffer",
    [
        # fragmented write
        (("*ID", "N?"), b"SCPI,MOCK,VERSION_1.0", b""),
        # sequential write
        (("*IDN?", "*ESR?", "*STB?"), b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255", b""),
        # burst write
        (("*IDN?*ESR?*STB?"), b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255", b""),
        # burst write with garbage
        (
            ("ab*IDN?cd*ESR?*STB?qwerty"),
            b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255",
            b"qwerty",
        ),
    ],
)
def test_serial_write_no_termination(
    no_termination_chars_resource_manager, writes, wanted_response, wanted_input_buffer
):
    instr = no_termination_chars_resource_manager.open_resource(
        "ASRL1::INSTR",
        write_termination=None,
        read_termination=None,
        end_input=pyvisa.constants.SerialTermination.none,
        end_output=pyvisa.constants.SerialTermination.none,
        send_end=False,
    )
    visa_library = instr.visalib
    session_handle = instr.session
    session = visa_library.sessions[session_handle]
    device = session.device
    for write in writes:
        instr.write(write)
    assert instr.read_bytes(len(wanted_response)) == wanted_response
    assert device._input_buffer == wanted_input_buffer
    device._input_buffer = bytearray()
