# -*- coding: utf-8 -*-
import collections

import pyvisa
import pyvisa.attributes
import pyvisa.constants
from pyvisa_sim.sessions import serial

serial.SerialInstrumentSession


def test_serial_nonsupported_vi_attr(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL1::INSTR", read_termination="\n", write_termination="\r\n"
    )
    visa_library = instr.visalib
    session_handle = instr.session
    session = visa_library.sessions[session_handle]

    old_key = pyvisa.constants.ResourceAttribute.asrl_avalaible_number
    old_value = pyvisa.attributes.AttributesByID[old_key]

    del pyvisa.attributes.AttributesByID[old_key]

    assert session.get_attribute(
        pyvisa.constants.ResourceAttribute.asrl_avalaible_number
    ) == (0, pyvisa.constants.StatusCode.error_nonsupported_attribute)

    pyvisa.attributes.AttributesByID[old_key] = old_value

    old_resources = pyvisa.attributes.AttrVI_ATTR_ASRL_AVAIL_NUM.resources
    pyvisa.attributes.AttrVI_ATTR_ASRL_AVAIL_NUM.resources = []
    assert session.get_attribute(
        pyvisa.constants.ResourceAttribute.asrl_avalaible_number
    ) == (0, pyvisa.constants.StatusCode.error_nonsupported_attribute)
    pyvisa.attributes.AttrVI_ATTR_ASRL_AVAIL_NUM.resources = old_resources

    session.device._input_buffer = bytearray()
    session.device._output_buffers.clear()


def test_serial_bytes_in_buffer(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )
    visa_library = instr.visalib
    session_handle = instr.session
    session = visa_library.sessions[session_handle]

    instr.write("*IDN?")
    instr.write(":VOLT:IMM:AMPL?")
    assert instr.bytes_in_buffer == len(f"SCPI,MOCK,VERSION_1.0\n{1.0:+.8E}\n")

    session.device._input_buffer = bytearray()
    session.device._output_buffers.clear()


def test_serial_flush(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )
    visa_library = instr.visalib
    session_handle = instr.session
    session = visa_library.sessions[session_handle]

    instr.write("*IDN?")
    assert session.device._output_buffers != collections.deque()

    instr.flush(pyvisa.constants.BufferOperation.discard_receive_buffer)
    assert session.device._output_buffers == collections.deque()

    session.device._input_buffer = bytearray()
    session.device._output_buffers.clear()


def test_serial_write_with_termination_last_bit(resource_manager):
    instr = resource_manager.open_resource(
        "ASRL4::INSTR",
        read_termination="\n",
        write_termination="\r\n",
    )
    visa_library = instr.visalib
    session_handle = instr.session
    session = visa_library.sessions[session_handle]

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

    session.device._input_buffer = bytearray()
    session.device._output_buffers.clear()
