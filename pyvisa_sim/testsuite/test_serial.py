# -*- coding: utf-8 -*-
import pytest

import pyvisa
import pyvisa.constants
from pyvisa_sim.sessions import serial

serial.SerialInstrumentSession


@pytest.mark.dependency()
def test_serial_flush(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )
    instr.write("*IDN?")
    assert instr.bytes_in_buffer != 0

    instr.flush(pyvisa.constants.BufferOperation.discard_read_buffer_no_io)
    assert instr.bytes_in_buffer == 0


@pytest.mark.dependency(depends=["test_serial_flush"])
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

    instr.flush(pyvisa.constants.BufferOperation.discard_read_buffer_no_io)


@pytest.mark.dependency(depends=["test_serial_flush"])
def test_serial_bytes_in_buffer(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )
    instr.write("*IDN?")
    instr.write(":VOLT:IMM:AMPL?")
    assert instr.bytes_in_buffer == len(f"SCPI,MOCK,VERSION_1.0\n{1.0:+.8E}\n")

    instr.flush(pyvisa.constants.BufferOperation.discard_read_buffer_no_io)
