# -*- coding: utf-8 -*-
"""Base classes for devices parts.

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import enum
from typing import (
    Dict,
    Final,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

import stringparser
from typing_extensions import TypeAlias  # not needed starting with 3.10

from .common import logger


# Sentinel enum which is the only 'clean' way to have sentinels and meaningful typing
class Responses(enum.Enum):
    NO = object()


NoResponse: Final = Responses.NO

# Type aliases to be used when NoResponse is an acceptable value
OptionalStr: TypeAlias = Union[str, Literal[Responses.NO]]
OptionalBytes: TypeAlias = Union[bytes, Literal[Responses.NO]]


@overload
def to_bytes(val: str) -> bytes:
    ...


@overload
def to_bytes(val: Literal[Responses.NO]) -> Literal[Responses.NO]:
    ...


def to_bytes(val):
    """Takes a text message or NoResponse and encode it."""
    if val is NoResponse:
        return val

    val = val.replace("\\r", "\r").replace("\\n", "\n")
    return val.encode()


T = TypeVar("T", bound=Union[int, float, str])


class Specs(Generic[T]):
    """Specification to validate a property value.

    Parameters
    ----------
    specs : DIct[str, str]
        Specs as a dictionary as extracted from the yaml config.

    """

    #: Value that lead to some validation are int, float, str
    type: Optional[Type[T]]

    #: Minimal admissible value
    min: Optional[T]

    #: Maximal admissible value
    max: Optional[T]

    #: Discrete set of valid values
    valid: Set[T]

    # FIXME add support for special values
    # some instrument support INCR DECR for increment decrement,
    # other support MIN, MAX, DEF

    def __init__(self, specs: Dict[str, str]) -> None:
        if "type" not in specs:
            raise ValueError("No property type was specified.")

        specs_type = None
        t = specs["type"]
        if t:
            for key, val in (("float", float), ("int", int), ("str", str)):
                if t == key:
                    specs_type = val
                    break

        if specs_type is None:
            raise ValueError(
                f"Invalid property type '{t}', valid types are: "
                "'int', 'float', 'str'"
            )
        self.type = specs_type

        self.min = specs_type(specs["min"]) if "min" in specs else None
        self.max = specs_type(specs["max"]) if "max" in specs else None
        self.valid = set([specs_type(val) for val in specs.get("valid", ())])


class Property(Generic[T]):
    """A device property

    Parameters
    ----------
    name : str
        Name of the property
    value : str
        Default value as a string
    specs : Dict[str, str]
        Specification used to validate the property value.

    """

    #: Name of the property
    name: str

    #: Specification used to validate
    specs: Optional[Specs[T]]

    def __init__(self, name: str, value: str, specs: Dict[str, str]):
        self.name = name
        try:
            self.specs = Specs[T](specs) if specs else None
        except ValueError as e:
            raise ValueError(f"Failed to create Specs for property {name}") from e
        self._value = None
        self.init_value(value)

    def init_value(self, string_value: str) -> None:
        """Initialize the value hold by the Property."""
        self.set_value(string_value)

    def get_value(self) -> Optional[T]:
        """Return the value stored by the Property."""
        return self._value

    def set_value(self, string_value: str) -> None:
        """Set the value"""
        self._value = self.validate_value(string_value)

    def validate_value(self, string_value: str) -> T:
        """Validate that a value match the Property specs."""
        specs = self.specs
        if specs is None:
            # This make str the default type
            return string_value  # type: ignore

        assert specs.type
        value: T = specs.type(string_value)  # type: ignore
        # Mypy dislike comparison with unresolved type vars it seems
        if specs.min is not None and value < specs.min:  # type: ignore
            raise ValueError(
                f"Value provided for {self.name}: {value} "
                f"is less than the minimum {specs.min}"
            )
        if specs.max is not None and value > specs.max:  # type: ignore
            raise ValueError(
                f"Value provided for {self.name}: {value} "
                f"is more than the maximum {specs.max}"
            )
        if specs.valid is not None and specs.valid and value not in specs.valid:
            raise ValueError(
                f"Value provide for {self.name}: {value}"
                f"Does not belong to the list of valid values: {specs.valid}"
            )
        return value

    # --- Private API

    #: Current value of the property.
    _value: Optional[T]


class Component:
    """A component of a device."""

    def __init__(self) -> None:
        self._dialogues = {}
        self._properties = {}
        self._getters = {}
        self._setters = []

    def add_dialogue(self, query: str, response: str) -> None:
        """Add dialogue to device.

        Parameters
        ----------
        query : str
            Query to which the dialog answers to.
        response : str
            Response to the dialog query.

        """
        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(
        self,
        name: str,
        default_value: str,
        getter_pair: Optional[Tuple[str, str]],
        setter_triplet: Optional[Tuple[str, OptionalStr, OptionalStr]],
        specs: Dict[str, str],
    ):
        """Add property to device

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
        self._properties[name] = Property(name, default_value, specs)

        if getter_pair:
            query, response = getter_pair
            self._getters[to_bytes(query)] = name, response

        if setter_triplet:
            query, response_, error = setter_triplet
            self._setters.append(
                (name, stringparser.Parser(query), to_bytes(response_), to_bytes(error))
            )

    def match(self, query: bytes) -> Optional[OptionalBytes]:
        """Try to find a match for a query in the instrument commands."""
        raise NotImplementedError()

    # --- Private API

    #: Stores the queries accepted by the device.
    #: query: response
    _dialogues: Dict[bytes, bytes]

    #: Maps property names to value, type, validator
    _properties: Dict[str, Property]

    #: Stores the getter queries accepted by the device.
    #: query: (property_name, response)
    _getters: Dict[bytes, Tuple[str, str]]

    #: Stores the setters queries accepted by the device.
    #: (property_name, string parser query, response, error response)
    _setters: List[Tuple[str, stringparser.Parser, OptionalBytes, OptionalBytes]]

    def _match_dialog(
        self, query: bytes, dialogues: Optional[Dict[bytes, bytes]] = None
    ) -> Optional[bytes]:
        """Tries to match in dialogues

        Parameters
        ----------
        query : bytes
            Query that we try to match to.
        dialogues : Optional[Dict[bytes, bytes]], optional
            Alternative dialogs to use when matching.

        Returns
        -------
        Optional[bytes]
            Response if a dialog matched.

        """
        if dialogues is None:
            dialogues = self._dialogues

        # Try to match in the queries
        if query in dialogues:
            response = dialogues[query]
            logger.debug("Found response in queries: %s" % repr(response))

            return response

        return None

    def _match_getters(
        self,
        query: bytes,
        getters: Optional[Dict[bytes, Tuple[str, str]]] = None,
    ) -> Optional[bytes]:
        """Tries to match in getters

        Parameters
        ----------
        query : bytes
            Query that we try to match to.
        dialogues : Optional[Dict[bytes, bytes]], optional
            Alternative getters to use when matching.

        Returns
        -------
        Optional[bytes]
            Response if a dialog matched.

        """
        if getters is None:
            getters = self._getters

        if query in getters:
            name, response = getters[query]
            logger.debug("Found response in getter of %s" % name)
            response = response.format(self._properties[name].get_value())
            return response.encode("utf-8")

        return None

    def _match_setters(self, query: bytes) -> Optional[OptionalBytes]:
        """Tries to match in setters

        Parameters
        ----------
        query : bytes
            Query that we try to match to.

        Returns
        -------
        Optional[bytes]
            Response if a dialog matched.

        """
        q = query.decode("utf-8")
        for name, parser, response, error_response in self._setters:
            try:
                value = parser(q)
                logger.debug("Found response in setter of %s" % name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response

        return None
