# -*- coding: utf-8 -*-
"""
    pyvisa-sim.tcpip
    ~~~~~~~~~~~~~~~~

    TCPIP simulated session class.

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


@sessions.Session.register(constants.InterfaceType.tcpip, 'INSTR')
class TCPIPInstrumentSession(sessions.Session):

    def __init__(self, resource_manager_session, resource_name, parsed):
        super(TCPIPInstrumentSession, self).__init__(resource_manager_session, resource_name, parsed)

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed['board'])
        self.attrs[constants.VI_ATTR_TCPIP_ADDR] = self.parsed['host_address']
        self.attrs[constants.VI_ATTR_TCPIP_DEVICE_NAME] = self.parsed['lan_device_name']

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)

        now = start = time.time()

        out = b''

        while now - start <= timeout:
            try:
                last = self.device.read()
            except queue.Empty:
                time.sleep(.01)
                continue
            finally:
                now = time.time()

            out += last

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
            self.device.write(data[i:i+1])

        if send_end:
            # EOM 4882
            pass

