"""Run each lab fault in the simulator (soft-PLC copy of batching.st) and print the
values a troubleshooter would see: HMI tags, alarm words, rack I/O.

    python tools/fault_snapshots.py

The numbers in faults/F*.md come from this script, so the write-ups match what
the lab really does. Re-run it after any logic change.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lab.iomap import DI, DO, IR, MW  # noqa: E402
from lab.rig import Rig, alarm_text  # noqa: E402


def rig():
    r = Rig()
    r.tick()
    return r


def snap(r, title, extra=()):
    m = r.plc.mw
    print(f"\n--- {title}  (t = {r.plant.t:.1f} s)")
    print(f"State {m[MW['State']]}  ActiveSilo {m[MW['ActiveSilo']]}  Status {m[MW['Status']] & 0xFFFF}"
          f"  Alarm1 {m[MW['Alarm1']] & 0xFFFF}  Alarm2 {m[MW['Alarm2']] & 0xFFFF}")
    print("alarms:", alarm_text(m[MW["Alarm1"]], m[MW["Alarm2"]]))
    print("lamp", r.plc.co[DO["AlarmLamp"]], "sounder", r.plc.co[DO["Sounder"]])
    for label, value in extra:
        print(f"  {label}: {value}")


def feeding(silo):
    return lambda r: r.plc.State == 60 and r.plc.Silo == silo


def f1():
    r = rig(); r.cmd(1); r.run_until(feeding(3)); r.run(4)
    before = r.plc.mw[MW["Weight3"]]
    r.plant.set_fault("F1"); r.run(0.5)
    snap(r, "F1 silo 3 loop broken", [
        ("Weight3 before", before), ("IR_Weight3 raw", r.plc.ir[IR["Weight3"]]),
        ("HMI Weight3 now", r.plc.mw[MW["Weight3"]]), ("Actual3 so far", r.plc.mw[MW["Actual3"]]),
        ("HR_GateSP3", r.plc.hr[2]), ("ResumeState", r.plc.ResumeState)])
    r.plant.set_fault("F1", False); r.cmd(5); r.run(1.5); r.cmd(4)
    r.run_until(lambda x: x.plc.State == 0)
    print("  after fix: Actual3", round(r.plc.ActualKg[3], 1), "batches", r.plc.mw[MW["BatchesDone"]])


def f2():
    r = rig(); r.cmd(1); r.run_until(feeding(1)); r.run(5)
    hb = r.plc.ir[IR["Heartbeat"]]
    r.plant.set_fault("F2"); r.run(1.2)
    print("\n  after 1.2 s: rack comm_ok", r.plant.comm_ok, "C1 Hz", round(r.plant.c1.freq, 1),
          "PLC State", r.plc.State, "PLC still thinks C1_SpeedOK", r.plc.di[DI["C1_SpeedOK"]])
    r.run(1.5)
    snap(r, "F2 node address wrong", [
        ("heartbeat frozen at", f"{hb} -> {r.plc.ir[IR['Heartbeat']]}"),
        ("plant gates %", [round(g.pos / 10, 1) for g in r.plant.gates]),
        ("plant C1/C2 Hz", (round(r.plant.c1.freq, 1), round(r.plant.c2.freq, 1))),
        ("PLC image C1_Run (stale)", r.plc.di[DI["C1_Run"]])])
    r.plant.set_fault("F2", False); r.run(1); r.cmd(5); r.run(1.5); r.cmd(4)
    r.run_until(lambda x: x.plc.State == 0)
    print("  after fix: batches", r.plc.mw[MW["BatchesDone"]], "spill", round(r.plant.spill_kg, 1),
          "pile", round(r.plant.pile_kg, 1))


def f3():
    r = rig(); r.plant.set_fault("F3"); r.cmd(1)
    r.run_until(feeding(1))
    print("\n  empty belt running: C1 current", round(r.plant.c1.current, 1), "A")
    peak = 0.0
    while r.plc.State != 100:
        r.tick(); peak = max(peak, r.plant.c1.current)
    snap(r, "F3 conveyor 1 overload", [
        ("C1 peak current A", round(peak, 1)), ("IR_C1_FaultCode", r.plc.ir[IR["C1_FaultCode"]]),
        ("DI_C1_Fault", r.plc.di[DI["C1_Fault"]]), ("C1 load kg", round(r.plant.c1.load, 1)),
        ("Actual1 at trip", r.plc.mw[MW["Actual1"]]), ("ResumeState", r.plc.ResumeState)])
    r.run(60)
    print("  60 s later: C2 Hz", round(r.plant.c2.freq, 1))
    r.cmd(5); r.run(1.5); r.cmd(4)
    t0 = r.plant.t
    r.run_until(lambda x: x.plc.State == 100, 200)
    print(f"  reset without fixing: tripped again after {r.plant.t - t0:.1f} s")
    r.run(60); r.plant.set_fault("F3", False); r.cmd(5); r.run(1.5); r.cmd(4)
    r.run_until(lambda x: x.plc.State == 0)
    print("  after fix: batches", r.plc.mw[MW["BatchesDone"]], "Actual1", round(r.plc.ActualKg[1], 1))


def f4():
    r = rig(); r.plant.set_fault("F4"); r.cmd(1)
    r.run_until(lambda x: x.plc.State == 100)
    snap(r, "F4 gate 4 jammed", [
        ("ActiveSilo", r.plc.mw[MW["ActiveSilo"]]),
        ("IR_GateStatus4", f"{r.plc.ir[IR['GateStatus4']]} (16#{r.plc.ir[IR['GateStatus4']]:04X})"),
        ("IR_GateAlarm4", r.plc.ir[IR["GateAlarm4"]]), ("IR_GatePos4 (0.1 %)", r.plc.ir[IR["GatePos4"]]),
        ("HR_GateSP4 when it stalled", "1000 (fast feed), now 0")])
    r.run(30); r.plant.set_fault("F4", False)
    n = len(r.trace); r.cmd(5); r.run(1.5); r.cmd(4)
    r.run_until(lambda x: x.plc.State == 0)
    print("  after fix: steps", [s for _, s in r.trace[n:]][:8], "... batches", r.plc.mw[MW["BatchesDone"]])


def f5():
    r = rig(); r.plant.set_fault("F5"); r.cmd(1)
    r.run_until(lambda x: x.plc.State == 90); r.run(3)
    print("\n  3 s into door open: DO_Door_OpenSol", r.plc.co[DO["Door_OpenSol"]],
          "DI_Door_Open", r.plc.di[DI["Door_Open"]], "DI_Door_Closed", r.plc.di[DI["Door_Closed"]])
    r.run_until(lambda x: x.plc.State == 100, 30)
    snap(r, "F5 door solenoid wire open", [
        ("mixer running", r.plant.mixer_running), ("mixer kg", round(r.plant.mixer_kg, 1)),
        ("ResumeState", r.plc.ResumeState)])
    r.plant.set_fault("F5", False); r.cmd(5); r.run(1.5); r.cmd(4)
    r.run_until(lambda x: x.plc.State == 0)
    print("  after fix: discharged", round(r.plant.discharged_kg, 1), "batches", r.plc.mw[MW["BatchesDone"]])


def f6():
    r = Rig(f6_bad_edit=True); r.tick(); r.cmd(1)
    r.run_until(lambda x: x.plc.State == 0)
    m = r.plc.mw
    snap(r, "F6 bad edit", [
        ("Recipe 1 (R1_A..E)", [m[MW[f"R1_{c}"]] for c in "ABCDE"]),
        ("Targets", [m[MW[f"Target{i}"]] for i in range(1, 6)]),
        ("Actuals", [m[MW[f"Actual{i}"]] for i in range(1, 6)]),
        ("batch total kg", round(sum(r.plc.ActualKg[1:]), 1))])


def f7():
    r = rig(); r.cmd(1); r.run_until(feeding(5))
    a = (r.plc.mw[MW["Weight4"]], r.plc.mw[MW["Weight5"]]); r.run(5)
    b = (r.plc.mw[MW["Weight4"]], r.plc.mw[MW["Weight5"]])
    print("\n--- F7 tag off by one")
    print(f"  silo 4 (FUXA 1048) {a[0]} -> {b[0]}; silo 5 (FUXA 1049, the wrong tag) {a[1]} -> {b[1]} over 5 s")


if __name__ == "__main__":
    for f in (f1, f2, f3, f4, f5, f6, f7):
        f()
