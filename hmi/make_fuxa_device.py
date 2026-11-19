"""Create or update the "BatchPLC" Modbus TCP device in FUXA with every HMI tag.

    python hmi/make_fuxa_device.py                   # soft-PLC, 127.0.0.1:5021
    python hmi/make_fuxa_device.py --plc 127.0.0.1:502   # OpenPLC
    python hmi/make_fuxa_device.py --dry-run         # print the JSON only

Tags come from lab/iomap.py (%MWn = holding register 1024 + n, 0-based).
FUXA's "Address offset" counts from 1, so offset = register + 1
(checked on FUXA 1.3.1: offset 1105 reads %MW80 = 60).

Reload the FUXA editor page afterwards so it shows the new tags.
"""

import argparse
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lab.iomap import MW, MW_BASE, MW_WORDS  # noqa: E402

FUXA = "http://127.0.0.1:1881"
DESCRIPTIONS = {
    "ModeReq": "write 1 Manual, 2 Semi-auto, 3 Auto (idle only)",
    "Cmd": "write 1 Start, 2 Stop at end, 3 Hold, 4 Resume, 5 Reset, 6 Next, 7 Abort",
    "ManualBits": "bit0 C2, bit1 C1, bit2 mixer, bit3 door, bit4 home gates",
    "Alarm1": "bit-packed alarms, see DESIGN.md",
    "Alarm2": "per-silo alarms, see DESIGN.md",
    "Status": "bit0 running, bit1 held, bit2 waiting Next, bit3 accepted, bit4 not enough",
}
DIVISORS = {**{f"Inflight{i}": 10 for i in range(1, 6)}, **{f"GatePos{i}": 10 for i in range(1, 6)},
            "C1_Freq": 10, "C1_Current": 10, "C2_Freq": 10, "C2_Current": 10}


def get(path):
    with urllib.request.urlopen(FUXA + path, timeout=5) as r:
        return json.load(r)


def build(project, plc_address):
    devices = project.get("devices", {})
    dev = next((d for d in devices.values() if d.get("name") == "BatchPLC"), None)
    if dev is None:
        dev = {"id": "d_batchplc-lab", "name": "BatchPLC", "type": "ModbusTCP", "enabled": True,
               "polling": 500, "tags": {}}
    dev["property"] = {"address": plc_address, "port": None, "slot": None, "rack": None,
                       "slaveid": "1", "baudrate": 9600, "databits": 8, "stopbits": 1,
                       "parity": "None", "connectionOption": "TcpPort", "delay": 10,
                       "forceFC16": False}
    by_name = {t["name"]: t for t in dev.get("tags", {}).values()}
    tags = {}
    for name, n in MW.items():
        reg = MW_BASE + n
        old = by_name.get(name)
        tid = old["id"] if old else f"t_batchplc-mw{n:03d}"
        tags[tid] = {
            "id": tid, "name": name,
            "type": "UInt16" if name in MW_WORDS else "Int16",
            "memaddress": "400000", "address": reg + 1,
            "divisor": DIVISORS.get(name),
            "daq": {"enabled": False, "interval": 60, "changed": False, "restored": False},
            "description": f"%MW{n} (register {reg}, 0-based). {DESCRIPTIONS.get(name, '')}".strip(),
        }
    dev["tags"] = tags
    return dev


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plc", default="127.0.0.1:5021", help="PLC ip:port (OpenPLC is 127.0.0.1:502)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dev = build(get("/api/project"), args.plc)
    if args.dry_run:
        print(json.dumps(dev, indent=1))
        return
    body = json.dumps({"cmd": "set-device", "data": dev}).encode()
    req = urllib.request.Request(FUXA + "/api/projectData", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        print("FUXA:", r.status, f"BatchPLC -> {args.plc}, {len(dev['tags'])} tags")


if __name__ == "__main__":
    main()
