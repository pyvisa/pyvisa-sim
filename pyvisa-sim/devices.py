# -*- coding: utf-8 -*-
"""
    pyvisa-sim.devices
    ~~~~~~~~~~~~~~~~~~

    Classes to simulate devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

from pyvisa import constants, rname

from .common import logger
from .component import to_bytes, Component, NoResponse


class StatusRegister(object):

    def __init__(self, values):
        object.__init__(self)
        self._value = 0
        self._error_map = {}
        for name, value in values.items():
            if name == 'q':
                continue
            self._error_map[name] = int(value)

    def set(self, error_key):
        self._value = self._value | self._error_map[error_key]

    def keys(self):
        return self._error_map.keys()

    @property
    def value(self):
        return to_bytes(str(self._value))

    def clear(self):
        self._value = 0


class ErrorQueue(object):

    def __init__(self, values):

        super(ErrorQueue, self).__init__()
        self._queue = []
        self._error_map = {}
        for name, value in values.items():
            if name in ('q', 'default', 'strict'):
                continue
            self._error_map[name] = to_bytes(value)
        self._default = to_bytes(values['default'])

    def append(self, err):
        if err in self._error_map:
            self._queue.append(self._error_map[err])

    @property
    def value(self):
        if self._queue:
            return self._queue.pop(0)
        else:
            return self._default

    def clear(self):
        self._queue = []


class Device(Component):
    """A representation of a responsive device

    :param name: The identification name of the device
    :type name: str
    :param name: fullpath of the device where it is defined.
    :type name: str
    """

    # To be bound when adding the Device to Devices
    _resource_name = None

    # Default end of message used in query operations
    # :type: bytes
    _query_eom = b''

    # Default end of message used in response operations
    # :type: bytes
    _response_eom = None

    def __init__(self, name, delimiter):

        super(Device, self).__init__()

        #: Name of the device.
        self.name = name

        #: Special character use to delimit multiple messages.
        self.delimiter = delimiter

        #: Mapping between a name and a Channels object
        self._channels = {}

        #: Stores the error response for each query accepted by the device.
        #: :type: dict[bytes, bytes | NoResponse]
        self._error_response = {}

        #: Stores the registers by name.
        #: Register name -> Register object
        #: :type: dict[str, StatusRegister]
        self._status_registers = {}

        self._error_map = {}

        #: Stores the specific end of messages for device.
        #: TYPE CLASS -> (query termination, response termination)
        #: :type: dict[(pyvisa.constants.InterfaceType, str), (str, str)]
        self._eoms = {}

        #: Buffer in which the user can read
        #: :type: bytearray
        self._output_buffer = bytearray()

        #: Buffer in which the user can write
        #: :type: bytearray
        self._input_buffer = bytearray()

        #: Mapping an error queue query and the queue.
        #: :type: dict
        self._error_queues = {}

    @property
    def resource_name(self):
        """Assigned resource name
        """
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value):
        p = rname.parse_resource_name(value)
        self._resource_name = str(p)
        try:
            self._query_eom, self._response_eom =\
                self._eoms[(p.interface_type_const, p.resource_class)]
        except KeyError:
            logger.warning('No eom provided for %s, %s.'
                           'Using LF.'% (p.interface_type_const, p.resource_class))
            self._query_eom, self._response_eom = b'\n', b'\n'

    def add_channels(self, ch_name, ch_obj):
        """Add a channel definition.

        """
        self._channels[ch_name] = ch_obj

    def add_error_handler(self, error_input):
        """Add error handler to the device
        """

        if isinstance(error_input, dict):
            error_response = error_input.get('response', {})
            cerr = error_response.get('command_error', NoResponse)
            qerr = error_response.get('query_error', NoResponse)

            response_dict = {'command_error': cerr,
                             'query_error': qerr}

            register_list = error_input.get('status_register', [])

            for register_dict in register_list:
                query = register_dict['q']
                register = StatusRegister(register_dict)
                self._status_registers[to_bytes(query)] = register
                for key in register.keys():
                    self._error_map[key] = register

            queue_list = error_input.get('error_queue', [])

            for queue_dict in queue_list:
                query = queue_dict['q']
                err_queue = ErrorQueue(queue_dict)
                self._error_queues[to_bytes(query)] = err_queue

        else:
            response_dict = {'command_error': error_input,
                             'query_error': error_input}

        for key, value in response_dict.items():
            self._error_response[key] = to_bytes(value)

    def error_response(self, error_key):
        if error_key in self._error_map:
            self._error_map[error_key].set(error_key)

        for q in self._error_queues.values():
            q.append(error_key)

        return self._error_response.get(error_key)

    def add_eom(self, type_class, query_termination, response_termination):
        """Add default end of message for a given interface type and resource class.

        :param type_class: interface type and resource class as strings joined by space
        :param query_termination: end of message used in queries.
        :param response_termination: end of message used in responses.
        """
        interface_type, resource_class = type_class.split(' ')
        interface_type = getattr(constants.InterfaceType,
                                 interface_type.lower())
        self._eoms[(interface_type,
                    resource_class)] = (to_bytes(query_termination),
                                        to_bytes(response_termination))

    def write(self, data):
        """Write data into the device input buffer.

        :param data: single element byte
        :type data: bytes
        """
        logger.debug('Writing into device input buffer: %r' % data)
        if not isinstance(data, bytes):
            raise TypeError('data must be an instance of bytes')

        if len(data) != 1:
            msg = 'data must have a length of 1, not %d'
            raise ValueError(msg % len(data))

        self._input_buffer.extend(data)

        l = len(self._query_eom)
        if not self._input_buffer.endswith(self._query_eom):
            return

        try:
            message = bytes(self._input_buffer[:-l])
            queries = (message.split(self.delimiter) if self.delimiter
                       else [message])
            for query in queries:
                response = self._match(query)
                eom = self._response_eom

                if response is None:
                    response = self.error_response('command_error')

                if response is not NoResponse:
                    self._output_buffer.extend(response)
                    self._output_buffer.extend(eom)

        finally:
            self._input_buffer = bytearray()

    def read(self):
        """Return a single byte from the output buffer
        """
        if self._output_buffer:
            b, self._output_buffer = (self._output_buffer[0:1],
                                      self._output_buffer[1:])
            return b

        return b''

    def _match(self, query):
        """Tries to match in dialogues, getters and setters and subcomponents

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
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

    def _match_registers(self, query):
        """Tries to match in status registers

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        if query in self._status_registers:
            register = self._status_registers[query]
            response = register.value
            logger.debug('Found response in status register: %s',
                         repr(response))
            register.clear()

            return response

    def _match_errors_queues(self, query):
        """Tries to match in error queues

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        if query in self._error_queues:
            queue = self._error_queues[query]
            response = queue.value
            logger.debug('Found response in error queue: %s',
                         repr(response))

            return response


class Devices(object):
    """The group of connected devices.

    """

    def __init__(self):

        #: Devices
        #: dict[str, Device]
        self._internal = {}

    def add_device(self, resource_name, device):
        """Bind device to resource name
        """

        if device.resource_name is not None:
            msg = 'The device %r is already assigned to %s'
            raise ValueError(msg % (device, device.resource_name))

        device.resource_name = resource_name

        self._internal[device.resource_name] = device

    def __getitem__(self, item):
        return self._internal[item]

    def list_resources(self):
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())
