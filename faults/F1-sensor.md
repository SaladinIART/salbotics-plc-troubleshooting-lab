# F1 · Sensor: silo 3 weight signal lost

**Mirrors:** sensor checks on a production line. **Plant:** the silo 3 load-cell transmitter's 4–20 mA loop opens (a broken cable or loose junction-box terminal) while Material C is being weighed out.

**Inject:** start a batch; when the Feeder HMI shows "Silo weighing 3", type `fault F1 on` at `lab>`. **Repair:** `fault F1 off`.

## 0. Symptom (HMI)

- The batch stops: Step **100** (hold), Status 2.
- Alarm1 **4096** (bit 12, weight signal fault) and Alarm2 **4096** (bit 12, silo 3). Lamp flashing, sounder on.
- **Silo 3 weight reads −5000 kg.** A silo can't weigh less than nothing: that's the clue.

## 1. Check the I/O

| Tag (OpenPLC Monitoring) | Healthy | With F1 |
|---|---|---|
| `IR_Weight3` (raw counts) | about 17 855 (8 949 kg) | **0** |
| `HR_GateSP3` | 1000 or 250 while feeding | 0 (gate closed by the hold) |

Raw counts are mA × 1600, so 0 counts = 0 mA. A live 4–20 mA loop never reads below 4 mA (6 400 counts); 0 mA means the loop is open.

## 2. Program online

In `batching.st`, section 2: `SignalBad[i] := (RawW[i] < 5760) OR (RawW[i] > 32640);`, which is below 3.6 mA or above 20.4 mA. `SignalBad[3]` is TRUE, so `A_Signal` latched and the sequence went to HOLD with `ResumeState` = 60 (feeding). The program is doing its job; the fault is outside it.

## 3. Configuration

Nothing to change: the other four silos read normally on the same rack, so the rack and its scaling are fine. The fault is on this one channel.

## 4. Repair and prove

1. At the transmitter, measure the loop current with a meter in series: 0 mA confirms the open loop. Check the cable and the junction-box terminals.
2. Repair (`fault F1 off`). Silo 3 weight returns to normal.
3. **Reset + ack** (silences the sounder, clears the latch), then **Resume**.
4. The batch carries on from the 53 kg already weighed out and finishes Material C at **396 kg** of 400 kg (in tolerance), because the start weight was kept through the hold.

## Recording script (about 3 min)

1. "Batch running, silo 3 feeding." Show the Feeder HMI.
2. Inject F1. "The batch held. Alarm: weight signal fault, silo 3. And the weight reads minus five thousand kilos."
3. OpenPLC Monitoring: "`IR_Weight3` is zero counts. That's zero milliamps; a healthy loop never goes below four. So the loop is open: a sensor or wiring fault, not the program."
4. "Other silos read fine on the same rack, so it's this channel only."
5. "On site I'd put a meter in the loop. Here, repair." `fault F1 off`. Reset, Resume.
6. "It carried on from where it stopped and finished in tolerance." Show 396 / 400 kg.

**Lesson:** a live-zero signal (4–20 mA) tells you the difference between "empty" and "broken". Read the raw value before you trust the engineering value.
