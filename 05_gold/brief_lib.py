"""Pure-Python helpers for the Daily Brief narrator (03_daily_brief.ipynb): the prompt and the grounding validator.

No Spark, no AI call, no workspace, so everything here is unit-tested locally:

    uv run --no-project --with pytest python -m pytest 05_gold/tests/test_brief_lib.py -v

The validator is the "is this brief grounded?" check. It reads the brief and the CONTEXT payload the model was given and
fails the brief if it contains a number or ID that is not in the context, a probability claim, or too many words.
It checks that the facts are present in the context; it does not check that a sentence uses them sensibly, and it does
not read spelled-out numbers ("six"). The prompt asks for digits.
"""
import json
import re

PROMPT_VERSION = "v2"   # v1 -> v2: added the overdue totals rule after the first run said "three milestones are late" when 6 were (context only had the top 3)
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

    # --- length
    words = len(brief_md.split())
    if words > MAX_WORDS:
        failures.append(f"too long: {words} words (limit {MAX_WORDS})")

    return (not failures, failures)


def build_brief_prompt(context):
    """The full prompt for the Daily Brief (prompt_version v2): rules, shape, then the CONTEXT as JSON."""
    return f"""You are the project manager's co-pilot on the Blue Ridge LNG Terminal, Phase 2 build. Write today's Daily Brief for the project manager from the CONTEXT below.

GROUNDING RULES
- Use only facts in the CONTEXT. Never invent milestones, drawings, people, dates or causes.
- Reproduce numbers exactly as given, as digits. Rounding to the precision shown is fine (for example $4.8M). Do not calculate new numbers (no percentages of your own, no sums, no differences).
- Describe schedule risk only by its band ("High risk", "Medium risk"). Never write a percentage, probability, chance or likelihood for risk.
- Frame compliance as triage: "N of M drawings flagged for engineer review this week". Do not say the drawings are non-compliant or failed.
- Milestones listed under schedule_overdue_top3 are already late: say "already late". schedule_overdue_top3 shows only the worst three; when you say how many milestones are late or overdue, use the totals (schedule_overdue_total, schedule_already_late, schedule_due_today), never the length of that list.
- Refer to milestones and drawings by their IDs exactly as written (for example MS-281).

SHAPE
- One opening sentence on overall status.
- Then 4 to 5 short Markdown bullets, each starting with a bold label: **Schedule**, **Budget**, **Safety**, **Compliance**, **Risk**.
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
