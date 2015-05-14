# -*- coding: utf-8 -*-
"""
    pyvisa-sim.parser
    ~~~~~~~~~~~~~~~~~

    Parser function

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

import os
from io import open, StringIO
from contextlib import closing
from traceback import format_exc

import pkg_resources
import yaml

from .devices import Devices, Device, NoResponse


def _ver_to_tuple(ver):
    return tuple(map(int, (ver.split("."))))


#: Version of the specification
SPEC_VERSION = '1.0'

SPEC_VERSION_TUPLE = _ver_to_tuple(SPEC_VERSION)


class SimpleChainmap(object):
    """Combine multiple mappings for sequential lookup.
    """

    def __init__(self, *maps):
        self._maps = maps

    def __getitem__(self, key):
        for mapping in self._maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)


def _s(s):
    """Strip white spaces
    """
    if s is NoResponse:
        return s

    return s.strip(' ')


def _get_pair(dd):
    """Return a pair from a dialogue dictionary.

    :param dd: Dialogue dictionary.
    :type dd: Dict[str, str]
    :return: (query, response)
    :rtype: (str, str)
    """
    return _s(dd['q']), _s(dd.get('r', NoResponse))


def _get_triplet(dd):
    """Return a triplet from a dialogue dictionary.

    :param dd: Dialogue dictionary.
    :type dd: Dict[str, str]
    :return: (query, response, error response)
    :rtype: (str, str | NoResponse, str | NoResponse)
    """
    return _s(dd['q']), _s(dd.get('r', NoResponse)), _s(dd.get('e', NoResponse))


def _load(content_or_fp):
    """YAML Parse a file or str and check version.
    """
    try:
        data = yaml.load(content_or_fp, Loader=yaml.loader.BaseLoader)
    except Exception as e:
        raise type(e)('Malformed yaml file:\n%r' % format_exc())

    try:
        ver = data['spec']
    except:
        raise ValueError('The file does not specify a spec version')

    try:
        ver = tuple(map(int, (ver.split("."))))
    except:
        raise ValueError("Invalid spec version format. Expect 'X.Y'"
                         " (X and Y integers), found %s" % ver)

    if ver > SPEC_VERSION_TUPLE:
        raise ValueError('The spec version of the file is '
                         '%s but the parser is %s. '
                         'Please update pyvisa-sim.' % (ver, SPEC_VERSION))

    return data


def parse_resource(name):
    """Parse a resource file
    """
    with closing(pkg_resources.resource_stream(__name__, name)) as fp:
        rbytes = fp.read()

    return _load(StringIO(rbytes.decode('utf-8')))


def parse_file(fullpath):
    """Parse a file
    """

    with open(fullpath, encoding='utf-8') as fp:
        return _load(fp)


def get_devices(filename, bundled):
    """Get a Devices object from a file.

    :param filename: full path of the file to parse or name of the resource.
    :param is_resource: boolean indicating if it is a resource.
    :rtype: Devices
    """

    loader = Loader(filename, bundled)

    data = loader.data

    devices = Devices()

    # Iterate through the resources and generate each individual device
    # on demand.

    for resource_name, resource_dict in data.get('resources', {}).items():
        device_name = resource_dict['device']

        dd = loader.get_device_dict(device_name,
                                    resource_dict.get('filename', None),
                                    resource_dict.get('bundled', False),
                                    required_version=SPEC_VERSION_TUPLE[0])

        devices.add_device(resource_name,
                           get_device(device_name, dd, loader))

    return devices


def get_device(name, device_dict, loader):
    """Get a device from a device dictionary.

    :param name: name of the device
    :param device_dict: device dictionary
    :rtype: Device
    """
    device = Device(name, device_dict.get('delimiter', ';'))
    
    err = device_dict.get('error', {})
    device.add_error_handler(err)

    bases = device_dict.get('bases', ())
    if bases:
        bases = (loader.get_device_dict(required_version=SPEC_VERSION_TUPLE[0], **b)
                 for b in bases)
        device_dict = SimpleChainmap(device_dict, *bases)

    for itype, eom_dict in device_dict.get('eom', {}).items():
        device.add_eom(itype, *_get_pair(eom_dict))

    for dia in device_dict.get('dialogues', ()):
        try:
            device.add_dialogue(*_get_pair(dia))
        except Exception as e:
            raise Exception('In device %s, malformed dialogue %s\n%r' % (name, dia, e))

    for prop_name, prop_dict in device_dict.get('properties', {}).items():
        try:
            getter = _get_pair(prop_dict['getter']) if 'getter' in prop_dict else None
            setter = _get_triplet(prop_dict['setter']) if 'setter' in prop_dict else None
            device.add_property(prop_name, prop_dict.get('default', ''),
                                getter, setter, prop_dict.get('specs', {}))
        except Exception as e:
            raise Exception('In device %s, malformed property %s\n%r' % (name, prop_name, e))

    return device


class Loader(object):

    def __init__(self, filename, bundled):

        # (absolute path / resource name / None, bundled) -> dict
        # :type: dict[str | None, bool, dict]
        self._cache = {}

        self.data = self._load(filename, bundled, SPEC_VERSION_TUPLE[0])

        self._filename = filename
        self._bundled = bundled
        self._basepath = os.path.dirname(filename)

    def load(self, filename, bundled, parent, required_version):

        if self._bundled and not bundled:
            msg = 'Only other bundled files can be loaded from bundled files.'
            raise ValueError(msg)

        if parent is None:
            parent = self._filename

        base = os.path.dirname(parent)

        filename = os.path.join(base, filename)

        return self._load(filename, bundled, required_version)

    def _load(self, filename, bundled, required_version):

        if (filename, bundled) in self._cache:
            return self._cache[(filename, bundled)]

        if bundled:
            data = parse_resource(filename)
        else:
            data = parse_file(filename)

        ver = _ver_to_tuple(data['spec'])[0]
        if ver != required_version:
            raise ValueError('Invalid version in %s (bundled = %s). '
                             'Expected %s, found %s,' % (filename, bundled,
                                                         required_version, ver)
                             )

        self._cache[(filename, bundled)] = data

        return data

    def get_device_dict(self, device, filename, bundled, required_version):

        if filename is None:
            data = self.data
        else:
            data = self.load(filename, bundled, required_version)

        return data['devices'][device]
