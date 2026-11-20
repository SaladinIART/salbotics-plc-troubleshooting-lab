"""Instructor panel: switch plant faults without the simulator's console.

    python3 tools/instructor.py F3 on        # inject
    python3 tools/instructor.py F3 off       # repair
    python3 tools/instructor.py refill       # refill all five silos
    python3 tools/instructor.py status       # which faults are on

Talks to the plant simulator's Modbus server as unit 99 (OpenPLC uses unit 1 and
never touches these coils). Run it where the simulator runs: inside WSL, e.g.
    wsl -d Ubuntu-22.04-D -- python3 /mnt/d/Dev/plc/salbotics-plc-troubleshooting-lab/tools/instructor.py F3 on
"""

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lab.iomap import INSTRUCTOR_FAULT_COILS, INSTRUCTOR_REFILL_COIL, INSTRUCTOR_UNIT  # noqa: E402
from lab.modbus import ModbusClient  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", help="F1..F5, refill or status")
    ap.add_argument("state", nargs="?", choices=["on", "off"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5020)
    a = ap.parse_args()
    c = ModbusClient(a.host, a.port, unit=INSTRUCTOR_UNIT, timeout=2)
    try:
        what = a.what.upper()
        if what in INSTRUCTOR_FAULT_COILS and a.state:
            c.write_coil(INSTRUCTOR_FAULT_COILS[what], a.state == "on")
        elif what == "REFILL":
            c.write_coil(INSTRUCTOR_REFILL_COIL, True)
        elif what != "STATUS":
            ap.error("use F1..F5 on|off, refill or status")
        bits = c.read_coils(min(INSTRUCTOR_FAULT_COILS.values()), len(INSTRUCTOR_FAULT_COILS))
        on = [code for code, b in zip(INSTRUCTOR_FAULT_COILS, bits) if b]
        print("faults on:", ", ".join(on) or "none")
    finally:
        c.close()


if __name__ == "__main__":
    main()
