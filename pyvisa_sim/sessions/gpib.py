# -*- coding: utf-8 -*-
"""GPIB simulated session.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import time
from typing import Tuple

from pyvisa import constants, rname

from . import session


@session.Session.register(constants.InterfaceType.gpib, "INSTR")
class GPIBInstrumentSession(session.Session):
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
            # EOM4882
            pass

        return len(data), constants.StatusCode.success
