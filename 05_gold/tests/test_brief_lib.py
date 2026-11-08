"""Unit tests for the daily-brief grounding validator and prompt builder (brief_lib.py). No AI call, no workspace.

    uv run --no-project --with pytest python -m pytest 05_gold/tests/test_brief_lib.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 05_gold/, where brief_lib.py lives

import brief_lib as bl  # noqa: E402

CONTEXT = {
    "project": "Blue Ridge LNG Terminal, Phase 2",
    "as_of_date": "2026-11-06",
    "kpi": {
        "milestones_hit": 6, "milestones_total": 11, "slipped_milestone_id": "MS-281", "slipped_days": 4,
        "budget_eac_pct": 2.3, "budget_overrun_usd": 4800000.0, "budget_total_usd": 208700000.0,
        "trir_28d": 0.0, "safety_days_without_incident": 28, "open_ncrs": 24,
        "open_ncrs_compliance": 9, "open_ncrs_workmanship": 15,
    },
    "compliance_this_week": {
        "reviewed_drawings": 238, "passed_drawings": 187, "flagged_drawings": 51,
        "top_fail_findings": [
            {"drawing_id": "BRL-INS-PID-0052", "citation": "ASME B31.3 §328", "severity": "critical", "reason": "Weld map missing."},
        ],
        "fail_findings_by_citation": [{"citation": "IBC 1005.1", "fail_findings": 33}],
    },
    "schedule_overdue_top3": [
        {"milestone_id": "MS-281", "name": "Cryogenic Tank T-203 Install Complete", "days_late": 4, "downstream_open_count": 37},
        {"milestone_id": "MS-271", "name": "Install heat exchanger - Main Substation (WP-281)", "days_late": 15, "downstream_open_count": 60},
    ],
    "risk_forecast_top3": [
        {"milestone_id": "MS-335", "name": "Loop check - Train 4", "discipline": "instr", "planned_end": "2026-11-20", "risk_band": "High"},
    ],
}

GOOD = (
    "The project is mostly on track, but MS-281 is already late by 4 days.\n"
    "- **Schedule**: 6 of 11 key milestones hit; MS-281 is already late by 4 days and MS-271 by 15 days.\n"
    "- **Budget**: EAC is up 2.3%, about $4.8M over a $208.7M budget.\n"
    "- **Safety**: 28 days without an incident and a TRIR of 0.\n"
    "- **Compliance**: 51 of 238 drawings flagged for engineer review this week, including BRL-INS-PID-0052.\n"
    "- **Risk**: MS-335 is High risk.\n"
    "Want me to dig into MS-281?"
)


def check(text, ctx=CONTEXT):
    return bl.validate_brief(text, ctx)


def test_grounded_brief_passes():
    ok, failures = check(GOOD)
    assert ok and failures == []


def test_invented_number_fails():
    ok, failures = check(GOOD.replace("28 days", "31 days"))
    assert not ok and any("31" in f for f in failures)


def test_invented_milestone_fails():
    ok, failures = check(GOOD.replace("MS-335", "MS-999"))
    assert not ok and any("MS-999" in f for f in failures)


def test_invented_drawing_fails():
    ok, failures = check(GOOD.replace("BRL-INS-PID-0052", "BRL-INS-PID-0099"))
    assert not ok and any("BRL-INS-PID-0099" in f for f in failures)


def test_probability_percentage_fails():
    ok, failures = check(GOOD.replace("MS-335 is High risk.", "MS-335 has a 72% chance of slipping."))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_percent_next_to_risk_fails_even_if_number_is_grounded():
    # 2.3 is a grounded number, but a percentage beside risk wording is still a probability claim
    ok, failures = check(GOOD.replace("MS-335 is High risk.", "MS-335 is High risk at 2.3%."))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_probability_word_fails():
    ok, failures = check(GOOD.replace("is High risk", "has a high probability of slipping"))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_budget_percent_passes():
    ok, failures = check("Budget is +2.3% over EAC. Want me to dig in?")
    assert ok, failures


def test_money_normalization_passes():
    for text in ("About $4.8M over budget.", "About $4.8 million over budget.", "Overrun is $4,800,000.", "Total budget is $208.7M.",
                 "Total budget is $208.7 million."):
        ok, failures = check(text)
        assert ok, (text, failures)


def test_wrong_money_fails():
    ok, failures = check("About $5.9M over budget.")
    assert not ok and any("5.9" in f for f in failures)


def test_integers_are_exact():
    ok, failures = check("51 of 239 drawings flagged.")
    assert not ok and any("239" in f for f in failures)


def test_id_digits_are_not_checked_as_numbers():
    # 281 / 0052 only appear inside IDs that exist in the context, so they are not stray numbers
    ok, failures = check("MS-281 and BRL-INS-PID-0052 need attention.")
    assert ok, failures


def test_list_markers_and_ordinals_are_exempt():
    ok, failures = check("1. First point\n2. Second point\nOn the 1st of the month, the 2nd review ran.")
    assert ok, failures


def test_over_length_fails():
    ok, failures = check("word " * 151)
    assert not ok and any("word" in f.lower() and "151" in f for f in failures)


def test_150_words_is_the_limit():
    ok, failures = check("word " * 150)
    assert ok, failures


def test_prompt_contains_rules_and_context_and_no_probability():
    p = bl.build_brief_prompt(CONTEXT)
    assert "CONTEXT" in p and json.dumps(CONTEXT, indent=2, sort_keys=True) in p
    for must in ("Use only facts", "already late", "High risk", "flagged for engineer review", "130 words", "schedule_overdue_total"):
        assert must in p, must
    assert "slip_probability" not in p


def test_retry_prompt_appends_failures():
    p = bl.build_retry_prompt(CONTEXT, "DRAFT TEXT", ["number 31 not in CONTEXT"])
    assert "Your previous draft failed these checks" in p and "number 31 not in CONTEXT" in p and "DRAFT TEXT" in p
    assert p.startswith(bl.build_brief_prompt(CONTEXT))
