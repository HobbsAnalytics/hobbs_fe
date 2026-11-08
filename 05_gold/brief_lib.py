"""Pure-Python helpers for the Daily Brief narrator (03_daily_brief.ipynb): the prompt and the grounding validator.

No Spark, no AI call, no workspace, so everything here is unit-tested locally:

    uv run --no-project --with pytest python -m pytest 05_gold/tests/test_brief_lib.py -v

The validator is the "is this brief grounded?" check. It reads the brief and the CONTEXT payload the model was given and
fails the brief if it contains a number or ID that is not in the context, a probability claim, or too many words.
Beyond "is the number in the context" it also checks, deterministically: that a number next to late / overdue / behind is
the already-late count, that a number next to High / Medium / Low risk is that band's total, that the five bullet labels
appear once each as list items, and that Risk, Schedule and Compliance bullets hold the right content.
It does not judge paraphrase semantics (whether a sentence uses a true fact sensibly) and it does not read spelled-out
numbers ("six"); the prompt asks for digits. A human read of the final brief covers what these checks cannot.
"""
import json
import re

PROMPT_VERSION = "v3"   # v1 -> v2 -> v3, each a disclosed revision after human review found a factual error; see the prompt history in daily_brief_today.md
MAX_WORDS = 150          # the validator's hard limit; the prompt asks for about 130
PROMPT_WORDS = 130

MS_ID = re.compile(r"\bMS-\d+\b")
DRAWING_ID = re.compile(r"\bBRL-[A-Z]+-[A-Z]+-\d+\b")

# One number as written in prose: optional $, digits with optional thousands commas and decimals, optional unit.
NUMBER = re.compile(r"(?P<dollar>\$)?(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<frac>\.\d+)?\s*(?P<unit>%|million\b|billion\b|thousand\b|[MBK]\b)?")
SCALE = {"m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9, "k": 1e3, "thousand": 1e3}

# Exemptions, each deliberate:
#  1. milestone / drawing IDs: their digits are checked as IDs, not as numbers;
#  2. list markers at the start of a line ("1. ", "2) "): formatting, not facts;
#  3. ordinals ("1st", "2nd", "3rd", "4th"): wording, not facts.
LIST_MARKER = re.compile(r"(?m)^\s*\d+[.)]\s")
ORDINAL = re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.I)

# A percentage within this many characters of risk / probability wording is a probability claim.
RISK_WORDS = re.compile(r"risk|probab|chance|likel|odds|confiden", re.I)
PROB_PHRASES = re.compile(r"probabilit|\bchances? of\b|\blikelihood\b|\bodds\b|\bpercent (?:chance|likely)\b", re.I)
PROXIMITY = 40


def _strip_ids(text):
    return DRAWING_ID.sub(" ", MS_ID.sub(" ", text))


def _parse(m):
    """(value, scale_factor, decimals_shown, is_percent) for a NUMBER match."""
    int_part = m.group("int").replace(",", "")
    frac = m.group("frac") or ""
    unit = (m.group("unit") or "").lower()
    value = float(int_part + frac)
    scale = SCALE.get(unit, 1.0)
    return value * scale, scale, len(frac) - 1 if frac else 0, unit == "%"


def _context_numbers(node, out):
    if isinstance(node, bool) or node is None:
        return
    if isinstance(node, (int, float)):
        out.add(float(node))
    elif isinstance(node, str):
        for m in NUMBER.finditer(_strip_ids(node)):
            out.add(_parse(m)[0])
    elif isinstance(node, dict):
        for v in node.values():
            _context_numbers(v, out)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _context_numbers(v, out)


def _context_ids(context):
    text = json.dumps(context)
    return set(MS_ID.findall(text)), set(DRAWING_ID.findall(text))


def _number_ok(value, scale, decimals, dollar, allowed):
    if scale > 1:    # "$4.8M": correct to the precision shown, i.e. within half a unit of the last digit written
        tol = 0.5 * 10 ** (-decimals) * scale
    elif dollar or value >= 1000:   # "$4,800,000": small relative tolerance for rounded money
        tol = 0.005 * value
    else:            # plain integers and decimals ("28", "2.3"): exact
        tol = 1e-9
    return any(abs(value - a) <= tol for a in allowed)


LABELS = ("Schedule", "Budget", "Safety", "Compliance", "Risk")
LABEL_LINE = re.compile(r"^\s*(?P<marker>[-*]\s+)?\*\*(?P<label>[A-Za-z]+):?\*\*:?\s*(?P<text>.*)$")
TIME_PHRASES = re.compile(r"\b(?:this period|last week|last month|next week|this month|this quarter|yesterday|recently|lately|"
                          r"January|February|March|April|June|July|August|September|October|November|December)\b")
GENERALISATION = re.compile(r"\b(?:primarily|mainly|mostly|largely|predominantly|typically|generally)\b", re.I)

# Words that follow a number when it counts something other than milestones ("15 days late", "60 downstream tasks").
UNIT_WORDS = {"day", "days", "week", "weeks", "hour", "hours", "downstream", "task", "tasks", "drawing", "drawings", "finding", "findings",
              "ncr", "ncrs", "dependency", "dependencies"}
LATE_AFTER = re.compile(r"(?<![\d.$,])(\d+)(?![\d.]*\d)\s+((?:[\w'-]+\s+){0,3}?)(late|overdue|behind)\b", re.I)
LATE_BEFORE = re.compile(r"\b(late|overdue|behind)\s*(?:milestones?)?\s*[:(=]\s*(\d+)\b", re.I)
BAND_AFTER = re.compile(r"(?<![\d.$,])(\d+)(?![\d.]*\d)\s+((?:[\w'-]+\s+){0,4}?)(High|Medium|Low)[\s-]*(?:risk|band)", re.I)
BAND_BEFORE = re.compile(r"\b(High|Medium|Low)[\s-]*(?:risk|band)s?\s*(?:milestones?\s*)?[:(=]\s*(\d+)\b", re.I)
BAND_KEY = {"high": "risk_high_total", "medium": "risk_medium_total", "low": "risk_low_total"}


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?;])\s+|\n", text) if s.strip()]


def _clean_for_counts(text):
    text = _strip_ids(text)
    return re.sub(r"\([\s,]*(?:and\s*)?[\s,]*\)", " ", text)   # parentheses emptied by removing IDs


def _parse_sections(brief_md):
    """({label: bullet text}, failures). A bullet is the single line that starts with its bold label."""
    found, failures, sections = [], [], {}
    for line in brief_md.splitlines():
        m = LABEL_LINE.match(line)
        if not m:
            continue
        label = m.group("label")
        found.append(label)
        if not m.group("marker"):
            failures.append(f"label {label} is not a Markdown list item (start the line with '- ')")
        sections.setdefault(label, m.group("text"))
    for label in LABELS:
        n = found.count(label)
        if n == 0:
            failures.append(f"section {label} is missing")
        elif n > 1:
            failures.append(f"label {label} appears more than once")
    for label in dict.fromkeys(found):
        if label not in LABELS:
            failures.append(f"unexpected label {label}; use exactly {', '.join(LABELS)}")
    return sections, failures


def _has_number(text, n):
    return any(abs(_parse(m)[0] - n) < 1e-9 for m in NUMBER.finditer(_strip_ids(text)))


def _section_content_failures(sections, context):
    out = []
    if "Risk" in sections:
        if not re.search(r"\b(?:High|Medium|Low)\b", sections["Risk"], re.I):
            out.append("Risk bullet must name a risk band (High, Medium or Low)")
        if re.search(r"\bNCRs?\b|non-?conformance", sections["Risk"], re.I):
            out.append("Risk bullet mentions NCRs; NCRs belong in the Compliance bullet")
    late = context.get("schedule_already_late")
    if "Schedule" in sections and late is not None and not _has_number(sections["Schedule"], late):
        out.append(f"Schedule bullet must state the already-late count ({late})")
    comp = context.get("compliance_this_week", {})
    flagged, reviewed = comp.get("flagged_drawings"), comp.get("reviewed_drawings")
    if "Compliance" in sections and flagged is not None and reviewed is not None:
        t = sections["Compliance"]
        if not (_has_number(t, flagged) and _has_number(t, reviewed) and re.search(r"flagged", t, re.I) and re.search(r"engineer review", t, re.I)):
            out.append(f"Compliance bullet must state the triage line '{flagged} of {reviewed} drawings flagged for engineer review this week'")
    return out


def _count_adjacency_failures(brief_md, context):
    out = []
    late, total, today = (context.get(k) for k in ("schedule_already_late", "schedule_overdue_total", "schedule_due_today"))
    for sent in _sentences(brief_md):
        text = _clean_for_counts(sent)
        claims = []   # (value, word)
        for m in LATE_AFTER.finditer(text):
            first = (m.group(2).split() or [""])[0].lower()
            if first in UNIT_WORDS or re.search(r"\btop\s+$", text[:m.start(1)], re.I):
                continue
            claims.append((int(m.group(1)), m.group(3).lower()))
        claims += [(int(m.group(2)), m.group(1).lower()) for m in LATE_BEFORE.finditer(text)]
        for v, word in claims:
            if late is None or v == late:
                continue
            states_today = today is not None and re.search(r"due today", text, re.I) and _has_number(text, today)
            if total is not None and v == total and states_today:
                continue
            out.append(f"count {v} next to '{word}' must be the already-late count {late} "
                       f"(or the overdue total {total} only if the same sentence also gives the {today} due today): '{' '.join(sent.split())}'")
    for sent in _sentences(brief_md):
        text = _clean_for_counts(sent)
        claims = []   # (value, band)
        for m in BAND_AFTER.finditer(text):
            words = m.group(2).lower().split()
            if (words and words[0] in UNIT_WORDS) or any(w in ("late", "overdue", "behind") for w in words) or re.search(r"\btop\s+$", text[:m.start(1)], re.I):
                continue
            claims.append((int(m.group(1)), m.group(3).lower()))
        claims += [(int(m.group(2)), m.group(1).lower()) for m in BAND_BEFORE.finditer(text)]
        for v, band in claims:
            want = context.get(BAND_KEY[band])
            if want is not None and v != want:
                out.append(f"count {v} next to '{band.capitalize()} risk' must be {BAND_KEY[band]} = {want} "
                           f"(name the top ones as 'the top {context.get('top_n_listed', 3)} are ...' instead of counting the list): '{' '.join(sent.split())}'")
    return out


def validate_brief(brief_md, context):
    """Return (ok, failures). Checks: numbers, IDs, no probabilities, length."""
    failures = []

    # --- IDs: every milestone / drawing ID in the brief must exist in the context
    ms_ctx, dr_ctx = _context_ids(context)
    for found, known, kind in ((MS_ID.findall(brief_md), ms_ctx, "milestone"), (DRAWING_ID.findall(brief_md), dr_ctx, "drawing")):
        for i in dict.fromkeys(found):
            if i not in known:
                failures.append(f"{kind} ID {i} is not in CONTEXT")

    # --- numbers: after removing IDs, list markers and ordinals, each must match a number in the context
    allowed = set()
    _context_numbers(context, allowed)
    body = ORDINAL.sub(" ", LIST_MARKER.sub(" ", _strip_ids(brief_md)))
    for m in NUMBER.finditer(body):
        value, scale, decimals, _ = _parse(m)
        if not _number_ok(value, scale, decimals, bool(m.group("dollar")), allowed):
            failures.append(f"number {m.group(0).strip()} is not in CONTEXT")

    # --- no probabilities: no percentage near risk wording, and no probability phrasing
    for m in NUMBER.finditer(body):
        if m.group("unit") == "%":
            window = body[max(0, m.start() - PROXIMITY): m.end() + PROXIMITY]
            if RISK_WORDS.search(window):
                failures.append(f"probability claim: percentage {m.group(0).strip()} next to risk wording ('{' '.join(window.split())}'); use the risk band")
    for m in PROB_PHRASES.finditer(brief_md):
        failures.append(f"probability phrasing '{m.group(0)}'; describe risk by band only")

    # --- bullet labels: exactly the five labels, each once, each a Markdown list item
    sections, label_failures = _parse_sections(brief_md)
    failures += label_failures
    failures += _section_content_failures(sections, context)

    # --- counts next to late / overdue / behind and next to a risk band must be the context's totals
    failures += _count_adjacency_failures(brief_md, context)

    # --- time phrases and generalisations the context does not support
    ctx_text = json.dumps(context).lower()
    for m in TIME_PHRASES.finditer(brief_md):
        if m.group(0).lower() not in ctx_text:
            failures.append(f"time phrase '{m.group(0)}' is not in CONTEXT; say 'this week' or use the dates given")
    for m in GENERALISATION.finditer(brief_md):
        failures.append(f"generalisation word '{m.group(0)}'; describe compliance findings by citation counts only")

    # --- length
    words = len(brief_md.split())
    if words > MAX_WORDS:
        failures.append(f"too long: {words} words (limit {MAX_WORDS})")

    return (not failures, failures)


def build_brief_prompt(context):
    """The full prompt for the Daily Brief (prompt_version v3): rules, shape, then the CONTEXT as JSON."""
    al, dt_, ot = context.get("schedule_already_late", "N"), context.get("schedule_due_today", "N"), context.get("schedule_overdue_total", "N")
    rh, rm, rl = (context.get(k, "N") for k in ("risk_high_total", "risk_medium_total", "risk_low_total"))
    n, win = context.get("top_n_listed", 3), context.get("risk_forecast_window_days", 90)
    return f"""You are the project manager's co-pilot on the Blue Ridge LNG Terminal, Phase 2 build. Write today's Daily Brief for the project manager from the CONTEXT below.

GROUNDING RULES
- Use only facts in the CONTEXT. Never invent milestones, drawings, people, dates or causes.
- Reproduce numbers exactly as given, as digits. Rounding to the precision shown is fine (for example $4.8M). Do not calculate new numbers (no percentages of your own, no sums, no differences).
- Use no time phrases that are not in the CONTEXT: no "this period", "last week", no month names. "This week" is fine for compliance.
- Describe schedule risk only by its band ("High risk", "Medium risk"). Never write a percentage, probability, chance or likelihood for risk.
- Frame compliance as triage: "N of M drawings flagged for engineer review this week". Do not say the drawings are non-compliant or failed.
- Characterize compliance findings by citation counts only (fail_findings_by_citation). Never generalize from the sample reasons in top_fail_findings: do not say "primarily", "mostly" or name a common cause.
- Late milestones. Say "{al} milestones are already late and {dt_} due today". Do not use {ot} (schedule_overdue_total) as the late count, because it includes the milestone due today. schedule_overdue_top3 shows only the worst {n}: you may name them with their own days late (for example "MS-271 is already late by 15 days"), but never use the length of that list as a count.
- Risk milestones. If you mention how many milestones are High risk, use {rh} (Medium {rm}, Low {rl}); these count open milestones due in the next {win} days. You may name the top ones as "the top {n} are ...", using only milestones listed under risk_forecast_top3.
- Open NCRs go in the Compliance bullet, never in the Risk bullet.
- Refer to milestones and drawings by their IDs exactly as written (for example MS-281).

SHAPE
- One opening sentence on overall status.
- Then exactly five bullets, in this order, each a real Markdown list item starting with "- " and a bold label with a colon inside the bold: "- **Schedule:** ...", "- **Budget:** ...", "- **Safety:** ...", "- **Compliance:** ...", "- **Risk:** ...".
  - Schedule: the late phrasing above, plus the worst late milestone.
  - Budget: the overrun and total budget.
  - Safety: days without an incident and the 28-day TRIR.
  - Compliance: the triage line, the lead citation by count, and the open NCRs if you mention them.
  - Risk: milestones by risk band only (the High count above and the top ones named).
- Then one closing question offering to dig in.
- At most {PROMPT_WORDS} words in total. Plain business tone for a project manager. No headings, no preamble.

CONTEXT (JSON)
{json.dumps(context, indent=2, sort_keys=True)}
"""


def build_retry_prompt(context, previous_draft, failures):
    """The original prompt plus the failed checks, for the single retry."""
    listed = "\n".join(f"- {f}" for f in failures)
    return (
        build_brief_prompt(context)
        + f"\nYour previous draft failed these checks:\n{listed}\n\nPREVIOUS DRAFT\n{previous_draft}\n\n"
        "Rewrite the brief using only CONTEXT facts and fix every failed check. Keep the same shape and the same word limit."
    )


def grounding_table(brief_md, context):
    """Programmatic trace for the human-read table: one row per bullet claim token (number or ID) with the context paths that hold it."""
    paths = []   # (path, number, from_text)

    def walk(node, path):
        if isinstance(node, bool) or node is None:
            return
        if isinstance(node, (int, float)):
            paths.append((path, float(node), False))
        elif isinstance(node, str):
            for m in NUMBER.finditer(_strip_ids(node)):
                paths.append((path, _parse(m)[0], True))
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(context, "")
    id_paths = {}
    def walk_ids(node, path):
        if isinstance(node, str):
            for i in MS_ID.findall(node) + DRAWING_ID.findall(node):
                id_paths.setdefault(i, path)
        elif isinstance(node, dict):
            for k, v in node.items():
                walk_ids(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk_ids(v, f"{path}[{i}]")
    walk_ids(context, "")

    rows, section = [], "Opening"
    for line in brief_md.splitlines():
        if not line.strip():
            continue
        m = LABEL_LINE.match(line)
        if m:
            section = m.group("label")
        elif section == "Risk" or (section != "Opening" and not line.lstrip().startswith(("-", "*"))):
            section = "Closing"
        body = _strip_ids(ORDINAL.sub(" ", LIST_MARKER.sub(" ", line)))
        line_words = set(re.findall(r"[a-z]+", line.lower()))
        for i in dict.fromkeys(MS_ID.findall(line) + DRAWING_ID.findall(line)):
            rows.append({"section": section, "claim": i, "context_path": id_paths.get(i, "NOT FOUND")})
        for nm in NUMBER.finditer(body):
            value, scale, decimals, _ = _parse(nm)
            hits = [(p, txt) for p, a, txt in paths if _number_ok(value, scale, decimals, bool(nm.group("dollar")), {a})]
            # several context values can equal the same number; rank by how many words of the bullet appear in the path's field names
            # (days_late for "15 days late"), numeric fields before numbers inside text. Up to two are shown, so ambiguity stays visible.
            def rank(h):
                toks = set(re.findall(r"[a-z]+", re.sub(r"\[\d+\]", "", h[0]).lower()))
                return (-len(toks & line_words), h[1])
            hits.sort(key=rank)
            shown = [p + (" (inside text)" if txt else "") for p, txt in dict.fromkeys(hits)][:2]
            rows.append({"section": section, "claim": nm.group(0).strip(), "context_path": ", ".join(shown) or "NOT FOUND"})
    return rows
