# F4 · Stepper drive: silo 4 gate jammed

**Mirrors:** checking stepper motors and drives. **Plant:** a lump of caked Material D jams the silo 4 gate blade. When the drive tries to open it, the motor stalls.

**Inject:** `fault F4 on` before a batch. **Repair:** `fault F4 off`.

## 0. Symptom (HMI)

- Silos 1–3 weigh out normally. When silo 4 starts, the batch holds: Step **100**, Alarm1 **512** (bit 9, gate drive fault), Alarm2 **256** (bit 8, gate 4). Lamp flashing, sounder on.
- Feeder HMI: gate 4 alarm code **1** (stall); gate 4 open **2.0 %**, stuck there.

## 1. Check the I/O

| Tag | Value | Meaning |
|---|---|---|
| `IR_GateStatus4` | 8 (16#0008) | fault bit only. Not ready, **not homed** (a stall loses the position) |
| `IR_GateAlarm4` | 1 | stall |
| `IR_GatePos4` | 20 | 2.0 %: it moved a little, then stopped |
| `HR_GateSP4` | was 1000 (fast feed), now 0 | the PLC asked for fully open |

## 2. Program online

Section 2 reads bit 3 of the status word (`GateFault[i]`); section 6 latches `GateFaultSilo[4]` and `A_GateFault`. The command was right; the drive couldn't follow it.

## 3. Configuration / drive

- **The drive is healthy:** it detected the stall and protected the motor. The other four gates work, so it's not power, enable or communications.
- **After a stall the drive no longer knows where the gate is,** so it must be homed again before it may move.

## 4. Repair and prove

1. Isolate the drive, clear the jam at the gate (`fault F4 off`).
2. **Reset + ack** (reset pulse to the gate drives), then **Resume**.
3. **The sequence homes the gates by itself first** (steps 10 → **12** → 20 …), then carries on with silo 4. Batch completes.
4. If the jam is still there, homing works (closing direction) but opening stalls again. That tells you the blade is still blocked.

## Recording script (about 3 min)

1. "Batch running. Silos 1 to 3 fine. Silo 4 starts … hold."
2. "Gate drive fault, gate 4. Alarm code 1: stall. It's stuck at 2 percent."
3. Monitoring: "Status word 8: fault, and the homed bit is gone. A stepper that stalls loses its position."
4. "PLC asked for 100 percent open. The drive tried and stalled: mechanical, not electrical. The other gates are fine."
5. "Clear the jam." `fault F4 off`. Reset, Resume. "Watch the step: 12, home gates, first. Then it finishes silo 4."

**Lesson:** a stalled stepper has lost its position. Fix the mechanical cause, then re-home before you trust any position again.
