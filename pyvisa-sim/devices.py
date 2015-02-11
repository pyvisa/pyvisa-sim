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

from pyvisa import logger, constants

from . import common


def to_bytes(val):
    """Takes a text message and return a tuple

    """
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    return val.encode()


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
            for key, val in (('float', float), ('int', int)):
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

    def __init__(self, name, error_response):

        # Name of the device.
        self.name = name

        # :type: bytes
        self.error_response = to_bytes(error_response)

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
        self._setters.append((name,
                              stringparser.Parser(query),
                              to_bytes(response),
                              to_bytes(error)))

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

        query = bytes(self._input_buffer[:-l])
        response = self._match(query)
        eom = self._response_eom

        if response is None:
            response = self.error_response

        self._output_buffer.extend(response)
        self._output_buffer.extend(eom)

        self._input_buffer = bytearray()

    def _match(self, query):
        """Tries to match in dialogues, getters and setters

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """

        # Try to match in the queries
        try:
            response = self._dialogues[query]
            logger.debug('Found response in queries: %s' % repr(response))

            return response

        except KeyError:
            pass

        # Now in the getters
        try:
            name, response = self._getters[query]
            logger.debug('Found response in getter of %s' % name)

            return response.format(self._properties[name].value).encode('utf-8')

        except KeyError:
            pass

        q = query.decode('utf-8')

        # Finally in the setters, this will be slow.
        for name, parser, response, err in self._setters:
            try:
                value = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response

            except ValueError:
                return err

        return None

    def read(self):
        """Return a single byte from the output buffer
        """
        if self._output_buffer:
            b, self._output_buffer = self._output_buffer[0:1], self._output_buffer[1:]
            return b

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

