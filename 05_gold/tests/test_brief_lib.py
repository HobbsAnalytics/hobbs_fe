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
    "schedule_overdue_total": 7, "schedule_already_late": 6, "schedule_due_today": 1,
    "risk_high_total": 5, "risk_medium_total": 3, "risk_low_total": 40, "risk_forecast_window_days": 90, "top_n_listed": 3,
    "schedule_overdue_top3": [
        {"milestone_id": "MS-281", "name": "Cryogenic Tank T-203 Install Complete", "days_late": 4, "downstream_open_count": 37},
        {"milestone_id": "MS-271", "name": "Install heat exchanger - Main Substation (WP-281)", "days_late": 15, "downstream_open_count": 60},
    ],
    "risk_forecast_top3": [
        {"milestone_id": "MS-335", "name": "Loop check - Train 4", "discipline": "instr", "planned_end": "2026-11-20", "risk_band": "High"},
        {"milestone_id": "MS-351", "name": "Loop check - Tank T-203", "discipline": "instr", "planned_end": "2026-11-21", "risk_band": "High"},
        {"milestone_id": "MS-352", "name": "Calibrate transmitters - Jetty 2", "discipline": "instr", "planned_end": "2026-11-22", "risk_band": "High"},
    ],
}

SECTIONS = {
    "Schedule": "6 milestones are already late and 1 is due today; MS-281 is already late by 4 days and MS-271 by 15 days.",
    "Budget": "EAC is up 2.3%, about $4.8M over a $208.7M budget.",
    "Safety": "28 days without an incident and a TRIR of 0.",
    "Compliance": "51 of 238 drawings flagged for engineer review this week, including BRL-INS-PID-0052; 24 open NCRs, 9 compliance-related.",
    "Risk": "5 milestones are High risk; the top 3 are MS-335 and others on the list.",
}
OPENER = "The project is on track overall, but MS-281 is already late by 4 days."
CLOSER = "Want me to dig into MS-281?"


def mk(opener=OPENER, closer=CLOSER, **over):
    """Build a brief in the required shape; over= replaces a section's text, or drops it when the value is None."""
    secs = {**SECTIONS, **over}
    bullets = [f"- **{k}:** {v}" for k, v in secs.items() if v is not None]
    return "\n".join([opener, *bullets, closer])


GOOD = mk()


def check(text, ctx=CONTEXT):
    return bl.validate_brief(text, ctx)


def test_grounded_brief_passes():
    ok, failures = check(GOOD)
    assert ok and failures == []


def test_invented_number_fails():
    ok, failures = check(mk(Safety="31 days without an incident and a TRIR of 0."))
    assert not ok and any("31" in f for f in failures)


def test_invented_milestone_fails():
    ok, failures = check(mk(Risk="5 milestones are High risk; the top one is MS-999."))
    assert not ok and any("MS-999" in f for f in failures)


def test_invented_drawing_fails():
    ok, failures = check(mk(Compliance="51 of 238 drawings flagged for engineer review this week, including BRL-INS-PID-0099."))
    assert not ok and any("BRL-INS-PID-0099" in f for f in failures)


def test_probability_percentage_fails():
    ok, failures = check(mk(Risk="5 milestones are High risk, MS-335 has a 72% chance of slipping."))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_percent_next_to_risk_fails_even_if_number_is_grounded():
    # 2.3 is a grounded number, but a percentage beside risk wording is still a probability claim
    ok, failures = check(mk(Risk="5 milestones are High risk at 2.3%."))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_probability_word_fails():
    ok, failures = check(mk(Risk="5 milestones are High risk with a high probability of slipping."))
    assert not ok and any("probab" in f.lower() for f in failures)


def test_budget_percent_passes():
    ok, failures = check(mk(Budget="EAC is +2.3% over budget."))
    assert ok, failures


def test_money_normalization_passes():
    for text in ("About $4.8M over budget.", "About $4.8 million over budget.", "Overrun is $4,800,000.", "Total budget is $208.7M.",
                 "Total budget is $208.7 million."):
        ok, failures = check(mk(Budget=text))
        assert ok, (text, failures)


def test_wrong_money_fails():
    ok, failures = check(mk(Budget="About $5.9M over budget."))
    assert not ok and any("5.9" in f for f in failures)


def test_integers_are_exact():
    ok, failures = check(mk(Compliance="51 of 239 drawings flagged for engineer review this week."))
    assert not ok and any("239" in f for f in failures)


def test_id_digits_are_not_checked_as_numbers():
    # 281 / 0052 only appear inside IDs that exist in the context, so they are not stray numbers
    ok, failures = check(mk(Safety="28 days without an incident; MS-281 and BRL-INS-PID-0052 need attention."))
    assert ok, failures


def test_list_markers_and_ordinals_are_exempt():
    ok, failures = check(mk(Safety="28 days without an incident.\n1. First point\n2. Second point\nOn the 1st of the month, the 2nd review ran."))
    assert ok, failures


def test_over_length_fails():
    ok, failures = check(mk(Safety="28 days without an incident. " + "word " * 151))
    assert not ok and any("too long" in f and "words" in f for f in failures)


def test_150_words_is_the_limit():
    base = len(mk().split())
    ok, failures = check(mk(Safety="28 days without an incident. " + "word " * (150 - base)))
    assert ok, failures


# ---- fix round 1: count adjacency, section content, labels, time phrases ----

def test_seven_already_late_fails_when_context_is_six_plus_one():
    ok, failures = check(mk(Schedule="7 milestones are already late; MS-281 is already late by 4 days."))
    assert not ok and any("late" in f and "7" in f for f in failures)


def test_seven_overdue_fails():
    ok, failures = check(mk(opener="The project is on track, though 7 milestones are now overdue."))
    assert not ok and any("overdue" in f and "7" in f for f in failures)


def test_six_already_late_and_one_due_today_passes():
    ok, failures = check(mk(Schedule="6 already late and 1 due today; MS-271 is already late by 15 days."))
    assert ok, failures


def test_seven_late_passes_only_if_same_sentence_states_due_today_count():
    ok, failures = check(mk(Schedule="7 milestones are overdue: 6 already late and 1 due today."))
    assert ok, failures


def test_day_counts_next_to_late_are_not_milestone_counts():
    ok, failures = check(mk(Schedule="6 milestones are already late and 1 is due today; MS-271 is 15 days late with 60 downstream tasks open."))
    assert ok, failures


def test_three_high_risk_fails_when_context_has_five():
    ok, failures = check(mk(Risk="3 milestones are High risk: MS-335 and others."))
    assert not ok and any("High" in f and "3" in f for f in failures)


def test_five_high_risk_and_top_three_phrase_passes():
    ok, failures = check(mk(Risk="5 milestones are High risk; the top 3 are MS-335, MS-351 and MS-352."))
    assert ok, failures


def test_risk_bullet_with_ncr_fails():
    ok, failures = check(mk(Risk="5 milestones are High risk, and 24 open NCRs."))
    assert not ok and any("Risk" in f and "NCR" in f for f in failures)


def test_risk_bullet_without_band_fails():
    ok, failures = check(mk(Risk="MS-335 is a concern for the project."))
    assert not ok and any("Risk" in f and "band" in f for f in failures)


def test_missing_label_fails():
    ok, failures = check(mk(Safety=None))
    assert not ok and any("Safety" in f and "missing" in f for f in failures)


def test_duplicate_label_fails():
    ok, failures = check(GOOD + "\n- **Budget:** EAC is up 2.3%.")
    assert not ok and any("Budget" in f and "more than once" in f for f in failures)


def test_label_not_a_list_item_fails():
    ok, failures = check(GOOD.replace("- **Budget:**", "**Budget:**"))
    assert not ok and any("Budget" in f and "list item" in f for f in failures)


def test_schedule_bullet_without_late_count_fails():
    ok, failures = check(mk(Schedule="MS-281 is already late by 4 days."))
    assert not ok and any("Schedule" in f and "6" in f for f in failures)


def test_compliance_bullet_without_triage_line_fails():
    ok, failures = check(mk(Compliance="Several drawings need a look."))
    assert not ok and any("Compliance" in f for f in failures)


def test_time_phrase_not_in_context_fails():
    for phrase in ("slipped this period", "due through January"):
        ok, failures = check(mk(Schedule=f"6 milestones are already late and 1 is due today; MS-281 {phrase}."))
        assert not ok and any("time phrase" in f for f in failures), phrase


def test_generalization_words_fail():
    ok, failures = check(mk(Compliance="51 of 238 drawings flagged for engineer review this week, primarily pressure relief issues."))
    assert not ok and any("primarily" in f for f in failures)


def test_prompt_contains_rules_and_context_and_no_probability():
    p = bl.build_brief_prompt(CONTEXT)
    assert "CONTEXT" in p and json.dumps(CONTEXT, indent=2, sort_keys=True) in p
    for must in ("Use only facts", "already late", "High risk", "flagged for engineer review", "130 words", "schedule_overdue_total"):
        assert must in p, must
    assert "slip_probability" not in p
    # v3: exact required phrasings, filled from the context
    assert "6 milestones are already late and 1 due today" in p and "use 5" in p and "citation counts only" in p


def test_retry_prompt_appends_failures():
    p = bl.build_retry_prompt(CONTEXT, "DRAFT TEXT", ["number 31 not in CONTEXT"])
    assert "Your previous draft failed these checks" in p and "number 31 not in CONTEXT" in p and "DRAFT TEXT" in p
    assert p.startswith(bl.build_brief_prompt(CONTEXT))


def test_grounding_table_traces_every_claim_and_prefers_matching_field():
    rows = bl.grounding_table(GOOD, CONTEXT)
    assert rows and all(r["context_path"] != "NOT FOUND" for r in rows)
    late = [r for r in rows if r["claim"] == "6" and r["section"] == "Schedule"][0]
    assert late["context_path"].split(",")[0] == "schedule_already_late"
