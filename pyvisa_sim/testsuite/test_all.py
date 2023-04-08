# -*- coding: utf-8 -*-
import logging

import pytest
from pyvisa.errors import VisaIOError


def assert_instrument_response(device, query, data):
    response = device.query(query)
    assert response == data, "%s, %r == %r" % (device.resource_name, query, data)


def test_list(resource_manager):
    assert set(resource_manager.list_resources("?*")) == {
        "ASRL1::INSTR",
        "ASRL2::INSTR",
        "ASRL3::INSTR",
        "ASRL4::INSTR",
        "TCPIP0::localhost::inst0::INSTR",
        "TCPIP0::localhost::10001::SOCKET",
        "TCPIP0::localhost:2222::inst0::INSTR",
        "TCPIP0::localhost:3333::inst0::INSTR",
        "TCPIP0::localhost:4444::inst0::INSTR",
        "USB0::0x1111::0x2222::0x1234::0::INSTR",
        "USB0::0x1111::0x2222::0x2468::0::INSTR",
        "USB0::0x1111::0x2222::0x3692::0::INSTR",
        "USB0::0x1111::0x2222::0x4444::0::INSTR",
        "USB0::0x1111::0x2222::0x4445::0::RAW",
        "GPIB0::4::INSTR",
        "GPIB0::8::INSTR",
        "GPIB0::9::INSTR",
        "GPIB0::10::INSTR",
    }


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL1::INSTR",
        "GPIB0::8::INSTR",
        "TCPIP0::localhost::inst0::INSTR",
        "TCPIP0::localhost::10001::SOCKET",
        "USB0::0x1111::0x2222::0x1234::0::INSTR",
        "USB0::0x1111::0x2222::0x4445::0::RAW",
    ],
)
def test_instruments(resource, resource_manager):
    inst = resource_manager.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    assert_instrument_response(inst, "?IDN", "LSG Serial #1234")

    assert_instrument_response(inst, "?FREQ", "100.00")
    assert_instrument_response(inst, "!FREQ 10.3", "OK")
    assert_instrument_response(inst, "?FREQ", "10.30")

    assert_instrument_response(inst, "?AMP", "1.00")
    assert_instrument_response(inst, "!AMP 3.8", "OK")
    assert_instrument_response(inst, "?AMP", "3.80")

    assert_instrument_response(inst, "?OFF", "0.00")
    assert_instrument_response(inst, "!OFF 1.2", "OK")
    assert_instrument_response(inst, "?OFF", "1.20")

    assert_instrument_response(inst, "?OUT", "0")
    assert_instrument_response(inst, "!OUT 1", "OK")
    assert_instrument_response(inst, "?OUT", "1")

    assert_instrument_response(inst, "?WVF", "0")
    assert_instrument_response(inst, "!WVF 1", "OK")
    assert_instrument_response(inst, "?WVF", "1")

    assert_instrument_response(inst, "!CAL", "OK")

    # Errors

    assert_instrument_response(inst, "!WVF 23", "ERROR")
    assert_instrument_response(inst, "!AMP -1.0", "ERROR")
    assert_instrument_response(inst, "!AMP 11.0", "ERROR")
    assert_instrument_response(inst, "!FREQ 0.0", "FREQ_ERROR")
    assert_instrument_response(inst, "BOGUS_COMMAND", "ERROR")

    inst.close()


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL3::INSTR",
        "GPIB0::10::INSTR",
        "TCPIP0::localhost:3333::inst0::INSTR",
        "USB0::0x1111::0x2222::0x3692::0::INSTR",
    ],
)
def test_instruments_on_invalid_command(resource, resource_manager):
    inst = resource_manager.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    response = inst.query("FAKE_COMMAND")
    assert response == "INVALID_COMMAND", "invalid command test - response"

    status_reg = inst.query("*ESR?")
    assert int(status_reg) == 32, "invalid command test - status"


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL2::INSTR",
        "GPIB0::9::INSTR",
        "TCPIP0::localhost:2222::inst0::INSTR",
        "USB0::0x1111::0x2222::0x2468::0::INSTR",
    ],
)
def test_instrument_on_invalid_values(resource, resource_manager):
    inst = resource_manager.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    inst.write("FAKE_COMMAND")
    status_reg = inst.query("*ESR?")
    assert int(status_reg) == 32, "invalid test command"

    inst.write(":VOLT:IMM:AMPL 2.00")
    status_reg = inst.query("*ESR?")
    assert int(status_reg) == 0

    inst.write(":VOLT:IMM:AMPL 0.5")
    status_reg = inst.query("*ESR?")
    assert int(status_reg) == 32, "invalid range test - <min"

    inst.write(":VOLT:IMM:AMPL 6.5")
    status_reg = inst.query("*ESR?")
    assert int(status_reg) == 32, "invalid range test - >max"


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL3::INSTR",
        "GPIB0::10::INSTR",
        "TCPIP0::localhost:3333::inst0::INSTR",
        "USB0::0x1111::0x2222::0x3692::0::INSTR",
    ],
)
def test_instruments_with_timeouts(resource, resource_manager):
    inst = resource_manager.open_resource(resource, timeout=0.1)

    with pytest.raises(VisaIOError):
        inst.read()


@pytest.mark.parametrize(
    "resource",
    [
        "ASRL4::INSTR",
        "GPIB0::4::INSTR",
        "TCPIP0::localhost:4444::inst0::INSTR",
        "USB0::0x1111::0x2222::0x4444::0::INSTR",
    ],
)
def test_instrument_for_error_state(resource, resource_manager):
    inst = resource_manager.open_resource(
        resource,
        read_termination="\n",
        write_termination="\r\n" if resource.startswith("ASRL") else "\n",
    )

    assert_instrument_response(inst, ":SYST:ERR?", "0, No Error")

    inst.write("FAKE COMMAND")
    assert_instrument_response(inst, ":SYST:ERR?", "1, Command error")

    inst.write(":VOLT:IMM:AMPL 0")
    assert_instrument_response(inst, ":SYST:ERR?", "1, Command error")


def test_device_write_logging(caplog, resource_manager) -> None:
    instr = resource_manager.open_resource(
        "USB0::0x1111::0x2222::0x4444::0::INSTR",
        read_termination="\n",
        write_termination="\n",
    )

    with caplog.at_level(logging.DEBUG):
        instr.write("*IDN?")
        instr.read()

    assert "input buffer: b'D'" not in caplog.text
    assert r"input buffer: b'*IDN?\n'" in caplog.text
