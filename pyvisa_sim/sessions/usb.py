# -*- coding: utf-8 -*-
"""USB simulated session class.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import time
from typing import Tuple

from pyvisa import constants, rname

from . import session


@session.Session.register(constants.InterfaceType.usb, "INSTR")
class USBInstrumentSession(session.Session):
    parsed: rname.USBInstr

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.interface_number] = int(
            self.parsed.board
        )
        self.attrs[
            constants.ResourceAttribute.manufacturer_id
        ] = self.parsed.manufacturer_id
        self.attrs[constants.ResourceAttribute.model_code] = self.parsed.model_code
        self.attrs[
            constants.ResourceAttribute.usb_serial_number
        ] = self.parsed.serial_number
        self.attrs[constants.ResourceAttribute.usb_interface_number] = int(
            self.parsed.board
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
            # EOM 4882
            pass

        return len(data), constants.StatusCode.success


@session.Session.register(constants.InterfaceType.usb, "RAW")
class USBRawSession(session.Session):
    parsed: rname.USBRaw

    def after_parsing(self) -> None:
        self.attrs[constants.ResourceAttribute.interface_number] = int(
            self.parsed.board
        )
        self.attrs[
            constants.ResourceAttribute.manufacturer_id
        ] = self.parsed.manufacturer_id
        self.attrs[constants.ResourceAttribute.model_code] = self.parsed.model_code
        self.attrs[
            constants.ResourceAttribute.usb_serial_number
        ] = self.parsed.serial_number
        self.attrs[constants.ResourceAttribute.usb_interface_number] = int(
            self.parsed.board
        )

    def read(self, count: int) -> Tuple[bytes, constants.StatusCode]:
        end_char, _ = self.get_attribute(constants.ResourceAttribute.termchar)
        enabled, _ = self.get_attribute(constants.ResourceAttribute.termchar_enabled)
        timeout, _ = self.get_attribute(constants.ResourceAttribute.timeout_value)
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

    def write(self, data: bytes) -> Tuple[int, constants.StatusCode]:
        send_end = self.get_attribute(constants.ResourceAttribute.send_end_enabled)

        for i in range(len(data)):
            self.device.write(data[i : i + 1])

        if send_end:
            # EOM 4882
            pass

        return len(data), constants.StatusCode.success
