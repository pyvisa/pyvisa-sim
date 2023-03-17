# -*- coding: utf-8 -*-
"""TCPIP simulated session class.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
from pyvisa import constants, rname

from . import session


class BaseTCPIPSession(session.MessageBasedSession):
    """Base class for TCPIP sessions."""


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
