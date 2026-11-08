"""Validate the code-excerpts corpus (04_vector_search/code_excerpts/*.md) without any Databricks access.

Each excerpt is a markdown file with a YAML front-matter block (between two `---` lines) followed by the body.
Run: uv run --no-project --with pytest --with pyyaml python -m pytest 04_vector_search/tests
"""
from pathlib import Path

import pytest
import yaml

EXCERPT_DIR = Path(__file__).resolve().parents[1] / "code_excerpts"
REQUIRED = ["citation_id", "citation_label", "title", "source", "is_paraphrase", "related_flaw_type"]
FLAW_TYPES = {
    "flange_rating_mismatch",
    "missing_loto_tag",
    "egress_width_under_code",
    "weld_joint_spec_mismatch",
    "missing_pressure_relief_notation",
    "none",
}
# The five strings compliance_findings.citation can hold (03_doc_intelligence); the app looks them up exactly.
PRIMARY_LABELS = [
    "ASME B16.5 §4.2",
    "OSHA 1910.147",
    "IBC 1005.1",
    "ASME B31.3 §341",
    "ASME B31.3 §322",
]


def parse(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no front-matter"
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body.strip()


def excerpt_files():
    return sorted(p for p in EXCERPT_DIR.glob("*.md") if p.name.lower() != "readme.md")


@pytest.fixture(scope="module")
def entries():
    return [(p, *parse(p)) for p in excerpt_files()]


def test_file_count_between_40_and_60():
    assert 40 <= len(excerpt_files()) <= 60


def test_required_front_matter_present_and_non_empty(entries):
    for path, meta, _ in entries:
        for field in REQUIRED:
            assert field in meta, f"{path.name}: missing {field}"
            assert meta[field] not in (None, ""), f"{path.name}: empty {field}"
        assert isinstance(meta["is_paraphrase"], bool), f"{path.name}: is_paraphrase must be a bool"
        assert meta["related_flaw_type"] in FLAW_TYPES, f"{path.name}: bad related_flaw_type"


def test_citation_ids_unique(entries):
    ids = [m["citation_id"] for _, m, _ in entries]
    assert len(ids) == len(set(ids))


def test_five_primary_labels_present_exactly(entries):
    labels = [m["citation_label"] for _, m, _ in entries]
    for label in PRIMARY_LABELS:
        assert labels.count(label) == 1, f"{label!r} should appear exactly once, found {labels.count(label)}"


def test_asme_and_ibc_are_paraphrases(entries):
    for path, meta, _ in entries:
        if str(meta["source"]).startswith(("ASME", "IBC")):
            assert meta["is_paraphrase"] is True, f"{path.name}: copyrighted source must be a paraphrase"


def test_bodies_non_empty_and_short(entries):
    for path, _, body in entries:
        assert body, f"{path.name}: empty body"
        assert len(body) < 1500, f"{path.name}: body too long for an excerpt"
