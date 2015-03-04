# -*- coding: utf-8 -*-
"""
    pyvisa-sim.devices
    ~~~~~~~~~~~~~~~~~~

    Classes to simulate devices.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""
from pyvisa.errors import VisaIOError, VisaIOWarning

try:
    import Queue as queue
except ImportError:
    import queue

import stringparser

from pyvisa import logger, constants 

from . import common


def to_bytes(val):
    """Takes a text message and return a tuple

    """
    if type(val) in (bytes, str):
        val = val.replace('\\r', '\r').replace('\\n', '\n')
        return val.encode()
    return val


class NoResponse(object):
    """Sentinel used for when there should not be a response to a query
    """

    
EVAL_GLOBALS = {'__builtins__': None}


EVAL_LOCALS = {
    'VI_WARN_QUEUE_OVERFLOW'       : constants.VI_WARN_QUEUE_OVERFLOW, 
    'VI_WARN_CONFIG_NLOADED'       : constants.VI_WARN_CONFIG_NLOADED, 
    'VI_WARN_NULL_OBJECT'          : constants.VI_WARN_NULL_OBJECT, 
    'VI_WARN_NSUP_ATTR_STATE'      : constants.VI_WARN_NSUP_ATTR_STATE, 
    'VI_WARN_UNKNOWN_STATUS'       : constants.VI_WARN_UNKNOWN_STATUS, 
    'VI_WARN_NSUP_BUF'             : constants.VI_WARN_NSUP_BUF, 

    # The following one is a non-standard NI extension
    'VI_WARN_EXT_FUNC_NIMPL'       : constants.VI_WARN_EXT_FUNC_NIMPL, 

    'VI_ERROR_SYSTEM_ERROR'        : constants.VI_ERROR_SYSTEM_ERROR, 
    'VI_ERROR_INV_OBJECT'          : constants.VI_ERROR_INV_OBJECT, 
    'VI_ERROR_RSRC_LOCKED'         : constants.VI_ERROR_RSRC_LOCKED, 
    'VI_ERROR_INV_EXPR'            : constants.VI_ERROR_INV_EXPR, 
    'VI_ERROR_RSRC_NFOUND'         : constants.VI_ERROR_RSRC_NFOUND, 
    'VI_ERROR_INV_RSRC_NAME'       : constants.VI_ERROR_INV_RSRC_NAME, 
    'VI_ERROR_INV_ACC_MODE'        : constants.VI_ERROR_INV_ACC_MODE, 
    'VI_ERROR_TMO'                 : constants.VI_ERROR_TMO, 
    'VI_ERROR_CLOSING_FAILED'      : constants.VI_ERROR_CLOSING_FAILED, 
    'VI_ERROR_INV_DEGREE'          : constants.VI_ERROR_INV_DEGREE, 
    'VI_ERROR_INV_JOB_ID'          : constants.VI_ERROR_INV_JOB_ID, 
    'VI_ERROR_NSUP_ATTR'           : constants.VI_ERROR_NSUP_ATTR, 
    'VI_ERROR_NSUP_ATTR_STATE'     : constants.VI_ERROR_NSUP_ATTR_STATE, 
    'VI_ERROR_ATTR_READONLY'       : constants.VI_ERROR_ATTR_READONLY, 
    'VI_ERROR_INV_LOCK_TYPE'       : constants.VI_ERROR_INV_LOCK_TYPE, 
    'VI_ERROR_INV_ACCESS_KEY'      : constants.VI_ERROR_INV_ACCESS_KEY, 
    'VI_ERROR_INV_EVENT'           : constants.VI_ERROR_INV_EVENT, 
    'VI_ERROR_INV_MECH'            : constants.VI_ERROR_INV_MECH, 
    'VI_ERROR_HNDLR_NINSTALLED'    : constants.VI_ERROR_HNDLR_NINSTALLED, 
    'VI_ERROR_INV_HNDLR_REF'       : constants.VI_ERROR_INV_HNDLR_REF, 
    'VI_ERROR_INV_CONTEXT'         : constants.VI_ERROR_INV_CONTEXT, 
    'VI_ERROR_QUEUE_OVERFLOW'      : constants.VI_ERROR_QUEUE_OVERFLOW, 
    'VI_ERROR_NENABLED'            : constants.VI_ERROR_NENABLED, 
    'VI_ERROR_ABORT'               : constants.VI_ERROR_ABORT, 
    'VI_ERROR_RAW_WR_PROT_VIOL'    : constants.VI_ERROR_RAW_WR_PROT_VIOL, 
    'VI_ERROR_RAW_RD_PROT_VIOL'    : constants.VI_ERROR_RAW_RD_PROT_VIOL, 
    'VI_ERROR_OUTP_PROT_VIOL'      : constants.VI_ERROR_OUTP_PROT_VIOL, 
    'VI_ERROR_INP_PROT_VIOL'       : constants.VI_ERROR_INP_PROT_VIOL, 
    'VI_ERROR_BERR'                : constants.VI_ERROR_BERR, 
    'VI_ERROR_IN_PROGRESS'         : constants.VI_ERROR_IN_PROGRESS, 
    'VI_ERROR_INV_SETUP'           : constants.VI_ERROR_INV_SETUP, 
    'VI_ERROR_QUEUE_ERROR'         : constants.VI_ERROR_QUEUE_ERROR, 
    'VI_ERROR_ALLOC'               : constants.VI_ERROR_ALLOC, 
    'VI_ERROR_INV_MASK'            : constants.VI_ERROR_INV_MASK, 
    'VI_ERROR_IO'                  : constants.VI_ERROR_IO, 
    'VI_ERROR_INV_FMT'             : constants.VI_ERROR_INV_FMT, 
    'VI_ERROR_NSUP_FMT'            : constants.VI_ERROR_NSUP_FMT, 
    'VI_ERROR_LINE_IN_USE'         : constants.VI_ERROR_LINE_IN_USE, 
    'VI_ERROR_NSUP_MODE'           : constants.VI_ERROR_NSUP_MODE, 
    'VI_ERROR_SRQ_NOCCURRED'       : constants.VI_ERROR_SRQ_NOCCURRED, 
    'VI_ERROR_INV_SPACE'           : constants.VI_ERROR_INV_SPACE, 
    'VI_ERROR_INV_OFFSET'          : constants.VI_ERROR_INV_OFFSET, 
    'VI_ERROR_INV_WIDTH'           : constants.VI_ERROR_INV_WIDTH, 
    'VI_ERROR_NSUP_OFFSET'         : constants.VI_ERROR_NSUP_OFFSET, 
    'VI_ERROR_NSUP_VAR_WIDTH'      : constants.VI_ERROR_NSUP_VAR_WIDTH, 
    'VI_ERROR_WINDOW_NMAPPED'      : constants.VI_ERROR_WINDOW_NMAPPED, 
    'VI_ERROR_RESP_PENDING'        : constants.VI_ERROR_RESP_PENDING, 
    'VI_ERROR_NLISTENERS'          : constants.VI_ERROR_NLISTENERS, 
    'VI_ERROR_NCIC'                : constants.VI_ERROR_NCIC, 
    'VI_ERROR_NSYS_CNTLR'          : constants.VI_ERROR_NSYS_CNTLR, 
    'VI_ERROR_NSUP_OPER'           : constants.VI_ERROR_NSUP_OPER, 
    'VI_ERROR_INTR_PENDING'        : constants.VI_ERROR_INTR_PENDING, 
    'VI_ERROR_ASRL_PARITY'         : constants.VI_ERROR_ASRL_PARITY, 
    'VI_ERROR_ASRL_FRAMING'        : constants.VI_ERROR_ASRL_FRAMING, 
    'VI_ERROR_ASRL_OVERRUN'        : constants.VI_ERROR_ASRL_OVERRUN, 
    'VI_ERROR_TRIG_NMAPPED'        : constants.VI_ERROR_TRIG_NMAPPED, 
    'VI_ERROR_NSUP_ALIGN_OFFSET'   : constants.VI_ERROR_NSUP_ALIGN_OFFSET, 
    'VI_ERROR_USER_BUF'            : constants.VI_ERROR_USER_BUF, 
    'VI_ERROR_RSRC_BUSY'           : constants.VI_ERROR_RSRC_BUSY, 
    'VI_ERROR_NSUP_WIDTH'          : constants.VI_ERROR_NSUP_WIDTH, 
    'VI_ERROR_INV_PARAMETER'       : constants.VI_ERROR_INV_PARAMETER, 
    'VI_ERROR_INV_PROT'            : constants.VI_ERROR_INV_PROT, 
    'VI_ERROR_INV_SIZE'            : constants.VI_ERROR_INV_SIZE, 
    'VI_ERROR_WINDOW_MAPPED'       : constants.VI_ERROR_WINDOW_MAPPED, 
    'VI_ERROR_NIMPL_OPER'          : constants.VI_ERROR_NIMPL_OPER, 
    'VI_ERROR_INV_LENGTH'          : constants.VI_ERROR_INV_LENGTH, 
    'VI_ERROR_INV_MODE'            : constants.VI_ERROR_INV_MODE, 
    'VI_ERROR_SESN_NLOCKED'        : constants.VI_ERROR_SESN_NLOCKED, 
    'VI_ERROR_MEM_NSHARED'         : constants.VI_ERROR_MEM_NSHARED, 
    'VI_ERROR_LIBRARY_NFOUND'      : constants.VI_ERROR_LIBRARY_NFOUND, 
    'VI_ERROR_NSUP_INTR'           : constants.VI_ERROR_NSUP_INTR, 
    'VI_ERROR_INV_LINE'            : constants.VI_ERROR_INV_LINE, 
    'VI_ERROR_FILE_ACCESS'         : constants.VI_ERROR_FILE_ACCESS, 
    'VI_ERROR_FILE_IO'             : constants.VI_ERROR_FILE_IO, 
    'VI_ERROR_NSUP_LINE'           : constants.VI_ERROR_NSUP_LINE, 
    'VI_ERROR_NSUP_MECH'           : constants.VI_ERROR_NSUP_MECH, 
    'VI_ERROR_INTF_NUM_NCONFIG'    : constants.VI_ERROR_INTF_NUM_NCONFIG, 
    'VI_ERROR_CONN_LOST'           : constants.VI_ERROR_CONN_LOST, 

    # The following two are a non-standard NI extensions
    'VI_ERROR_MACHINE_NAVAIL'      : constants.VI_ERROR_MACHINE_NAVAIL, 
    'VI_ERROR_NPERMISSION'         : constants.VI_ERROR_NPERMISSION, 
    'VisaIOError'                  : VisaIOError,
    'VisaIOWarning'                : VisaIOWarning,
}


class ErrorResponse(object):
    
    def __init__(self, error_input):
        exception_str = error_input.split('raise')[-1]
        self._exception = eval(exception_str, EVAL_GLOBALS, EVAL_LOCALS)
    
    def raise_exception(self):
        raise self._exception

    @classmethod
    def parse_error(cls, error_input):
        if type(error_input) is str:
            if 'raise' in error_input:
                return cls(error_input)
            elif 'null_response' in error_input:
                return NoResponse()
            return error_input
        else:
            return error_input


class Property(object):
    """A device property
    """

    _value = None

    def __init__(self, name, value, specs):
        """
        :param name: name of the property
        :param value: default value
        :param specs: specification dictionary
        :return:
        """

        t = specs.get('type', None)
        if t:
            for key, val in (('float', float), ('int', int), ('str', str)):
                if t == key:
                    t = specs['type'] = val
                    break

        for key in ('min', 'max'):
            if key in specs:
                specs[key] = t(specs[key])

        if 'valid' in specs:
            specs['valid'] = set([t(val) for val in specs['valid']])

        self.name = name
        self.specs = specs
        self.set_value(value)

    @property
    def value(self):
        return self._value

    def set_value(self, string_value):
        """Set the value
        """
        specs = self.specs
        if 'type' in specs:
            value = specs['type'](string_value)
        else:
            value = string_value
        if 'min' in specs and value < specs['min']:
            raise ValueError
        if 'max' in specs and value > specs['max']:
            raise ValueError
        if 'valid' in specs and value not in specs['valid']:
            raise ValueError
        self._value = value


class Device(object):
    """A representation of a responsive device

    :param name: The identification name of the device
    :type name: str
    :param name: fullpath of the device where it is defined.
    :type name: str
    """

    # To be bound when adding the Device to Devices
    _resource_name = None

    # Default end of message used in query operations
    # :type: bytes
    _query_eom = b''

    # Default end of message used in response operations
    # :type: bytes
    _response_eom = None

    def __init__(self, name, error_response):

        # Name of the device.
        self.name = name

        # :type: bytes
        self.error_response = {}
        for key, value in error_response.items():
            self.error_response[key] = to_bytes(value)

        #: Stores the specific end of messages for device.
        #: TYPE CLASS -> (query termination, response termination)
        #: :type: dict[(pyvisa.constants.InterfaceType, str), (str, str)]
        self._eoms = {}

        #: Stores the queries accepted by the device.
        #: query: (response, error response)
        #: :type: dict[bytes, bytes]
        self._dialogues = {}

        #: Maps property names to value, type, validator
        #: :type: dict[str, Property]
        self._properties = {}

        #: Stores the getter queries accepted by the device.
        #: query: (property_name, response)
        #: :type: dict[bytes, (str, str)]
        self._getters = {}

        #: Stores the setters queries accepted by the device.
        #: (property_name, string parser query, response, error response)
        #: :type: list[(str, stringparser.Parser, bytes, bytes)]
        self._setters = []

        #: Buffer in which the user can read
        #: :type: bytearray
        self._output_buffer = bytearray()

        #: Buffer in which the user can write
        #: :type: bytearray
        self._input_buffer = bytearray()

    @property
    def resource_name(self):
        """Assigned resource name
        """
        return self._resource_name

    @resource_name.setter
    def resource_name(self, value):
        p = common.parse_resource_name(value)
        self._resource_name = p['canonical_resource_name']
        self._query_eom, self._response_eom = self._eoms[(p['interface_type'],
                                                          p['resource_class'])]

    def add_dialogue(self, query, response):
        """Add dialogue to device.

        :param query: query string
        :param response: response string
        """
        self._dialogues[to_bytes(query)] = to_bytes(response)

    def add_property(self, name, default_value, getter_pair, setter_triplet, specs):
        """Add property to device

        :param name: property name
        :param default_value: default value as string
        :param getter_pair: (query, response)
        :param setter_triplet: (query, response, error)
        :param specs: specification of the Property
        """
        self._properties[name] = Property(name, default_value, specs)

        query, response = getter_pair
        self._getters[to_bytes(query)] = name, response

        query, response, error = setter_triplet
        self._setters.append((name,
                              stringparser.Parser(query),
                              to_bytes(response),
                              to_bytes(error)))

    def add_eom(self, type_class, query_termination, response_termination):
        """Add default end of message for a given interface type and resource class.

        :param type_class: interface type and resource class as strings joined by space
        :param query_termination: end of message used in queries.
        :param response_termination: end of message used in responses.
        """
        interface_type, resource_class = type_class.split(' ')
        interface_type = getattr(constants.InterfaceType, interface_type.lower())
        self._eoms[(interface_type, resource_class)] = (to_bytes(query_termination),
                                                        to_bytes(response_termination))

    def write(self, data):
        """Write data into the device input buffer.

        :param data: single element byte
        :type data: bytes
        """
        logger.debug('Writing into device input buffer: %r' % data)
        if not isinstance(data, bytes):
            raise TypeError('data must be an instance of bytes')

        if len(data) != 1:
            raise ValueError('data must have a length of 1, not %d' % len(data))

        self._input_buffer.extend(data)

        l = len(self._query_eom)
        if not self._input_buffer.endswith(self._query_eom):
            return

        query = bytes(self._input_buffer[:-l])
        response = self._match(query)
        eom = self._response_eom

        if response is None:
            response = self.error_response['invalid_write']

        if isinstance(response, NoResponse):
            self._output_buffer = bytearray()
        elif isinstance(response, ErrorResponse):
            response.raise_exception()
        else:
            self._output_buffer.extend(response)
            self._output_buffer.extend(eom)

        self._input_buffer = bytearray()

    def _match(self, query):
        """Tries to match in dialogues, getters and setters

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """

        # Try to match in the queries
        try:
            response = self._dialogues[query]
            logger.debug('Found response in queries: %s' % repr(response))

            return response

        except KeyError:
            pass

        # Now in the getters
        try:
            name, response = self._getters[query]
            logger.debug('Found response in getter of %s' % name)

            return response.format(self._properties[name].value).encode('utf-8')

        except KeyError:
            pass

        q = query.decode('utf-8')

        # Finally in the setters, this will be slow.
        for name, parser, response, err in self._setters:
            try:
                value = parser(q)
                logger.debug('Found response in setter of %s' % name)
            except ValueError:
                continue

            try:
                self._properties[name].set_value(value)
                return response

            except ValueError:
                return err

        return None

    def read(self):
        """Return a single byte from the output buffer
        """
        error_response = self.error_response.get('unexpected_read')
        if self._output_buffer:
            b, self._output_buffer = self._output_buffer[0:1], self._output_buffer[1:]
            return b
        elif isinstance(error_response, bytes):
            self._output_buffer.extend(error_response)
            self._output_buffer.extend(self._response_eom)
            b, self._output_buffer = self._output_buffer[0:1], self._output_buffer[1:]
            return b
        elif isinstance(error_response, ErrorResponse):
            error_response.raise_exception()

        return b''


class Devices(object):
    """The group of connected devices.
    """

    def __init__(self):

        #: Devices
        #: dict[str, Device]
        self._internal = {}

    def add_device(self, resource_name, device):
        """Bind device to resource name
        """

        if device.resource_name is not None:
            raise ValueError('The device %r is already assigned to %s' % (device, device.resource_name))

        device.resource_name = resource_name

        self._internal[device.resource_name] = device

    def __getitem__(self, item):
        return self._internal[item]

    def list_resources(self):
        """List resource names.

        :rtype: tuple[str]
        """
        return tuple(self._internal.keys())

