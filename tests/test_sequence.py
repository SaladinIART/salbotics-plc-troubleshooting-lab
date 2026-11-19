import unittest

from lab.iomap import MW
from tests.helpers import (FULL_PATH, R1, alarm1, alarm2, co, di, finish, feeding, new_rig,
                           start, tol)


class FullBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig = rig = new_rig()
        cls.c1_before_c2_ok = False
        cls.c2_stopped_before_c1 = False
        cls.gate_on_stopped_belt = False
        start(rig)
        while True:
            rig.tick()
            p = rig.plant
            if co(rig, "C1_RunCmd") and not di(rig, "C2_SpeedOK"):
                cls.c1_before_c2_ok = True
            if co(rig, "C1_RunCmd") and not co(rig, "C2_RunCmd"):
                cls.c2_stopped_before_c1 = True
            if any(g.pos > 0 for g in p.gates) and p.c1.speed < 0.3 * 1.5:
                cls.gate_on_stopped_belt = True
            if rig.plc.State == 0:
                break

    def test_state_order(self):
        self.assertEqual(self.rig.state_path(), FULL_PATH)

    def test_every_material_in_tolerance(self):
        for i, target in enumerate(R1, start=1):
            actual = self.rig.plc.ActualKg[i]
            self.assertLessEqual(abs(actual - target), tol(target), f"silo {i}: {actual:.1f} kg")

    def test_mass_balance_and_nothing_on_the_floor(self):
        p = self.rig.plant
        self.assertAlmostEqual(p.discharged_kg, p.dispensed_kg, delta=0.5)
        self.assertEqual(p.spill_kg, 0.0)
        self.assertEqual(p.pile_kg, 0.0)
        self.assertLess(p.mixer_kg + p.c1.load + p.c2.load, 0.5)

    def test_belts_start_downstream_first_and_stop_upstream_first(self):
        self.assertFalse(self.c1_before_c2_ok)
        self.assertFalse(self.c2_stopped_before_c1)

    def test_no_gate_open_over_a_stopped_belt(self):
        self.assertFalse(self.gate_on_stopped_belt)

    def test_no_alarms_and_counters(self):
        mw = self.rig.plc.mw
        self.assertEqual(mw[MW["Alarm1"]], 0)
        self.assertEqual(mw[MW["Alarm2"]], 0)
        self.assertEqual(mw[MW["BatchesDone"]], 1)


class Learning(unittest.TestCase):
    def test_inflight_learns_and_errors_shrink(self):
        rig = new_rig()
        rig.plc.set_hmi("BatchReq", 4)
        errors = []
        start(rig)
        done = 0
        while done < 4:
            rig.run_until(lambda r: r.plc.State == 70)
            errors.append([rig.plc.ActualKg[i] - R1[i - 1] for i in range(1, 6)])
            rig.run_until(lambda r: r.plc.State in (0, 5))
            done += 1
        for i in range(5):
            self.assertLessEqual(abs(errors[-1][i]), abs(errors[0][i]) + 0.01, errors)
            self.assertLessEqual(abs(errors[-1][i]), 2.0, errors)
        self.assertEqual(rig.plc.mw[MW["BatchesDone"]], 4)


class Modes(unittest.TestCase):
    def test_semi_auto_waits_for_next(self):
        rig = new_rig()
        rig.mode(2)
        self.assertEqual(rig.plc.Mode, 2)
        start(rig)
        rig.run_until(lambda r: r.plc.State == 50)
        rig.run(30)
        self.assertEqual(rig.plc.State, 50)
        self.assertTrue(rig.plc.mw[MW["Status"]] & 0x0004)  # waiting for Next
        presses = 0
        while rig.plc.State != 0:
            if rig.plc.mw[MW["Status"]] & 0x0004:
                rig.cmd(6)
                presses += 1
            rig.tick()
        self.assertEqual(presses, 6)  # five silos and the door
        self.assertAlmostEqual(rig.plant.discharged_kg, rig.plant.dispensed_kg, delta=0.5)

    def test_mode_changes_only_when_idle(self):
        rig = new_rig()
        start(rig)
        rig.run(5)
        rig.mode(1)
        self.assertEqual(rig.plc.Mode, 3)
        self.assertEqual(rig.plc.mw[MW["ModeReq"]], 0)

    def test_manual_interlocks(self):
        rig = new_rig()
        rig.mode(1)
        rig.plc.set_hmi("ManualBits", 0x0002)          # C1 alone
        rig.run(3)
        self.assertFalse(co(rig, "C1_RunCmd"))
        rig.plc.set_hmi("ManualBits", 0x0001 | 0x0010)  # C2 + home gates
        rig.run(5)
        self.assertTrue(di(rig, "C2_SpeedOK"))
        self.assertTrue(all(g.homed for g in rig.plant.gates))
        rig.plc.set_hmi("ManGateSP1", 500)
        rig.run(2)
        self.assertEqual(rig.plant.gates[0].pos, 0.0)  # C1 not running: gate held shut
        rig.plc.set_hmi("ManualBits", 0x0001 | 0x0002)
        rig.run(5)
        self.assertTrue(co(rig, "C1_RunCmd"))
        self.assertAlmostEqual(rig.plant.gates[0].pos, 500.0, delta=1)
        rig.plc.set_hmi("ManualBits", 0x0001)          # stop C1: gate must close
        rig.run(3)
        self.assertEqual(rig.plant.gates[0].pos, 0.0)
        self.assertEqual(rig.plant.spill_kg, 0.0)


class Warnings(unittest.TestCase):
    def test_low_level_lamp_steady_and_sounder_until_ack(self):
        rig = new_rig(silo_kg=(15000, 12000, 9000, 6000, 2050))
        start(rig)
        rig.run_until(lambda r: r.plc.LowSilo[5])
        rig.run(1)
        self.assertTrue(alarm2(rig, 4))
        self.assertTrue(alarm1(rig, 13))
        self.assertTrue(co(rig, "Sounder"))
        lamp = set()
        for _ in range(30):
            rig.tick()
            lamp.add(co(rig, "AlarmLamp"))
        self.assertEqual(lamp, {True})                 # steady, not flashing
        rig.cmd(5)
        rig.run(2)
        self.assertFalse(co(rig, "Sounder"))
        self.assertTrue(co(rig, "AlarmLamp"))
        finish(rig)
        self.assertEqual(rig.plc.mw[MW["BatchesDone"]], 1)

    def test_not_enough_material_blocks_start(self):
        rig = new_rig(silo_kg=(15000, 12000, 9000, 6000, 550))
        start(rig)
        rig.run(1)
        self.assertEqual(rig.plc.State, 0)
        self.assertTrue(rig.plc.mw[MW["Status"]] & 0x0010)
        self.assertTrue(alarm1(rig, 14))

    def test_recipe_over_mixer_capacity_blocks_start(self):
        rig = new_rig()
        rig.plc.set_hmi("R1_A", 2000)
        start(rig)
        rig.run(1)
        self.assertEqual(rig.plc.State, 0)
        self.assertEqual(rig.plant.dispensed_kg, 0.0)


class StopsAndHolds(unittest.TestCase):
    def test_estop_aborts_and_kills_outputs(self):
        rig = new_rig()
        start(rig)
        rig.run_until(feeding(rig, 2))
        rig.plant.estop = True
        rig.run(0.3)
        self.assertEqual(rig.plc.State, 0)
        for name in ("C1_RunCmd", "C2_RunCmd", "Mix_RunCmd", "Door_OpenSol"):
            self.assertFalse(co(rig, name), name)
        self.assertTrue(alarm1(rig, 0))
        rig.run(5)
        self.assertEqual(rig.plant.c1.freq, 0.0)
        rig.plant.estop = False
        rig.cmd(5)
        rig.run(2)
        self.assertFalse(alarm1(rig, 0))

    def test_operator_hold_and_resume(self):
        rig = new_rig()
        start(rig)
        rig.run_until(feeding(rig, 1))
        rig.run(5)
        rig.cmd(3)
        self.assertEqual(rig.plc.State, 100)
        rig.run(70)
        self.assertEqual(rig.plant.c1.freq, 0.0)
        self.assertEqual(rig.plant.c2.freq, 0.0)
        rig.cmd(4)
        finish(rig)
        self.assertEqual(rig.plc.mw[MW["BatchesDone"]], 1)
        for i, target in enumerate(R1, start=1):
            self.assertLessEqual(abs(rig.plc.ActualKg[i] - target), tol(target))
        self.assertAlmostEqual(rig.plant.discharged_kg, rig.plant.dispensed_kg, delta=0.5)


if __name__ == "__main__":
    unittest.main()
