# -*- coding: utf-8 -*-
"""
    pyvisa-sim.devices
    ~~~~~~~~~~~~~~~~~~

    Classes to simulate devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

import stringparser

from pyvisa import logger

try:
    import Queue as queue
except ImportError:
    import queue

from . import sessions


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

    resource_name = None

    def __init__(self, name, error_response):

        # Name of the device.
        self.name = name

        self.error_response = text_to_iter(error_response)

        #: Stores the queries accepted by the device.
        #: query: (response, error response)
        #: dict[tuple[bytes], tuple[bytes]]
        self._queries = {}

        #: Maps property names to value, type, validator
        #: dict[str, (object, callable, callable)]
        self._properties = {}

        #: Stores the getter queries accepted by the device.
        #: query: (property_name, response)
        #: dict[tuple[bytes], [str, tuple[bytes]]]
        self._getters = {}

        #: Stores the setters queries accepted by the device.
        #: (property_name, string parser query, response, error response)
        #: list[str, tuple[bytes], tuple[bytes], tuple[bytes]]]
        self._setters = []

        #: Buffer in which the user can read
        #: queue.Queue[bytes]
        self._output_buffer = queue.Queue()

        #: Buffer in which the user can write
        #: [bytes]
        self._input_buffer = list()

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

        # It would be better to call this only if an end of message is found.
        # But we need to be careful with multiple messages in one.
        answer = self._match_input_buffer()

        if answer is None:
            return

        for part in answer:
            self._output_buffer.put(part)

        self._input_buffer.clear()

    def _match_input_buffer(self):
        # After writing to the input buffer, tries to see if the query is in the
        # list of dialogues it understands and reply accordingly.

        ib = tuple(self._input_buffer)

        try:
            answer = self._queries[ib]
            logger.debug('Found answer in queries: %s' % repr(answer))

            return answer

        except KeyError:
            pass

        # Now in the getters
        try:
            name, answer = self._getters[ib]
            logger.debug('Found answer in getter of %s' % name)

            return text_to_iter(answer.format(self._properties[name].value))

        except KeyError:
            pass

        q = b''.join(self._input_buffer).decode('utf-8')

        # Finally in the setters, this will be slow.
        for name, parser, answer, err in self._setters:
            try:
                value = parser(q)
                logger.debug('Found answer in getter of %s' % name)
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

        self._internal[resource_name] = device
        device.resource_name = resource_name

    def __getitem__(self, item):
        return self._internal[item]

    def list_resources(self):
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())

