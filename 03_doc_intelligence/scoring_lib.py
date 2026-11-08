"""Pure scoring functions for 04_ground_truth_scoring.ipynb. No Spark, no AI call: unit-tested locally (tests/test_scoring.py).

Matching key: a (drawing_id, citation) pair. A predicted pair is a FAIL entry in the column being scored; a true pair is a row of
ground_truth_findings. TP = in both, FP = predicted only, FN = true only. REVIEW and PASS rows are neither predictions nor
ground truth. Page agreement is a diagnostic on the TPs: the share whose predicted page equals the planted page (a pair predicted on
several pages agrees when any of its predicted pages equals the planted page).

The three evaluation columns of a raw judge table are derived with compliance_lib, never re-implemented here:
  A  every entry of the judge's answer                         compliance_lib.raw_entries
  B  after the judge's own found_in_text self-check            compliance_lib.flatten_judgement (FAIL rows)
  C  after the guardrails (rule applicability, consistency)    compliance_lib.judge_with_guardrails (FAIL rows)
"""
from __future__ import annotations

import re

import compliance_lib as lib

COLUMNS = ("A", "B", "C")


def entries_by_column(drawing_id, drawing_type, markdown, response, error):
    """{'A': [entry], 'B': [entry], 'C': [entry]} for one drawing; an entry is a dict with at least citation, page_num, reason,
    evidence_text. REVIEW and PASS rows give no entry."""
    a = lib.raw_entries(response, error)
    b = [r for r in lib.flatten_judgement(drawing_id, response, error) if r["status"] == "FAIL"]
    rows, _suppressed = lib.judge_with_guardrails(drawing_id, drawing_type, markdown or "", response, error)
    c = [r for r in rows if r["status"] == "FAIL"]
    return {"A": a, "B": b, "C": c}


def is_review(drawing_id, response, error):
    # True when the judge's answer for the drawing is unusable (the REVIEW row of flatten_judgement).
    return any(r["status"] == "REVIEW" for r in lib.flatten_judgement(drawing_id, response, error))


def safe_div(num, den):
    return round(num / den, 4) if den else None


def prf(tp, fp, fn):
    p, r = safe_div(tp, tp + fp), safe_div(tp, tp + fn)
    f1 = round(2 * p * r / (p + r), 4) if p is not None and r is not None and (p + r) else None
    return p, r, f1


def score_pairs(pred_pages, truth_pages, citations=None):
    """pred_pages: {(drawing_id, citation): set of predicted pages}; truth_pages: {(drawing_id, citation): planted page}.
    Returns {citation or 'ALL': dict(tp, fp, fn, precision, recall, f1, page_agreement, tp_pairs, fp_pairs, fn_pairs)}."""
    cits = list(citations) if citations is not None else sorted({c for _, c in set(pred_pages) | set(truth_pages)})
    out = {}
    for cit in [*cits, "ALL"]:
        keep = (lambda k: True) if cit == "ALL" else (lambda k, cit=cit: k[1] == cit)
        pred = {k for k in pred_pages if keep(k)}
        truth = {k for k in truth_pages if keep(k)}
        tp, fp, fn = sorted(pred & truth), sorted(pred - truth), sorted(truth - pred)
        agree = sum(1 for k in tp if truth_pages[k] in pred_pages[k])
        p, r, f1 = prf(len(tp), len(fp), len(fn))
        out[cit] = dict(tp=len(tp), fp=len(fp), fn=len(fn), precision=p, recall=r, f1=f1,
                        page_agreement=safe_div(agree, len(tp)), tp_pairs=tp, fp_pairs=fp, fn_pairs=fn)
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# False-positive causes (the Task 8 diagnosis)
# ---------------------------------------------------------------------------------------------------------------------------
LOTO_MISREAD = re.compile(r"\b(?:ROTO|LOT0|L0TO|L0T0|LOTOTO|LQTO|IOTO|LOTQ|LOTD)-\d+[A-Z]?", re.I)
CAUSES = ("loto_ocr_misread", "flange_arithmetic", "other")


def fp_cause(citation, markdown):
    """Likely cause of a false positive on `citation` for a drawing with this parsed text.
    loto_ocr_misread:  OSHA 1910.147 and the parsed text spells a LOTO tag with a misread prefix (ROTO-, LOT0-, LOTOTO- ...), so the judge
                       can see the tag only as something else.
    flange_arithmetic: ASME B16.5 §4.2, the judge compared a class against a design pressure and got it wrong.
    other:             everything else."""
    if citation == "OSHA 1910.147" and LOTO_MISREAD.search(markdown or ""):
        return "loto_ocr_misread"
    if citation == "ASME B16.5 §4.2":
        return "flange_arithmetic"
    return "other"


def loto_misread_example(markdown):
    # The first misread tag in the text (for the wins-and-losses note), or None.
    m = LOTO_MISREAD.search(markdown or "")
    return m.group(0) if m else None
