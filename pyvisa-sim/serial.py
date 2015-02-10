# -*- coding: utf-8 -*-
"""
    pyvisa-sim.serial
    ~~~~~~~~~~~~~~~~~

    ASRL (Serial) simulated session class.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

from __future__ import division, unicode_literals, print_function, absolute_import

try:
    import Queue as queue
except ImportError:
    import queue

import time

from pyvisa import constants

from . import common
from . import sessions


@sessions.Session.register(constants.InterfaceType.asrl, 'INSTR')
class SerialInstrumentSession(sessions.Session):

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed['board'])

    def read(self, count):

        # TODO: Implement VI_ATTR_SUPPRESS_END_EN
        end_in, _ = self.get_attribute(constants.VI_ATTR_ASRL_END_IN)

        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        end_char = common.int_to_byte(end_char)

        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)

        last_bit, _ = self.get_attribute(constants.VI_ATTR_ASRL_DATA_BITS)
        mask = 1 << (last_bit - 1)
        now = start = time.time()

        out = b''

        while now - start <= timeout:
            try:
                out += self.device.read()
            except queue.Empty:
                time.sleep(.01)
                continue
            finally:
                now = time.time()

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
                raise ValueError('Unknown value for VI_ATTR_ASRL_END_IN')

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data):
        send_end, _ = self.get_attribute(constants.VI_ATTR_SEND_END_EN)
        asrl_end, _ = self.get_attribute(constants.VI_ATTR_ASRL_END_OUT)

        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        end_char = common.int_to_byte(end_char)

        if asrl_end == constants.SerialTermination.last_bit:
            last_bit, _ = self.get_attribute(constants.VI_ATTR_ASRL_DATA_BITS)
            mask = 1 << (last_bit - 1)
            for val in common.iter_bytes(data, mask, send_end):
                self.device.write(val)
        else:

            for i in range(len(data)):
                self.device.write(data[i:i+1])

            if asrl_end == constants.SerialTermination.termination_char:
                if send_end:
                    self.device.write(end_char)

            elif asrl_end == constants.SerialTermination.termination_break:
                if send_end:
                    # ASRL Break
                    pass

            elif not asrl_end == constants.SerialTermination.none:
                raise ValueError('Unknown value for VI_ATTR_ASRL_END_OUT')

