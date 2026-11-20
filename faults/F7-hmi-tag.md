# F7 · HMI change: a tag pointing one register too far

**Mirrors:** making HMI changes. **Plant:** while editing the Feeder HMI, someone typed the "Silo 4 weight" tag address one too high. FUXA counts from 1 and the PLC map from 0, so off-by-one mistakes are easy.

**Inject:** in FUXA → Connections → BatchPLC → tag `Weight4`, change the address offset from **1048** to **1049**. **Repair:** set it back to 1048.

## 0. Symptom (HMI)

- No alarm.
- While **silo 5** (Material E) is weighing out, the Feeder HMI shows **silo 4's weight dropping** (2 600 → 2 565 kg in 5 s). It looks like gate 4 is leaking. Someone could spend an hour on the wrong gate.

## 1. Check the I/O

- Gate 4: position 0, no alarm. Gate 5 is open (25 %, dribble).
- The real silo 4 weight is steady (5 804 kg).

## 2. Program online (the PLC is right)

In OpenPLC Monitoring:

| Tag | Value |
|---|---|
| `HMI_Weight4` (%MW23) | **5 804 kg, steady** |
| `HMI_Weight5` (%MW24) | 2 600 → 2 565 kg, falling |

What the HMI calls "silo 4" is really %MW24, silo 5.

## 3. Configuration (this is the fault)

- **The map:** `hmi/fuxa-tags.csv` says `Weight4` = register 1047 (0-based) = FUXA offset **1048**. The tag says 1049 = silo 5.
- **The check:** change one PLC value at a time and watch which HMI number moves. In the lab, typing `refill 4 9000` at `lab>` changes the real silo 4, but the wrong tag doesn't move.

## 4. Repair and prove

1. Set `Weight4` back to offset 1048.
2. Repeat the one-value check: refill silo 4 and the right display moves.
3. If you rebuilt the tags with `python hmi/make_fuxa_device.py`, it regenerates every address from the map.

## Recording script (about 2 min)

1. "Silo 5 is feeding … but the HMI says silo 4 is dropping. Leaking gate?"
2. "Gate 4 is closed, no alarm. Check the PLC itself: Monitoring says silo 4 is steady. The HMI is lying."
3. "The tag's address is one too high: it's showing silo 5."
4. Fix the address; refill silo 4 and show the right number move.

**Lesson:** check the PLC before you believe the HMI. Test every HMI change by moving one value and watching which display follows.
