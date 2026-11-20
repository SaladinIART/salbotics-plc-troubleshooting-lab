# The seven faults

A demonstration rebuilt with open tools: a simulated plant, not any company's equipment. Each page follows the same fault-tracing order:

0. **Read the HMI and the alarm.** What stopped, and which step was it on?
1. **Check the I/O.** Are the inputs and outputs what the step expects?
2. **Read the program online** (OpenPLC → Monitoring). Which condition isn't met?
3. **Check the configuration** (module address, drive settings, HMI tag addresses).
4. **Only then repair or swap** the field device, and prove the fix with a full batch.

| Fault | Task it mirrors | Page | Alarm shown |
|---|---|---|---|
| F1 | Sensor check | [F1-sensor.md](F1-sensor.md) | Weight signal fault, silo 3 |
| F2 | Remote I/O module configuration | [F2-module-address.md](F2-module-address.md) | Remote I/O comms lost |
| F3 | VFD / inverter check | [F3-vfd-trip.md](F3-vfd-trip.md) | Conveyor 1 VFD trip |
| F4 | Stepper drive (silo gate) | [F4-gate-stepper.md](F4-gate-stepper.md) | Gate 4 drive fault |
| F5 | Output on, device not moving | [F5-output-wiring.md](F5-output-wiring.md) | Discharge door open timeout |
| F6 | Program edit and download | [F6-program-edit.md](F6-program-edit.md) | none: off-ratio batch |
| F7 | HMI changes | [F7-hmi-tag.md](F7-hmi-tag.md) | none: the HMI shows the wrong silo |

**Real-plant conditions** (corrosion, sensor drift and access, belt and motor wear) and ideas for faults F8–F10: [REAL_WORLD.md](REAL_WORLD.md).

**Where the numbers come from:** every value on these pages was captured by running the fault in the lab (`python tools/fault_snapshots.py`, 2026-11-20). The real OpenPLC run shows the same values, within a few kilograms or tenths of a second.

## How the pages are illustrated

Each fault is run on the real stack (OpenPLC Runtime v3 + plant simulator + FUXA) and captured as screenshots at each step: symptom, I/O in OpenPLC Monitoring, the test, the repair. **F3 is done** ([F3-vfd-trip.md](F3-vfd-trip.md)); the other pages still carry a text script and get their screenshots next. Images live in [img/](img/).

To reproduce a page yourself:
1. **OpenPLC:** running the program (http://localhost:8080). Status should say Running.
2. **Plant simulator:** running in WSL (`python3 -m lab.run_plant --port 5020`).
3. **FUXA:** running (`D:\Tools\fuxa\start-fuxa.cmd`), with the Feeder HMI and Mixer HMI open in Chrome.
4. **Inject faults** at the simulator's `lab>` prompt, or from anywhere with `python3 tools/instructor.py F3 on` (refill silos: `tools/instructor.py refill`).

**Alarm words on the HMI:** they're numbers. Read them as bits (DESIGN.md has the full list). The ones you'll meet here: Alarm1 2 = comms lost, 4 = conveyor 1 VFD trip, 128 = door open timeout, 512 = gate drive fault, 4096 = weight signal fault. Alarm2 256 = gate 4, 4096 = silo 3 signal.

**Lamp:** flashing means a trip, steady means a warning. A snapshot can catch the flash in its off phase.

Licence for these pages: CC BY 4.0.
