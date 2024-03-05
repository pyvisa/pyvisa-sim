# -*- coding: utf-8 -*-
"""ASRL (Serial) simulated session class.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import time
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

    def read(self, count: int) -> Tuple[bytes, constants.StatusCode]:
        # TODO: Implement VI_ATTR_SUPPRESS_END_EN
        end_in, _ = self.get_attribute(constants.ResourceAttribute.asrl_end_in)

        end_char, _ = self.get_attribute(constants.ResourceAttribute.termchar)
        end_char = common.int_to_byte(end_char)

        enabled, _ = self.get_attribute(constants.ResourceAttribute.termchar_enabled)
        timeout, _ = self.get_attribute(constants.ResourceAttribute.timeout_value)
        timeout /= 1000

        last_bit, _ = self.get_attribute(constants.ResourceAttribute.asrl_data_bits)
        mask = 1 << (last_bit - 1)
        start = time.monotonic()

        out = b""

        while time.monotonic() - start <= timeout:
            last = self.device.read()

            if not last:
                time.sleep(0.01)
                continue

            out += last

            if end_in == constants.SerialTermination.termination_char:
                if out[-1:] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            elif end_in == constants.SerialTermination.last_bit:
                if common.last_int(out) & mask:
                    return out, constants.StatusCode.success

                if enabled and out[-1:] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            elif end_in == constants.SerialTermination.none:
                if out[-1:] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            else:
                raise ValueError("Unknown value for VI_ATTR_ASRL_END_IN")

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

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
