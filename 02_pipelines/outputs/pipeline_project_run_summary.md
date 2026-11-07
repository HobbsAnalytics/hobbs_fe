# Project pipeline run summary

Auto Loader and Spark Declarative Pipelines (SDP) turn the six synthetic project CSVs in the landing Volume into six bronze streaming tables and six silver materialized views, in one serverless pipeline (`02_pipelines/pipeline_project.py`, declared in `resources/pipeline-project.yml`).

| Field | Value |
|---|---|
| Pipeline | `bluerridge-pipeline-project` (bundle resource `pipeline_project`, target `demo`) |
| pipeline_id | `1d76045d-1abc-47f3-8336-f3bc6eb8d077` |
| update_id | `9cc6e9fa-047e-4da2-9e0f-444e6b3ae099` |
| State | COMPLETED |
| Mode | Triggered, serverless. `full_refresh = true`: a reload of all six files from the Volume. The initial load (update `0dd33b4c-2db0-45a9-9c3d-aafa7bc22274`, same code apart from two table comments) produced the same twelve row counts |
| Created / completed (UTC) | 2026-11-07T02:41:15.682Z / 2026-11-07T02:42:23.411Z |
| duration_sec | 67.7 from update creation to COMPLETED; 17.7 of it in the RUNNING state, the rest is serverless start-up and the INITIALIZING, RESETTING and SETTING_UP_TABLES states |
| Pipeline page | https://fevm-mfg-mc-se-sa.cloud.databricks.com/pipelines/1d76045d-1abc-47f3-8336-f3bc6eb8d077?w=7474644652812129 |
| Update page | https://fevm-mfg-mc-se-sa.cloud.databricks.com/#joblist/pipelines/1d76045d-1abc-47f3-8336-f3bc6eb8d077/updates/9cc6e9fa-047e-4da2-9e0f-444e6b3ae099 |
| Raw records | [`evidence/pipeline_run_logs/pipeline_project_run.json`](../../evidence/pipeline_run_logs/pipeline_project_run.json) (update record from `databricks pipelines get-update`), [`pipeline_project_run_metrics.json`](../../evidence/pipeline_run_logs/pipeline_project_run_metrics.json) (the numbers below, as JSON) |
| Table schemas | [`pipeline_project_schema.json`](pipeline_project_schema.json) |

## Record counts

Every table was read back with `SELECT count(*)` after the update and compared with the generator's [`row_counts.json`](../../01_synthetic_data/outputs/row_counts.json). "Rows written" is the `num_output_rows` the update reported for the table's flow.

| Layer | Table | Type | Expected | Rows written | Rows in table | Match |
|---|---|---|---:|---:|---:|---|
| bronze | `bluerridge_bronze_project.schedule_raw` | streaming table | 500 | 500 | 500 | yes |
| bronze | `bluerridge_bronze_project.cost_raw` | streaming table | 120 | 120 | 120 | yes |
| bronze | `bluerridge_bronze_project.ncrs_raw` | streaming table | 80 | 80 | 80 | yes |
| bronze | `bluerridge_bronze_project.change_orders_raw` | streaming table | 20 | 20 | 20 | yes |
| bronze | `bluerridge_bronze_project.safety_log_raw` | streaming table | 400 | 400 | 400 | yes |
| bronze | `bluerridge_bronze_project.daily_reports_raw` | streaming table | 180 | 180 | 180 | yes |
| silver | `bluerridge_silver_engineering.schedule` | materialized view | 500 | 500 | 500 | yes |
| silver | `bluerridge_silver_engineering.cost` | materialized view | 120 | 120 | 120 | yes |
| silver | `bluerridge_silver_engineering.ncrs` | materialized view | 80 | 80 | 80 | yes |
| silver | `bluerridge_silver_engineering.change_orders` | materialized view | 20 | 20 | 20 | yes |
| silver | `bluerridge_silver_engineering.safety_log` | materialized view | 400 | 400 | 400 | yes |
| silver | `bluerridge_silver_engineering.daily_reports` | materialized view | 180 | 180 | 180 | yes |

All twelve tables hold exactly the generated rows: 1,300 bronze and 1,300 silver. No bronze row has anything in `_rescued_data` (0 of 1,300), so every value parsed into its inferred type.

## Data quality

Bronze has no constraints by design: it keeps whatever the source sent. Silver carries 15 expectations, read from the update's event log (`flow_progress` events, `data_quality.expectations`).

| Silver table | Expectation | Action | Rule | Passed | Failed |
|---|---|---|---|---:|---:|
| `schedule` | `milestone_id_not_null` | DROP | `milestone_id IS NOT NULL` | 500 | 0 |
| `schedule` | `discipline_in_vocabulary` | FAIL | `discipline IN ('mechanical', 'electrical', 'structural', 'piping', 'instr')` | 500 | 0 |
| `schedule` | `planned_dates_ordered` | WARN | `planned_end >= planned_start` | 500 | 0 |
| `cost` | `cost_id_not_null` | DROP | `cost_id IS NOT NULL` | 120 | 0 |
| `cost` | `variance_is_eac_minus_budget` | WARN | `variance_usd = eac_usd - budget_usd` | 120 | 0 |
| `cost` | `amounts_not_negative` | WARN | `budget_usd >= 0 AND committed_usd >= 0 AND actual_usd >= 0` | 120 | 0 |
| `ncrs` | `ncr_id_not_null` | DROP | `ncr_id IS NOT NULL` | 80 | 0 |
| `ncrs` | `closed_not_before_raised` | WARN | `closed_date IS NULL OR closed_date >= raised_date` | 80 | 0 |
| `change_orders` | `co_id_not_null` | DROP | `co_id IS NOT NULL` | 20 | 0 |
| `change_orders` | `decided_not_before_requested` | WARN | `decided_date IS NULL OR decided_date >= requested_date` | 20 | 0 |
| `safety_log` | `log_id_not_null` | DROP | `log_id IS NOT NULL` | 400 | 0 |
| `safety_log` | `days_lost_not_negative` | WARN | `days_lost >= 0` | 400 | 0 |
| `daily_reports` | `report_id_not_null` | DROP | `report_id IS NOT NULL` | 180 | 0 |
| `daily_reports` | `report_date_not_null` | DROP | `report_date IS NOT NULL` | 180 | 0 |
| `daily_reports` | `headcount_positive` | WARN | `headcount > 0` | 180 | 0 |

Actions: **DROP** is `expect_or_drop` (the row is removed), **FAIL** is `expect_or_fail` (the update fails), **WARN** is `expect` (the row is kept and the violation is counted).

Result: 15 expectations, 0 failed records, 0 dropped rows, update not failed. The synthetic data is clean, so each expectation passes for every row; the drop and fail paths were not exercised in this run (no bad rows were injected into the production Volume to force them).

## How it is wired

- **API**: `from pyspark import pipelines as dp`, with `@dp.table` (bronze streaming tables), `@dp.materialized_view` (silver) and `@dp.expect_or_drop` / `@dp.expect_or_fail` / `@dp.expect` / `@dp.expect_all_or_drop`.
- **Auto Loader**: `cloudFiles.format=csv`, `cloudFiles.inferColumnTypes=true`, `cloudFiles.schemaEvolutionMode=addNewColumns`, `header=true`, `rescuedDataColumn=_rescued_data`. Each stream loads the Volume folder `/Volumes/mfg_mc_se_sa/bluerridge_landing/project` with `pathGlobFilter=<dataset>.csv`, because Auto Loader reads directories (pointing `load()` at the file itself fails with "is not a directory"). Bronze adds `_ingest_timestamp` and `_source_file`.
- **One pipeline, two schemas**: the pipeline's default schema is `bluerridge_bronze_project`; the silver datasets are declared with the fully-qualified name `mfg_mc_se_sa.bluerridge_silver_engineering.<table>`. The CLI and the platform accepted this, so the two-pipeline fallback was not needed.
- **Silver**: explicit types (dates, `INT`, `BIGINT` for whole-dollar amounts, `BOOLEAN`), trimmed strings with blanks as NULL, lower-cased enumerations, lineage columns kept, `_rescued_data` left behind. `schedule` also gets `slip_days` and `depends_on_ids`.
- **Re-runs**: Auto Loader reads each file path once, so a plain update after the first load adds nothing (see the table below). After regenerating the CSVs with different content, run `databricks bundle run pipeline_project -t demo --full-refresh-all --profile DEFAULT`.

## Other updates of this pipeline

All COMPLETED. After the first dry run the module changed only in table comments, code comments and formatting, never in datasets, options, expressions or expectations.

| update_id | What | Outcome |
|---|---|---|
| `af16957e-6c83-4021-ba13-93557ce97f8c` | `--validate-only` dry run | Graph valid: 6 streaming tables and 6 materialized views, written to two schemas |
| `0dd33b4c-2db0-45a9-9c3d-aafa7bc22274` | Initial load | The same twelve counts as above, 0 dropped |
| `ccde86ad-f88b-469c-866e-fa42ea48290a` | Re-run with no new files | Counts unchanged: no duplicates |
| `ba13c9e3-a676-49ad-9b67-51da3ee721a2` | Re-run after rewriting `schedule.csv` with identical bytes (new modification time) | `schedule_raw` still 500 rows, 500 distinct `milestone_id`: a touched file is not re-read |
| `9cc6e9fa-047e-4da2-9e0f-444e6b3ae099` | Full refresh (this document) | Twelve tables rebuilt from the Volume |
| `965b2418-3741-4bcd-aece-cab8f89d83e8` | `--validate-only` on the committed file, run after the last comment and formatting edits | Graph valid, so the committed bytes load |

## How these numbers were read

```sql
-- rows written and expectation results for this update
SELECT origin.flow_name, details:flow_progress.metrics.num_output_rows,
       details:flow_progress.data_quality.dropped_records,
       details:flow_progress.data_quality.expectations
FROM event_log('1d76045d-1abc-47f3-8336-f3bc6eb8d077')
WHERE event_type = 'flow_progress' AND origin.update_id = '9cc6e9fa-047e-4da2-9e0f-444e6b3ae099'
  AND (details:flow_progress.metrics.num_output_rows IS NOT NULL
       OR details:flow_progress.data_quality.expectations IS NOT NULL);

-- rows in each table, and rescued bronze rows
SELECT count(*), sum(CASE WHEN _rescued_data IS NOT NULL THEN 1 ELSE 0 END)
FROM mfg_mc_se_sa.bluerridge_bronze_project.schedule_raw;   -- likewise for the other eleven tables
```
