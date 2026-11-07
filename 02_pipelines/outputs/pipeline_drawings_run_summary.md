# Drawings pipeline run summary

Auto Loader and Spark Declarative Pipelines (SDP) turn the 1,200 synthetic drawing PDFs in the landing Volume into one bronze streaming table (the files as bytes) and one silver materialized view (a tracking table keyed by drawing id), in one serverless pipeline (`02_pipelines/pipeline_drawings.py`, declared in `resources/pipeline-drawings.yml`). It sits beside the project-data pipeline ([summary](pipeline_project_run_summary.md)) and is the second half of the Lakeflow ingestion box.

| Field | Value |
|---|---|
| Pipeline | `bluerridge-pipeline-drawings` (bundle resource `pipeline_drawings`, target `demo`) |
| pipeline_id | `6201f0e1-ccb9-4768-bba8-adf2473245cd` |
| update_id | `b420d5ac-e9de-4c39-a6ad-0b8e7b624272` |
| State | COMPLETED |
| Mode | Triggered, serverless. `full_refresh = true`: the last step of the malformed-file test (below), which rebuilds both tables from the Volume after the test file was deleted. The code is the committed `pipeline_drawings.py` (sha256 `890e672c...`) |
| Created / completed (UTC) | 2026-11-07T03:32:04.727Z / 2026-11-07T03:32:59.772Z |
| duration_sec | 55.0 from update creation to COMPLETED; 19.6 of it in the RUNNING state, the rest is serverless start-up and the INITIALIZING, RESETTING and SETTING_UP_TABLES states |
| Pipeline page | https://fevm-mfg-mc-se-sa.cloud.databricks.com/pipelines/6201f0e1-ccb9-4768-bba8-adf2473245cd?w=7474644652812129 |
| Update page | https://fevm-mfg-mc-se-sa.cloud.databricks.com/#joblist/pipelines/6201f0e1-ccb9-4768-bba8-adf2473245cd/updates/b420d5ac-e9de-4c39-a6ad-0b8e7b624272 |
| Raw records | [`evidence/pipeline_run_logs/pipeline_drawings_run.json`](../../evidence/pipeline_run_logs/pipeline_drawings_run.json) (update record from `databricks pipelines get-update`), [`pipeline_drawings_run_metrics.json`](../../evidence/pipeline_run_logs/pipeline_drawings_run_metrics.json) (the numbers below, as JSON, read from the event log and the tables) |
| Test | [`02_pipelines/tests/test_malformed_drawing.py`](../tests/test_malformed_drawing.py) |

## Record counts

Every table was read back with `SELECT count(*)` after the update. "Expected" is the length of the generator's [`drawing_manifest.json`](../../01_synthetic_data/outputs/drawing_manifest.json), which is also the number of PDFs in the Volume. "Rows written" is the `num_output_rows` the update reported for the table's flow.

| Layer | Table | Type | Expected | Rows written | Rows in table | Match |
|---|---|---|---:|---:|---:|---|
| bronze | `bluerridge_bronze_drawings.raw_files` | streaming table | 1,200 | 1,200 (two micro-batches, 1,000 + 200) | 1,200 | yes |
| silver | `bluerridge_silver_engineering.drawings_raw_tracking` | materialized view | 1,200 | 1,200 | 1,200 | yes |

- **Bronze**: 1,200 rows on 1,200 distinct paths, all 1,200 start with the `%PDF-` header, sizes 4,591 to 15,640 bytes, 9,145,510 bytes in total (exactly what `read_files()` sees in the Volume). **Rescued-data count: 0 of 1,200.**
- **Silver**: 1,200 distinct `drawing_id`s, the same set as the manifest's, and `volume_path` equals the manifest's `volume_path` for all 1,200.
- Columns, bronze: `path STRING, modification_time TIMESTAMP, length BIGINT, content BINARY, _rescued_data STRING, _ingest_timestamp TIMESTAMP, _source_file STRING`. Silver: `drawing_id STRING, volume_path STRING, length BIGINT, modification_time TIMESTAMP, _source_file STRING`.

## Malformed-file test: quarantined, not crashed

The plan's first review focus is a non-PDF dropped into the drawings Volume. [`test_malformed_drawing.py`](../tests/test_malformed_drawing.py) drives it against the workspace (a live test, opt-in with `BLUERRIDGE_LIVE_TESTS=1`): upload `MALFORMED-TEST.pdf`, run the pipeline, assert on what landed, then always delete the file and full-refresh so the tables return to the 1,200 real drawings. It was written first and run red twice before it went green: once with `pipeline_drawings` not deployed, and once against the first deployed version (plain `binaryFile`, no rescue marker), where the update completed but the test failed because nothing flagged the file.

| Step | Result |
|---|---|
| Test file | `MALFORMED-TEST.pdf`, 58 bytes of plain text: `This is plain text renamed .pdf; it is not a PDF document.` |
| Update that ingested it | `f8c24c64-3632-4af3-86ec-a7b746aa3e3e`, incremental, COMPLETED in 57.1 s. Bronze wrote exactly 1 row (the one new file); silver wrote 1,201 |
| The bronze row | `path` `dbfs:/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/MALFORMED-TEST.pdf`, `length` 58, first bytes `5468697320697320` ("This is "), `content` intact, `_rescued_data` = `{"_file_path":"/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/MALFORMED-TEST.pdf","reason":"content does not start with the %PDF- header"}` |
| Bronze at that moment | 1,201 rows: 1,200 real PDFs with `_rescued_data` NULL, and 1 flagged (read back with `VERSION AS OF 22`) |
| Expectations in that update | `no_rescued_data` passed 0, failed 1 (warn-only: the row is kept); `drawing_id_present` passed 1,201, failed 0 |
| Cleanup | File deleted from the Volume, then a full refresh (`b420d5ac-...`, the update this document is about): bronze 1,200, silver 1,200, 0 flagged, 0 malformed files left in the Volume |

**What `_rescued_data` means for this source.** Auto Loader's `binaryFile` format has a fixed schema (`path`, `modificationTime`, `length`, `content`) and never parses the bytes, so it has nothing to rescue. Checked on the workspace: `cloudFiles.schemaEvolutionMode=rescue` is rejected (`CF_UNSUPPORTED_SCHEMA_EVOLUTION_MODE`, "Please set the schema evolution mode to 'none'"), and neither the default read nor `rescuedDataColumn` adds a `_rescued_data` column. A text file renamed `.pdf` is therefore an ordinary row, and it cannot fail the update. The pipeline sets `_rescued_data` itself, with the meaning the column has in the CSV bronze tables: NULL when the file starts with `%PDF-`, a small JSON (file path and reason) when it does not. The row is kept and nothing is dropped. Silver stays a plain passthrough, so the flagged file also appears there until the cleanup refresh; a consumer that wants only real PDFs filters bronze on `_rescued_data IS NULL`.

## Data quality

Bronze keeps everything the Volume holds, so its one rule only warns. Silver keeps the project pipeline's convention that a primary id must be present. Read from the event log (`flow_progress` events, `data_quality.expectations`), summed over a flow's micro-batches.

| Dataset | Expectation | Action | Rule | Passed | Failed | Same, in the malformed-file update |
|---|---|---|---|---:|---:|---|
| `raw_files` | `no_rescued_data` | WARN | `_rescued_data IS NULL` | 1,200 | 0 | 0 passed, 1 failed (the test file, kept) |
| `drawings_raw_tracking` | `drawing_id_present` | DROP | `drawing_id <> ''` | 1,200 | 0 | 1,201 passed, 0 failed |

Actions: **DROP** is `expect_or_drop` (the row is removed), **WARN** is `expect` (the row is kept and the violation is counted). Result for this update: 2 expectations, 0 failed records, 0 dropped rows, update not failed.

## How it is wired

- **API**: `from pyspark import pipelines as dp`, with `@dp.table` (bronze streaming table), `@dp.materialized_view` (silver), `@dp.expect` and `@dp.expect_or_drop`.
- **Auto Loader**: `cloudFiles.format=binaryFile`, `cloudFiles.schemaEvolutionMode=none`, `pathGlobFilter=*.pdf`, loading the Volume folder `/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings`. Bronze renames `modificationTime` to `modification_time` and adds `_rescued_data`, `_ingest_timestamp` and `_source_file`.
- **One pipeline, two schemas**: as in the project pipeline, the default schema is `bluerridge_bronze_drawings` and the silver dataset carries the fully-qualified name `mfg_mc_se_sa.bluerridge_silver_engineering.drawings_raw_tracking`. The silver schema also holds the project pipeline's six views; they were not touched (the deploy reported that pipeline unchanged).
- **Silver**: `drawing_id` is `regexp_extract(path, '/([^/]+)\.pdf$', 1)`; `volume_path` is `path` without the `dbfs:` scheme (binaryFile reports `dbfs:/Volumes/...`, the manifest and the Files API use `/Volumes/...`); the bytes are left in bronze.
- **Re-runs**: Auto Loader reads each file path once, so a plain update after the load adds nothing: update `185df85d-...` ran with nothing new and wrote no bronze rows (no new table version), and the counts stayed 1,200 bronze rows on 1,200 distinct paths and 1,200 silver rows. A deleted file keeps its bronze row until a full refresh, which is why the test ends with one. After regenerating the PDFs with different content, run `databricks bundle run pipeline_drawings -t demo --full-refresh-all --profile DEFAULT`.

## Updates of this pipeline

Twelve updates, 11 COMPLETED and 1 FAILED. Code versions: **v0** = `schemaEvolutionMode=rescue`; **v1** = `none`, a `pdf_magic_header` expectation, no `_rescued_data`; **v2** = adds the `_rescued_data` marker and `no_rescued_data` (replacing `pdf_magic_header`); **final** = v2 with the marker expression moved into a helper and lines wrapped, no change in behavior (the committed file).

| update_id | Code | What | Outcome |
|---|---|---|---|
| `39c29008-b85f-4315-becd-ede4dffafbef` | v0 | `--validate-only` dry run | **FAILED**: `CF_UNSUPPORTED_SCHEMA_EVOLUTION_MODE`, rescue mode is not supported for binaryFile. Fixed by `none` |
| `5c545b2f-a440-4e6c-a71e-99aec47f25d1` | v1 | `--validate-only` | Graph valid: 1 streaming table and 1 materialized view |
| `195e3ef3-a100-4ab7-b329-3e69be05a4e1` | v1 | Initial load | 1,200 bronze rows (1,000 + 200), 1,200 silver |
| `fafae720-f0c1-483c-ac63-d2a56723cad4` | v1 | Test, first run: incremental with the test file | COMPLETED, 1 bronze row; the test went red on the missing `_rescued_data` |
| `bff366e9-d261-4844-938b-1545f2df8995` | v1 | Test cleanup, full refresh | 1,200 and 1,200 |
| `c6962b46-0222-4487-a61e-3ce10b7c4dda` | v2 | `--validate-only` | Graph valid |
| `0b77c6ca-299f-47b0-a69f-6fc1869cfd85` | v2 | Full refresh | 1,200 and 1,200 with the `_rescued_data` column, 0 flagged |
| `7e697950-a284-44cd-b232-d4922531358a` | v2 | Test, green: incremental with the test file | COMPLETED, 1 bronze row, flagged |
| `4f13035e-2fdb-4f7c-b2af-fe29d458562a` | v2 | Test cleanup, full refresh | 1,200 and 1,200 |
| `f8c24c64-3632-4af3-86ec-a7b746aa3e3e` | final | Test, green: incremental with the test file | COMPLETED, 1 bronze row, flagged (table above) |
| `b420d5ac-e9de-4c39-a6ad-0b8e7b624272` | final | Test cleanup, full refresh (this document) | 1,200 and 1,200, 0 flagged |
| `185df85d-c65e-4557-b955-842815c242b2` | final | Plain update, nothing new | COMPLETED, no bronze rows written, counts unchanged |

## How these numbers were read

```sql
-- rows written and expectation results for one update
SELECT origin.flow_name, details:flow_progress.metrics.num_output_rows,
       details:flow_progress.data_quality.dropped_records,
       details:flow_progress.data_quality.expectations
FROM event_log('6201f0e1-ccb9-4768-bba8-adf2473245cd')
WHERE event_type = 'flow_progress' AND origin.update_id = 'b420d5ac-e9de-4c39-a6ad-0b8e7b624272'
  AND (details:flow_progress.metrics.num_output_rows IS NOT NULL
       OR details:flow_progress.data_quality.expectations IS NOT NULL);

-- rows in bronze, rows with the PDF header, rescued rows
SELECT count(*), count_if(hex(substring(content, 1, 5)) = '255044462D'), count(_rescued_data)
FROM mfg_mc_se_sa.bluerridge_bronze_drawings.raw_files;

-- the test file's row, from the table version the incremental update wrote
SELECT path, length, _rescued_data FROM mfg_mc_se_sa.bluerridge_bronze_drawings.raw_files
VERSION AS OF 22 WHERE path LIKE '%MALFORMED%';
```
