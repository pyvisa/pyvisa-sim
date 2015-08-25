# -*- coding: utf-8 -*-

from pyvisa.testsuite import BaseTestCase
from pyvisa.errors import VisaIOError
import visa


class TestAll(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.rm = visa.ResourceManager('@sim')

    def test_list(self):
        self.assertEqual(set(self.rm.list_resources('?*')),
                         set((
                          'ASRL1::INSTR',
                          'USB0::0x1111::0x2222::0x1234::0::INSTR',
                          'TCPIP0::localhost::inst0::INSTR',
                          'TCPIP0::localhost::10001::SOCKET',
                          'GPIB0::8::65535::INSTR',
                          'ASRL2::INSTR',
                          'USB0::0x1111::0x2222::0x2468::0::INSTR',
                          'TCPIP0::localhost:2222::inst0::INSTR',
                          'GPIB0::9::65535::INSTR',
                          'ASRL3::INSTR',
                          'USB0::0x1111::0x2222::0x3692::0::INSTR',
                          'TCPIP0::localhost:3333::inst0::INSTR',
                          'GPIB0::10::65535::INSTR',
                          'ASRL4::INSTR',
                          'USB0::0x1111::0x2222::0x4444::0::INSTR',
                          'TCPIP0::localhost:4444::inst0::INSTR',
                          'GPIB0::4::65535::INSTR',
                          'USB0::0x1111::0x2222::0x4445::0::RAW'
                         )))

    def test_devices(self):
        run_list = (
            'GPIB0::8::65535::INSTR',
            'TCPIP0::localhost::inst0::INSTR',
            'ASRL1::INSTR',
            'USB0::0x1111::0x2222::0x4445::0::RAW',
            'USB0::0x1111::0x2222::0x1234::0::INSTR',
            'TCPIP0::localhost::10001::SOCKET',
            )
        for rn in run_list:
            self._test_device(rn)

    def test_devices_2(self):
        run_list = (
            'ASRL2::INSTR',
            'USB0::0x1111::0x2222::0x2468::0::INSTR',
            'TCPIP0::localhost:2222::inst0::INSTR',
            'GPIB0::9::65535::INSTR',
            )
        for rn in run_list:
            self._test_device_2(rn)

    def test_devices_3(self):
        run_list = (
            'ASRL3::INSTR',
            'USB0::0x1111::0x2222::0x3692::0::INSTR',
            'TCPIP0::localhost:3333::inst0::INSTR',
            'GPIB0::10::65535::INSTR',
            )
        for rn in run_list:
            self._test_device_3(rn)

    def test_devices_timeouts(self):
        # Test timeout.
        run_list = (
                'ASRL3::INSTR',
                'USB0::0x1111::0x2222::0x3692::0::INSTR',
                'TCPIP0::localhost:3333::inst0::INSTR',
                'GPIB0::10::65535::INSTR',
                )
        for rn in run_list:
            self._test_devices_timeouts(rn)

    def test_devices_4(self):
        run_list = (
            'ASRL4::INSTR',
            'USB0::0x1111::0x2222::0x4444::0::INSTR',
            'TCPIP0::localhost:4444::inst0::INSTR',
            'GPIB0::4::INSTR',
            )
        for rn in run_list:
            self._test_devices_4(rn)

    def _test(self, inst, a, b):
        query = inst.query(a)
        self.assertEqual(query, b,
                         msg='%s, %r == %r' % (inst.resource_name, query, b))

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
        self._test(inst, '!AMP -1.0', 'ERROR')
        self._test(inst, '!AMP 11.0', 'ERROR')
        self._test(inst, '!FREQ 0.0', 'FREQ_ERROR')
        self._test(inst, 'BOGUS_COMMAND', 'ERROR')

        inst.close()

    def _test_device_2(self, resource_name):
        inst = self.rm.open_resource(
            resource_name,
            read_termination='\n',
            write_termination='\r\n' if resource_name.startswith('ASRL') else '\n'
            )

        inst.write('FAKE_COMMAND')
        status_reg = inst.query('*ESR?')
        self.assertEqual(int(status_reg), 32, 'invalid test command')

        inst.write(':VOLT:IMM:AMPL 2.00')
        status_reg = inst.query('*ESR?')
        self.assertEqual(int(status_reg), 0)

        inst.write(':VOLT:IMM:AMPL 0.5')
        status_reg = inst.query('*ESR?')
        self.assertEqual(int(status_reg), 32, 'invalid range test - <min')

        inst.write(':VOLT:IMM:AMPL 6.5')
        status_reg = inst.query('*ESR?')
        self.assertEqual(int(status_reg), 32, 'invalid range test - >max')

    def _test_device_3(self, resource_name):
        inst = self.rm.open_resource(
            resource_name,
            read_termination='\n',
            write_termination='\r\n' if resource_name.startswith('ASRL') else '\n'
            )

        response = inst.query('FAKE_COMMAND')
        self.assertEqual(response, 'INVALID_COMMAND',
                         'invalid command test - response')

        status_reg = inst.query('*ESR?')
        self.assertEqual(int(status_reg), 32, 'invalid command test - status')

    def _test_devices_timeouts(self, resource_name):
        inst = self.rm.open_resource(resource_name, timeout=0.1)
        self.assertRaises(VisaIOError, inst.read)

    def _test_devices_4(self, resource_name):
        inst = self.rm.open_resource(
            resource_name,
            read_termination='\n',
            write_termination='\r\n' if resource_name.startswith('ASRL') else '\n'
            )

        self._test(inst, ":SYST:ERR?", '0, No Error')
        inst.write("FAKE COMMAND")
        self._test(inst, ":SYST:ERR?", '1, Command error')
        inst.write(":VOLT:IMM:AMPL 0")
        self._test(inst, ":SYST:ERR?", '1, Command error')
