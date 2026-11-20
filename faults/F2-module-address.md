# F2 · Module configuration: remote I/O node address wrong

**Mirrors:** swapping an I/O module or card and checking its configuration (DIP switches). **Plant:** after a card swap, the remote I/O rack's node-address switches are set to **2**, but the master PLC polls node **1**.

**Inject:** while silo 1 is feeding, type `fault F2 on`. **Repair:** `fault F2 off`.

## 0. Symptom (HMI)

- Everything stops at once: belts, gates and mixer.
- After about 2 s, Step **100**, Alarm1 **2** (bit 1, remote I/O comms lost), lamp flashing, sounder on.
- **The HMI values freeze.** Weights, gate positions and currents stop changing.

## 1. Check the I/O

- **The PLC's picture is stale.** 1.2 s after the fault, the plant's conveyor 1 was already slowing (42 Hz), but the PLC still showed `DI_C1_SpeedOK` TRUE and stayed in step 60. It was reading old values.
- **The rack protected the plant on its own.** After 1 s of silence it applied its fault action: outputs off, setpoints to 0. So the gates closed and the belts coasted to a stop.

## 2. Program online

- `IR_Heartbeat` stays at one value (93 in the capture). The rack counts it up every 100 ms; frozen means no fresh data.
- Section 5 of the program: `HBSame := IR_Heartbeat = LastHB;` → `CommsTmr` (2 s) → `A_Comms`.
- The OpenPLC dashboard log shows "Modbus Read … failed on MB device RIO1" and reconnect attempts.

## 3. Configuration (this is the fault)

- OpenPLC → Slave Devices → RIO1: **Slave ID 1**.
- The rack answers only its own node address. In the lab, `fault F2 on` sets the rack to 2; on real hardware you'd read it off the module's address switches.
- Mismatch found: the module was set to 2 after the swap.

## 4. Repair and prove

1. Set the module back to node 1 (`fault F2 off`). The heartbeat moves again.
2. **Reset + ack**, then **Resume**. The sequence restarts the mixer, then conveyor 2, then conveyor 1, and carries on weighing silo 1.
3. Batch completes: nothing spilled, nothing dropped on the floor.

## Recording script (about 3 min)

1. "Silo 1 feeding. Now I'll change the rack's node address, like a card swapped without checking its switches." `fault F2 on`.
2. "Everything stopped, then: comms lost. Notice the HMI numbers froze."
3. Monitoring: "The heartbeat isn't moving. The PLC is looking at old data: for a second it still thought conveyor 1 was running."
4. "The rack shut its own outputs after one second. That's its fault action, and why nothing spilled."
5. Slave Devices page: "The master polls node 1. The module says 2. Fix the switch." `fault F2 off`.
6. Reset, Resume: "Downstream first, then upstream, and the batch finishes."

**Lesson:** when every input freezes at once, suspect the communication or the module configuration before any single sensor. Check the address settings after every module swap.
