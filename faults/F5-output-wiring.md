# F5 · Output on, device not moving: discharge door solenoid

**Mirrors:** the classic "the PLC says it's on, but nothing moves". **Plant:** the wire from the output card to the mixer's discharge-door solenoid valve is broken (or a terminal is loose).

**Inject:** `fault F5 on` before a batch (the door only opens at the end). **Repair:** `fault F5 off`.

## 0. Symptom (HMI)

- Weighing, conveying and mixing all finish. At Step **90** (open door) nothing happens. After 10 s: Step **100**, Alarm1 **128** (bit 7, discharge door open timeout). Lamp flashing, sounder on.
- The mixer keeps turning with the whole batch inside (1 980 kg). It's safe, but stuck.

## 1. Check the I/O (this finds it)

| Tag | Value |
|---|---|
| `DO_Door_OpenSol` | **TRUE** (output on; on real hardware the card's LED is lit) |
| `DI_Door_Open` | FALSE |
| `DI_Door_Closed` | **TRUE**: the door never moved |

The output is on, and the door's closed switch never let go. So the command left the PLC but the movement never happened.

## 2. Program online

Step 90: `DoorCmd` TRUE → `DoorOpenTmr` (10 s) → `A_DoorOpenTO`. The program logic is satisfied; the problem is after the output.

## 3. Configuration / field

On real hardware, with the output on:
1. Measure **24 V at the output card terminal**: present → the PLC and card are fine.
2. Measure **at the valve coil**: absent → the fault is in the wire between them.
3. If 24 V reached the coil, you'd check the valve, then the air supply, then the cylinder.

## 4. Repair and prove

1. Repair the wire (`fault F5 off`).
2. **Reset + ack**, then **Resume**. After its restart checks (mixer running, door closed) the sequence returns to step 90; the door opens and the batch discharges (all 1 980 kg).

## Recording script (about 3 min)

1. "Mixing done. Step 90, open the door … nothing. Ten seconds: door open timeout."
2. Monitoring: "The PLC output is TRUE. The door-open switch never came on, and the door-closed switch never went off. So the door never moved."
3. "Program's fine. On site: meter on the card terminal, 24 volts there. At the valve coil, nothing. It's the wire."
4. `fault F5 off`. Reset, Resume. "Door opens, batch discharges."

**Lesson:** when the output is on and the device isn't moving, follow the voltage from the output terminal to the device. The fault is wherever the voltage stops.
