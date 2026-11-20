# Glossary

Every technical word used in this lab, in one plain sentence. In alphabetical order.

| Word | Plain meaning |
|---|---|
| **4–20 mA** | A common way for a sensor to send a reading down a wire: 4 milliamps means "zero" and 20 means "full". Because zero isn't 0 mA, a reading of 0 mA means the wire is broken, not that the value is zero. |
| **Actuator** | Anything that makes something move: a motor, a valve, a gate. |
| **Alarm** | A message the controller raises when something is wrong. A **trip** stops the process; a **warning** only informs. |
| **Alarm word** | Sixteen alarms packed into one number, one per bit. 4 means "bit 2 is on"; the bit list is in [DESIGN.md](../DESIGN.md). |
| **Batch** | One complete mix: weigh every ingredient, convey, mix, discharge. |
| **Calibration** | Checking a sensor against a known reference (for scales, a test weight) and correcting it. |
| **Conveyor** | A moving belt that carries material. |
| **Discharge** | Emptying the finished batch out of the mixer. |
| **E-stop** | The red emergency-stop button. In real plants it cuts power through a dedicated safety circuit, not only through the PLC. |
| **Fault code** | A number a drive shows to say *how* it stopped (for example 2 = motor overload). It doesn't say *why*. |
| **FUXA** | Free software for building operator screens (HMIs) in a web browser. Used here for both screens. |
| **Heartbeat** | A number a device keeps changing so others can tell it's alive. If it stops changing, communication is lost. |
| **HMI** | Human–Machine Interface: the screen people use to watch and control a machine. |
| **Hold** | The controller's safe pause: gates shut, belts empty, everything waits for a person. |
| **Homing** | Moving a motor to a known reference position so it knows where it is again. |
| **I/O** | Inputs and outputs: the signals coming into the controller (sensors) and going out of it (to motors, valves, lamps). |
| **IEC 61131-3** | The international standard for PLC programming languages. This lab's program is written in one of them, Structured Text. |
| **In-flight** | Material already falling when a gate closes. The controller closes slightly early to allow for it, and learns the amount over time. |
| **Interlock** | A rule the controller always enforces for safety or to protect the process. Example: never open a gate onto a stopped belt. |
| **Load cell** | A weighing sensor. Silos sit on load cells, so the controller knows how much is inside. |
| **Lockout / tagout** | Isolating a machine's energy and putting your personal lock on it before working on it, so nobody can start it. |
| **Modbus** | A simple, very common language that industrial devices use to exchange numbers over a network. |
| **Monitoring (online)** | Watching the program's values live while it runs. The single most useful troubleshooting view. |
| **Node address** | A device's number on a network. If two sides disagree on it, they can't talk (fault F2). |
| **OpenPLC** | Free, open-source software that turns an ordinary computer into a PLC. |
| **Output card / terminal** | Where the controller's output signal leaves as electricity, to a wire that runs to the device. |
| **PLC** | Programmable Logic Controller: a tough industrial computer that runs machines, reading inputs and setting outputs in a fast, endless loop. |
| **Recipe** | The list of how much of each ingredient goes into one batch. |
| **Remote I/O** | A box of input and output cards placed near the machines, connected to the PLC by a network cable instead of hundreds of wires. |
| **Reset** | Clearing an alarm after the cause is fixed. Resetting without fixing usually just brings the alarm back. |
| **Root cause** | The real reason something failed, as opposed to the symptom you see first. |
| **Sequence / step** | The controller works through numbered steps (feed, settle, check weight…); the step number tells you where it stopped. |
| **Silo** | A tall container holding one raw material. |
| **Simulator** | A program that behaves like the real machines, so the controller can be tested and practised on safely. |
| **Solenoid valve** | An electrically switched valve; here it lets compressed air open the mixer door. |
| **Stall** | A motor told to move that can't (something blocks it). Stepper drives detect this and stop. |
| **Stepper motor / drive** | A motor that moves in precise small steps; the drive is the electronics that powers it and reports its position. |
| **Tag** | A named value on an HMI or in a PLC (for example "Weight4"), linked to an address. A tag at the wrong address shows the wrong thing (fault F7). |
| **Tolerance** | How far from the target weight is still acceptable (here: 1 %, or at least 5 kg). |
| **VFD** | Variable Frequency Drive: electronics that start, stop and control the speed of a motor, and protect it (for example from overload). |
| **Zero-speed switch** | A sensor that checks a belt is really moving, so a snapped or slipping belt is caught even if the motor still turns. |
