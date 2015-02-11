# -*- coding: utf-8 -*-

from pyvisa.testsuite import BaseTestCase
import visa


class TestAll(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.rm = visa.ResourceManager('@sim')

    def test_list(self):
        self.assertEqual(set(self.rm.list_resources()),
                         set(('GPIB0::8::65535::INSTR',
                              'TCPIP0::localhost::inst0::INSTR',
                              'ASRL1::INSTR',
                              'USB0::0x1111::0x2222::0x1234::0::INSTR')))
    def test_devices(self):
        for rn in self.rm.list_resources():
            self._test_device(rn)

    def _test(self, inst, a, b):
        self.assertEqual(inst.query(a), b, msg=inst.resource_name + ', %r == %r' % (a, b))

    def _test_device(self, resource_name):
        inst = self.rm.open_resource(resource_name, read_termination='\n',
                                     write_termination='\r\n' if resource_name.startswith('ASRL') else '\n')
        self._test(inst, '?IDN', 'LSG Serial #1234')

        self._test(inst, '?FREQ', '100.00')
        self._test(inst, '!FREQ 10.3', 'OK')
        self._test(inst, '?FREQ', '10.30')

        self._test(inst, '?AMP', '1.00')
        self._test(inst, '!AMP 3.8', 'OK')
        self._test(inst, '?AMP', '3.80')

        self._test(inst, '?OFF', '0.00')
        self._test(inst, '!OFF 1.2', 'OK')
        self._test(inst, '?OFF', '1.20')

        self._test(inst, '?OUT', '0')
        self._test(inst, '!OUT 1', 'OK')
        self._test(inst, '?OUT', '1')

        self._test(inst, '?WVF', '0')
        self._test(inst, '!WVF 1', 'OK')
        self._test(inst, '?WVF', '1')

        self._test(inst, '!CAL', 'OK')

        # Errors

        self._test(inst, '!WVF 23', 'ERROR')

        inst.close()

