# -*- coding: utf-8 -*-
"""Base classes for devices parts.

:copyright: 2014-2026 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""

import enum
import random
import re
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


def _single_to_bytes(val: str) -> bytes:
    """Encodes a string with UTF-8, handling a single BYTES(...) directive.

    If the string is "BYTES(...)" where "..." is some substring, that substring
    is encoded using latin-1 rather than utf-8 and the surrounding BYTES()
    directive is removed.

    Examples
    --------

    The string "abcdefg" will be encoded to b"abcdefg".

    The string "BYTES(\x01\x02\x03\xf0\xe0\xc0)" will be encoded to
    b"\x10\x20\x30\xf0\xe0\xc0".

    The string "abBYTES(\x01\x02\x03\xf0\xe0\xc0)cd" will be encoded to
    b"abBYTES(\x01\x02\x03\xf0\xe0\xc0)cd".

    The string "BYTES(\x01)BYTES(\x02)" will be encoded to
    b"BYTES(\x01)BYTES(\x02)".

    """
    if match := re.fullmatch(r"BYTES\((.*)\)", val, flags=re.DOTALL):
        return match[1].encode("latin-1")
    return val.encode()


@overload
def to_bytes(val: str) -> bytes: ...


@overload
def to_bytes(val: Literal[Responses.NO]) -> Literal[Responses.NO]: ...


def to_bytes(val):
    """Takes a text message or NoResponse and encode it.

    Any substring of the form "BYTES(...)" where "..." is some substring, that
    substring is encoded using latin-1 rather than utf-8 and the surrounding
    BYTES() directive is removed.

    Examples
    --------

    The string "abcdefg" will be encoded to b"abcdefg".

    The string "BYTES(\x01\x02\x03\xf0\xe0\xc0)" will be encoded to
    b"\x10\x20\x30\xf0\xe0\xc0".

    The string "abBYTES(\x01\x02\x03\xf0\xe0\xc0)cd" will be encoded to
    b"ab\x01\x02\x03\xf0\xe0\xc0cd".

    The string "BYTES(\x01)BYTES(\x02)" will be encoded to b"\x01\x02".

    """
    if val is NoResponse:
        return val

    val = val.replace("\\r", "\r").replace("\\n", "\n")

    partitioned_string = re.split(r"(BYTES\([^)]+\))", val)
    return b"".join(map(_single_to_bytes, partitioned_string))


T = TypeVar("T", int, float, str)


def _split_command_and_suffix(query: str) -> Tuple[str, str]:
    """Split a command string into its mnemonic and trailing parameter suffix."""
    if not query:
        return "", ""

    if " " in query:
        command, suffix = re.split(r"\s+", query, maxsplit=1)
        return command, " " + suffix

    return query, ""


def _query_variants_for_scpi(query: str) -> List[str]:
    """Return the set of valid SCPI mnemonic prefixes for a query."""
    command, suffix = _split_command_and_suffix(query)
    if not command:
        return [query]

    parts = re.findall(r"[A-Za-z0-9]+|[^A-Za-z0-9]+", command)
    aliases: list[str] = [""]

    for part in parts:
        if re.search(r"[A-Za-z]", part):
            candidates: list[str] = []
            for current in aliases:
                candidates.extend(current + part[:i] for i in range(1, len(part) + 1))
            aliases = candidates
        else:
            aliases = [current + part for current in aliases]

    seen = set()
    normalized = []
    for alias in aliases:
        text = (alias.lower() + suffix).strip()
        if text not in seen:
            seen.add(text)
            normalized.append(text)

    return normalized


@overload
def _normalize_scpi_match(query: str) -> str: ...
@overload
def _normalize_scpi_match(query: bytes) -> bytes: ...


def _normalize_scpi_match(query):
    """Lower-case only the SCPI command prefix, preserving trailing arguments."""
    if isinstance(query, bytes):
        try:
            text = query.decode("utf-8")
        except UnicodeDecodeError:
            return query
        return _normalize_scpi_match(text).encode("utf-8")

    command, suffix = _split_command_and_suffix(query)
    return f"{command.lower()}{suffix}"


def random_response(response: str) -> str:
    """
    Return a response containing one or more random values.
    """
    random_directive = re.findall(
        r"{RANDOM\((\d*.\d*), (\d*.\d*), (\d*)\).*}", response
    )
    if len(random_directive) == 0:
        raise Exception(
            "pyvisa-sim: Wrong RANDOM directive, see documentation for correct usage."
        )
    response = re.sub(r"RANDOM\((\d*.\d*), (\d*.\d*), (\d*)\)", "", response)
    min_value, max_value, num_of_results = random_directive[0]
    output_str = []
    for i in range(int(num_of_results)):
        value = random.uniform(float(min_value), float(max_value))
        output_str.append(response.format(value))
    return ", ".join(output_str)


class Specs(Generic[T]):
    """Specification to validate a property value.

    Parameters
    ----------
    specs : Dict[str, str]
        Specs as a dictionary as extracted from the yaml config.

    """

    #: Value that lead to some validation are int, float, str
    type: Type[T]

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

        specs_type: Type[T] | None = None
        t = specs["type"]
        if t:
            for key, val in (("float", float), ("int", int), ("str", str)):
                if t == key:
                    specs_type = val  # type: ignore
                    break

        if specs_type is None:
            raise ValueError(
                f"Invalid property type '{t}', valid types are: 'int', 'float', 'str'"
            )
        self.type = specs_type

        self.min = self.type(specs["min"]) if "min" in specs else None
        self.max = self.type(specs["max"]) if "max" in specs else None
        self.valid = {self.type(val) for val in specs.get("valid", ())}


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
        value: T = specs.type(string_value)
        # Mypy dislike comparison with unresolved type vars it seems
        if specs.min is not None and value < specs.min:
            raise ValueError(
                f"Value provided for {self.name}: {value} "
                f"is less than the minimum {specs.min}"
            )
        if specs.max is not None and value > specs.max:
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
        self._dialogues_scpi = {}
        self._properties = {}
        self._getters = {}
        self._getters_scpi = {}
        self._setters = []

    def add_dialogue(
        self, query: str, response: str | Literal[Responses.NO], scpi: bool = False
    ) -> None:
        """Add dialogue to device.

        Parameters
        ----------
        query : str
            Query to which the dialog answers to.
        response : str
            Response to the dialog query.
        scpi : bool, optional
            Whether the query is SCPI-compliant and should match case-insensitive
            prefixes.

        """
        if scpi:
            for alias in _query_variants_for_scpi(query):
                self._dialogues_scpi[to_bytes(alias)] = to_bytes(response)
            return

        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(
        self,
        name: str,
        default_value: str,
        getter_pair: Optional[Tuple[str, str]],
        setter_triplet: Optional[Tuple[str, OptionalStr, OptionalStr]],
        specs: Dict[str, str],
        getter_scpi: bool = False,
        setter_scpi: bool = False,
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
            if getter_scpi:
                for alias in _query_variants_for_scpi(query):
                    self._getters_scpi[to_bytes(alias)] = name, response
            else:
                self._getters[to_bytes(query)] = name, response

        if setter_triplet:
            query, response_, error = setter_triplet
            variants = _query_variants_for_scpi(query) if setter_scpi else [query]
            for alias in variants:
                self._setters.append(
                    (
                        name,
                        stringparser.Parser(
                            alias if not setter_scpi else alias.lower()
                        ),
                        to_bytes(response_),
                        to_bytes(error),
                        setter_scpi,
                    )
                )

    def match(self, query: bytes) -> Optional[OptionalBytes]:
        """Try to find a match for a query in the instrument commands."""
        raise NotImplementedError()

    # --- Private API

    #: Stores the exact-match queries accepted by the device.
    #: query: response
    _dialogues: Dict[bytes, bytes | Literal[Responses.NO]]

    #: Stores SCPI-compliant query aliases accepted by the device.
    #: query: response
    _dialogues_scpi: Dict[bytes, bytes | Literal[Responses.NO]]

    #: Maps property names to value, type, validator
    _properties: Dict[str, Property]

    #: Stores the exact-match getter queries accepted by the device.
    #: query: (property_name, response)
    _getters: Dict[bytes, Tuple[str, str]]

    #: Stores the SCPI-compliant getter queries accepted by the device.
    #: query: (property_name, response)
    _getters_scpi: Dict[bytes, Tuple[str, str]]

    #: Stores the setters queries accepted by the device.
    #: (property_name, string parser query, response, error response, scpi)
    _setters: List[Tuple[str, stringparser.Parser, OptionalBytes, OptionalBytes, bool]]

    def _match_dialog(
        self,
        query: bytes,
        dialogues: Optional[Dict[bytes, bytes | Literal[Responses.NO]]] = None,
        scpi_dialogues: Optional[Dict[bytes, bytes | Literal[Responses.NO]]] = None,
    ) -> Optional[bytes | Literal[Responses.NO]]:
        """Tries to match in dialogues

        Parameters
        ----------
        query : bytes
            Query that we try to match to.
        dialogues : Optional[Dict[bytes, bytes | Literal[Responses.NO]]], optional
            Alternative dialogs to use when matching.

        Returns
        -------
        Optional[bytes]
            Response if a dialog matched.

        """
        if dialogues is None:
            dialogues = self._dialogues
        if scpi_dialogues is None:
            scpi_dialogues = self._dialogues_scpi

        # Try to match in the queries
        if query in dialogues:
            response = dialogues[query]
            logger.debug("Found response in queries: %s" % repr(response))

            if response is not NoResponse and b"RANDOM" in response:
                # Preserve raw bytes around text formatting directives.
                response = random_response(
                    response.decode("utf-8", errors="surrogateescape")
                ).encode("utf-8", errors="surrogateescape")

            return response

        try:
            normalized = _normalize_scpi_match(query)
        except (TypeError, ValueError):
            normalized = query

        if normalized in scpi_dialogues:
            response = scpi_dialogues[normalized]
            logger.debug("Found response in SCPI query: %r", response)

            if response is not NoResponse and b"RANDOM" in response:
                response = random_response(
                    response.decode("utf-8", errors="surrogateescape")
                ).encode("utf-8", errors="surrogateescape")

            return response

        return None

    def _match_getters(
        self,
        query: bytes,
        getters: Optional[Dict[bytes, Tuple[str, str]]] = None,
        scpi_getters: Optional[Dict[bytes, Tuple[str, str]]] = None,
    ) -> Optional[bytes]:
        """Tries to match in getters

        Parameters
        ----------
        query : bytes
            Query that we try to match to.
        getters : Optional[Dict[bytes, Tuple[str, str]]], optional
            Alternative getters to use when matching.
        scpi_getters : Optional[Dict[bytes, Tuple[str, str]]], optional
            Alternative SCPI getters to use when matching.

        Returns
        -------
        Optional[bytes]
            Response if a dialog matched.

        """
        if getters is None:
            getters = self._getters
        if scpi_getters is None:
            scpi_getters = self._getters_scpi

        if query in getters:
            name, response = getters[query]
            logger.debug("Found response in getter of %s" % name)

            if "RANDOM" in response:
                response = random_response(response)
            else:
                value = self._properties[name].get_value()
                response = response.format(value)

            return response.encode("utf-8")

        try:
            normalized = _normalize_scpi_match(query)
        except (TypeError, ValueError):
            normalized = query

        if normalized in scpi_getters:
            name, response = scpi_getters[normalized]
            logger.debug("Found response in SCPI getter of %s", name)

            if "RANDOM" in response:
                response = random_response(response)
            else:
                value = self._properties[name].get_value()
                response = response.format(value)

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
        try:
            q = query.decode("utf-8")
        except UnicodeDecodeError:
            # Setters use text patterns; binary commands may match a channel.
            return None
        for name, parser, response, error_response, scpi in self._setters:
            candidate = _normalize_scpi_match(q) if scpi else q
            try:
                value = parser(candidate)
                logger.debug("Found response in setter of %s", name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response
            except ValueError:
                if isinstance(error_response, bytes):
                    return error_response

        return None
