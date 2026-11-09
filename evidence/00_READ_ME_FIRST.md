# Evidence tour: start here

1. **What this is:** a Databricks Project Manager Co-Pilot for a fictional Bechtel-style LNG build, *Blue Ridge LNG Terminal, Phase 2*. GenAI audits 1,200 synthetic engineering drawings against five code rules, and a React + FastAPI Databricks App serves the results to the PM. The app includes a Genie chat that runs as the signed-in user.
2. **How to verify it without running anything:** every link below is a committed file produced by a real run. Executed notebooks keep their cell outputs, with the job run id and run URL in the notebook metadata. Pipeline summaries are read from the event log. App evidence is app-log excerpts. Each line says what the file shows.
3. **Where it ran:** workspace `https://fevm-mfg-mc-se-sa.cloud.databricks.com`, catalog `mfg_mc_se_sa`, schemas `bluerridge_*`. App `bluerridge-pm-copilot` is RUNNING at `https://bluerridge-pm-copilot-7474644652812129.aws.databricksapps.com` (sign-in required).
4. **Status:** all six FE Bar boxes are ☑ (box 4, ML or GenAI, is shown as two rows). The final deploy check is in [`deploy_transcript.md`](deploy_transcript.md): bundle validate, the idempotent grants re-run, app state, the boot self-test, the live signed-in chat, and tests.
5. **Read the limits too:** [Honest limitations](#honest-limitations), at the bottom, lists what is synthetic, approximate or in preview.

## At a glance

| # | FE Bar box | Headline proof | Status |
|---|---|---|---|
| 1 | Lakeflow ingestion | [`02_pipelines/outputs/pipeline_project_run_summary.md`](../02_pipelines/outputs/pipeline_project_run_summary.md) | ☑ |
| 2 | Unity Catalog governance | [`evidence/grant_listing.md`](grant_listing.md) | ☑ |
| 3 | Lakebase serving | [`08_lakebase/outputs/synced_tables_listing.md`](../08_lakebase/outputs/synced_tables_listing.md) | ☑ |
| 4 | ML: schedule-risk forecast | [`evidence/risk_model_metrics.json`](risk_model_metrics.json) | ☑ |
| 5 | GenAI: document intelligence and the daily brief | [`evidence/sample_compliance_outputs/compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md) | ☑ |
| 6 | Genie Agent | [`evidence/genie_qa_transcript.md`](genie_qa_transcript.md) | ☑ |
| 7 | Databricks App | [`09_app/outputs/live_obo_chat.md`](../09_app/outputs/live_obo_chat.md) | ☑ |

The rubric has six boxes. Box 4 is "ML or GenAI" (one box), and this tour shows it as two rows (4 and 5) because both were built. The row numbers 1 to 7 are rows of this tour, not seven boxes.

## 1. Lakeflow ingestion (Auto Loader + Spark Declarative Pipelines)

| Status | File | What it shows |
|---|---|---|
| ☑ | [`02_pipelines/outputs/pipeline_project_run_summary.md`](../02_pipelines/outputs/pipeline_project_run_summary.md) | Project pipeline run summary, update `9cc6e9fa…`. Six CSVs land in 6 bronze streaming tables and 6 silver materialized views, 1,300 rows per layer, each equal to the generator's count. 15 expectations, 0 failed records. All 8 updates of the pipeline are listed, including the one FAILED dry run |
| ☑ | [`02_pipelines/outputs/pipeline_drawings_run_summary.md`](../02_pipelines/outputs/pipeline_drawings_run_summary.md) | Drawings pipeline run summary, update `b420d5ac…`. 1,200 PDFs land in `raw_files` (bronze) and `drawings_raw_tracking` (silver), 1,200 rows each. Includes the malformed-file test: a non-PDF is flagged and kept, and the run does not crash |
| ☑ | [`evidence/pipeline_run_logs/pipeline_project_run_metrics.json`](pipeline_run_logs/pipeline_project_run_metrics.json), [`pipeline_drawings_run_metrics.json`](pipeline_run_logs/pipeline_drawings_run_metrics.json) | The same numbers as raw JSON from the pipeline event logs: rows written, rows dropped, and passed and failed counts for every expectation, per table |
| ☑ | [`02_pipelines/pipeline_project.py`](../02_pipelines/pipeline_project.py), [`resources/pipeline-project.yml`](../resources/pipeline-project.yml) | The SDP code (`@dp.table`, `@dp.materialized_view`, `@dp.expect_or_drop` / `expect_or_fail` / `expect`) and its bundle resource |
| ☑ | [`02_pipelines/tests/test_malformed_drawing.py`](../02_pipelines/tests/test_malformed_drawing.py) | The live malformed-file test. Its result is in the drawings summary |

## 2. Unity Catalog governance

| Status | File | What it shows |
|---|---|---|
| ☑ | [`evidence/grant_listing.md`](grant_listing.md) | Written by `06_governance/apply.ipynb`, run `543672861542223`. It holds `SHOW GRANTS` for all seven `bluerridge_*` schemas and the 112 tags. The tags use `br_*` keys because the account's governed tags own `layer` and `sensitivity`. It also shows the **row filter** on `gold_pm.drawing_register` with its asserted allow/deny table, the groups outcome (account groups could not be created) and the inherited `account users` access, stated plainly |
| ☑ | [`06_governance/outputs/lineage_edges.md`](../06_governance/outputs/lineage_edges.md) | 29 table-level and 25 column-level lineage edges from `system.access.table_lineage` and `column_lineage`, bronze to silver to gold, with a Mermaid diagram |
| ☑ | [`09_app/outputs/post_deploy_grants_run.md`](../09_app/outputs/post_deploy_grants_run.md) | The app service principal's grants, applied by [`scripts/post_deploy_grants.sh`](../scripts/post_deploy_grants.sh) and verified with `SHOW GRANTS`, the row-filter mapping row and the Postgres privileges. Three runs: the first applies them (Task 18). The second (Task 18) and the third (Task 24, 2026-11-09) are idempotent re-runs: the mapping MERGE inserts 0 rows |
| ☑ | [`06_governance/row_filters.sql`](../06_governance/row_filters.sql), [`tags.sql`](../06_governance/tags.sql), [`grants.sql`](../06_governance/grants.sql) | The exact statements the notebook applied |
| ☑ | [`00_setup/outputs/schemas_listing.md`](../00_setup/outputs/schemas_listing.md) | The seven governed schemas and the two landing Volumes, as the setup notebook listed them live |

## 3. Lakebase serving

| Status | File | What it shows |
|---|---|---|
| ☑ | [`08_lakebase/outputs/synced_tables_listing.md`](../08_lakebase/outputs/synced_tables_listing.md) | Written by `08_lakebase/01_create_instance.ipynb`, run `235776026823899`. The Autoscaling project `bluerridge-pm` (1 CU, ACTIVE) has five SNAPSHOT synced tables, all online. Row counts read over Postgres equal the Unity Catalog counts (90 / 1,379 / 64 / 7 / 1). KPI point-read latency: p50 3.0 ms on Lakebase vs 428 ms on the SQL warehouse. Also explains why `drawing_register` is not synced |
| ☑ | [`08_lakebase/outputs/latency_raw.json`](../08_lakebase/outputs/latency_raw.json) | The raw timing samples behind the latency table |
| ☑ | [`resources/lakebase.yml`](../resources/lakebase.yml) | The project and the five synced tables as bundle resources (`postgres_projects`, `postgres_synced_tables`) |
| ☑ | [`09_app/outputs/endpoint_selftest.md`](../09_app/outputs/endpoint_selftest.md) | At boot, the deployed app's service principal reads all five synced tables (same counts), the warehouse (`drawing_register_visible=1200`), the Volume and Vector Search, ending with `done ok=True` |

## 4. ML: schedule-risk forecast

| Status | File | What it shows |
|---|---|---|
| ☑ | [`evidence/risk_model_metrics.json`](risk_model_metrics.json) | `ai_forecast` of the weekly slip trend per discipline, with an 8-week backtest: MAE 10.6 days (naive last-value baseline 10.9), bias −9.8 days, 80% interval coverage 14%. 64 open milestones in bands of 26 High / 27 Medium / 11 Low. MLflow experiment `4276059729056540`, run `74b797256d304671b7ca7330db408728`, job run `942883011040522` |
| ☑ | [`05_gold/outputs/risk_top5.md`](../05_gold/outputs/risk_top5.md) | The top 5 risks and the 7 overdue milestones (6 late, 1 due today) in PM language, with a "how much to trust this" paragraph |
| ☑ | [`05_gold/02_risk_forecast.ipynb`](../05_gold/02_risk_forecast.ipynb) | The executed notebook: series build, `ai_forecast` call, backtest, banding and MLflow logging. [HTML](notebook_html_exports/02_risk_forecast.html) |
| ☑ | [`05_gold/outputs/risk_forecast_chart.png`](../05_gold/outputs/risk_forecast_chart.png) | The forecast against history, with the interval band and the backtest overlay |
| ☑ | [`resources/job-risk-forecast.yml`](../resources/job-risk-forecast.yml) | The weekly refresh job, deployed with its schedule PAUSED. It has 0 runs: the evidence came from a one-time submit |

## 5. GenAI: document intelligence and the daily brief

| Status | File | What it shows |
|---|---|---|
| ☑ | [`evidence/sample_compliance_outputs/compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md) | **The scorecard.** The `ai_query` compliance judge (Claude Sonnet 4.5, neutral prompt v3) scored against 274 planted flaws: precision **58.1%**, recall **81.0%**, F1 67.7%. Broken down by flaw type, by drawing type and by stage (A raw, B self-check, C guardrails). Also the prompt lineage v1/v2/v3 (v2 marked superseded for integrity), false-positive causes and five MLflow run ids |
| ☑ | [`03_doc_intelligence/03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb) | The deterministic guardrails, which make no AI call (run `117575921357807`). The **guardrail audit table** ("What each guardrail suppressed, and what it cost in recall") lists 598 suppressed entries by rule. The final `compliance_findings` table has 1,379 rows on 1,200 drawings, and all shape assertions passed. [HTML](notebook_html_exports/03b_compliance_guardrails.html) |
| ☑ | [`03_doc_intelligence/outputs/sample_findings.jsonl`](../03_doc_intelligence/outputs/sample_findings.jsonl), [`sample_extracted.jsonl`](../03_doc_intelligence/outputs/sample_extracted.jsonl), [`sample_parsed.md`](../03_doc_intelligence/outputs/sample_parsed.md) | Real model outputs: 20 judge findings (FAIL, PASS and REVIEW) with page and bbox, and 10 `ai_extract` + `ai_classify` rows. Over all 1,200 drawings, drawing type was right for 1,200 and discipline for 1,198. Also one `ai_parse_document` result with element boxes (1,200 parsed, 0 errors) |
| ☑ | [`05_gold/outputs/daily_brief_today.md`](../05_gold/outputs/daily_brief_today.md) | The `ai_query` daily brief (prompt v3, job run `1067568868183925`). It has its deterministic grounding checks, a claim-by-claim trace to the context JSON and the v1 → v3 prompt history. The human read is in [`v3_human_read.md`](../05_gold/outputs/daily_brief_history/v3_human_read.md) |
| ☑ | [`04_vector_search/outputs/sample_query.md`](../04_vector_search/outputs/sample_query.md) | Vector Search index `code_excerpts_vs` on endpoint `bluerridge_vs`, with 52 of 52 rows indexed. In the smoke test, the right citation is in the top 3 for 5 of 5 queries |

## 6. Genie Agent

| Status | File | What it shows |
|---|---|---|
| ☑ | [`evidence/genie_qa_transcript.md`](genie_qa_transcript.md) | 15 questions asked through the Genie Conversation API (run `770421906253489`). Each has Genie's answer, the generated SQL, the first rows, the expected answer and a rule-based verdict. **Curated 10/10, held-out 5/5.** The five held-out questions were never loaded into the space |
| ☑ | [`07_genie_agent/outputs/genie_qa_results.json`](../07_genie_agent/outputs/genie_qa_results.json) | The same benchmark as machine-readable JSON |
| ☑ | [`resources/genie-space.yml`](../resources/genie-space.yml), [`07_genie_agent/genie_space.geniespace.json`](../07_genie_agent/genie_space.geniespace.json) | The space as a bundle resource (`genie_spaces`), id `01f1db9edffa1a298195db2806ce45e3`: 11 tables, instructions and 10 example SQLs |
| ☑ | [`07_genie_agent/sample_questions.md`](../07_genie_agent/sample_questions.md), [`heldout_questions.md`](../07_genie_agent/heldout_questions.md) | The verified SQL and its live result for each benchmark question. The expected answers are query results, not typed numbers |
| ☑ | [`09_app/outputs/live_obo_chat.md`](../09_app/outputs/live_obo_chat.md) | The same space answering a signed-in user's question inside the app: `outcome=done got_sql=True rows=85` |

## 7. Databricks App

| Status | File | What it shows |
|---|---|---|
| ☑ | [`09_app/outputs/live_obo_chat.md`](../09_app/outputs/live_obo_chat.md) | **Live signed-in session, as a scrubbed log excerpt (2026-11-09 UTC).** `whoami` logs `auth_mode=OBO` for the user. One chat question is answered by Genie *as that user*: `transport=conversation_api outcome=done got_sql=True rows=85`. The MCP endpoint refused the user's token with 403, and the guarded fallback answered. The drawing opened from the answer returned its metadata and PDF (200). An unauthenticated `/api/*` call gets 401 from the proxy |
| ☑ | [`09_app/outputs/chat_selftest.md`](../09_app/outputs/chat_selftest.md) | The deployed app's boot self-test. Every data route's function runs live: 238 reviewed / 51 failed, 26 High, 6 late + 1 due today, `bbox` as 4 floats. One Genie question runs as the SP through the managed Genie MCP server: `transport=mcp got_sql=True rows=1 headline=51` |
| ☑ | [`evidence/deploy_transcript.md`](deploy_transcript.md) | The final verification: `bundle validate` OK, the idempotent grants re-run, `apps get` (RUNNING, deployment `01f1dbe7…` SUCCEEDED, scopes intact), the boot log ending `done ok=True`, the proxy 401 checks, and the test and build results |
| ☑ | [`09_app/outputs/first_deploy.md`](../09_app/outputs/first_deploy.md) | The first deploy: the resolved resource bindings (warehouse, Lakebase, Genie space, Volume), the OBO scopes, the service principal and a clean uvicorn boot |
| ☑ | [`09_app/backend/AUTH_NOTES.md`](../09_app/backend/AUTH_NOTES.md), [`auth.py`](../09_app/backend/auth.py), [`tests/test_chat.py`](../09_app/backend/tests/test_chat.py) | The OBO design, with its cited docs and repos. The user's forwarded token is used with `auth_type="pat"` and fails closed with a 401. Genie is called only as the user, and the data routes run as the SP. Tests assert that the SP client is never used for Genie and that a planted token never appears in a response or a log line |

## Supporting evidence

**Deploy.** The bundle is [`databricks.yml`](../databricks.yml) plus [`resources/`](../resources/). It deploys the pipelines, jobs, Vector Search endpoint and index, Genie space, Lakebase project and synced tables, and the app. CLI v1.20 has no pre-deploy or post-deploy hooks. The steps outside the bundle (schemas, notebook runs and SP grants) follow one documented order in [`docs/BUILD.md`](../docs/BUILD.md#deploy-order).

**Synthetic data and ground truth.**
- [`row_counts.json`](../01_synthetic_data/outputs/row_counts.json): the six project datasets.
- [`drawing_manifest.json`](../01_synthetic_data/outputs/drawing_manifest.json): the 1,200 drawings, 240 of them flawed.
- [`ground_truth_findings.jsonl`](../01_synthetic_data/outputs/ground_truth_findings.jsonl): the 274 planted flaws, each with page, bbox and citation. The judge is scored against these.
- [`spot_check/`](../01_synthetic_data/outputs/spot_check/): three drawings with their ground-truth boxes drawn in red.

**Other docs.**
- [`README.md`](../README.md): one-page overview.
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md): the system as built.
- [`docs/TALK_TRACK.md`](../docs/TALK_TRACK.md): presenter notes.
- [`09_app/API.md`](../09_app/API.md): the endpoints and the chat stream.
- [`evidence/mockups/`](mockups/): the design the UI was built against.

### Executed notebooks

Each notebook ran once as a serverless job run. [`scripts/nb_evidence.py`](../scripts/nb_evidence.py) wrote that run's cell outputs into the `.ipynb`, and it stops if any code cell differs from the run's. Each notebook also has an HTML export.

| Status | Notebook | Job run id | HTML | Box |
|---|---|---|---|---|
| ☑ | [`00_setup/00_create_schemas_and_volumes.ipynb`](../00_setup/00_create_schemas_and_volumes.ipynb) | 571415278261289 | [html](notebook_html_exports/00_create_schemas_and_volumes.html) | 2 |
| ☑ | [`01_synthetic_data/01_generate_project_data.ipynb`](../01_synthetic_data/01_generate_project_data.ipynb) | 131224071230349 | [html](notebook_html_exports/01_generate_project_data.html) | 1 |
| ☑ | [`01_synthetic_data/02_generate_drawings.ipynb`](../01_synthetic_data/02_generate_drawings.ipynb) | 939533185566691 | [html](notebook_html_exports/02_generate_drawings.html) | 1, 5 |
| ☑ | [`03_doc_intelligence/01_parse_drawings.ipynb`](../03_doc_intelligence/01_parse_drawings.ipynb) | 504676373135398 | [html](notebook_html_exports/01_parse_drawings.html) | 5 |
| ☑ | [`03_doc_intelligence/02_extract_classify.ipynb`](../03_doc_intelligence/02_extract_classify.ipynb) | 751609482738894 | [html](notebook_html_exports/02_extract_classify.html) | 5 |
| ☑ | [`03_doc_intelligence/03_compliance_check.ipynb`](../03_doc_intelligence/03_compliance_check.ipynb) | 649534681854336 | [html](notebook_html_exports/03_compliance_check.html) | 5 |
| ☑ | [`03_doc_intelligence/03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb) | 117575921357807 | [html](notebook_html_exports/03b_compliance_guardrails.html) | 5 |
| ☑ | [`03_doc_intelligence/04_ground_truth_scoring.ipynb`](../03_doc_intelligence/04_ground_truth_scoring.ipynb) | 63308297933870 | [html](notebook_html_exports/04_ground_truth_scoring.html) | 5 |
| ☑ | [`04_vector_search/01_load_code_excerpts.ipynb`](../04_vector_search/01_load_code_excerpts.ipynb) | 842380082804308 | [html](notebook_html_exports/01_load_code_excerpts.html) | 5 |
| ☑ | [`04_vector_search/02_create_endpoint_and_index.ipynb`](../04_vector_search/02_create_endpoint_and_index.ipynb) | 672553436601810 | [html](notebook_html_exports/02_create_endpoint_and_index.html) | 5 |
| ☑ | [`05_gold/01_kpi_daily.ipynb`](../05_gold/01_kpi_daily.ipynb) | 165516624533785 | [html](notebook_html_exports/01_kpi_daily.html) | 3, 7 |
| ☑ | [`05_gold/02_risk_forecast.ipynb`](../05_gold/02_risk_forecast.ipynb) | 942883011040522 | [html](notebook_html_exports/02_risk_forecast.html) | 4 |
| ☑ | [`05_gold/03_daily_brief.ipynb`](../05_gold/03_daily_brief.ipynb) | 1067568868183925 | [html](notebook_html_exports/03_daily_brief.html) | 5 |
| ☑ | [`06_governance/apply.ipynb`](../06_governance/apply.ipynb) | 543672861542223 | [html](notebook_html_exports/apply_governance.html) | 2 |
| ☑ | [`07_genie_agent/01_create_space.ipynb`](../07_genie_agent/01_create_space.ipynb) | 793283877903127 | [html](notebook_html_exports/01_create_space.html) | 6 |
| ☑ | [`07_genie_agent/02_run_sample_qa.ipynb`](../07_genie_agent/02_run_sample_qa.ipynb) | 770421906253489 | [html](notebook_html_exports/02_run_sample_qa.html) | 6 |
| ☑ | [`08_lakebase/01_create_instance.ipynb`](../08_lakebase/01_create_instance.ipynb) | 235776026823899 | [html](notebook_html_exports/01_create_instance.html) | 3 |

`05_gold/01_kpi_daily.ipynb` asserts the story numbers that the app's KPI strip shows ([`kpi_today.md`](../05_gold/outputs/kpi_today.md)): 6 of 11 key milestones hit, MS-281 4 days late, EAC +2.3% ($4.8M), TRIR 0, 24 open NCRs (9 / 15), and 238 / 187 / 51 drawings this week. For how a notebook is run and captured, see [`docs/BUILD.md`](../docs/BUILD.md#running-a-notebook-so-its-outputs-are-real).

## Honest limitations

| Limitation | What it means | Where it is shown |
|---|---|---|
| **All data is synthetic** | The project data and drawings were generated (the drawings with seed 42), and flaws were planted on 240 of 1,200 drawings. The ground truth covers only the planted flaws, so the scores describe this synthetic set, not real drawings | [`compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md), [`drawing_manifest.json`](../01_synthetic_data/outputs/drawing_manifest.json) |
| **Citation labels are illustrative** | The five labels (`ASME B16.5 §4.2`, `OSHA 1910.147`, `IBC 1005.1`, `ASME B31.3 §341`, `ASME B31.3 §322`) are fixed project labels. **Clause numbers are not authoritative**: real ASME B16.5 ratings are in section 2, for example. The 52 code excerpts are paraphrases, not quotes | [`04_vector_search/code_excerpts/README.md`](../04_vector_search/code_excerpts/README.md) |
| **The judge is a triage aid, not a verdict** | Precision is 58.1% and recall 81.0%. In the as-of week, 51 of 238 drawings are flagged: 21 of them carry planted flaws and 30 are false alarms. 3 of the 24 flawed drawings are missed. Quality varies by rule: the lockout/tagout rule has 34.0% precision and the weld rule 100%. The guardrails removed 98 false positives at a cost of 2 true positives (audit table in 03b). Prompt v2 contained dataset-derived hints and was superseded for integrity, so its higher score is not the one reported | [`compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md), [`03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb) |
| **Precision and recall are in-sample** | The 58.1% / 81.0% figures are in-sample. Prompts v1 to v3 and both guardrail rounds were developed from error analysis on the same 1,200 drawings that are scored. There is no held-out drawing split, so these are not generalization estimates. (The Genie benchmark, by contrast, has 5 held-out questions.) | [`compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md) |
| **57 FAIL rows still contradict themselves** | 57 FAIL rows in `bluerridge_gold_pm.compliance_findings` carry hedging reasons such as "...appears compliant. However...". 49 of them are not planted flaws, and 6 fall in the as-of week (example: BRL-MEC-GA-0308). Cause: the `_admits` guardrail checks only the last sentence, and the 400-character reason truncation often cuts that sentence (9 rows hit the limit). The sample files skip hedging FAILs by a fixed rule, which is disclosed only in a markdown cell of 03b. The guardrails were deliberately not re-tuned. Engineers confirm every flag; fixing the truncation is on the roadmap | `_admits` in [`compliance_lib.py`](../03_doc_intelligence/compliance_lib.py), [`sample_findings.jsonl`](../03_doc_intelligence/outputs/sample_findings.jsonl), [`03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb) |
| **The review week is simulated, and not all highlights are tight** | The as-of week's 238 drawings, of which exactly 24 carry planted flaws, were chosen deterministically from the manifest's `has_flaw` (`compliance_lib.py`), so the week's mix is by design; this is disclosed in notebook 03 only. Also, 105 of 498 FAIL rows (21%) have `bbox_source='page'`: a whole-page highlight, which the UI labels "approximate" | [`03_compliance_check.ipynb`](../03_doc_intelligence/03_compliance_check.ipynb), [`compliance_lib.py`](../03_doc_intelligence/compliance_lib.py) |
| **KPI strip says "On track" while milestones are late** | `kpi_daily.schedule_status` is `on_track` because the worst key-milestone slip is 4 days, under the documented rule (at_risk at 5 to 9 days, behind at 10 or more). Separately, 6 milestones are late and 1 is due today, including the criticality-5 cryogenic tank gate MS-281 (4 days late). The "Late or due today" list is the actionable one | [`kpi_today.md`](../05_gold/outputs/kpi_today.md) |
| **The forecast is a v1 trend model** | Its backtest MAE of 10.6 days is about the same as a naive last-value baseline (10.9). The 80% interval covered only 14% of held-out points, so the score is overconfident. It is shown only as a ranking in High / Medium / Low bands, never as a probability in the app, the daily brief or Genie answers. The committed [`risk_top5.md`](../05_gold/outputs/risk_top5.md) does print a percentage beside the band (for example "High (93%)") | [`risk_model_metrics.json`](risk_model_metrics.json), [`risk_top5.md`](../05_gold/outputs/risk_top5.md) |
| **Genie MCP is Public Preview, and the live OBO chat used the fallback** | The chat calls the managed Genie MCP server first. That path is verified live as the service principal (`transport=mcp`). In the live signed-in session, MCP refused the user's token with HTTP 403, and the guarded Conversation API fallback answered. The cause of the 403 was not diagnosed | [`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md), [`chat_selftest.md`](../09_app/outputs/chat_selftest.md) |
| **Live OBO check: verified, one session** | One signed-in session on 2026-11-09 UTC: `auth_mode=OBO`, one chat question answered with SQL, and a drawing PDF loaded. That is one sample, not a load test. Unit tests also cover the OBO-only rule: a 401 without a token, and no SP fallback | [`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md) |
| **App pages are not row-filtered per user** | Every app data route runs as the app service principal, which is mapped to `'*'` in `bluerridge_agents.discipline_access`. In the app's own pages every user sees every discipline. Only the Genie chat runs as the user, so only chat answers are row-filtered per user. Running the data routes on behalf of the user is a roadmap item | [`AUTH_NOTES.md`](../09_app/backend/AUTH_NOTES.md), [`grant_listing.md`](grant_listing.md) |
| **Inherited `account users` read access** | The shared catalog grants `account users` USE CATALOG, USE SCHEMA, SELECT, READ VOLUME and EXECUTE, and Unity Catalog inherits these into every `bluerridge_*` schema. So every table is readable account-wide. The row filter on `drawing_register` is the only access control this build adds, which is acceptable only because the data is synthetic | [`grant_listing.md`](grant_listing.md#inherited-access-outside-this-projects-control) |
| No account-level groups | Unity Catalog rejects workspace-local groups, and account admin was not available. The PM and engineer group grants are written down but not applied | [`grant_listing.md`](grant_listing.md#groups-outcome-not-possible-and-why) |
| Deploy is a documented sequence, not one command | `bundle deploy` creates every bundle resource. Schemas, notebook runs and SP grants follow one documented order, because CLI v1.20 has no deploy hooks | [`docs/BUILD.md`](../docs/BUILD.md#deploy-order) |
| Text proof, no screenshots | Screenshots were intentionally omitted (user decision). The app evidence is log excerpts and self-test lines, not screenshots or a recording. The user checked the UI in their own signed-in browser | [`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md) |
| Model output varies | Re-running `ai_parse_document`, the judge or Genie would drift a little. The scores come from the saved judge answers, and the Genie benchmark is one sample | [`compliance_eval_summary.md`](sample_compliance_outputs/compliance_eval_summary.md#non-determinism-and-what-these-numbers-are-from), [`genie_qa_transcript.md`](genie_qa_transcript.md) |
