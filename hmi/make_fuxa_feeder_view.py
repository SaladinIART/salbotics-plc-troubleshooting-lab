"""Create or update the "Feeder HMI" screen in FUXA (maintenance / troubleshooting screen
at the auto-feeding system: Manual, Semi-auto and Auto).

    python hmi/make_fuxa_feeder_view.py            # needs FUXA running and the BatchPLC device
    python hmi/make_fuxa_feeder_view.py --dry-run  # print the view JSON only

Run hmi/make_fuxa_device.py first. Reload the FUXA editor afterwards.

Manual mode drives devices through the ManualBits word (bit0 C2, bit1 C1, bit2 mixer,
bit3 door, bit4 home gates). The buttons write whole preset words, so each press
replaces the previous selection. "C1 alone" is there on purpose: the interlock keeps
conveyor 1 stopped unless conveyor 2 is running, which is worth seeing once.
"""

import argparse
import json

from fuxa_view import DARK, MUTED, TEXT, View, load_tags, post, view_json

VIEW_ID = "v_feeder-hmi"


def build(tags):
    v = View(tags, prefix="fd")
    v.rect(0, 0, 1024, 56, fill=DARK, stroke=DARK)
    v.text(20, 36, "FEEDER HMI  ·  maintenance", size=22, fill="#ffffff", weight="bold")
    v.text(1004, 34, "Salbotics troubleshooting lab · simulated plant", size=12, fill="#cbd5e1", anchor="end")

    # Mode
    v.rect(20, 72, 300, 156)
    v.text(36, 98, "Mode", size=16, weight="bold")
    v.text(36, 124, "Now (1 Man · 2 Semi · 3 Auto)", size=14, fill=MUTED)
    v.value(304, 124, "Mode")
    for k, (label, m) in enumerate([("Manual", 1), ("Semi-auto", 2), ("Auto", 3)]):
        v.button(32 + k * 94, 140, 90, 44, label, m, tag="ModeReq")
    v.text(36, 208, "Mode changes only when the sequence is idle (step 0).", size=12, fill=MUTED)

    # Sequence
    v.rect(336, 72, 668, 156)
    v.text(352, 98, "Sequence", size=16, weight="bold")
    for k, (label, tag) in enumerate([("Step", "State"), ("Silo weighing", "ActiveSilo"),
                                      ("Status word", "Status"), ("Batches done", "BatchesDone")]):
        y = 122 + k * 24
        v.text(352, y, label, size=14, fill=MUTED)
        v.value(520, y, tag)
    v.text(352, 218, "Status bit 2 = waiting for Next (semi-auto)", size=12, fill=MUTED)
    cmds = [("Start", 1, "#16a34a", "#ffffff"), ("Next", 6, "#ffffff", TEXT),
            ("Hold", 3, "#f59e0b", TEXT), ("Resume", 4, "#ffffff", TEXT),
            ("Reset + ack", 5, "#2563eb", "#ffffff"), ("Abort", 7, "#dc2626", "#ffffff")]
    for k, (label, cmd, bg, fg) in enumerate(cmds):
        col, row = k % 3, k // 3
        v.button(548 + col * 148, 108 + row * 52, 142, 44, label, cmd, bg, fg)

    # Silos and gates
    v.rect(20, 244, 984, 222)
    v.text(36, 270, "Silos and gates", size=16, weight="bold")
    v.text(380, 270, "Manual gate opening: 0–1000 = 0–100.0 %. Works only in Manual, after homing, "
                     "with conveyor 1 running.", size=12, fill=MUTED)
    heads = [("Silo", 36, "start"), ("Weight kg", 300, "end"), ("Gate open %", 430, "end"),
             ("Gate alarm", 540, "end"), ("In-flight kg", 660, "end"), ("Manual gate setpoint", 700, "start")]
    for label, x, anchor in heads:
        v.text(x, 296, label, size=13, fill=MUTED, anchor=anchor, weight="bold")
    for i, letter in enumerate("ABCDE", start=1):
        y = 324 + (i - 1) * 28
        v.text(36, y, f"Silo {i}  (Material {letter})", size=14)
        v.value(300, y, f"Weight{i}", size=15)
        v.value(430, y, f"GatePos{i}", size=15)
        v.value(540, y, f"GateAlarm{i}", size=15)
        v.value(660, y, f"Inflight{i}", size=15)
        v.input(700, y - 19, 90, f"ManGateSP{i}", 0, 1000, h=26)
        v.value(860, y, f"ManGateSP{i}", size=14, fill=MUTED)
    v.text(36, 458, "Gate alarm 1 = stall (jammed). Silo low-level and gate-fault bits are in alarm word 2.",
           size=12, fill=MUTED)

    # Manual devices
    v.rect(20, 482, 480, 270)
    v.text(36, 508, "Manual devices", size=16, weight="bold")
    v.text(36, 532, "Selected word (bit0 C2 · bit1 C1 · bit2 mixer · bit3 door · bit4 home)", size=12, fill=MUTED)
    v.value(484, 532, "ManualBits", size=15)
    presets = [("All stop", 0, "#dc2626", "#ffffff"), ("Home gates", 16, "#ffffff", TEXT),
               ("C2 run", 1, "#ffffff", TEXT), ("C2 + C1 run", 3, "#ffffff", TEXT),
               ("C2 + C1 + mixer", 7, "#ffffff", TEXT), ("Mixer run", 4, "#ffffff", TEXT),
               ("Mixer + door open", 12, "#ffffff", TEXT), ("C1 alone (interlock)", 2, "#fde68a", TEXT)]
    for k, (label, word, bg, fg) in enumerate(presets):
        col, row = k % 2, k // 2
        v.button(32 + col * 230, 548 + row * 50, 224, 44, label, word, bg, fg, tag="ManualBits")

    # Conveyors
    v.rect(516, 482, 488, 150)
    v.text(532, 508, "Conveyors (VFDs)", size=16, weight="bold")
    for label, x in [("Hz", 720), ("A", 820), ("Fault code", 960)]:
        v.text(x, 534, label, size=13, fill=MUTED, anchor="end", weight="bold")
    for k, (name, tag) in enumerate([("Conveyor 1 (collecting)", "C1"), ("Conveyor 2 (incline)", "C2")]):
        y = 564 + k * 30
        v.text(532, y, name, size=14)
        v.value(720, y, f"{tag}_Freq", size=15)
        v.value(820, y, f"{tag}_Current", size=15)
        v.value(960, y, f"{tag}_FaultCode", size=15)
    v.text(532, 620, "Fault code 2 = motor overload. Find the cause before you reset.", size=12, fill=MUTED)

    # Alarms
    v.rect(516, 644, 488, 108)
    v.text(532, 670, "Alarms", size=16, weight="bold")
    v.text(532, 698, "Alarm word 1", size=14, fill=MUTED)
    v.value(700, 698, "Alarm1", size=15)
    v.text(532, 724, "Alarm word 2", size=14, fill=MUTED)
    v.value(700, 724, "Alarm2", size=15)
    v.text(720, 698, "Bit lists: DESIGN.md", size=12, fill=MUTED)
    v.text(720, 724, "0 = no alarm", size=12, fill=MUTED)

    return view_json(VIEW_ID, "Feeder HMI", v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    view = build(load_tags())
    if args.dry_run:
        print(json.dumps(view, indent=1))
        return
    print("FUXA:", post("set-view", view), f"Feeder HMI: {len(view['items'])} bound controls")


if __name__ == "__main__":
    main()
