"""Pure functions for the compliance judge (03_compliance_check.ipynb). No Spark, no AI call: unit-tested locally.

* RULES / build_prompt: the fixed, paraphrased rule set and the prompt text the judge sees. The only per-drawing inputs are
  the drawing type, the discipline and the parsed markdown; nothing from the generator's ground truth reaches the prompt.
* flatten_judgement: one raw judge answer -> the finding rows (FAIL), a PASS sentinel, or one REVIEW row.
* assign_review_dates: the simulated review date of each drawing.
* resolve_parse_bbox: a normalised box from the parser's element boxes, for a finding that has no ground-truth box.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta

# --------------------------------------------------------------------------------------------------
# The rule set. ASME and IBC are copyrighted, so each rule is a paraphrased engineering requirement plus its clause number;
# the OSHA rule paraphrases a public-domain regulation. One rule per citation.
# --------------------------------------------------------------------------------------------------

RULES = [
    {
        "citation": "ASME B16.5 §4.2",
        "severity": "critical",
        "title": "Flange pressure rating",
        "text": (
            "Every flanged joint must use a flange class whose maximum allowable pressure is at least the design pressure of the line "
            "it sits on. Use the flange rating table printed on the drawing (class against maximum allowable pressure). Line tags end "
            "with a class code that the general notes decode to a flange class, and each line is labelled with its design pressure (DP, PSIG). "
            "On a specification sheet, check each row: the rating of the flange class shown must cover the row's design pressure. "
            "Violation: a flange class shown (for example CL150) whose table rating is below the design pressure of its line or row."
        ),
    },
    {
        "citation": "OSHA 1910.147",
        "severity": "high",
        "title": "Lockout/tagout isolation",
        "text": (
            "Every item of powered equipment (pump, compressor, motor-driven machine, electric heater, local control panel) must carry an "
            "energy isolation (lockout/tagout) tag, drawn as a LOTO-nnnn label next to the equipment. Compare the list of powered "
            "equipment tags (K-, P-, E-, LCP- tags) with the LOTO tags: a LOTO tag carries the number of its equipment tag, including a suffix "
            "letter (pump P-2104A has LOTO-2104A, compressor K-2104 has LOTO-2104). The tags may be anywhere in the text, and the circle symbol "
            "before a tag, or the letter O of LOTO, may come out as O, 0 or an extra letter. Vessels, drums and tanks are not powered equipment. "
            "Violation: a powered equipment item with no LOTO tag of its own."
        ),
    },
    {
        "citation": "IBC 1005.1",
        "severity": "high",
        "title": "Means of egress width",
        "text": (
            "Each exit must provide a clear width at least equal to the width required for the occupant load it serves. Compare, for every "
            "exit, the clear width provided (the CLR labels and the PROVIDED column of the egress schedule) with the required clear width "
            "in the egress schedule. Violation: an exit whose provided clear width is smaller than its required clear width."
        ),
    },
    {
        "citation": "ASME B31.3 §341",
        "severity": "medium",
        "title": "Weld joint type and examination",
        "text": (
            "Weld joints and their examination must follow the piping class requirement the drawing states. For cold (cryogenic) service "
            "that requirement is a butt weld (BW) with 100% radiographic examination (RT) in every class. Check every weld label on an isometric "
            "(W1, W2, ... with joint type and examination) and every row of a weld requirements table. Violation: a weld or class row with a "
            "different joint type (fillet FW or socket SW instead of BW) or with less examination than the requirement (VT only, MT 5%, none)."
        ),
    },
    {
        "citation": "ASME B31.3 §322",
        "severity": "critical",
        "title": "Pressure relief protection",
        "text": (
            "Every pressure vessel or drum must be protected by a pressure relief device, shown with a PSV tag and a set pressure. "
            "Compare the vessels (V- tags) with the PSV tags and set pressures: the digits of a PSV tag follow its vessel tag (V-2504 is "
            "protected by PSV-2504), and the tag may be anywhere in the text. On a schematic the PSV tag and set pressure are enough; only a "
            "relief device schedule table also lists an orifice, so check there that every row has all three entries. "
            "Violation: a vessel or schedule row without a PSV tag, set pressure or (in a schedule) orifice."
        ),
    },
]
CITATIONS = [r["citation"] for r in RULES]
SEVERITIES = ("critical", "high", "medium", "low")

INSTRUCTIONS = (
    "You are a senior piping and facilities engineer checking one engineering drawing of an LNG terminal against the five rules below. "
    "The drawing was read from a PDF by a parser: the text of a schematic comes as one block in no particular order, so match items "
    "(equipment, tags, labels) by their tags and numbers, not by position; a tag that is not next to its equipment still counts, and the parser "
    "may write the letter O as a zero (LOT0-2104A is the tag LOTO-2104A). Report only violations that the text of the drawing itself "
    "shows, and do not report a rule that the drawing does not have an element for (for example a sheet with no exits has nothing to "
    "check for the egress rule). Check every rule that applies, and every item the rule covers. A drawing can have several violations, "
    "including more than one of the same rule, and a compliant drawing has none.\n\n"
    "Be exact rather than eager. Before you report a missing item (a LOTO tag, a PSV, a relief schedule entry), search the whole drawing text "
    "for the item that would make the drawing comply, for example LOTO-2104A for pump P-2104A or PSV-2102 for vessel V-2102. If it appears "
    "anywhere in the text, the item is present and there is no violation. Before you report a number (a flange rating, an exit width, a weld "
    "examination), compare the two numbers and report only if the drawing's own figures break the rule. Do not report a doubtful case, a case "
    "you could only suspect, or a case whose explanation says the requirement is met: reporting nothing is correct for a compliant drawing."
)
OUTPUT_FORMAT = (
    "Answer with JSON only: an object with one key, findings, an array with one entry per violation (an empty array when there is none). "
    "Each entry has: expected_item (the tag, label or value whose presence would make the item comply, for example LOTO-2104A, PSV-2102, "
    "CLASS 600 or higher, 48 IN), found_in_text (true if you found that expected item anywhere in the drawing text, otherwise false), "
    "status (always FAIL), citation (exactly one of the five citations above), severity (critical, high, medium or low), "
    "reason (one or two plain sentences a project manager can read, naming the item and the numbers), page_num (the page the item is on, "
    "counting from 0, as in the page_num comments in the text) and evidence_text (a short exact quote, 40 characters at most, of the label "
    "or table cell in the drawing text that shows the violation, for example FLG CL150 or K-2502)."
)


def rules_text() -> str:
    return "\n\n".join(f"RULE {i}. {r['citation']} - {r['title']} (usual severity: {r['severity']})\n{r['text']}" for i, r in enumerate(RULES, 1))


def build_prompt_prefix() -> str:
    # Everything in the prompt before the per-drawing part. The same text goes to every drawing.
    return f"{INSTRUCTIONS}\n\nRULES\n\n{rules_text()}\n\n{OUTPUT_FORMAT}\n\n"


def sql_prompt_expr(prefix_sql_literal: str) -> str:
    # The SQL expression that builds the prompt from the three per-drawing inputs; no other column reaches the model.
    return (f"concat({prefix_sql_literal}, 'DRAWING TYPE: ', coalesce(drawing_type, 'unknown'), '\\nDISCIPLINE: ', coalesce(discipline, 'unknown'), "
            f"'\\n\\nDRAWING TEXT:\\n', parsed_markdown)")


# --------------------------------------------------------------------------------------------------
# One judge answer -> rows
# --------------------------------------------------------------------------------------------------

_CITATION_PATTERNS = [  # (regex on the lower-cased text, canonical citation)
    (re.compile(r"b\s*16\.?5"), "ASME B16.5 §4.2"),
    (re.compile(r"1910\.?\s*147"), "OSHA 1910.147"),
    (re.compile(r"\bibc\b.*1005|1005\.?\s*1"), "IBC 1005.1"),
    (re.compile(r"b\s*31\.?3.*341|341"), "ASME B31.3 §341"),
    (re.compile(r"b\s*31\.?3.*322|322"), "ASME B31.3 §322"),
]


def normalize_citation(text):
    # One of the five canonical citations, or None.
    if not isinstance(text, str):
        return None
    t = text.lower()
    return next((canon for pattern, canon in _CITATION_PATTERNS if pattern.search(t)), None)


def normalize_severity(text):
    t = text.strip().lower() if isinstance(text, str) else ""
    return t if t in SEVERITIES else "medium"


def _one_line(value, limit):
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None
    text = " ".join(str(value).split())
    return text[:limit] or None


def _row(drawing_id, finding_id, status, reason, citation=None, severity=None, page_num=None, evidence_text=None):
    return {"drawing_id": drawing_id, "finding_id": finding_id, "status": status, "reason": reason, "citation": citation,
            "severity": severity, "page_num": page_num, "evidence_text": evidence_text}


def _review(drawing_id, why):
    return [_row(drawing_id, f"{drawing_id}-REVIEW", "REVIEW", f"Judge output could not be parsed: {why}"[:300])]


def flatten_judgement(drawing_id, response, error):
    """The rows for one drawing from the judge's raw answer (`response` text, `error` text or None). Never raises.

    * error set, or the answer is not the expected JSON  -> one REVIEW row with a reason.
    * no findings                                        -> one PASS row (citation, page, severity, evidence are None).
    * findings                                           -> one FAIL row per finding with a recognised citation, finding_id
                                                             <drawing_id>-C01, -C02, ...; if none of them has a recognised
                                                             citation the drawing gets one REVIEW row instead.
    """
    try:
        if error:
            return _review(drawing_id, " ".join(str(error).split())[:200])
        if not isinstance(response, str) or not response.strip():
            return _review(drawing_id, "empty response")
        body = response.strip()
        body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body)
        parsed = json.loads(body)
        found = parsed.get("findings") if isinstance(parsed, dict) else None
        if not isinstance(found, list):
            return _review(drawing_id, "no findings array")
        if not all(isinstance(f, dict) for f in found):
            return _review(drawing_id, "a finding is not an object")
        if not found:
            return [_row(drawing_id, f"{drawing_id}-PASS", "PASS", "No violation of the five checked rules found.")]
        rows, cleared = [], 0
        for f in found:
            if str(f.get("status", "FAIL")).strip().upper() == "PASS":
                continue
            citation = normalize_citation(f.get("citation"))
            if citation is None:
                continue
            if f.get("found_in_text") is True:  # the judge's own check found the item that makes the drawing comply: not a violation
                cleared += 1
                continue
            page = f.get("page_num")
            page = int(page) if isinstance(page, (int, float)) and not isinstance(page, bool) and page >= 0 else 0
            rows.append(_row(drawing_id, f"{drawing_id}-C{len(rows) + 1:02d}", "FAIL",
                             _one_line(f.get("reason"), 400) or f"Violation of {citation}.", citation,
                             normalize_severity(f.get("severity")), page, _one_line(f.get("evidence_text"), 80)))
        if rows:
            return rows
        if all(str(f.get("status", "FAIL")).strip().upper() == "PASS" for f in found) or (
                cleared and cleared + sum(str(f.get("status", "FAIL")).strip().upper() == "PASS" for f in found) >= len(found)):
            return [_row(drawing_id, f"{drawing_id}-PASS", "PASS", "No violation of the five checked rules found.")]
        return _review(drawing_id, "findings cite no rule from the rule set")
    except Exception as e:  # a malformed answer must never fail the run
        return _review(drawing_id, f"{type(e).__name__}: {str(e)[:120]}")


# --------------------------------------------------------------------------------------------------
# Simulated review dates
# --------------------------------------------------------------------------------------------------

AS_OF_WEEK = (date(2026, 10, 31), date(2026, 11, 6))
HISTORY_START = date(2026, 6, 1)
WEEK_DRAWINGS, WEEK_FLAWED = 238, 24


def _h(drawing_id, salt):
    return int(hashlib.sha256(f"{salt}:{drawing_id}".encode()).hexdigest()[:12], 16)


def assign_review_dates(manifest):
    """{drawing_id: 'YYYY-MM-DD'}, deterministic. Exactly 238 drawings (24 of them flawed in the manifest) fall in the as-of week
    2026-10-31..2026-11-06; the others spread over 2026-06-01..2026-10-30. Chosen by a seeded hash of drawing_id."""
    flawed = sorted((d["drawing_id"] for d in manifest if d["has_flaw"]), key=lambda i: _h(i, "week"))
    clean = sorted((d["drawing_id"] for d in manifest if not d["has_flaw"]), key=lambda i: _h(i, "week"))
    in_week = set(flawed[:WEEK_FLAWED]) | set(clean[:WEEK_DRAWINGS - WEEK_FLAWED])
    week_days = (AS_OF_WEEK[1] - AS_OF_WEEK[0]).days + 1
    history_days = (AS_OF_WEEK[0] - HISTORY_START).days
    out = {}
    for d in manifest:
        i = d["drawing_id"]
        if i in in_week:
            out[i] = (AS_OF_WEEK[0] + timedelta(days=_h(i, "day") % week_days)).isoformat()
        else:
            out[i] = (HISTORY_START + timedelta(days=_h(i, "day") % history_days)).isoformat()
    return out


# --------------------------------------------------------------------------------------------------
# Boxes from the parser's elements
# --------------------------------------------------------------------------------------------------

PT_PER_PX = 1 / 2.75
SHEET_PX = (1224 * 2.75, 792 * 2.75)  # the sheets are 17 x 11 in landscape = 1224 x 792 pt, rendered at 2.75 px/pt = 3366 x 2178 px


def _squash(text):
    # Compare text without case, white space or punctuation; the parser sometimes reads the O of LOTO as a zero.
    return re.sub(r"[^A-Z0-9]", "", str(text).upper().replace("0", "O"))


def resolve_parse_bbox(parse_json, page_num, evidence_text, sheet_px=SHEET_PX):
    """[x, y, w, h] as fractions of the page, origin top-left, of the smallest parsed element on `page_num` whose text contains
    `evidence_text`; None when there is none. Parser boxes are [x1, y1, x2, y2] in pixels."""
    needle = _squash(evidence_text or "")
    if not parse_json or len(needle) < 3:
        return None
    try:
        doc = json.loads(parse_json) if isinstance(parse_json, str) else parse_json
        best = None
        for el in doc["document"]["elements"]:
            if _squash(el.get("content") or "").find(needle) < 0:
                continue
            for b in el.get("bbox") or []:
                if b.get("page_id") != page_num:
                    continue
                x1, y1, x2, y2 = (float(v) for v in b["coord"])
                area = max(x2 - x1, 0) * max(y2 - y1, 0)
                if best is None or area < best[0]:
                    best = (area, x1, y1, x2, y2)
        if best is None:
            return None
        _, x1, y1, x2, y2 = best
        W, H = sheet_px
        x, y = min(max(x1 / W, 0.0), 1.0), min(max(y1 / H, 0.0), 1.0)
        w, h = min(max((x2 - x1) / W, 0.0), 1.0 - x), min(max((y2 - y1) / H, 0.0), 1.0 - y)
        return [round(x, 4), round(y, 4), round(w, 4), round(h, 4)]
    except Exception:
        return None
