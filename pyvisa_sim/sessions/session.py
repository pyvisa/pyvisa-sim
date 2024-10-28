# -*- coding: utf-8 -*-
"""Base session class.

:copyright: 2014-2024 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""

import time
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar

from pyvisa import attributes, constants, rname, typing

from ..common import int_to_byte, logger
from ..devices import Device

S = TypeVar("S", bound="Session")


class Session:
    """A base class for Session objects.

    Just makes sure that common methods are defined and information is stored.

    Parameters
    ----------
    resource_manager_session : VISARMSession
        The session handle of the parent Resource Manager
    resource_name : str
        The resource name.
    parsed : rname.ResourceName
        Parsed resource name (optional).

    """

    #: Maps (Interface Type, Resource Class) to Python class encapsulating that resource.
    #: dict[(Interface Type, Resource Class) , Session]
    _session_classes: Dict[Tuple[constants.InterfaceType, str], Type["Session"]] = {}

    #: Session handler for the resource manager.
    session_type: Tuple[constants.InterfaceType, str]

    #: Simulated device access by this session
    device: Device

    @classmethod
    def get_session_class(
        cls, interface_type: constants.InterfaceType, resource_class: str
    ) -> Type["Session"]:
        """Return the session class for a given interface type and resource class.

        Parameters
        ----------
        interface_type : constants.InterfaceType
            Type of the interface for which we need a Session class.
        resource_class : str
            Resource class for which we need a Session class.

        Returns
        -------
        Type[Session]
            Registered session class.

        """
        try:
            return cls._session_classes[(interface_type, resource_class)]
        except KeyError:
            raise ValueError(
                "No class registered for %s, %s" % (interface_type, resource_class)
            )

    @classmethod
    def register(
        cls, interface_type: constants.InterfaceType, resource_class: str
    ) -> Callable[[Type[S]], Type[S]]:
        """Register a session class for a given interface type and resource class.

        Parameters
        ----------
        interface_type : constants.InterfaceType
            Type of the interface this session should be used for.
        resource_class : str
            Resource class for which this session should be used for.

        """

        def _internal(python_class):
            if (interface_type, resource_class) in cls._session_classes:
                logger.warning(
                    "%s is already registered in the ResourceManager. "
                    "Overwriting with %s"
                    % ((interface_type, resource_class), python_class)
                )

            python_class.session_type = (interface_type, resource_class)
            cls._session_classes[(interface_type, resource_class)] = python_class
            return python_class

        return _internal

    def __init__(
        self,
        resource_manager_session: typing.VISARMSession,
        resource_name: str,
        parsed: Optional[rname.ResourceName] = None,
    ):
        if parsed is None:
            parsed = rname.parse_resource_name(resource_name)
        self.parsed = parsed
        self.attrs = {
            constants.ResourceAttribute.resource_manager_session: resource_manager_session,
            constants.ResourceAttribute.resource_name: str(parsed),
            constants.ResourceAttribute.resource_class: parsed.resource_class,
            constants.ResourceAttribute.interface_type: parsed.interface_type_const,
        }
        self.after_parsing()

    def after_parsing(self) -> None:
        """Override in derived class to customize the session.

        Executed after the resource name has been parsed and the attr dictionary
        has been filled.

        """
        pass

    def get_attribute(
        self, attribute: constants.ResourceAttribute
    ) -> Tuple[Any, constants.StatusCode]:
        """Get an attribute from the session.

        Parameters
        ----------
        attribute : constants.ResourceAttribute
            Attribute whose value to retrieve.

        Returns
        -------
        object
            Attribute value.
        constants.StatusCode
            Status code of the operation execution.

        """

        # Check that the attribute exists.
        try:
            attr = attributes.AttributesByID[attribute]
        except KeyError:
            return 0, constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return 0, constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is readable.
        if not attr.read:
            raise Exception("Do not now how to handle write only attributes.")

        # Return the current value of the default according the VISA spec
        return (
            self.attrs.setdefault(attribute, attr.default),
            constants.StatusCode.success,
        )

    def set_attribute(
        self, attribute: constants.ResourceAttribute, attribute_state: Any
    ) -> constants.StatusCode:
        """Get an attribute from the session.

        Parameters
        ----------
        attribute : constants.ResourceAttribute
            Attribute whose value to alter.
        attribute_state : object
            Value to set the attribute to.

        Returns
        -------
        constants.StatusCode
            Status code describing the operation execution.

        """

        # Check that the attribute exists.
        try:
            attr = attributes.AttributesByID[attribute]
        except KeyError:
            return constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is valid for this session type.
        if not attr.in_resource(self.session_type):
            return constants.StatusCode.error_nonsupported_attribute

        # Check that the attribute is writable.
        if not attr.write:
            return constants.StatusCode.error_attribute_read_only

        try:
            self.attrs[attribute] = attribute_state
        except ValueError:
            return constants.StatusCode.error_nonsupported_attribute_state

        return constants.StatusCode.success


class MessageBasedSession(Session):
    """Base class for Message-Based sessions that support ``read`` and ``write`` methods."""

    def read(self, count: int) -> Tuple[bytes, constants.StatusCode]:
        timeout, _ = self.get_attribute(constants.ResourceAttribute.timeout_value)
        timeout /= 1000

        suppress_end_enabled, _ = self.get_attribute(
            constants.ResourceAttribute.suppress_end_enabled
        )
        termchar, _ = self.get_attribute(constants.ResourceAttribute.termchar)
        termchar = int_to_byte(termchar)
        termchar_enabled, _ = self.get_attribute(
            constants.ResourceAttribute.termchar_enabled
        )

        interface_type, _ = self.get_attribute(
            constants.ResourceAttribute.interface_type
        )
        is_asrl = interface_type == constants.InterfaceType.asrl
        if is_asrl:
            asrl_end_in, _ = self.get_attribute(constants.ResourceAttribute.asrl_end_in)
            asrl_last_bit, _ = self.get_attribute(
                constants.ResourceAttribute.asrl_data_bits
            )
            if asrl_last_bit:
                asrl_last_bit_mask = 1 << (asrl_last_bit - 1)

        start = time.monotonic()

        out = bytearray()

        while time.monotonic() - start <= timeout:
            last, end_indicator = self.device.read()

            out += last

            # N.B.: References here are to VPP-4.3 rev. 7.2.1
            # (https://www.ivifoundation.org/downloads/VISA/vpp43_2024-01-04.pdf).

            is_termchar = last == termchar

            if is_asrl:
                end_indicator = False
                if asrl_end_in == constants.SerialTermination.none:
                    # Rule 6.1.6.
                    end_indicator = False
                elif (
                    asrl_end_in == constants.SerialTermination.termination_char
                    and is_termchar
                ) or (
                    asrl_end_in == constants.SerialTermination.last_bit
                    and out[-1] & asrl_last_bit_mask
                ):
                    # Rule 6.1.7.
                    end_indicator = True

            if end_indicator and not suppress_end_enabled:
                # Rule 6.1.1, Rule 6.1.4, Observation 6.1.3.
                return out, constants.StatusCode.success
            elif is_termchar and termchar_enabled:
                # Rule 6.1.2, Rule 6.1.5, Observation 6.1.4.
                return out, constants.StatusCode.success_termination_character_read
            elif len(out) == count:
                # Rule 6.1.3.
                return out, constants.StatusCode.success_max_count_read

            # Busy-wait only if the device's output buffer was empty.
            if not last:
                time.sleep(0.01)
        else:
            return out, constants.StatusCode.error_timeout

    def write(self, data: bytes) -> Tuple[int, constants.StatusCode]:
        send_end = self.get_attribute(constants.ResourceAttribute.send_end_enabled)

        self.device.write(data)

        if send_end:
            # EOM4882
            pass

        return len(data), constants.StatusCode.success
