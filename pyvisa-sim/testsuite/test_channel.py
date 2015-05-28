# -*- coding: utf-8 -*-

import os

from pyvisa.testsuite import BaseTestCase
import visa

PACKAGE = os.path.dirname(__file__)


class TestChannels(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        path = os.path.join(PACKAGE, 'channels.yaml')
        cls.rm = visa.ResourceManager(path+'@sim')

    def test_device_with_channel_preselection(self):
        run_list = (
            'GPIB0::8::65535::INSTR',
            'TCPIP0::localhost:1111::inst0::INSTR',
            'ASRL1::INSTR',
            'USB0::0x1111::0x2222::0x1234::0::INSTR'
            )
        for rn in run_list:
            self._test_device_with_channel_preselection(rn)

    def test_device_with_inline_selection(self):
        run_list = (
            'ASRL2::INSTR',
            'USB0::0x1111::0x2222::0x2468::0::INSTR',
            'TCPIP0::localhost:2222::inst0::INSTR',
            'GPIB0::9::65535::INSTR',
            )
        for rn in run_list:
            self._test_device_with_inline_selection(rn)

    def _test(self, inst, a, b):
        query = inst.query(a)
        self.assertEqual(query, b,
                         msg=inst.resource_name + ', %r == %r' % (query, b))

    def _test_device_with_channel_preselection(self, resource_name):
        inst = self.rm.open_resource(resource_name, read_termination='\n',
                                     write_termination='\r\n' if resource_name.startswith('ASRL') else '\n')
        self._test(inst, 'I?', '1')

        self._test(inst, 'F?', '1.000')
        inst.write('F 5.0')
        self._test(inst, 'F?', '5.000')
        self._test(inst, 'I 2;F?', '1.000')

        inst.close()

    def _test_device_with_inline_selection(self, resource_name):
        inst = self.rm.open_resource(
            resource_name,
            read_termination='\n',
            write_termination='\r\n' if resource_name.startswith('ASRL') else '\n'
            )

        self._test(inst, "CH 1:VOLT:IMM:AMPL?", '+1.00000000E+00')
        inst.write("CH 1:VOLT:IMM:AMPL 2.0")
        self._test(inst, "CH 1:VOLT:IMM:AMPL?", '+2.00000000E+00')
        self._test(inst, "CH 2:VOLT:IMM:AMPL?", '+1.00000000E+00')
