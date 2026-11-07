"""Tests for the compliance judge, 03_doc_intelligence/03_compliance_check.ipynb.

Two required tests (task 8):

* test_malformed_judge_output_falls_back_to_review: a unit test of the pure function that turns one raw
  judge answer into rows (compliance_lib.flatten_judgement). No AI call, no workspace. Covers a valid
  answer with two findings, an empty answer (PASS), malformed JSON and an error status (both REVIEW).
* test_findings_grain_is_one_row_per_finding: a live test of gold_pm.compliance_findings after the
  notebook ran. Opt-in, like the T5 test:  BLUERRIDGE_LIVE_TESTS=1 pytest 03_doc_intelligence/tests -v

Run from the repo root (pyproject.toml puts 03_doc_intelligence on the pytest path).
"""
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

import pytest

import compliance_lib as lib

REPO_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH = REPO_ROOT / "01_synthetic_data" / "outputs" / "ground_truth_findings.jsonl"
CITATIONS = {"ASME B16.5 §4.2", "OSHA 1910.147", "IBC 1005.1", "ASME B31.3 §341", "ASME B31.3 §322"}


def finding(**over):
    base = {"status": "FAIL", "reason": "Flange class 150 on a 500 PSIG line.", "citation": "ASME B16.5 §4.2",
            "severity": "critical", "page_num": 0, "evidence_text": "FLG CL150"}
    base.update(over)
    return base


def answer(*findings):
    return json.dumps({"findings": list(findings)})


# ---------------------------------------------------------------- unit tests (no workspace)

def test_two_findings_become_two_fail_rows():
    rows = lib.flatten_judgement("D1", answer(finding(), finding(citation="OSHA 1910.147", severity="high", evidence_text="K-2502")), None)
    assert [r["status"] for r in rows] == ["FAIL", "FAIL"]
    assert len({r["finding_id"] for r in rows}) == 2
    assert {r["citation"] for r in rows} == {"ASME B16.5 §4.2", "OSHA 1910.147"}
    assert all(r["drawing_id"] == "D1" and r["reason"] and r["evidence_text"] for r in rows)


def test_no_findings_become_one_pass_sentinel():
    rows = lib.flatten_judgement("D1", answer(), None)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "PASS" and r["reason"]
    assert all(r[k] is None for k in ("citation", "page_num", "severity", "evidence_text"))


@pytest.mark.parametrize("bad", ["{not json", "", None, "[]", '{"findings": "none"}', '{"other": 1}', '{"findings": [42]}'])
def test_malformed_judge_output_falls_back_to_review(bad):
    rows = lib.flatten_judgement("D1", bad, None)
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "REVIEW"
    assert r["reason"] and r["reason"].startswith("Judge output could not be parsed")
    assert r["citation"] is None and r["severity"] is None


def test_error_status_falls_back_to_review():
    rows = lib.flatten_judgement("D1", None, "REQUEST_LIMIT_EXCEEDED: slow down")
    assert len(rows) == 1 and rows[0]["status"] == "REVIEW"
    assert "REQUEST_LIMIT_EXCEEDED" in rows[0]["reason"]
    # an error wins even when a response came back with it
    assert lib.flatten_judgement("D1", answer(finding()), "timeout")[0]["status"] == "REVIEW"


def test_severity_and_citation_are_normalised():
    rows = lib.flatten_judgement("D1", answer(finding(severity="SEVERE"), finding(citation="ASME B31.3 Para. 322", severity="Low"),
                                              finding(citation="NFPA 59A", reason="x")), None)
    assert rows[0]["severity"] == "medium"          # not one of the four: coerced
    assert rows[1]["citation"] == "ASME B31.3 §322" and rows[1]["severity"] == "low"
    assert len(rows) == 2                            # a citation outside the five rules is not a finding


def test_finding_the_judge_itself_cleared_is_not_a_violation():
    # found_in_text true: the judge's own search found the item that makes the drawing comply
    rows = lib.flatten_judgement("D1", answer(finding(found_in_text=True), finding(citation="OSHA 1910.147", found_in_text=False)), None)
    assert [r["status"] for r in rows] == ["FAIL"] and rows[0]["citation"] == "OSHA 1910.147"
    rows = lib.flatten_judgement("D1", answer(finding(found_in_text=True)), None)
    assert [r["status"] for r in rows] == ["PASS"]


def test_only_unknown_citations_is_review_not_pass():
    rows = lib.flatten_judgement("D1", answer(finding(citation="NFPA 59A")), None)
    assert len(rows) == 1 and rows[0]["status"] == "REVIEW"


def test_review_dates_put_238_drawings_in_the_as_of_week():
    manifest = [{"drawing_id": f"D{i:04d}", "has_flaw": i % 5 == 0} for i in range(1200)]  # 240 flawed
    dates = lib.assign_review_dates(manifest)
    assert len(dates) == 1200
    week = [d for d, v in dates.items() if "2026-10-31" <= v <= "2026-11-06"]
    assert len(week) == 238
    assert sum(1 for d in week if int(d[1:]) % 5 == 0) == 24
    assert min(dates.values()) >= "2026-06-01" and max(dates.values()) <= "2026-11-06"
    assert dates == lib.assign_review_dates(manifest)  # deterministic


def test_bbox_from_parse_elements_is_the_tightest_match_and_normalised():
    pj = json.dumps({"document": {"elements": [
        {"id": 1, "type": "figure", "content": "A\nFLG CL150\nB", "bbox": [{"coord": [336.6, 217.8, 3029.4, 1960.2], "page_id": 0}]},
        {"id": 2, "type": "text", "content": "FLG CL150", "bbox": [{"coord": [336.6, 217.8, 673.2, 435.6], "page_id": 0}]},
        {"id": 3, "type": "text", "content": "FLG CL150", "bbox": [{"coord": [0, 0, 100, 100], "page_id": 1}]}]}})
    box = lib.resolve_parse_bbox(pj, 0, "FLG CL150")
    assert box == pytest.approx([0.1, 0.1, 0.1, 0.1])
    assert lib.resolve_parse_bbox(pj, 0, "NOT THERE") is None
    assert lib.resolve_parse_bbox(None, 0, "FLG CL150") is None


# ---------------------------------------------------------------- live test (needs the table)

def sql(statement):
    out = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", statement, "--profile", "DEFAULT"],
                         cwd=REPO_ROOT, capture_output=True, text=True, timeout=600, check=True).stdout
    return json.loads(out[out.index("["):])


@pytest.mark.skipif(os.environ.get("BLUERRIDGE_LIVE_TESTS") != "1", reason="live workspace test: set BLUERRIDGE_LIVE_TESTS=1")
def test_findings_grain_is_one_row_per_finding():
    planted = Counter(json.loads(line)["drawing_id"] for line in GROUND_TRUTH.read_text().splitlines())
    three = sorted(d for d, n in planted.items() if n == 3)
    assert len(three) == 10
    ids = ", ".join(f"'{d}'" for d in three)
    rows = sql(f"SELECT drawing_id, finding_id, status, bbox, bbox_source, citation, severity FROM "
               f"mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings WHERE drawing_id IN ({ids})")
    by_drawing = {d: [r for r in rows if r["drawing_id"] == d] for d in three}
    # pick the drawing where the judge found the most of the 3 planted flaws
    best = max(three, key=lambda d: sum(r["status"] == "FAIL" for r in by_drawing[d]))
    mine = by_drawing[best]
    fails = [r for r in mine if r["status"] == "FAIL"]
    print(f"{best}: {len(fails)} FAIL rows of 3 planted")
    assert fails, "the judge found nothing on any of the ten 3-flaw drawings"
    assert len(mine) == len(fails), "a drawing with violations has FAIL rows only (no PASS/REVIEW sentinel)"
    assert len({r["finding_id"] for r in mine}) == len(mine), "finding_id is distinct per row"
    for r in fails:
        bbox = json.loads(r["bbox"]) if isinstance(r["bbox"], str) else r["bbox"]
        assert bbox is not None and len(bbox) == 4 and all(0 <= float(v) <= 1 for v in bbox)
        assert not isinstance(bbox[0], (list, dict)), "no nested arrays"
        assert r["citation"] in CITATIONS and r["severity"] in {"critical", "high", "medium", "low"}
    # the grain holds across the whole table
    dup = sql("SELECT COUNT(*) AS n FROM (SELECT drawing_id, finding_id FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings "
              "GROUP BY 1, 2 HAVING COUNT(*) > 1)")
    assert int(dup[0]["n"]) == 0
