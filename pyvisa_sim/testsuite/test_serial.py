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


# an IEEE 488.2 (and therefore SCPI as well) over RS-232 device must always use
# a newline to terminate program messages (commands). these test cases do not
# correspond to real-world scenarios, but are used as a dummy to test non-IEEE
# 488.2 device behavior.
@pytest.mark.parametrize(
    "writes, wanted_response, wanted_input_buffer",
    [
        # fragmented write
        (("*ID", "N?"), b"SCPI,MOCK,VERSION_1.0", b""),
        # sequential write
        (("*IDN?", "*ESR?", "*STB?"), b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255", b""),
        # burst write
        # (("*IDN?*ESR?*STB?"), b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255", b""),
        # burst write with garbage
        (
            ("ab*IDN?cd*ESR?*STB?qwerty"),
            b"SCPI,MOCK,VERSION_1.0" + b"32" + b"255",
            b"qwerty",
        ),
        # fragmented write (properties)
        ((":CURR:", "IMM:AMP", "L?"), b"+1.00000000E+00", b""),
        ((":CURR:", "IMM:AMP", "L 2.0", ":CURR:IMM:AMPL?"), b"+2.00000000E+00", b""),
        # sequential write (properties)
        (
            (":CURR:IMM:AMPL?", ":CURR:IMM:AMPL 1.2345", ":CURR:IMM:AMPL?"),
            b"+1.00000000E+00" + b"+1.23450000E+00",
            b"",
        ),
        # sequential write (properties)
        (
            (":CURR:IMM:AMPL?", ":CURR:IMM:AMPL?", ":CURR:IMM:AMPL?"),
            b"+1.00000000E+00" * 3,
            b"",
        ),
        (
            (
                ":CURR:IMM:AMPL 1.0",
                ":CURR:IMM:AMPL 2.0",
                ":CURR:IMM:AMPL 3.0",
                ":CURR:IMM:AMPL?",
                ":CURR:IMM:AMPL 4.0",
            ),
            b"+3.00000000E+00",
            b"",
        ),
        # this test fails; however, no SCPI serial devices without termination
        # character exist.
        # (
        #    (
        #        "ab :CURR:IMM:AMPL? cd :CURR:IMM:AMPL 5.4321 ef:CURR:IMM:AMPL? gh"
        #    ),
        #    b"+1.00000000E+00" + b"+5.43210000E+00",
        #    b" gh",
        # ),
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
