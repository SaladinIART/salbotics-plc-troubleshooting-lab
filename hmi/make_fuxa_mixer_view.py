"""Create or update the "Mixer HMI" screen in FUXA (operator screen).

    python hmi/make_fuxa_mixer_view.py            # needs FUXA running and the BatchPLC device
    python hmi/make_fuxa_mixer_view.py --dry-run  # print the view JSON only

Run hmi/make_fuxa_device.py first: this script binds to the BatchPLC tags by name.
Reload the FUXA editor afterwards. Built for FUXA 1.3.1 (view format read from a
screen saved by its own editor).
"""

import argparse
import json

from fuxa_view import MUTED, TEXT, DARK, View, load_tags, post, view_json

VIEW_ID = "v_mixer-hmi"


def build(tags):
    v = View(tags)
    v.rect(0, 0, 1024, 56, fill=DARK, stroke=DARK)
    v.text(20, 36, "MIXER HMI  ·  operator", size=22, fill="#ffffff", weight="bold")
    v.text(1004, 34, "Salbotics troubleshooting lab · simulated plant", size=12, fill="#cbd5e1", anchor="end")

    # Batch status
    v.rect(20, 72, 320, 272)
    v.text(36, 98, "Batch status", size=16, weight="bold")
    rows = [("Mode (1 Man · 2 Semi · 3 Auto)", "Mode"), ("Step (see list)", "State"),
            ("Silo weighing now", "ActiveSilo"), ("Batches done", "BatchesDone"),
            ("Mixing time left (s)", "MixRemain_s"), ("Status word", "Status"),
            ("Alarm word 1", "Alarm1"), ("Alarm word 2", "Alarm2")]
    for k, (label, tag) in enumerate(rows):
        y = 128 + k * 28
        v.text(36, y, label, size=14, fill=MUTED)
        v.value(324, y, tag)

    # Batch settings
    v.rect(356, 72, 300, 200)
    v.text(372, 98, "Batch settings", size=16, weight="bold")
    v.text(372, 116, "Type a number, press Enter", size=12, fill=MUTED)
    for k, (label, tag, mn, mx) in enumerate([("Recipe (1–4)", "RecipeSel", 1, 4),
                                              ("Batches to make", "BatchReq", 1, 99),
                                              ("Mixing time (s)", "MixTime_s", 0, 600)]):
        y = 140 + k * 40
        v.text(372, y + 19, label, size=14, fill=MUTED)
        v.input(520, y, 90, tag, mn, mx)
        v.value(640, y + 19, tag, size=14, fill=MUTED)

    # Commands
    v.rect(672, 72, 332, 272)
    v.text(688, 98, "Commands", size=16, weight="bold")
    buttons = [("Start", 1, "#16a34a", "#ffffff"), ("Stop at end", 2, "#ffffff", TEXT),
               ("Hold", 3, "#f59e0b", TEXT), ("Resume / accept", 4, "#ffffff", TEXT),
               ("Reset + ack", 5, "#2563eb", "#ffffff"), ("Next (semi-auto)", 6, "#ffffff", TEXT),
               ("Abort batch", 7, "#dc2626", "#ffffff")]
    for k, (label, cmd, bg, fg) in enumerate(buttons):
        col, row = k % 2, k // 2
        v.button(688 + col * 156, 112 + row * 52, 148, 44, label, cmd, bg, fg)

    # This batch
    v.rect(20, 360, 636, 252)
    v.text(36, 386, "This batch", size=16, weight="bold")
    heads = [("Material", 36, "start"), ("Target kg", 250, "end"), ("Actual kg", 360, "end"),
             ("Silo kg", 470, "end"), ("Gate %", 560, "end"), ("In-flight kg", 640, "end")]
    for label, x, anchor in heads:
        v.text(x, 414, label, size=13, fill=MUTED, anchor=anchor, weight="bold")
    for i, letter in enumerate("ABCDE", start=1):
        y = 444 + (i - 1) * 32
        v.text(36, y, f"Material {letter}  (silo {i})", size=14)
        v.value(250, y, f"Target{i}", size=15)
        v.value(360, y, f"Actual{i}", size=15)
        v.value(470, y, f"Weight{i}", size=15)
        v.value(560, y, f"GatePos{i}", size=15)
        v.value(640, y, f"Inflight{i}", size=15)

    # Step list
    v.rect(672, 360, 332, 388)
    v.text(688, 386, "Step numbers", size=16, weight="bold")
    steps = [(0, "Idle"), (5, "Load recipe"), (10, "Start checks"), (12, "Home gates"),
             (20, "Start mixer"), (30, "Start conveyor 2"), (40, "Start conveyor 1"),
             (50, "Select silo"), (60, "Feeding"), (62, "Settle"), (64, "Check weight"),
             (70, "Run out conveyor 1"), (72, "Run out conveyor 2"), (80, "Mixing"),
             (90, "Open door"), (92, "Discharge"), (94, "Close door"), (96, "Batch done"),
             (100, "HOLD: check alarms")]
    for k, (n, name) in enumerate(steps):
        col, row = k // 10, k % 10
        x = 688 + col * 160
        y = 412 + row * 32
        v.text(x + 26, y, str(n), size=13, anchor="end", weight="bold")
        v.text(x + 34, y, name, size=13, fill=MUTED)

    v.text(20, 640, "Alarms: a flashing lamp means a trip, a steady lamp a warning. Reset + ack silences the sounder; "
                    "Resume carries on.", size=12, fill=MUTED)
    v.text(20, 660, "Alarm word bits are listed in DESIGN.md (alarm word 1 and 2).", size=12, fill=MUTED)

    return view_json(VIEW_ID, "Mixer HMI", v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    tags = load_tags()
    view = build(tags)
    if args.dry_run:
        print(json.dumps(view, indent=1))
        return
    print("FUXA:", post("set-view", view), f"Mixer HMI: {len(view['items'])} bound controls")


if __name__ == "__main__":
    main()
