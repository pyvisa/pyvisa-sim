# -*- coding: utf-8 -*-
"""
    pyvisa-sim.devices
    ~~~~~~~~~~~~~~~~~~

    Classes to simulate devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

import os
import pkg_resources
from io import open, StringIO
from contextlib import closing

from pyvisa.compat import string_types

try:
    import Queue as queue
except ImportError:
    import queue

from . import sessions

DEFAULT = tuple(r"""
@resource ASRL1
>>> *IDN?\n
<<< Very Big Corporation of America,Jet Propulsor,SIM42,4.2\n
@end

@resource USB::0x1234::125::A22-5
>>> *IDN?\n
<<< Very Big Corporation of America,Jet Propulsor,SIM42,4.2\n
@end

@resource TCPIP::localhost
>>> *IDN?\r\n<EOM4882>
<<< Very Big Corporation of America,Jet Propulsor,SIM42,4.2\r\n<EOM4882>
@end

@resource GPIB0::12
>>> *IDN?\n
<<< Very Big Corporation of America,Jet Propulsor,SIM42,4.2\n
@end
""".split('\n'))


def message_to_iterable(val):
    """
    :param val:
    :return:
    """
    val = val.replace('\\r', '\r').replace('\\n', '\n')
    if val.endswith('<EOM4882>'):
        return tuple(el.encode() for el in val.strip('<EOM4882>')) + (sessions.EOM4882, )
    else:
        return tuple(el.encode() for el in val)


class Device(object):
    """A representation of a responsive device

    :param resource_name: The resource name of the device.
    :type resource_name: str
    """

    def __init__(self, resource_name):
        self.resource_name = resource_name

        #: Stores the queries accepted by the device.
        #: dict[tuple[bytes], tuple[bytes])
        self._queries = {}

        #: Buffer in which the user can read
        #: queue.Queue[bytes]
        self._output_buffer = queue.Queue()

        #: Buffer in which the user can write
        #: [bytes]
        self._input_buffer = list()

    @classmethod
    def from_lines(cls, lines, normalizer):
        """Create device from an iterable of configuration lines.

        :param lines: configuration liens.
        :type lines: list[str]
        :param normalizer: a callable the converts a VISA resource name into its normalized version.
        :type normalizer: (str) -> str
        :return: a Device
        :rtype: Device
        """
        header, lines = lines[0], lines[1:]

        parts = [part for part in header.split(' ') if part]

        if len(parts) != 2:
            raise ValueError('Invalid header')

        res = cls(normalizer(parts[1]))

        ilines = iter(lines)
        for line in ilines:
            line = line.strip()

            # Ignore empty or comment lines
            if not line or line.startswith('#'):
                continue

            # Start a message to the device
            if line.startswith('>>>'):
                a = line[3:].strip(' ')

                line = next(ilines, '')

                while line.startswith('...'):
                    a += line[3:].strip(' ')

                # Start the response from the device
                if line.startswith('<<<'):
                    b = line[3:].strip(' ')

                    line = next(ilines, '')

                    while line.startswith('...'):
                        b += line[3:].strip(' ')
                else:
                    raise ValueError('No response found')
            else:
                raise ValueError('Text outside dialog')

            res._queries[message_to_iterable(a)] = message_to_iterable(b)

        return res

    def write(self, data):
        """Write data into the device input buffer.

        :param data: single element byte
        :type data: bytes
        """

        if not isinstance(data, bytes):
            raise TypeError('data must be an instance of bytes.')

        if len(data) !=1:
            raise ValueError('data must have a length of 1, not %d' % len(data))

        self._input_buffer.append(data)

        # After writing to the input buffer, tries to see if the query is in the
        # list of messages it understands and reply accordingly.
        try:
            answer = self._queries[tuple(self._input_buffer)]

            for part in answer:
                self._output_buffer.put(part)

            self._input_buffer.clear()
        except KeyError:
            pass

    def read(self):
        """Return a single byte from the output buffer
        """
        return self._output_buffer.get_nowait()


class Devices(object):
    """The group of connected devices.

    :param configuration: file or iterable of configuration.
    :param normalizer: a callable the converts a VISA resource name into its normalized version.
    :type normalizer: (str) -> str
    """

    def __init__(self, configuration, normalizer):

        #: Devices
        #: dict[str, Device]
        self._internal = {}
        self.normalizer = normalizer
        self.load_definitions(configuration)

    def add_device(self, device):
        """Add device.
        """
        self._internal[device.resource_name] = device

    def __getitem__(self, item):
        return self._internal[item]

    def list_resources(self):
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())

    def load_definitions(self, file, is_resource=False):
        """Load devices from a definition file or iterable of strings

        :param file: file or iterable of strings
        :param is_resource: indicates if the file is a resource deployed with the library.
        :return:
        """
        # Permit both filenames and line-iterables
        if isinstance(file, string_types):
            try:
                if is_resource:
                    with closing(pkg_resources.resource_stream(__name__, file)) as fp:
                        rbytes = fp.read()
                    return self.load_definitions(StringIO(rbytes.decode('utf-8')), is_resource)
                else:
                    with open(file, encoding='utf-8') as fp:
                        return self.load_definitions(fp, is_resource)
            except Exception as e:
                msg = getattr(e, 'message', '') or str(e)
                raise ValueError('While opening {0}\n{1}'.format(file, msg))

        ifile = enumerate(file, 1)
        for no, line in ifile:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('@import'):
                if is_resource:
                    path = line[7:].strip()
                else:
                    try:
                        path = os.path.dirname(file.name)
                    except AttributeError:
                        path = os.getcwd()
                    path = os.path.join(path, os.path.normpath(line[7:].strip()))
                self.load_definitions(path, is_resource)

            elif line.startswith('@resource'):
                lines = [line, ]
                for no, line in ifile:
                    line = line.strip()
                    if line.startswith('@end'):
                        try:
                            self.add_device(Device.from_lines(lines, self.normalizer))
                        except Exception as e:
                            raise ValueError('Invalid definition in line %d' % no)
                        break
                    elif line.startswith('@resource'):
                        raise ValueError('cannot nest @resource directives in line %d' % no)
                    lines.append(line)

            else:
                raise ValueError('Invalid resource definition. Definitions lines outside resources.')

