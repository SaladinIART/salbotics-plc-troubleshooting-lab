# Salbotics PLC troubleshooting lab

A weigh-batching cell you can break on purpose and fix: five silos on load cells, two conveyors up three storeys, a rotary mixer, two HMIs, and seven faults taken from real maintenance work (sensor, I/O module setting, VFD trip, gate stepper drive, output wiring, bad program edit, HMI tag).

**A demonstration rebuilt with open tools.** It is not a copy of any company's program, and the materials (A–E), recipes and numbers are invented.

- Design, I/O list, register map, sequence, alarms and the seven faults: [DESIGN.md](DESIGN.md)
- PLC program (IEC 61131-3 Structured Text for OpenPLC): [plc/batching.st](plc/batching.st)
- HMI tag list for FUXA: [hmi/fuxa-tags.csv](hmi/fuxa-tags.csv)

## Status

| Part | State |
|---|---|
| Design, plant simulator, soft-PLC, tests (34, all passing) | done |
| `plc/batching.st` | **compiles in OpenPLC Runtime v3** (2026-11-20; one fix: one timer per declaration line, because v3's compiler crashes on `A, B : TON;`) |
| FUXA screens, one write-up and video per fault | next (needs OpenPLC and FUXA installed) |

## Quick start without installing anything

Needs Python 3.10 or newer (standard library only).

```
python -m unittest                      # 34 tests: full batch, modes, all seven faults
python -m lab.run_softplc               # plant + soft-PLC; HMI map on 127.0.0.1:5021
```

At the `lab>` prompt: `cmd 1` starts a batch, `status` shows plant and PLC, `fault F3 on` breaks conveyor 1, `cmd 5` resets, `cmd 4` resumes. Type `help` for the rest.

## Full lab: OpenPLC + plant simulator + FUXA

Everything stays on D: (the WSL disk is `D:\WSL\Ubuntu-22.04`; FUXA goes in `D:\Tools\fuxa`). Install only from the official sources below.

### 1. OpenPLC Runtime v3 (in WSL)

Source: https://github.com/thiagoralves/OpenPLC_v3 (GPL-3.0). The project page marks v3 end-of-life and points to v4, but v3 is used here because it can upload a `.st` file from its web page, poll a remote Modbus device, and serve Modbus to the HMI (see DESIGN.md, decision 4).

```
wsl -d Ubuntu-22.04-D
cd ~
git clone https://github.com/thiagoralves/OpenPLC_v3.git
cd OpenPLC_v3
./install.sh linux
sudo ./start_openplc.sh
```

Then open http://localhost:8080. v3's default login is `openplc` / `openplc`; change it after the first login. Check these steps against the project README on the day you install; the install script takes a while.

### 2. Plant simulator (the remote I/O rack)

In a second WSL terminal (Ubuntu 22.04 has Python 3.10):

```
cd /mnt/d/Dev/plc/salbotics-plc-troubleshooting-lab
python3 -m lab.run_plant --host 127.0.0.1 --port 5020
```

In the OpenPLC web page, **Slave Devices → Add new device**:
- Device type: Generic Modbus TCP device · Slave ID: **1** · IP: 127.0.0.1 · Port: 5020
- Discrete Inputs: start 0, size 16 → %IX100.0
- Coils: start 0, size 16 → %QX100.0
- Input Registers: start 0, size 27 → %IW100
- Holding Registers – Read: start 0, size 0
- Holding Registers – Write: start 0, size 7 → %QW100

The page shows the resulting addresses; they must match the table in DESIGN.md.

### 3. Load the program

**Programs → Upload Program** → `plc/batching.st` → compile → **Start PLC**. The first compile is the first real check of the ST file; if OpenPLC reports an error, fix it in both `plc/batching.st` and `lab/controller.py` and rerun the tests.

Watch tags live under **Monitoring**.

### 4. FUXA (on Windows, Node.js 22)

Source: https://github.com/frangoteam/FUXA (MIT). Node.js v22 is already installed.

1. Install the lighter official package (no Siemens S7 driver; Modbus works), keeping everything on D: (installed this way on 2026-11-20, FUXA 1.3.1, about 250 MB):
   ```
   npm install -g @frangoteam/fuxa-min@1.3.1 --prefix D:\Tools\fuxa --cache D:\Tools\npm-cache
   ```
2. Start it with `D:\Tools\fuxa\start-fuxa.cmd`. It runs from `D:\Tools\fuxa`, so projects are saved in `D:\Tools\fuxa\_appdata`. Close the window to stop it.
3. Open http://localhost:1881/editor to build screens (Chrome is recommended); http://localhost:1881 shows the running HMI.
4. Add a Modbus TCP device: 127.0.0.1, port **502** (OpenPLC), or port **5021** for the soft-PLC.
5. Add the tags: run `python hmi/make_fuxa_device.py` (soft-PLC) or `python hmi/make_fuxa_device.py --plc 127.0.0.1:502` (OpenPLC) while FUXA is running, then reload the editor. It creates the `BatchPLC` device with all 75 HMI tags from [hmi/fuxa-tags.csv](hmi/fuxa-tags.csv). **FUXA's address offset counts from 1: offset = 0-based register + 1** (checked on FUXA 1.3.1: offset 1105 reads `MixTime_s` = 60). Fault F7 is exactly this kind of mistake.
6. Add the two screens (both share the helpers in `hmi/fuxa_view.py`):
   - `python hmi/make_fuxa_mixer_view.py` → **Mixer HMI** (operator): batch status, recipe / batch count / mixing time inputs, Start, Stop at end, Hold, Resume, Reset + ack, Next and Abort, and the per-material target / actual / silo / gate / in-flight table. Open http://localhost:1881/home?viewName=Mixer%20HMI
   - `python hmi/make_fuxa_feeder_view.py` → **Feeder HMI** (maintenance): Manual / Semi-auto / Auto, the sequence buttons, silo weights, gate positions and alarm codes, manual gate setpoints, manual device presets (including "C1 alone" to show the interlock), VFD frequency, current and fault codes, and the alarm words. Open http://localhost:1881/home?viewName=Feeder%20HMI

   Inputs send their value when you press Enter. Manual presets write the whole ManualBits word, so each press replaces the last one.

### Fault injection

At the simulator's `lab>` prompt: `fault F1 on` … `fault F5 on`, and `off` to repair. F6 is a program file: upload `plc/faults/F6_batching_bad_edit.st` instead of the normal program (soft-PLC: `python -m lab.run_softplc --f6`). F7 is an HMI tag: in FUXA, change `Weight4`'s address offset from 1048 to 1049 (register 1048, which is silo 5).

## Licences

| Part | Licence |
|---|---|
| This lab's code and PLC program | MIT ([LICENSE](LICENSE)) |
| This lab's documents and fault write-ups | CC BY 4.0 |
| OpenPLC Runtime v3 | GPL-3.0 (installed separately, not included) |
| FUXA | MIT (installed separately, not included) |
