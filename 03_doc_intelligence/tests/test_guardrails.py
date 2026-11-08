"""Unit tests for the zero-cost guardrails on the saved judge output (compliance_lib.judge_with_guardrails). No AI call, no workspace.

    pytest 03_doc_intelligence/tests/test_guardrails.py -v
"""
import json
from pathlib import Path

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


def test_reason_sentence_scope_the_conclusion_decides():
    # a premise that admits something in an earlier sentence does not make the conclusion a non-violation
    reason = "A vessel is not powered equipment. Compressor K-2601 has no LOTO tag."
    rows, suppressed = run("PID", entry(reason=reason, evidence_text="K-2601"))
    assert rows[0]["status"] == "FAIL" and not suppressed
    rows, suppressed = run("PID", entry(reason="Compressor K-2601 has no LOTO tag. However, vessels are not powered equipment.", evidence_text="K-2601"))
    assert rows[0]["status"] == "PASS"  # the conclusion itself admits it


def test_found_in_text_only_clears_presence_rules():
    rows, suppressed = run("GA", entry(citation=IBC, found_in_text=True, expected_item="44 IN", reason="Exit 3 provides 36 in but requires 44 in."))
    assert rows[0]["status"] == "FAIL" and not suppressed
    rows, suppressed = run("SPEC", entry(citation=FLANGE, found_in_text=True, expected_item="CLASS 600", reason="Class 300 rating is below the design pressure."))
    assert rows[0]["status"] == "FAIL" and not suppressed
    rows, suppressed = run("PID", entry(citation=RELIEF, found_in_text=True, evidence_text="V-2102", reason="Vessel has no PSV."))
    assert rows[0]["status"] == "PASS" and "judge's self-check" in suppressed[0]["suppression_detail"]


def test_pass_reason_counts_the_suppressed_entries():
    rows, suppressed = run("ISO", entry(citation=LOTO), entry(citation=RELIEF, evidence_text="V-1"))
    assert rows[0]["status"] == "PASS" and "2 judge entries suppressed" in rows[0]["reason"] and "compliance_suppressed" in rows[0]["reason"]
    assert run("PID")[0][0]["reason"] == "No violation of the five checked rules found."


def test_every_raw_entry_is_kept_or_suppressed():
    entries = [entry(citation=LOTO), entry(citation=IBC, evidence_text="EXIT 1"), entry(found_in_text=True), entry(citation=FLANGE, evidence_text="FLG"),
               entry(reason="Vessel V-1 has PSV-1, so it is protected.", citation=RELIEF)]
    response = json.dumps({"findings": entries})
    kept, suppressed = lib.judge_with_guardrails("D1", "PID", "text", response, None)
    assert len(lib.raw_entries(response)) == len(entries) == len([k for k in kept if k["status"] == "FAIL"]) + len(suppressed)


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


# ---- the prompt must not carry generator knowledge
GENERATOR = Path(__file__).resolve().parents[2] / "01_synthetic_data" / "02_generate_drawings.py"
VARIANT_LITERALS = ["FW", "SW", "BW", "VT ONLY", "MT 5%", "RT", "100% RT", "RT 100%", "fillet", "socket", "butt", "NONE", "CL150", "FLG CL", "LOTO-0000"]


def _generator_constants():
    import ast
    tree = ast.parse(GENERATOR.read_text())
    wanted = {"RATING_PSIG", "CLASSES", "CLASS_CODE", "CLASS_SERVICE", "FLAW_TYPES"}
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in wanted for t in node.targets):
            out.append(ast.literal_eval(node.value))
    return out


def _flatten(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _flatten(k); yield from _flatten(v)
    elif isinstance(value, (tuple, list)):
        for v in value:
            yield from _flatten(v)
    else:
        yield value


def test_prompt_has_no_generator_literals():
    import re
    prompt = lib.build_prompt_prefix()
    for lit in VARIANT_LITERALS:
        assert not re.search(r"(?<![A-Za-z0-9])" + re.escape(lit) + r"(?![A-Za-z0-9])", prompt), f"corruption/value literal {lit!r} is in the prompt"
    # no drawing-tag-shaped token (K-2502, LOTO-2104A, PSV-2102, V-2504 ...)
    assert not re.findall(r"\b[A-Za-z]{1,4}-\d{3,4}[A-Za-z]?\b", prompt)
    # none of the class numbers, ratings, class codes or service words the generator draws, and not the flaw type names
    consts = _generator_constants()
    assert len(consts) == 5, "the generator constants moved: update this test"
    for const in consts:
        for v in _flatten(const):
            token = str(v)
            if len(token) < 2 and not token.isdigit():
                continue
            if token in set(lib.CITATIONS) | set(lib.SEVERITIES):
                continue  # the citations and the severity scale are the fixed output vocabulary
            assert not re.search(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", prompt), f"generator literal {token!r} is in the prompt"
    # the answer-format examples are gone
    assert "for example" not in lib.OUTPUT_FORMAT
