"""Synthetic engineering-drawing PDFs with planted compliance flaws, plus the ground truth to score them.

`generate_drawings(n, flaw_rate, seed, out_dir)` draws `n` mock sheets with ReportLab (a title block, a
revision table, general notes and a schematic built from lines, boxes and text) and plants a known flaw in
exactly `round(n * flaw_rate)` of them. Every planted flaw is recorded with the bounding box of the element
that is wrong, so the compliance judge (03_doc_intelligence) can be scored against it.

Drawing types, which are also the `ai_classify` labels:  ISO (piping isometric), PID (P&ID), GA (general
arrangement plan), SPEC (specification sheet with tables), OTHER (symbols and legend sheet, never flawed).

Flaw taxonomy (one citation and one severity per type; a type is planted at most once per drawing):

    flange_rating_mismatch            ASME B16.5 §4.2    flange class too low for the line's design pressure
    missing_loto_tag                  OSHA 1910.147      powered equipment drawn without its LOTO isolation tag
    egress_width_under_code           IBC 1005.1         exit clear width below the width required for its load
    weld_joint_spec_mismatch          ASME B31.3 §341    weld joint type / examination differs from the piping class
    missing_pressure_relief_notation  ASME B31.3 §322    pressure vessel (or schedule row) without its PSV notation

Conventions the downstream tasks rely on:

* `page_num` is 0-based, like the page ids `ai_parse_document` returns. A drawing has one or two sheets.
* `bbox` is `[x, y, w, h]`, each normalised to 0.0-1.0 of the page, origin at the TOP-LEFT with y growing
  downwards (the same frame as the parser's boxes and a browser overlay; PDF user space is bottom-left).
* The box encloses the offending element and, for a "missing" flaw, the empty slot where it belongs.
* Dates, names and layouts are random but seeded: the same `seed` gives byte-identical PDFs
  (ReportLab runs with `invariant=1`), manifest and ground truth.

The file name starts with a digit, so import it by string:  importlib.import_module("02_generate_drawings").
"""
from __future__ import annotations

import io
import json
import math
import random
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from faker import Faker
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# --------------------------------------------------------------------------------------------------
# Taxonomy and vocabulary
# --------------------------------------------------------------------------------------------------

FLAW_TYPES = {  # flaw_type: (citation, severity)
    "flange_rating_mismatch": ("ASME B16.5 §4.2", "critical"),
    "missing_loto_tag": ("OSHA 1910.147", "high"),
    "egress_width_under_code": ("IBC 1005.1", "high"),
    "weld_joint_spec_mismatch": ("ASME B31.3 §341", "medium"),
    "missing_pressure_relief_notation": ("ASME B31.3 §322", "critical"),
}

# Which flaw types each kind of sheet has an element for.
SUPPORTS = {
    "ISO": ("flange_rating_mismatch", "weld_joint_spec_mismatch"),
    "PID": ("flange_rating_mismatch", "missing_loto_tag", "missing_pressure_relief_notation"),
    "GA": ("missing_loto_tag", "egress_width_under_code"),
    "SPEC": ("flange_rating_mismatch", "weld_joint_spec_mismatch", "missing_pressure_relief_notation"),
    "OTHER": (),
}
TYPE_WEIGHTS = {"ISO": 0.34, "PID": 0.30, "GA": 0.22, "SPEC": 0.11, "OTHER": 0.03}
PAGE2_PROBABILITY = {"ISO": 0.12, "PID": 0.15, "GA": 0.10, "SPEC": 0.40, "OTHER": 0.0}
MULTI_FLAW_SHARE = {3: 0.04, 2: 0.06}  # of the flawed drawings: ~4% carry three flaws, ~6% two (so ~10% carry several)

# Disciplines are the compliance_findings.discipline values used by the project datasets.
DISCIPLINE_WEIGHTS = {
    "ISO": {"piping": 1.0},
    "PID": {"piping": 0.70, "instr": 0.30},
    "GA": {"structural": 0.35, "mechanical": 0.35, "electrical": 0.30},
    "SPEC": {"piping": 0.65, "mechanical": 0.35},
    "OTHER": {"piping": 0.4, "mechanical": 0.2, "electrical": 0.2, "instr": 0.1, "structural": 0.1},
}
DISCIPLINE_CODE = {"piping": "PIP", "structural": "STR", "mechanical": "MEC", "electrical": "ELE", "instr": "INS"}
TYPE_CODE = {"ISO": "ISO", "PID": "PID", "GA": "GA", "SPEC": "SPC", "OTHER": "DTL"}
REVISIONS = "ABCDE"
REVISION_WEIGHTS = (0.12, 0.26, 0.30, 0.20, 0.12)
REVISION_NOTES = ("ISSUED FOR REVIEW", "ISSUED FOR DESIGN", "REVISED PER CLIENT COMMENTS",
                  "ISSUED FOR APPROVAL", "ISSUED FOR CONSTRUCTION")
TITLES = {
    "ISO": "PIPING ISOMETRIC",
    "PID": "PIPING AND INSTRUMENTATION DIAGRAM",
    "GA": "GENERAL ARRANGEMENT - PLAN",
    "SPEC": "PIPING MATERIAL AND WELDING SPECIFICATION",
    "OTHER": "STANDARD SYMBOLS AND LEGEND",
}
AREAS = ("TRAIN 3", "TRAIN 4", "TANK T-203", "TANK T-204", "JETTY 2", "PIPE RACK NORTH", "PIPE RACK SOUTH",
         "UTILITIES BLOCK", "MAIN SUBSTATION", "FLARE AND VENT")
SERVICES = (("LNG", "LIQUEFIED NATURAL GAS"), ("BOG", "BOIL-OFF GAS"), ("MR", "MIXED REFRIGERANT"),
            ("NG", "FEED GAS"), ("FG", "FUEL GAS"), ("N2", "NITROGEN"))
BUILDINGS = ("COMPRESSOR BUILDING", "PUMP HOUSE", "CONTROL BUILDING", "ELECTRICAL SUBSTATION", "UTILITY BUILDING")

# ASME B16.5 pressure-temperature ratings, stainless steel group 2.1, at 100 F (psig).
CLASSES = (150, 300, 600, 900, 1500)
RATING_PSIG = {150: 275, 300: 720, 600: 1440, 900: 2160, 1500: 3600}
CLASS_CODE = {150: "A1S", 300: "B3S", 600: "C6S", 900: "D9S", 1500: "E15S"}
CLASS_SERVICE = {150: "BOG, FUEL GAS, N2", 300: "LNG, LOW-PRESSURE REFRIGERANT", 600: "MEDIUM-PRESSURE REFRIGERANT",
                 900: "HIGH-PRESSURE REFRIGERANT", 1500: "COMPRESSOR DISCHARGE"}

# --------------------------------------------------------------------------------------------------
# Page geometry (PDF points, origin bottom-left). ANSI B, 17 x 11 in, landscape.
# --------------------------------------------------------------------------------------------------

PAGE_W, PAGE_H = 1224.0, 792.0
MARGIN = 18.0
COL_X0, COL_X1 = 826.0, 1202.0  # right-hand column: notes, rating reference, revision table, title block
REG, BOLD = "Helvetica", "Helvetica-Bold"
BBOX_PAD = 3.0  # points of breathing room added around a recorded element
AS_OF = date(2026, 11, 6)  # the project data is anchored here; revision dates all fall before it


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    def union(self, o: "Box") -> "Box":
        return Box(min(self.x0, o.x0), min(self.y0, o.y0), max(self.x1, o.x1), max(self.y1, o.y1))

    def pad(self, p: float) -> "Box":
        return Box(self.x0 - p, self.y0 - p, self.x1 + p, self.y1 + p)

    def intersects(self, o: "Box") -> bool:
        return self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1

    def contains(self, o: "Box") -> bool:
        return self.x0 <= o.x0 and self.y0 <= o.y0 and o.x1 <= self.x1 and o.y1 <= self.y1

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0


def normalise_bbox(box: Box) -> list[float]:
    """PDF-space box -> [x, y, w, h] in 0..1 of the page, origin top-left, y downwards."""
    x0, x1 = max(0.0, box.x0 - BBOX_PAD), min(PAGE_W, box.x1 + BBOX_PAD)
    y0, y1 = max(0.0, box.y0 - BBOX_PAD), min(PAGE_H, box.y1 + BBOX_PAD)
    x, y = round(x0 / PAGE_W, 4), round((PAGE_H - y1) / PAGE_H, 4)
    w, h = round((x1 - x0) / PAGE_W, 4), round((y1 - y0) / PAGE_H, 4)
    return [x, y, min(w, round(1.0 - x, 4)), min(h, round(1.0 - y, 4))]


class _Tracker:
    """Collects the union of every primitive drawn while it is active."""

    def __init__(self):
        self.box: Box | None = None

    def add(self, b: Box):
        self.box = b if self.box is None else self.box.union(b)


class Sheet:
    """One ReportLab page plus the bookkeeping that turns drawn primitives into bounding boxes.

    Every drawing call returns the Box it covered and reports it to the active trackers, so a flaw's bbox
    is, by construction, the union of what was drawn for the offending element:

        with sheet.track() as t:
            draw_the_element(...)
        bbox = t.box
    """

    def __init__(self, c: canvas.Canvas, rng: random.Random, np_rng: np.random.Generator):
        self.c, self.rng, self.np = c, rng, np_rng
        self._trackers: list[_Tracker] = []

    # --- bookkeeping
    @contextmanager
    def track(self):
        t = _Tracker()
        self._trackers.append(t)
        try:
            yield t
        finally:
            self._trackers.remove(t)

    def reserve(self, box: Box) -> Box:
        """Count an empty region (the slot where a missing tag belongs) towards the boxes being tracked."""
        return self._note(box)

    def _note(self, box: Box) -> Box:
        for t in self._trackers:
            t.add(box)
        return box

    # --- primitives
    def _stroke(self, lw, dash=None, gray=0.0):
        self.c.setLineWidth(lw)
        self.c.setStrokeGray(gray)
        self.c.setDash(dash if dash else [])

    def line(self, x0, y0, x1, y1, lw=0.8, dash=None, gray=0.0) -> Box:
        self._stroke(lw, dash, gray)
        self.c.line(x0, y0, x1, y1)
        h = lw / 2
        return self._note(Box(min(x0, x1) - h, min(y0, y1) - h, max(x0, x1) + h, max(y0, y1) + h))

    def rect(self, x, y, w, h, lw=0.8, fill=None, radius=0.0, stroke=True, dash=None, gray=0.0) -> Box:
        self._stroke(lw, dash, gray)
        if fill is not None:
            self.c.setFillGray(fill)
        flags = dict(stroke=1 if stroke else 0, fill=0 if fill is None else 1)
        if radius:
            self.c.roundRect(x, y, w, h, radius, **flags)
        else:
            self.c.rect(x, y, w, h, **flags)
        self.c.setFillGray(0)
        return self._note(Box(x, y, x + w, y + h))

    def circle(self, cx, cy, r, lw=0.8, fill=None) -> Box:
        self._stroke(lw)
        if fill is not None:
            self.c.setFillGray(fill)
        self.c.circle(cx, cy, r, stroke=1, fill=0 if fill is None else 1)
        self.c.setFillGray(0)
        return self._note(Box(cx - r, cy - r, cx + r, cy + r))

    def poly(self, pts, close=False, lw=0.8, fill=None, dash=None) -> Box:
        self._stroke(lw, dash)
        if fill is not None:
            self.c.setFillGray(fill)
        p = self.c.beginPath()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        if close:
            p.close()
        self.c.drawPath(p, stroke=1, fill=0 if fill is None else 1)
        self.c.setFillGray(0)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        h = lw / 2
        return self._note(Box(min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h))

    def arc(self, cx, cy, r, start, extent, lw=0.8) -> Box:
        self._stroke(lw)
        self.c.arc(cx - r, cy - r, cx + r, cy + r, start, extent)
        pts = [(cx + r * math.cos(math.radians(start + extent * i / 6)),
                cy + r * math.sin(math.radians(start + extent * i / 6))) for i in range(7)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        return self._note(Box(min(xs), min(ys), max(xs), max(ys)))

    def text(self, x, y, s, size=7.0, bold=False, anchor="l", gray=0.0) -> Box:
        font = BOLD if bold else REG
        w = stringWidth(s, font, size)
        x0 = x - w / 2 if anchor == "c" else x - w if anchor == "r" else x
        self.c.setFillGray(gray)
        self.c.setFont(font, size)
        self.c.drawString(x0, y, s)
        self.c.setFillGray(0)
        return self._note(Box(x0, y - 0.22 * size, x0 + w, y + 0.74 * size))

    # --- compound helpers
    def numbered(self, x, y_top, width, items, size=7.2, leading=9.0) -> float:
        """Numbered, wrapped notes. Returns the y just below the last line."""
        y = y_top
        for i, item in enumerate(items, 1):
            for j, ln in enumerate(simpleSplit(item, REG, size, width - 12)):
                y -= leading
                if j == 0:
                    self.text(x, y, f"{i}.", size, bold=True)
                self.text(x + 12, y, ln, size)
            y -= 2.5
        return y

    def bullets(self, x, y_top, items, size=7.2, leading=9.0) -> float:
        y = y_top
        for item in items:
            y -= leading
            self.text(x, y, "- " + item, size)
        return y

    def table(self, x, y_top, widths, rows, header=None, size=7.0, row_h=11.5, hdr_h=None) -> list[Box]:
        """Ruled table. Returns the Box of every data row (header excluded), top to bottom."""
        hdr_h = hdr_h or row_h
        total = sum(widths)
        y, boxes = y_top, []

        def draw_row(cells, h, bold, shade):
            nonlocal y
            xx = x
            for cell, w in zip(cells, widths):
                self.rect(xx, y - h, w, h, lw=0.5, fill=0.88 if shade else None)
                if cell:
                    s = size
                    while stringWidth(cell, BOLD if bold else REG, s) > w - 4 and s > 5.0:
                        s -= 0.2
                    self.text(xx + 2.5, y - h + (h - 0.72 * s) / 2, cell, s, bold=bold)
                xx += w
            y -= h

        if header:
            draw_row(header, hdr_h, True, True)
        for cells in rows:
            top = y
            draw_row(cells, row_h, False, False)
            boxes.append(Box(x, top - row_h, x + total, top))
        return boxes


class LabelPlacer:
    """Puts callout labels next to an anchor point without overlapping earlier labels or the pipe route."""

    ANGLES = (50, 130, 20, 160, 90, -50, -130, -20, -160, -90, 0, 180)

    def __init__(self, sh: Sheet, region: Box, route=()):
        self.sh, self.region, self.route, self.boxes = sh, region, list(route), []

    def _hits_route(self, box: Box) -> bool:
        b = box.pad(1.5)
        for (x0, y0), (x1, y1) in zip(self.route, self.route[1:]):
            steps = max(2, int(math.hypot(x1 - x0, y1 - y0) / 3))
            for i in range(steps + 1):
                px, py = x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps
                if b.x0 <= px <= b.x1 and b.y0 <= py <= b.y1:
                    return True
        return False

    def place(self, anchor, s, size=7.0, bold=False, leader=True, dists=(16, 28, 40, 54), required=True):
        ax, ay = anchor
        w = stringWidth(s, BOLD if bold else REG, size)
        first = None
        for d in dists:
            for ang in self.ANGLES:
                dx, dy = d * math.cos(math.radians(ang)), d * math.sin(math.radians(ang))
                mode = "l" if dx > 4 else "r" if dx < -4 else "c"
                x0 = ax + dx if mode == "l" else ax + dx - w if mode == "r" else ax + dx - w / 2
                ty = ay + dy - 0.3 * size
                box = Box(x0, ty - 0.22 * size, x0 + w, ty + 0.74 * size)
                first = first or (box, ax + dx, ty, mode)
                if (self.region.contains(box) and not any(box.pad(1.5).intersects(o) for o in self.boxes)
                        and not self._hits_route(box)):
                    return self._commit(anchor, box, ax + dx, ty, mode, s, size, bold, leader)
        if not required:
            return None
        box, tx, ty, mode = first  # nothing was free: take the first candidate and shift it inside the region
        shift = max(0.0, self.region.x0 - box.x0) - max(0.0, box.x1 - self.region.x1)
        box = Box(box.x0 + shift, box.y0, box.x1 + shift, box.y1)
        return self._commit(anchor, box, tx + shift, ty, mode, s, size, bold, leader)

    def _commit(self, anchor, box, tx, ty, mode, s, size, bold, leader):
        if leader:
            lx = min(max(anchor[0], box.x0), box.x1)
            ly = min(max(anchor[1], box.y0), box.y1)
            self.sh.line(anchor[0], anchor[1], lx, ly, lw=0.45)
        self.sh.text(tx, ty, s, size, bold=bold, anchor=mode)
        self.boxes.append(box)
        return box


# --------------------------------------------------------------------------------------------------
# Symbols
# --------------------------------------------------------------------------------------------------

def _frame(ang):
    a = math.radians(ang)
    return (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))


def sym_bowtie(sh, cx, cy, ang=0.0, half_len=9.0, half_w=5.0, lw=0.9):
    """Valve body: two triangles meeting at a point, axis along `ang` degrees."""
    (ux, uy), (vx, vy) = _frame(ang)

    def p(u, v):
        return (cx + u * ux + v * vx, cy + u * uy + v * vy)

    sh.poly([p(-half_len, -half_w), p(0, 0), p(-half_len, half_w)], close=True, lw=lw, fill=1.0)
    sh.poly([p(half_len, -half_w), p(0, 0), p(half_len, half_w)], close=True, lw=lw, fill=1.0)


def sym_flange(sh, cx, cy, ang=0.0, half=6.5, gap=2.2):
    """Flanged joint: two short ticks across the pipe."""
    (ux, uy), (vx, vy) = _frame(ang)
    for s in (-gap, gap):
        sh.line(cx + s * ux - half * vx, cy + s * uy - half * vy, cx + s * ux + half * vx, cy + s * uy + half * vy, lw=1.1)


def sym_loto(sh, x, y, label):
    """LOTO energy-isolation tag: a small tag shape with its tag number. (x, y) is the lower-left corner."""
    w = stringWidth(label, BOLD, 6.3) + 14
    sh.rect(x, y, w, 11, lw=0.9, fill=1.0, radius=2.5)
    sh.circle(x + 5.5, y + 5.5, 1.7, lw=0.6)
    sh.text(x + 10, y + 3.3, label, 6.3, bold=True)
    return Box(x, y, x + w, y + 11)


def sym_instrument(sh, cx, cy, top, bottom, r=10.0):
    sh.circle(cx, cy, r, lw=0.9, fill=1.0)
    sh.line(cx - r, cy, cx + r, cy, lw=0.6)
    sh.text(cx, cy + 2.2, top, 5.8, bold=True, anchor="c")
    sh.text(cx, cy - 6.6, bottom, 5.8, anchor="c")


def sym_psv(sh, cx, cy):
    """Pressure safety valve: vertical bow-tie, spring above, outlet to the right."""
    sym_bowtie(sh, cx, cy, ang=90, half_len=8, half_w=5)
    sh.line(cx + 5, cy, cx + 16, cy, lw=0.9)
    sh.poly([(cx, cy + 8), (cx - 3, cy + 11), (cx + 3, cy + 14), (cx - 3, cy + 17), (cx + 3, cy + 20), (cx, cy + 23)], lw=0.8)


def sym_pump(sh, cx, cy, r=14.0):
    sh.circle(cx, cy, r, lw=1.1, fill=1.0)
    sh.poly([(cx - 6, cy - 7), (cx + 8, cy), (cx - 6, cy + 7)], close=True, lw=0.8)
    sh.line(cx, cy + r, cx, cy + r + 8, lw=1.0)
    sh.rect(cx - 10, cy + r + 8, 20, 14, lw=1.0, fill=1.0)
    sh.text(cx, cy + r + 12.5, "M", 7.5, bold=True, anchor="c")


def sym_compressor(sh, cx, cy):
    sh.poly([(cx - 28, cy - 12), (cx + 28, cy - 20), (cx + 28, cy + 20), (cx - 28, cy + 12)], close=True, lw=1.1, fill=1.0)
    sh.line(cx, cy + 16, cx, cy + 24, lw=1.0)
    sh.rect(cx - 10, cy + 24, 20, 14, lw=1.0, fill=1.0)
    sh.text(cx, cy + 28.5, "M", 7.5, bold=True, anchor="c")


def sym_vessel(sh, cx, cy, w=44.0, h=110.0):
    sh.rect(cx - w / 2, cy - h / 2, w, h, lw=1.2, fill=1.0, radius=w / 2 - 2)


def sym_door(sh, wall, x, y, width):
    """Door in a wall: clears the wall, then draws the leaf and its swing. (x, y) is the hinge point."""
    gap = {"L": (x - 3, y, 6, width), "R": (x - 3, y, 6, width), "B": (x, y - 3, width, 6), "T": (x, y - 3, width, 6)}[wall]
    sh.rect(*gap, lw=0, fill=1.0, stroke=False)
    leaf = {"L": (x - width, y), "R": (x + width, y), "B": (x, y - width), "T": (x, y + width)}[wall]
    sh.line(x, y, *leaf, lw=1.0)
    start = {"L": 90, "R": 0, "B": 270, "T": 0}[wall]
    sh.arc(x, y, width, start, 90, lw=0.5)


# --------------------------------------------------------------------------------------------------
# Helpers for the drawing content
# --------------------------------------------------------------------------------------------------

_FAKE: Faker | None = None


def _person(rng) -> str:
    global _FAKE
    if _FAKE is None:
        _FAKE = Faker("en_US")
    _FAKE.seed_instance(rng.randrange(2 ** 31))
    return f"{_FAKE.first_name()[0]}. {_FAKE.last_name()}".upper()


def _initials(name: str) -> str:
    return name[0] + name[3]


def _choice(rng, weights: dict):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def design_pressure(rng, cls: int) -> int:
    """A design pressure that needs flange class `cls`: above the next class down, below `cls`'s own rating."""
    below = [c for c in CLASSES if c < cls]
    lo = 1.05 * RATING_PSIG[below[-1]] if below else 50.0
    hi = 0.92 * RATING_PSIG[cls]
    return int(round(rng.uniform(lo, hi) / 5.0) * 5)


def under_rated(rng, cls: int) -> int:
    """A flange class one or two steps below `cls`: too weak for a pressure `design_pressure` produced for `cls`."""
    return rng.choice([c for c in CLASSES if c < cls][-2:])


def ft_in(inches: int) -> str:
    return f"{inches // 12}'-{inches % 12}\""


def rating_reference(sh, y_top):
    """Small flange class -> max pressure table used by every sheet that shows flanges."""
    x = COL_X0 + 6
    sh.text(x, y_top - 9, "FLANGE RATING REFERENCE", 8, bold=True)
    sh.text(x, y_top - 18, "ASME B16.5, SS GROUP 2.1, AT 100 F", 6.4)
    sh.table(x, y_top - 22, [90, 120], [[f"CLASS {c}", f"{RATING_PSIG[c]} PSIG"] for c in CLASSES],
             header=["FLANGE CLASS", "MAX ALLOWABLE PRESSURE"], size=6.6, row_h=10.5)


def notes_column(sh, notes, refs, rating=True):
    x, width = COL_X0 + 6, COL_X1 - COL_X0 - 12
    sh.text(x, 757, "GENERAL NOTES", 9, bold=True)
    y = sh.numbered(x, 753, width, notes)
    sh.text(x, y - 12, "REFERENCE CODES AND STANDARDS", 9, bold=True)
    sh.bullets(x, y - 16, refs)
    if rating:
        rating_reference(sh, 346)


# --------------------------------------------------------------------------------------------------
# Sheet drawers. Each takes (sheet, meta, plants) and returns [(flaw_type, Box), ...] for what it planted.
# --------------------------------------------------------------------------------------------------

ISO_AXES = {"+x": (math.cos(math.radians(30)), math.sin(math.radians(30))),
            "-x": (-math.cos(math.radians(30)), -math.sin(math.radians(30))),
            "+y": (-math.cos(math.radians(30)), math.sin(math.radians(30))),
            "-y": (math.cos(math.radians(30)), -math.sin(math.radians(30))),
            "+z": (0.0, 1.0), "-z": (0.0, -1.0)}


def _iso_route(rng, np_rng, region: Box):
    """A random pipe run along the three isometric axes, scaled to fill `region`."""
    moves, prev, wanted = [], None, rng.randint(4, 6)
    while len(moves) < wanted:
        axis = rng.choice("xyz")
        if axis != prev:
            moves.append(rng.choice("+-") + axis)
            prev = axis
    pts = [(0.0, 0.0)]
    for m in moves:
        length = float(np_rng.uniform(55, 135))
        pts.append((pts[-1][0] + ISO_AXES[m][0] * length, pts[-1][1] + ISO_AXES[m][1] * length))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bw, bh = max(max(xs) - min(xs), 1.0), max(max(ys) - min(ys), 1.0)
    s = min(region.w / bw, region.h / bh, 1.9)
    ox = region.x0 + (region.w - bw * s) / 2 - min(xs) * s
    oy = region.y0 + (region.h - bh * s) / 2 - min(ys) * s
    return [(ox + x * s, oy + y * s) for x, y in pts]


def draw_iso(sh: Sheet, meta, plants):
    rng, np_rng, planted = sh.rng, sh.np, []
    cls = rng.choices((300, 600, 900), weights=(0.45, 0.35, 0.20))[0]
    dp, nps = design_pressure(rng, cls), rng.choice((4, 6, 8, 10, 12))
    svc = rng.choice(SERVICES)
    tag = f'{nps}"-{svc[0]}-{rng.randrange(1001, 1999)}-{CLASS_CODE[cls]}'
    material = "A312 TP304L" if cls < 600 else "A312 TP316L"
    meta["subtitle"] = f"LINE {tag} - {meta['area']}"

    sh.table(30, 760, [150, 62, 40, 66, 116, 100, 130, 120],
             [[tag, svc[0], str(nps), CLASS_CODE[cls], material, f"{dp} PSIG", "-270 / 140 F", f"CL{cls} RF"]],
             header=["LINE NO.", "SERVICE", "NPS", "CLASS", "MATERIAL", "DESIGN PRESS", "DESIGN TEMP", "FLANGE CLASS"],
             size=7.4, row_h=15, hdr_h=12)

    region = Box(60, 215, 745, 715)
    pts = _iso_route(rng, np_rng, region)
    segs = list(zip(pts, pts[1:]))
    dirs = []
    for (x0, y0), (x1, y1) in segs:
        d = math.hypot(x1 - x0, y1 - y0)
        dirs.append(((x1 - x0) / d, (y1 - y0) / d))
    sh.poly(pts, lw=2.0)
    placer = LabelPlacer(sh, region, route=pts)

    def at(p, d, t):
        return (p[0] + d[0] * t, p[1] + d[1] * t)

    def angle(d):
        return math.degrees(math.atan2(d[1], d[0]))

    # flow arrow on the first run
    ax, ay = at(pts[0], dirs[0], min(38.0, 0.5 * math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])))
    nx, ny = -dirs[0][1], dirs[0][0]
    sh.poly([at((ax, ay), dirs[0], 6), (ax - dirs[0][0] * 3 + nx * 3.5, ay - dirs[0][1] * 3 + ny * 3.5),
             (ax - dirs[0][0] * 3 - nx * 3.5, ay - dirs[0][1] * 3 - ny * 3.5)], close=True, lw=0.6, fill=0.0)

    # flanges: one at each end, and a pair round a valve on the longest straight run
    flanges = [(at(pts[0], dirs[0], 7), angle(dirs[0])), (at(pts[-1], dirs[-1], -7), angle(dirs[-1]))]
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    j = max(range(len(segs)), key=lambda k: lengths[k])
    valve = lengths[j] >= 85
    if valve:
        mid = ((segs[j][0][0] + segs[j][1][0]) / 2, (segs[j][0][1] + segs[j][1][1]) / 2)
        sym_bowtie(sh, mid[0], mid[1], angle(dirs[j]), half_len=9, half_w=5.5)
        placer.boxes.append(Box(mid[0] - 10, mid[1] - 10, mid[0] + 10, mid[1] + 10))
        flanges += [(at(mid, dirs[j], -15), angle(dirs[j])), (at(mid, dirs[j], 15), angle(dirs[j]))]
    bad_flange = rng.randrange(len(flanges)) if "flange_rating_mismatch" in plants else -1
    shown_bad = under_rated(rng, cls)
    for i, (p, ang) in enumerate(flanges):
        with sh.track() as t:
            sym_flange(sh, p[0], p[1], ang)
            placer.place(p, f'FLG {nps}" CL{shown_bad if i == bad_flange else cls} RF WN', size=7.0)
        if i == bad_flange:
            planted.append(("flange_rating_mismatch", t.box))

    # welds: one on the run into every elbow
    welds = []
    for i in range(1, len(pts) - 1):
        welds.append({"at": at(pts[i], dirs[i - 1], -11), "type": "BW", "exam": "RT 100%", "where": rng.choice("SF")})
    bad_weld = rng.randrange(len(welds)) if "weld_joint_spec_mismatch" in plants else -1
    if bad_weld >= 0:
        welds[bad_weld]["type"], welds[bad_weld]["exam"] = rng.choice((("FW", "VT"), ("SW", "MT 5%"), ("BW", "NONE")))
    for i, wd in enumerate(welds):
        with sh.track() as t:
            sh.circle(wd["at"][0], wd["at"][1], 2.6, fill=0.0)
            placer.place(wd["at"], f"W{i + 1} {wd['type']} {wd['exam']}", size=6.8)
        if i == bad_weld:
            planted.append(("weld_joint_spec_mismatch", t.box))

    # tie-ins and dimensions (decoration; dimensions are skipped where there is no clear space)
    placer.place(pts[0], f"FROM {rng.choice('VPK')}-{rng.randrange(1001, 1099)} NOZZLE N{rng.randint(1, 4)}", size=6.8, bold=True)
    placer.place(pts[-1], f"TO {rng.choice('VPKE')}-{rng.randrange(1101, 1199)} NOZZLE N{rng.randint(1, 4)}", size=6.8, bold=True)
    for a, b in segs:
        placer.place(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), ft_in(rng.randrange(30, 190)), size=6.5,
                     leader=False, dists=(8, 14, 22), required=False)
    sh.text(770, 697, "N", 8, bold=True, anchor="c")
    sh.poly([(770, 668), (765, 680), (775, 680)], close=True, lw=0.6, fill=0.0)
    sh.line(770, 668, 770, 690, lw=0.8)

    # bill of materials and weld table
    n_fl = len(flanges)
    bom = [[str(k), q, d] for k, (q, d) in enumerate([
        (f"{rng.randrange(12, 60)} FT", f'PIPE {nps}" SCH 40S SMLS, {material}'),
        (str(len(pts) - 2), f'ELBOW 90 DEG LR {nps}" BW, A403 WP{material[-4:]}'),
        (str(n_fl), f'FLANGE WN {nps}" CL{cls} RF, A182 F{material[-4:]}'),
        (str(n_fl // 2), f'GASKET SPIRAL WOUND {nps}" CL{cls}'),
    ] + ([("1", f'GATE VALVE {nps}" CL{cls} FLG, BODY CF3M')] if valve else []), 1)]
    sh.text(30, 196, "BILL OF MATERIALS", 8, bold=True)
    sh.table(30, 190, [34, 44, 322], bom, header=["ITEM", "QTY", "DESCRIPTION"], size=7.0, row_h=11.5)
    sh.text(440, 196, "WELD TABLE", 8, bold=True)
    sh.table(440, 190, [52, 52, 44, 130, 96],
             [[f"W{i + 1}", w["type"], str(nps), w["exam"], "FIELD" if w["where"] == "F" else "SHOP"] for i, w in enumerate(welds)],
             header=["WELD NO.", "TYPE", "NPS", "EXAMINATION", "SHOP / FIELD"], size=7.0, row_h=11.5)

    notes_column(sh, [
        "ALL DIMENSIONS ARE IN FEET AND INCHES. ISOMETRIC IS NOT TO SCALE.",
        "PIPING CLASS, MATERIAL AND DESIGN CONDITIONS ARE AS SHOWN IN THE LINE DATA TABLE.",
        f"FLANGES PER ASME B16.5. FLANGE CLASS SHALL BE RATED FOR THE DESIGN PRESSURE (SEE FLANGE RATING REFERENCE): CL{cls} FOR THIS LINE.",
        f"WELDING AND EXAMINATION PER ASME B31.3 PARA. 341. CLASS {CLASS_CODE[cls]} IS COLD SERVICE: FULL-PENETRATION BUTT WELDS (BW) WITH 100% RT. SOCKET AND FILLET WELDS ARE NOT PERMITTED.",
        "WELDS ARE IDENTIFIED IN THE WELD TABLE AS SHOP OR FIELD. NOZZLE ORIENTATIONS PER EQUIPMENT DRAWINGS.",
        "PIPE SUPPORTS ARE BY OTHERS. SUPPORT LOCATIONS PER STRESS ANALYSIS.",
    ], ["ASME B31.3 PROCESS PIPING", "ASME B16.5 PIPE FLANGES AND FLANGED FITTINGS", "ASME B16.9 FACTORY-MADE BUTT-WELDING FITTINGS"])
    return planted


PID_LINES = (575, 335)  # y of the two process trains


def draw_pid(sh: Sheet, meta, plants):
    rng, planted = sh.rng, []
    sh.text(40, 744, f"PROCESS FLOW AND INSTRUMENTATION - {meta['area']}", 11, bold=True)
    meta["subtitle"] = f"{meta['area']} - PROCESS UNIT"
    base = rng.randrange(2100, 2900, 100)

    # --- model: equipment on two trains, one line definition per train
    items = []
    for train, y in enumerate(PID_LINES):
        m = rng.choice((3, 3, 4)) if train == 0 else 3
        for i in range(m):
            items.append({"train": train, "x": 150 + (i + 0.5) * 600 / m, "y": y,
                          "kind": rng.choices("VPK", weights=(0.34, 0.40, 0.26))[0]})
    if not any(it["kind"] == "V" for it in items):
        rng.choice(items)["kind"] = "V"
    if not any(it["kind"] in "PK" for it in items):
        rng.choice(items)["kind"] = "P"
    half = {"V": 22.0, "P": 14.0, "K": 28.0}
    desc = {"V": ("KNOCKOUT DRUM", "SUCTION DRUM", "SEPARATOR", "SURGE DRUM"),
            "P": ("LNG TRANSFER PUMP", "REFLUX PUMP", "BOOSTER PUMP"), "K": ("BOG COMPRESSOR", "REFRIGERANT COMPRESSOR")}
    lines = []
    for train in range(len(PID_LINES)):
        cls = rng.choices((300, 600, 900), weights=(0.5, 0.35, 0.15))[0]
        svc = rng.choice(SERVICES)
        dp = design_pressure(rng, cls)
        nps = rng.choice((4, 6, 8, 10, 12, 16))
        lines.append({"cls": cls, "dp": dp, "svc": svc, "tag": f'{nps}"-{svc[0]}-{base + 50 + train}-{CLASS_CODE[cls]}'})
    for n, it in enumerate(items, 1):
        ln = lines[it["train"]]
        it["tag"] = f"{it['kind']}-{base + n}" + ("A" if it["kind"] == "P" else "")
        it["desc"], it["dp"] = rng.choice(desc[it["kind"]]), ln["dp"]
        it["psv"] = f"PSV-{base + n}"

    segs = []
    for train in range(len(PID_LINES)):
        row = [it for it in items if it["train"] == train]
        for a, b in zip(row, row[1:]):
            segs.append({"train": train, "x0": a["x"] + half[a["kind"]], "x1": b["x"] - half[b["kind"]], "y": a["y"], "first": a is row[0]})

    vessels = [it for it in items if it["kind"] == "V"]
    rotating = [it for it in items if it["kind"] in "PK"]
    bad_psv = rng.choice(vessels) if "missing_pressure_relief_notation" in plants else None
    bad_loto = rng.choice(rotating) if "missing_loto_tag" in plants else None
    bad_seg = rng.choice(segs) if "flange_rating_mismatch" in plants else None
    shown_bad = under_rated(rng, lines[bad_seg["train"]]["cls"]) if bad_seg else None

    # --- pipes first, so the equipment (white-filled) sits on top of them
    for y in PID_LINES:
        sh.line(40, y, 800, y, lw=1.5)
        sh.poly([(800, y), (792, y + 3.5), (792, y - 3.5)], close=True, lw=0.5, fill=0.0)
        sh.text(44, y + 7, f"FROM {rng.choice(('LNG RUNDOWN HEADER', 'FEED GAS HEADER', 'REFRIGERANT HEADER', 'BOG HEADER'))}", 6.6, bold=True)
        sh.text(796, y + 7, f"TO {rng.choice(('STORAGE TANK', 'FLARE HEADER', 'NEXT UNIT', 'LOADING LINE'))}", 6.6, bold=True, anchor="r")

    # --- equipment
    for it in items:
        cx, y = it["x"], it["y"]
        with sh.track() as t:
            if it["kind"] == "V":
                sym_vessel(sh, cx, y)
                sh.text(cx, y - 67, it["tag"], 8, bold=True, anchor="c")
                sh.text(cx, y - 77, it["desc"], 6.4, anchor="c")
                sh.text(cx, y - 86, f"DP {it['dp']} PSIG / -270 TO 140 F", 6.2, anchor="c")
                sh.line(cx, y + 55, cx, y + 64, lw=1.0)
                if it is bad_psv:
                    sh.reserve(Box(cx - 8, y + 55, cx + 72, y + 95))  # the PSV and its labels belong here
                else:
                    sym_psv(sh, cx, y + 72)
                    sh.text(cx + 10, y + 88, it["psv"], 6.4, bold=True)
                    sh.text(cx + 10, y + 79, f"SET {it['dp']} PSIG", 6.2)
            else:
                if it["kind"] == "P":
                    sym_pump(sh, cx, y)
                else:
                    sym_compressor(sh, cx, y)
                dy = 14 if it["kind"] == "P" else 20
                sh.text(cx, y - dy - 12, it["tag"], 8, bold=True, anchor="c")
                sh.text(cx, y - dy - 22, it["desc"], 6.4, anchor="c")
                slot = Box(cx + 16, y + (28 if it["kind"] == "P" else 26), cx + 70, y + (40 if it["kind"] == "P" else 38))
                if it is bad_loto:
                    sh.reserve(slot)
                else:
                    sym_loto(sh, slot.x0, slot.y0, f"LOTO-{it['tag'][2:]}")
        if it is bad_psv:
            planted.append(("missing_pressure_relief_notation", t.box))
        if it is bad_loto:
            planted.append(("missing_loto_tag", t.box))

    # --- in-line items on every segment between two machines
    for k, sg in enumerate(segs):
        ln, y, L = lines[sg["train"]], sg["y"], sg["x1"] - sg["x0"]
        xf, xv, xc = sg["x0"] + 0.22 * L, sg["x0"] + 0.68 * L, sg["x0"] + 0.5 * L
        with sh.track() as t:
            sym_flange(sh, xf, y, 0.0)
            sh.text(xf, y + 11, f"FLG CL{shown_bad if sg is bad_seg else ln['cls']}", 6.6, bold=True, anchor="c")
        if sg is bad_seg:
            planted.append(("flange_rating_mismatch", t.box))
        sh.text(xc, y - 15, ln["tag"], 7, bold=True, anchor="c")
        sh.text(xc, y - 24, f"DP {ln['dp']} PSIG", 6.3, anchor="c")
        sym_bowtie(sh, xv, y, 0.0)
        if sg["first"]:  # control loop on the first segment of each train
            sh.circle(xv, y + 9, 5, lw=0.8, fill=1.0)
            sh.line(xv, y + 5.5, xv, y + 4, lw=0.8)
            sym_instrument(sh, xv, y + 44, "FIC", str(base + 60 + sg["train"]))
            sh.line(xv, y + 34, xv, y + 14, lw=0.6, dash=[2, 2])
        else:
            sh.text(xv, y + 11, f"HV-{base + 70 + k}", 6.4, anchor="c")

    # --- legend and equipment list
    sh.text(30, 148, "LEGEND", 8, bold=True)
    sh.rect(30, 30, 390, 112, lw=0.6)
    sym_bowtie(sh, 48, 126, 0.0)
    sh.text(66, 123.5, "HV   MANUAL VALVE", 6.6)
    sym_bowtie(sh, 48, 100, 0.0)
    sh.circle(48, 109, 4, lw=0.7, fill=1.0)
    sh.text(66, 97.5, "FV   CONTROL VALVE", 6.6)
    sym_instrument(sh, 48, 74, "PT", "101", r=8)
    sh.text(66, 71.5, "INSTRUMENT, TAGS PER ISA 5.1", 6.6)
    sym_flange(sh, 48, 48, 0.0)
    sh.text(66, 45.5, "FLG   FLANGED JOINT", 6.6)
    sym_psv(sh, 235, 108)
    sh.text(258, 105.5, "PSV   PRESSURE SAFETY VALVE", 6.6)
    sym_loto(sh, 222, 74, "LOTO-0000")
    sh.text(284, 77.5, "LOTO   ENERGY ISOLATION TAG", 6.6)
    sh.text(222, 45.5, "DP   DESIGN PRESSURE (PSIG)", 6.6)
    sh.text(40, 35, "SEE NOTES FOR LINE CLASS CODES", 6.2)
    sh.text(430, 148, "EQUIPMENT LIST", 8, bold=True)
    sh.table(430, 142, [62, 150, 70, 102], [[it["tag"], it["desc"], str(it["dp"]), "-270 / 140"] for it in items[:8]],
             header=["TAG", "DESCRIPTION", "DP (PSIG)", "TEMP (F)"], size=6.6, row_h=11)

    notes_column(sh, [
        "THIS DRAWING IS A SCHEMATIC. MATERIALS AND DETAILS ARE IN THE PIPING CLASS SPECIFICATION.",
        "LINE TAG FORMAT IS NPS-SERVICE-NUMBER-CLASS. CLASS CODES: A1S = CL150, B3S = CL300, C6S = CL600, D9S = CL900, E15S = CL1500.",
        "THE FLANGE CLASS AT EVERY FLANGED JOINT SHALL BE RATED FOR THE LINE DESIGN PRESSURE (ASME B16.5); SEE FLANGE RATING REFERENCE.",
        "EVERY PRESSURE VESSEL SHALL BE PROTECTED BY A PRESSURE RELIEF DEVICE (PSV). ITS TAG AND SET PRESSURE ARE SHOWN ON THE VESSEL (ASME B31.3 PARA. 322).",
        "EVERY PUMP AND COMPRESSOR SHALL CARRY A LOTO ENERGY ISOLATION TAG AT ITS MOTOR (OSHA 29 CFR 1910.147).",
        "INSTRUMENT TAGS PER ISA 5.1. CONTROL LOOP DETAILS ARE ON THE LOOP DIAGRAMS.",
    ], ["ASME B31.3 PROCESS PIPING", "ASME B16.5 PIPE FLANGES AND FLANGED FITTINGS", "OSHA 29 CFR 1910.147 LOCKOUT/TAGOUT", "ISA 5.1 INSTRUMENTATION SYMBOLS"])
    return planted


GA_DOORS = (("L", 335), ("L", 465), ("R", 335), ("R", 465), ("B", 210), ("B", 357), ("B", 502),
            ("T", 210), ("T", 357), ("T", 502))
BX0, BX1, BY0, BY1 = 140.0, 720.0, 270.0, 660.0  # building footprint on the GA plan (6 pt per foot)


def draw_ga(sh: Sheet, meta, plants):
    rng, np_rng, planted = sh.rng, sh.np, []
    building = rng.choice(BUILDINGS)
    meta["subtitle"] = f"{building} - {meta['area']}"
    gx, gy = [BX0 + 145 * i for i in range(5)], [BY0 + 130 * j for j in range(4)]
    for i, x in enumerate(gx):
        sh.line(x, 252, x, 678, lw=0.4, dash=[8, 3, 2, 3], gray=0.5)
        sh.circle(x, 690, 8, lw=0.7)
        sh.text(x, 687, "ABCDE"[i], 8, bold=True, anchor="c")
    for j, y in enumerate(gy):
        sh.line(122, y, 738, y, lw=0.4, dash=[8, 3, 2, 3], gray=0.5)
        sh.circle(112, y, 8, lw=0.7)
        sh.text(112, y - 3, str(j + 1), 8, bold=True, anchor="c")
    sh.line(BX0, 722, BX1, 722, lw=0.6)
    for x in (BX0, BX1):
        sh.line(x, 718, x, 726, lw=0.6)
    sh.text((BX0 + BX1) / 2, 728, ft_in(round((BX1 - BX0) / 6 * 12)), 7.5, anchor="c")

    sh.rect(BX0, BY0, BX1 - BX0, BY1 - BY0, lw=3.0)
    sh.rect(575, 530, 145, 130, lw=2.0)
    sh.text(647, 600, "CONTROL ROOM", 7.5, bold=True, anchor="c")
    sh.rect(575, 270, 145, 130, lw=2.0)
    sh.text(647, 330, "ELECTRICAL / MCC ROOM", 7.5, bold=True, anchor="c")
    sh.text(158, 645, f"{building} - PLAN", 9, bold=True)
    sh.text(158, 634, "FINISHED FLOOR EL. 100'-0\"", 6.6)

    # powered equipment in the main hall, each with a LOTO isolation tag
    kinds = [("K", "BOG COMPRESSOR", 92, 56), ("P", "LNG PUMP", 58, 40), ("P", "BOOSTER PUMP", 58, 40),
             ("E", "ELECTRIC HEATER", 72, 44), ("LCP", "LOCAL PANEL", 56, 56), ("K", "REFRIGERANT COMPRESSOR", 92, 56)]
    cells = rng.sample([(c, r) for c in range(3) for r in range(2)], rng.randint(4, 6))
    base = rng.randrange(3100, 3900, 100)
    equipment = []
    for n, (cell, (kind, desc, w, h)) in enumerate(zip(cells, rng.sample(kinds, len(cells))), 1):
        cxx = 160 + cell[0] * 132 + 66 + float(np_rng.uniform(-8, 8))
        cyy = 300 + cell[1] * 165 + 70 + float(np_rng.uniform(-10, 10))
        equipment.append({"box": Box(cxx - w / 2, cyy - h / 2, cxx + w / 2, cyy + h / 2), "kind": kind, "desc": desc,
                          "tag": f"{kind}-{base + n}" + ("A" if kind == "P" else "")})
    bad_loto = rng.choice(equipment) if "missing_loto_tag" in plants else None
    for eq in equipment:
        b = eq["box"]
        with sh.track() as t:
            sh.rect(b.x0, b.y0, b.w, b.h, lw=1.2, fill=0.93)
            sh.line(b.x0, b.y0, b.x1, b.y1, lw=0.4, gray=0.55)
            sh.line(b.x0, b.y1, b.x1, b.y0, lw=0.4, gray=0.55)
            sh.rect(b.x0 + 4, b.y0 + b.h / 2 - 9, b.w - 8, 18, lw=0, fill=0.93, stroke=False)
            sh.text(b.x0 + b.w / 2, b.y0 + b.h / 2 + 1, eq["tag"], 8, bold=True, anchor="c")
            sh.text(b.x0 + b.w / 2, b.y0 + b.h / 2 - 7, eq["desc"], 5.8, anchor="c")
            slot = Box(b.x0, b.y1 + 3, b.x0 + 62, b.y1 + 14)
            if eq is bad_loto:
                sh.reserve(slot)
            else:
                sym_loto(sh, slot.x0, slot.y0, f"LOTO-{eq['tag'].split('-', 1)[1]}")
        if eq is bad_loto:
            planted.append(("missing_loto_tag", t.box))

    # exits: clear widths against what the occupant load requires
    exits = []
    for wall, pos in sorted(rng.sample(GA_DOORS, rng.choice((3, 4)))):
        req = rng.choice((36, 44, 48, 60))
        occ = {36: rng.randint(20, 50), 44: rng.randint(60, 150), 48: rng.randint(160, 200), 60: rng.randint(210, 300)}[req]
        exits.append({"wall": wall, "pos": pos, "req": req, "occ": occ, "prov": req + rng.choice((0, 0, 4, 8)),
                      "area": "MCC ROOM" if (wall, pos) == ("R", 335) else "MAIN HALL"})
    bad_exit = rng.choice(exits) if "egress_width_under_code" in plants else None
    if bad_exit:
        bad_exit["prov"] = bad_exit["req"] - rng.choice((6, 8, 10, 12))
    for k, ex in enumerate(exits, 1):
        wall, pos, w = ex["wall"], ex["pos"], ex["prov"] * 0.5  # 6 pt per foot
        hinge = {"L": (BX0, pos - w / 2), "R": (BX1, pos - w / 2), "B": (pos - w / 2, BY0), "T": (pos - w / 2, BY1)}[wall]
        with sh.track() as t:
            sym_door(sh, wall, hinge[0], hinge[1], w)
            lab1, lab2 = f"EXIT {k}", f"CLR {ex['prov']} IN"
            if wall == "L":
                sh.text(BX0 - w - 8, pos + 2, lab1, 7.2, bold=True, anchor="r")
                sh.text(BX0 - w - 8, pos - 7, lab2, 6.8, anchor="r")
            elif wall == "R":
                sh.text(BX1 + w + 8, pos + 2, lab1, 7.2, bold=True)
                sh.text(BX1 + w + 8, pos - 7, lab2, 6.8)
            elif wall == "B":
                sh.text(pos, BY0 - w - 14, lab1, 7.2, bold=True, anchor="c")
                sh.text(pos, BY0 - w - 23, lab2, 6.8, anchor="c")
            else:
                sh.text(pos, BY1 + w + 17, lab1, 7.2, bold=True, anchor="c")
                sh.text(pos, BY1 + w + 8, lab2, 6.8, anchor="c")
        if ex is bad_exit:
            planted.append(("egress_width_under_code", t.box))

    sh.text(30, 214, "EGRESS SCHEDULE", 8, bold=True)
    sh.table(30, 208, [50, 130, 80, 130, 120],
             [[f"EXIT {k}", ex["area"], str(ex["occ"]), str(ex["req"]), str(ex["prov"])] for k, ex in enumerate(exits, 1)],
             header=["EXIT", "AREA SERVED", "OCC. LOAD", "REQ'D CLR WIDTH (IN)", "PROVIDED (IN)"], size=7.0, row_h=12, hdr_h=13)
    sh.text(570, 216, "KEY", 8, bold=True)
    sh.rect(570, 148, 244, 64, lw=0.6)
    sh.rect(580, 192, 26, 12, lw=1.2, fill=0.93)
    sh.text(614, 194.5, "POWERED EQUIPMENT (TAG INSIDE)", 6.6)
    sym_loto(sh, 580, 173, "LOTO-0000")
    sh.text(650, 176.5, "LOTO ISOLATION TAG", 6.6)
    sym_door(sh, "L", 592, 153, 12)
    sh.text(614, 155.5, "EXIT DOOR WITH SWING", 6.6)

    notes_column(sh, [
        "DIMENSIONS ARE IN FEET AND INCHES. GRID LINES ARE COLUMN CENTERLINES. PLAN IS 6 PT TO THE FOOT.",
        "MEANS OF EGRESS SHALL BE SIZED FOR THE OCCUPANT LOAD SERVED (IBC 1005.1). MINIMUM CLEAR WIDTH IS 36 IN, OR 44 IN WHERE THE LOAD EXCEEDS 50. THE PROVIDED WIDTH OF EACH EXIT SHALL NOT BE LESS THAN THE REQUIRED WIDTH IN THE EGRESS SCHEDULE.",
        "EVERY ITEM OF POWERED EQUIPMENT SHALL CARRY A LOTO ENERGY ISOLATION TAG AT ITS DISCONNECT (OSHA 29 CFR 1910.147).",
        "EQUIPMENT LOCATIONS ARE SCHEMATIC. SEE PIPING AND ELECTRICAL DRAWINGS FOR CONNECTIONS.",
        "ALL EXIT DOORS SWING IN THE DIRECTION OF EGRESS.",
    ], ["IBC 2021 CHAPTER 10 MEANS OF EGRESS", "OSHA 29 CFR 1910.147 LOCKOUT/TAGOUT", "NFPA 59A LNG FACILITIES"], rating=False)
    return planted


def draw_spec(sh: Sheet, meta, plants):
    rng, planted = sh.rng, []
    area = meta["area"]
    meta["subtitle"] = f"PROCESS PIPING - {area}"
    base = rng.randrange(3100, 3900, 100)

    # Table 1: piping classes. A flawed row shows a flange class that cannot hold the row's design pressure.
    sh.text(30, 748, "TABLE 1 - PIPING CLASS SUMMARY", 9, bold=True)
    rows1, dps = [], {}
    bad1 = rng.choice([c for c in CLASSES if c >= 300]) if "flange_rating_mismatch" in plants else None
    for cls in CLASSES:
        dps[cls] = design_pressure(rng, cls)
        shown = under_rated(rng, cls) if cls == bad1 else cls
        rows1.append([CLASS_CODE[cls], "A312 TP304L" if cls < 600 else "A312 TP316L", str(shown), f"{RATING_PSIG[shown]} PSIG",
                      f"{dps[cls]} PSIG", "-270 / 140 F", CLASS_SERVICE[cls]])
    boxes1 = sh.table(30, 742, [70, 120, 80, 110, 120, 100, 184], rows1,
                      header=["CLASS CODE", "MATERIAL", "FLANGE CLASS", "RATING @ 100 F", "DESIGN PRESS", "DESIGN TEMP", "SERVICE"],
                      size=8.0, row_h=20, hdr_h=20)
    if bad1:
        planted.append(("flange_rating_mismatch", boxes1[CLASSES.index(bad1)]))

    # Table 2: joint types and examination. Cold service takes butt welds with 100% RT in every class.
    sh.text(30, 600, "TABLE 2 - WELD JOINT AND EXAMINATION REQUIREMENTS (ASME B31.3 PARA. 341)", 9, bold=True)
    bad2 = rng.choice(CLASSES) if "weld_joint_spec_mismatch" in plants else None
    rows2 = []
    for cls in CLASSES:
        joint, exam = "BW", "100% RT"
        if cls == bad2:
            joint, exam = rng.choice((("FW", "VT ONLY"), ("SW", "MT 5%"), ("BW", "NONE")))
        rows2.append([CLASS_CODE[cls], joint, exam, f"WPS-{CLASS_CODE[cls]}-{rng.randint(1, 9):02d}", "COLD SERVICE"])
    boxes2 = sh.table(30, 594, [70, 110, 140, 200, 264], rows2,
                      header=["CLASS CODE", "JOINT TYPE", "EXAMINATION", "WELD PROCEDURE", "REMARKS"], size=8.0, row_h=20, hdr_h=20)
    if bad2:
        planted.append(("weld_joint_spec_mismatch", boxes2[CLASSES.index(bad2)]))

    # Table 3: relief devices. A flawed row has no PSV tag, set pressure or orifice.
    sh.text(30, 452, "TABLE 3 - PRESSURE RELIEF DEVICE SCHEDULE (ASME B31.3 PARA. 322)", 9, bold=True)
    count = rng.randint(5, 7)
    bad3 = rng.randrange(count) if "missing_pressure_relief_notation" in plants else -1
    descs = rng.sample(["KNOCKOUT DRUM", "SUCTION DRUM", "SEPARATOR", "SURGE DRUM", "FUEL GAS DRUM", "FLASH DRUM", "SCRUBBER"], count)
    rows3 = []
    for i, d in enumerate(descs):
        dp = dps[rng.choice(CLASSES)]
        row = [f"V-{base + i + 1}", d, f"{dp} PSIG"]
        row += ["", "", ""] if i == bad3 else [f"PSV-{base + i + 1}", f"{dp} PSIG", rng.choice("DEFGHJKL")]
        rows3.append(row + [area])
    boxes3 = sh.table(30, 446, [90, 170, 110, 100, 110, 70, 134], rows3,
                      header=["EQUIPMENT TAG", "DESCRIPTION", "DESIGN PRESS", "PSV TAG", "SET PRESS", "ORIFICE", "AREA"],
                      size=8.0, row_h=20, hdr_h=20)
    if bad3 >= 0:
        planted.append(("missing_pressure_relief_notation", boxes3[bad3]))

    sh.text(30, 40, "ABBREVIATIONS: BW BUTT WELD, SW SOCKET WELD, FW FILLET WELD, RT RADIOGRAPHIC, VT VISUAL, MT MAGNETIC PARTICLE, "
                    "PSV PRESSURE SAFETY VALVE, PSIG POUNDS PER SQUARE INCH GAUGE.", 6.6)

    notes_column(sh, [
        "THIS SPECIFICATION GOVERNS ALL PROCESS PIPING IN THE AREA SHOWN IN THE TITLE BLOCK.",
        "THE FLANGE CLASS IN TABLE 1 SHALL BE RATED FOR THE DESIGN PRESSURE OF ITS CLASS (ASME B16.5); SEE FLANGE RATING REFERENCE.",
        "ALL CLASSES ARE COLD-SERVICE STAINLESS: FULL-PENETRATION BUTT WELDS (BW) WITH 100% RT. SOCKET AND FILLET WELDS ARE NOT PERMITTED (ASME B31.3 PARA. 341).",
        "EVERY PRESSURE VESSEL SHALL BE LISTED IN TABLE 3 WITH ITS RELIEF DEVICE TAG, SET PRESSURE AND ORIFICE (ASME B31.3 PARA. 322).",
        "CLASS CODES: A1S = CL150, B3S = CL300, C6S = CL600, D9S = CL900, E15S = CL1500.",
    ], ["ASME B31.3 PROCESS PIPING", "ASME B16.5 PIPE FLANGES AND FLANGED FITTINGS", "API 526 FLANGED STEEL PRESSURE RELIEF VALVES"])
    return planted


def draw_legend(sh: Sheet, meta, plants):
    """Symbols sheet. It defines the symbols the other sheets use and never carries a planted flaw."""
    meta["subtitle"] = "ALL AREAS"
    entries = [
        ("GATE VALVE (HV)", "MANUAL ISOLATION VALVE", lambda x, y: sym_bowtie(sh, x, y, 0.0, 14, 8)),
        ("CONTROL VALVE (FV)", "ACTUATED CONTROL VALVE", lambda x, y: (sym_bowtie(sh, x, y, 0.0, 14, 8), sh.circle(x, y + 14, 7, fill=1.0))),
        ("INSTRUMENT", "FUNCTION LETTERS OVER LOOP NUMBER", lambda x, y: sym_instrument(sh, x, y, "PIC", "101", r=14)),
        ("PRESSURE SAFETY VALVE (PSV)", "TAG AND SET PRESSURE SHOWN AT THE VESSEL", lambda x, y: sym_psv(sh, x - 6, y - 6)),
        ("LOTO ENERGY ISOLATION TAG", "ON EVERY PUMP, COMPRESSOR, POWERED UNIT", lambda x, y: sym_loto(sh, x - 33, y - 5, "LOTO-0000")),
        ("FLANGED JOINT (FLG)", "CLASS SHOWN AT THE JOINT", lambda x, y: sym_flange(sh, x, y, 0.0, 10, 3)),
        ("BUTT WELD CALLOUT", "WELD NUMBER, TYPE, EXAMINATION", lambda x, y: (sh.circle(x - 30, y, 3, fill=0.0), sh.text(x - 22, y - 2.5, "W1 BW RT 100%", 7))),
        ("PUMP", "CENTRIFUGAL PUMP WITH MOTOR", lambda x, y: sym_pump(sh, x, y - 10)),
        ("PRESSURE VESSEL", "TAG, DESIGN DATA AND PSV AT THE VESSEL", lambda x, y: sym_vessel(sh, x, y, 36, 70)),
        ("EXIT DOOR", "CLEAR WIDTH SHOWN IN INCHES", lambda x, y: sym_door(sh, "L", x, y - 14, 28)),
        ("POWERED EQUIPMENT", "FOOTPRINT ON GENERAL ARRANGEMENTS", lambda x, y: (sh.rect(x - 34, y - 18, 68, 36, lw=1.2, fill=0.93), sh.text(x, y - 2, "K-0000", 8, bold=True, anchor="c"))),
        ("COMPRESSOR", "CENTRIFUGAL COMPRESSOR WITH MOTOR", lambda x, y: sym_compressor(sh, x, y - 8)),
    ]
    for n, (head, caption, draw) in enumerate(entries):
        col, row = n % 4, n // 4
        x0, y_top = 30 + col * 197, 750 - row * 235
        sh.rect(x0, y_top - 220, 191, 220, lw=0.6)
        sh.text(x0 + 6, y_top - 14, head, 7.6, bold=True)
        draw(x0 + 95, y_top - 110)
        sh.text(x0 + 6, y_top - 208, caption, 6.4)
    notes_column(sh, [
        "THIS SHEET DEFINES THE SYMBOLS AND ABBREVIATIONS USED ON ALL PROJECT PIPING, INSTRUMENTATION AND ARRANGEMENT DRAWINGS.",
        "SYMBOLS ARE SHOWN AT A LARGER SCALE THAN ON THE DRAWINGS THEY SERVE.",
        "PROJECT CODES AND STANDARDS ARE LISTED ON EACH DRAWING THAT APPLIES THEM.",
    ], ["ISA 5.1 INSTRUMENTATION SYMBOLS AND IDENTIFICATION", "ASME B31.3 PROCESS PIPING"], rating=False)
    return []


DRAWERS = {"ISO": draw_iso, "PID": draw_pid, "GA": draw_ga, "SPEC": draw_spec, "OTHER": draw_legend}
SCALES = {"ISO": "NTS", "PID": "NTS", "GA": "1:50", "SPEC": "N/A", "OTHER": "NTS"}


# --------------------------------------------------------------------------------------------------
# Frame, title block and revision table
# --------------------------------------------------------------------------------------------------

def draw_frame(sh: Sheet, meta, page_no: int, pages: int):
    sh.rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, lw=1.6)
    sh.rect(MARGIN + 4, MARGIN + 4, PAGE_W - 2 * MARGIN - 8, PAGE_H - 2 * MARGIN - 8, lw=0.5)

    rows = [
        (26, [(126, "DRAWN BY", meta["drawn"]), (125, "CHECKED BY", meta["checked"]), (125, "APPROVED BY", meta["approved"])]),
        (26, [(94, "SCALE", meta["scale"]), (94, "SHEET", f"{page_no} OF {pages}"), (94, "DATE", meta["date"]),
              (94, "DISCIPLINE", meta["discipline"].upper())]),
    ]
    y = 22.0
    for h, cells in rows:
        x = COL_X0
        for w, label, value in cells:
            sh.rect(x, y, w, h, lw=0.6)
            sh.text(x + 3, y + h - 7.5, label, 5.8)
            size = 9.0
            while stringWidth(value, BOLD, size) > w - 8 and size > 6:
                size -= 0.3
            sh.text(x + 4, y + 4, value, size, bold=True)
            x += w
        y += h
    sh.rect(COL_X0, y, 282, 34, lw=0.6)
    sh.text(COL_X0 + 3, y + 26.5, "DRAWING NUMBER", 5.8)
    sh.text(COL_X0 + 4, y + 7, meta["drawing_id"], 14, bold=True)
    sh.rect(COL_X0 + 282, y, 94, 34, lw=0.6)
    sh.text(COL_X0 + 285, y + 26.5, "REV", 5.8)
    sh.text(COL_X0 + 289, y + 7, meta["revision"], 16, bold=True)
    y += 34
    sh.rect(COL_X0, y, 376, 44, lw=0.6)
    sh.text(COL_X0 + 3, y + 36, "TITLE", 5.8)
    sh.text(COL_X0 + 5, y + 21, meta["title"], 10, bold=True)
    sh.text(COL_X0 + 5, y + 8, meta["subtitle"], 8.5)
    y += 44
    sh.rect(COL_X0, y, 376, 20, lw=0.6)
    sh.text(COL_X0 + 3, y + 13, "PROJECT", 5.8)
    sh.text(COL_X0 + 5, y + 4, "BLUE RIDGE LNG TERMINAL - PHASE 2", 8.5, bold=True)
    y += 20  # = 172

    sh.table(COL_X0, y + 14 * 5, [26, 62, 190, 48, 50], meta["history"][-4:],
             header=["REV", "DATE", "DESCRIPTION", "BY", "CHK"], size=6.6, row_h=14)


def build_meta(plan: "DrawingPlan", seed: int) -> dict:
    rng = random.Random(f"{seed}:{plan.index}:meta")
    n_rev = REVISIONS.index(plan.revision) + 1
    start = date(2025, 4, 1)
    days = sorted(rng.sample(range(0, (AS_OF - timedelta(days=7) - start).days), n_rev))
    history = []
    for i, d in enumerate(days):
        by, chk = _initials(_person(rng)), _initials(_person(rng))
        history.append([REVISIONS[i], (start + timedelta(days=d)).isoformat(), REVISION_NOTES[i], by, chk])
    return {
        "drawing_id": plan.drawing_id, "discipline": plan.discipline, "revision": plan.revision,
        "title": TITLES[plan.drawing_type], "subtitle": "", "area": rng.choice(AREAS), "scale": SCALES[plan.drawing_type],
        "date": history[-1][1], "history": history,
        "drawn": _person(rng), "checked": _person(rng), "approved": _person(rng),
    }


# --------------------------------------------------------------------------------------------------
# Planning: which drawing is what, and where the flaws go
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DrawingPlan:
    index: int
    drawing_id: str
    drawing_type: str
    discipline: str
    revision: str
    pages: int
    flaws: tuple  # ((flaw_type, page_index), ...)


def plan_drawings(n: int, flaw_rate: float, seed: int) -> list[DrawingPlan]:
    if n < 0 or not 0.0 <= flaw_rate <= 1.0:
        raise ValueError(f"need n >= 0 and 0 <= flaw_rate <= 1, got n={n}, flaw_rate={flaw_rate}")
    rng = random.Random(seed)
    k = round(n * flaw_rate)
    flawed = rng.sample(range(n), k)  # exactly k drawings carry a flaw, not a coin flip per drawing
    n3 = round(MULTI_FLAW_SHARE[3] * k)
    n2 = round(MULTI_FLAW_SHARE[2] * k)
    count = {idx: 3 if j < n3 else 2 if j < n3 + n2 else 1 for j, idx in enumerate(flawed)}
    singles = [idx for idx in flawed if count[idx] == 1]
    kinds = [list(FLAW_TYPES)[i % len(FLAW_TYPES)] for i in range(len(singles))]  # balanced across the five types
    rng.shuffle(kinds)
    single_kind = dict(zip(singles, kinds))

    plans = []
    for idx in range(n):
        wanted = count.get(idx, 0)
        if wanted == 0:
            dtype, flaw_kinds = _choice(rng, TYPE_WEIGHTS), []
        elif wanted == 1:
            kind = single_kind[idx]
            dtype = _choice(rng, {t: w for t, w in TYPE_WEIGHTS.items() if kind in SUPPORTS[t]})
            flaw_kinds = [kind]
        else:
            dtype = _choice(rng, {t: w for t, w in TYPE_WEIGHTS.items() if len(SUPPORTS[t]) >= wanted})
            flaw_kinds = rng.sample(SUPPORTS[dtype], wanted)
        discipline = _choice(rng, DISCIPLINE_WEIGHTS[dtype])
        revision = rng.choices(REVISIONS, weights=REVISION_WEIGHTS)[0]
        pages = 2 if rng.random() < PAGE2_PROBABILITY[dtype] else 1
        plans.append(DrawingPlan(
            index=idx,
            drawing_id=f"BRL-{DISCIPLINE_CODE[discipline]}-{TYPE_CODE[dtype]}-{idx + 1:04d}",
            drawing_type=dtype, discipline=discipline, revision=revision, pages=pages,
            flaws=tuple((kind, rng.randrange(pages)) for kind in flaw_kinds),
        ))
    return plans


def render_drawing(plan: DrawingPlan, seed: int):
    """Draw one PDF. Returns (pdf_bytes, [(flaw_type, page_index, Box), ...])."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H), invariant=1)  # invariant: fixed dates and ids -> reproducible bytes
    c.setTitle(f"{plan.drawing_id} REV {plan.revision}")
    c.setAuthor("Blue Ridge LNG Terminal Phase 2 - Project Engineering")
    c.setSubject(TITLES[plan.drawing_type])
    meta = build_meta(plan, seed)
    planted = []
    for page in range(plan.pages):
        sh = Sheet(c, random.Random(f"{seed}:{plan.index}:{page}"), np.random.default_rng([seed, plan.index, page]))
        wanted = [kind for kind, pg in plan.flaws if pg == page]
        found = DRAWERS[plan.drawing_type](sh, meta, wanted)
        assert sorted(k for k, _ in found) == sorted(wanted), f"{plan.drawing_id} p{page}: planted {found}, wanted {wanted}"
        draw_frame(sh, meta, page + 1, plan.pages)
        planted += [(kind, page, box) for kind, box in found]
        c.showPage()
    c.save()
    return buf.getvalue(), planted


# --------------------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------------------

@dataclass
class GenerateResult:
    manifest: list  # [{drawing_id, discipline, revision, drawing_type, volume_path, has_flaw}]
    ground_truth: list  # [{drawing_id, finding_id, page_num, bbox, citation, severity, flaw_type}]

    @property
    def manifest_count(self) -> int:
        return len(self.manifest)

    @property
    def flawed_count(self) -> int:
        return sum(1 for d in self.manifest if d["has_flaw"])

    @property
    def finding_count(self) -> int:
        return len(self.ground_truth)

    def write_manifest(self, path) -> None:
        """A JSON array with one drawing per line (readable in a diff)."""
        rows = ",\n".join("  " + json.dumps(d, ensure_ascii=False) for d in self.manifest)
        Path(path).write_text("[\n" + rows + "\n]\n", encoding="utf-8")

    def write_ground_truth(self, path) -> None:
        """JSON Lines, one planted finding per line."""
        Path(path).write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in self.ground_truth), encoding="utf-8")


def generate_drawings(n: int, flaw_rate: float, seed: int, out_dir, progress_every: int = 0) -> GenerateResult:
    """Write `n` drawing PDFs to `out_dir` and return their manifest and planted-flaw ground truth."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest, ground_truth = [], []
    for plan in plan_drawings(n, flaw_rate, seed):
        pdf, planted = render_drawing(plan, seed)
        path = out / f"{plan.drawing_id}.pdf"
        path.write_bytes(pdf)  # one write per file: Volumes do not like append / seek
        manifest.append({"drawing_id": plan.drawing_id, "discipline": plan.discipline, "revision": plan.revision,
                         "drawing_type": plan.drawing_type, "volume_path": path.as_posix(), "has_flaw": bool(planted)})
        for k, (kind, page, box) in enumerate(planted, 1):
            citation, severity = FLAW_TYPES[kind]
            ground_truth.append({"drawing_id": plan.drawing_id, "finding_id": f"{plan.drawing_id}-F{k:02d}", "page_num": page,
                                 "bbox": normalise_bbox(box), "citation": citation, "severity": severity, "flaw_type": kind})
        if progress_every and (plan.index + 1) % progress_every == 0:
            print(f"{plan.index + 1}/{n} drawings written")
    return GenerateResult(manifest, ground_truth)


if __name__ == "__main__":  # local spot checks:  python 02_generate_drawings.py --n 20 --out /tmp/drawings
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--flaw-rate", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="drawings_out")
    a = ap.parse_args()
    res = generate_drawings(a.n, a.flaw_rate, a.seed, a.out)
    res.write_manifest(Path(a.out) / "drawing_manifest.json")
    res.write_ground_truth(Path(a.out) / "ground_truth_findings.jsonl")
    print(f"{res.manifest_count} drawings, {res.flawed_count} flawed, {res.finding_count} findings -> {a.out}")
