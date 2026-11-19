"""Soft-PLC: a line-by-line Python copy of plc/batching.st.

Same sections, same tag names, same step numbers, so the tests prove the logic
and the HMIs work before OpenPLC is installed. If you change one file, change
the other; tests/test_st_consistency.py checks the steps and addresses match.
"""

from .iomap import DI, DI_COUNT, DO, DO_COUNT, HR, HR_COUNT, IR, IR_COUNT, MW, MW_COUNT
from .modbus import s16

SCAN_MS = 100


class TON:
    """IEC on-delay timer, times in ms against the controller clock."""

    def __init__(self):
        self.q = False
        self.et = 0
        self._running = False
        self._start = 0

    def __call__(self, IN, PT, now):
        if not IN:
            self._running = False
            self.et = 0
            self.q = False
        else:
            if not self._running:
                self._running = True
                self._start = now
            self.et = min(now - self._start, PT)
            self.q = self.et >= PT


def real_to_int(x):
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def limit(mn, x, mx):
    return max(mn, min(x, mx))


R = range(1, 6)


class Controller:
    def __init__(self, f6_bad_edit=False):
        self.f6_bad_edit = f6_bad_edit   # F6: run the program with the bad edit
        # process image of the remote rack and the HMI memory
        self.di = [False] * DI_COUNT
        self.co = [False] * DO_COUNT
        self.ir = [0] * IR_COUNT
        self.hr = [0] * HR_COUNT
        self.mw = [0] * MW_COUNT
        self.now = 0

        self.FirstScanDone = False
        self.Mode = 3
        self.State = 0
        self.LastState = -1
        self.ResumeState = 0
        self.Silo = 1
        self.RecipeBase = 0

        z = lambda v: [v] * 6  # noqa: E731  (index 0 unused, like ARRAY[1..5])
        self.WeightKg = z(0.0)
        self.SignalBad = z(False)
        self.GatePos = z(0)
        self.GateHomed = z(False)
        self.GateFault = z(False)
        self.GateSP = z(0)
        self.AllHomed = False
        self.RecipeKg = [0.0] * 21
        self.TargetKg = z(0.0)
        self.ActualKg = z(0.0)
        self.StartKg = z(0.0)
        self.InflightKg = z(0.0)
        self.Started = z(False)
        self.Done = z(False)
        self.TopUps = z(0)
        self.ProgressKg = 0.0
        self.Progressed = False
        self.GateCmdSP = 0

        self.StopAtEnd = False
        self.NextGiven = False
        self.WaitNext = False
        self.BatchReq = 1
        self.BatchesDone = 0
        self.MixRemain = 0
        self.Accepted = False

        for a in ("A_EStop", "A_Comms", "A_C1Trip", "A_C2Trip", "A_C1Zero", "A_C2Zero",
                  "A_MixFail", "A_DoorOpenTO", "A_DoorCloseTO", "A_GateFault", "A_Tol",
                  "A_NoFlow", "A_Signal", "A_HomeTO", "W_Low", "W_NotEnough"):
            setattr(self, a, False)
        self.LowSilo = z(False)
        self.GateFaultSilo = z(False)
        self.SignalSilo = z(False)
        self.AnyTrip = False
        self.TolPending = False
        self.ResetReq = False
        self.ResetPulse = False
        self.SounderOn = False
        self.Alarm1 = self.Alarm2 = self.PrevAlarm1 = self.PrevAlarm2 = 0

        self.C1Cmd = self.C2Cmd = self.MixCmd = self.DoorCmd = False
        self.HoldC1 = self.HoldC2 = False
        self.LastHB = 0
        self.SecPulse = False
        self.Flash = False
        self.NextSec = 1000
        for t in ("StepTmr", "ClockTmr", "CommsTmr", "C1ZeroTmr", "C2ZeroTmr", "MixFbTmr",
                  "NoFlowTmr", "ResetTmr", "DoorOpenTmr", "DoorCloseTmr"):
            setattr(self, t, TON())

    # ---- HMI helpers (what FUXA does) -----------------------------------
    def hmi(self, tag):
        return self.mw[MW[tag]]

    def set_hmi(self, tag, value):
        self.mw[MW[tag]] = s16(value)

    # ---- one PLC scan -----------------------------------------------------
    def scan(self):
        self.now += SCAN_MS
        now = self.now
        di, ir, mw = self.di, self.ir, self.mw
        M = lambda tag: mw[MW[tag]]  # noqa: E731

        # 1. First scan: default recipes
        if not self.FirstScanDone:
            if M("MixTime_s") == 0 and M("R1_A") == 0:
                defaults = {"A": (800, 600, 1000, 500), "B": (500, 600, 0, 500),
                            "C": (400, 400, 500, 500), "D": (200, 300, 300, 500),
                            "E": (100, 100, 200, 0)}
                for letter, vals in defaults.items():
                    for r, v in enumerate(vals, start=1):
                        mw[MW[f"R{r}_{letter}"]] = v
                mw[MW["MixTime_s"]] = 60
                mw[MW["RecipeSel"]] = 1
                mw[MW["BatchReq"]] = 1
            for i in R:
                self.InflightKg[i] = 5.0
            self.FirstScanDone = True

        # 2. Inputs into internal tags
        self.AllHomed = True
        for i in R:
            raw = s16(ir[IR[f"Weight{i}"]])
            self.SignalBad[i] = raw < 5760 or raw > 32640
            self.WeightKg[i] = (raw - 6400) * 20000.0 / 25600.0
            self.GatePos[i] = s16(ir[IR[f"GatePos{i}"]])
            stat = ir[IR[f"GateStatus{i}"]] & 0xFFFF
            self.GateHomed[i] = stat & 0x0002 != 0
            self.GateFault[i] = stat & 0x0008 != 0
            if not self.GateHomed[i]:
                self.AllHomed = False
        if not 1 <= M("RecipeSel") <= 4:
            mw[MW["RecipeSel"]] = 1
        for r in range(1, 5):
            for m, letter in enumerate("ABCDE", start=1):
                self.RecipeKg[(r - 1) * 5 + m] = float(M(f"R{r}_{letter}"))

        # 3. HMI commands
        cmd = M("Cmd")
        CmdStart, CmdStop, CmdHold, CmdResume = cmd == 1, cmd == 2, cmd == 3, cmd == 4
        CmdReset, CmdNext, CmdAbort = cmd == 5, cmd == 6, cmd == 7
        mw[MW["Cmd"]] = 0
        if M("ModeReq") != 0:
            if self.State == 0 and 1 <= M("ModeReq") <= 3:
                self.Mode = M("ModeReq")
            mw[MW["ModeReq"]] = 0
        if CmdStop:
            self.StopAtEnd = True

        # 4. One-second pulse and lamp flasher
        self.ClockTmr(not self.ClockTmr.q, 3_600_000, now)
        self.SecPulse = False
        if self.ClockTmr.et >= self.NextSec:
            self.SecPulse = True
            self.Flash = not self.Flash
            self.NextSec += 1000
        if self.ClockTmr.q:
            self.NextSec = 1000

        # 5. Comms watchdog
        hb = s16(ir[IR["Heartbeat"]])
        HBSame = hb == self.LastHB
        self.LastHB = hb
        self.CommsTmr(HBSame, 2000, now)

        # 6. Alarm detection
        if not di[DI["EStopOK"]]:
            self.A_EStop = True
        if self.CommsTmr.q:
            self.A_Comms = True
        if di[DI["C1_Fault"]]:
            self.A_C1Trip = True
        if di[DI["C2_Fault"]]:
            self.A_C2Trip = True
        self.C1ZeroTmr(self.C1Cmd and not di[DI["C1_SpeedOK"]], 5000, now)
        if self.C1ZeroTmr.q:
            self.A_C1Zero = True
        self.C2ZeroTmr(self.C2Cmd and not di[DI["C2_SpeedOK"]], 5000, now)
        if self.C2ZeroTmr.q:
            self.A_C2Zero = True
        self.MixFbTmr(self.MixCmd and not di[DI["Mix_Run"]], 3000, now)
        if self.MixFbTmr.q:
            self.A_MixFail = True
        self.W_Low = False
        for i in R:
            if self.SignalBad[i]:
                self.SignalSilo[i] = True
                self.A_Signal = True
            if self.GateFault[i]:
                self.GateFaultSilo[i] = True
                self.A_GateFault = True
            self.LowSilo[i] = (not self.SignalBad[i]) and self.WeightKg[i] < 2000.0
            if self.LowSilo[i]:
                self.W_Low = True

        # 7. Reset + acknowledge
        if CmdReset:
            self.ResetReq = True
            self.SounderOn = False
        self.ResetTmr(self.ResetReq, 1000, now)
        self.ResetPulse = self.ResetReq and not self.ResetTmr.q
        if self.ResetTmr.q:
            self.ResetReq = False
            for a in ("A_EStop", "A_Comms", "A_C1Trip", "A_C2Trip", "A_C1Zero", "A_C2Zero",
                      "A_MixFail", "A_DoorOpenTO", "A_DoorCloseTO", "A_GateFault", "A_Tol",
                      "A_NoFlow", "A_Signal", "A_HomeTO", "W_NotEnough"):
                setattr(self, a, False)
            for i in R:
                self.GateFaultSilo[i] = False
                self.SignalSilo[i] = False

        self.AnyTrip = any((self.A_EStop, self.A_Comms, self.A_C1Trip, self.A_C2Trip,
                            self.A_C1Zero, self.A_C2Zero, self.A_MixFail, self.A_DoorOpenTO,
                            self.A_DoorCloseTO, self.A_GateFault, self.A_Tol, self.A_NoFlow,
                            self.A_Signal, self.A_HomeTO))

        # 8. Sequence
        if self.Mode == 1:
            self.State = 0
        elif self.A_EStop or CmdAbort:
            self.State = 0
        elif 5 <= self.State < 100 and (self.AnyTrip or CmdHold):
            self.ResumeState = self.State
            self.HoldC1 = self.C1Cmd
            self.HoldC2 = self.C2Cmd
            self.State = 100

        if self.State != self.LastState:
            self.StepTmr(False, 3_600_000, now)
            self.LastState = self.State
            self.NextGiven = False
        self.StepTmr(True, 3_600_000, now)
        if CmdNext:
            self.NextGiven = True
        self.Progressed = False
        self.WaitNext = False
        et = self.StepTmr.et
        s = self.State
        auto_or_next = self.Mode == 3 or self.NextGiven

        if s == 0:
            self.GateCmdSP = 0
            if self.Mode in (2, 3) and CmdStart and not self.AnyTrip:
                self.BatchReq = max(1, M("BatchReq"))
                self.BatchesDone = 0
                self.StopAtEnd = False
                self.ResumeState = 0
                self.Accepted = False
                self.State = 5
        elif s == 5:
            self.RecipeBase = (M("RecipeSel") - 1) * 5
            b = self.RecipeBase
            self.TargetKg[1] = self.RecipeKg[b + 1]
            self.TargetKg[2] = self.RecipeKg[b + 1] if self.f6_bad_edit else self.RecipeKg[b + 2]
            self.TargetKg[3] = self.RecipeKg[b + 3]
            self.TargetKg[4] = self.RecipeKg[b + 4]
            self.TargetKg[5] = self.RecipeKg[b + 5]
            SumKg = 0.0
            self.W_NotEnough = False
            for i in R:
                self.Started[i] = self.Done[i] = False
                self.TopUps[i] = 0
                self.ActualKg[i] = self.StartKg[i] = 0.0
                SumKg += self.TargetKg[i]
                if self.TargetKg[i] > 0.0 and self.WeightKg[i] < self.TargetKg[i] + 500.0:
                    self.W_NotEnough = True
            self.Silo = 1
            self.TolPending = False
            self.State = 0 if (SumKg <= 0.0 or SumKg > 2500.0 or self.W_NotEnough) else 10
        elif s == 10:
            if di[DI["Door_Closed"]] and not self.AnyTrip:
                self.State = 20 if self.AllHomed else 12
        elif s == 12:
            if self.AllHomed:
                self.State = 20
            elif et >= 15000:
                self.A_HomeTO = True
        elif s == 20:
            if di[DI["Mix_Run"]]:
                if 80 <= self.ResumeState < 100:
                    self.State = self.ResumeState
                    self.ResumeState = 0
                else:
                    self.State = 30
        elif s == 30:
            if di[DI["C2_SpeedOK"]]:
                self.State = 40
        elif s == 40:
            if di[DI["C1_SpeedOK"]]:
                self.State = 70 if 70 <= self.ResumeState < 80 else 50
                self.ResumeState = 0
        elif s == 50:
            self.GateCmdSP = 0
            NextSilo = 0
            for i in range(5, 0, -1):
                if not self.Done[i] and self.TargetKg[i] > 0.0:
                    NextSilo = i
            if NextSilo == 0:
                self.State = 70
            elif auto_or_next:
                self.Silo = NextSilo
                k = self.Silo
                if not self.Started[k]:
                    self.StartKg[k] = self.WeightKg[k]
                    self.Started[k] = True
                self.ProgressKg = self.StartKg[k] - self.WeightKg[k]
                self.State = 60
            else:
                self.WaitNext = True
        elif s == 60:
            k = self.Silo
            Dispensed = self.StartKg[k] - self.WeightKg[k]
            self.ActualKg[k] = Dispensed
            Remaining = self.TargetKg[k] - Dispensed
            DribbleKg = max(30.0, 0.1 * self.TargetKg[k])
            CutoffKg = 0.5 * self.InflightKg[k] if self.TopUps[k] > 0 else self.InflightKg[k]
            if Remaining <= CutoffKg:
                self.GateCmdSP = 0
                self.State = 62
            elif Remaining > DribbleKg and self.TopUps[k] == 0:
                self.GateCmdSP = 1000
            else:
                self.GateCmdSP = 250
            if Dispensed - self.ProgressKg >= 2.0:
                self.ProgressKg = Dispensed
                self.Progressed = True
        elif s == 62:
            self.GateCmdSP = 0
            if et >= 2000:
                self.State = 64
        elif s == 64:
            k = self.Silo
            Dispensed = self.StartKg[k] - self.WeightKg[k]
            self.ActualKg[k] = Dispensed
            ErrKg = Dispensed - self.TargetKg[k]
            TolKg = max(5.0, 0.01 * self.TargetKg[k])
            if abs(ErrKg) <= TolKg:
                if self.TopUps[k] == 0:
                    self.InflightKg[k] = limit(0.0, self.InflightKg[k] + 0.5 * ErrKg, 50.0)
                self.Done[k] = True
                self.State = 50
            elif ErrKg < 0.0 and self.TopUps[k] < 2:
                self.TopUps[k] += 1
                self.State = 60
            else:
                self.A_Tol = True
                self.TolPending = True
        elif s == 70:
            self.GateCmdSP = 0
            if et >= 25000:
                self.State = 72
        elif s == 72:
            if et >= 35000:
                self.MixRemain = M("MixTime_s")
                self.State = 80
        elif s == 80:
            if self.SecPulse and self.MixRemain > 0:
                self.MixRemain -= 1
            if self.MixRemain <= 0:
                self.State = 90
        elif s == 90:
            if self.Mode == 2 and not self.NextGiven:
                self.WaitNext = True
            if auto_or_next and di[DI["Door_Open"]]:
                self.State = 92
        elif s == 92:
            if et >= 20000:
                self.State = 94
        elif s == 94:
            if di[DI["Door_Closed"]]:
                self.State = 96
        elif s == 96:
            self.BatchesDone += 1
            self.State = 0 if (self.BatchesDone >= self.BatchReq or self.StopAtEnd) else 5
        elif s == 100:
            self.GateCmdSP = 0
            if CmdResume and not self.AnyTrip:
                if self.TolPending:
                    self.Done[self.Silo] = True
                    self.TolPending = False
                    self.Accepted = True
                self.State = 10

        self.DoorOpenTmr(self.State == 90 and (self.Mode == 3 or self.NextGiven)
                         and not di[DI["Door_Open"]], 10000, now)
        if self.DoorOpenTmr.q:
            self.A_DoorOpenTO = True
        self.DoorCloseTmr(self.State == 94 and not di[DI["Door_Closed"]], 10000, now)
        if self.DoorCloseTmr.q:
            self.A_DoorCloseTO = True
        self.NoFlowTmr(self.State == 60 and self.GatePos[self.Silo] >= 200 and not self.Progressed,
                       8000, now)
        if self.NoFlowTmr.q:
            self.A_NoFlow = True

        # 9. Outputs from the state
        s = self.State
        et = self.StepTmr.et
        SeqC2 = (30 <= s <= 72) or (s == 100 and self.HoldC2 and et < 60000)
        SeqC1 = (40 <= s <= 70) or (s == 100 and self.HoldC1 and et < 25000)
        SeqMix = (20 <= s <= 96) or s == 100
        SeqDoor = (s == 90 and (self.Mode == 3 or self.NextGiven)) or s == 92
        SeqHome = s == 12
        for i in R:
            self.GateSP[i] = 0
        if s == 60:
            self.GateSP[self.Silo] = self.GateCmdSP
        if self.Mode == 1:
            bits = M("ManualBits") & 0xFFFF
            SeqC2 = bits & 0x0001 != 0
            SeqC1 = bits & 0x0002 != 0
            SeqMix = bits & 0x0004 != 0
            SeqDoor = bits & 0x0008 != 0
            SeqHome = bits & 0x0010 != 0
            for i in R:
                self.GateSP[i] = limit(0, M(f"ManGateSP{i}"), 1000)
        else:
            mw[MW["ManualBits"]] = 0
            for i in R:
                mw[MW[f"ManGateSP{i}"]] = 0

        # 10. Interlocks
        self.C2Cmd = SeqC2 and not self.A_C2Trip and not self.A_C2Zero
        self.C1Cmd = (SeqC1 and self.C2Cmd and di[DI["C2_SpeedOK"]]
                      and not self.A_C1Trip and not self.A_C1Zero)
        self.MixCmd = SeqMix and not self.A_MixFail
        self.DoorCmd = SeqDoor
        if not (self.C1Cmd and di[DI["C1_SpeedOK"]]):
            for i in R:
                self.GateSP[i] = 0
        if self.A_EStop or not di[DI["EStopOK"]]:
            self.C1Cmd = self.C2Cmd = self.MixCmd = self.DoorCmd = SeqHome = False
            for i in R:
                self.GateSP[i] = 0

        # 11. Alarm words, lamp, sounder
        a1 = 0
        for bit, flag in enumerate((self.A_EStop, self.A_Comms, self.A_C1Trip, self.A_C2Trip,
                                    self.A_C1Zero, self.A_C2Zero, self.A_MixFail,
                                    self.A_DoorOpenTO, self.A_DoorCloseTO, self.A_GateFault,
                                    self.A_Tol, self.A_NoFlow, self.A_Signal, self.W_Low,
                                    self.W_NotEnough, self.A_HomeTO)):
            if flag:
                a1 |= 1 << bit
        a2 = 0
        for i in R:
            if self.LowSilo[i]:
                a2 |= 1 << (i - 1)
            if self.GateFaultSilo[i]:
                a2 |= 1 << (i + 4)
            if self.SignalSilo[i]:
                a2 |= 1 << (i + 9)
        if (a1 & ~self.PrevAlarm1) or (a2 & ~self.PrevAlarm2):
            self.SounderOn = True
        self.PrevAlarm1, self.PrevAlarm2 = a1, a2
        self.Alarm1, self.Alarm2 = a1, a2

        # 12. Write the remote rack
        co = self.co
        co[DO["C1_RunCmd"]] = self.C1Cmd
        co[DO["C2_RunCmd"]] = self.C2Cmd
        co[DO["Mix_RunCmd"]] = self.MixCmd
        co[DO["Door_OpenSol"]] = self.DoorCmd
        co[DO["C1_Reset"]] = co[DO["C2_Reset"]] = co[DO["Gates_Reset"]] = self.ResetPulse
        co[DO["Gates_Enable"]] = di[DI["EStopOK"]]
        co[DO["Gates_Home"]] = SeqHome
        co[DO["AlarmLamp"]] = (self.AnyTrip and self.Flash) or (self.W_Low and not self.AnyTrip)
        co[DO["Sounder"]] = self.SounderOn
        for i in R:
            self.hr[HR[f"GateSP{i}"]] = self.GateSP[i]
        self.hr[HR["C1_SpeedRef"]] = 500
        self.hr[HR["C2_SpeedRef"]] = 500

        # 13. Write the HMI map
        status = 0
        if 0 < s < 100:
            status |= 0x0001
        if s == 100:
            status |= 0x0002
        if self.WaitNext:
            status |= 0x0004
        if self.Accepted:
            status |= 0x0008
        if self.W_NotEnough:
            status |= 0x0010
        mw[MW["Status"]] = s16(status)
        mw[MW["Alarm1"]] = s16(a1)
        mw[MW["Alarm2"]] = s16(a2)
        mw[MW["Mode"]] = self.Mode
        mw[MW["State"]] = s
        mw[MW["ActiveSilo"]] = self.Silo if 50 <= s <= 64 else 0
        mw[MW["BatchesDone"]] = self.BatchesDone
        mw[MW["MixRemain_s"]] = self.MixRemain
        for i in R:
            mw[MW[f"Weight{i}"]] = real_to_int(self.WeightKg[i])
            mw[MW[f"Target{i}"]] = real_to_int(self.TargetKg[i])
            mw[MW[f"Actual{i}"]] = real_to_int(self.ActualKg[i])
            mw[MW[f"Inflight{i}"]] = real_to_int(self.InflightKg[i] * 10.0)
            mw[MW[f"GatePos{i}"]] = self.GatePos[i]
            mw[MW[f"GateAlarm{i}"]] = s16(ir[IR[f"GateAlarm{i}"]])
        for tag in ("C1_Freq", "C1_Current", "C1_FaultCode", "C2_Freq", "C2_Current", "C2_FaultCode"):
            mw[MW[tag]] = s16(ir[IR[tag]])
