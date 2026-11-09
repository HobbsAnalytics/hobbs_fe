# Blue Ridge LNG PM Co-Pilot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an end-to-end Databricks project-management demo for a fictional Bechtel LNG build, submitted as a repo whose committed artifacts prove each FE Bar component ran.

**Architecture:** One DAB spans synthetic data generation → Lakeflow (Auto Loader + SDP) ingestion → GenAI document intelligence (parse/extract/classify/judge) → gold aggregates + ML forecast → Vector Search + Genie Space + Lakebase sync → React/FastAPI app with OBO chat. Every component commits evidence (notebook HTMLs, pipeline logs, sample LLM outputs, Genie Q&A transcript, app screenshots, demo video).

**Tech Stack:** Databricks SDP (DLT), AI Functions (`ai_parse_document`, `ai_extract`, `ai_classify`, `ai_query`, `ai_forecast`), Vector Search, Genie Space, Lakebase (Postgres), Databricks Apps. Frontend: React 18 + Vite + TypeScript + Tailwind + Zustand + framer-motion + TanStack React Query + Lucide + Recharts. Backend: Python FastAPI + Databricks SDK + Databricks SQL Connector + psycopg.

**Spec:** `docs/superpowers/specs/2026-11-06-bluerridge-pm-copilot-design.md`

## Global Constraints

- **Deadline:** 2026-11-20 (2 weeks). Solo build; autonomous overnight execution after plan approval.
- **Data:** Synthetic only. No real customer data.
- **Catalog:** `mfg_mc_se_sa` (CREATE CATALOG unavailable at the workspace). Schemas prefixed `bluerridge_`.
- **Profile:** `DEFAULT` (`https://fevm-mfg-mc-se-sa.cloud.databricks.com`). Always pass `--profile DEFAULT`.
- **Warehouse:** `hobbs` · ID `527214d7319cb124` · Medium · RUNNING.
- **Foundation Models:** `databricks-claude-sonnet-4-5` (quality calls — judge, narrator); `databricks-claude-haiku-4-5` (volume calls — parse/extract/classify).
- **"Lakeflow ingestion" satisfied by:** Auto Loader + Spark Declarative Pipelines (SDP). No managed-connector requirement.
- **Auth:** OBO for Genie Conversation API calls from the app (`user_api_scopes: [dashboards.genie]`); SP for everything else. Builder MUST consult current Databricks App OBO docs + at least one working public OBO reference before writing auth code.
- **Code copyright:** ASME + IBC paraphrased with clause citations only (never verbatim). OSHA (29 CFR 1910.*) is federal and may be stored verbatim.
- **`compliance_findings` grain:** one row per **finding** (not per drawing). PK `(drawing_id, finding_id)`. Carries `page_num` + `bbox` for highlighting.
- **"This week"** means `generated_at >= current_date() - INTERVAL 7 DAYS`.
- **Visual language locked to RCM reference** (slate base, emerald/teal brand, Inter font, dark gradient sidebar `linear-gradient(180deg,#0f172a 0%,#1e293b 50%,#0f172a 100%)`, rounded-xl cards, status pills using `bg-50/text-700/border-200`, emerald live-pulse dot, framer-motion stagger). Visual DNA source: `/Users/joseph.hobbs/Downloads/rcm-databricks-demo-main/05_databricks_app/frontend/`.
- **Grader cannot execute the app.** Every component ships committed, scannable evidence; `evidence/00_READ_ME_FIRST.md` is the grader's tour.
- **Repo:** `https://github.com/HobbsAnalytics/hobbs_fe` on branch `main`. Push after every task.
- **Commit attribution (required):** every commit must end with `Co-authored-by: Isaac <no-reply@databricks.com>`.
- **One `databricks bundle deploy -t demo` must succeed** (via `scripts:` pre/post-deploy hooks that create Lakebase + grant SP). Documented fallback sequence in `docs/BUILD.md` is acceptable if the hooks don't suffice.

## Review Focus

Five input classes the spec implies but no task's happy path exercises, most-likely-to-bite first. Each line has a dedicated test in the owning task:

1. **Non-PDF or malformed file dropped into the drawings Volume.** Auto Loader must `rescuedDataColumn` it, not crash. (Owner: Task 5, Step "test malformed file.") *(Superseded for `binaryFile`: it has no `_rescued_data` and rejects `schemaEvolutionMode=rescue`, so `pipeline_drawings.py` flags non-PDFs itself; see the `docs/BUILD.md` gotcha.)*
2. **`ai_query` returns malformed JSON for a drawing.** Compliance pipeline must emit a `REVIEW` row with a null-safe `reason`, not fail the whole run. (Owner: Task 8.)
3. **Drawing with multiple compliance violations.** Pipeline emits N rows in `compliance_findings`, not one row with a nested array. (Owner: Task 8.)
4. **Genie Space returns an ambiguous or empty result.** Chat UI shows an `Empty` state with a next-step suggestion, never a frozen spinner. (Owner: Task 20.)
5. **PDF viewer bbox out of page bounds.** Viewer clamps to page or shows "approximate location" — never draws off-canvas. (Owner: Task 22.)

---

## Repo File Structure

Established in Task 1; tasks after it only add/edit within this skeleton.

```
hobbs_fe/
├── README.md
├── .gitignore
├── databricks.yml                    # root DAB
├── resources/
│   ├── pipeline-project.yml          # SDP for project data
│   ├── pipeline-drawings.yml         # SDP for drawings
│   ├── job-synthetic-data.yml        # one-time generation
│   ├── job-doc-intelligence.yml      # orchestrates parse → judge
│   ├── job-risk-forecast.yml         # ai_forecast
│   ├── vector-search.yml             # endpoint + index
│   ├── lakebase.yml                  # database instance + synced tables
│   ├── genie-space.yml               # Genie Space config
│   └── app.yml                       # Databricks App
├── 01_synthetic_data/
│   ├── 01_generate_project_data.ipynb
│   ├── 02_generate_drawings.py           # Python module imported by notebook + job
│   ├── 02_generate_drawings.ipynb
│   └── outputs/
├── 02_pipelines/
│   ├── pipeline_project.py               # SDP module
│   ├── pipeline_drawings.py              # SDP module
│   └── outputs/
├── 03_doc_intelligence/
│   ├── 01_parse_drawings.ipynb
│   ├── 02_extract_classify.ipynb
│   ├── 03_compliance_check.ipynb
│   ├── 04_ground_truth_scoring.ipynb
│   └── outputs/
├── 04_vector_search/
│   ├── 01_load_code_excerpts.ipynb
│   ├── 02_create_endpoint_and_index.ipynb
│   └── outputs/
├── 05_gold/
│   ├── 01_kpi_daily.ipynb
│   ├── 02_risk_forecast.ipynb
│   ├── 03_daily_brief.ipynb
│   └── outputs/
├── 06_governance/
│   ├── tags.sql
│   ├── grants.sql
│   ├── row_filters.sql
│   └── outputs/
├── 07_genie_agent/
│   ├── sample_questions.md               # curated 10 Q + verified SQL
│   ├── 01_create_space.ipynb
│   ├── 02_run_sample_qa.ipynb            # produces evidence/genie_qa_transcript.md
│   └── outputs/
├── 08_lakebase/
│   ├── 01_create_instance.ipynb
│   └── outputs/
├── 09_app/
│   ├── frontend/
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.js
│   │   ├── postcss.config.js
│   │   ├── index.html
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── stores/appStore.ts
│   │       ├── styles/globals.css
│   │       ├── hooks/useChat.ts
│   │       ├── hooks/useKpis.ts
│   │       ├── hooks/useCompliance.ts
│   │       ├── hooks/useWhoami.ts
│   │       ├── components/layout/{Sidebar,TopBar,PageTransition}.tsx
│   │       ├── components/shared/{StatusBadge,MetricCard,LoadingSkeleton,EmptyState,ErrorAlert}.tsx
│   │       ├── components/copilot/{CoPilotPage,ChatLog,ChatInput,AssistantMessage,UserMessage,SourcesCard,GeneratedSqlCard,VerifyFooter,IdentityChip,SuggestedActions,ProjectKnowledge,ComplianceSummaryTile}.tsx
│   │       ├── components/compliance/{CompliancePage,FindingsTable,FindingDrawer}.tsx
│   │       ├── components/drawings/{PdfViewer,BBoxOverlay}.tsx
│   │       └── components/dashboards/{KpiStrip,DailyBriefCard,RiskForecastCard}.tsx
│   ├── backend/
│   │   ├── main.py                       # FastAPI entrypoint
│   │   ├── auth.py                       # OBO + whoami
│   │   ├── config.py                     # env, catalog/schema names
│   │   ├── databricks_client.py          # SDK + SQL connector
│   │   ├── lakebase.py                   # psycopg + credential generation
│   │   ├── genie.py                      # Genie Conversation API (OBO)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py                 # /health
│   │       ├── whoami.py                 # /api/whoami
│   │       ├── kpi.py                    # /api/kpi/*
│   │       ├── compliance.py             # /api/compliance/*
│   │       ├── drawings.py               # /api/drawings/{id}
│   │       └── chat.py                   # /api/chat (Genie OBO)
│   ├── tests/                            # pytest + Vitest + Playwright
│   ├── requirements.txt
│   ├── app.yaml                          # Databricks App config w/ user_api_scopes
│   └── deploy.sh
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD.md                          # one-page deploy guide
│   ├── TALK_TRACK.md                     # presenter notes for the roleplay
│   └── superpowers/
│       ├── specs/2026-11-06-bluerridge-pm-copilot-design.md
│       └── plans/2026-11-06-bluerridge-pm-copilot.md       (this doc)
└── evidence/
    ├── 00_READ_ME_FIRST.md                # grader's tour
    ├── mockups/                           # from the brainstorm
    ├── pipeline_run_logs/
    ├── notebook_html_exports/
    ├── sample_compliance_outputs/
    ├── genie_qa_transcript.md
    ├── risk_model_metrics.json
    ├── grant_listing.md
    ├── app_screenshots/
    └── app_demo.mp4
```

---

## Task 1: Repo scaffolding + DAB skeleton

**Files:**
- Create: `.gitignore`, `README.md`, `databricks.yml`, `pyproject.toml`
- Create: all directory stubs listed in File Structure (empty folders with `.gitkeep`)
- Create: `docs/BUILD.md` (one-page deploy sequence)
- Create: `evidence/00_READ_ME_FIRST.md` (skeleton grader tour; populated as later tasks run)

**Interfaces produced:**
- `databricks.yml` with `bundle.name: bluerridge_pm_copilot`, targets `demo`, variable `catalog` default `mfg_mc_se_sa`, variable `warehouse_id` default `527214d7319cb124`, variable `schema_prefix` default `bluerridge`, empty `include:` list ready for `resources/*.yml`.

- [ ] **Step 1:** Write `.gitignore` covering `node_modules/`, `dist/`, `__pycache__/`, `*.pyc`, `.env`, `.venv/`, `.superpowers/`, `.DS_Store`, `*.log`, `.databricks/`.
- [ ] **Step 2:** Write `databricks.yml` with the bundle metadata, variables, and empty `include:`. Validate with `databricks bundle validate --profile DEFAULT` — expect success.
- [ ] **Step 3:** Create the folder tree with `.gitkeep` files in every empty directory.
- [ ] **Step 4:** Write `README.md` with: project title, one-paragraph description, "Grader? Start at `evidence/00_READ_ME_FIRST.md`" callout, link to the spec and the plan.
- [ ] **Step 5:** Write `evidence/00_READ_ME_FIRST.md` with the FE Bar box → evidence artifact checklist from spec §9 (artifact paths point to files tasks will produce; mark each `☐ pending` for now).
- [ ] **Step 6:** `databricks bundle validate --profile DEFAULT` → PASS.
- [ ] **Step 7:** Commit + push: `scaffold: DAB skeleton + evidence tour`.

---

## Task 2: Synthetic project data generator

**Files:**
- Create: `01_synthetic_data/01_generate_project_data.ipynb`
- Create: `01_synthetic_data/outputs/row_counts.json`
- Create: `01_synthetic_data/outputs/sample_schedule.csv` + 5 other sample CSVs (one per entity)

**Interfaces produced:**
- Six CSV datasets written to `/Volumes/mfg_mc_se_sa/bluerridge_landing/project/`:
  - `schedule.csv` (~500 rows: `milestone_id, name, discipline, planned_start, planned_end, actual_start, actual_end, depends_on, criticality`)
  - `cost.csv` (~120 line items + 20 change orders)
  - `ncrs.csv` (~80 rows, 24 with `status='open'`)
  - `change_orders.csv` (20 rows)
  - `safety_log.csv` (~400 rows)
  - `daily_reports.csv` (~180 free-text rows)

- [ ] **Step 1:** Write the notebook: use Faker + numpy to produce deterministic data (`random.seed(42)`). Each dataset gets its own cell with a `display(df.limit(5))` output and a `print(f"{name}: {len(df)} rows")` summary.
- [ ] **Step 2:** Volume creation: first cell runs `CREATE VOLUME IF NOT EXISTS mfg_mc_se_sa.bluerridge_landing.project` via `spark.sql`. Prior cell creates the schema if missing.
- [ ] **Step 3:** Write each CSV to the Volume with `.write.option("header",True).csv(...)`. Also save five-row samples to `01_synthetic_data/outputs/sample_*.csv`.
- [ ] **Step 4:** Final cell emits `01_synthetic_data/outputs/row_counts.json` with `{dataset: count}` entries.
- [ ] **Step 5:** Execute end-to-end (`databricks workspace import-dir` + `databricks jobs submit-run` OR run interactively via `databricks notebooks execute` — pick what works). Confirm `Volume` lists all six CSVs via `databricks fs ls dbfs:/Volumes/...`.
- [ ] **Step 6:** Export the executed notebook to HTML into `evidence/notebook_html_exports/01_generate_project_data.html`.
- [ ] **Step 7:** Commit + push: `feat(data): synthetic project data generator`.

---

## Task 3: Synthetic drawing PDF generator with ground truth

**Files:**
- Create: `01_synthetic_data/02_generate_drawings.py` (reusable module)
- Create: `01_synthetic_data/02_generate_drawings.ipynb`
- Create: `01_synthetic_data/outputs/drawing_manifest.json`
- Create: `01_synthetic_data/outputs/ground_truth_findings.jsonl`

**Interfaces produced:**
- 1,200 PDF files at `/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/*.pdf`.
- `drawing_manifest.json`: `[{drawing_id, discipline, revision, drawing_type, volume_path, has_flaw}]`.
- `ground_truth_findings.jsonl`: one JSON per flaw with `{drawing_id, finding_id, page_num, bbox, citation, severity, flaw_type}`.

**Flaw taxonomy (planted deliberately, with known coordinates):**
- `flange_rating_mismatch` → cite `ASME B16.5 §4.2`
- `missing_loto_tag` → cite `OSHA 1910.147`
- `egress_width_under_code` → cite `IBC 1005.1`
- `weld_joint_spec_mismatch` → cite `ASME B31.3 §341`
- `missing_pressure_relief_notation` → cite `ASME B31.3 §322`

- [ ] **Step 1:** Write failing unit test `01_synthetic_data/tests/test_generate_drawings.py`:

```python
def test_generates_expected_count_and_flaw_rate():
    out = generate_drawings(n=100, flaw_rate=0.2, seed=42, out_dir=tmp_path)
    assert out.manifest_count == 100
    assert 15 <= out.flawed_count <= 25     # ~20%
    assert all((tmp_path / f"{d['drawing_id']}.pdf").exists() for d in out.manifest)
    assert all(f['bbox'] and f['page_num'] >= 0 for f in out.ground_truth)
```

- [ ] **Step 2:** Run `pytest 01_synthetic_data/tests/test_generate_drawings.py -v` — expect FAIL (module not implemented).
- [ ] **Step 3:** Implement `generate_drawings(n: int, flaw_rate: float, seed: int, out_dir: Path) -> GenerateResult` in `02_generate_drawings.py` using **ReportLab** (chosen library). PDFs show a mock title block + a schematic diagram drawn with primitives; when a flaw is planted, the generator records the bounding box of the offending element.
- [ ] **Step 4:** Run the test — expect PASS.
- [ ] **Step 5:** Write the notebook that calls `generate_drawings(n=1200, flaw_rate=0.2, seed=42, out_dir="/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings")`. Commit `drawing_manifest.json` + `ground_truth_findings.jsonl` to `01_synthetic_data/outputs/`.
- [ ] **Step 6:** Spot-check: open 2 PDFs via `databricks fs cp` + local preview; confirm bbox coords look right against the rendered page.
- [ ] **Step 7:** Export notebook to `evidence/notebook_html_exports/02_generate_drawings.html`.
- [ ] **Step 8:** Commit + push: `feat(data): synthetic drawing PDFs with ground-truth flaws`.

---

## Task 4: SDP pipeline — project data ingestion (Lakeflow box)

**Files:**
- Create: `02_pipelines/pipeline_project.py`
- Create: `resources/pipeline-project.yml`
- Create: `02_pipelines/outputs/pipeline_project_schema.json` (post-run)

**Interfaces produced:**
- Six bronze tables: `mfg_mc_se_sa.bluerridge_bronze_project.{schedule_raw, cost_raw, ncrs_raw, change_orders_raw, safety_log_raw, daily_reports_raw}`.
- Six silver tables under `bluerridge_silver_engineering.*` with typed columns + DQ constraints (DROP for missing primary IDs, FAIL UPDATE for missing non-null business keys).

- [ ] **Step 1:** Write `pipeline_project.py` using the Python SDP API (`@dlt.table`, `@dlt.expect_or_drop`). Bronze layer uses Auto Loader (`spark.readStream.format("cloudFiles").option("cloudFiles.format","csv")`) with `rescuedDataColumn`. Silver layer applies types and DQ.
- [ ] **Step 2:** Write `resources/pipeline-project.yml` as a bundle resource of type `pipelines`, pointing at `02_pipelines/pipeline_project.py`, target `mfg_mc_se_sa.bluerridge_bronze_project`, serverless.
- [ ] **Step 3:** Add `include: - resources/pipeline-project.yml` to `databricks.yml`. `databricks bundle validate --profile DEFAULT` → PASS.
- [ ] **Step 4:** `databricks bundle deploy -t demo --profile DEFAULT`. Then `databricks bundle run pipeline_project -t demo --profile DEFAULT`.
- [ ] **Step 5:** After a successful run, query row counts for all 12 tables via `databricks experimental aitools tools query "SELECT ..."`. Assert each ≥ expected row count from Task 2. Write `02_pipelines/outputs/pipeline_project_run_summary.md` with `{pipeline_id, update_id, duration_sec, record_counts_by_table, DQ_assertion_results}`.
- [ ] **Step 6:** Copy the pipeline run JSON (via `databricks pipelines get-update`) to `evidence/pipeline_run_logs/pipeline_project_run.json`.
- [ ] **Step 7:** Commit + push: `feat(pipelines): SDP ingestion for project data`.

---

## Task 5: SDP pipeline — drawings ingestion (Lakeflow box, continued)

**Files:**
- Create: `02_pipelines/pipeline_drawings.py`
- Create: `resources/pipeline-drawings.yml`
- Create: `02_pipelines/tests/test_malformed_drawing.py`
- Create: `02_pipelines/outputs/pipeline_drawings_run_summary.md`

**Interfaces produced:**
- `mfg_mc_se_sa.bluerridge_bronze_drawings.raw_files` with cols `[path, modification_time, length, content BINARY, _rescued_data, _ingest_ts]`.
- Silver placeholder table `bluerridge_silver_engineering.drawings_raw_tracking` (passthrough with drawing_id extracted from filename).

- [ ] **Step 1:** Write failing test:

```python
def test_malformed_file_is_quarantined_not_crashed():
    # drop a text file renamed .pdf into the Volume, re-run pipeline
    # assert row for it exists with _rescued_data not null and content.length < 100
```

- [ ] **Step 2:** Run the test — expect FAIL (pipeline not yet deployed).
- [ ] **Step 3:** Implement `pipeline_drawings.py` with `cloudFiles.format=binaryFile`, `rescuedDataColumn`, `cloudFiles.schemaEvolutionMode=rescue`. Extract `drawing_id` from filename at silver. *(Superseded: `binaryFile` rejects `schemaEvolutionMode=rescue` and adds no `_rescued_data`; the code uses `none` and sets `_rescued_data` itself for files without the `%PDF-` header. See the `docs/BUILD.md` gotcha.)*
- [ ] **Step 4:** Write `resources/pipeline-drawings.yml`; include it in `databricks.yml`.
- [ ] **Step 5:** `databricks bundle deploy -t demo` + `databricks bundle run pipeline_drawings -t demo`. Confirm `bronze_drawings.raw_files` has 1,200 rows.
- [ ] **Step 6:** Re-run the malformed-file test — expect PASS.
- [ ] **Step 7:** Write run summary; copy update JSON to `evidence/pipeline_run_logs/pipeline_drawings_run.json`.
- [ ] **Step 8:** Commit + push: `feat(pipelines): SDP ingestion for drawings`.

---

## Task 6: Doc intelligence — ai_parse_document

**Files:**
- Create: `03_doc_intelligence/01_parse_drawings.ipynb`
- Create: `03_doc_intelligence/outputs/sample_parsed.md`

**Interfaces produced:**
- `mfg_mc_se_sa.bluerridge_silver_engineering.drawings_parsed` with cols `[drawing_id, volume_path, parsed_markdown STRING, parse_status, parsed_at]`.

- [ ] **Step 1:** In the notebook, read `bronze_drawings.raw_files` and call `ai_parse_document(content)` on each row's binary. Model: default. Use `databricks-haiku-4-5` only if ai_parse_document accepts a `model` kwarg (test which call signature works at runtime; otherwise accept the service default).
- [ ] **Step 2:** Materialize to `drawings_parsed`. Show a `display` of 5 random rows with their parsed text.
- [ ] **Step 3:** Dump one full parsed drawing to `03_doc_intelligence/outputs/sample_parsed.md` so a grader can see what `ai_parse_document` actually produces.
- [ ] **Step 4:** Export notebook to `evidence/notebook_html_exports/01_parse_drawings.html`.
- [ ] **Step 5:** Commit + push: `feat(doc-intel): parse drawings via ai_parse_document`.

---

## Task 7: Doc intelligence — ai_extract + ai_classify

**Files:**
- Create: `03_doc_intelligence/02_extract_classify.ipynb`
- Create: `03_doc_intelligence/outputs/sample_extracted.jsonl`

**Interfaces produced:**
- `bluerridge_silver_engineering.drawings_extracted` with cols:
  `[drawing_id, title_block_number, discipline, revision, drawing_type, spec_citations ARRAY<STRING>, extracted_at]`.

- [ ] **Step 1:** `ai_extract(parsed_markdown, schema => '{title_block_number: string, revision: string, discipline: string, spec_citations: array<string>}')` on `drawings_parsed`.
- [ ] **Step 2:** `ai_classify(parsed_markdown, labels => array('ISO','PID','GA','SPEC','OTHER'))` → `drawing_type`.
- [ ] **Step 3:** Write result to `drawings_extracted`. Validate: `count` should equal `drawings_parsed` row count; `discipline IS NOT NULL` for ≥95% of rows.
- [ ] **Step 4:** Dump 10 rows to `sample_extracted.jsonl` for grader readability.
- [ ] **Step 5:** Export notebook HTML.
- [ ] **Step 6:** Commit + push: `feat(doc-intel): extract + classify drawings`.

---

## Task 8: Doc intelligence — compliance judge (hero AI step)

**Files:**
- Create: `03_doc_intelligence/03_compliance_check.ipynb`
- Create: `03_doc_intelligence/tests/test_findings_grain.py`
- Create: `03_doc_intelligence/outputs/sample_findings.jsonl`

**Interfaces produced:**
- `mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings` with the schema from spec §7. Grain: one row per **finding**. PK `(drawing_id, finding_id)`.

- [ ] **Step 1:** Write failing test:

```python
def test_findings_grain_is_one_row_per_finding():
    # pick a drawing with 3 planted flaws; after judge, assert 3 rows in compliance_findings
    rows = sql(f"SELECT * FROM {TBL} WHERE drawing_id = '{multi_flaw_id}'").collect()
    assert len(rows) == 3
    assert all(r['bbox'] is not None for r in rows)
    assert len({r['finding_id'] for r in rows}) == 3

def test_malformed_judge_output_falls_back_to_review():
    # inject a response that fails JSON parse → row with status='REVIEW', reason non-null, no crash
```

- [ ] **Step 2:** Run tests — expect FAIL.
- [ ] **Step 3:** In the notebook, call `ai_query('databricks-claude-sonnet-4-5', <prompt>, responseFormat=STRUCT<findings:ARRAY<STRUCT<status:STRING,reason:STRING,citation:STRING,severity:STRING,page_num:INT,bbox:ARRAY<DOUBLE>>>>)` on each `drawings_parsed` row. Flatten the array with `LATERAL VIEW explode` to achieve one-row-per-finding grain. Catch malformed responses with a `try_cast`-style guard and emit a `REVIEW` row.
- [ ] **Step 4:** Write to `compliance_findings`. Add `finding_id` as `uuid()` and `matched_ground_truth BOOLEAN` populated by LEFT JOIN against `ground_truth_findings`.
- [ ] **Step 5:** Run both tests — expect PASS.
- [ ] **Step 6:** Dump 20 sample rows to `sample_findings.jsonl` (mix of pass/fail/review).
- [ ] **Step 7:** Export notebook HTML.
- [ ] **Step 8:** Commit + push: `feat(doc-intel): compliance judge → gold_pm.compliance_findings`.

---

## Task 9: Doc intelligence — ground-truth scoring + evidence

**Files:**
- Create: `03_doc_intelligence/04_ground_truth_scoring.ipynb`
- Create: `evidence/sample_compliance_outputs/compliance_eval_summary.md`

**Interfaces produced:**
- `bluerridge_gold_pm.compliance_eval` with `[precision, recall, f1_by_flaw_type]` (one row per flaw type).

- [ ] **Step 1:** JOIN `compliance_findings` ↔ `ground_truth_findings` on `(drawing_id, approximate page/citation match)`. Compute per-flaw-type precision/recall/F1.
- [ ] **Step 2:** `display` a per-flaw-type bar chart; export the summary table and chart as `compliance_eval_summary.md` with embedded data and ASCII chart.
- [ ] **Step 3:** Dump a 10-row "wins and losses" table to the same file: true positives, false positives, false negatives.
- [ ] **Step 4:** Export notebook HTML.
- [ ] **Step 5:** Commit + push: `feat(doc-intel): ground-truth scoring + eval evidence`.

---

## Task 10: Vector Search — code excerpts corpus + index

**Files:**
- Create: `04_vector_search/01_load_code_excerpts.ipynb`
- Create: `04_vector_search/02_create_endpoint_and_index.ipynb`
- Create: `resources/vector-search.yml`
- Create: `04_vector_search/outputs/corpus_sample.md`
- Create: `04_vector_search/code_excerpts/*.md` (~50 excerpts, paraphrased ASME/IBC + verbatim OSHA)

**Interfaces produced:**
- `bluerridge_agents.code_excerpts` with cols `[citation_id, citation_label, title, source, text, is_paraphrase, embedding ARRAY<FLOAT>]` (embedding managed by VS).
- VS endpoint `bluerridge_vs` and index `bluerridge_agents.code_excerpts_vs`.

- [ ] **Step 1:** Write ~50 markdown files under `04_vector_search/code_excerpts/` — one per clause. ASME + IBC paraphrased, OSHA verbatim. Each file has YAML front-matter: `citation_label`, `source`, `is_paraphrase`.
- [ ] **Step 2:** Load into `code_excerpts` table (notebook 1).
- [ ] **Step 3:** `resources/vector-search.yml` declares endpoint + index with embedding model `databricks-bge-large-en`. Include in `databricks.yml`.
- [ ] **Step 4:** `databricks bundle deploy -t demo` + notebook 2 runs the index sync.
- [ ] **Step 5:** Smoke test: query the index for "flange rating" via `databricks vector-search-indexes query-index` — expect `ASME B16.5 §4.2` in top 3 results. Save sample results to `04_vector_search/outputs/sample_query.md`.
- [ ] **Step 6:** Export both notebook HTMLs.
- [ ] **Step 7:** Commit + push: `feat(vs): code excerpts corpus + Vector Search index`.

---

## Task 11: Gold — KPI daily

**Files:**
- Create: `05_gold/01_kpi_daily.ipynb`

**Interfaces produced:**
- `bluerridge_gold_pm.kpi_daily` with `[date, schedule_status, schedule_milestones_hit, schedule_milestones_total, budget_eac_pct, budget_overrun_usd, safety_days_without_incident, open_ncrs, compliance_failed_this_week]`.

- [ ] **Step 1:** SQL that joins silver tables (schedule, cost, ncrs, safety_log) and `compliance_findings` into daily snapshots.
- [ ] **Step 2:** `display` the current-day row and the last 7 days. Store the current row verbatim in `05_gold/outputs/kpi_today.md`.
- [ ] **Step 3:** Export notebook HTML.
- [ ] **Step 4:** Commit + push: `feat(gold): kpi_daily`.

---

## Task 12: Gold — risk forecast (ML box)

**Files:**
- Create: `05_gold/02_risk_forecast.ipynb`
- Create: `resources/job-risk-forecast.yml`
- Create: `evidence/risk_model_metrics.json`

**Interfaces produced:**
- `bluerridge_gold_pm.risk_forecast` with `[milestone_id, name, forecast_date, slip_probability, forecast_confidence_lower, forecast_confidence_upper, horizon_days]`.

- [ ] **Step 1:** From `silver_engineering.schedule`, compute per-milestone daily delay history (`actual_end - planned_end`). Pivot to a time series per milestone.
- [ ] **Step 2:** Call `ai_forecast(TABLE(...), horizon => INTERVAL 90 DAYS, time_col => 'ds', value_col => 'y')`. Materialize to `risk_forecast`.
- [ ] **Step 3:** Compute aggregate MAE / bias; dump to `evidence/risk_model_metrics.json`.
- [ ] **Step 4:** Export notebook HTML.
- [ ] **Step 5:** Wrap in `resources/job-risk-forecast.yml` for scheduled refresh.
- [ ] **Step 6:** Commit + push: `feat(ml): schedule-slip risk forecast`.

---

## Task 13: Gold — daily brief (GenAI narrator)

**Files:**
- Create: `05_gold/03_daily_brief.ipynb`

**Interfaces produced:**
- `bluerridge_gold_pm.daily_brief` with `[date, brief_md, generated_at]`.

- [ ] **Step 1:** Build a context payload: `kpi_daily` current row + top-5 compliance findings this week + top-3 risk-forecast milestones.
- [ ] **Step 2:** `ai_query('databricks-claude-sonnet-4-5', 'You are the PM co-pilot. Write a 3-sentence Daily Brief that opens with status, flags the biggest risk, and ends with a question.', <context>)`.
- [ ] **Step 3:** Materialize to `daily_brief`. Show today's brief inline.
- [ ] **Step 4:** Save today's brief to `05_gold/outputs/daily_brief_today.md`.
- [ ] **Step 5:** Export notebook HTML.
- [ ] **Step 6:** Commit + push: `feat(gold): daily brief narrator`.

---

## Task 14: Governance (Unity Catalog box)

**Files:**
- Create: `06_governance/tags.sql`, `grants.sql`, `row_filters.sql`
- Create: `06_governance/apply.ipynb` (runs the SQL + captures evidence)
- Create: `evidence/grant_listing.md`

**Interfaces produced:**
- Tags applied to `bluerridge_*` schemas: `layer`, `sensitivity`, `data_class`.
- Grants: an `engineer_group` placeholder (user's primary user as member) with silver + gold READ; app SP (looked up at deploy time) with gold READ.
- Row filter on `drawings_extracted` by `discipline` (demonstrative; attached to a view).

- [ ] **Step 1:** Write all three SQL files with explicit schema paths and clear comments.
- [ ] **Step 2:** `apply.ipynb` runs each file via `spark.sql`, then runs `SHOW GRANTS ON SCHEMA mfg_mc_se_sa.bluerridge_<x>` for each schema and tabulates results.
- [ ] **Step 3:** Dump to `evidence/grant_listing.md`.
- [ ] **Step 4:** Export notebook HTML.
- [ ] **Step 5:** Commit + push: `feat(governance): tags + grants + row filter + grant listing`.

---

## Task 15: Genie Space (Genie Agent box)

**Files:**
- Create: `07_genie_agent/sample_questions.md`
- Create: `resources/genie-space.yml`
- Create: `07_genie_agent/01_create_space.ipynb`
- Create: `07_genie_agent/02_run_sample_qa.ipynb`
- Create: `evidence/genie_qa_transcript.md`

**Interfaces produced:**
- Genie Space `bluerridge_pm_copilot` over `bluerridge_gold_pm.*` + `bluerridge_silver_engineering.schedule, .ncrs`, with description, instructions, 10 verified sample questions with expected SQL, and a Space ID written to `07_genie_agent/outputs/space_id.txt`.

- [ ] **Step 1:** Write `sample_questions.md` with 10 Q→expected-SQL pairs covering: compliance ("how many drawings failed this week?"), schedule ("which milestones slipped?"), cost ("explain budget variance"), risk ("top 3 schedule risks?"), NCRs, daily brief lookup.
- [ ] **Step 2:** `resources/genie-space.yml` declares the Space with tables, synonyms (ISO↔isometric, NCR↔nonconformance, RFI↔request for information), and seed questions.
- [ ] **Step 3:** `databricks bundle deploy -t demo`. The Space ID lands in `space_id.txt`.
- [ ] **Step 4:** `02_run_sample_qa.ipynb` calls the Genie Conversation API for each sample question; records user Q, generated SQL, first 5 result rows into `evidence/genie_qa_transcript.md`.
- [ ] **Step 5:** Verify ≥7 of 10 questions return a non-empty result with syntactically valid SQL.
- [ ] **Step 6:** Export both notebook HTMLs.
- [ ] **Step 7:** Commit + push: `feat(genie): Genie Space + sample Q&A transcript`.

---

## Task 16: Lakebase instance + synced tables (Lakebase box)

**Files:**
- Create: `08_lakebase/01_create_instance.ipynb`
- Create: `resources/lakebase.yml`
- Create: `08_lakebase/outputs/synced_tables_listing.md`

**Interfaces produced:**
- Lakebase instance `bluerridge-pm`.
- Synced tables: `kpi_daily`, `compliance_findings`, `risk_forecast` (synced from gold).

- [ ] **Step 1:** `resources/lakebase.yml` defines `database_instance` (CU_1) + three `synced_database_table` resources.
- [ ] **Step 2:** `databricks bundle deploy -t demo`. Confirm each synced table reaches state `AVAILABLE`.
- [ ] **Step 3:** Smoke test: connect via psycopg (notebook) and `SELECT COUNT(*)` on each table. Store the counts in `synced_tables_listing.md` along with the Lakebase `read_write_dns`.
- [ ] **Step 4:** Export notebook HTML.
- [ ] **Step 5:** Commit + push: `feat(lakebase): instance + synced tables for hot KPI reads`.

---

## Task 17: App scaffolding (frontend + backend)

**Files:**
- Create: `09_app/frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `index.html`
- Create: `09_app/frontend/src/{main.tsx,App.tsx,styles/globals.css}`
- Create: `09_app/backend/{main.py,config.py,requirements.txt}`
- Create: `09_app/app.yaml`, `09_app/deploy.sh`

**Interfaces produced:**
- Running `cd 09_app/frontend && npm install && npm run dev` serves the App shell locally.
- Running `cd 09_app && uvicorn backend.main:app --reload` serves `/health` returning 200.
- `app.yaml` includes `user_api_scopes: [dashboards.genie]` (OBO), `env` for `CATALOG`, `WAREHOUSE_ID`, `LAKEBASE_INSTANCE`, `GENIE_SPACE_ID`.

- [ ] **Step 1:** Copy the exact `package.json` + `tailwind.config.js` + `tsconfig.json` + `postcss.config.js` + `globals.css` from `/Users/joseph.hobbs/Downloads/rcm-databricks-demo-main/05_databricks_app/frontend/`. Update `name` to `bluerridge-pm-copilot`.
- [ ] **Step 2:** Scaffold `App.tsx` with placeholder routes `/`, `/compliance`, `/drawings/:id`. Dark gradient sidebar + white top bar skeleton. No real content yet.
- [ ] **Step 3:** FastAPI `main.py` wires `/health`. `config.py` reads env with sensible defaults.
- [ ] **Step 4:** `requirements.txt`: `fastapi`, `uvicorn[standard]`, `databricks-sdk`, `databricks-sql-connector`, `psycopg[binary]`, `httpx`.
- [ ] **Step 5:** `app.yaml` includes `user_api_scopes`.
- [ ] **Step 6:** `resources/app.yml` as DAB resource. Include in `databricks.yml`.
- [ ] **Step 7:** `npm run build` and `uvicorn --help` both succeed locally. `databricks bundle validate` PASSes.
- [ ] **Step 8:** Commit + push: `scaffold(app): React + FastAPI shells matching RCM visual DNA`.

---

## Task 18: Backend auth — OBO + whoami

**Files:**
- Create: `09_app/backend/auth.py`, `09_app/backend/routes/whoami.py`
- Create: `09_app/backend/tests/test_whoami.py`
- Create: `docs/BUILD.md` (updated — "Auth: how OBO is wired")

**Interfaces produced:**
- `GET /api/whoami` → `{email: str, user_name: str, auth_mode: 'OBO'|'SP'}` reading `x-forwarded-email` + `x-forwarded-user` headers.
- `auth.py: get_user_token(request) -> str` returning the forwarded user token for Genie OBO calls.

- [ ] **Step 1 (RESEARCH):** Before writing a line of auth code, read the current Databricks App OBO docs. Fetch one working public reference app that uses `user_api_scopes` and OBO. Note the exact header names, token-forwarding mechanism, and SDK call shape in a one-page memo at `09_app/backend/AUTH_NOTES.md`. **Required: the memo cites the docs URL and the reference repo URL.**
- [ ] **Step 2:** Write failing test for `/api/whoami`:

```python
def test_whoami_reads_forwarded_headers():
    r = client.get("/api/whoami", headers={
        "x-forwarded-email": "joseph.hobbs@databricks.com",
        "x-forwarded-user": "joseph.hobbs",
    })
    assert r.status_code == 200
    j = r.json()
    assert j["email"] == "joseph.hobbs@databricks.com"
    assert j["auth_mode"] == "OBO"
```

- [ ] **Step 3:** Run test — FAIL.
- [ ] **Step 4:** Implement `/api/whoami` and `auth.py: get_user_token`. Keep SP auth for everything else via the SDK's default auth.
- [ ] **Step 5:** Run test — PASS. Also deploy the app and curl `/api/whoami` from a browser session to confirm the headers truly arrive (not just unit-mocked).
- [ ] **Step 6:** Commit + push: `feat(auth): OBO + /api/whoami + research memo`.

---

## Task 19: Backend endpoints — KPI, compliance, drawings

**Files:**
- Create: `09_app/backend/routes/{kpi.py,compliance.py,drawings.py}`
- Create: `09_app/backend/{databricks_client.py,lakebase.py}`
- Create: `09_app/backend/tests/test_routes.py`

**Interfaces produced:**
- `GET /api/kpi/today` → `{schedule, budget, safety, open_ncrs}` from Lakebase.
- `GET /api/compliance/findings?week=current` → `[{...}]` from Lakebase.
- `GET /api/drawings/{drawing_id}` → `{drawing_id, volume_path, findings: [...]}` (findings from Lakebase, drawing metadata from SQL warehouse).
- `GET /api/drawings/{drawing_id}/pdf` → streams the PDF binary from the Volume (requires SP auth to the Volume).

- [ ] **Step 1:** `lakebase.py` wraps psycopg connection using `databricks database generate-database-credential` for the SP; connection pool via `psycopg_pool`.
- [ ] **Step 2:** `databricks_client.py` wraps `WorkspaceClient` + SQL connector (for non-Lakebase queries like PDF streaming from Volume).
- [ ] **Step 3:** Write failing tests for each endpoint (unit, with mocked clients).
- [ ] **Step 4:** Implement endpoints; run tests — PASS.
- [ ] **Step 5:** Deploy; curl each endpoint; confirm data flows.
- [ ] **Step 6:** Commit + push: `feat(api): KPI + compliance + drawings routes`.

---

## Task 20: Backend chat — Genie Conversation API (OBO)

**Files:**
- Create: `09_app/backend/routes/chat.py`, `09_app/backend/genie.py`
- Create: `09_app/backend/tests/test_chat.py`

**Interfaces produced:**
- `POST /api/chat` body `{message: str, conversation_id: str?}` →
  stream of events:
  `{type: 'status', value: 'running'|'done'|'error'}`,
  `{type: 'answer', text: str}`,
  `{type: 'sql', query: str}`,
  `{type: 'result', rows: [...], columns: [...]}`,
  `{type: 'sources', items: [{drawing_id, page_num, bbox}]}`.
- Empty / ambiguous Genie result → single `status=done` + `answer="I'm not sure which milestones you mean — try naming a discipline or specifying 'this week'."` (per Review Focus #4).

- [ ] **Step 1:** Write failing test:

```python
def test_chat_streams_sql_and_answer_for_known_question(mocked_genie):
    r = client.post("/api/chat", json={"message": "How many drawings failed this week?"})
    events = parse_sse(r.text)
    assert any(e["type"] == "sql" for e in events)
    assert any(e["type"] == "answer" for e in events)

def test_chat_ambiguous_question_returns_graceful_empty():
    r = client.post("/api/chat", json={"message": "which?"})
    events = parse_sse(r.text)
    assert any(e["type"] == "answer" and "not sure" in e["text"].lower() for e in events)
```

- [ ] **Step 2:** Run tests — FAIL.
- [ ] **Step 3:** Implement `genie.py: converse(space_id, message, user_token, conversation_id?)` as an async generator yielding the event sequence. Uses the Genie Conversation API with the forwarded user token (OBO).
- [ ] **Step 4:** Implement `/api/chat` using FastAPI SSE (`StreamingResponse` with `text/event-stream`).
- [ ] **Step 5:** Run tests — PASS. Deploy; curl the endpoint; confirm streaming.
- [ ] **Step 6:** Commit + push: `feat(api): /api/chat via Genie Conversation API (OBO) with empty-state`.

---

## Task 21: Frontend — layout + routing + KPI strip

**Files:**
- Create: `09_app/frontend/src/stores/appStore.ts`
- Create: `09_app/frontend/src/hooks/{useKpis.ts,useWhoami.ts}.ts`
- Create: `09_app/frontend/src/components/layout/{Sidebar,TopBar,PageTransition}.tsx`
- Create: `09_app/frontend/src/components/shared/{StatusBadge,LoadingSkeleton,EmptyState,ErrorAlert,MetricCard}.tsx`
- Create: `09_app/frontend/src/components/dashboards/KpiStrip.tsx`

**Interfaces produced:**
- Sidebar with nav items: AI Co-Pilot (home), Dashboards, Doc Compliance (with badge), Schedule & Risk, Cost & Budget, Safety & Quality.
- TopBar: breadcrumb + search field + project selector + bell + avatar.
- KPI strip: 4 compressed metric cards (Schedule / Budget / Safety / Open NCRs) reading from `/api/kpi/today`.
- Visual DNA matches the brainstorm mockup `evidence/mockups/dashboard-v3-chat.html`.

- [ ] **Step 1:** Copy `appStore.ts`, `Sidebar.tsx`, `TopBar.tsx`, `PageTransition.tsx`, `StatusBadge.tsx`, `LoadingSkeleton.tsx` from the RCM reference, adapted for construction nav items and project name.
- [ ] **Step 2:** `useKpis.ts` via TanStack Query hitting `/api/kpi/today` with 5-min stale time.
- [ ] **Step 3:** `KpiStrip.tsx` renders the 4 cards (icon + label + value + sub). Semantic color via `kpi-icon-good/warn/bad` driven by status.
- [ ] **Step 4:** Loading → `LoadingSkeleton`; Empty → `EmptyState`; Error → `ErrorAlert`. All three states covered.
- [ ] **Step 5:** `npm run build` succeeds. Vitest smoke test: `KpiStrip` renders 4 cards given mock data.
- [ ] **Step 6:** Commit + push: `feat(ui): layout + KPI strip`.

---

## Task 22: Frontend — Co-Pilot chat (home)

**Files:**
- Create: `09_app/frontend/src/hooks/useChat.ts`
- Create: `09_app/frontend/src/components/copilot/*.tsx` (all per File Structure)
- Create: `09_app/frontend/src/components/dashboards/{DailyBriefCard,RiskForecastCard}.tsx` (used in right rail)

**Interfaces produced:**
- `/` route renders the Co-Pilot page.
- Chat log seeds with today's `daily_brief`.
- User input calls `/api/chat`; `useChat.ts` consumes SSE and renders a streaming assistant message with: text, `<SourcesCard>` (clickable drawings), `<GeneratedSqlCard>` (collapsible), `<VerifyFooter>`.
- `<IdentityChip>` shows the signed-in user and (truthfully) "OBO" vs "SP" per the current answer.
- Right rail: `<SuggestedActions>` (4 pre-filled prompts), `<ComplianceSummaryTile>`, `<ProjectKnowledge>`.
- Empty-state assistant message rendered when `/api/chat` returns the graceful empty answer.

- [ ] **Step 1:** Write Vitest for `useChat.ts`: given a mocked SSE stream, assert the hook accumulates text and sources correctly.
- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Implement `useChat.ts` (uses `EventSource` or `fetch` + `TextDecoder` reader). Implement all `copilot/*` components. Model the visual against `evidence/mockups/dashboard-v3-chat.html`.
- [ ] **Step 4:** Playwright smoke test (if time): type "which failed drawings are blocking commissioning?" → assistant answer appears with ≥1 source + SQL card.
- [ ] **Step 5:** `npm run build` succeeds.
- [ ] **Step 6:** Commit + push: `feat(ui): Co-Pilot chat home with sources, SQL, identity`.

---

## Task 23: Frontend — Compliance page + PDF viewer

**Files:**
- Create: `09_app/frontend/src/hooks/useCompliance.ts`
- Create: `09_app/frontend/src/components/compliance/{CompliancePage,FindingsTable,FindingDrawer}.tsx`
- Create: `09_app/frontend/src/components/drawings/{PdfViewer,BBoxOverlay}.tsx`
- Create: `09_app/frontend/tests/BBoxOverlay.test.tsx`

**Interfaces produced:**
- `/compliance` lists the current-week findings as a table (drawing_id · reason · citation · severity · Open PDF).
- `/drawings/:id` renders the PDF (via `pdf.js` or `react-pdf`) with an overlay drawing the `bbox` highlights.
- Review Focus #5: `<BBoxOverlay>` clamps bboxes to page bounds and labels off-page coords as "approximate."

- [ ] **Step 1:** Write failing test for `BBoxOverlay`:

```ts
test('clamps bbox to page bounds and marks approximate', () => {
  const { getByText } = render(<BBoxOverlay page={{w:800,h:1000}} bbox={[900,0,100,100]} />);
  expect(getByText(/approximate/i)).toBeInTheDocument();
});
```

- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Implement `PdfViewer` using `react-pdf`. Implement `BBoxOverlay` with clamp + approximate label.
- [ ] **Step 4:** `FindingsTable` reads `/api/compliance/findings` with virtualization for 240+ cumulative rows.
- [ ] **Step 5:** Run test — PASS. `npm run build` succeeds.
- [ ] **Step 6:** Commit + push: `feat(ui): compliance page + PDF viewer with bbox highlights`.

---

## Task 24: End-to-end deploy + evidence capture + grader tour

**Files:**
- Modify: `databricks.yml` (final `scripts:` pre/post-deploy hooks for Lakebase create + grant SP + initial pipeline run)
- Create: `scripts/post_deploy.sh`, `scripts/pre_deploy.sh`
- Modify: `evidence/00_READ_ME_FIRST.md` (fill in with real artifact paths and ☑ check marks)
- Create: `evidence/app_screenshots/*.png` (home, compliance, PDF viewer, chat response, right rail)
- Create: `evidence/app_demo.mp4` (60-90s screen recording)
- Modify: `docs/BUILD.md` (final deploy sequence)
- Modify: `docs/ARCHITECTURE.md` (final architecture doc; mirrors spec with implementation notes)
- Modify: `docs/TALK_TRACK.md` (presenter notes for the roleplay)

**Interfaces produced:**
- `databricks bundle validate --profile DEFAULT` → PASS.
- `databricks bundle deploy -t demo --profile DEFAULT` → SUCCESS end-to-end (via scripts hooks).
- `databricks bundle run <each resource> -t demo --profile DEFAULT` → SUCCESS.
- All checkboxes in `evidence/00_READ_ME_FIRST.md` are ☑, each pointing to a real committed file.

- [ ] **Step 1:** Write `scripts/pre_deploy.sh` to create the Lakebase instance if missing. Write `scripts/post_deploy.sh` to apply SP Postgres grants, run `06_governance/grants.sql`, and trigger initial pipeline runs.
- [ ] **Step 2:** Add `scripts:` block in `databricks.yml` wiring these.
- [ ] **Step 3:** Fresh workspace smoke: run `databricks bundle deploy -t demo` end-to-end on a clean target. If it fails, fix and loop. Capture the deploy transcript to `evidence/deploy_transcript.txt`.
- [ ] **Step 4:** `databricks bundle run` each resource. Capture per-run JSON to `evidence/pipeline_run_logs/`.
- [ ] **Step 5:** Open the deployed app in a browser. Capture screenshots: `01_copilot_home.png`, `02_assistant_response_with_sources.png`, `03_compliance_page.png`, `04_pdf_viewer_highlighted.png`, `05_right_rail.png`. Save to `evidence/app_screenshots/`.
- [ ] **Step 6:** Record 60-90s screen recording of a full user journey (open → read brief → ask a question → click a drawing citation → see highlighted PDF). Save as `evidence/app_demo.mp4`.
- [ ] **Step 7:** Finalize `evidence/00_READ_ME_FIRST.md`: a numbered tour, one item per FE Bar box, each with an `[Open this file]` link, each marked ☑.
- [ ] **Step 8:** Finalize `docs/ARCHITECTURE.md` + `docs/BUILD.md` + `docs/TALK_TRACK.md`.
- [ ] **Step 9:** `npm run build` + `databricks bundle validate` + a final smoke of each pipeline. Everything green.
- [ ] **Step 10:** Commit + push: `feat: end-to-end deploy + evidence tour`.

---

## Appendix A — Running order

Tasks are strictly sequential. Each one depends on tables/resources from earlier ones:

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24
```

Several pairs could parallelize if we had multiple executors (e.g., 11+13 both consume silver and compute gold; 21 and 22 both touch the frontend). Given the solo-overnight constraint, sequential is simpler and the dependency graph is linear enough.

## Appendix B — Known fallbacks

- **If `databricks bundle deploy` can't do one-shot** (e.g., Lakebase ordering can't be scripted cleanly), document the manual sequence in `BUILD.md` and keep §13 Goal 4 satisfied by that documented sequence.
- **If Genie Conversation API OBO can't reach `dashboards.genie`** from inside the app, fall back to running Genie queries as the SP and set `auth_mode: 'SP'` in `/api/whoami`. The identity chip reflects it truthfully.
- **If `ai_forecast` isn't callable from a notebook in this workspace**, fall back to a tiny Prophet or `statsforecast` model inside the notebook — same output table shape — and note the swap in `evidence/risk_model_metrics.json`.
- **If total AI function cost on 1,200 drawings is prohibitive**, cap at 300 drawings for the full pipeline and keep ground-truth for all 300. The UI numbers scale proportionally.
