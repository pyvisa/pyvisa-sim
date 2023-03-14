# -*- coding: utf-8 -*-
"""Parser function

:copyright: 2014-2022 by PyVISA-sim Authors, see AUTHORS for more details.
:license: MIT, see LICENSE for more details.

"""
import importlib.resources
import os
import pathlib
from contextlib import closing
from io import StringIO, open
from traceback import format_exc
from typing import (
    Any,
    BinaryIO,
    Dict,
    Generic,
    Literal,
    Mapping,
    TextIO,
    Tuple,
    TypeVar,
    Union,
)

import yaml

from .channels import Channels
from .component import Component, NoResponse, Responses
from .devices import Device, Devices


def _ver_to_tuple(ver: str) -> Tuple[int, ...]:
    return tuple(map(int, (ver.split("."))))


#: Version of the specification
SPEC_VERSION = "1.1"

SPEC_VERSION_TUPLE = _ver_to_tuple(SPEC_VERSION)


# FIXME does not allow to alter an inherited dialogue, property, etc
K = TypeVar("K")
V = TypeVar("V")


class SimpleChainmap(Generic[K, V]):
    """Combine multiple mappings for sequential lookup."""

    def __init__(self, *maps: Mapping[K, V]) -> None:
        self._maps = maps

    def __getitem__(self, key: K) -> V:
        for mapping in self._maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)


def _get_pair(dd: Dict[str, str]) -> Tuple[str, str]:
    """Return a pair from a dialogue dictionary."""
    return dd["q"].strip(" "), dd["r"].strip(" ") if "r" in dd else NoResponse  # type: ignore[return-value]


def _get_triplet(
    dd: Dict[str, str]
) -> Tuple[str, Union[str, Literal[Responses.NO]], Union[str, Literal[Responses.NO]]]:
    """Return a triplet from a dialogue dictionary."""
    return (
        dd["q"].strip(" "),
        dd["r"].strip(" ") if "r" in dd else NoResponse,
        dd["e"].strip(" ") if "e" in dd else NoResponse,
    )


def _load(content_or_fp: Union[str, bytes, TextIO, BinaryIO]) -> Dict[str, Any]:
    """YAML Parse a file or str and check version."""
    try:
        data = yaml.load(content_or_fp, Loader=yaml.loader.BaseLoader)
    except Exception as e:
        raise type(e)("Malformed yaml file:\n%r" % format_exc())

    try:
        ver = data["spec"]
    except Exception as e:
        raise ValueError("The file does not specify a spec version") from e

    try:
        ver = tuple(map(int, (ver.split("."))))
    except Exception as e:
        raise ValueError(
            "Invalid spec version format. Expect 'X.Y'"
            " (X and Y integers), found %s" % ver
        ) from e

    if ver > SPEC_VERSION_TUPLE:
        raise ValueError(
            "The spec version of the file is "
            "%s but the parser is %s. "
            "Please update pyvisa-sim." % (ver, SPEC_VERSION)
        )

    return data


def parse_resource(name: str) -> Dict[str, Any]:
    """Parse a resource file."""
    with closing(importlib.resources.open_binary("pyvisa_sim", name)) as fp:
        rbytes = fp.read()

    return _load(StringIO(rbytes.decode("utf-8")))


def parse_file(fullpath: Union[str, pathlib.Path]) -> Dict[str, Any]:
    """Parse a file."""
    with open(fullpath, encoding="utf-8") as fp:
        return _load(fp)


def update_component(
    name: str, comp: Component, component_dict: Dict[str, Any]
) -> None:
    """Get a component from a component dict."""
    for dia in component_dict.get("dialogues", ()):
        try:
            comp.add_dialogue(*_get_pair(dia))
        except Exception as e:
            msg = "In device %s, malformed dialogue %s\n%r"
            raise Exception(msg % (name, dia, e))

    for prop_name, prop_dict in component_dict.get("properties", {}).items():
        try:
            getter = _get_pair(prop_dict["getter"]) if "getter" in prop_dict else None
            setter = (
                _get_triplet(prop_dict["setter"]) if "setter" in prop_dict else None
            )
            comp.add_property(
                prop_name,
                prop_dict.get("default", ""),
                getter,
                setter,
                prop_dict.get("specs", {}),
            )
        except Exception as e:
            msg = "In device %s, malformed property %s\n%r"
            raise type(e)(msg % (name, prop_name, format_exc()))


def get_bases(definition_dict: Dict[str, Any], loader: "Loader") -> Dict[str, Any]:
    """Collect inherited behaviors."""
    bases = definition_dict.get("bases", ())
    if bases:
        # FIXME this currently does not work
        raise NotImplementedError
        bases = (
            loader.get_comp_dict(required_version=SPEC_VERSION_TUPLE[0], **b)  # type: ignore
            for b in bases
        )
        return SimpleChainmap(definition_dict, *bases)
    else:
        return definition_dict


def get_channel(
    device: Device,
    ch_name: str,
    channel_dict: Dict[str, Any],
    loader: "Loader",
    resource_dict: Dict[str, Any],
) -> Channels:
    """Get a channels from a channels dictionary.

    Parameters
    ----------
    device : Device
        Device from which to retrieve a channel
    ch_name : str
        Name of the channel to access
    channel_dict : Dict[str, Any]
        Definition of the channel.
    loader : Loader
        Loader containing all the loaded information.
    resource_dict : Dict[str, Any]
        Dictionary describing the resource to which the device is attached.

    Returns
    -------
    Channels:
        Channels for the device.

    """
    cd = get_bases(channel_dict, loader)

    r_ids = resource_dict.get("channel_ids", {}).get(ch_name, [])
    ids = r_ids if r_ids else channel_dict.get("ids", {})

    can_select = False if channel_dict.get("can_select") == "False" else True
    channels = Channels(device, ids, can_select)

    update_component(ch_name, channels, cd)

    return channels


def get_device(
    name: str,
    device_dict: Dict[str, Any],
    loader: "Loader",
    resource_dict: Dict[str, str],
) -> Device:
    """Get a device from a device dictionary.

    Parameters
    ----------
    name : str
        Name identifying the device.
    device_dict : Dict[str, Any]
        Dictionary describing the device.
    loader : Loader
        Global loader centralizing all devices information.
    resource_dict : Dict[str, str]
        Resource information to which the device is attached.

    Returns
    -------
    Device
        Accessed device

    """
    device = Device(name, device_dict.get("delimiter", ";").encode("utf-8"))

    device_dict = get_bases(device_dict, loader)

    err = device_dict.get("error", {})
    device.add_error_handler(err)

    for itype, eom_dict in device_dict.get("eom", {}).items():
        device.add_eom(itype, *_get_pair(eom_dict))

    update_component(name, device, device_dict)

    for ch_name, ch_dict in device_dict.get("channels", {}).items():
        device.add_channels(
            ch_name, get_channel(device, ch_name, ch_dict, loader, resource_dict)
        )

    return device


class Loader:
    """Loader handling accessing the definitions in YAML files.

    Parameters
    ----------
    filename : Union[str, pathlib.Path]
        Path to the file to be loaded on creation.
    bundled : bool
        Is the file bundled with pyvisa-sim itself.

    """

    #: Definitions loaded from a YAML file.
    data: Dict[str, Any]

    def __init__(self, filename: Union[str, pathlib.Path], bundled: bool):
        self._cache = {}
        self._filename = filename
        self._bundled = bundled
        self.data = self._load(filename, bundled, SPEC_VERSION_TUPLE[0])

    def load(
        self,
        filename: Union[str, pathlib.Path],
        bundled: bool,
        parent: Union[str, pathlib.Path, None],
        required_version: int,
    ):
        """Load a new file into the loader.

        Parameters
        ----------
        filename : Union[str, pathlib.Path]
            Filename of the file to parse or name of the resource.
        bundled : bool
            Is the definition file bundled in pyvisa-sim.
        parent : Union[str, pathlib.Path, None]
            Path to directory in which the file can be found. If none the directory
            in which the initial file was located.
        required_version : int
            Major required version.

        """
        if self._bundled and not bundled:
            msg = "Only other bundled files can be loaded from bundled files."
            raise ValueError(msg)

        if parent is None:
            parent = self._filename

        base = os.path.dirname(parent)

        filename = os.path.join(base, filename)

        return self._load(filename, bundled, required_version)

    def get_device_dict(
        self,
        device: str,
        filename: Union[str, pathlib.Path, None],
        bundled: bool,
        required_version: int,
    ):
        """Access a device definition.

        Parameters
        ----------
        device : str
            Name of the device information to access.
        filename : Union[str, pathlib.Path]
            Filename of the file to parse or name of the resource.
            The file must be located in the same directory as the original file.
        bundled : bool
            Is the definition file bundled in pyvisa-sim.
        required_version : int
            Major required version.

        """
        if filename is None:
            data = self.data
        else:
            data = self.load(filename, bundled, None, required_version)

        return data["devices"][device]

    # --- Private API

    #: (absolute path / resource name / None, bundled) -> dict
    _cache: Dict[Tuple[Union[str, pathlib.Path, None], bool], Dict[str, str]]

    #: Path the first loaded file.
    _filename: Union[str, pathlib.Path]

    #: Is the loader working with bundled resources.
    _bundled: bool

    def _load(
        self, filename: Union[str, pathlib.Path], bundled: bool, required_version: int
    ) -> Dict[str, Any]:
        """Load a YAML definition file.

        The major version of the definition must match.

        """
        if (filename, bundled) in self._cache:
            return self._cache[(filename, bundled)]

        if bundled:
            assert isinstance(filename, str)
            data = parse_resource(filename)
        else:
            data = parse_file(filename)

        ver = _ver_to_tuple(data["spec"])[0]
        if ver != required_version:
            raise ValueError(
                "Invalid version in %s (bundled = %s). "
                "Expected %s, found %s," % (filename, bundled, required_version, ver)
            )

        self._cache[(filename, bundled)] = data

        return data


def get_devices(filename: Union[str, pathlib.Path], bundled: bool) -> Devices:
    """Get a Devices object from a file.

    Parameters
    ----------
    filename : Union[str, pathlib.Path]
        Full path of the file to parse or name of the resource.
    bundled : bool
        Is the definition file bundled in pyvisa-sim.

    Returns
    -------
    Devices
        Devices found in the definition file.

    """

    loader = Loader(filename, bundled)
    devices = Devices()

    # Iterate through the resources and generate each individual device
    # on demand.

    for resource_name, resource_dict in loader.data.get("resources", {}).items():
        device_name = resource_dict["device"]

        dd = loader.get_device_dict(
            device_name,
            resource_dict.get("filename", None),
            resource_dict.get("bundled", False),
            SPEC_VERSION_TUPLE[0],
        )

        devices.add_device(
            resource_name, get_device(device_name, dd, loader, resource_dict)
        )

    return devices
