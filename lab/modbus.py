"""Minimal Modbus TCP server and client, Python standard library only.

Supports function codes 1, 2, 3, 4, 5, 6, 15 and 16, which is all OpenPLC and
FUXA use here. Not a general-purpose Modbus stack.
"""

import socket
import socketserver
import struct
import threading

ILLEGAL_FUNCTION, ILLEGAL_ADDRESS, ILLEGAL_VALUE = 1, 2, 3


class DataStore:
    """Four Modbus tables plus a lock.

    co = coils, di = discrete inputs (bools); hr = holding, ir = input registers
    (ints, stored as signed or unsigned, sent as unsigned 16-bit).
    `unit_ids`: the unit IDs this device answers; None answers any.
    `on_request(unit)`: called (under the lock) after every request it answered.
    """

    def __init__(self, co=0, di=0, hr=0, ir=0, unit_ids=None, on_request=None):
        self.co = [False] * co
        self.di = [False] * di
        self.hr = [0] * hr
        self.ir = [0] * ir
        self.unit_ids = unit_ids
        self.on_request = on_request
        self.lock = threading.RLock()

    def accepts(self, unit):
        return self.unit_ids is None or unit in self.unit_ids

    def handle(self, pdu):
        """Process one request PDU, return the response PDU."""
        if not pdu:
            return bytes([0x80, ILLEGAL_FUNCTION])
        fc = pdu[0]
        try:
            if fc in (1, 2):
                start, count = struct.unpack(">HH", pdu[1:5])
                table = self.co if fc == 1 else self.di
                if not 1 <= count <= 2000:
                    return _exc(fc, ILLEGAL_VALUE)
                if start + count > len(table):
                    return _exc(fc, ILLEGAL_ADDRESS)
                bits = table[start:start + count]
                data = bytearray((count + 7) // 8)
                for n, b in enumerate(bits):
                    if b:
                        data[n // 8] |= 1 << (n % 8)
                return bytes([fc, len(data)]) + bytes(data)
            if fc in (3, 4):
                start, count = struct.unpack(">HH", pdu[1:5])
                table = self.hr if fc == 3 else self.ir
                if not 1 <= count <= 125:
                    return _exc(fc, ILLEGAL_VALUE)
                if start + count > len(table):
                    return _exc(fc, ILLEGAL_ADDRESS)
                vals = [v & 0xFFFF for v in table[start:start + count]]
                return bytes([fc, 2 * count]) + struct.pack(f">{count}H", *vals)
            if fc == 5:
                addr, value = struct.unpack(">HH", pdu[1:5])
                if value not in (0x0000, 0xFF00):
                    return _exc(fc, ILLEGAL_VALUE)
                if addr >= len(self.co):
                    return _exc(fc, ILLEGAL_ADDRESS)
                self.co[addr] = value == 0xFF00
                return pdu[:5]
            if fc == 6:
                addr, value = struct.unpack(">HH", pdu[1:5])
                if addr >= len(self.hr):
                    return _exc(fc, ILLEGAL_ADDRESS)
                self.hr[addr] = s16(value)
                return pdu[:5]
            if fc == 15:
                start, count, nbytes = struct.unpack(">HHB", pdu[1:6])
                if not 1 <= count <= 1968 or nbytes != (count + 7) // 8:
                    return _exc(fc, ILLEGAL_VALUE)
                if start + count > len(self.co):
                    return _exc(fc, ILLEGAL_ADDRESS)
                data = pdu[6:6 + nbytes]
                for n in range(count):
                    self.co[start + n] = bool(data[n // 8] >> (n % 8) & 1)
                return pdu[:5]
            if fc == 16:
                start, count, nbytes = struct.unpack(">HHB", pdu[1:6])
                if not 1 <= count <= 123 or nbytes != 2 * count:
                    return _exc(fc, ILLEGAL_VALUE)
                if start + count > len(self.hr):
                    return _exc(fc, ILLEGAL_ADDRESS)
                vals = struct.unpack(f">{count}H", pdu[6:6 + nbytes])
                for n, v in enumerate(vals):
                    self.hr[start + n] = s16(v)
                return pdu[:5]
        except struct.error:
            return _exc(fc, ILLEGAL_VALUE)
        return _exc(fc, ILLEGAL_FUNCTION)


def _exc(fc, code):
    return bytes([fc | 0x80, code])


def s16(v):
    """Unsigned 16-bit -> signed (what an IEC INT holds)."""
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed")
        buf += chunk
    return buf


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        store = self.server.store
        sock = self.request
        while True:
            try:
                head = _recv_exact(sock, 7)
                tid, pid, length, unit = struct.unpack(">HHHB", head)
                if length < 2 or length > 254:
                    return
                pdu = _recv_exact(sock, length - 1)
            except (ConnectionError, OSError):
                return
            if pid != 0 or not store.accepts(unit):
                continue  # wrong node address: stay silent, the master times out
            with store.lock:
                resp = store.handle(pdu)
                if store.on_request and not resp[0] & 0x80:
                    store.on_request(unit)
            try:
                sock.sendall(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)
            except OSError:
                return


class ModbusServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, store, host="127.0.0.1", port=5020):
        self.store = store
        super().__init__((host, port), _Handler)

    def start(self):
        t = threading.Thread(target=self.serve_forever, daemon=True)
        t.start()
        return t


class ModbusError(Exception):
    pass


class ModbusClient:
    """Tiny blocking client, used by the tests and the console."""

    def __init__(self, host="127.0.0.1", port=5020, unit=1, timeout=1.0):
        self.unit = unit
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.tid = 0

    def close(self):
        self.sock.close()

    def _call(self, pdu):
        self.tid = (self.tid + 1) & 0xFFFF
        self.sock.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, self.unit) + pdu)
        head = _recv_exact(self.sock, 7)
        tid, _, length, _ = struct.unpack(">HHHB", head)
        resp = _recv_exact(self.sock, length - 1)
        if tid != self.tid:
            raise ModbusError("transaction id mismatch")
        if resp[0] & 0x80:
            raise ModbusError(f"exception code {resp[1]}")
        return resp

    def _read_bits(self, fc, start, count):
        resp = self._call(struct.pack(">BHH", fc, start, count))
        data = resp[2:]
        return [bool(data[n // 8] >> (n % 8) & 1) for n in range(count)]

    def _read_regs(self, fc, start, count):
        resp = self._call(struct.pack(">BHH", fc, start, count))
        return list(struct.unpack(f">{count}H", resp[2:2 + 2 * count]))

    def read_coils(self, start, count):
        return self._read_bits(1, start, count)

    def read_discrete_inputs(self, start, count):
        return self._read_bits(2, start, count)

    def read_holding(self, start, count):
        return self._read_regs(3, start, count)

    def read_input(self, start, count):
        return self._read_regs(4, start, count)

    def write_coil(self, addr, value):
        self._call(struct.pack(">BHH", 5, addr, 0xFF00 if value else 0))

    def write_register(self, addr, value):
        self._call(struct.pack(">BHH", 6, addr, value & 0xFFFF))

    def write_coils(self, start, values):
        data = bytearray((len(values) + 7) // 8)
        for n, v in enumerate(values):
            if v:
                data[n // 8] |= 1 << (n % 8)
        self._call(struct.pack(">BHHB", 15, start, len(values), len(data)) + bytes(data))

    def write_registers(self, start, values):
        vals = [v & 0xFFFF for v in values]
        self._call(struct.pack(f">BHHB{len(vals)}H", 16, start, len(vals), 2 * len(vals), *vals))
