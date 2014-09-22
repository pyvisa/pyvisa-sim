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

import sys
import time

from pyvisa import constants

from . import common
from . import sessions


if sys.version >= '3':
    def iter_bytes(data, mask, send_end):
        for d in data[:-1]:
            yield bytes([d & ~mask])

        if send_end:
            yield bytes([data[-1] | ~mask])
        else:
            yield bytes([data[-1] & ~mask])

    int_to_byte = lambda val: bytes([val])
    last_int = lambda val: val[-1]
else:
    def iter_bytes(data, mask, send_end):
        for d in data[:-1]:
            yield chr(ord(d) & ~mask)

        if send_end:
            yield chr(ord(data[-1]) | ~mask)
        else:
            yield chr(ord(data[-1]) & ~mask)

    int_to_byte = chr
    last_int = lambda val: ord(val[-1])


ASRLBREAK = common.NamedObject('ASRLBREAK')


@sessions.Session.register(constants.InterfaceType.asrl, 'INSTR')
class SerialInstrumentSession(sessions.Session):

    def __init__(self, resource_manager_session, resource_name, parsed):
        super(SerialInstrumentSession, self).__init__(resource_manager_session, resource_name, parsed)
        self.buffer = queue.Queue()

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed['board'])

    def read(self, count):

        # TODO: Implement VI_ATTR_SUPPRESS_END_EN
        end_in, _ = self.get_attribute(constants.VI_ATTR_ASRL_END_IN)

        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        end_char = int_to_byte(end_char)

        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)

        last_bit, _ = self.get_attribute(constants.VI_ATTR_ASRL_DATA_BITS)
        mask = 1 << (last_bit - 1)
        now = start = time.time()

        out = b''

        while now - start <= timeout:
            try:
                out += self.buffer.get_nowait()
            except queue.Empty:
                time.sleep(.01)
                continue
            finally:
                now = time.time()

            if end_in == constants.SerialTermination.termination_char:
                if out[-1:] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            elif end_in == constants.SerialTermination.last_bit:

                if last_int(out) & mask:
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
        end_char = int_to_byte(end_char)

        if asrl_end == constants.SerialTermination.last_bit:
            last_bit, _ = self.get_attribute(constants.VI_ATTR_ASRL_DATA_BITS)
            mask = 1 << (last_bit - 1)
            for val in iter_bytes(data, mask, send_end):
                self.buffer.put(val)
        else:

            for i in range(len(data)):
                self.buffer.put(data[i:i+1])

            if asrl_end == constants.SerialTermination.termination_char:
                if send_end:
                    self.buffer.put(end_char)

            elif asrl_end == constants.SerialTermination.termination_break:
                if send_end:
                    self.buffer.put(ASRLBREAK)

            elif not asrl_end == constants.SerialTermination.none:
                raise ValueError('Unknown value for VI_ATTR_ASRL_END_OUT')

