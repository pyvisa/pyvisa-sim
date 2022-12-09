# -*- coding: utf-8 -*-
"""USB simulated session class.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import time

from pyvisa import constants

from . import sessions


@sessions.Session.register(constants.InterfaceType.usb, "INSTR")
class USBInstrumentSession(sessions.Session):
    def __init__(self, resource_manager_session, resource_name, parsed):
        super(USBInstrumentSession, self).__init__(
            resource_manager_session, resource_name, parsed
        )

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_MANF_ID] = self.parsed.manufacturer_id
        self.attrs[constants.VI_ATTR_MODEL_CODE] = self.parsed.model_code
        self.attrs[constants.VI_ATTR_USB_SERIAL_NUM] = self.parsed.serial_number
        self.attrs[constants.VI_ATTR_USB_INTFC_NUM] = int(self.parsed.board)

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)
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

    def write(self, data):
        send_end = self.get_attribute(constants.VI_ATTR_SEND_END_EN)

        for i in range(len(data)):
            self.device.write(data[i : i + 1])

        if send_end:
            # EOM 4882
            pass

        return len(data), constants.StatusCode.success


@sessions.Session.register(constants.InterfaceType.usb, "RAW")
class USBRawSession(sessions.Session):
    def __init__(self, resource_manager_session, resource_name, parsed):
        super(USBRawSession, self).__init__(
            resource_manager_session, resource_name, parsed
        )

    def after_parsing(self):
        self.attrs[constants.VI_ATTR_INTF_NUM] = int(self.parsed.board)
        self.attrs[constants.VI_ATTR_MANF_ID] = self.parsed.manufacturer_id
        self.attrs[constants.VI_ATTR_MODEL_CODE] = self.parsed.model_code
        self.attrs[constants.VI_ATTR_USB_SERIAL_NUM] = self.parsed.serial_number
        self.attrs[constants.VI_ATTR_USB_INTFC_NUM] = int(self.parsed.board)

    def read(self, count):
        end_char, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR)
        enabled, _ = self.get_attribute(constants.VI_ATTR_TERMCHAR_EN)
        timeout, _ = self.get_attribute(constants.VI_ATTR_TMO_VALUE)
        timeout /= 1000

        now = start = time.time()

        out = b""

        while now - start <= timeout:
            last = self.device.read()

            if not last:
                time.sleep(0.01)
                now = time.time()
                continue

            out += last

            if enabled:
                if len(out) > 0 and out[-1] == end_char:
                    return out, constants.StatusCode.success_termination_character_read

            if len(out) == count:
                return out, constants.StatusCode.success_max_count_read
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data):
        send_end = self.get_attribute(constants.VI_ATTR_SEND_END_EN)

        for i in range(len(data)):
            self.device.write(data[i : i + 1])

        if send_end:
            # EOM 4882
            pass

        return len(data), constants.StatusCode.success
