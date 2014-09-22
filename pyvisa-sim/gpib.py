# -*- coding: utf-8 -*-
"""
    pyvisa-sim.gpib
    ~~~~~~~~~~~~~~~

    GPIB simulated session.

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

from . import sessions


@sessions.Session.register(constants.InterfaceType.gpib, 'INSTR')
class GPIBInstrumentSession(sessions.Session):

    def __init__(self, resource_manager_session, resource_name, parsed):
        super(GPIBInstrumentSession, self).__init__(resource_manager_session, resource_name, parsed)
        self.buffer = queue.Queue()

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed['board'])
        self.attrs[constants.VI_ATTR_GPIB_PRIMARY_ADDR] = int(self.parsed['primary_address'])
        self.attrs[constants.VI_ATTR_GPIB_SECONDARY_ADDR] = int(self.parsed['secondary_address'])

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)

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

            if enabled:
                if out[-1] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data):
        send_end = self.get_attribute(constants.VI_ATTR_SEND_END_EN)

        for i in range(len(data)):
            self.buffer.put(data[i:i+1])

        if send_end:
            self.buffer.put(sessions.EOM4882)
