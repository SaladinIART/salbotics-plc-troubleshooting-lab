"""Run the plant simulator as a Modbus TCP remote I/O rack for OpenPLC.

    python3 -m lab.run_plant --host 127.0.0.1 --port 5020

OpenPLC (Slave Devices) polls it: generic TCP device, slave ID 1, this IP and port.
Type `help` at the lab> prompt for fault injection.
"""

import argparse
import threading
import time

from .modbus import ModbusServer
from .plant import Plant
from .rig import console


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1", help="listen address (0.0.0.0 to accept other machines)")
    ap.add_argument("--port", type=int, default=5020)
    args = ap.parse_args()

    plant = Plant()
    lock = plant.store.lock
    server = ModbusServer(plant.store, args.host, args.port)
    server.start()
    stop = threading.Event()

    def loop():
        nxt = time.monotonic()
        while not stop.is_set():
            with lock:
                plant.step(0.1)
            nxt += 0.1
            time.sleep(max(0.0, nxt - time.monotonic()))

    threading.Thread(target=loop, daemon=True).start()
    print(f"plant rack listening on {args.host}:{args.port} (unit 1)")
    try:
        console(plant, lock)
    finally:
        stop.set()
        server.shutdown()


if __name__ == "__main__":
    main()
