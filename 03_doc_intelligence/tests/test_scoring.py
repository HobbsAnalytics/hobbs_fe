"""Unit tests for scoring_lib (pure functions behind 04_ground_truth_scoring.ipynb)."""
import json

import compliance_lib as lib
import scoring_lib as sc

FL, LO, IB, WE, RE = lib.CITATIONS


def test_prf_counts_and_undefined_cases():
    assert sc.prf(3, 1, 1) == (0.75, 0.75, 0.75)
    assert sc.prf(0, 0, 0) == (None, None, None)          # nothing predicted, nothing true
    p, r, f1 = sc.prf(0, 2, 0)
    assert (p, r, f1) == (0.0, None, None)                # recall undefined without truth


def test_score_pairs_tp_fp_fn_page_agreement_and_micro():
    truth = {("D1", LO): 0, ("D2", FL): 1, ("D3", RE): 0}
    pred = {("D1", LO): {0}, ("D2", FL): {0, 2}, ("D4", LO): {0}}   # D2 pair is a TP on the wrong pages; D4 is a FP; D3 is a FN
    s = sc.score_pairs(pred, truth, lib.CITATIONS)
    assert (s[LO]["tp"], s[LO]["fp"], s[LO]["fn"]) == (1, 1, 0)
    assert (s[FL]["tp"], s[FL]["fp"], s[FL]["fn"]) == (1, 0, 0) and s[FL]["page_agreement"] == 0.0
    assert (s[RE]["tp"], s[RE]["fp"], s[RE]["fn"]) == (0, 0, 1)
    assert s[IB]["precision"] is None and s[IB]["recall"] is None
    a = s["ALL"]
    assert (a["tp"], a["fp"], a["fn"]) == (2, 1, 1)
    assert a["precision"] == round(2 / 3, 4) and a["recall"] == round(2 / 3, 4) and a["page_agreement"] == 0.5
    assert a["tp"] == sum(s[c]["tp"] for c in lib.CITATIONS)  # the micro row is the sum of the per-citation rows


def test_a_b_c_columns_follow_compliance_lib():
    # An ISO sheet: the LOTO entry is routed away by the guardrails (C), a presence entry the judge cleared is out of B and C.
    answer = json.dumps({"findings": [
        {"expected_item": "x", "found_in_text": False, "status": "FAIL", "citation": LO, "severity": "high", "reason": "No tag for pump P-1.", "page_num": 0, "evidence_text": "P-1"},
        {"expected_item": "PSV-2", "found_in_text": True, "status": "FAIL", "citation": RE, "severity": "critical", "reason": "No relief for V-2.", "page_num": 0, "evidence_text": "V-2"},
        {"expected_item": "CLASS 600", "found_in_text": False, "status": "FAIL", "citation": FL, "severity": "critical", "reason": "CL150 is rated 285 against 400 PSIG.", "page_num": 1, "evidence_text": "FLG CL150"},
    ]})
    cols = sc.entries_by_column("D1", "ISO", "text", answer, None)
    assert [e["citation"] for e in cols["A"]] == [LO, RE, FL]
    assert [e["citation"] for e in cols["B"]] == [LO, FL]
    assert [e["citation"] for e in cols["C"]] == [FL]
    assert not sc.is_review("D1", answer, None)
    assert sc.is_review("D2", "not json", None) and sc.entries_by_column("D2", "PID", "", "not json", None) == {"A": [], "B": [], "C": []}


def test_fp_cause():
    assert sc.fp_cause(LO, "... ROTO-2104A ...") == "loto_ocr_misread"
    assert sc.fp_cause(LO, "... LOTO-2104A ...") == "other"
    assert sc.fp_cause(FL, "") == "flange_arithmetic"
    assert sc.fp_cause(RE, "ROTO-1") == "other"
    assert sc.loto_misread_example("x LOT0-3304A y") == "LOT0-3304A"
