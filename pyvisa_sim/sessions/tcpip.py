# -*- coding: utf-8 -*-
"""TCPIP simulated session class.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import time
from typing import Tuple

from pyvisa import constants, rname

from . import session


class BaseTCPIPSession(session.Session):
    """Base class for TCPIP sessions."""

    def read(self, count: int) -> Tuple[bytes, constants.StatusCode]:
        end_char, _ = self.get_attribute(constants.ResourceAttribute.termchar)
        enabled, _ = self.get_attribute(constants.ResourceAttribute.termchar_enabled)
        timeout, _ = self.get_attribute(constants.ResourceAttribute.timeout_value)
        timeout /= 1000

        start = time.time()

        out = b""

        while time.time() - start <= timeout:
            last = self.device.read()

            if not last:
                time.sleep(0.01)
                continue

            out += last

            if enabled:
                if len(out) > 0 and out[-1] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data: bytes) -> Tuple[int, constants.StatusCode]:
        send_end = self.get_attribute(constants.ResourceAttribute.send_end_enabled)

        for i in range(len(data)):
            self.device.write(data[i : i + 1])

        if send_end:
            # EOM 4882
            pass

        return len(data), constants.StatusCode.success


@session.Session.register(constants.InterfaceType.tcpip, "INSTR")
class TCPIPInstrumentSession(BaseTCPIPSession):

    parsed: rname.TCPIPInstr

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.interface_number] = int(
            self.parsed.board
        )
        self.attrs[constants.ResourceAttribute.tcpip_address] = self.parsed.host_address
        self.attrs[
            constants.ResourceAttribute.tcpip_device_name
        ] = self.parsed.lan_device_name


@session.Session.register(constants.InterfaceType.tcpip, "SOCKET")
class TCPIPSocketSession(BaseTCPIPSession):

    parsed: rname.TCPIPSocket

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.interface_number] = int(
            self.parsed.board
        )
        self.attrs[constants.ResourceAttribute.tcpip_address] = self.parsed.host_address
        self.attrs[constants.ResourceAttribute.tcpip_port] = int(self.parsed.port)
