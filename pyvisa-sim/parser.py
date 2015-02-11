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

import pkg_resources
import yaml

from .devices import Devices, Device


#: Version of the specification
SPEC_VERSION = '1.0'


def _s(s):
    """Strip white spaces
    """
    return s.strip(' ')


def _get_pair(dd):
    """Return a pair from a dialogue dictionary.

    :param dd: Dialogue dictionary.
    :type dd: Dict[str, str]
    :return: (query, response)
    :rtype: (str, str)
    """
    return _s(dd['q']), _s(dd.get('r', ''))


def _get_triplet(dd, default_error):
    """Return a triplet from a dialogue dictionary.

    :param dd: Dialogue dictionary.
    :type dd: Dict[str, str]
    :param default_error: Default error response
    :type default_error: str
    :return: (query, response, error response)
    :rtype: (str, str, str)
    """
    return _s(dd['q']), _s(dd.get('r', '')), _s(dd.get('e', default_error))


def _load(content_or_fp):
    """YAML Parse a file or str and check version.
    """
    try:
        data = yaml.load(content_or_fp, Loader=yaml.loader.BaseLoader)
    except Exception as e:
        raise Exception('Malformed yaml file:\n%r' % e)

    if data['spec'] != SPEC_VERSION:
        raise ValueError('The spec version of the file is '
                         '%s but the loader is %s' % (data['spec'], SPEC_VERSION))

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


def get_devices(filename, is_resource):
    """Get a Devices object from a file.

    :param filename: full path of the file to parse or name of the resource.
    :param is_resource: boolean indicating if it is a resource.
    :rtype: Devices
    """

    if is_resource:
        data = parse_resource(filename)
    else:
        data = parse_file(filename)

    # Use to cache files that have been already read:
    # (name, is_resource) -> devices dict
    devices_in_file = {}

    devices = Devices()

    # Iterate through the resources and generate each individual device
    # on demand.

    for resource_name, resource_dict in data.get('resources', {}).items():
        device_name = resource_dict['device']

        new_filename = resource_dict.get('filename', None)
        new_is_resource = resource_dict.get('is_resource', False)

        if new_filename:
            # If the device definition should be loaded from another file
            if new_filename not in devices_in_file:
                if new_is_resource:
                    new_data = parse_resource(new_filename)
                else:
                    path = os.path.dirname(filename)
                    new_data = parse_file(os.path.join(path, os.path.normpath(new_filename)))

                devices_in_file[(new_filename, is_resource)] = new_data['devices']

            device_dict = devices_in_file[(new_filename, is_resource)][device_name]
        else:
            device_dict = data['devices'][device_name]

        devices.add_device(resource_name,
                           get_device(device_name, device_dict))

    return devices


def get_device(name, device_dict):
    """Get a device from a device dictionary.

    :param name: name of the device
    :param device_dict: device dictionary
    :rtype: Device
    """
    err = device_dict.get('error', '')

    device = Device(name, err)

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
            setter = _get_triplet(prop_dict['setter'], err) if 'setter' in prop_dict else None
            device.add_property(prop_name, prop_dict.get('default', ''),
                                getter, setter, prop_dict.get('specs', {}))
        except Exception as e:
            raise Exception('In device %s, malformed property %s\n%r' % (name, prop_name, e))

    return device
