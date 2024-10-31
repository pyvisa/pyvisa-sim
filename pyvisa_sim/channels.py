# -*- coding: utf-8 -*-
"""Classes to enable the use of channels in devices.

:copyright: 2014-2024 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypeVar

import stringparser

from .common import logger
from .component import Component, OptionalBytes, OptionalStr, Property, T, to_bytes

if TYPE_CHECKING:
    from .devices import Device


class ChannelProperty(Property[T]):
    """A channel property storing the value for all channels."""

    def __init__(
        self, channel: "Channels", name: str, default_value: str, specs: Dict[str, str]
    ) -> None:
        self._channel = channel
        super(ChannelProperty, self).__init__(name, default_value, specs)

    def init_value(self, string_value: str) -> None:
        """Create an empty defaultdict holding the default value."""
        value = self.validate_value(string_value)
        self._value = defaultdict(lambda: value)

    def get_value(self) -> Optional[T]:
        """Get the current value for a channel."""
        return self._value[self._channel._selected]

    def set_value(self, string_value: str) -> None:
        """Set the current value for a channel."""
        value = self.validate_value(string_value)
        self._value[self._channel._selected] = value

    # --- Private API

    #: Reference to the channel holding that property.
    _channel: "Channels"

    #: Value of the property on a per channel basis
    _value: Dict[Any, T]  # type: ignore


V = TypeVar("V")


class ChDict(Dict[str, Dict[bytes, V]]):
    """Default dict like creating specialized command sets for a channel."""

    def __missing__(self, key: str) -> Dict[bytes, V]:
        """Create a channel specialized version of the mapping found in __default__."""
        return {
            k.decode("utf-8").format(ch_id=key).encode("utf-8"): v
            for k, v in self["__default__"].items()
        }


class Channels(Component):
    """A component representing a device channels."""

    #: Flag indicating whether or not the channel can be selected inside
    #: the query or if it is pre-selected by a previous command.
    can_select: bool

    def __init__(self, device: "Device", ids: List[str], can_select: bool):
        super(Channels, self).__init__()
        self.can_select: bool = can_select
        self._selected = None
        self._device = device
        self._ids = ids
        self._getters = ChDict(__default__={})
        self._dialogues = ChDict(__default__={})

    def add_dialogue(self, query: str, response: str) -> None:
        """Add dialogue to channel.

        Parameters
        ----------
        query : str
            Query string to which this dialogue answers to.
        response : str
            Response sent in response to a query.

        """
        self._dialogues["__default__"][to_bytes(query)] = to_bytes(response)

    def add_property(
        self,
        name: str,
        default_value: str,
        getter_pair: Optional[Tuple[str, str]],
        setter_triplet: Optional[Tuple[str, OptionalStr, OptionalStr]],
        specs: Dict[str, str],
    ) -> None:
        """Add property to channel

        Parameters
        ----------
        property_name : str
            Name of the property.
        default_value : str
            Default value of the property as a str.
        getter_pair : Optional[Tuple[str, str]]
            Parameters for accessing the property value (query and response str)
        setter_triplet : Optional[Tuple[str, OptionalStr, OptionalStr]]
            Parameters for setting the property value. The response and error
            are optional.
        specs : Dict[str, str]
            Specification for the property as a dict.

        """
        self._properties[name] = ChannelProperty(self, name, default_value, specs)

        if getter_pair:
            query, response = getter_pair
            self._getters["__default__"][to_bytes(query)] = name, response

        if setter_triplet:
            query, response_, error = setter_triplet
            self._setters.append(
                (name, stringparser.Parser(query), to_bytes(response_), to_bytes(error))
            )

    def match(self, query: bytes) -> Optional[OptionalBytes]:
        """Try to find a match for a query in the channel commands."""
        if not self.can_select:
            ch_id = self._device._properties["selected_channel"].get_value()
            if ch_id in self._ids:
                self._selected = ch_id
            else:
                return None

            response = self._match_dialog(query, self._dialogues["__default__"])
            if response is not None:
                return response

            response = self._match_getters(query, self._getters["__default__"])
            if response is not None:
                return response

        else:
            for ch_id in self._ids:
                self._selected = ch_id
                response = self._match_dialog(query, self._dialogues[ch_id])
                if response is not None:
                    return response

                response = self._match_getters(query, self._getters[ch_id])

                if response is not None:
                    return response

        return self._match_setters(query)

    # --- Private API

    #: Currently active channel, this can either reflect the currently
    #: selected channel on the device or the currently inspected possible
    #: when attempting to match.
    _selected: Optional[str]

    #: Reference to the parent device from which we might need to query and
    #: set the current selected channel
    _device: "Device"

    #: Ids of the activated channels.
    _ids: List[str]

    #: Dialogues organized by channel IDs
    _dialogues: Dict[str, Dict[bytes, bytes]]  # type: ignore

    #: Getters organized by channel ID
    _getters: Dict[str, Dict[bytes, Tuple[str, str]]]  # type: ignore

    def _match_setters(self, query: bytes) -> Optional[OptionalBytes]:
        """Try to find a match"""
        q = query.decode("utf-8")
        for name, parser, response, error_response in self._setters:
            try:
                parsed = parser(q)
                logger.debug("Found response in setter of %s" % name)
            except ValueError:
                continue

            try:
                if isinstance(parsed, dict) and "ch_id" in parsed:
                    self._selected = parsed["ch_id"]
                    self._properties[name].set_value(str(parsed["0"]))
                else:
                    self._properties[name].set_value(str(parsed))
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response
                return self._device.error_response("command_error")

        return None
