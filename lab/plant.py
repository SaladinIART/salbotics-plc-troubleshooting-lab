"""Plant simulator: five weighed silos, two conveyors, a rotary mixer, and the
remote I/O rack they are wired to. Standard library only.

The rack's Modbus tables live in `self.store` (a lab.modbus.DataStore). Each
`step(dt)` reads the outputs the PLC wrote (coils, holding registers), moves
the machines, and writes the inputs (discrete inputs, input registers).
"""

from collections import deque

from .iomap import (DI, DI_COUNT, DO, DO_COUNT, HR, HR_COUNT, IR, IR_COUNT,
                    RAW_4MA, RAW_SPAN, SILO_SPAN_KG, UNIT_ID, GATE_BITS)
from .modbus import DataStore

CELL_M = 0.15          # belt model resolution
NOMINAL_HZ = 50.0
NOMINAL_MPS = 1.5
FAULTS = {
    "F1": "Silo 3 weight transmitter loop broken (0 mA)",
    "F2": "Remote rack node address set to 2 (master polls 1)",
    "F3": "Conveyor 1 drag: seized idlers, overload under load",
    "F4": "Gate 4 jammed by caked material",
    "F5": "Discharge door solenoid wire open",
}


class Silo:
    def __init__(self, kg, max_rate):
        self.kg = kg
        self.max_rate = max_rate      # kg/s at 100 % open
        self.filtered = kg            # transmitter output, 0.3 s filter

    def outflow(self, gate_frac, dt):
        if gate_frac <= 0.0 or self.kg <= 0.0:
            return 0.0
        out = min(self.kg, self.max_rate * gate_frac ** 1.5 * dt)
        self.kg -= out
        return out

    def raw(self, dt, broken=False):
        self.filtered += (self.kg - self.filtered) * min(1.0, dt / 0.3)
        if broken:
            return 0
        raw = int(round(RAW_4MA + RAW_SPAN * self.filtered / SILO_SPAN_KG))
        return max(0, min(32767, raw))


class GateDrive:
    SPEED = 500.0  # 0.1 % units per second (50 %/s)

    def __init__(self):
        self.pos = 0.0
        self.homed = False
        self.homing = False
        self.fault = False
        self.alarm = 0
        self.jammed = False
        self._home = False
        self._reset = False
        self.sp_eff = 0

    def step(self, dt, enable, sp, home, reset, comm_ok):
        if reset and not self._reset and self.fault:
            self.fault = False
            self.alarm = 0
        self._reset = reset
        if home and not self._home and enable and not self.fault:
            self.homing = True
        self._home = home
        if not enable or self.fault:
            self.homing = False
        if self.homing:
            target = 0.0
        elif self.homed:
            target = float(max(0, min(1000, sp))) if comm_ok else 0.0  # comm loss: close
        else:
            target = self.pos
        self.sp_eff = target
        if enable and not self.fault:
            step = self.SPEED * dt
            new = min(target, self.pos + step) if target > self.pos else max(target, self.pos - step)
            if self.jammed and new > self.pos and new > 20.0:
                self.pos = max(self.pos, 20.0)
                self.fault = True
                self.alarm = 1
                self.homed = False
                self.homing = False
            else:
                self.pos = new
        if self.homing and self.pos <= 0.0:
            self.homing = False
            self.homed = True

    def status(self, enable):
        s = 0
        if enable and not self.fault:
            s |= GATE_BITS["ready"]
        if self.homed:
            s |= GATE_BITS["homed"]
        if self.homed and abs(self.pos - self.sp_eff) <= 5.0:
            s |= GATE_BITS["inpos"]
        if self.fault:
            s |= GATE_BITS["fault"]
        return s


class Conveyor:
    def __init__(self, length_m, rated_a, i0, k_a_per_kg):
        self.cells = deque([0.0] * int(round(length_m / CELL_M)))
        self.rated = rated_a
        self.i0 = i0
        self.k = k_a_per_kg
        self.freq = 0.0
        self.current = 0.0
        self.tripped = False
        self.code = 0
        self.heat = 0.0
        self.drag_a = 0.0
        self._dist = 0.0
        self._reset = False

    @property
    def load(self):
        return sum(self.cells)

    @property
    def speed(self):
        return self.freq / NOMINAL_HZ * NOMINAL_MPS

    def step(self, dt, run, reset, ref_hz, estop):
        if reset and not self._reset and self.tripped:
            self.tripped = False
            self.code = 0
            self.heat = 0.0
        self._reset = reset
        target = ref_hz if (run and not self.tripped and not estop) else 0.0
        if self.freq < target:
            self.freq = min(target, self.freq + 10.0 * dt)
        else:
            self.freq = max(target, self.freq - 25.0 * dt)
        self.current = (self.i0 + self.k * self.load + self.drag_a) if self.freq > 0.5 else 0.0
        if self.current > 1.05 * self.rated:
            self.heat += (self.current / self.rated - 1.05) * dt
        else:
            self.heat = max(0.0, self.heat - 0.1 * dt)
        if self.heat >= 0.5 and not self.tripped:
            self.tripped = True
            self.code = 2          # motor overload
        self._dist += self.speed * dt
        out = 0.0
        while self._dist >= CELL_M:
            self._dist -= CELL_M
            out += self.cells.pop()
            self.cells.appendleft(0.0)
        return out


class Plant:
    def __init__(self, silo_kg=(15000.0, 12000.0, 9000.0, 6000.0, 2600.0)):
        rates = (25.0, 22.0, 20.0, 15.0, 10.0)
        self.silos = [Silo(kg, r) for kg, r in zip(silo_kg, rates)]
        self.gates = [GateDrive() for _ in range(5)]
        self.c1 = Conveyor(30.0, rated_a=20.0, i0=6.0, k_a_per_kg=0.012)
        self.c2 = Conveyor(45.0, rated_a=30.0, i0=8.0, k_a_per_kg=0.02)
        self.mixer_kg = 0.0
        self.mixer_running = False
        self._mix_t = 0.0
        self.door = 0.0             # 0 closed .. 1 open
        self.discharged_kg = 0.0
        self.dispensed_kg = 0.0
        self.spill_kg = 0.0         # pushed into the chute while C2 stopped
        self.pile_kg = 0.0          # dropped onto a stopped C1
        self.estop = False
        self.faults = set()
        self.since_contact = 0.0
        self.comm_ok = False
        self.t = 0.0
        self._hb = 0
        self.store = DataStore(co=DO_COUNT, di=DI_COUNT, hr=HR_COUNT, ir=IR_COUNT,
                               unit_ids={UNIT_ID}, on_request=self.touch)
        self._write_inputs(0.1)

    # ---- instructor controls ------------------------------------------
    def set_fault(self, code, on=True):
        if code not in FAULTS:
            raise ValueError(f"unknown fault {code}; simulator faults are {', '.join(FAULTS)}")
        (self.faults.add if on else self.faults.discard)(code)
        self.store.unit_ids = {2} if "F2" in self.faults else {UNIT_ID}
        self.c1.drag_a = 14.0 if "F3" in self.faults else 0.0
        self.gates[3].jammed = "F4" in self.faults

    def refill(self, silo, kg=15000.0):
        s = self.silos[silo - 1]
        s.kg = s.filtered = float(kg)

    def touch(self):
        """The master talked to the rack (called by the server or the direct link)."""
        self.since_contact = 0.0

    # ---- simulation ----------------------------------------------------
    def step(self, dt=0.1):
        self.t += dt
        self.since_contact += dt
        self.comm_ok = self.since_contact <= 1.0
        st = self.store
        if self.comm_ok:
            co, hr = list(st.co), list(st.hr)
        else:  # rack fault action: outputs off, setpoints to 0, gate-drive enable held
            co, hr = [False] * DO_COUNT, [0] * HR_COUNT
            co[DO["Gates_Enable"]] = st.co[DO["Gates_Enable"]]
        estop = self.estop

        enable = co[DO["Gates_Enable"]] and not estop
        for n, g in enumerate(self.gates):
            g.step(dt, enable, hr[HR[f"GateSP{n + 1}"]], co[DO["Gates_Home"]],
                   co[DO["Gates_Reset"]], self.comm_ok)

        fed = 0.0
        for g, s in zip(self.gates, self.silos):
            fed += s.outflow(g.pos / 1000.0, dt)
        self.dispensed_kg += fed
        if fed and self.c1.speed < 0.05:
            self.pile_kg += fed
        self.c1.cells[0] += fed

        to_c2 = self.c1.step(dt, co[DO["C1_RunCmd"]], co[DO["C1_Reset"]],
                             hr[HR["C1_SpeedRef"]] / 10.0, estop)
        if to_c2 and self.c2.speed < 0.05:
            self.spill_kg += to_c2
        else:
            self.c2.cells[0] += to_c2
        self.mixer_kg += self.c2.step(dt, co[DO["C2_RunCmd"]], co[DO["C2_Reset"]],
                                      hr[HR["C2_SpeedRef"]] / 10.0, estop)

        if co[DO["Mix_RunCmd"]] and not estop:
            self._mix_t += dt
        else:
            self._mix_t = 0.0
        self.mixer_running = self._mix_t >= 0.5

        sol = co[DO["Door_OpenSol"]] and "F5" not in self.faults
        self.door = min(1.0, self.door + dt / 3.0) if sol else max(0.0, self.door - dt / 3.0)
        if self.door > 0.5:
            out = min(self.mixer_kg, 150.0 * dt)
            self.mixer_kg -= out
            self.discharged_kg += out

        self._write_inputs(dt, enable)

    def _write_inputs(self, dt, enable=False):
        st = self.store
        self._hb = (self._hb + 1) % 10000
        di = st.di
        di[DI["EStopOK"]] = not self.estop
        for tag, c in (("C1", self.c1), ("C2", self.c2)):
            di[DI[f"{tag}_Run"]] = c.freq > 0.5
            di[DI[f"{tag}_Fault"]] = c.tripped
            di[DI[f"{tag}_SpeedOK"]] = c.speed > 0.3 * NOMINAL_MPS
        di[DI["Mix_Run"]] = self.mixer_running
        di[DI["Door_Open"]] = self.door >= 0.95
        di[DI["Door_Closed"]] = self.door <= 0.05
        ir = st.ir
        ir[IR["Heartbeat"]] = self._hb
        for n in range(5):
            ir[IR[f"Weight{n + 1}"]] = self.silos[n].raw(dt, broken=(n == 2 and "F1" in self.faults))
            g = self.gates[n]
            ir[IR[f"GatePos{n + 1}"]] = int(round(g.pos))
            ir[IR[f"GateStatus{n + 1}"]] = g.status(enable)
            ir[IR[f"GateAlarm{n + 1}"]] = g.alarm
        for tag, c in (("C1", self.c1), ("C2", self.c2)):
            ir[IR[f"{tag}_Freq"]] = int(round(c.freq * 10))
            ir[IR[f"{tag}_Current"]] = int(round(c.current * 10))
            ir[IR[f"{tag}_FaultCode"]] = c.code

    # ---- accounting ------------------------------------------------------
    def material_in_system(self):
        return self.c1.load + self.c2.load + self.mixer_kg + self.discharged_kg + self.spill_kg

    def summary(self):
        return (f"t={self.t:7.1f}s comms={'ok' if self.comm_ok else 'LOST'} "
                f"estop={'ON' if self.estop else 'off'} faults={sorted(self.faults) or '-'}\n"
                f"silos kg: {', '.join(f'{s.kg:.0f}' for s in self.silos)}\n"
                f"gates %: {', '.join(f'{g.pos / 10:.1f}' + ('!' if g.fault else '') for g in self.gates)}\n"
                f"C1 {self.c1.freq:4.1f} Hz {self.c1.current:4.1f} A load {self.c1.load:6.1f} kg"
                f"{' TRIP' if self.c1.tripped else ''} | "
                f"C2 {self.c2.freq:4.1f} Hz {self.c2.current:4.1f} A load {self.c2.load:6.1f} kg"
                f"{' TRIP' if self.c2.tripped else ''}\n"
                f"mixer {'RUN' if self.mixer_running else 'off'} {self.mixer_kg:.1f} kg, "
                f"door {self.door * 100:.0f} %, discharged {self.discharged_kg:.1f} kg, "
                f"floor: spill {self.spill_kg:.1f} kg, pile {self.pile_kg:.1f} kg")


def link_inputs(plant, ctrl):
    """Direct link (no TCP): rack inputs -> PLC image, if the node address matches."""
    if plant.store.accepts(UNIT_ID):
        ctrl.di[:] = plant.store.di
        ctrl.ir[:] = plant.store.ir
        plant.touch()


def link_outputs(plant, ctrl):
    if plant.store.accepts(UNIT_ID):
        plant.store.co[:] = ctrl.co
        plant.store.hr[:] = ctrl.hr
        plant.touch()
