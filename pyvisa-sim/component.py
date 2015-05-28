# -*- coding: utf-8 -*-
"""
    pyvisa-sim.component
    ~~~~~~~~~~~~~~~~~~~~

    Base classes for devices parts.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
import stringparser

from .common import logger


def to_bytes(val):
    """Takes a text message and return a tuple
    """
    if val is NoResponse:
        return val
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    return val.encode()


# Sentinel used for when there should not be a response to a query
NoResponse = object()


class Property(object):
    """A device property
    """

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
        self._value = None
        self.init_value(value)

    def init_value(self, string_value):
        """Initialize the value hold by the Property.

        """
        self.set_value(string_value)

    def get_value(self):
        """Return the value stored by the Property.

        """
        return self._value

    def set_value(self, string_value):
        """Set the value
        """
        self._value = self.validate_value(string_value)

    def validate_value(self, string_value):
        """Validate that a value match the Property specs.

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
        return value


class Component(object):
    """A component of a device.

    """

    def __init__(self):

        #: Stores the queries accepted by the device.
        #: query: response
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

    def add_dialogue(self, query, response):
        """Add dialogue to device.

        :param query: query string
        :param response: response string
        """
        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(self, name, default_value, getter_pair, setter_triplet,
                     specs):
        """Add property to device

        :param name: property name
        :param default_value: default value as string
        :param getter_pair: (query, response)
        :param setter_triplet: (query, response, error)
        :param specs: specification of the Property
        """
        self._properties[name] = Property(name, default_value, specs)

        if getter_pair:
            query, response = getter_pair
            self._getters[to_bytes(query)] = name, response

        if setter_triplet:
            query, response, error = setter_triplet
            self._setters.append((name,
                                  stringparser.Parser(query),
                                  to_bytes(response),
                                  to_bytes(error)))

    def match(self, query):
        """Try to find a match for a query in the instrument commands.

        """
        raise NotImplementedError()

    def _match_dialog(self, query, dialogues=None):
        """Tries to match in dialogues

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        if dialogues is None:
            dialogues = self._dialogues

        # Try to match in the queries
        if query in dialogues:
            response = dialogues[query]
            logger.debug('Found response in queries: %s' % repr(response))

            return response

    def _match_getters(self, query, getters=None):
        """Tries to match in getters

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        if getters is None:
            getters = self._getters

        if query in getters:
            name, response = getters[query]
            logger.debug('Found response in getter of %s' % name)
            response = response.format(self._properties[name].get_value())
            return response.encode('utf-8')

    def _match_setters(self, query):
        """Tries to match in setters

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        q = query.decode('utf-8')
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
