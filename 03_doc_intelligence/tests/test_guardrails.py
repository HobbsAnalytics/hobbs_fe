"""Unit tests for the zero-cost guardrails on the saved judge output (compliance_lib.judge_with_guardrails). No AI call, no workspace.

    pytest 03_doc_intelligence/tests/test_guardrails.py -v
"""
import json

import pytest

import compliance_lib as lib

FLANGE, LOTO, IBC, WELD, RELIEF = lib.CITATIONS


def entry(**over):
    base = {"expected_item": "X", "found_in_text": False, "status": "FAIL", "citation": LOTO, "severity": "high",
            "reason": "Pump P-2104A has no LOTO tag.", "page_num": 0, "evidence_text": "P-2104A"}
    base.update(over)
    return base


def run(drawing_type, *entries, markdown="NOTHING RELEVANT"):
    return lib.judge_with_guardrails("D1", drawing_type, markdown, json.dumps({"findings": list(entries)}), None)


# ---- the applicability matrix
def test_matrix_covers_every_type_and_citation_with_a_rationale():
    assert set(lib.APPLICABILITY) == {"ISO", "PID", "GA", "SPEC", "OTHER"}
    for dtype, cells in lib.APPLICABILITY.items():
        assert set(cells) == set(lib.CITATIONS), dtype
        for citation, (applies, why) in cells.items():
            assert isinstance(applies, bool) and len(why) > 15, (dtype, citation)


def test_matrix_routes_the_obvious_cases():
    assert not lib.applies("ISO", LOTO) and not lib.applies("ISO", IBC) and not lib.applies("ISO", RELIEF)
    assert lib.applies("ISO", FLANGE) and lib.applies("ISO", WELD)
    assert lib.applies("PID", LOTO) and lib.applies("PID", RELIEF) and not lib.applies("PID", IBC)
    assert lib.applies("GA", IBC) and not lib.applies("GA", FLANGE)
    assert not any(lib.applies("OTHER", c) for c in lib.CITATIONS)
    assert lib.applies(None, LOTO) and lib.applies("unknown", IBC)  # a drawing that cannot be routed is not suppressed


def test_not_applicable_entry_is_suppressed_and_drawing_passes():
    rows, suppressed = run("ISO", entry(citation=LOTO), entry(citation=RELIEF, evidence_text="V-1083"))
    assert [r["status"] for r in rows] == ["PASS"] and rows[0]["citation"] is None
    assert [s["suppressed_by"] for s in suppressed] == ["rule_applicability"] * 2
    assert all(s["suppression_detail"] and s["citation"] and s["drawing_id"] == "D1" for s in suppressed)


def test_mixed_keeps_applicable_fail_with_renumbered_ids():
    rows, suppressed = run("PID", entry(citation=IBC, evidence_text="EXIT 1"), entry(citation=LOTO), entry(citation=FLANGE, evidence_text="FLG CL150"))
    assert [(r["status"], r["citation"], r["finding_id"]) for r in rows] == [("FAIL", LOTO, "D1-C01"), ("FAIL", FLANGE, "D1-C02")]
    assert len(suppressed) == 1 and suppressed[0]["citation"] == IBC


# ---- self-contradiction
def test_judge_found_the_item_itself():
    rows, suppressed = run("PID", entry(found_in_text=True))
    assert rows[0]["status"] == "PASS" and suppressed[0]["suppressed_by"] == "self_contradiction"


def test_expected_item_present_in_the_drawing_text_despite_found_false():
    md = "M\nLOT0-2505A\nP-2505A\nBOOSTER PUMP"  # the parser wrote the O of LOTO as a zero
    rows, suppressed = run("PID", entry(expected_item="LOTO-2505A", found_in_text=False), markdown=md)
    assert rows[0]["status"] == "PASS" and "expected_item" in suppressed[0]["suppression_detail"]
    # a requirement quoted in the notes is not a tag: a weld that breaks "BW with 100% RT" stays a FAIL although the words are in the drawing
    rows, _ = run("SPEC", entry(citation=WELD, expected_item="BW with 100% RT", reason="Class A1S shows FW with VT ONLY."), markdown="COLD SERVICE: BW WITH 100% RT")
    assert rows[0]["status"] == "FAIL"
    # an expected item that is really absent stays a FAIL (a ROTO- misread of the parser is not guessed away)
    rows, suppressed = run("PID", entry(expected_item="LOTO-2207A"), markdown="ROTO-2207A\nP-2207A")
    assert rows[0]["status"] == "FAIL" and not suppressed


@pytest.mark.parametrize("reason", [
    "Pump P-2105A has a tag shown as LOT0-2105A, but this appears to be a parser error and the LOTO tag is present in the drawing.",
    "Pump P-2403A has LOTO-2403A. However, only P-2403A is shown, so this pump has its LOTO tag.",
    "Vessel V-2603 has PSV-2603, so it is protected.",
    "LOTO-2703A is present in the text as 'O LOTO-2703A', so this is not a violation.",
    "The flange class is adequate for the line design pressure.",
    "Class E15S: rating 3600 PSIG is below the design pressure 3110 PSIG. Wait, 3600 is greater than 3110, so this is compliant.",
])
def test_reason_that_admits_compliance_is_suppressed(reason):
    rows, suppressed = run("PID", entry(reason=reason))
    assert rows[0]["status"] == "PASS", reason
    assert suppressed[0]["suppressed_by"] == "self_contradiction"


@pytest.mark.parametrize("reason", [
    "Pump P-2101A has no LOTO energy isolation tag. Expected LOTO-2101A is not present in the drawing text.",
    "Flange CL150 is inadequate: rated 275 PSIG against a line design pressure of 500 PSIG.",
    "Vessel V-2506 has no PSV tag or set pressure, so it is not protected.",
    "Pump P-2102A has no LOTO tag; the drawing shows ROTO-2102A instead.",
    "Compressor K-2702 is powered equipment and requires a LOTO tag. No LOTO-2702 tag is present in the drawing.",
    "Pump P-2105A has no LOTO tag. Only LOTO-2101A is present in the drawing text.",
])
def test_reason_that_states_a_violation_is_kept(reason):
    rows, suppressed = run("PID", entry(reason=reason))
    assert rows[0]["status"] == "FAIL" and not suppressed, reason


def test_loto_rule_applied_to_a_vessel_contradicts_the_rule_itself():
    rows, suppressed = run("PID", entry(evidence_text="V-2505", reason="Vessel V-2505 has no LOTO tag."))
    assert rows[0]["status"] == "PASS" and suppressed[0]["suppressed_by"] == "self_contradiction"


# ---- unchanged fallbacks
def test_error_and_malformed_stay_review_and_nothing_is_suppressed():
    for response, error in ((None, "timeout"), ("{not json", None), ('{"findings": "x"}', None)):
        rows, suppressed = lib.judge_with_guardrails("D1", "PID", "text", response, error)
        assert [r["status"] for r in rows] == ["REVIEW"] and rows[0]["reason"].startswith("Judge output could not be parsed") and not suppressed


def test_empty_findings_pass_and_unknown_citation_only_is_review():
    assert run("PID")[0][0]["status"] == "PASS"
    assert run("PID", entry(citation="NFPA 59A"))[0][0]["status"] == "REVIEW"
