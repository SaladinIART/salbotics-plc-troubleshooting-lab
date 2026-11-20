# Real-plant conditions behind the lab

The simulator is clean; a real batching line isn't. These are the engineering challenges met on the kind of line this lab models: a medium-scale process plant with **corrosive dust and high humidity**. They're the reason several of the faults exist, and why a troubleshooter's first question is often about the environment, not the program.

## 1. Corrosion from dust and humidity

- **What happens:** corrosive dust settles on everything and absorbs moisture from the humid air. Terminals, junction boxes, sensor mountings and brackets corrode.
- **How it shows up as a fault:**
  - a 4–20 mA loop that opens or goes intermittent at a corroded terminal → **F1** (weight signal lost; intermittent before it fails completely)
  - a loose or broken output wire at a corroded terminal → **F5** (output on, device not moving)
  - a gate blade that sticks with caked material → **F4** (stepper stall)
- **What helps:** sealed enclosures and glands, regular terminal checks and cleaning, corrosion-resistant mountings and fasteners, and recording what was found so the worst spots get checked more often.

## 2. Sensor noise, reading errors and hard-to-reach sensors

- **What happens:**
  - Dust, humidity and corroded mountings make readings noisy or drift.
  - A load cell on a corroded or shifted mounting reads wrong even though the electronics are fine.
  - Some sensors were installed where they're hard to reach, so checks get skipped.
- **What the lab shows:** a *clean* failure (F1: 0 mA, easy to spot). A drifting sensor is harder: the reading looks plausible, and the batch just comes out wrong.
- **What helps:**
  - Scheduled sensor health checks and calibration (for weighing: test weights, zero and span checks), with a log of results.
  - Trending the readings, so drift shows up before quality does.
  - Designing for access: sensors placed where they can be checked safely and quickly.

## 3. Conveyor belt and motor wear

- **What happens:** belts wear and can snap; idlers seize; motors wear (bearings, alignment, overheating).
- **How it shows up:**
  - **F3:** drag from seized idlers trips the drive on overload, and only when loaded.
  - **A snapped belt:** the motor keeps turning, so the drive shows no fault, but the belt stops. The zero-speed switch catches it (the lab's "conveyor zero speed" alarm). Motor current also drops to the no-load value.
- **What helps:** watch motor current and temperature for trends, inspect belts and idlers on a schedule, and keep a spare belt and splice kit for the line's critical conveyors.

## Faults to add next (ideas)

| Idea | What the trainee would see | Real cause it teaches |
|---|---|---|
| F8 load-cell drift | No alarm; one material always comes out a few % off; a test weight reads wrong | corroded or shifted mounting, overdue calibration |
| F9 belt snap | "Conveyor 2 zero speed" with the VFD running and current at no-load | worn belt or splice failure |
| F10 noisy signal | weight jumps around, false "no flow" or tolerance trips | moisture in a junction box, poor shielding or earthing |

Licence for this page: CC BY 4.0.
