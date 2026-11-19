"""Plant + soft-PLC wired together without TCP, plus the instructor console.

Used by the tests and by `python -m lab.run_softplc`.
"""

from .controller import Controller
from .iomap import ALARM1, ALARM2, MW, STATES, CMDS
from .plant import FAULTS, Plant, link_inputs, link_outputs


class Rig:
    def __init__(self, f6_bad_edit=False, silo_kg=None):
        self.plant = Plant(silo_kg) if silo_kg else Plant()
        self.plc = Controller(f6_bad_edit=f6_bad_edit)
        self.trace = []  # (time s, state) every time the state changes

    def tick(self):
        link_inputs(self.plant, self.plc)
        self.plc.scan()
        link_outputs(self.plant, self.plc)
        self.plant.step(0.1)
        if not self.trace or self.trace[-1][1] != self.plc.State:
            self.trace.append((round(self.plant.t, 1), self.plc.State))

    def run(self, seconds):
        for _ in range(int(round(seconds * 10))):
            self.tick()

    def run_until(self, cond, timeout=900.0):
        """Tick until cond(rig) is true. Returns the time it took."""
        start = self.plant.t
        while not cond(self):
            if self.plant.t - start > timeout:
                raise TimeoutError(f"condition not met in {timeout} s (state {self.plc.State})")
            self.tick()
        return self.plant.t - start

    # HMI actions
    def cmd(self, code):
        self.plc.set_hmi("Cmd", code)
        self.tick()

    def mode(self, m):
        self.plc.set_hmi("ModeReq", m)
        self.tick()

    def state_path(self):
        out = []
        for _, s in self.trace:
            if not out or out[-1] != s:
                out.append(s)
        return out


def alarm_text(alarm1, alarm2):
    a1 = alarm1 & 0xFFFF
    a2 = alarm2 & 0xFFFF
    names = [ALARM1[b] for b in range(16) if a1 >> b & 1]
    names += [ALARM2[b] for b in range(15) if a2 >> b & 1]
    return ", ".join(names) or "none"


def plc_summary(plc):
    m = plc.mw
    return (f"PLC mode {plc.Mode} state {plc.State} {STATES.get(plc.State, '?')} "
            f"silo {m[MW['ActiveSilo']]} batches {m[MW['BatchesDone']]} "
            f"mix {m[MW['MixRemain_s']]} s\n"
            f"targets {[m[MW[f'Target{i}']] for i in range(1, 6)]} "
            f"actuals {[m[MW[f'Actual{i}']] for i in range(1, 6)]}\n"
            f"alarms: {alarm_text(m[MW['Alarm1']], m[MW['Alarm2']])}")


HELP = """commands:
  status                 plant (and PLC) summary
  fault F1..F5 on|off    inject / clear a fault ({faults})
  faults                 list active faults
  estop on|off           press / release the E-stop
  refill N [kg]          refill silo N (default 15000 kg)
  cmd N                  soft-PLC only: HMI command ({cmds})
  mode N                 soft-PLC only: 1 Manual, 2 Semi-auto, 3 Auto
  quit"""


def console(plant, lock, plc=None, set_hmi=None):
    """Instructor console on stdin. `lock` guards the plant (and soft-PLC).
    `set_hmi(tag, value)` writes an HMI tag the way the HMI would."""
    set_hmi = set_hmi or (plc.set_hmi if plc else None)
    print(HELP.format(faults=", ".join(f"{k} {v}" for k, v in FAULTS.items()),
                      cmds=", ".join(f"{k} {v}" for k, v in CMDS.items())))
    while True:
        try:
            line = input("lab> ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not line:
            continue
        p = line.split()
        try:
            with lock:
                if p[0] in ("quit", "exit"):
                    return
                elif p[0] == "status":
                    print(plant.summary())
                    if plc:
                        print(plc_summary(plc))
                elif p[0] == "fault" and len(p) == 3:
                    plant.set_fault(p[1].upper(), p[2] == "on")
                    print("active faults:", sorted(plant.faults) or "none")
                elif p[0] == "faults":
                    print("active faults:", sorted(plant.faults) or "none")
                elif p[0] == "estop" and len(p) == 2:
                    plant.estop = p[1] == "on"
                elif p[0] == "refill" and len(p) in (2, 3):
                    plant.refill(int(p[1]), float(p[2]) if len(p) == 3 else 15000.0)
                elif p[0] == "cmd" and plc and len(p) == 2:
                    set_hmi("Cmd", int(p[1]))
                elif p[0] == "mode" and plc and len(p) == 2:
                    set_hmi("ModeReq", int(p[1]))
                else:
                    print(HELP.format(faults=", ".join(FAULTS), cmds=", ".join(map(str, CMDS))))
        except (ValueError, IndexError) as e:
            print("error:", e)
