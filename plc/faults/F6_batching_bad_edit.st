(* Salbotics PLC troubleshooting lab: weigh-batching cell.
   A demonstration rebuilt with open tools. Not any company's program.
   Materials A-E and all numbers are invented. Addresses: lab/iomap.py.
   Target: OpenPLC Runtime v3, 100 ms task. Licence: MIT. *)

PROGRAM Batching  (* F6 lab fault: contains one bad edit. Do not use in production. *)
VAR
  DI_EStopOK AT %IX100.0 : BOOL;
  DI_C1_Run AT %IX100.1 : BOOL;
  DI_C1_Fault AT %IX100.2 : BOOL;
  DI_C1_SpeedOK AT %IX100.3 : BOOL;
  DI_C2_Run AT %IX100.4 : BOOL;
  DI_C2_Fault AT %IX100.5 : BOOL;
  DI_C2_SpeedOK AT %IX100.6 : BOOL;
  DI_Mix_Run AT %IX100.7 : BOOL;
  DI_Door_Open AT %IX101.0 : BOOL;
  DI_Door_Closed AT %IX101.1 : BOOL;
  DO_C1_RunCmd AT %QX100.0 : BOOL;
  DO_C1_Reset AT %QX100.1 : BOOL;
  DO_C2_RunCmd AT %QX100.2 : BOOL;
  DO_C2_Reset AT %QX100.3 : BOOL;
  DO_Mix_RunCmd AT %QX100.4 : BOOL;
  DO_Door_OpenSol AT %QX100.5 : BOOL;
  DO_AlarmLamp AT %QX100.6 : BOOL;
  DO_Sounder AT %QX100.7 : BOOL;
  DO_Gates_Enable AT %QX101.0 : BOOL;
  DO_Gates_Reset AT %QX101.1 : BOOL;
  DO_Gates_Home AT %QX101.2 : BOOL;
  IR_Heartbeat AT %IW100 : INT;
  IR_Weight1 AT %IW101 : INT;
  IR_Weight2 AT %IW102 : INT;
  IR_Weight3 AT %IW103 : INT;
  IR_Weight4 AT %IW104 : INT;
  IR_Weight5 AT %IW105 : INT;
  IR_GatePos1 AT %IW106 : INT;
  IR_GatePos2 AT %IW107 : INT;
  IR_GatePos3 AT %IW108 : INT;
  IR_GatePos4 AT %IW109 : INT;
  IR_GatePos5 AT %IW110 : INT;
  IR_GateStatus1 AT %IW111 : WORD;
  IR_GateStatus2 AT %IW112 : WORD;
  IR_GateStatus3 AT %IW113 : WORD;
  IR_GateStatus4 AT %IW114 : WORD;
  IR_GateStatus5 AT %IW115 : WORD;
  IR_GateAlarm1 AT %IW116 : INT;
  IR_GateAlarm2 AT %IW117 : INT;
  IR_GateAlarm3 AT %IW118 : INT;
  IR_GateAlarm4 AT %IW119 : INT;
  IR_GateAlarm5 AT %IW120 : INT;
  IR_C1_Freq AT %IW121 : INT;
  IR_C1_Current AT %IW122 : INT;
  IR_C1_FaultCode AT %IW123 : INT;
  IR_C2_Freq AT %IW124 : INT;
  IR_C2_Current AT %IW125 : INT;
  IR_C2_FaultCode AT %IW126 : INT;
  HR_GateSP1 AT %QW100 : INT;
  HR_GateSP2 AT %QW101 : INT;
  HR_GateSP3 AT %QW102 : INT;
  HR_GateSP4 AT %QW103 : INT;
  HR_GateSP5 AT %QW104 : INT;
  HR_C1_SpeedRef AT %QW105 : INT;
  HR_C2_SpeedRef AT %QW106 : INT;
  HMI_ModeReq AT %MW0 : INT;
  HMI_Cmd AT %MW1 : INT;
  HMI_RecipeSel AT %MW2 : INT;
  HMI_BatchReq AT %MW3 : INT;
  HMI_ManualBits AT %MW4 : WORD;
  HMI_ManGateSP1 AT %MW5 : INT;
  HMI_ManGateSP2 AT %MW6 : INT;
  HMI_ManGateSP3 AT %MW7 : INT;
  HMI_ManGateSP4 AT %MW8 : INT;
  HMI_ManGateSP5 AT %MW9 : INT;
  HMI_Mode AT %MW10 : INT;
  HMI_State AT %MW11 : INT;
  HMI_ActiveSilo AT %MW12 : INT;
  HMI_BatchesDone AT %MW13 : INT;
  HMI_MixRemain_s AT %MW14 : INT;
  HMI_Alarm1 AT %MW15 : WORD;
  HMI_Alarm2 AT %MW16 : WORD;
  HMI_Status AT %MW17 : WORD;
  HMI_Weight1 AT %MW20 : INT;
  HMI_Target1 AT %MW25 : INT;
  HMI_Actual1 AT %MW30 : INT;
  HMI_Inflight1 AT %MW35 : INT;
  HMI_GatePos1 AT %MW40 : INT;
  HMI_Weight2 AT %MW21 : INT;
  HMI_Target2 AT %MW26 : INT;
  HMI_Actual2 AT %MW31 : INT;
  HMI_Inflight2 AT %MW36 : INT;
  HMI_GatePos2 AT %MW41 : INT;
  HMI_Weight3 AT %MW22 : INT;
  HMI_Target3 AT %MW27 : INT;
  HMI_Actual3 AT %MW32 : INT;
  HMI_Inflight3 AT %MW37 : INT;
  HMI_GatePos3 AT %MW42 : INT;
  HMI_Weight4 AT %MW23 : INT;
  HMI_Target4 AT %MW28 : INT;
  HMI_Actual4 AT %MW33 : INT;
  HMI_Inflight4 AT %MW38 : INT;
  HMI_GatePos4 AT %MW43 : INT;
  HMI_Weight5 AT %MW24 : INT;
  HMI_Target5 AT %MW29 : INT;
  HMI_Actual5 AT %MW34 : INT;
  HMI_Inflight5 AT %MW39 : INT;
  HMI_GatePos5 AT %MW44 : INT;
  HMI_C1_Freq AT %MW45 : INT;
  HMI_C1_Current AT %MW46 : INT;
  HMI_C2_Freq AT %MW47 : INT;
  HMI_C2_Current AT %MW48 : INT;
  HMI_C1_FaultCode AT %MW49 : INT;
  HMI_C2_FaultCode AT %MW50 : INT;
  HMI_GateAlarm1 AT %MW51 : INT;
  HMI_GateAlarm2 AT %MW52 : INT;
  HMI_GateAlarm3 AT %MW53 : INT;
  HMI_GateAlarm4 AT %MW54 : INT;
  HMI_GateAlarm5 AT %MW55 : INT;
  HMI_R1_A AT %MW60 : INT;
  HMI_R1_B AT %MW61 : INT;
  HMI_R1_C AT %MW62 : INT;
  HMI_R1_D AT %MW63 : INT;
  HMI_R1_E AT %MW64 : INT;
  HMI_R2_A AT %MW65 : INT;
  HMI_R2_B AT %MW66 : INT;
  HMI_R2_C AT %MW67 : INT;
  HMI_R2_D AT %MW68 : INT;
  HMI_R2_E AT %MW69 : INT;
  HMI_R3_A AT %MW70 : INT;
  HMI_R3_B AT %MW71 : INT;
  HMI_R3_C AT %MW72 : INT;
  HMI_R3_D AT %MW73 : INT;
  HMI_R3_E AT %MW74 : INT;
  HMI_R4_A AT %MW75 : INT;
  HMI_R4_B AT %MW76 : INT;
  HMI_R4_C AT %MW77 : INT;
  HMI_R4_D AT %MW78 : INT;
  HMI_R4_E AT %MW79 : INT;
  HMI_MixTime_s AT %MW80 : INT;
END_VAR
VAR
  FirstScanDone : BOOL := FALSE;
  Mode : INT := 3;            (* 1 Manual, 2 Semi-auto, 3 Auto *)
  State : INT := 0;
  LastState : INT := -1;
  ResumeState : INT := 0;
  i : INT;
  Silo : INT := 1;
  NextSilo : INT := 0;
  RecipeBase : INT := 0;

  RawW : ARRAY[1..5] OF INT;
  WeightKg : ARRAY[1..5] OF REAL;
  SignalBad : ARRAY[1..5] OF BOOL;
  GatePos : ARRAY[1..5] OF INT;
  GateStat : ARRAY[1..5] OF WORD;
  GateReady : ARRAY[1..5] OF BOOL;
  GateHomed : ARRAY[1..5] OF BOOL;
  GateFault : ARRAY[1..5] OF BOOL;
  GateSP : ARRAY[1..5] OF INT;
  AllHomed : BOOL;

  RecipeKg : ARRAY[1..20] OF REAL;
  TargetKg : ARRAY[1..5] OF REAL;
  ActualKg : ARRAY[1..5] OF REAL;
  StartKg : ARRAY[1..5] OF REAL;
  InflightKg : ARRAY[1..5] OF REAL;
  Started : ARRAY[1..5] OF BOOL;
  Done : ARRAY[1..5] OF BOOL;
  TopUps : ARRAY[1..5] OF INT;
  Dispensed : REAL;
  Remaining : REAL;
  DribbleKg : REAL;
  CutoffKg : REAL;
  ErrKg : REAL;
  TolKg : REAL;
  SumKg : REAL;
  ProgressKg : REAL;
  Progressed : BOOL;
  GateCmdSP : INT := 0;

  CmdStart, CmdStop, CmdHold, CmdResume, CmdReset, CmdNext, CmdAbort : BOOL;
  StopAtEnd : BOOL;
  NextGiven : BOOL;
  WaitNext : BOOL;
  BatchReq : INT := 1;
  BatchesDone : INT := 0;
  MixRemain : INT := 0;
  Accepted : BOOL;

  A_EStop, A_Comms, A_C1Trip, A_C2Trip, A_C1Zero, A_C2Zero, A_MixFail : BOOL;
  A_DoorOpenTO, A_DoorCloseTO, A_GateFault, A_Tol, A_NoFlow, A_Signal, A_HomeTO : BOOL;
  W_Low, W_NotEnough : BOOL;
  LowSilo : ARRAY[1..5] OF BOOL;
  GateFaultSilo : ARRAY[1..5] OF BOOL;
  SignalSilo : ARRAY[1..5] OF BOOL;
  AnyTrip : BOOL;
  TolPending : BOOL;
  ResetReq : BOOL;
  ResetPulse : BOOL;
  SounderOn : BOOL;
  Alarm1, Alarm2, PrevAlarm1, PrevAlarm2, Status, ManBits : WORD;

  SeqC1, SeqC2, SeqMix, SeqDoor, SeqHome : BOOL;
  C1Cmd, C2Cmd, MixCmd, DoorCmd : BOOL;
  HoldC1, HoldC2 : BOOL;

  LastHB : INT := 0;
  HBSame : BOOL;
  SecPulse, Flash : BOOL;
  NextSec : TIME := T#1s;

  (* One FB instance per line: OpenPLC v3's compiler (matiec) crashes on 'A, B : TON;'. *)
  StepTmr : TON;
  ClockTmr : TON;
  CommsTmr : TON;
  C1ZeroTmr : TON;
  C2ZeroTmr : TON;
  MixFbTmr : TON;
  NoFlowTmr : TON;
  ResetTmr : TON;
  DoorOpenTmr : TON;
  DoorCloseTmr : TON;
END_VAR

(* ===== 1. First scan: default recipes ===== *)
IF NOT FirstScanDone THEN
  IF HMI_MixTime_s = 0 AND HMI_R1_A = 0 THEN
    HMI_R1_A := 800;  HMI_R1_B := 500; HMI_R1_C := 400; HMI_R1_D := 200; HMI_R1_E := 100;
    HMI_R2_A := 600;  HMI_R2_B := 600; HMI_R2_C := 400; HMI_R2_D := 300; HMI_R2_E := 100;
    HMI_R3_A := 1000; HMI_R3_B := 0;   HMI_R3_C := 500; HMI_R3_D := 300; HMI_R3_E := 200;
    HMI_R4_A := 500;  HMI_R4_B := 500; HMI_R4_C := 500; HMI_R4_D := 500; HMI_R4_E := 0;
    HMI_MixTime_s := 60;
    HMI_RecipeSel := 1;
    HMI_BatchReq := 1;
  END_IF;
  FOR i := 1 TO 5 DO
    InflightKg[i] := 5.0;
  END_FOR;
  FirstScanDone := TRUE;
END_IF;

(* ===== 2. Inputs into internal tags ===== *)
RawW[1] := IR_Weight1; RawW[2] := IR_Weight2; RawW[3] := IR_Weight3;
RawW[4] := IR_Weight4; RawW[5] := IR_Weight5;
GatePos[1] := IR_GatePos1; GatePos[2] := IR_GatePos2; GatePos[3] := IR_GatePos3;
GatePos[4] := IR_GatePos4; GatePos[5] := IR_GatePos5;
GateStat[1] := IR_GateStatus1; GateStat[2] := IR_GateStatus2; GateStat[3] := IR_GateStatus3;
GateStat[4] := IR_GateStatus4; GateStat[5] := IR_GateStatus5;
AllHomed := TRUE;
FOR i := 1 TO 5 DO
  (* 4-20 mA = 6400-32000 raw = 0-20000 kg. Below 3.6 mA = broken loop. *)
  SignalBad[i] := (RawW[i] < 5760) OR (RawW[i] > 32640);
  WeightKg[i] := INT_TO_REAL(RawW[i] - 6400) * 20000.0 / 25600.0;
  GateReady[i] := (GateStat[i] AND 16#0001) <> 16#0000;
  GateHomed[i] := (GateStat[i] AND 16#0002) <> 16#0000;
  GateFault[i] := (GateStat[i] AND 16#0008) <> 16#0000;
  IF NOT GateHomed[i] THEN AllHomed := FALSE; END_IF;
END_FOR;

IF HMI_RecipeSel < 1 OR HMI_RecipeSel > 4 THEN HMI_RecipeSel := 1; END_IF;
RecipeKg[1] := INT_TO_REAL(HMI_R1_A);  RecipeKg[2] := INT_TO_REAL(HMI_R1_B);
RecipeKg[3] := INT_TO_REAL(HMI_R1_C);  RecipeKg[4] := INT_TO_REAL(HMI_R1_D);
RecipeKg[5] := INT_TO_REAL(HMI_R1_E);  RecipeKg[6] := INT_TO_REAL(HMI_R2_A);
RecipeKg[7] := INT_TO_REAL(HMI_R2_B);  RecipeKg[8] := INT_TO_REAL(HMI_R2_C);
RecipeKg[9] := INT_TO_REAL(HMI_R2_D);  RecipeKg[10] := INT_TO_REAL(HMI_R2_E);
RecipeKg[11] := INT_TO_REAL(HMI_R3_A); RecipeKg[12] := INT_TO_REAL(HMI_R3_B);
RecipeKg[13] := INT_TO_REAL(HMI_R3_C); RecipeKg[14] := INT_TO_REAL(HMI_R3_D);
RecipeKg[15] := INT_TO_REAL(HMI_R3_E); RecipeKg[16] := INT_TO_REAL(HMI_R4_A);
RecipeKg[17] := INT_TO_REAL(HMI_R4_B); RecipeKg[18] := INT_TO_REAL(HMI_R4_C);
RecipeKg[19] := INT_TO_REAL(HMI_R4_D); RecipeKg[20] := INT_TO_REAL(HMI_R4_E);

(* ===== 3. HMI commands (one-shot: the PLC clears them) ===== *)
CmdStart := HMI_Cmd = 1;
CmdStop := HMI_Cmd = 2;
CmdHold := HMI_Cmd = 3;
CmdResume := HMI_Cmd = 4;
CmdReset := HMI_Cmd = 5;
CmdNext := HMI_Cmd = 6;
CmdAbort := HMI_Cmd = 7;
HMI_Cmd := 0;
IF HMI_ModeReq <> 0 THEN
  IF State = 0 AND HMI_ModeReq >= 1 AND HMI_ModeReq <= 3 THEN
    Mode := HMI_ModeReq;
  END_IF;
  HMI_ModeReq := 0;
END_IF;
IF CmdStop THEN StopAtEnd := TRUE; END_IF;

(* ===== 4. One-second pulse and lamp flasher ===== *)
ClockTmr(IN := NOT ClockTmr.Q, PT := T#1h);
SecPulse := FALSE;
IF ClockTmr.ET >= NextSec THEN
  SecPulse := TRUE;
  Flash := NOT Flash;
  NextSec := NextSec + T#1s;
END_IF;
IF ClockTmr.Q THEN NextSec := T#1s; END_IF;

(* ===== 5. Remote I/O comms watchdog: heartbeat must keep changing ===== *)
HBSame := IR_Heartbeat = LastHB;
LastHB := IR_Heartbeat;
CommsTmr(IN := HBSame, PT := T#2s);

(* ===== 6. Alarm detection (trips latch until Reset) ===== *)
IF NOT DI_EStopOK THEN A_EStop := TRUE; END_IF;
IF CommsTmr.Q THEN A_Comms := TRUE; END_IF;
IF DI_C1_Fault THEN A_C1Trip := TRUE; END_IF;
IF DI_C2_Fault THEN A_C2Trip := TRUE; END_IF;
C1ZeroTmr(IN := C1Cmd AND NOT DI_C1_SpeedOK, PT := T#5s);
IF C1ZeroTmr.Q THEN A_C1Zero := TRUE; END_IF;
C2ZeroTmr(IN := C2Cmd AND NOT DI_C2_SpeedOK, PT := T#5s);
IF C2ZeroTmr.Q THEN A_C2Zero := TRUE; END_IF;
MixFbTmr(IN := MixCmd AND NOT DI_Mix_Run, PT := T#3s);
IF MixFbTmr.Q THEN A_MixFail := TRUE; END_IF;
W_Low := FALSE;
FOR i := 1 TO 5 DO
  IF SignalBad[i] THEN SignalSilo[i] := TRUE; A_Signal := TRUE; END_IF;
  IF GateFault[i] THEN GateFaultSilo[i] := TRUE; A_GateFault := TRUE; END_IF;
  LowSilo[i] := (NOT SignalBad[i]) AND (WeightKg[i] < 2000.0);
  IF LowSilo[i] THEN W_Low := TRUE; END_IF;
END_FOR;

(* ===== 7. Reset + acknowledge: 1 s reset pulse, then clear the latches ===== *)
IF CmdReset THEN
  ResetReq := TRUE;
  SounderOn := FALSE;
END_IF;
ResetTmr(IN := ResetReq, PT := T#1s);
ResetPulse := ResetReq AND NOT ResetTmr.Q;
IF ResetTmr.Q THEN
  ResetReq := FALSE;
  A_EStop := FALSE; A_Comms := FALSE; A_C1Trip := FALSE; A_C2Trip := FALSE;
  A_C1Zero := FALSE; A_C2Zero := FALSE; A_MixFail := FALSE;
  A_DoorOpenTO := FALSE; A_DoorCloseTO := FALSE; A_GateFault := FALSE;
  A_Tol := FALSE; A_NoFlow := FALSE; A_Signal := FALSE; A_HomeTO := FALSE;
  W_NotEnough := FALSE;
  FOR i := 1 TO 5 DO
    GateFaultSilo[i] := FALSE;
    SignalSilo[i] := FALSE;
  END_FOR;
END_IF;

AnyTrip := A_EStop OR A_Comms OR A_C1Trip OR A_C2Trip OR A_C1Zero OR A_C2Zero
           OR A_MixFail OR A_DoorOpenTO OR A_DoorCloseTO OR A_GateFault
           OR A_Tol OR A_NoFlow OR A_Signal OR A_HomeTO;

(* ===== 8. Sequence ===== *)
IF Mode = 1 THEN
  State := 0;                                   (* Manual: no sequence *)
ELSIF A_EStop OR CmdAbort THEN
  State := 0;                                   (* batch dropped *)
ELSIF State >= 5 AND State < 100 AND (AnyTrip OR CmdHold) THEN
  ResumeState := State;                         (* remember where we were *)
  HoldC1 := C1Cmd;
  HoldC2 := C2Cmd;
  State := 100;
END_IF;

IF State <> LastState THEN                      (* restart the step timer *)
  StepTmr(IN := FALSE, PT := T#1h);
  LastState := State;
  NextGiven := FALSE;
END_IF;
StepTmr(IN := TRUE, PT := T#1h);
IF CmdNext THEN NextGiven := TRUE; END_IF;
Progressed := FALSE;
WaitNext := FALSE;

CASE State OF
  0: (* IDLE *)
    GateCmdSP := 0;
    IF (Mode = 2 OR Mode = 3) AND CmdStart AND NOT AnyTrip THEN
      BatchReq := HMI_BatchReq;
      IF BatchReq < 1 THEN BatchReq := 1; END_IF;
      BatchesDone := 0;
      StopAtEnd := FALSE;
      ResumeState := 0;
      Accepted := FALSE;
      State := 5;
    END_IF;

  5: (* LOAD_RECIPE *)
    RecipeBase := (HMI_RecipeSel - 1) * 5;
    TargetKg[1] := RecipeKg[RecipeBase + 1];
    TargetKg[2] := RecipeKg[RecipeBase + 1];   (* edited 'to fix silo 2' *)
    TargetKg[3] := RecipeKg[RecipeBase + 3];
    TargetKg[4] := RecipeKg[RecipeBase + 4];
    TargetKg[5] := RecipeKg[RecipeBase + 5];
    SumKg := 0.0;
    W_NotEnough := FALSE;
    FOR i := 1 TO 5 DO
      Started[i] := FALSE; Done[i] := FALSE; TopUps[i] := 0;
      ActualKg[i] := 0.0; StartKg[i] := 0.0;
      SumKg := SumKg + TargetKg[i];
      IF TargetKg[i] > 0.0 AND WeightKg[i] < TargetKg[i] + 500.0 THEN
        W_NotEnough := TRUE;
      END_IF;
    END_FOR;
    Silo := 1;
    TolPending := FALSE;
    IF SumKg <= 0.0 OR SumKg > 2500.0 OR W_NotEnough THEN
      State := 0;
    ELSE
      State := 10;
    END_IF;

  10: (* START_CHECKS *)
    IF DI_Door_Closed AND NOT AnyTrip THEN
      IF AllHomed THEN State := 20; ELSE State := 12; END_IF;
    END_IF;

  12: (* HOME_GATES *)
    IF AllHomed THEN
      State := 20;
    ELSIF StepTmr.ET >= T#15s THEN
      A_HomeTO := TRUE;
    END_IF;

  20: (* START_MIXER *)
    IF DI_Mix_Run THEN
      IF ResumeState >= 80 AND ResumeState < 100 THEN
        State := ResumeState;
        ResumeState := 0;
      ELSE
        State := 30;
      END_IF;
    END_IF;

  30: (* START_C2: downstream first *)
    IF DI_C2_SpeedOK THEN State := 40; END_IF;

  40: (* START_C1 *)
    IF DI_C1_SpeedOK THEN
      IF ResumeState >= 70 AND ResumeState < 80 THEN State := 70; ELSE State := 50; END_IF;
      ResumeState := 0;
    END_IF;

  50: (* SELECT_SILO *)
    GateCmdSP := 0;
    NextSilo := 0;
    FOR i := 5 TO 1 BY -1 DO
      IF (NOT Done[i]) AND TargetKg[i] > 0.0 THEN NextSilo := i; END_IF;
    END_FOR;
    IF NextSilo = 0 THEN
      State := 70;
    ELSIF Mode = 3 OR NextGiven THEN
      Silo := NextSilo;
      IF NOT Started[Silo] THEN
        StartKg[Silo] := WeightKg[Silo];
        Started[Silo] := TRUE;
      END_IF;
      ProgressKg := StartKg[Silo] - WeightKg[Silo];
      State := 60;
    ELSE
      WaitNext := TRUE;                         (* Semi-auto: waiting for Next *)
    END_IF;

  60: (* FEED: loss-in-weight *)
    Dispensed := StartKg[Silo] - WeightKg[Silo];
    ActualKg[Silo] := Dispensed;
    Remaining := TargetKg[Silo] - Dispensed;
    DribbleKg := MAX(30.0, 0.1 * TargetKg[Silo]);
    IF TopUps[Silo] > 0 THEN
      CutoffKg := 0.5 * InflightKg[Silo];
    ELSE
      CutoffKg := InflightKg[Silo];
    END_IF;
    IF Remaining <= CutoffKg THEN
      GateCmdSP := 0;
      State := 62;
    ELSIF Remaining > DribbleKg AND TopUps[Silo] = 0 THEN
      GateCmdSP := 1000;                        (* fast feed *)
    ELSE
      GateCmdSP := 250;                         (* dribble *)
    END_IF;
    IF Dispensed - ProgressKg >= 2.0 THEN
      ProgressKg := Dispensed;
      Progressed := TRUE;
    END_IF;

  62: (* SETTLE *)
    GateCmdSP := 0;
    IF StepTmr.ET >= T#2s THEN State := 64; END_IF;

  64: (* CHECK_WEIGHT *)
    Dispensed := StartKg[Silo] - WeightKg[Silo];
    ActualKg[Silo] := Dispensed;
    ErrKg := Dispensed - TargetKg[Silo];
    TolKg := MAX(5.0, 0.01 * TargetKg[Silo]);
    IF ABS(ErrKg) <= TolKg THEN
      IF TopUps[Silo] = 0 THEN
        InflightKg[Silo] := LIMIT(0.0, InflightKg[Silo] + 0.5 * ErrKg, 50.0);
      END_IF;
      Done[Silo] := TRUE;
      State := 50;
    ELSIF ErrKg < 0.0 AND TopUps[Silo] < 2 THEN
      TopUps[Silo] := TopUps[Silo] + 1;
      State := 60;
    ELSE
      A_Tol := TRUE;
      TolPending := TRUE;
    END_IF;

  70: (* RUNOUT_C1 *)
    GateCmdSP := 0;
    IF StepTmr.ET >= T#25s THEN State := 72; END_IF;

  72: (* RUNOUT_C2: upstream stopped first *)
    IF StepTmr.ET >= T#35s THEN
      MixRemain := HMI_MixTime_s;
      State := 80;
    END_IF;

  80: (* MIX *)
    IF SecPulse AND MixRemain > 0 THEN MixRemain := MixRemain - 1; END_IF;
    IF MixRemain <= 0 THEN State := 90; END_IF;

  90: (* DOOR_OPEN *)
    IF Mode = 2 AND NOT NextGiven THEN WaitNext := TRUE; END_IF;
    IF (Mode = 3 OR NextGiven) AND DI_Door_Open THEN State := 92; END_IF;

  92: (* DISCHARGE *)
    IF StepTmr.ET >= T#20s THEN State := 94; END_IF;

  94: (* DOOR_CLOSE *)
    IF DI_Door_Closed THEN State := 96; END_IF;

  96: (* BATCH_DONE *)
    BatchesDone := BatchesDone + 1;
    IF BatchesDone >= BatchReq OR StopAtEnd THEN
      State := 0;
    ELSE
      State := 5;
    END_IF;

  100: (* HOLD *)
    GateCmdSP := 0;
    IF CmdResume AND NOT AnyTrip THEN
      IF TolPending THEN                        (* operator accepts the weight *)
        Done[Silo] := TRUE;
        TolPending := FALSE;
        Accepted := TRUE;
      END_IF;
      State := 10;
    END_IF;
END_CASE;

DoorOpenTmr(IN := (State = 90) AND (Mode = 3 OR NextGiven) AND NOT DI_Door_Open, PT := T#10s);
IF DoorOpenTmr.Q THEN A_DoorOpenTO := TRUE; END_IF;
DoorCloseTmr(IN := (State = 94) AND NOT DI_Door_Closed, PT := T#10s);
IF DoorCloseTmr.Q THEN A_DoorCloseTO := TRUE; END_IF;
NoFlowTmr(IN := (State = 60) AND (GatePos[Silo] >= 200) AND NOT Progressed, PT := T#8s);
IF NoFlowTmr.Q THEN A_NoFlow := TRUE; END_IF;

(* ===== 9. Outputs: what the state asks for ===== *)
SeqC2 := (State >= 30 AND State <= 72) OR (State = 100 AND HoldC2 AND StepTmr.ET < T#60s);
SeqC1 := (State >= 40 AND State <= 70) OR (State = 100 AND HoldC1 AND StepTmr.ET < T#25s);
SeqMix := (State >= 20 AND State <= 96) OR State = 100;
SeqDoor := (State = 90 AND (Mode = 3 OR NextGiven)) OR State = 92;
SeqHome := State = 12;
FOR i := 1 TO 5 DO
  GateSP[i] := 0;
END_FOR;
IF State = 60 THEN GateSP[Silo] := GateCmdSP; END_IF;

IF Mode = 1 THEN                                (* Manual from the Feeder HMI *)
  ManBits := HMI_ManualBits;
  SeqC2 := (ManBits AND 16#0001) <> 16#0000;
  SeqC1 := (ManBits AND 16#0002) <> 16#0000;
  SeqMix := (ManBits AND 16#0004) <> 16#0000;
  SeqDoor := (ManBits AND 16#0008) <> 16#0000;
  SeqHome := (ManBits AND 16#0010) <> 16#0000;
  GateSP[1] := LIMIT(0, HMI_ManGateSP1, 1000);
  GateSP[2] := LIMIT(0, HMI_ManGateSP2, 1000);
  GateSP[3] := LIMIT(0, HMI_ManGateSP3, 1000);
  GateSP[4] := LIMIT(0, HMI_ManGateSP4, 1000);
  GateSP[5] := LIMIT(0, HMI_ManGateSP5, 1000);
ELSE
  HMI_ManualBits := 16#0000;
  HMI_ManGateSP1 := 0; HMI_ManGateSP2 := 0; HMI_ManGateSP3 := 0;
  HMI_ManGateSP4 := 0; HMI_ManGateSP5 := 0;
END_IF;

(* ===== 10. Interlocks: active in every mode ===== *)
C2Cmd := SeqC2 AND NOT A_C2Trip AND NOT A_C2Zero;
C1Cmd := SeqC1 AND C2Cmd AND DI_C2_SpeedOK AND NOT A_C1Trip AND NOT A_C1Zero;
MixCmd := SeqMix AND NOT A_MixFail;
DoorCmd := SeqDoor;
IF NOT (C1Cmd AND DI_C1_SpeedOK) THEN           (* never feed onto a stopped belt *)
  FOR i := 1 TO 5 DO
    GateSP[i] := 0;
  END_FOR;
END_IF;
IF A_EStop OR NOT DI_EStopOK THEN
  C1Cmd := FALSE; C2Cmd := FALSE; MixCmd := FALSE; DoorCmd := FALSE; SeqHome := FALSE;
  FOR i := 1 TO 5 DO
    GateSP[i] := 0;
  END_FOR;
END_IF;

(* ===== 11. Alarm words, lamp and sounder ===== *)
Alarm1 := 16#0000;
IF A_EStop THEN Alarm1 := Alarm1 OR 16#0001; END_IF;
IF A_Comms THEN Alarm1 := Alarm1 OR 16#0002; END_IF;
IF A_C1Trip THEN Alarm1 := Alarm1 OR 16#0004; END_IF;
IF A_C2Trip THEN Alarm1 := Alarm1 OR 16#0008; END_IF;
IF A_C1Zero THEN Alarm1 := Alarm1 OR 16#0010; END_IF;
IF A_C2Zero THEN Alarm1 := Alarm1 OR 16#0020; END_IF;
IF A_MixFail THEN Alarm1 := Alarm1 OR 16#0040; END_IF;
IF A_DoorOpenTO THEN Alarm1 := Alarm1 OR 16#0080; END_IF;
IF A_DoorCloseTO THEN Alarm1 := Alarm1 OR 16#0100; END_IF;
IF A_GateFault THEN Alarm1 := Alarm1 OR 16#0200; END_IF;
IF A_Tol THEN Alarm1 := Alarm1 OR 16#0400; END_IF;
IF A_NoFlow THEN Alarm1 := Alarm1 OR 16#0800; END_IF;
IF A_Signal THEN Alarm1 := Alarm1 OR 16#1000; END_IF;
IF W_Low THEN Alarm1 := Alarm1 OR 16#2000; END_IF;
IF W_NotEnough THEN Alarm1 := Alarm1 OR 16#4000; END_IF;
IF A_HomeTO THEN Alarm1 := Alarm1 OR 16#8000; END_IF;
Alarm2 := 16#0000;
FOR i := 1 TO 5 DO
  IF LowSilo[i] THEN Alarm2 := Alarm2 OR SHL(WORD#1, i - 1); END_IF;
  IF GateFaultSilo[i] THEN Alarm2 := Alarm2 OR SHL(WORD#1, i + 4); END_IF;
  IF SignalSilo[i] THEN Alarm2 := Alarm2 OR SHL(WORD#1, i + 9); END_IF;
END_FOR;
IF ((Alarm1 AND NOT PrevAlarm1) <> 16#0000) OR ((Alarm2 AND NOT PrevAlarm2) <> 16#0000) THEN
  SounderOn := TRUE;                            (* a new alarm sounds until acknowledged *)
END_IF;
PrevAlarm1 := Alarm1;
PrevAlarm2 := Alarm2;

(* ===== 12. Write the remote rack ===== *)
DO_C1_RunCmd := C1Cmd;
DO_C2_RunCmd := C2Cmd;
DO_Mix_RunCmd := MixCmd;
DO_Door_OpenSol := DoorCmd;
DO_C1_Reset := ResetPulse;
DO_C2_Reset := ResetPulse;
DO_Gates_Reset := ResetPulse;
DO_Gates_Enable := DI_EStopOK;
DO_Gates_Home := SeqHome;
DO_AlarmLamp := (AnyTrip AND Flash) OR (W_Low AND NOT AnyTrip);
DO_Sounder := SounderOn;
HR_GateSP1 := GateSP[1]; HR_GateSP2 := GateSP[2]; HR_GateSP3 := GateSP[3];
HR_GateSP4 := GateSP[4]; HR_GateSP5 := GateSP[5];
HR_C1_SpeedRef := 500;
HR_C2_SpeedRef := 500;

(* ===== 13. Write the HMI map ===== *)
Status := 16#0000;
IF State > 0 AND State < 100 THEN Status := Status OR 16#0001; END_IF;
IF State = 100 THEN Status := Status OR 16#0002; END_IF;
IF WaitNext THEN Status := Status OR 16#0004; END_IF;
IF Accepted THEN Status := Status OR 16#0008; END_IF;
IF W_NotEnough THEN Status := Status OR 16#0010; END_IF;
HMI_Status := Status;
HMI_Alarm1 := Alarm1;
HMI_Alarm2 := Alarm2;
HMI_Mode := Mode;
HMI_State := State;
IF State >= 50 AND State <= 64 THEN HMI_ActiveSilo := Silo; ELSE HMI_ActiveSilo := 0; END_IF;
HMI_BatchesDone := BatchesDone;
HMI_MixRemain_s := MixRemain;
HMI_Weight1 := REAL_TO_INT(WeightKg[1]); HMI_Weight2 := REAL_TO_INT(WeightKg[2]);
HMI_Weight3 := REAL_TO_INT(WeightKg[3]); HMI_Weight4 := REAL_TO_INT(WeightKg[4]);
HMI_Weight5 := REAL_TO_INT(WeightKg[5]);
HMI_Target1 := REAL_TO_INT(TargetKg[1]); HMI_Target2 := REAL_TO_INT(TargetKg[2]);
HMI_Target3 := REAL_TO_INT(TargetKg[3]); HMI_Target4 := REAL_TO_INT(TargetKg[4]);
HMI_Target5 := REAL_TO_INT(TargetKg[5]);
HMI_Actual1 := REAL_TO_INT(ActualKg[1]); HMI_Actual2 := REAL_TO_INT(ActualKg[2]);
HMI_Actual3 := REAL_TO_INT(ActualKg[3]); HMI_Actual4 := REAL_TO_INT(ActualKg[4]);
HMI_Actual5 := REAL_TO_INT(ActualKg[5]);
HMI_Inflight1 := REAL_TO_INT(InflightKg[1] * 10.0); HMI_Inflight2 := REAL_TO_INT(InflightKg[2] * 10.0);
HMI_Inflight3 := REAL_TO_INT(InflightKg[3] * 10.0); HMI_Inflight4 := REAL_TO_INT(InflightKg[4] * 10.0);
HMI_Inflight5 := REAL_TO_INT(InflightKg[5] * 10.0);
HMI_GatePos1 := GatePos[1]; HMI_GatePos2 := GatePos[2]; HMI_GatePos3 := GatePos[3];
HMI_GatePos4 := GatePos[4]; HMI_GatePos5 := GatePos[5];
HMI_C1_Freq := IR_C1_Freq; HMI_C1_Current := IR_C1_Current; HMI_C1_FaultCode := IR_C1_FaultCode;
HMI_C2_Freq := IR_C2_Freq; HMI_C2_Current := IR_C2_Current; HMI_C2_FaultCode := IR_C2_FaultCode;
HMI_GateAlarm1 := IR_GateAlarm1; HMI_GateAlarm2 := IR_GateAlarm2; HMI_GateAlarm3 := IR_GateAlarm3;
HMI_GateAlarm4 := IR_GateAlarm4; HMI_GateAlarm5 := IR_GateAlarm5;
END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#100ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : Batching;
  END_RESOURCE
END_CONFIGURATION
