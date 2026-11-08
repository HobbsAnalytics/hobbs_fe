"""Pure functions for the compliance judge (03_compliance_check.ipynb, 03b_compliance_guardrails.ipynb). No Spark, no AI call: unit-tested locally.

* RULES / build_prompt: the fixed, paraphrased rule set and the prompt text the judge sees. The only per-drawing inputs are
  the drawing type, the discipline and the parsed markdown; nothing from the generator's ground truth reaches the prompt, and the
  rules name no value, tag or example that the synthetic generator draws (tests/test_guardrails.py::test_prompt_has_no_generator_literals).
* flatten_judgement: one raw judge answer -> the finding rows (FAIL), a PASS sentinel, or one REVIEW row.
* judge_with_guardrails: the same, plus a rule-applicability matrix and a self-consistency filter (no AI call); returns the suppressed entries too.
* assign_review_dates: the simulated review date of each drawing.
* resolve_parse_bbox: a normalised box from the parser's element boxes, for a finding that has no ground-truth box.

The five citations are fixed, illustrative labels for this synthetic demo (the ground truth and every table use them); the clause numbers are
not authoritative. Verify any clause against the licensed standard.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, timedelta

# --------------------------------------------------------------------------------------------------
# The rule set. ASME and IBC are copyrighted, so each rule is a general, paraphrased engineering requirement plus its clause number;
# the OSHA rule paraphrases a public-domain regulation. One rule per citation. A rule says what to compare against what, never which
# values or labels are wrong.
# --------------------------------------------------------------------------------------------------

RULES = [
    {
        "citation": "ASME B16.5 §4.2",
        "severity": "critical",
        "title": "Flange pressure rating",
        "text": (
            "A flanged joint must use a pressure class whose rated maximum allowable pressure is at least the design pressure of the line, "
            "pipe class or table row it serves. Read the class and the design pressure the drawing states for the item, and the drawing's own "
            "rating table (class against maximum allowable pressure), and compare the two numbers. "
            "Violation: a stated class whose rating in the table is below the stated design pressure."
        ),
    },
    {
        "citation": "OSHA 1910.147",
        "severity": "high",
        "title": "Lockout/tagout isolation",
        "text": (
            "Every item of powered or rotating equipment must have an energy-isolation (lockout/tagout) tag or callout of its own, as the "
            "drawing's legend and notes define it. Make the list of such equipment from the drawing's tags, make the list of isolation tags, and "
            "match them by number: an isolation tag carries the number of its equipment tag, including any suffix letter. The tags may be "
            "anywhere in the text, and the parser may misread a letter or a symbol in them. Vessels, drums and tanks are not powered equipment. "
            "Violation: a powered or rotating equipment item with no isolation tag of its own."
        ),
    },
    {
        "citation": "IBC 1005.1",
        "severity": "high",
        "title": "Means of egress width",
        "text": (
            "Each exit must provide a clear width at least equal to the width required for the occupant load it serves. For every exit, "
            "compare the clear width provided (on the exit itself and in the egress schedule) with the required clear width the drawing gives "
            "for its occupant load. Violation: an exit whose provided clear width is smaller than its required clear width."
        ),
    },
    {
        "citation": "ASME B31.3 §341",
        "severity": "medium",
        "title": "Weld joint type and examination",
        "text": (
            "Where the drawing or its specification states a required weld joint type or extent of examination for a line, pipe class or "
            "service, every weld callout and every table row for that service must meet it. Read the requirement, then check each weld callout "
            "and each row against it. Violation: a joint type that differs from the required type, or an examination level that falls short "
            "of the required extent."
        ),
    },
    {
        "citation": "ASME B31.3 §322",
        "severity": "critical",
        "title": "Pressure relief protection",
        "text": (
            "Every pressure vessel or drum must be protected by a pressure relief device that the drawing shows with its tag and set pressure. "
            "Make the list of vessels and the list of relief devices and match them by number: a relief device tag carries the number of "
            "its vessel tag, and may be anywhere in the text. On a schematic the tag and set pressure are enough; where the drawing gives a "
            "relief device schedule, each of its rows must also be complete (device tag, set pressure and sizing data). "
            "Violation: a vessel with no relief device, or an incomplete schedule row."
        ),
    },
]
CITATIONS = [r["citation"] for r in RULES]
SEVERITIES = ("critical", "high", "medium", "low")
LOTO_RULE, RELIEF_RULE = CITATIONS[1], CITATIONS[4]
PRESENCE_RULES = (LOTO_RULE, RELIEF_RULE)  # rules that ask "is the required item there?": finding it in the text means the drawing complies

INSTRUCTIONS = (
    "You are a senior piping and facilities engineer checking one engineering drawing of an LNG terminal against the five rules below. "
    "The drawing was read from a PDF by a parser: the text of a schematic comes as one block in no particular order, so match items "
    "(equipment, tags, labels) by their tags and numbers, not by position; a tag that is not next to its equipment still counts, and the parser "
    "may misread a letter as a digit or add a stray character. Report only violations that the text of the drawing itself "
    "shows, and do not report a rule that the drawing does not have an element for (for example a sheet with no exits has nothing to "
    "check for the egress rule). Check every rule that applies, and every item the rule covers. A drawing can have several violations, "
    "including more than one of the same rule, and a compliant drawing has none.\n\n"
    "Be exact rather than eager. Before you report a missing item (an isolation tag, a relief device), search the whole drawing text "
    "for the item that would make the drawing comply. If it appears anywhere in the text, the item is present and there is no violation. "
    "Before you report a number (a flange rating, an exit width, an examination level), compare the two numbers and report only if the "
    "drawing's own figures break the rule. Do not report a doubtful case, a case "
    "you could only suspect, or a case whose explanation says the requirement is met: reporting nothing is correct for a compliant drawing."
)
OUTPUT_FORMAT = (
    "Answer with JSON only: an object with one key, findings, an array with one entry per violation (an empty array when there is none). "
    "Each entry has: expected_item (the tag, label or value whose presence would make the item comply), found_in_text (true if you found "
    "that expected item anywhere in the drawing text, otherwise false), "
    "status (always FAIL), citation (exactly one of the five citations above), severity (critical, high, medium or low), "
    "reason (one or two plain sentences a project manager can read, naming the item and the numbers), page_num (the page the item is on, "
    "counting from 0, as in the page_num comments in the text) and evidence_text (a short verbatim quote, about 3 to 12 words, from the "
    "drawing text that shows the violation)."
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


def _pass(drawing_id, reason="No violation of the five checked rules found."):
    return [_row(drawing_id, f"{drawing_id}-PASS", "PASS", reason)]


def parse_answer(response, error):
    """('review', why) | ('entries', [entry, ...]) for one raw judge answer. An entry is a finding with a recognised citation that is
    not marked PASS, normalised: citation, severity, reason, page_num, evidence_text, plus the judge's expected_item and found_in_text.
    An empty list means the judge found nothing. Never raises."""
    try:
        if error:
            return "review", " ".join(str(error).split())[:200]
        if not isinstance(response, str) or not response.strip():
            return "review", "empty response"
        parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip()))
        found = parsed.get("findings") if isinstance(parsed, dict) else None
        if not isinstance(found, list):
            return "review", "no findings array"
        if not all(isinstance(f, dict) for f in found):
            return "review", "a finding is not an object"
        live = [f for f in found if str(f.get("status", "FAIL")).strip().upper() != "PASS"]
        entries = []
        for f in live:
            citation = normalize_citation(f.get("citation"))
            if citation is None:
                continue
            page = f.get("page_num")
            page = int(page) if isinstance(page, (int, float)) and not isinstance(page, bool) and page >= 0 else 0
            entries.append({"citation": citation, "severity": normalize_severity(f.get("severity")),
                            "reason": _one_line(f.get("reason"), 400) or f"Violation of {citation}.", "page_num": page,
                            "evidence_text": _one_line(f.get("evidence_text"), 120), "expected_item": f.get("expected_item"),
                            "found_in_text": f.get("found_in_text")})
        if live and not entries:
            return "review", "findings cite no rule from the rule set"
        return "entries", entries
    except Exception as e:  # a malformed answer must never fail the run
        return "review", f"{type(e).__name__}: {str(e)[:120]}"


def raw_entries(response, error=None):
    # Every FAIL entry of the judge's answer, before any self-check or guardrail (empty for an answer that is an error or unreadable).
    kind, payload = parse_answer(response, error)
    return payload if kind == "entries" else []


def judge_cleared(entry):
    # The judge's own self-check: it searched the drawing text for the item that would make the drawing comply, and found it. That means
    # compliance only for a rule that asks whether an item is PRESENT (lockout/tagout, relief device). For a threshold rule (flange rating,
    # exit width, weld requirement) the required value is printed in the drawing whether or not the item meets it, so it says nothing.
    return entry.get("found_in_text") is True and entry["citation"] in PRESENCE_RULES


def flatten_judgement(drawing_id, response, error):
    """The rows for one drawing from the judge's raw answer (`response` text, `error` text or None). Never raises.

    * error set, or the answer is not the expected JSON  -> one REVIEW row with a reason.
    * no findings                                        -> one PASS row (citation, page, severity, evidence are None).
    * findings                                           -> one FAIL row per finding with a recognised citation, finding_id
                                                             <drawing_id>-C01, -C02, ..., except that an entry the judge itself cleared
                                                             (judge_cleared) is not a violation; if none of them has a recognised
                                                             citation the drawing gets one REVIEW row instead.
    """
    kind, payload = parse_answer(response, error)
    if kind == "review":
        return _review(drawing_id, payload)
    rows = [e for e in payload if not judge_cleared(e)]
    if not rows:
        return _pass(drawing_id)
    return [_row(drawing_id, f"{drawing_id}-C{n:02d}", "FAIL", e["reason"], e["citation"], e["severity"], e["page_num"], e["evidence_text"])
            for n, e in enumerate(rows, 1)]


# --------------------------------------------------------------------------------------------------
# Guardrails over the saved judge output (no AI call): rule routing and a self-consistency filter
# --------------------------------------------------------------------------------------------------

_FL, _LO, _IB, _WE, _RE = CITATIONS
_YES, _NO = True, False
# drawing_type -> citation -> (applies, one-line engineering rationale). The routing a rule engine does before calling a model.
# DISCLOSURE: this matrix mirrors which items this project's synthetic drawing set depicts on each sheet type, and it equals the synthetic
# generator's sheet-content table (SUPPORTS in 01_synthetic_data/02_generate_drawings.py) in all 25 cells, by design. A real deployment
# would derive it from the project's drawing index and standards. Only the ISO cells ever suppressed anything in the recorded run, so
# "no planted flaw lost to rule_applicability" holds by construction.
APPLICABILITY = {
    "ISO": {
        _FL: (_YES, "An isometric shows one line with its flanged joints and the line's design pressure, so flange ratings can be checked."),
        _LO: (_NO, "An isometric shows pipe, fittings and nozzle tie-ins only; the powered equipment and its isolation tags are on the P&ID and the plan."),
        _IB: (_NO, "Means of egress belongs to building plans; an isometric of a pipe run has no exits."),
        _WE: (_YES, "An isometric carries the weld map: each shop and field weld with its joint type and examination."),
        _RE: (_NO, "Vessels and their relief devices are shown on the P&ID and the relief schedule, not on a single-line isometric."),
    },
    "PID": {
        _FL: (_YES, "A P&ID tags each line with a flange class and design pressure."),
        _LO: (_YES, "Pumps, compressors and their isolation (LOTO) points are drawn on the P&ID."),
        _IB: (_NO, "A process schematic has no building, exits or occupant load."),
        _WE: (_NO, "A P&ID is not to scale and does not show weld joints or examination; those are on isometrics and the piping class spec."),
        _RE: (_YES, "Vessels and the PSVs that protect them, with set pressures, are shown on the P&ID."),
    },
    "GA": {
        _FL: (_NO, "A general arrangement plan locates equipment and rooms; line flange classes are not on it."),
        _LO: (_YES, "This project's general arrangement sheets carry equipment isolation (LOTO) callouts next to the equipment."),
        _IB: (_YES, "The plan with its egress schedule is where exit widths against occupant load are shown."),
        _WE: (_NO, "Weld joints are not shown on an arrangement plan."),
        _RE: (_NO, "Relief devices and their set pressures are on the P&ID and the relief schedule, not on the arrangement plan."),
    },
    "SPEC": {
        _FL: (_YES, "The piping class specification tabulates flange class against design pressure."),
        _LO: (_NO, "A specification sheet has tables only; there is no equipment to isolate."),
        _IB: (_NO, "A piping or relief specification has no exits or occupant load."),
        _WE: (_YES, "The piping class specification states the weld joint type and examination for each class."),
        _RE: (_YES, "This project's piping specification sheets include a relief-device schedule listing each vessel with its PSV."),
    },
    "OTHER": {c: (_NO, "A symbols/legend or typical-detail sheet defines notation; it describes no installed item to check against this rule.") for c in CITATIONS},
}


def applies(drawing_type, citation):
    # Whether `citation` is routed to a drawing of this type. A drawing that cannot be routed (no type) is not suppressed.
    cells = APPLICABILITY.get(drawing_type)
    return True if cells is None else cells[citation][0]


_ADMITS_COMPLIANCE = [  # conservative: phrases with which a judge says, in the same breath as a "violation", that the item is fine
    re.compile(r"\bnot a violation\b", re.I),
    re.compile(r"\b(?:is|are) present in the (?:drawing|text|drawing text)\b", re.I),
    re.compile(r"\bso (?:it|this \w+|the \w+) (?:is|are) (?:protected|compliant|adequate)\b", re.I),
    re.compile(r"\bso this \w+ has its\b", re.I),
    re.compile(r"\b(?:is|are) (?:adequate|compliant)\b", re.I),
    re.compile(r"\b(?:is|are) not powered equipment\b", re.I),
    re.compile(r"\bno violation\b", re.I),
]
_NEGATED = re.compile(r"\b(?:no|not|only|none|without|missing|isn't|aren't)\b", re.I)
_NEEDS_AFFIRMATIVE_SENTENCE = (1, 2, 4)  # indexes in _ADMITS_COMPLIANCE: "X is present", "so it is protected", "is adequate/compliant"


def _admits(reason):
    # The phrase by which the reason's CONCLUSION (its last sentence) admits compliance, or None. Earlier sentences are premises: "A vessel
    # is not powered equipment. Compressor K-1 has no LOTO tag." concludes with a violation. "is present" / "is compliant" phrases do not count
    # in a negated sentence ("No isolation tag is present" states a violation).
    sentences = [x for x in re.split(r"(?<=[.;!?])\s+", reason.strip()) if x]
    if not sentences:
        return None
    last = sentences[-1]
    for k, pattern in enumerate(_ADMITS_COMPLIANCE):
        m = pattern.search(last)
        if m and not (k in _NEEDS_AFFIRMATIVE_SENTENCE and _NEGATED.search(last)):
            return m.group(0)
    return None


def _squash_tag(text):
    return re.sub(r"[^A-Z0-9]", "", str(text).upper().replace("0", "O"))


def contradiction(entry, markdown):
    """Why this FAIL entry contradicts itself or the drawing text, or None. Structured fields first: found_in_text (presence rules only, see
    judge_cleared) and expected_item against the drawing text (a tag, presence rules only); then a vessel check; then, as the fallback,
    conservative phrases in the conclusion of the reason."""
    citation = entry["citation"] if "citation" in entry and entry["citation"] in CITATIONS else normalize_citation(entry.get("citation"))
    presence = citation in PRESENCE_RULES
    if presence and entry.get("found_in_text") is True:
        return "found_in_text is true: the judge's own search found the item that makes the drawing comply (carried over from the judge's self-check)"
    expected = _squash_tag(entry.get("expected_item") or "")
    # only for a tag-like item on a presence rule: a requirement or threshold quoted in the notes is there whether or not the item meets it
    if presence and re.fullmatch(r"[A-Za-z0-9]{2,6}-\d{3,5}[A-Za-z]?", str(entry.get("expected_item") or "").strip()) and expected in _squash_tag(markdown or ""):
        return f"expected_item {str(entry.get('expected_item'))[:60]!r} is in the drawing text although found_in_text is false"
    if citation == _LO and re.match(r"\s*V-\d", str(entry.get("evidence_text") or ""), re.I):
        return "the lockout/tagout rule was applied to a vessel, which the rule itself excludes (vessels are not powered equipment)"
    phrase = _admits(str(entry.get("reason") or ""))
    return f"the reason admits compliance: {phrase!r}" if phrase else None


def judge_with_guardrails(drawing_id, drawing_type, markdown, response, error):
    """(rows, suppressed) for one drawing. `rows` as flatten_judgement (FAIL rows, or one PASS, or one REVIEW), but a FAIL entry is taken
    out when its citation does not apply to the drawing type (suppressed_by 'rule_applicability') or when it contradicts itself
    (suppressed_by 'self_contradiction', which includes the judge's own found_in_text self-check on the presence rules). A drawing whose
    entries are all suppressed gets the PASS row, its reason saying how many were suppressed. Never raises."""
    kind, payload = parse_answer(response, error)
    if kind == "review":
        return _review(drawing_id, payload), []
    kept, suppressed = [], []
    for e in payload:
        if not applies(drawing_type, e["citation"]):
            by, detail = "rule_applicability", f"{e['citation']} does not apply to a {drawing_type} drawing: {APPLICABILITY[drawing_type][e['citation']][1]}"
        else:
            detail = contradiction(e, markdown)
            by = "self_contradiction" if detail else None
        common = dict(drawing_id=drawing_id, status="FAIL", reason=e["reason"], citation=e["citation"], severity=e["severity"],
                      page_num=e["page_num"], evidence_text=e["evidence_text"])
        if by:
            suppressed.append({**common, "finding_id": f"{drawing_id}-S{len(suppressed) + 1:02d}", "suppressed_by": by, "suppression_detail": detail[:400]})
        else:
            kept.append({**common, "finding_id": f"{drawing_id}-C{len(kept) + 1:02d}"})
    if kept:
        return kept, suppressed
    if suppressed:
        return _pass(drawing_id, f"No violation after guardrails ({len(suppressed)} judge {'entry' if len(suppressed) == 1 else 'entries'} suppressed, see compliance_suppressed)."), suppressed
    return _pass(drawing_id), []


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
