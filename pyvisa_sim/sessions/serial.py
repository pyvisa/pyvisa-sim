# -*- coding: utf-8 -*-
"""ASRL (Serial) simulated session class.

:copyright: 2014-2024 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""

from typing import Tuple

from pyvisa import constants, rname

from .. import common
from . import session


@session.Session.register(constants.InterfaceType.asrl, "INSTR")
class SerialInstrumentSession(session.MessageBasedSession):
    parsed: rname.ASRLInstr

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.interface_number] = int(
            self.parsed.board
        )

    def write(self, data: bytes) -> Tuple[int, constants.StatusCode]:
        send_end, _ = self.get_attribute(constants.ResourceAttribute.send_end_enabled)
        asrl_end, _ = self.get_attribute(constants.ResourceAttribute.asrl_end_out)
        data_bits, _ = self.get_attribute(constants.ResourceAttribute.asrl_data_bits)

        end_char, _ = self.get_attribute(constants.ResourceAttribute.termchar)
        end_char = common.int_to_byte(end_char)

        len_transferred = len(data)

        if asrl_end == constants.SerialTermination.last_bit:
            val = b"".join(common.iter_bytes(data, data_bits, send_end))
            self.device.write(val)
        else:
            val = b"".join(common.iter_bytes(data, data_bits, send_end=None))
            self.device.write(val)

            if asrl_end == constants.SerialTermination.termination_char:
                if send_end:
                    self.device.write(end_char)
                    len_transferred += 1

            elif asrl_end == constants.SerialTermination.termination_break:
                if send_end:
                    # ASRL Break
                    pass

            elif not asrl_end == constants.SerialTermination.none:
                raise ValueError("Unknown value for VI_ATTR_ASRL_END_OUT")

        return len_transferred, constants.StatusCode.success
