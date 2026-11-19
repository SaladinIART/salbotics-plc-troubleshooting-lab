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
| `plc/batching.st` | written and checked against the tested Python copy; **not yet compiled in OpenPLC** |
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

1. Download the latest release zip from https://github.com/frangoteam/FUXA/releases and unpack it to `D:\Tools\fuxa`.
2. In PowerShell:
   ```
   cd D:\Tools\fuxa\server
   npm install --cache D:\Tools\npm-cache
   npm start
   ```
   The `--cache` flag keeps npm's download cache off C:.
3. Open http://localhost:1881 (Chrome is recommended).
4. Add a Modbus TCP device: 127.0.0.1, port **502** (OpenPLC), or port **5021** for the soft-PLC.
5. Add the tags in [hmi/fuxa-tags.csv](hmi/fuxa-tags.csv): all are holding registers at the 0-based address in `register_0_based`. **Check with one tag first** (for example `State`, register 1035) whether your FUXA version counts addresses from 0 or 1, then build the two screens. Fault F7 is exactly this mistake.

### Fault injection

At the simulator's `lab>` prompt: `fault F1 on` … `fault F5 on`, and `off` to repair. F6 is a program file: upload `plc/faults/F6_batching_bad_edit.st` instead of the normal program (soft-PLC: `python -m lab.run_softplc --f6`). F7 is an HMI tag: point the "Silo 4 weight" tag at 1048 instead of 1047.

## Licences

| Part | Licence |
|---|---|
| This lab's code and PLC program | MIT ([LICENSE](LICENSE)) |
| This lab's documents and fault write-ups | CC BY 4.0 |
| OpenPLC Runtime v3 | GPL-3.0 (installed separately, not included) |
| FUXA | MIT (installed separately, not included) |
