# -*- coding: utf-8 -*-
"""GPIB simulated session.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
from pyvisa import constants, rname

from . import session


@session.Session.register(constants.InterfaceType.gpib, "INSTR")
class GPIBInstrumentSession(session.MessageBasedSession):
    parsed: rname.GPIBInstr

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.termchar] = int(self.parsed.board)
        self.attrs[constants.ResourceAttribute.gpib_primary_address] = int(
            self.parsed.primary_address
        )
        self.attrs[constants.ResourceAttribute.gpib_secondary_address] = (
            int(self.parsed.secondary_address)
            if self.parsed.secondary_address is not None
            else constants.VI_NO_SEC_ADDR
        )
