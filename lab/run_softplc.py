"""Run plant + soft-PLC together and serve the PLC's Modbus map to the HMIs.

    python -m lab.run_softplc --hmi-port 5021 [--f6]

The map matches OpenPLC v3, so FUXA tags work unchanged with either:
  %MWn       -> holding register 1024 + n   (HMI tags, see DESIGN.md)
  %IW100+n   -> input register 100 + n      (raw rack inputs)
  %IX100.0+  -> discrete input 800 + n
  %QX100.0+  -> coil 800 + n
  %QW100+n   -> holding register 100 + n
"""

import argparse
import threading
import time

from .iomap import MW, MW_BASE, MW_COUNT
from .modbus import DataStore, ModbusServer, s16
from .rig import Rig, console


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--hmi-port", type=int, default=5021)
    ap.add_argument("--f6", action="store_true", help="run the program with the F6 bad edit")
    args = ap.parse_args()

    rig = Rig(f6_bad_edit=args.f6)
    plc = rig.plc
    store = DataStore(co=1024, di=1024, hr=MW_BASE + MW_COUNT, ir=1024)
    lock = store.lock
    stop = threading.Event()

    def loop():
        nxt = time.monotonic()
        while not stop.is_set():
            with lock:
                plc.mw[:] = [s16(v) for v in store.hr[MW_BASE:MW_BASE + MW_COUNT]]  # HMI writes in
                rig.tick()
                store.hr[MW_BASE:MW_BASE + MW_COUNT] = plc.mw
                store.ir[100:100 + len(plc.ir)] = plc.ir
                store.di[800:800 + len(plc.di)] = plc.di
                store.co[800:800 + len(plc.co)] = plc.co
                store.hr[100:100 + len(plc.hr)] = plc.hr
            nxt += 0.1
            time.sleep(max(0.0, nxt - time.monotonic()))

    with lock:  # first scan loads the default recipes before the HMI connects
        rig.tick()
        store.hr[MW_BASE:MW_BASE + MW_COUNT] = plc.mw
    server = ModbusServer(store, args.host, args.hmi_port)
    server.start()
    threading.Thread(target=loop, daemon=True).start()
    print(f"soft-PLC HMI map on {args.host}:{args.hmi_port}{'  [F6 bad edit loaded]' if args.f6 else ''}")
    try:
        def set_hmi(tag, value):
            store.hr[MW_BASE + MW[tag]] = s16(value)
        console(rig.plant, lock, plc, set_hmi)
    finally:
        stop.set()
        server.shutdown()


if __name__ == "__main__":
    main()
