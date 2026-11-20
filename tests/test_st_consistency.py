"""The ST program can't be compiled here (OpenPLC isn't installed), so check that
it matches the address map and the tested Python copy."""

import pathlib
import re
import unittest

from lab.iomap import STATES, st_located

ROOT = pathlib.Path(__file__).resolve().parents[1]
ST = (ROOT / "plc" / "batching.st").read_text(encoding="utf-8")
F6 = (ROOT / "plc" / "faults" / "F6_batching_bad_edit.st").read_text(encoding="utf-8")
PY = (ROOT / "lab" / "controller.py").read_text(encoding="utf-8")


def strip_comments(text):
    return re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)


class StMatchesMap(unittest.TestCase):
    def test_located_variables_match_iomap(self):
        found = set(re.findall(r"^\s*(\w+)\s+AT\s+(%\w+[\d.]*)\s*:\s*(\w+);", ST, flags=re.M))
        self.assertEqual(found, set(st_located()))

    def test_no_address_used_twice(self):
        addrs = [a for _, a, _ in st_located()]
        self.assertEqual(len(addrs), len(set(addrs)))

    def test_case_steps_match_python_and_map(self):
        body = strip_comments(ST)
        case = body[body.index("CASE State OF"):body.index("END_CASE")]
        st_steps = {int(n) for n in re.findall(r"^\s*(\d+)\s*:", case, flags=re.M)}
        py_steps = {int(n) for n in re.findall(r"\bs == (\d+)", PY)}
        self.assertEqual(st_steps, set(STATES))
        self.assertEqual(py_steps, set(STATES))

    def test_timer_presets_match_python(self):
        st_t = sorted(int(n) for n in re.findall(r"T#(\d+)s\b", strip_comments(ST)))
        for secs in set(st_t) - {1}:
            self.assertRegex(PY, rf"\b{secs * 1000}\b", f"{secs} s preset missing in controller.py")

    def test_every_timer_is_called(self):
        decl = re.findall(r"^\s*([\w, ]+)\s*:\s*TON;", ST, flags=re.M)
        names = [n.strip() for line in decl for n in line.split(",")]
        self.assertGreaterEqual(len(names), 10)
        for n in names:
            self.assertRegex(ST, rf"\b{n}\(IN", n)

    def test_one_fb_instance_per_declaration(self):
        # OpenPLC v3's matiec segfaults on "A, B : TON;" (found 2026-11-20).
        multi = re.findall(r"^\s*\w+\s*,[\w ,]*:\s*(TON|TOF|TP|R_TRIG|F_TRIG|CTU|CTD)\s*;", ST, flags=re.M)
        self.assertEqual(multi, [])

    def test_openplc_monitoring_can_parse_every_located_line(self):
        # OpenPLC v3 webserver/monitoring.py: line.strip().split(' ') -> name, AT, %addr, :, TYPE;
        lines = [l for l in ST.splitlines()
                 if l.find(" AT ") > 0 and "%" in l and "(*" not in l and "*)" not in l]
        self.assertEqual(len(lines), len(st_located()))
        for line in lines:
            tmp = line.strip().split(" ")
            self.assertEqual((tmp[1], tmp[3]), ("AT", ":"), line)
            self.assertTrue(tmp[2].startswith("%"), line)

    def test_configuration_block(self):
        self.assertIn("TASK task0(INTERVAL := T#100ms", ST)
        self.assertIn("PROGRAM instance0 WITH task0 : Batching;", ST)

    def test_statements_terminated(self):
        for kw in ("IF", "FOR", "CASE"):
            opens = len(re.findall(rf"(?<![\w_]){kw}\b", strip_comments(ST)))
            ends = len(re.findall(rf"END_{kw}\b", strip_comments(ST)))
            self.assertEqual(opens, ends, kw)


class F6File(unittest.TestCase):
    def test_exactly_one_logic_line_differs(self):
        a = strip_comments(ST).splitlines()
        b = strip_comments(F6).splitlines()
        self.assertEqual(len(a), len(b))
        diff = [(x.strip(), y.strip()) for x, y in zip(a, b) if x != y]
        diff = [d for d in diff if not d[0].startswith("PROGRAM")]
        self.assertEqual(diff, [("TargetKg[2] := RecipeKg[RecipeBase + 2];",
                                 "TargetKg[2] := RecipeKg[RecipeBase + 1];")])


if __name__ == "__main__":
    unittest.main()
