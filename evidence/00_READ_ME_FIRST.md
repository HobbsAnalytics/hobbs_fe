# Evidence tour: start here

This repository is graded by reading it, not by running it. Each FE Bar component below links to the committed files that prove it ran.

How to read it:

1. Find the box in the table below and open its headline artifact.
2. To see how the data was produced, open the executed notebook (listed at the bottom). Outputs are embedded in the `.ipynb`, which GitHub renders. Each executed notebook records the Databricks job run id and run URL in its metadata and has an HTML export in [`notebook_html_exports/`](notebook_html_exports/).
3. Everything is synthetic. Workspace `https://fevm-mfg-mc-se-sa.cloud.databricks.com`, catalog `mfg_mc_se_sa`, schemas `bluerridge_*`.

Status key: **☑ done** means the file is committed and the link resolves. **☐ pending** means the path is planned and the file has not been produced yet.

## At a glance

| # | FE Bar box | Headline proof | Status |
|---|---|---|---|
| 1 | Lakeflow ingestion | [`02_pipelines/outputs/pipeline_project_run_summary.md`](../02_pipelines/outputs/pipeline_project_run_summary.md) (project data) and [`02_pipelines/outputs/pipeline_drawings_run_summary.md`](../02_pipelines/outputs/pipeline_drawings_run_summary.md) (drawing PDFs) | ☑ done |
| 2 | Unity Catalog governance | [`evidence/grant_listing.md`](grant_listing.md) | ☑ done |
| 3 | Lakebase | [`08_lakebase/outputs/synced_tables_listing.md`](../08_lakebase/outputs/synced_tables_listing.md) | ☐ pending |
| 4 | GenAI: document intelligence | [`evidence/sample_compliance_outputs/compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md) | ☑ done |
| 5 | ML: schedule-risk forecast | [`evidence/risk_model_metrics.json`](risk_model_metrics.json) | ☑ done |
| 6 | Genie Agent | [`evidence/genie_qa_transcript.md`](genie_qa_transcript.md) | ☑ done |
| 7 | Databricks App | [`evidence/app_demo.mp4`](app_demo.mp4) and [`evidence/app_screenshots/`](app_screenshots/) | ☐ pending |
| 8 | One-command deploy | [`evidence/deploy_transcript.txt`](deploy_transcript.txt) | ☐ pending |

## Foundation: Unity Catalog layout

Not an FE Bar box, but everything below writes into these objects.

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`00_setup/outputs/schemas_listing.md`](../00_setup/outputs/schemas_listing.md) | The seven `bluerridge_*` schemas and the Volumes `drawings` and `project` exist in `mfg_mc_se_sa` (live listing written by the setup notebook) |

## Synthetic data (feeds boxes 1 and 4)

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`01_synthetic_data/outputs/row_counts.json`](../01_synthetic_data/outputs/row_counts.json) | Row counts of the six synthetic project datasets |
| ☑ done | [`01_synthetic_data/outputs/sample_*.csv`](../01_synthetic_data/outputs/) | Five-row samples of each project dataset |
| ☑ done | [`01_synthetic_data/outputs/drawing_manifest.json`](../01_synthetic_data/outputs/drawing_manifest.json) | The 1,200 generated drawing PDFs: id, discipline, revision, type (ISO, PID, GA, SPEC, OTHER), Volume path, whether a flaw was planted (240 are flawed) |
| ☑ done | [`01_synthetic_data/outputs/ground_truth_findings.jsonl`](../01_synthetic_data/outputs/ground_truth_findings.jsonl) | The 274 planted flaws, one line each, with page, bounding box and code citation: what the compliance judge is scored against |
| ☑ done | [`01_synthetic_data/outputs/spot_check/`](../01_synthetic_data/outputs/spot_check/) | Three drawings copied back from the Volume with their ground-truth boxes outlined in red (a three-flaw P&ID, a flaw on a second sheet, an under-width exit), showing the boxes sit on the planted elements |

## 1. Lakeflow ingestion (Auto Loader + Spark Declarative Pipelines)

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`02_pipelines/outputs/pipeline_project_run_summary.md`](../02_pipelines/outputs/pipeline_project_run_summary.md) | Project pipeline run: id, duration, row counts for all twelve bronze and silver tables, data-quality results |
| ☑ done | [`02_pipelines/outputs/pipeline_drawings_run_summary.md`](../02_pipelines/outputs/pipeline_drawings_run_summary.md) | Drawings pipeline run: id, duration, row counts for the bronze table and the silver view, data-quality results, and the malformed-file test with the quarantined row |
| ☑ done | [`02_pipelines/outputs/pipeline_project_schema.json`](../02_pipelines/outputs/pipeline_project_schema.json) | Table schemas the project pipeline produced |
| ☑ done | [`evidence/pipeline_run_logs/pipeline_project_run.json`](pipeline_run_logs/pipeline_project_run.json) | Raw pipeline update record for the project run |
| ☑ done | [`evidence/pipeline_run_logs/pipeline_project_run_metrics.json`](pipeline_run_logs/pipeline_project_run_metrics.json) | The project run's numbers as JSON, read from the pipeline event log: rows written, rows dropped and every expectation's passed and failed counts per table, plus the update's state timeline |
| ☑ done | [`evidence/pipeline_run_logs/pipeline_drawings_run.json`](pipeline_run_logs/pipeline_drawings_run.json) | Raw pipeline update record for the drawings run |
| ☑ done | [`evidence/pipeline_run_logs/pipeline_drawings_run_metrics.json`](pipeline_run_logs/pipeline_drawings_run_metrics.json) | The drawings run's numbers as JSON, read from the pipeline event log and the tables: rows written and every expectation's passed and failed counts per table for the malformed-file update, the clean rebuild and a no-op update, the update state timelines, and the quarantined row itself |
| ☑ done | [`02_pipelines/tests/test_malformed_drawing.py`](../02_pipelines/tests/test_malformed_drawing.py) | A non-PDF dropped into the drawings Volume is flagged in `_rescued_data` and kept instead of crashing the run (a live workspace test, opt-in with `BLUERRIDGE_LIVE_TESTS=1`; its result is in the drawings run summary) |

## 2. Unity Catalog governance

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`00_setup/outputs/schemas_listing.md`](../00_setup/outputs/schemas_listing.md) | The governed schemas and Volumes exist, owned by the builder |
| ☑ done | [`evidence/grant_listing.md`](grant_listing.md) | `SHOW GRANTS` for every `bluerridge_*` schema, the 112 tags applied, the row filter on `drawing_register` with its allow/deny demo, and the groups outcome (account groups not possible, no direct broad grants), and the inherited account-wide read access from the catalog |
| ☑ done | [`06_governance/outputs/lineage_edges.md`](../06_governance/outputs/lineage_edges.md) | 27 de-duplicated lineage edges, bronze to silver to gold, with the `compliance_findings` and `kpi_daily` paths |
| ☑ done | [`06_governance/`](../06_governance/) (`tags.sql`, `grants.sql`, `row_filters.sql`) | The exact statements that were applied |

## 3. Lakebase

| Status | Artifact | What it proves |
|---|---|---|
| ☐ pending | [`08_lakebase/outputs/synced_tables_listing.md`](../08_lakebase/outputs/synced_tables_listing.md) | Instance `bluerridge-pm`, its three synced tables in state AVAILABLE, a row count read back over Postgres for each, and the read-write DNS |

## 4. GenAI: document intelligence

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`03_doc_intelligence/outputs/sample_parsed.md`](../03_doc_intelligence/outputs/sample_parsed.md) | One drawing, `BRL-INS-PID-0052` (a P&ID with three planted flaws), as `ai_parse_document` parsed it: the `parsed_markdown` stored in `drawings_parsed`, the pixel box of every element and the element each planted flaw falls in. The notebook under "Executed notebooks" parsed all 1,200 drawings with no errors |
| ☑ done | [`03_doc_intelligence/outputs/sample_extracted.jsonl`](../03_doc_intelligence/outputs/sample_extracted.jsonl) | Ten rows of `drawings_extracted`, one JSON object per line, covering all five disciplines and all five drawing types: the title block fields and cited standards `ai_extract` returned and the type `ai_classify` chose. The notebook under "Executed notebooks" ran both functions over all 1,200 drawings with no failed call and scored the answers against the generator's records: drawing type 1,200 of 1,200 right, revision 1,200, discipline 1,198 (two NULL), drawing number 1,193 (the misses are listed in the notebook) |
| ☑ done | [`03_doc_intelligence/outputs/sample_findings.jsonl`](../03_doc_intelligence/outputs/sample_findings.jsonl) | Twenty compliance-judge findings covering pass, fail and review (after the rule-applicability and consistency guardrails) |
| ☑ done | [`03_doc_intelligence/outputs/sample_suppressed.jsonl`](../03_doc_intelligence/outputs/sample_suppressed.jsonl) | Three rows of `compliance_suppressed`: judge entries that a guardrail removed (rule applicability, expected item present in the drawing text, reason that admits compliance), kept apart from the findings |
| ☑ done | [`03_doc_intelligence/outputs/submit_payloads/`](../03_doc_intelligence/outputs/submit_payloads/) | The exact `jobs submit` requests of the judge run, the guardrails run and the scoring run, each with `disable_auto_optimization: true` (`get-run` does not return the flag, so the request is the proof) |
| ☑ done | [`evidence/sample_compliance_outputs/compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md) | The scorecard of the AI compliance judge against the 274 planted flaws: headline precision / recall / F1 (final table: 58.1% / 81.0% / 67.7%), per-flaw-type table, A/B/C columns, prompt lineage (v2 flagged as superseded for integrity), drawing-level and as-of-week confusion, per-drawing-type results, wins and losses, false-positive causes, MLflow experiment and run ids, the non-determinism note |
| ☑ done | [`04_vector_search/outputs/corpus_sample.md`](../04_vector_search/outputs/corpus_sample.md) | The code-excerpt corpus behind the Vector Search index |
| ☑ done | [`04_vector_search/outputs/sample_query.md`](../04_vector_search/outputs/sample_query.md) | A live index query for "flange rating" returning `ASME B16.5 §4.2` |
| ☑ done | [`05_gold/outputs/daily_brief_today.md`](../05_gold/outputs/daily_brief_today.md) | The `ai_query` narrator's daily brief |

## 5. ML: schedule-risk forecast

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`evidence/risk_model_metrics.json`](risk_model_metrics.json) | Mean absolute error and bias of the `ai_forecast` schedule-slip model |
| ☑ done | [`05_gold/outputs/risk_top5.md`](../05_gold/outputs/risk_top5.md) | The top 5 schedule risks in PM language, with the method in two sentences |
| ☑ done | [`05_gold/outputs/submit_payloads/02_submit.json`](../05_gold/outputs/submit_payloads/02_submit.json) | The one-time `jobs submit` payload that produced the notebook's evidence run, with `{{job.run_id}}` passed in |
| ☑ done | [`resources/job-risk-forecast.yml`](../resources/job-risk-forecast.yml) | The deployed weekly refresh job `bluerridge-risk-forecast` (id 563080592506156): schedule PAUSED, never run |
| ☑ done | [`05_gold/outputs/risk_forecast_chart.png`](../05_gold/outputs/risk_forecast_chart.png) | Forecast against history with the interval band and the backtest overlay |
| ☑ done | [`05_gold/outputs/kpi_today.md`](../05_gold/outputs/kpi_today.md) | The gold KPI row the app's KPI strip reads |

## 6. Genie Agent

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`evidence/genie_qa_transcript.md`](genie_qa_transcript.md) | Fifteen questions (10 curated, 5 held-out and never loaded into the space) asked through the Genie Conversation API: Genie's answer, generated SQL, first five result rows, expected answer and a rule-based verdict. Curated 10/10, held-out 5/5 |
| ☑ done | [`07_genie_agent/sample_questions.md`](../07_genie_agent/sample_questions.md) | The curated ten questions with verified SQL and the result of running it |
| ☑ done | [`07_genie_agent/heldout_questions.md`](../07_genie_agent/heldout_questions.md) | The five held-out questions with verified SQL (not loaded into the space) |
| ☑ done | [`resources/genie-space.yml`](../resources/genie-space.yml) | The space as a bundle resource (`genie_spaces`), definition in [`genie_space.geniespace.json`](../07_genie_agent/genie_space.geniespace.json) |
| ☑ done | [`07_genie_agent/outputs/space_id.txt`](../07_genie_agent/outputs/space_id.txt) | The deployed Genie Space's ID |

## 7. Databricks App

| Status | Artifact | What it proves |
|---|---|---|
| ☐ pending | [`evidence/app_screenshots/`](app_screenshots/) | `01_copilot_home.png`, `02_assistant_response_with_sources.png`, `03_compliance_page.png`, `04_pdf_viewer_highlighted.png`, `05_right_rail.png` from the deployed app |
| ☐ pending | [`evidence/app_demo.mp4`](app_demo.mp4) | A 60 to 90 second run-through: open, read the brief, ask a question, click a drawing citation, see the highlighted PDF |
| ☐ pending | [`09_app/backend/AUTH_NOTES.md`](../09_app/backend/AUTH_NOTES.md) | The on-behalf-of auth research memo that preceded the auth code |
| ☐ pending | [`evidence/mockups/`](mockups/) | The design mockups the UI was built against |

## 8. One-command deploy

| Status | Artifact | What it proves |
|---|---|---|
| ☑ done | [`databricks.yml`](../databricks.yml) | The bundle definition, which passes `databricks bundle validate --profile DEFAULT` |
| ☑ done | [`docs/BUILD.md`](../docs/BUILD.md) | The deploy sequence and the recipe for executing notebooks |
| ☐ pending | [`evidence/deploy_transcript.txt`](deploy_transcript.txt) | `databricks bundle deploy -t demo` run end to end |

## Executed notebooks

Each has its outputs embedded in the `.ipynb` and an HTML export of the same run.

| Status | Notebook | HTML export | Box |
|---|---|---|---|
| ☑ done | [`00_setup/00_create_schemas_and_volumes.ipynb`](../00_setup/00_create_schemas_and_volumes.ipynb) | [html](notebook_html_exports/00_create_schemas_and_volumes.html) | Foundation |
| ☑ done | [`01_synthetic_data/01_generate_project_data.ipynb`](../01_synthetic_data/01_generate_project_data.ipynb) | [html](notebook_html_exports/01_generate_project_data.html) | 1, 4 |
| ☑ done | [`01_synthetic_data/02_generate_drawings.ipynb`](../01_synthetic_data/02_generate_drawings.ipynb) | [html](notebook_html_exports/02_generate_drawings.html) | 1, 4 |
| ☑ done | [`03_doc_intelligence/01_parse_drawings.ipynb`](../03_doc_intelligence/01_parse_drawings.ipynb) | [html](notebook_html_exports/01_parse_drawings.html) | 4 |
| ☑ done | [`03_doc_intelligence/02_extract_classify.ipynb`](../03_doc_intelligence/02_extract_classify.ipynb) | [html](notebook_html_exports/02_extract_classify.html) | 4 |
| ☑ done | [`03_doc_intelligence/03_compliance_check.ipynb`](../03_doc_intelligence/03_compliance_check.ipynb) | [html](notebook_html_exports/03_compliance_check.html) | 4 |
| ☑ done | [`03_doc_intelligence/03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb) | [html](notebook_html_exports/03b_compliance_guardrails.html) | 4 |
| ☑ done | [`03_doc_intelligence/04_ground_truth_scoring.ipynb`](../03_doc_intelligence/04_ground_truth_scoring.ipynb) | [html](notebook_html_exports/04_ground_truth_scoring.html) | 4 |
| ☑ done | [`04_vector_search/01_load_code_excerpts.ipynb`](../04_vector_search/01_load_code_excerpts.ipynb) | [html](notebook_html_exports/01_load_code_excerpts.html) | 4 |
| ☑ done | [`04_vector_search/02_create_endpoint_and_index.ipynb`](../04_vector_search/02_create_endpoint_and_index.ipynb) | [html](notebook_html_exports/02_create_endpoint_and_index.html) | 4 |
| ☑ done | [`05_gold/01_kpi_daily.ipynb`](../05_gold/01_kpi_daily.ipynb) | [html](notebook_html_exports/01_kpi_daily.html) | 5 |
| ☑ done | [`05_gold/02_risk_forecast.ipynb`](../05_gold/02_risk_forecast.ipynb) | [html](notebook_html_exports/02_risk_forecast.html) | 5 |
| ☑ done | [`05_gold/03_daily_brief.ipynb`](../05_gold/03_daily_brief.ipynb) | [html](notebook_html_exports/03_daily_brief.html) | 4 |
| ☑ done | [`06_governance/apply.ipynb`](../06_governance/apply.ipynb) | [html](notebook_html_exports/apply_governance.html) | 2 |
| ☑ done | [`07_genie_agent/01_create_space.ipynb`](../07_genie_agent/01_create_space.ipynb) | [html](notebook_html_exports/01_create_space.html) | 6 |
| ☑ done | [`07_genie_agent/02_run_sample_qa.ipynb`](../07_genie_agent/02_run_sample_qa.ipynb) | [html](notebook_html_exports/02_run_sample_qa.html) | 6 |
| ☐ pending | [`08_lakebase/01_create_instance.ipynb`](../08_lakebase/01_create_instance.ipynb) | [html](notebook_html_exports/01_create_instance.html) | 3 |

How a notebook is executed and captured is described in [`docs/BUILD.md`](../docs/BUILD.md#running-a-notebook-so-its-outputs-are-real).
