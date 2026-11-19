"""Shared helpers for building FUXA 1.3.1 screens from the lab's tag list.

The view format (svg-ext-value, svg-ext-html_button, svg-ext-html_input and the
click -> onSetValue event) was read from a screen saved by FUXA's own editor and
from its client code. Used by make_fuxa_mixer_view.py and make_fuxa_feeder_view.py.
"""

import json
import urllib.request
from xml.sax.saxutils import escape

FUXA = "http://127.0.0.1:1881"
DARK, PANEL, LINE, TEXT, MUTED = "#1f2937", "#f3f4f6", "#d1d5db", "#111827", "#4b5563"


class View:
    def __init__(self, tags, prefix="mx"):
        self.tags = tags          # tag name -> tag id
        self.svg = []
        self.items = {}
        self.n = 0
        self.p = prefix

    def _id(self):
        self.n += 1
        return f"{self.n:03d}"

    def rect(self, x, y, w, h, fill=PANEL, stroke=LINE):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
                        f'stroke="{stroke}" stroke-width="1" id="svg_{self.p}{self._id()}"/>')

    def text(self, x, y, s, size=14, fill=TEXT, anchor="start", weight="normal"):
        self.svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" '
                        f'font-weight="{weight}" fill="{fill}" stroke-width="0" text-anchor="{anchor}" '
                        f'xml:space="preserve" id="svg_{self.p}{self._id()}">{escape(s)}</text>')

    def value(self, x, y, tag, size=16, anchor="end", fill=TEXT):
        i = self._id()
        gid = f"VAL_{self.p}{i}"
        self.svg.append(
            f'<g xml:space="preserve" text-anchor="{anchor}" font-family="sans-serif" stroke-width="0" '
            f'font-size="{size}" stroke="{fill}" fill="{fill}" y="{y}" x="{x}" type="svg-ext-value" id="{gid}">'
            f'<text y="{y}" x="{x}" xml:space="preserve" text-anchor="{anchor}" font-family="sans-serif" '
            f'font-size="{size}" font-weight="bold" stroke="{fill}" fill="{fill}" stroke-width="0" '
            f'id="VAL_{self.p}t{i}">##</text></g>')
        self.items[gid] = {"id": gid, "type": "svg-ext-value", "name": tag, "label": "Value",
                           "hide": False, "lock": False,
                           "property": {"variableId": self.tags[tag], "events": [], "actions": []}}

    def button(self, x, y, w, h, label, cmd, bg="#ffffff", fg=TEXT, tag="Cmd"):
        i = self._id()
        gid = f"HXB_{self.p}{i}"
        self.svg.append(
            f'<g xml:space="preserve" stroke="rgba(0,0,0,0)" fill="rgba(0,0,0,0)" type="svg-ext-html_button" id="{gid}">'
            f'<rect id="svg_{self.p}b{i}" height="{h}" width="{w}" y="{y}" x="{x}" stroke-width="0"/>'
            f'<foreignObject id="H-HXB_{self.p}{i}" width="{w}" height="{h}" y="{y}" x="{x}">'
            f'<BUTTON xmlns="http://www.w3.org/1999/xhtml" style="width:calc(100% - 6px);height:calc(100% - 6px);'
            f'text-align:center;background-color:{bg};color:{fg};font-size:15px;font-family:sans-serif;'
            f'font-weight:bold;" class="md-btn  md-btn-raised" id="B-HXB_{self.p}{i}">{escape(label)}</BUTTON>'
            f'</foreignObject></g>')
        cmd_id = self.tags[tag]
        self.items[gid] = {"id": gid, "type": "svg-ext-html_button", "name": label, "label": "HtmlButton",
                           "hide": False, "lock": False,
                           "property": {"variableId": cmd_id, "actions": [],
                                        "events": [{"type": "click", "action": "onSetValue",
                                                    "actparam": str(cmd),
                                                    "actoptions": {"variableId": cmd_id}}]}}

    def input(self, x, y, w, tag, mn, mx, h=28):
        i = self._id()
        gid = f"HXI_{self.p}{i}"
        self.svg.append(
            f'<g xml:space="preserve" stroke="#000000" fill="#FFFFFF" type="svg-ext-html_input" id="{gid}">'
            f'<rect id="svg_{self.p}i{i}" height="{h}" width="{w}" y="{y}" x="{x}" stroke-width="0"/>'
            f'<foreignObject id="H-HXI_{self.p}{i}" width="{w}" height="{h}" y="{y}" x="{x}">'
            f'<INPUT xmlns="http://www.w3.org/1999/xhtml" style="width: calc(100% - 7px); height: calc(100% - 7px); '
            f'text-align: right; border: 1px solid #9ca3af; font-size: 15px; font-family: sans-serif; '
            f'background-color: rgb(255, 255, 255); color: rgb(0, 0, 0);" value="#.##" type="text" '
            f'id="I-HXI_{self.p}{i}"/></foreignObject></g>')
        self.items[gid] = {"id": gid, "type": "svg-ext-html_input", "name": tag, "label": "HtmlInput",
                           "hide": False, "lock": False,
                           "property": {"variableId": self.tags[tag], "events": [], "actions": [],
                                        "options": {"type": "number", "numeric": True, "min": mn, "max": mx}}}

    def svgcontent(self):
        body = "\n".join(self.svg)
        return ('<svg width="1024" height="768" xmlns="http://www.w3.org/2000/svg" '
                'xmlns:svg="http://www.w3.org/2000/svg" xmlns:html="http://www.w3.org/1999/xhtml">'
                '<filter id="blur-filter" x="-3" y="-3" width="200" height="200">'
                '<feGaussianBlur stdDeviation="3"/></filter>'
                f'<g><title>Layer 1</title>{body}</g></svg>')



def view_json(view_id, name, v):
    return {"id": view_id, "name": name, "type": "svg",
            "profile": {"width": 1024, "height": 768, "bkcolor": "#ffffffff", "margin": 10,
                        "align": "topCenter", "gridType": "fixed", "viewRenderDelay": 0},
            "items": v.items, "variables": {}, "svgcontent": v.svgcontent()}


def load_tags():
    """BatchPLC tag name -> FUXA tag id."""
    with urllib.request.urlopen(FUXA + "/api/project", timeout=5) as r:
        project = json.load(r)
    dev = next((d for d in project["devices"].values() if d.get("name") == "BatchPLC"), None)
    if not dev:
        raise SystemExit("No BatchPLC device in FUXA: run hmi/make_fuxa_device.py first.")
    return {t["name"]: t["id"] for t in dev["tags"].values()}


def post(cmd, data):
    body = json.dumps({"cmd": cmd, "data": data}).encode()
    req = urllib.request.Request(FUXA + "/api/projectData", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status
