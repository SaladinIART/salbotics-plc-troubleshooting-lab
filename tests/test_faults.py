"""One test class per lab fault: symptom, what the PLC shows, fix, finished batch."""

import unittest

from lab.iomap import IR, MW, MW_BASE, MW_COUNT
from lab.modbus import DataStore, ModbusClient, ModbusServer
from tests.helpers import (R1, alarm1, alarm2, co, di, finish, feeding, new_rig,
                           reset_and_resume, start, tol)


def assert_batch_good(tc, rig, batches=1):
    tc.assertEqual(rig.plc.mw[MW["BatchesDone"]], batches)
    for i, target in enumerate(R1, start=1):
        tc.assertLessEqual(abs(rig.plc.ActualKg[i] - target), tol(target), f"silo {i}")
    p = rig.plant
    tc.assertAlmostEqual(p.discharged_kg + p.spill_kg, p.dispensed_kg, delta=0.5)


class F1SensorLoopBroken(unittest.TestCase):
    def test(self):
        rig = new_rig()
        start(rig)
        rig.run_until(feeding(rig, 3))
        rig.run(4)
        rig.plant.set_fault("F1")
        rig.run(0.3)
        # symptom
        self.assertEqual(rig.plc.State, 100)
        self.assertTrue(alarm1(rig, 12))
        self.assertTrue(alarm2(rig, 12))                  # silo 3 signal fault
        # what the online program shows
        self.assertEqual(rig.plc.ir[IR["Weight3"]], 0)
        self.assertLess(rig.plc.mw[MW["Weight3"]], -4900)
        rig.run(3)
        self.assertEqual(rig.plant.gates[2].pos, 0.0)
        # reset without repair does not clear it
        rig.cmd(5)
        rig.run(2)
        self.assertTrue(alarm1(rig, 12))
        # fix
        rig.plant.set_fault("F1", False)
        reset_and_resume(rig)
        finish(rig)
        assert_batch_good(self, rig)


class F2NodeAddressWrong(unittest.TestCase):
    def test(self):
        rig = new_rig()
        start(rig)
        rig.run_until(feeding(rig, 1))
        rig.run(5)
        hb = rig.plc.ir[IR["Heartbeat"]]
        rig.plant.set_fault("F2")
        rig.run(1.5)
        self.assertFalse(rig.plant.comm_ok)               # rack watchdog cleared its outputs
        self.assertEqual(rig.plc.ir[IR["Heartbeat"]], hb)  # PLC sees a frozen heartbeat
        rig.run(1.5)
        self.assertEqual(rig.plc.State, 100)
        self.assertTrue(alarm1(rig, 1))
        rig.run(5)
        self.assertEqual(rig.plant.c1.freq, 0.0)
        self.assertTrue(all(g.pos == 0.0 for g in rig.plant.gates))
        rig.plant.set_fault("F2", False)
        rig.run(1)
        self.assertNotEqual(rig.plc.ir[IR["Heartbeat"]], hb)
        reset_and_resume(rig)
        finish(rig)
        assert_batch_good(self, rig)


class F3ConveyorOverload(unittest.TestCase):
    def test(self):
        rig = new_rig()
        rig.plant.set_fault("F3")
        start(rig)
        rig.run_until(feeding(rig, 1))                    # empty belt ran: no trip yet
        self.assertFalse(rig.plant.c1.tripped)
        self.assertGreater(rig.plant.c1.current, 19.0)    # but it already draws 20 A empty
        rig.run_until(lambda r: r.plc.State == 100, 120)
        self.assertTrue(alarm1(rig, 2))
        self.assertEqual(rig.plc.ir[IR["C1_FaultCode"]], 2)
        self.assertTrue(di(rig, "C1_Fault"))
        self.assertEqual(rig.plc.ResumeState, 60)
        rig.run(8)
        self.assertTrue(all(g.pos == 0.0 for g in rig.plant.gates))
        self.assertGreater(rig.plant.c2.freq, 0.0)        # C2 runs on to empty
        rig.run(60)
        self.assertEqual(rig.plant.c2.freq, 0.0)
        # reset without fixing: it runs, then trips again under load
        reset_and_resume(rig)
        rig.run_until(lambda r: r.plc.State == 100, 120)
        self.assertTrue(alarm1(rig, 2))
        rig.run(60)
        rig.plant.set_fault("F3", False)
        reset_and_resume(rig)
        finish(rig)
        assert_batch_good(self, rig)


class F4GateJammed(unittest.TestCase):
    def test(self):
        rig = new_rig()
        rig.plant.set_fault("F4")
        start(rig)
        rig.run_until(lambda r: r.plc.State == 100)
        self.assertEqual(rig.plc.Silo, 4)
        self.assertTrue(alarm1(rig, 9))
        self.assertTrue(alarm2(rig, 8))                   # gate 4
        self.assertEqual(rig.plc.ir[IR["GateAlarm4"]], 1)
        self.assertTrue(rig.plc.ir[IR["GateStatus4"]] & 0x0008)
        self.assertFalse(rig.plc.ir[IR["GateStatus4"]] & 0x0002)
        self.assertLessEqual(rig.plant.gates[3].pos, 20.0)
        rig.run(60)
        rig.plant.set_fault("F4", False)
        before = len(rig.trace)
        reset_and_resume(rig)
        finish(rig)
        self.assertIn(12, [s for _, s in rig.trace[before:]])  # gates re-homed first
        assert_batch_good(self, rig)


class F5DoorSolenoidWire(unittest.TestCase):
    def test(self):
        rig = new_rig()
        rig.plant.set_fault("F5")
        start(rig)
        rig.run_until(lambda r: r.plc.State == 90)
        rig.run(5)
        self.assertTrue(co(rig, "Door_OpenSol"))          # output on
        self.assertFalse(di(rig, "Door_Open"))            # device not moving
        self.assertTrue(di(rig, "Door_Closed"))
        rig.run(6)
        self.assertEqual(rig.plc.State, 100)
        self.assertTrue(alarm1(rig, 7))
        self.assertTrue(rig.plant.mixer_running)          # batch kept turning in the mixer
        self.assertGreater(rig.plant.mixer_kg, 1900)
        rig.plant.set_fault("F5", False)
        reset_and_resume(rig)
        finish(rig)
        assert_batch_good(self, rig)


class F6BadProgramEdit(unittest.TestCase):
    def test(self):
        rig = new_rig(f6_bad_edit=True)
        start(rig)
        finish(rig)
        mw = rig.plc.mw
        self.assertEqual(mw[MW["Alarm1"]], 0)             # no alarm at all
        self.assertEqual(mw[MW["R1_B"]], 500)
        self.assertEqual(mw[MW["Target2"]], 800)          # recipe says 500
        self.assertLessEqual(abs(rig.plc.ActualKg[2] - 800), tol(800))


class F7HmiTagOffByOne(unittest.TestCase):
    def test(self):
        rig = new_rig()
        store = DataStore(hr=MW_BASE + MW_COUNT)
        server = ModbusServer(store, "127.0.0.1", 0)
        server.start()
        client = ModbusClient("127.0.0.1", server.server_address[1])
        try:
            def sync():
                with store.lock:
                    store.hr[MW_BASE:MW_BASE + MW_COUNT] = rig.plc.mw
            start(rig)
            rig.run_until(feeding(rig, 5))
            sync()
            right = MW_BASE + MW["Weight4"]           # 1047
            wrong = right + 1                         # 1048: the F7 tag
            a = client.read_holding(right, 1)[0]
            b = client.read_holding(wrong, 1)[0]
            rig.run(5)
            sync()
            a2 = client.read_holding(right, 1)[0]
            b2 = client.read_holding(wrong, 1)[0]
            self.assertEqual(a, a2)                   # silo 4 really steady
            self.assertLess(b2, b)                    # the wrong tag "shows silo 4 dropping"
            self.assertEqual(b2, rig.plc.mw[MW["Weight5"]])
        finally:
            client.close()
            server.shutdown()
            server.server_close()


class InstructorPanel(unittest.TestCase):
    """Faults switched over Modbus unit 99, as tools/instructor.py does."""

    def test_coils_switch_faults_and_unit_99_keeps_working_during_f2(self):
        from lab.iomap import INSTRUCTOR_FAULT_COILS, INSTRUCTOR_UNIT
        rig = new_rig()
        server = ModbusServer(rig.plant.store, "127.0.0.1", 0)
        server.start()
        c = ModbusClient("127.0.0.1", server.server_address[1], unit=INSTRUCTOR_UNIT, timeout=1)
        try:
            c.write_coil(INSTRUCTOR_FAULT_COILS["F2"], True)
            rig.run(0.2)
            self.assertIn("F2", rig.plant.faults)
            rig.run(3)                                    # instructor traffic must not feed the watchdog
            c.read_coils(32, 5)
            rig.run(0.5)
            self.assertTrue(alarm1(rig, 1))               # comms lost, as with the console
            c.write_coil(INSTRUCTOR_FAULT_COILS["F2"], False)   # still reachable on unit 99
            rig.run(1)
            self.assertNotIn("F2", rig.plant.faults)
            rig.plant.set_fault("F3")                     # console and panel stay in step
            self.assertEqual(c.read_coils(INSTRUCTOR_FAULT_COILS["F3"], 1), [True])
        finally:
            c.close()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
