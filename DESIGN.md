# Design: weigh-batching cell troubleshooting lab (CP-11a)

A demonstration rebuilt with open tools. It is **not** a copy of any company's program. It models a generic medium-scale plant of the kind the owner maintained: five feeder silos weighed on load cells, two conveyors in series up three storeys, and a rotary mixer, with two HMIs. Materials are called **A to E**, and every recipe and number here is invented for the lab.

Input: [DESIGN_INPUT.md](DESIGN_INPUT.md) (decisions 1–3). The addresses in this file come from [lab/iomap.py](lab/iomap.py), which is the single source of truth. The tests check that the PLC program matches it.

## Decisions

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Where it lives | Own repo, linked from the PLC Learning Hub | owner, 2026-11-20 |
| 2 | Machine | 5-silo loss-in-weight batching, 2 inclined conveyors, rotary mixer | owner's description |
| 3 | Faults | Seven, one per task the owner did at work | owner: "follow your recommendation" |
| 4 | Runtime | **OpenPLC Runtime v3** in WSL `Ubuntu-22.04-D`, **FUXA** for both HMIs, **Python plant simulator** (standard library only) acting as the remote I/O rack. Plus a **soft-PLC mode**: a Python copy of the same logic, so the HMIs and every fault work even before OpenPLC is installed. | v3 is marked end-of-life, but it is the version with the three features this lab needs: upload a `.st` file in the web page, poll a remote Modbus device ("Slave Devices", like a master PLC polling a remote rack), and serve Modbus to the HMI. The new v4 runtime has no web page; it takes programs from the v4 Editor, and its docs don't yet show remote-device polling. Move to v4 later, once it has that. Everything stays on D: (the WSL disk lives there). |
| 5 | Recordings | Owner records the screen with narration using the **Windows Snipping Tool** (already installed, records a screen area with the microphone). One video per fault, 2–4 minutes, 1080p, following the same script: symptom → what the online program shows → cause → fix → proof it works. Videos are saved to `D:\Dev\plc\plc-lab-recordings\`, outside the repo; they are published only after the owner reviews them. | Nothing to install, and the fixed script makes every video match its written page. |

## How the pieces connect

```
 FUXA (Windows, :1881)                     OpenPLC Runtime v3 (WSL, web :8080)
 Feeder HMI + Mixer HMI   --Modbus TCP-->  Modbus server :502   (%MW0.. = HR 1024..)
                                           batching.st (100 ms task)
                                           Slave device "RIO1"  --Modbus TCP-->  plant simulator :5020
                                                                                 (remote I/O rack, unit 1,
                                                                                  VFDs, gate drives, load cells)
```

Soft-PLC mode replaces the middle box: `python -m lab.run_softplc` runs the same logic in Python and serves the same HMI map on port 5021, so the FUXA screens work unchanged.

## The plant (simulated)

| Item | Model |
|---|---|
| Silos 1–5 (Materials A–E) | 20 t span load cells, weight transmitter 4–20 mA (raw = mA × 1600). Start weights 15 000 / 12 000 / 9 000 / 6 000 / 2 600 kg. Full-open flow 25 / 22 / 20 / 15 / 10 kg/s; flow ∝ gate opening^1.5. Transmitter filter time constant 0.3 s. |
| Silo gates | Stepper drive in position mode, 0–100.0 % (0–1000), 50 %/s. Must be homed after power-up or a fault. Takes its setpoint from the rack's holding registers. |
| Conveyor 1 (collecting belt) | 30 m at 1.5 m/s (50 Hz). VFD ramps 10 Hz/s up, 25 Hz/s down. 20 A rated. Overload trip (fault code 2) when current stays above 105 % of rated. |
| Conveyor 2 (incline, about 3 storeys) | 45 m at 1.5 m/s, 30 A rated, more current per kg because it lifts. |
| Zero-speed switches | One per belt; "speed OK" above 30 % speed. |
| Rotary mixer | Contactor with feedback; capacity 2 500 kg; pneumatic discharge door with open and closed limit switches, 3 s travel, spring return closed; discharges at 150 kg/s. |
| Remote I/O rack | Answers only its node address (unit 1). If the master is silent for 1 s it applies its fault action: digital outputs off, setpoint registers to 0 (so the gates close), gate-drive enable held. Heartbeat register counts up every 100 ms. |

The simulator also counts material that would end up on the floor: material dropped onto a stopped conveyor 1, and material conveyor 1 pushes into the transfer chute while conveyor 2 is stopped. A correct sequence leaves both at zero.

## I/O list (remote rack, unit 1)

Addresses are 0-based on the wire. OpenPLC address in brackets.

**Discrete inputs:** 0 E-stop healthy (%IX100.0) · 1 C1 run feedback (%IX100.1) · 2 C1 VFD fault (%IX100.2) · 3 C1 speed OK (%IX100.3) · 4 C2 run feedback (%IX100.4) · 5 C2 VFD fault (%IX100.5) · 6 C2 speed OK (%IX100.6) · 7 mixer running (%IX100.7) · 8 door open LS (%IX101.0) · 9 door closed LS (%IX101.1).

**Coils:** 0 C1 run (%QX100.0) · 1 C1 reset · 2 C2 run · 3 C2 reset · 4 mixer run (%QX100.4) · 5 door open solenoid (%QX100.5) · 6 alarm lamp · 7 sounder (%QX100.7) · 8 gate drives enable (%QX101.0) · 9 gate drives reset · 10 gates home (%QX101.2).

**Input registers (%IW100 + n):** 0 heartbeat · 1–5 silo weight raw · 6–10 gate position (0.1 %) · 11–15 gate status word (bit0 ready, bit1 homed, bit2 in position, bit3 fault) · 16–20 gate alarm code (1 = stall) · 21 C1 frequency (0.1 Hz) · 22 C1 current (0.1 A) · 23 C1 fault code (2 = motor overload) · 24–26 the same for C2.

**Holding registers written by the PLC (%QW100 + n):** 0–4 gate setpoints (0.1 %) · 5 C1 speed reference (0.1 Hz) · 6 C2 speed reference.

**Units:** weight kg, gate position 0.1 %, frequency 0.1 Hz, current 0.1 A, times in seconds.

## HMI map (PLC memory, %MWn = holding register 1024 + n)

| %MW | Tag | Written by | Meaning |
|---|---|---|---|
| 0 | ModeReq | Feeder HMI | 1 Manual, 2 Semi-auto, 3 Auto; accepted only when idle; PLC clears it |
| 1 | Cmd | Both | 1 Start, 2 Stop at end of batch, 3 Hold, 4 Resume/accept, 5 Reset + acknowledge, 6 Next, 7 Abort; PLC clears it |
| 2 | RecipeSel | Mixer HMI | 1–4 |
| 3 | BatchReq | Mixer HMI | batches to make |
| 4 | ManualBits | Feeder HMI | bit0 C2, bit1 C1, bit2 mixer, bit3 door, bit4 home gates (Manual only) |
| 5–9 | ManGateSP1–5 | Feeder HMI | gate opening in Manual (0.1 %) |
| 10–14 | Mode, State, ActiveSilo, BatchesDone, MixRemain_s | PLC | status |
| 15, 16 | Alarm1, Alarm2 | PLC | bit-packed alarms (below) |
| 17 | Status | PLC | bit0 running, bit1 held, bit2 waiting for Next, bit3 out-of-tolerance batch accepted, bit4 not enough material |
| 20–24 | Weight1–5 | PLC | silo weight, kg |
| 25–29 | Target1–5 | PLC | this batch's target, kg |
| 30–34 | Actual1–5 | PLC | weighed out this batch, kg (live while feeding) |
| 35–39 | Inflight1–5 | PLC | in-flight compensation, 0.1 kg |
| 40–44 | GatePos1–5 | PLC | 0.1 % |
| 45–50 | C1/C2 frequency, current, fault code | PLC | copies of the drive values |
| 51–55 | GateAlarm1–5 | PLC | drive alarm codes |
| 60–79 | R1_A … R4_E | Mixer HMI (supervisor) | recipe kg per batch: recipe r, material m at 60 + 5(r−1) + m |
| 80 | MixTime_s | Mixer HMI (supervisor) | mixing time |

**Default recipes (invented):** R1 800/500/400/200/100 kg · R2 600/600/400/300/100 · R3 1000/0/500/300/200 · R4 500/500/500/500/0. Each batch must total more than 0 and at most 2 500 kg. Default mixing time 60 s.

## Batch sequence (state machine)

| State | Name | Does | Leaves when |
|---|---|---|---|
| 0 | IDLE | everything off | Start pressed in Semi-auto or Auto with no trip active → 5 |
| 5 | LOAD_RECIPE | copy recipe to targets; clear the batch record; check total ≤ 2 500 kg and each silo holds target + 500 kg | OK → 10; else back to 0 with a "not enough material" warning |
| 10 | START_CHECKS | wait for door closed and no trip | all gates homed → 20, else → 12 |
| 12 | HOME_GATES | home command to the gate drives | all homed → 20; 15 s → homing timeout trip |
| 20 | START_MIXER | mixer on (it turns through filling, mixing and discharge) | running feedback → 30 (or back to a held mix/discharge step) |
| 30 | START_C2 | **downstream first**: start the incline belt | zero-speed switch proves it → 40 |
| 40 | START_C1 | then the collecting belt (interlocked: C2 must be proven) | proven → 50 (or 70 if resuming a run-out) |
| 50 | SELECT_SILO | next silo with a target and not done; record its start weight once | found → 60 (Semi-auto waits for Next); none left → 70 |
| 60 | FEED | loss-in-weight: dispensed = start weight − now. Gate 100 % while remaining > dribble point (max of 30 kg, 10 % of target), then 25 % (dribble). Close when remaining ≤ in-flight | → 62 |
| 62 | SETTLE | gate closed, wait 2 s for the material in the air to land and the reading to settle | → 64 |
| 64 | CHECK_WEIGHT | error = actual − target; tolerance = max(5 kg, 1 %) | in tolerance → adapt in-flight by half the error (only when no top-up was needed), mark done → 50. Under by more than tolerance → top-up at 25 % with a half in-flight cut-off (twice at most) → 60. Over, or still under → **tolerance trip** |
| 70 | RUNOUT_C1 | gates shut; C1 runs 25 s to empty | → 72 |
| 72 | RUNOUT_C2 | **upstream stops first**: C1 off, C2 runs 35 s | → 80 |
| 80 | MIX | count down the mixing time (resumes where it stopped after a hold) | 0 s → 90 |
| 90 | DOOR_OPEN | Semi-auto waits for Next; open the door | open switch → 92; 10 s → door-open timeout trip |
| 92 | DISCHARGE | door open 20 s | → 94 |
| 94 | DOOR_CLOSE | solenoid off | closed switch → 96; 10 s → door-close timeout trip |
| 96 | BATCH_DONE | count the batch | more to make and no stop requested → 5; else → 0 |
| 100 | HOLD | gates shut; each belt that was running when the hold began runs on to empty (C1 25 s, C2 60 s) unless tripped; mixer keeps turning unless it failed | Resume with no trip active → 10, which restarts the mixer, then C2, then C1, and carries on where it stopped. Abort → 0 |

Any trip in states 5–96 moves the sequence to HOLD and remembers the step. E-stop and Abort go straight to IDLE and drop the batch. Manual mode works only from IDLE.

**Manual and Semi-auto (Feeder HMI).** Manual drives each device on its own: belts, mixer, door, gate homing and gate openings. The same interlocks stay active: C1 can't run unless C2 is running and proven, and no gate opens unless C1 is running and proven. Semi-auto is the Auto sequence with a stop for **Next** before each silo and before opening the door, for step-by-step checks.

## Interlocks and alarms

**Interlocks (every mode):**
- C1 runs only while C2 is commanded and its zero-speed switch proves it is moving, so material never piles up in the transfer chute.
- Every gate is forced shut unless C1 is commanded and proven moving, so material never drops onto a stopped belt.
- A tripped belt stops; because of the first rule, everything upstream of it stops too.
- E-stop: every output off, sequence to IDLE. In a real plant the E-stop is a hardwired safety circuit; the PLC only watches it. **This lab is not a safety system.**

**Alarm word 1 (%MW15):**

| Bit | Alarm | Type | Detected by |
|---|---|---|---|
| 0 | E-stop | trip | E-stop input low |
| 1 | Remote I/O comms lost | trip | heartbeat unchanged for 2 s |
| 2 / 3 | C1 / C2 VFD trip | trip | VFD fault input |
| 4 / 5 | C1 / C2 zero speed | trip | run command on, speed switch off for 5 s |
| 6 | Mixer failed to run | trip | run command on, no feedback for 3 s |
| 7 / 8 | Door open / close timeout | trip | limit switch not reached in 10 s |
| 9 | Gate drive fault | trip | fault bit in a drive status word |
| 10 | Weight out of tolerance | trip | CHECK_WEIGHT |
| 11 | No material flow | trip | gate ≥ 20 % open and less than 2 kg weighed out in 8 s (empty or bridged silo) |
| 12 | Weight signal fault | trip | raw below 3.6 mA (broken loop) or above 20.4 mA |
| 13 | Silo low level | warning | weight below 2 000 kg |
| 14 | Not enough material to start | warning | LOAD_RECIPE check |
| 15 | Gate homing timeout | trip | HOME_GATES over 15 s |

**Alarm word 2 (%MW16):** bits 0–4 low level silo 1–5, bits 5–9 gate drive fault 1–5, bits 10–14 weight signal fault silo 1–5. These say *which* silo.

**Lamp and sounder.** The lamp flashes while any trip is active, and is steady for a warning alone (such as a low silo). The sounder comes on whenever a new alarm bit appears, including a silo going low, and stays on until someone presses Reset + acknowledge.

**Reset + acknowledge.** Silences the sounder and sends a 1-second reset pulse to both VFDs and the gate drives. At the end of the pulse every latched trip clears; any whose cause is still there comes back on the next scan. A gate drive that faulted loses its home, so the next start or resume homes the gates first.

## The seven faults

Each fault is injected from the simulator console (`fault F3 on`), except F6 (a program file) and F7 (an HMI tag). They follow the owner's real tasks, in the order the owner traces faults: check what the HMI says, look at the program online, check the I/O and its configuration, then the field device.

| # | Owner's task | Fault in the lab | Symptom | What the online program shows | Cause | Fix |
|---|---|---|---|---|---|---|
| F1 | Sensor check | Silo 3 weight transmitter loop broken during its feed | Batch holds while weighing Material C; lamp flashing; "Silo 3 weight signal fault" | `IR_Weight3` raw = 0 (0 mA, below the 3.6 mA limit); `WeightKg[3]` reads about −5 000 kg; gate 3 setpoint 0 | Load-cell transmitter 4–20 mA loop open (cable or junction box) | Measure the loop current with a meter, repair the cable, `fault F1 off`; Reset, Resume. The batch carries on from the weight already dispensed. |
| F2 | Module / I-O card configuration | Remote rack's node-address switches set to 2 after a card swap (the master polls node 1) | Everything stops; "Remote I/O comms lost"; HMI values frozen | Heartbeat `IR_Heartbeat` stops changing; OpenPLC log shows "Modbus Read ... failed" for the slave device; every input frozen at its last value | Node address on the replacement module doesn't match the configuration | Compare the module's address switches with the PLC's slave-device settings, set it back to 1 (`fault F2 off`); Reset, Resume. |
| F3 | VFD / inverter check | Conveyor 1 drags (seized return idlers): the drive trips on overload once the belt is loaded | C1 stops during a feed, gates close, C2 runs on and stops; "Conveyor 1 VFD trip" | `DI_C1_Fault` on, `IR_C1_FaultCode` = 2 (motor overload), current rose above 21 A before the trip | Mechanical drag on the belt, not an electrical fault. Reset alone makes it run, then trip again within seconds of loading. | Find and free the drag (`fault F3 off`), then Reset and Resume. Lesson: never just keep resetting a drive. |
| F4 | Stepper / gate drive check | Gate 4 jammed by caked material | Holds when Material D starts; "Gate 4 drive fault" | `IR_GateStatus4` fault bit (16#0008) on, homed bit off; `IR_GateAlarm4` = 1 (stall); position stuck near 2 % | Lump jamming the gate blade | Isolate, clear the jam (`fault F4 off`), Reset; Resume homes the gates automatically, then feeds. If the jam is still there it stalls again. |
| F5 | Output on but the device doesn't move | Discharge door solenoid wire open between output card and valve | Mix finishes, door never opens; "Discharge door open timeout"; batch held in the mixer | `DO_Door_OpenSol` TRUE (output LED on), `DI_Door_Open` stays FALSE, `DI_Door_Closed` stays TRUE | Broken wire or loose terminal after the output card | With the output on, measure 24 V at the card terminal (present), then at the valve coil (absent): wire fault. Repair (`fault F5 off`), Reset, Resume. |
| F6 | Program edit and download | A copy-paste edit in LOAD_RECIPE loads Material A's setpoint into silo 2 (`plc/faults/F6_batching_bad_edit.st`) | No alarm. Batches come out off-ratio: silo 2 weighs out 800 kg instead of 500 kg on recipe 1 | `HMI_Target2` = 800 while `HMI_R1_B` = 500; `TargetKg[2] := RecipeKg[RecipeBase + 1]` in the program | Bad edit downloaded without comparing to the last good backup | Compare the running program with the backup (a file diff), restore the correct line, download, run a test batch. Lesson: the PLC does exactly what it is told. |
| F7 | HMI changes | Feeder HMI "Silo 4 weight" tag points one register too far (1048 instead of 1047) | HMI shows silo 4 dropping while Material E is weighed: looks like a leaking gate 4 | PLC's `HMI_Weight4` steady and correct; the HMI number matches `HMI_Weight5` | Off-by-one address (0-based vs 1-based numbering) in the tag | Check each HMI tag against this map, change one value at a time and watch which display moves; fix the address. Lesson: check the PLC before believing the HMI. |

Each fault gets its own page and video in CP-11c, written in this order: symptom → online view → cause → fix → proof.

## What the tests prove (and don't)

`python -m unittest` runs the plant simulator with the soft-PLC copy of the logic. The tests cover a full batch (state order, every material within tolerance, mass balance, nothing on the floor, belts started downstream first and stopped upstream first), in-flight learning, Semi-auto and Manual, warnings, E-stop, all seven faults (symptom, alarm, fix, finished batch), the Modbus server, and that the ST program's addresses and steps match `lab/iomap.py`.

They do **not** compile `plc/batching.st`: that happens the first time it is uploaded to OpenPLC (CP-11c). Until then the ST file is checked by review and by its match with the tested Python copy.
