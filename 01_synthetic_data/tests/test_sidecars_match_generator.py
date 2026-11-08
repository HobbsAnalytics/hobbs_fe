"""The committed sidecars must be exactly what the generator produces.

`01_synthetic_data/outputs/ground_truth_findings.jsonl` and `drawing_manifest.json` are the answer key that
03_doc_intelligence/04_ground_truth_scoring.ipynb scores the compliance judge against. If the generator drifts
(a changed layout, a new random draw) while the committed files stay put, the scores would be measured against a key that no
longer describes the PDFs. This test regenerates the full set (n=1200, flaw_rate=0.2, seed=42) into tmp_path and compares.

The output depends on the pinned library versions (reportlab==5.1.0, faker==40.44.0, see docs/BUILD.md). With other versions
the test is skipped with a reason that names the mismatch, rather than failing on a difference the generator code did not cause
or passing without having checked anything.

Run from the repo root:  uv run --no-project --with pytest --with reportlab==5.1.0 --with faker==40.44.0 --with numpy \
    python -m pytest 01_synthetic_data/tests/test_sidecars_match_generator.py -v
"""
import importlib
import json
from importlib import metadata
from pathlib import Path

import pytest

PINNED = {"reportlab": "5.1.0", "faker": "40.44.0"}
OUTPUTS = Path(__file__).resolve().parents[1] / "outputs"


def _version_mismatch():
    found = {}
    for name in PINNED:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            found[name] = "not installed"
    return {n: (PINNED[n], v) for n, v in found.items() if v != PINNED[n]}


def _without_prefix(manifest):
    # The manifest's volume_path starts with the Volume (committed) or the out_dir (regenerated); only the file name is compared.
    return [{**d, "volume_path": Path(d["volume_path"]).name} for d in manifest]


def test_committed_sidecars_equal_a_fresh_run(tmp_path):
    mismatch = _version_mismatch()
    if mismatch:
        pytest.skip("pinned generator libraries not installed, so the output may differ: "
                    + ", ".join(f"{n} needs {want}, found {have}" for n, (want, have) in mismatch.items()))
    gen = importlib.import_module("02_generate_drawings")
    result = gen.generate_drawings(n=1200, flaw_rate=0.2, seed=42, out_dir=tmp_path)
    result.write_manifest(tmp_path / "drawing_manifest.json")
    result.write_ground_truth(tmp_path / "ground_truth_findings.jsonl")

    committed_gt = (OUTPUTS / "ground_truth_findings.jsonl").read_text(encoding="utf-8")
    assert (tmp_path / "ground_truth_findings.jsonl").read_text(encoding="utf-8") == committed_gt, \
        "ground_truth_findings.jsonl differs from a fresh seed-42 run: regenerate the sidecars and re-score"
    committed = json.loads((OUTPUTS / "drawing_manifest.json").read_text(encoding="utf-8"))
    fresh = json.loads((tmp_path / "drawing_manifest.json").read_text(encoding="utf-8"))
    assert _without_prefix(fresh) == _without_prefix(committed), "drawing_manifest.json differs from a fresh seed-42 run"
