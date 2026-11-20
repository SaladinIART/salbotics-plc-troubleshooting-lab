"""Single source of truth for every address in the lab.

Two Modbus maps:

1. The remote I/O station (the plant simulator, unit ID 1). OpenPLC polls it as a
   "slave device", the way the master PLC polls a remote I/O rack. OpenPLC v3 puts
   the first slave device's data at %IX100.0 (discrete inputs), %QX100.0 (coils),
   %IW100 (input registers) and %QW100 (holding registers it writes).
   Confirmed in OpenPLC_v3 webserver/core/modbus_master.cpp (index 100+).

2. The PLC's own map that the HMIs (FUXA) read and write. OpenPLC v3 serves
   %MWn as holding register 1024 + n (modbus.cpp, MIN_16B_RANGE = 1024).

All addresses are 0-based protocol addresses (what goes on the wire).
"""

UNIT_ID = 1  # the station's node address ("DIP switches" on the real rack)

# ---- Remote I/O station --------------------------------------------------

DI = {  # discrete inputs (FC2) -> %IX100.0 ...
    "EStopOK": 0,      # safety relay healthy (TRUE = not pressed)
    "C1_Run": 1,       # conveyor 1 VFD run feedback
    "C1_Fault": 2,     # conveyor 1 VFD fault relay
    "C1_SpeedOK": 3,   # conveyor 1 zero-speed switch: belt moving
    "C2_Run": 4,
    "C2_Fault": 5,
    "C2_SpeedOK": 6,
    "Mix_Run": 7,      # mixer motor contactor feedback
    "Door_Open": 8,    # mixer discharge door open limit switch
    "Door_Closed": 9,  # mixer discharge door closed limit switch
}
DI_COUNT = 16

DO = {  # coils (FC1/5/15) -> %QX100.0 ...
    "C1_RunCmd": 0,
    "C1_Reset": 1,
    "C2_RunCmd": 2,
    "C2_Reset": 3,
    "Mix_RunCmd": 4,
    "Door_OpenSol": 5,  # discharge door solenoid (spring return closed)
    "AlarmLamp": 6,
    "Sounder": 7,
    "Gates_Enable": 8,  # enable for all five gate stepper drives
    "Gates_Reset": 9,
    "Gates_Home": 10,
}
DO_COUNT = 16

# Instructor panel on the same rack server, unit 99 (OpenPLC never polls it):
# coils 32-36 switch faults F1-F5 on/off, coil 40 refills every silo.
INSTRUCTOR_UNIT = 99
INSTRUCTOR_FAULT_COILS = {"F1": 32, "F2": 33, "F3": 34, "F4": 35, "F5": 36}
INSTRUCTOR_REFILL_COIL = 40
INSTRUCTOR_COIL_COUNT = 48

IR = {"Heartbeat": 0}  # input registers (FC4) -> %IW100 ...
for _i in range(1, 6):
    IR[f"Weight{_i}"] = _i                # weight transmitter, 4-20 mA as raw counts
for _i in range(1, 6):
    IR[f"GatePos{_i}"] = 5 + _i           # 0-1000 = 0.0-100.0 % open
for _i in range(1, 6):
    IR[f"GateStatus{_i}"] = 10 + _i       # bit0 ready, bit1 homed, bit2 in position, bit3 fault
for _i in range(1, 6):
    IR[f"GateAlarm{_i}"] = 15 + _i        # 0 none, 1 stall
IR.update({"C1_Freq": 21, "C1_Current": 22, "C1_FaultCode": 23,
           "C2_Freq": 24, "C2_Current": 25, "C2_FaultCode": 26})
IR_COUNT = 27

HR = {}  # holding registers the PLC writes (FC16) -> %QW100 ...
for _i in range(1, 6):
    HR[f"GateSP{_i}"] = _i - 1            # gate position setpoint 0-1000
HR.update({"C1_SpeedRef": 5, "C2_SpeedRef": 6})  # 0.1 Hz units
HR_COUNT = 7

# Raw scaling of the weight transmitters: raw = mA * 1600 (20 mA = 32000).
RAW_PER_MA = 1600
RAW_4MA = 6400
RAW_SPAN = 25600          # 4-20 mA
SILO_SPAN_KG = 20000.0    # 20 mA = 20 000 kg
RAW_WIRE_BREAK = 5760     # below 3.6 mA = broken loop
RAW_OVER_RANGE = 32640    # above 20.4 mA

GATE_BITS = {"ready": 0x0001, "homed": 0x0002, "inpos": 0x0004, "fault": 0x0008}
VFD_FAULT_CODES = {0: "none", 2: "OL motor overload"}
GATE_ALARM_CODES = {0: "none", 1: "stall (gate jammed)"}

# ---- PLC map for the HMIs: %MWn = holding register 1024 + n -------------

MW_BASE = 1024
MW = {"ModeReq": 0, "Cmd": 1, "RecipeSel": 2, "BatchReq": 3, "ManualBits": 4}
for _i in range(1, 6):
    MW[f"ManGateSP{_i}"] = 4 + _i          # 5..9
MW.update({"Mode": 10, "State": 11, "ActiveSilo": 12, "BatchesDone": 13,
           "MixRemain_s": 14, "Alarm1": 15, "Alarm2": 16, "Status": 17})
for _i in range(1, 6):
    MW[f"Weight{_i}"] = 19 + _i            # 20..24 kg
    MW[f"Target{_i}"] = 24 + _i            # 25..29 kg
    MW[f"Actual{_i}"] = 29 + _i            # 30..34 kg
    MW[f"Inflight{_i}"] = 34 + _i          # 35..39, 0.1 kg
    MW[f"GatePos{_i}"] = 39 + _i           # 40..44, 0.1 %
MW.update({"C1_Freq": 45, "C1_Current": 46, "C2_Freq": 47, "C2_Current": 48,
           "C1_FaultCode": 49, "C2_FaultCode": 50})
for _i in range(1, 6):
    MW[f"GateAlarm{_i}"] = 50 + _i         # 51..55
for _r in range(1, 5):
    for _m, _letter in enumerate("ABCDE"):
        MW[f"R{_r}_{_letter}"] = 60 + (_r - 1) * 5 + _m   # 60..79 recipe kg per batch
MW["MixTime_s"] = 80
MW_COUNT = 128

# Words declared WORD (bit-packed) in the PLC; everything else is INT.
MW_WORDS = {"ManualBits", "Alarm1", "Alarm2", "Status"}
IR_WORDS = {f"GateStatus{_i}" for _i in range(1, 6)}

MODES = {1: "Manual", 2: "Semi-auto", 3: "Auto"}
CMDS = {1: "Start", 2: "Stop at end of batch", 3: "Hold", 4: "Resume / accept",
        5: "Reset + acknowledge", 6: "Next (semi-auto)", 7: "Abort"}
MANUAL_BITS = {"C2": 0x0001, "C1": 0x0002, "Mixer": 0x0004, "Door": 0x0008, "Home": 0x0010}

ALARM1 = {  # bit -> name. Bits 13 and 14 are warnings; the rest are trips.
    0: "E-stop", 1: "Remote I/O comms lost", 2: "Conveyor 1 VFD trip",
    3: "Conveyor 2 VFD trip", 4: "Conveyor 1 zero speed", 5: "Conveyor 2 zero speed",
    6: "Mixer motor failed to run", 7: "Discharge door open timeout",
    8: "Discharge door close timeout", 9: "Gate drive fault", 10: "Weight out of tolerance",
    11: "No material flow", 12: "Weight signal fault", 13: "Silo low level (warning)",
    14: "Not enough material to start (warning)", 15: "Gate homing timeout",
}
ALARM2 = {}  # bits 0-4 low level silo 1-5, 5-9 gate fault 1-5, 10-14 weight signal 1-5
for _i in range(1, 6):
    ALARM2[_i - 1] = f"Silo {_i} low level"
    ALARM2[4 + _i] = f"Gate {_i} drive fault"
    ALARM2[9 + _i] = f"Silo {_i} weight signal fault"

STATES = {
    0: "IDLE", 5: "LOAD_RECIPE", 10: "START_CHECKS", 12: "HOME_GATES",
    20: "START_MIXER", 30: "START_C2", 40: "START_C1", 50: "SELECT_SILO",
    60: "FEED", 62: "SETTLE", 64: "CHECK_WEIGHT", 70: "RUNOUT_C1", 72: "RUNOUT_C2",
    80: "MIX", 90: "DOOR_OPEN", 92: "DISCHARGE", 94: "DOOR_CLOSE", 96: "BATCH_DONE",
    100: "HOLD",
}


def ix(addr):
    """Discrete input / coil index -> OpenPLC byte.bit text, e.g. 9 -> '101.1'."""
    return f"{100 + addr // 8}.{addr % 8}"


def st_located():
    """Every located variable as (ST name, IEC address, type)."""
    out = []
    for name, a in DI.items():
        out.append((f"DI_{name}", f"%IX{ix(a)}", "BOOL"))
    for name, a in DO.items():
        out.append((f"DO_{name}", f"%QX{ix(a)}", "BOOL"))
    for name, a in IR.items():
        out.append((f"IR_{name}", f"%IW{100 + a}", "WORD" if name in IR_WORDS else "INT"))
    for name, a in HR.items():
        out.append((f"HR_{name}", f"%QW{100 + a}", "INT"))
    for name, a in MW.items():
        out.append((f"HMI_{name}", f"%MW{a}", "WORD" if name in MW_WORDS else "INT"))
    return out
