"""Live test: a malformed "PDF" in the drawings Volume is quarantined, it does not crash ingestion.

Review focus 1 of the plan: a non-PDF in the landing Volume must not take the drawings ingestion
down. This test drives the real workspace through the Databricks CLI (profile DEFAULT, bundle
target demo):

  1. upload MALFORMED-TEST.pdf, a one-sentence text file, into the drawings Volume
  2. run the drawings pipeline: an ordinary incremental update that sees the one new file
  3. assert the update COMPLETED, the file has a bronze row that flags it as not a PDF, and the
     1,200 real drawings are all still there, untouched
  4. whatever happened, delete the file from the Volume and full-refresh the pipeline. A streaming
     table keeps the row of a source file that is later deleted, so only a full refresh takes
     bronze back to exactly the 1,200 real drawings; the fixture then checks that it did.

It is a live integration test, not a unit test, so it is opt-in. It needs `databricks bundle deploy
-t demo` and a finished first update of pipeline_drawings (the 1,200 PDFs loaded). It runs two
pipeline updates (a few minutes) and leaves the workspace as it found it. From the repo root:

    BLUERRIDGE_LIVE_TESTS=1 pytest 02_pipelines/tests/test_malformed_drawing.py -v

What "quarantined" means for this source. Bronze reads the PDFs with Auto Loader's binaryFile
format, which never parses the bytes: Auto Loader adds no `_rescued_data` column for it and rejects
`schemaEvolutionMode=rescue`. So a malformed file cannot fail the update, it lands as an ordinary
row, and the pipeline itself sets `_rescued_data` on it (NULL for a file with the `%PDF-` header, a
small JSON for one without), the meaning the column has in the CSV bronze tables. The file is kept,
not dropped, flagged by `_rescued_data`, and told apart from a drawing by its size and its missing
header.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("BLUERRIDGE_LIVE_TESTS") != "1",
    reason="live workspace test (writes to the drawings Volume, runs two pipeline updates): "
    "set BLUERRIDGE_LIVE_TESTS=1 to run it",
)

# databricks.yml lives at the repo root, and the bundle commands run from there.
REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE = "DEFAULT"
TARGET = "demo"
WAREHOUSE_ID = "527214d7319cb124"
CATALOG = "mfg_mc_se_sa"
PREFIX = "bluerridge"
PIPELINE_KEY = "pipeline_drawings"  # resource key in resources/pipeline-drawings.yml
CLI_TIMEOUT_SEC = 1800  # a pipeline update on cold serverless compute takes minutes, not hours

VOLUME_DIR = f"/Volumes/{CATALOG}/{PREFIX}_landing/drawings"
BRONZE = f"{CATALOG}.{PREFIX}_bronze_drawings.raw_files"
SILVER = f"{CATALOG}.{PREFIX}_silver_engineering.drawings_raw_tracking"

# What job_synthetic_data writes: the length of 01_synthetic_data/outputs/drawing_manifest.json.
VALID_DRAWINGS = 1200
MALFORMED_NAME = "MALFORMED-TEST.pdf"
MALFORMED_TEXT = "This is plain text renamed .pdf; it is not a PDF document."
MALFORMED_BYTES = MALFORMED_TEXT.encode()
MAX_QUARANTINE_BYTES = 100  # a real drawing here is 4.6 KB or more
PDF_MAGIC_HEX = "255044462D"  # b"%PDF-", the first five bytes of every PDF


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the Databricks CLI from the repo root with the project profile. Never raises on exit."""
    return subprocess.run(
        ["databricks", *args, "--profile", PROFILE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SEC,
        check=False,
    )


def cli(*args: str) -> str:
    """Like run_cli, but a non-zero exit raises with the CLI's own message. Returns stdout."""
    done = run_cli(*args)
    if done.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(f"`databricks {command}` exited {done.returncode}:\n{done.stderr}")
    return done.stdout


def query(statement: str) -> list[dict]:
    """Run one SQL statement on the project warehouse. Rows are dicts of strings (NULL is '')."""
    out = cli(
        "experimental", "aitools", "tools", "query",
        "--warehouse", WAREHOUSE_ID, "--output", "json", statement,
    )  # fmt: skip
    return json.loads(out)


def bronze_count() -> int:
    return int(query(f"SELECT count(*) AS n FROM {BRONZE}")[0]["n"])


def pipeline_id() -> str:
    """Id of the deployed drawings pipeline; a test failure if the bundle does not have one yet."""
    summary = json.loads(cli("bundle", "summary", "--target", TARGET, "--output", "json"))
    deployed = summary.get("resources", {}).get("pipelines", {}).get(PIPELINE_KEY, {})
    assert deployed.get("id"), (
        f"{PIPELINE_KEY} is not deployed: it needs resources/pipeline-drawings.yml in "
        f"databricks.yml and `databricks bundle deploy -t {TARGET} --profile {PROFILE}`"
    )
    return deployed["id"]


def run_pipeline(pid: str, *, full_refresh: bool = False) -> dict:
    """Run one update of the drawings pipeline to its end.

    Returns the update's record ({update_id, state, creation_time}) plus the CLI's `log`, which is
    what to read when the update FAILED."""
    seen = {u["update_id"] for u in _latest_updates(pid)}
    args = ["bundle", "run", PIPELINE_KEY, "--target", TARGET]
    done = run_cli(*args, *(["--full-refresh-all"] if full_refresh else []))
    started = [u for u in _latest_updates(pid) if u["update_id"] not in seen]
    assert started, f"`bundle run {PIPELINE_KEY}` started no update:\n{done.stdout}{done.stderr}"
    return {**started[0], "log": (done.stdout + done.stderr)[-2000:]}


def _latest_updates(pid: str) -> list[dict]:
    return json.loads(cli("pipelines", "get", pid, "--output", "json")).get("latest_updates", [])


@pytest.fixture
def malformed_pdf_in_volume():
    """Put MALFORMED-TEST.pdf in the drawings Volume for one test, then leave no trace.

    Yields a dict; the test stores the pipeline id in it as soon as it knows it. Afterwards the
    file is deleted, and if the test got as far as having a pipeline, the pipeline is
    full-refreshed so bronze holds exactly the real drawings again, and that is verified."""
    target = f"dbfs:{VOLUME_DIR}/{MALFORMED_NAME}"
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / MALFORMED_NAME
        local.write_bytes(MALFORMED_BYTES)
        cli("fs", "cp", str(local), target, "--overwrite")

    state = {"pipeline_id": None}
    yield state

    cli("fs", "rm", target)
    if state["pipeline_id"]:
        rebuilt = run_pipeline(state["pipeline_id"], full_refresh=True)
        assert rebuilt["state"] == "COMPLETED", f"cleanup refresh did not complete: {rebuilt}"
        assert bronze_count() == VALID_DRAWINGS, "cleanup left a row for the deleted malformed file"


def test_malformed_file_is_quarantined_not_crashed(malformed_pdf_in_volume):
    pid = pipeline_id()  # RED until pipeline_drawings is part of the bundle and deployed
    malformed_pdf_in_volume["pipeline_id"] = pid  # from here on the fixture rebuilds bronze

    baseline = bronze_count()
    assert baseline == VALID_DRAWINGS, (
        f"expected the {VALID_DRAWINGS} real drawings loaded before the test, found {baseline}: "
        f"run `databricks bundle run {PIPELINE_KEY} -t {TARGET} --profile {PROFILE}` first"
    )

    # The bogus file is in the Volume. An incremental update sees only that one new file.
    update = run_pipeline(pid)
    assert update["state"] == "COMPLETED", f"the malformed file broke the update: {update}"

    # Quarantined: kept as a row (not dropped, not duplicated), flagged in _rescued_data, small.
    bogus = query(f"""
        SELECT path, length,
               _rescued_data IS NOT NULL AS rescued,
               hex(substring(content, 1, 5)) AS magic,
               decode(content, 'UTF-8') AS text
        FROM {BRONZE}
        WHERE path LIKE '%/{MALFORMED_NAME}'
    """)
    assert len(bogus) == 1, f"expected exactly one bronze row for {MALFORMED_NAME}, got {bogus}"
    row = bogus[0]
    assert row["rescued"] == "true", "the malformed file is not flagged in _rescued_data"
    assert int(row["length"]) == len(MALFORMED_BYTES) < MAX_QUARANTINE_BYTES
    assert row["magic"] != PDF_MAGIC_HEX, "the malformed file looks like a PDF"
    assert row["text"] == MALFORMED_TEXT, "the bytes did not land intact"

    # The rest of the ingest succeeded: all real drawings are present, real PDFs, none flagged.
    valid = query(f"""
        SELECT count(*) AS n,
               count_if(hex(substring(content, 1, 5)) = '{PDF_MAGIC_HEX}') AS real_pdfs,
               count(_rescued_data) AS flagged
        FROM {BRONZE}
        WHERE path NOT LIKE '%/{MALFORMED_NAME}'
    """)[0]
    assert (int(valid["n"]), int(valid["real_pdfs"]), int(valid["flagged"])) == (
        VALID_DRAWINGS,
        VALID_DRAWINGS,
        0,
    )

    # Silver, the second dataset of the same update, handled the odd file name too.
    tracked = query(f"SELECT length FROM {SILVER} WHERE drawing_id = 'MALFORMED-TEST'")
    assert [int(r["length"]) for r in tracked] == [len(MALFORMED_BYTES)]
