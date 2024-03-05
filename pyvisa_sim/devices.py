# -*- coding: utf-8 -*-
"""Classes to simulate devices.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
from typing import Dict, List, Optional, Tuple, Union

from pyvisa import constants, rname

from .channels import Channels
from .common import logger
from .component import Component, NoResponse, OptionalBytes, to_bytes


class StatusRegister:
    """Class used to mimic a register.

    Parameters
    ----------
    values : values: Dict[str, int]
        Mapping between a name and the associated integer value.
        The name 'q' is reserved and ignored.

    """

    def __init__(self, values: Dict[str, int]) -> None:
        self._value = 0
        self._error_map = {}
        for name, value in values.items():
            if name == "q":
                continue
            self._error_map[name] = int(value)

    def set(self, error_key: str) -> None:
        self._value = self._value | self._error_map[error_key]

    def keys(self) -> List[str]:
        return list(self._error_map.keys())

    @property
    def value(self) -> bytes:
        return to_bytes(str(self._value))

    def clear(self) -> None:
        self._value = 0

    # --- Private API

    #: Mapping between name and integer values.
    _error_map: Dict[str, int]

    #: Current value of the register.
    _value: int


class ErrorQueue:
    """Store error messages in a FIFO queue.

    Parameters
    ----------
    values : values: Dict[str, str]
        Mapping between a name and the associated detailed error message.
        The names 'q', 'default' and 'strict' are reserved.
        'q' and 'strict' are ignored, 'default' is used to set up the default
        response when the queue is empty.

    """

    def __init__(self, values: Dict[str, str]) -> None:
        self._queue: List[bytes] = []
        self._error_map = {}
        for name, value in values.items():
            if name in ("q", "default", "strict"):
                continue
            self._error_map[name] = to_bytes(value)
        self._default = to_bytes(values["default"])

    def append(self, err: str) -> None:
        if err in self._error_map:
            self._queue.append(self._error_map[err])

    @property
    def value(self) -> bytes:
        if self._queue:
            return self._queue.pop(0)
        else:
            return self._default

    def clear(self) -> None:
        self._queue = []

    # --- Private API

    #: Queue of recorded errors
    _queue: List[bytes]

    #: Mapping between short error names and complete error messages
    _error_map: Dict[str, bytes]

    #: Default response when the queue is empty.
    _default: bytes


class Device(Component):
    """A representation of a responsive device

    Parameters
    ----------
    name : str
        The identification name of the device
    delimiter : bytes
        Character delimiting multiple message sent in a single query.

    """

    #: Name of the device.
    name: str

    #: Special character use to delimit multiple messages.
    delimiter: bytes

    def __init__(self, name: str, delimiter: bytes) -> None:
        super(Device, self).__init__()
        self.name = name
        self.delimiter = delimiter
        self._resource_name = None
        self._query_eom = b""
        self._response_eom = b""
        self._channels = {}
        self._error_response = {}
        self._status_registers = {}
        self._error_map = {}
        self._eoms = {}
        self._output_buffer = bytearray()
        self._input_buffer = bytearray()
        self._error_queues = {}

    @property
    def resource_name(self) -> Optional[str]:
        """Assigned resource name"""
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value: str) -> None:
        p = rname.parse_resource_name(value)
        self._resource_name = str(p)
        try:
            self._query_eom, self._response_eom = self._eoms[
                (p.interface_type_const, p.resource_class)
            ]
        except KeyError:
            logger.warning(
                "No eom provided for %s, %s."
                "Using LF." % (p.interface_type_const, p.resource_class)
            )
            self._query_eom, self._response_eom = b"\n", b"\n"

    def add_channels(self, ch_name: str, ch_obj: Channels) -> None:
        """Add a channel definition."""
        self._channels[ch_name] = ch_obj

    # FIXME use a TypedDict
    def add_error_handler(self, error_input: Union[dict, str]):
        """Add error handler to the device"""

        if isinstance(error_input, dict):
            error_response = error_input.get("response", {})
            cerr = error_response.get("command_error", NoResponse)
            qerr = error_response.get("query_error", NoResponse)

            response_dict = {"command_error": cerr, "query_error": qerr}

            register_list = error_input.get("status_register", [])

            for register_dict in register_list:
                query = register_dict["q"]
                register = StatusRegister(register_dict)
                self._status_registers[to_bytes(query)] = register
                for key in register.keys():
                    self._error_map[key] = register

            queue_list = error_input.get("error_queue", [])

            for queue_dict in queue_list:
                query = queue_dict["q"]
                err_queue = ErrorQueue(queue_dict)
                self._error_queues[to_bytes(query)] = err_queue

        else:
            response_dict = {"command_error": error_input, "query_error": error_input}

        for key, value in response_dict.items():
            self._error_response[key] = to_bytes(value)

    def error_response(self, error_key: str) -> Optional[bytes]:
        """Uupdate all error queues and return an error message if it exists."""
        if error_key in self._error_map:
            self._error_map[error_key].set(error_key)

        for q in self._error_queues.values():
            q.append(error_key)

        return self._error_response.get(error_key)

    def add_eom(
        self, type_class: str, query_termination: str, response_termination: str
    ) -> None:
        """Add default end of message for a given interface type and resource class.

        Parameters
        ----------
        type_class : str
            Interface type and resource class as strings joined by space
        query_termination : str
            End of message used in queries.
        response_termination : str
            End of message used in responses.

        """
        i_t, resource_class = type_class.split(" ")
        interface_type = getattr(constants.InterfaceType, i_t.lower())
        self._eoms[(interface_type, resource_class)] = (
            to_bytes(query_termination),
            to_bytes(response_termination),
        )

    def write(self, data: bytes) -> None:
        """Write data into the device input buffer."""
        logger.debug("Writing into device input buffer: %r" % data)
        if not isinstance(data, bytes):
            raise TypeError("data must be an instance of bytes")

        self._input_buffer.extend(data)

        le = len(self._query_eom)
        if not self._input_buffer.endswith(self._query_eom):
            return

        try:
            message = bytes(self._input_buffer[:-le])
            queries = message.split(self.delimiter) if self.delimiter else [message]
            for query in queries:
                response = self._match(query)
                eom = self._response_eom

                if response is None:
                    response = self.error_response("command_error")
                    assert response is not None

                if response is not NoResponse:
                    self._output_buffer.extend(response)
                    self._output_buffer.extend(eom)

        finally:
            self._input_buffer = bytearray()

    def read(self) -> bytes:
        """Return a single byte from the output buffer"""
        if self._output_buffer:
            b, self._output_buffer = (self._output_buffer[0:1], self._output_buffer[1:])
            return b

        return b""

    # --- Private API

    #: Resource name this device is bound to. Set when adding the device to Devices
    _resource_name: Optional[str]

    # Default end of message used in query operations
    _query_eom: bytes

    # Default end of message used in response operations
    _response_eom: bytes

    #: Mapping between a name and a Channels object
    _channels: Dict[str, Channels]

    #: Stores the error response for each query accepted by the device.
    _error_response: Dict[str, bytes]

    #: Stores the registers by name.
    #: Register name -> Register object
    _status_registers: Dict[bytes, StatusRegister]

    #: Mapping between error and register affected by the error.
    _error_map: Dict[str, StatusRegister]

    #: Stores the specific end of messages for device.
    #: TYPE CLASS -> (query termination, response termination)
    _eoms: Dict[Tuple[constants.InterfaceType, str], Tuple[bytes, bytes]]

    #: Buffer in which the user can read
    _output_buffer: bytearray

    #: Buffer in which the user can write
    _input_buffer: bytearray

    #: Mapping an error queue query and the queue.
    _error_queues: Dict[bytes, ErrorQueue]

    def _match(self, query: bytes) -> Optional[OptionalBytes]:
        """Tries to match in dialogues, getters and setters and channels."""
        response: Optional[OptionalBytes]
        response = self._match_dialog(query)
        if response is not None:
            return response

        response = self._match_getters(query)
        if response is not None:
            return response

        response = self._match_registers(query)
        if response is not None:
            return response

        response = self._match_errors_queues(query)
        if response is not None:
            return response

        response = self._match_setters(query)
        if response is not None:
            return response

        if response is None:
            for channel in self._channels.values():
                response = channel.match(query)
                if response:
                    return response

        return None

    def _match_registers(self, query: bytes) -> Optional[bytes]:
        """Tries to match in status registers."""
        if query in self._status_registers:
            register = self._status_registers[query]
            response = register.value
            logger.debug("Found response in status register: %s", repr(response))
            register.clear()

            return response

        return None

    def _match_errors_queues(self, query: bytes) -> Optional[bytes]:
        """Tries to match in error queues."""
        if query in self._error_queues:
            queue = self._error_queues[query]
            response = queue.value
            logger.debug("Found response in error queue: %s", repr(response))

            return response

        return None


class Devices:
    """The group of connected devices."""

    def __init__(self) -> None:
        self._internal = {}

    def add_device(self, resource_name: str, device: Device) -> None:
        """Bind device to resource name"""

        if device.resource_name is not None:
            msg = "The device %r is already assigned to %s"
            raise ValueError(msg % (device, device.resource_name))

        device.resource_name = resource_name

        self._internal[device.resource_name] = device

    def __getitem__(self, item: str) -> Device:
        return self._internal[item]

    def list_resources(self) -> Tuple[str, ...]:
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())

    # --- Private API

    #: Resource name to device map.
    _internal: Dict[str, Device]
