import socket
import unittest

from lab.modbus import DataStore, ModbusClient, ModbusError, ModbusServer


class ModbusRoundTrip(unittest.TestCase):
    def setUp(self):
        self.store = DataStore(co=20, di=20, hr=20, ir=20, unit_ids={1})
        self.store.di[3] = True
        self.store.ir[2] = 1234
        self.store.ir[3] = -2
        self.server = ModbusServer(self.store, "127.0.0.1", 0)
        self.server.start()
        self.port = self.server.server_address[1]
        self.c = ModbusClient("127.0.0.1", self.port, unit=1, timeout=0.5)

    def tearDown(self):
        self.c.close()
        self.server.shutdown()
        self.server.server_close()

    def test_reads(self):
        self.assertEqual(self.c.read_discrete_inputs(0, 5), [False, False, False, True, False])
        self.assertEqual(self.c.read_input(2, 2), [1234, 0xFFFE])

    def test_writes(self):
        self.c.write_coil(4, True)
        self.c.write_coils(10, [True, False, True])
        self.c.write_register(1, 42)
        self.c.write_registers(5, [1, 2, 0xFFFF])
        self.assertEqual(self.c.read_coils(9, 5), [False, True, False, True, False])
        self.assertTrue(self.store.co[4])
        self.assertEqual(self.store.hr[1], 42)
        self.assertEqual(self.store.hr[5:8], [1, 2, -1])
        self.assertEqual(self.c.read_holding(5, 3), [1, 2, 0xFFFF])

    def test_exceptions(self):
        with self.assertRaises(ModbusError):
            self.c.read_holding(19, 5)                  # past the end
        with self.assertRaises(ModbusError):
            self.c._call(bytes([0x2B, 0, 0]))          # unsupported function

    def test_wrong_unit_gets_no_reply(self):
        other = ModbusClient("127.0.0.1", self.port, unit=2, timeout=0.3)
        try:
            with self.assertRaises(socket.timeout):
                other.read_input(0, 1)
        finally:
            other.close()


if __name__ == "__main__":
    unittest.main()
