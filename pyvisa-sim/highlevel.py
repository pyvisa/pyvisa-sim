# -*- coding: utf-8 -*-
"""
    pyvisa-sim.highlevel
    ~~~~~~~~~~~~~~~~~~~~

    Simulated VISA Library.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

from __future__ import division, unicode_literals, print_function, absolute_import

import random
from traceback import format_exc

from pyvisa import constants, highlevel, rname
import pyvisa.errors as errors
from pyvisa.compat import OrderedDict

from . import parser
from . import sessions

# This import is required to register subclasses
from . import gpib, serial, tcpip, usb


class SimVisaLibrary(highlevel.VisaLibraryBase):
    """A pure Python backend for PyVISA.

    The object is basically a dispatcher with some common functions implemented.

    When a new resource object is requested to pyvisa, the library creates a Session object
    (that knows how to perform low-level communication operations) associated with a session handle
    (a number, usually refered just as session).

    A call to a library function is handled by PyVisaLibrary if it involves a resource agnostic
    function or dispatched to the correct session object (obtained from the session id).

    Importantly, the user is unaware of this. PyVisaLibrary behaves for the user just as NIVisaLibrary.
    """

    @staticmethod
    def get_debug_info():
        """Return a list of lines with backend info.
        """
        from . import __version__
        from .parser import SPEC_VERSION
        d = OrderedDict()
        d['Version'] = '%s' % __version__
        d['Spec version'] = SPEC_VERSION

        return d

    def _init(self):

        #: map session handle to session object.
        #: dict[int, SessionSim]
        self.sessions = {}

        try:
            if self.library_path == 'unset':
                self.devices = parser.get_devices('default.yaml', True)
            else:
                self.devices = parser.get_devices(self.library_path, False)
        except Exception as e:
            msg = 'Could not parse definitions file. %r'
            raise type(e)(msg % format_exc())

    def _register(self, obj):
        """Creates a random but unique session handle for a session object,
        register it in the sessions dictionary and return the value

        :param obj: a session object.
        :return: session handle
        :rtype: int
        """
        session = None

        while session is None or session in self.sessions:
            session = random.randint(1000000, 9999999)

        self.sessions[session] = obj
        return session

    # noinspection PyShadowingBuiltins
    def open(self, session, resource_name,
             access_mode=constants.AccessModes.no_lock, open_timeout=constants.VI_TMO_IMMEDIATE):
        """Opens a session to the specified resource.

        Corresponds to viOpen function of the VISA library.

        :param session: Resource Manager session
                        (should always be a session returned
                        from open_default_resource_manager()).
        :param resource_name: Unique symbolic name of a resource.
        :param access_mode: Specifies the mode by which the resource is to be accessed. (constants.AccessModes)
        :param open_timeout: Specifies the maximum time period (in milliseconds) that this operation waits
                             before returning an error.
        :return: Unique logical identifier reference to a session, return value of the library call.
        :rtype: session, :class:`pyvisa.constants.StatusCode`
        """

        try:
            open_timeout = int(open_timeout)
        except ValueError:
            raise ValueError('open_timeout (%r) must be an integer (or compatible type)' % open_timeout)

        try:
            parsed = rname.parse_resource_name(resource_name)
        except rname.InvalidResourceName:
            return 0, constants.StatusCode.error_invalid_resource_name

        # Loops through all session types, tries to parse the resource name and if ok, open it.
        cls = sessions.Session.get_session_class(parsed.interface_type_const, parsed.resource_class)

        sess = cls(session, resource_name, parsed)

        try:
            sess.device = self.devices[sess.attrs[constants.VI_ATTR_RSRC_NAME]]
        except KeyError:
            return 0, constants.StatusCode.error_resource_not_found

        return self._register(sess), constants.StatusCode.success

    def close(self, session):
        """Closes the specified session, event, or find list.

        Corresponds to viClose function of the VISA library.

        :param session: Unique logical identifier to a session, event, or find list.
        :return: return value of the library call.
        :rtype: :class:`pyvisa.constants.StatusCode`
        """
        try:
            del self.sessions[session]
            return constants.StatusCode.success
        except KeyError:
            return constants.StatusCode.error_invalid_object

    def open_default_resource_manager(self):
        """This function returns a session to the Default Resource Manager resource.

        Corresponds to viOpenDefaultRM function of the VISA library.

        :return: Unique logical identifier to a Default Resource Manager session, return value of the library call.
        :rtype: session, :class:`pyvisa.constants.StatusCode`
        """
        return self._register(self), constants.StatusCode.success

    def list_resources(self, session, query='?*::INSTR'):
        """Returns a tuple of all connected devices matching query.

        :param query: regular expression used to match devices.
        """

        # For each session type, ask for the list of connected resources and merge them into a single list.

        resources = self.devices.list_resources()

        resources = rname.filter(resources, query)

        if resources:
            return resources

        raise errors.VisaIOError(errors.StatusCode.error_resource_not_found.value)

    def read(self, session, count):
        """Reads data from device or interface synchronously.

        Corresponds to viRead function of the VISA library.

        :param session: Unique logical identifier to a session.
        :param count: Number of bytes to be read.
        :return: data read, return value of the library call.
        :rtype: bytes, :class:`pyvisa.constants.StatusCode`
        """

        try:
            sess = self.sessions[session]
        except KeyError:
            return b'', constants.StatusCode.error_invalid_object

        try:
            chunk, status = sess.read(count)
            if status == constants.StatusCode.error_timeout:
                raise errors.VisaIOError(constants.VI_ERROR_TMO)
            return chunk, status
        except AttributeError:
            return b'', constants.StatusCode.error_nonsupported_operation

    def write(self, session, data):
        """Writes data to device or interface synchronously.

        Corresponds to viWrite function of the VISA library.

        :param session: Unique logical identifier to a session.
        :param data: data to be written.
        :type data: str
        :return: Number of bytes actually transferred, return value of the library call.
        :rtype: int, :class:`pyvisa.constants.StatusCode`
        """

        try:
            sess = self.sessions[session]
        except KeyError:
            return constants.StatusCode.error_invalid_object

        try:
            return sess.write(data)
        except AttributeError:
            return constants.StatusCode.error_nonsupported_operation

    def get_attribute(self, session, attribute):
        """Retrieves the state of an attribute.

        Corresponds to viGetAttribute function of the VISA library.

        :param session: Unique logical identifier to a session, event, or find list.
        :param attribute: Resource attribute for which the state query is made (see Attributes.*)
        :return: The state of the queried attribute for a specified resource, return value of the library call.
        :rtype: unicode (Py2) or str (Py3), list or other type, :class:`pyvisa.constants.StatusCode`
        """
        try:
            sess = self.sessions[session]
        except KeyError:
            return 0, constants.StatusCode.error_invalid_object

        return sess.get_attribute(attribute)

    def set_attribute(self, session, attribute, attribute_state):
        """Sets the state of an attribute.

        Corresponds to viSetAttribute function of the VISA library.

        :param session: Unique logical identifier to a session.
        :param attribute: Attribute for which the state is to be modified. (Attributes.*)
        :param attribute_state: The state of the attribute to be set for the specified object.
        :return: return value of the library call.
        :rtype: :class:`pyvisa.constants.StatusCode`
        """

        try:
            sess = self.sessions[session]
        except KeyError:
            return constants.StatusCode.error_invalid_object

        return sess.set_attribute(attribute, attribute_state)

    def disable_event(self, session, event_type, mechanism):
        # TODO: implement this for GPIB finalization
        pass

    def discard_events(self, session, event_type, mechanism):
        # TODO: implement this for GPIB finalization
        pass
