# -*- coding: utf-8 -*-
"""
    pyvisa-sim.channel
    ~~~~~~~~~~~~~~~~~~

    Classes to enable the use of channels in devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
from collections import defaultdict

import stringparser

from .common import logger
from .component import Component, Property, to_bytes


class ChannelProperty(Property):
    """A channel property storing the value for all channels.

    """
    def __init__(self, channel, name, default_value, specs):

        #: Refrence to the channel holding that property.
        self._channel = channel

        super(ChannelProperty, self).__init__(name, default_value, specs)

    def init_value(self, string_value):
        """Create an empty defaultdict holding the default value.

        """
        value = self.validate_value(string_value)
        self._value = defaultdict(lambda: value)

    def get_value(self):
        """Get the current value for a channel.

        """
        return self._value[self._channel._selected]

    def set_value(self, string_value):
        """Set the current value for a channel.

        """
        value = self.validate_value(string_value)
        self._value[self._channel._selected] = value


class ChDict(dict):
    """Default dict like creating specialized sommand sets for a channel.

    """
    def __missing__(self, key):
        """Create a channel specialized version of the mapping found in
        __default__.

        """
        return {k.decode('utf-8').format(ch_id=key).encode('utf-8'): v
                for k, v in self['__default__'].items()}


class Channels(Component):
    """A component representing a device channels.

    """

    def __init__(self, device, ids, can_select):

        super(Channels, self).__init__()

        #: Flag indicating whether or not the channel can be selected inside
        #: the query or if it is pre-selected by a previous command.
        self.can_select = can_select

        #: Currently active channel, this can either reflect the currently
        #: selected channel on the device or the currently inspected possible
        #: when attempting to match.
        self._selected = None

        #: Reference to the parent device from which we might need to query and
        #: set the current selected channel
        self._device = device

        #: Ids of the activated channels.
        self._ids = ids

        self._getters = ChDict(__default__={})

        self._dialogues = ChDict(__default__={})

    def add_dialogue(self, query, response):
        """Add dialogue to channel.

        :param query: query string
        :param response: response string
        """
        self._dialogues['__default__'][to_bytes(query)] = to_bytes(response)

    def add_property(self, name, default_value, getter_pair, setter_triplet,
                     specs):
        """Add property to channel

        :param name: property name
        :param default_value: default value as string
        :param getter_pair: (query, response)
        :param setter_triplet: (query, response, error)
        :param specs: specification of the Property
        """
        self._properties[name] = ChannelProperty(self, name,
                                                 default_value, specs)

        if getter_pair:
            query, response = getter_pair
            self._getters['__default__'][to_bytes(query)] = name, response

        if setter_triplet:
            query, response, error = setter_triplet
            self._setters.append((name,
                                  stringparser.Parser(query),
                                  to_bytes(response),
                                  to_bytes(error)))

    def match(self, query):
        """Try to find a match for a query in the channel commands.

        """
        if not self.can_select:
            ch_id = self._device._properties['selected_channel'].get_value()
            if ch_id in self._ids:
                self._selected = ch_id
            else:
                return

            response = self._match_dialog(query,
                                          self._dialogues['__default__'])
            if response is not None:
                return response

            response = self._match_getters(query,
                                           self._getters['__default__'])
            if response is not None:
                return response

        else:
            for ch_id in self._ids:
                self._selected = ch_id
                response = self._match_dialog(query,
                                              self._dialogues[ch_id])
                if response is not None:
                    return response

                response = self._match_getters(query,
                                               self._getters[ch_id])

                if response is not None:
                    return response

        return self._match_setters(query)

    def _match_setters(self, query):
        """Try to find a match
        """
        q = query.decode('utf-8')
        for name, parser, response, error_response in self._setters:
            try:
                parsed = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                if isinstance(parsed, dict) and 'ch_id' in parsed:
                    self._selected = parsed['ch_id']
                    self._properties[name].set_value(parsed['0'])
                else:
                    self._properties[name].set_value(parsed)
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response
                return self._device.error_response('command_error')

        return None
