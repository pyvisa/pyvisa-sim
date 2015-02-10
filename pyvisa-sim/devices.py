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

from . import sessions
from . import common

def text_to_iter(val):
    """
    :param val:
    :return:
    """
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    if val.endswith('<EOM4882>'):
        return tuple(el.encode() for el in val.strip('<EOM4882>')) + (sessions.EOM4882, )
    else:
        return tuple(el.encode() for el in val)


class Property(object):

    def __init__(self, name, value, specs):

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
        self.set(value)

    def set(self, value):
        specs = self.specs
        if 'type' in specs:
            value = specs['type'](value)
        if 'min' in specs and value < specs['min']:
            raise ValueError
        if 'max' in specs and value > specs['max']:
            raise ValueError
        if 'valid' in specs and value not in specs['valid']:
            raise ValueError
        self.value = value


class Device(object):
    """A representation of a responsive device

    :param name: The identification name of the device
    :type name: str
    :param name: Fullpath of the device where it is defined.
    :type name: str
    """

    # To be bound when adding the Device to Devices
    _resource_name = None

    _query_eom = None
    _response_eom = None

    def __init__(self, name, error_response):

        # Name of the device.
        self.name = name

        self.error_response = text_to_iter(error_response)

        #: Stores the specific end of messages for device.
        #: TYPE CLASS -> (query termination, response termination)
        #: dict[str, (str, str)]
        self._eoms = {}

        #: Stores the queries accepted by the device.
        #: query: (response, error response)
        #: dict[tuple[bytes], tuple[bytes]]
        self._queries = {}

        #: Maps property names to value, type, validator
        #: dict[str, (object, callable, callable)]
        self._properties = {}

        #: Stores the getter queries accepted by the device.
        #: query: (property_name, response)
        #: dict[tuple[bytes], (str, tuple[bytes])]
        self._getters = {}

        #: Stores the setters queries accepted by the device.
        #: (property_name, string parser query, response, error response)
        #: list[(str, tuple[bytes], tuple[bytes], tuple[bytes]])]
        self._setters = []

        #: Buffer in which the user can read
        #: queue.Queue[bytes]
        self._output_buffer = queue.Queue()

        #: Buffer in which the user can write
        #: [bytes]
        self._input_buffer = list()

    @property
    def resource_name(self):
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value):
        p = common.parse_resource_name(value)
        self._resource_name = p['canonical_resource_name']
        self._query_eom, self._response_eom = self._eoms[(p['interface_type'],
                                                          p['resource_class'])]

    def add_dialogue(self, query, response):
        self._queries[text_to_iter(query)] = text_to_iter(response)

    def add_property(self, name, default_value, getter_pair, setter_triplet, specs):
        self._properties[name] = Property(name, default_value, specs)

        query, response = getter_pair
        self._getters[text_to_iter(query)] = name, response

        query, response, error = setter_triplet
        self._setters.append((name,
                              stringparser.Parser(query),
                              text_to_iter(response),
                              text_to_iter(error)))

    def add_eom(self, type_class, query_termination, response_termination):
        interface_type, resource_class = type_class.split(' ')
        interface_type = getattr(constants.InterfaceType, interface_type.lower())
        self._eoms[(interface_type, resource_class)] = (text_to_iter(query_termination),
                                                        text_to_iter(response_termination))

    def write(self, data):
        """Write data into the device input buffer.

        :param data: single element byte
        :type data: bytes
        """
        logger.debug('Writing into device input buffer: %r' % data)
        if not isinstance(data, (bytes, sessions.SpecialByte)):
            raise TypeError('data must be an instance of bytes or SpecialByte')

        if len(data) != 1:
            raise ValueError('data must have a length of 1, not %d' % len(data))

        self._input_buffer.append(data)

        l = len(self._query_eom)
        if not tuple(self._input_buffer[-l:]) == self._query_eom:
            return

        input_tuple = tuple(self._input_buffer[:-l])
        response = self._match(input_tuple)
        eom = self._response_eom

        if response is None:
            response = self.error_response

        for part in response:
            self._output_buffer.put(part)

        for part in eom:
            self._output_buffer.put(part)

        self._input_buffer.clear()

    def _match(self, part):
        # After writing to the input buffer, tries to see if the query is in the
        # list of dialogues it understands and reply accordingly.

        try:
            answer = self._queries[part]
            logger.debug('Found response in queries: %s' % repr(answer))

            return answer

        except KeyError:
            pass

        # Now in the getters
        try:
            name, answer = self._getters[part]
            logger.debug('Found response in getter of %s' % name)

            return text_to_iter(answer.format(self._properties[name].value))

        except KeyError:
            pass

        q = b''.join(part).decode('utf-8')

        # Finally in the setters, this will be slow.
        for name, parser, answer, err in self._setters:
            try:
                value = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                self._properties[name].set(value)
                return answer

            except ValueError:
                return err

        return None

    def read(self):
        """Return a single byte from the output buffer
        """
        return self._output_buffer.get_nowait()


class Devices(object):
    """The group of connected devices.
    """

    def __init__(self):

        #: Devices
        #: dict[str, Device]
        self._internal = {}

    def add_device(self, resource_name, device):
        """Add device.
        """

        if not device.resource_name is None:
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

