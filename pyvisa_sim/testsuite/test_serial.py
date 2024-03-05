# -*- coding: utf-8 -*-
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
