"""Tests for the synthetic drawing generator, 01_synthetic_data/02_generate_drawings.py.

The PDFs and the ground-truth sidecar are test data for the compliance pipeline, so these tests pin
what that pipeline relies on: the count and flaw rate, the manifest and ground-truth shapes, that the
output is deterministic, and that every ground-truth bbox really sits on the element that was planted.

Run from the repo root (pyproject.toml puts 01_synthetic_data on the pytest path):
    pytest 01_synthetic_data/tests/test_generate_drawings.py -v
"""
import importlib
import re
from collections import Counter

import pytest

MODULE = "02_generate_drawings"  # starts with a digit, so `import 02_generate_drawings` is a SyntaxError

TAXONOMY = {
    "flange_rating_mismatch": "ASME B16.5 §4.2",
    "missing_loto_tag": "OSHA 1910.147",
    "egress_width_under_code": "IBC 1005.1",
    "weld_joint_spec_mismatch": "ASME B31.3 §341",
    "missing_pressure_relief_notation": "ASME B31.3 §322",
}
MANIFEST_KEYS = {"drawing_id", "discipline", "revision", "drawing_type", "volume_path", "has_flaw"}
GROUND_TRUTH_KEYS = {"drawing_id", "finding_id", "page_num", "bbox", "citation", "severity", "flaw_type"}
DRAWING_TYPES = {"ISO", "PID", "GA", "SPEC", "OTHER"}  # the ai_classify labels
DISCIPLINES = {"piping", "structural", "mechanical", "electrical", "instr"}


def generate_drawings(**kwargs):
    # Imported on first call rather than at collection time, so a missing module is a plain test failure.
    return importlib.import_module(MODULE).generate_drawings(**kwargs)


def test_generates_expected_count_and_flaw_rate(tmp_path):
    out = generate_drawings(n=100, flaw_rate=0.2, seed=42, out_dir=tmp_path)
    assert out.manifest_count == 100
    assert 15 <= out.flawed_count <= 25     # ~20%
    assert all((tmp_path / f"{d['drawing_id']}.pdf").exists() for d in out.manifest)
    assert all(f['bbox'] and f['page_num'] >= 0 for f in out.ground_truth)


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    """300 drawings: enough for every flaw type, a three-flaw drawing and two-page sheets to turn up."""
    out_dir = tmp_path_factory.mktemp("drawings")
    return out_dir, generate_drawings(n=300, flaw_rate=0.2, seed=42, out_dir=out_dir)


def test_manifest_and_ground_truth_follow_the_interface(sample):
    out_dir, out = sample
    ids = [d["drawing_id"] for d in out.manifest]
    assert len(ids) == len(set(ids)) == 300
    for d in out.manifest:
        assert set(d) == MANIFEST_KEYS
        assert d["drawing_type"] in DRAWING_TYPES
        assert d["discipline"] in DISCIPLINES
        assert d["revision"]
        assert isinstance(d["has_flaw"], bool)
        assert d["volume_path"] == f"{out_dir.as_posix()}/{d['drawing_id']}.pdf"

    assert Counter(d["drawing_type"] for d in out.manifest).keys() >= {"ISO", "PID", "GA", "SPEC"}
    flawed_ids = {d["drawing_id"] for d in out.manifest if d["has_flaw"]}
    assert flawed_ids == {f["drawing_id"] for f in out.ground_truth}
    assert out.flawed_count == len(flawed_ids) == 60      # exactly round(300 * 0.2), not a coin flip per drawing

    finding_ids = [f["finding_id"] for f in out.ground_truth]
    assert len(finding_ids) == len(set(finding_ids))
    for f in out.ground_truth:
        assert set(f) == GROUND_TRUTH_KEYS
        assert f["citation"] == TAXONOMY[f["flaw_type"]]
        assert f["severity"] in {"critical", "high", "medium", "low"}
        assert isinstance(f["page_num"], int)
        x, y, w, h = f["bbox"]                              # normalised [x, y, w, h], origin top-left
        assert x >= 0.0 and y >= 0.0 and w > 0.0 and h > 0.0
        assert x + w <= 1.0 and y + h <= 1.0


def test_every_flaw_type_is_planted_and_some_drawings_have_several(sample):
    _, out = sample
    assert {f["flaw_type"] for f in out.ground_truth} == set(TAXONOMY)
    per_drawing = Counter(f["drawing_id"] for f in out.ground_truth)
    assert max(per_drawing.values()) == 3                   # the grain test in the compliance task needs one
    assert 0.05 <= sum(1 for c in per_drawing.values() if c > 1) / len(per_drawing) <= 0.20   # "~10%"
    for drawing_id, count in per_drawing.items():           # a flaw type is planted at most once per drawing
        types = {f["flaw_type"] for f in out.ground_truth if f["drawing_id"] == drawing_id}
        assert len(types) == count


def test_output_is_deterministic_for_a_seed(tmp_path):
    a = generate_drawings(n=40, flaw_rate=0.2, seed=7, out_dir=tmp_path / "a")
    b = generate_drawings(n=40, flaw_rate=0.2, seed=7, out_dir=tmp_path / "b")
    c = generate_drawings(n=40, flaw_rate=0.2, seed=8, out_dir=tmp_path / "c")
    assert a.ground_truth == b.ground_truth
    assert [d["drawing_id"] for d in a.manifest] == [d["drawing_id"] for d in b.manifest]
    assert all(
        (tmp_path / "a" / f"{d['drawing_id']}.pdf").read_bytes() == (tmp_path / "b" / f"{d['drawing_id']}.pdf").read_bytes()
        for d in a.manifest
    )
    assert a.ground_truth != c.ground_truth


def test_flaw_rate_extremes_and_bad_arguments(tmp_path):
    none = generate_drawings(n=12, flaw_rate=0.0, seed=1, out_dir=tmp_path / "none")
    every = generate_drawings(n=12, flaw_rate=1.0, seed=1, out_dir=tmp_path / "every")
    assert (none.flawed_count, none.finding_count) == (0, 0)
    assert every.flawed_count == 12 and every.finding_count >= 12
    assert all(d["drawing_type"] != "OTHER" for d in every.manifest)    # the symbols sheet has nothing to plant
    for bad in ({"n": 10, "flaw_rate": 1.5}, {"n": 10, "flaw_rate": -0.1}, {"n": -1, "flaw_rate": 0.2}):
        with pytest.raises(ValueError):
            generate_drawings(seed=1, out_dir=tmp_path / "bad", **bad)


def _text_runs(pdf_path):
    """Every text run in a PDF as (page_index, x, y, text), with x/y of the run's origin normalised like a bbox."""
    pypdf = pytest.importorskip("pypdf")
    reader = pypdf.PdfReader(pdf_path)
    runs = []
    for index, page in enumerate(reader.pages):
        width, height = float(page.mediabox.width), float(page.mediabox.height)

        def visit(text, cm, tm, font_dict, font_size, _index=index, _w=width, _h=height):
            if text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                runs.append((_index, x / _w, 1.0 - y / _h, text.strip()))

        page.extract_text(visitor_text=visit)
    return runs, len(reader.pages)


def test_each_bbox_sits_on_the_planted_element(sample):
    out_dir, out = sample
    by_drawing = {}
    for f in out.ground_truth:
        by_drawing.setdefault(f["drawing_id"], []).append(f)

    checked = Counter()
    for drawing_id, findings in by_drawing.items():
        runs, page_count = _text_runs(out_dir / f"{drawing_id}.pdf")
        for f in findings:
            assert f["page_num"] < page_count
            x, y, w, h = f["bbox"]
            inside = [t for (p, rx, ry, t) in runs if p == f["page_num"] and x <= rx <= x + w and y <= ry <= y + h]
            anywhere = [t for (_, _, _, t) in runs]
            kind = f["flaw_type"]
            assert inside, f"{f['finding_id']}: nothing is drawn inside the bbox"
            if kind == "flange_rating_mismatch":            # the under-rated flange (or table row) names its class
                assert any(re.search(r"CL\s?\d{3,4}|\b(?:150|300|600|900|1500)\b", t) for t in inside), inside
            elif kind == "egress_width_under_code":         # the exit shows its clear width
                assert any(re.search(r"\b\d{2,3}\b", t) for t in inside), inside
            elif kind == "weld_joint_spec_mismatch":        # the weld shows its type / examination
                assert any(re.search(r"\b(?:BW|SW|FW|RT|VT|PT|MT)\b|NONE", t) for t in inside), inside
            elif kind == "missing_loto_tag":                # equipment is there, its LOTO tag is not ...
                assert not any("LOTO" in t for t in inside), inside
                assert any("LOTO" in t for t in anywhere)   # ... although the sheet uses LOTO tags elsewhere
            elif kind == "missing_pressure_relief_notation":
                assert not any("PSV" in t for t in inside), inside
                assert any("PSV" in t for t in anywhere)
            checked[kind] += 1
    assert set(checked) == set(TAXONOMY)


def test_flaws_land_on_later_pages_of_multi_page_drawings(sample):
    _, out = sample
    assert {f["page_num"] for f in out.ground_truth} == {0, 1}
