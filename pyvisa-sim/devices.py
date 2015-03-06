# -*- coding: utf-8 -*-
"""
    pyvisa-sim.devices
    ~~~~~~~~~~~~~~~~~~

    Classes to simulate devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
try:
    import Queue as queue
except ImportError:
    import queue

import stringparser
import sys

from pyvisa import logger, constants 

from . import common


PY3 = sys.version_info[0] == 3


if PY3:
    string_types = str,
    text_type = str
    binary_type = bytes
else:
    string_types = basestring,
    text_type = unicode
    binary_type = str


def is_str(input_value):
    """Do string type checking across versions of Python
    """
    return isinstance(input_value, string_types)


def to_bytes(val):
    """Takes a text message and return a tuple

    """
    if type(val) in (text_type, binary_type):
        val = val.replace('\\r', '\r').replace('\\n', '\n')
        return val.encode()
    return val


class NoResponse(object):
    """Sentinel used for when there should not be a response to a query
    """

    @classmethod
    def parse_error(cls, error_input):
        if is_str(error_input):
            if 'null_response' in error_input:
                return NoResponse()
            return error_input
        else:
            return error_input


class Property(object):
    """A device property
    """

    _value = None

    def __init__(self, name, value, specs):
        """
        :param name: name of the property
        :param value: default value
        :param specs: specification dictionary
        :return:
        """

        t = specs.get('type', None)
        if t:
            for key, val in (('float', float), ('int', int), ('str', str)):
                if t == key:
                    t = specs['type'] = val
                    break

        for key in ('min', 'max'):
            if key in specs:
                specs[key] = t(specs[key])

        if 'valid' in specs:
            specs['valid'] = set([t(val) for val in specs['valid']])

        self.name = name
        self.specs = specs
        self.set_value(value)

    @property
    def value(self):
        return self._value

    def set_value(self, string_value):
        """Set the value
        """
        specs = self.specs
        if 'type' in specs:
            value = specs['type'](string_value)
        else:
            value = string_value
        if 'min' in specs and value < specs['min']:
            raise ValueError
        if 'max' in specs and value > specs['max']:
            raise ValueError
        if 'valid' in specs and value not in specs['valid']:
            raise ValueError
        self._value = value


class StatusRegister(object):
    
    def __init__(self, input_dict):
        object.__init__(self)
        self._value = 0
        self._error_map = {}
        for name, value in input_dict.items():
            if name != 'q':
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


class Device(object):
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

    def __init__(self, name):

        # Name of the device.
        self.name = name

        # :type: bytes
        self._error_response = {}
        self._error_map = {}
        self._status_registers = {}

        #: Stores the specific end of messages for device.
        #: TYPE CLASS -> (query termination, response termination)
        #: :type: dict[(pyvisa.constants.InterfaceType, str), (str, str)]
        self._eoms = {}

        #: Stores the queries accepted by the device.
        #: query: (response, error response)
        #: :type: dict[bytes, bytes]
        self._dialogues = {}

        #: Maps property names to value, type, validator
        #: :type: dict[str, Property]
        self._properties = {}

        #: Stores the getter queries accepted by the device.
        #: query: (property_name, response)
        #: :type: dict[bytes, (str, str)]
        self._getters = {}

        #: Stores the setters queries accepted by the device.
        #: (property_name, string parser query, response, error response)
        #: :type: list[(str, stringparser.Parser, bytes, bytes)]
        self._setters = []

        #: Buffer in which the user can read
        #: :type: bytearray
        self._output_buffer = bytearray()

        #: Buffer in which the user can write
        #: :type: bytearray
        self._input_buffer = bytearray()

    @property
    def resource_name(self):
        """Assigned resource name
        """
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value):
        p = common.parse_resource_name(value)
        self._resource_name = p['canonical_resource_name']
        self._query_eom, self._response_eom = self._eoms[(p['interface_type'],
                                                          p['resource_class'])]

    def add_error_handler(self, error_input):
        """Add error handler to the device
        """
        response_dict = {}
        if is_str(error_input):
            error_response = NoResponse.parse_error(error_input)
            response_dict = {
                'command_error': error_response,
                'query_error': error_response,
                }
        elif type(error_input) == dict:
            error_response = error_input.get('response', {})
            response_dict = {
                'command_error': NoResponse.parse_error(
                    error_response.get('command_error', NoResponse())
                    ),
                'query_error': NoResponse.parse_error(
                    error_response.get('query_error', NoResponse())
                    ),
                }
            register_list = error_input.get('status_register', [])
            for register_dict in register_list:
                query = register_dict.get('q')
                register = StatusRegister(register_dict)
                self._status_registers[to_bytes(query)] = register
                for key in register.keys():
                    self._error_map[key] = register

        for key, value in response_dict.items():
            self._error_response[key] = to_bytes(value)
        
        return response_dict['command_error']
    
    def error_response(self, error_key):
        if error_key in self._error_map:
            self._error_map[error_key].set(error_key)
        return self._error_response.get(error_key)

    def add_dialogue(self, query, response):
        """Add dialogue to device.

        :param query: query string
        :param response: response string
        """
        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(self, name, default_value, getter_pair, setter_triplet, specs):
        """Add property to device

        :param name: property name
        :param default_value: default value as string
        :param getter_pair: (query, response)
        :param setter_triplet: (query, response, error)
        :param specs: specification of the Property
        """
        self._properties[name] = Property(name, default_value, specs)

        query, response = getter_pair
        self._getters[to_bytes(query)] = name, response

        query, response, error = setter_triplet
        error_response = NoResponse.parse_error(error)
        self._setters.append((name,
                              stringparser.Parser(query),
                              to_bytes(response),
                              to_bytes(error_response)))

    def add_eom(self, type_class, query_termination, response_termination):
        """Add default end of message for a given interface type and resource class.

        :param type_class: interface type and resource class as strings joined by space
        :param query_termination: end of message used in queries.
        :param response_termination: end of message used in responses.
        """
        interface_type, resource_class = type_class.split(' ')
        interface_type = getattr(constants.InterfaceType, interface_type.lower())
        self._eoms[(interface_type, resource_class)] = (to_bytes(query_termination),
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
            raise ValueError('data must have a length of 1, not %d' % len(data))

        self._input_buffer.extend(data)

        l = len(self._query_eom)
        if not self._input_buffer.endswith(self._query_eom):
            return

        try:
            query = bytes(self._input_buffer[:-l])
            response = self._match(query)
            eom = self._response_eom

            if response is None:
                response = self.error_response('command_error')

            if isinstance(response, NoResponse):
                self._output_buffer = bytearray()
            else:
                self._output_buffer.extend(response)
                self._output_buffer.extend(eom)

        finally:
            self._input_buffer = bytearray()

    def _match(self, query):
        """Tries to match in dialogues, getters and setters

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """

        # Try to match in the queries
        if query in self._dialogues:
            response = self._dialogues[query]
            logger.debug('Found response in queries: %s' % repr(response))

            return response

        # Now in the getters
        if query in self._getters:
            name, response = self._getters[query]
            logger.debug('Found response in getter of %s' % name)

            return response.format(self._properties[name].value).encode('utf-8')

        # Try to match in the status registers
        if query in self._status_registers:
            register = self._status_registers[query]
            response = register.value
            logger.debug('Found response in status register: %s' % repr(response))
            register.clear()

            return response

        q = query.decode('utf-8')

        # Finally in the setters, this will be slow.
        for name, parser, response, error_response in self._setters:
            try:
                value = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response
                return self.error_response('command_error')

        return None

    def read(self):
        """Return a single byte from the output buffer
        """
        if self._output_buffer:
            b, self._output_buffer = self._output_buffer[0:1], self._output_buffer[1:]
            return b
        self.error_response('query_error')

        return b''


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
            raise ValueError('The device %r is already assigned to %s' % (device, device.resource_name))

        device.resource_name = resource_name

        self._internal[device.resource_name] = device

    def __getitem__(self, item):
        return self._internal[item]

    def list_resources(self):
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())

