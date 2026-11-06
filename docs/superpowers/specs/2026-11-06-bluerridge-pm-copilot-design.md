# Blue Ridge LNG — Project Manager Co-Pilot (Design)

**Date:** 2026-11-06
**Author:** Joseph Hobbs
**Status:** Draft — pending plan

---

## 1. Intent & Why

Build an end-to-end Databricks application that gives the project manager of a
large construction project a single AI-first surface for monitoring project
success. The project is a fictional **Blue Ridge LNG Terminal — Phase 2**, modeled
on the kind of EPC (engineering, procurement, construction) work Bechtel actually
runs.

The build exists to satisfy the **FE Bar certification**, which requires one
customer-grade solution that touches:

1. Lakeflow ingestion
2. Unity Catalog governance
3. Lakebase serving
4. ML or GenAI
5. A Genie Agent
6. A Databricks App

…for a specific industry pain, with synthetic or public data, submitted as a
single git repository.

The industry pain we're solving: **automated audit of engineering drawings
(ISO/P&ID/GA) against regulatory codes.** Bechtel-type EPC firms burn billable
hours on manual drawing audits. We make that an AI step and surface the result in
a Project Co-Pilot chat.

---

## 2. Grading Reality

Two independent grading mechanisms, both must pass:

### 2.1 Build grading — a code-reading agent

The grader does **not run the app**. It reads the repository and scores based on
**evidence of successful execution** that is discoverable from committed files.

This means every component must leave a **readable paper trail** inside the repo:

- Executed notebooks with cell outputs preserved (plus `.html` exports).
- Pipeline run logs / summaries (record counts, DQ assertion results) committed
  as JSON or Markdown.
- Sample LLM outputs (parsed drawings, extracted fields, compliance verdicts)
  committed as `.md`, `.jsonl`, or `.json`.
- Genie Agent Q→SQL→result transcript committed as Markdown.
- Model evaluation metrics (risk forecast) committed as JSON.
- App screenshots per page committed as PNG.
- A short screen recording (GIF/MP4) of the app in action.
- A top-level `evidence/00_READ_ME_FIRST.md` that maps **each FE Bar box → the
  exact artifact that proves it works.**

**Code alone is not evidence.** If a file could not have produced the committed
output, the grader will mark it unproven.

### 2.2 Roleplay grading — Yoodli

A separate rubric. Not addressed by this document except that the app must be
*presentable* (clear value story, clean visuals, business-focused language).

---

## 3. Goals / Non-Goals / Anti-Goals

### Goals

1. All six FE Bar boxes checked at demo-level fidelity.
2. Document compliance review (parse → extract → judge against rules) is the
   **hero** feature and the deepest build.
3. One Databricks App — a Project Co-Pilot chat — is the primary user surface.
4. Everything deploys with a single `databricks bundle deploy`.
5. Every component ships committed evidence of a successful run.
6. The repo is scannable in under 10 minutes by someone who has never seen it.

### Non-Goals

- Real customer or real Bechtel data (synthetic only).
- Production-grade reliability (error handling, retries, scaling).
- Multiple projects / multi-tenancy.
- A multi-agent (MAS) architecture — explicitly ruled out, see §5.
- An AppKit implementation — we mirror the chosen reference stack (§7).

### Anti-Goals (if we did these, the build fails)

- Shipping code without evidence of execution.
- A single component so deep it crowds out another required box.
- Realistic PII, PHI, or proprietary engineering data.
- A dashboard-first UX (chat is primary; dashboards jump off from it).

---

## 4. Constraints

| Constraint | Source |
|---|---|
| Submission deadline: **2 weeks** from 2026-11-06 (= 2026-11-20) | User |
| **Solo build.** User plans to run an overnight autonomous build to finish, test, and validate once the plan is approved | User |
| Synthetic or public data only | FE Bar rules |
| All six required product components | FE Bar rubric |
| Evidence of successful execution in the repo | FE Bar build grading |
| Grader cannot execute the app | FE Bar build grading |
| One repo, scannable | FE Bar submission format |
| Must be presentable to business + technical AI persona | FE Bar roleplay |
| Databricks-native wherever practical | FE Bar + Isaac guidance |
| Mirror the RCM demo's visual stack unless it conflicts with a Databricks primitive | User decision |
| "Lakeflow ingestion" box is satisfied by **Auto Loader + Spark Declarative Pipelines (SDP, formerly DLT)**; no Lakeflow Connect connector required | User decision |
| **On-Behalf-Of (OBO) auth** for Genie queries from the App; `user_api_scopes: [dashboards.genie]` wired | User decision |

### 4.2 Workspace-confirmed resources

Smoke-tested at design time with the `DEFAULT` profile
(`https://fevm-mfg-mc-se-sa.cloud.databricks.com`):

| Resource | Value | How confirmed |
|---|---|---|
| User | `joseph.hobbs@databricks.com` (admins group) | `current-user me` |
| Catalog | `mfg_mc_se_sa` (owns multiple schemas; CREATE SCHEMA works) | `schemas create/delete` round-trip |
| Warehouse | `hobbs` · ID `527214d7319cb124` · Medium · RUNNING | `warehouses list` |
| Foundation Model (default for ai_*) | `databricks-claude-sonnet-4-5` for quality calls; `databricks-claude-haiku-4-5` for high-volume parse/classify | `ai_query` smoke test |
| `ai_parse_document` | Available | smoke test (returned structured JSON) |
| `ai_forecast` | Likely available (syntax detail deferred to build) | not fully smoked |
| Vector Search | Shared endpoints exist (`vca_voice_endpoint`, etc.); builder picks reuse-vs-new | `vector-search-endpoints list-endpoints` |
| Lakebase | `database list-database-instances` works; create new per project | listed |
| Databricks Apps | Deploy works; `apps list` fine | listed |
| Pipelines (SDP/DLT) | Create works | listed |
| Jobs | Create works | listed |
| Genie Spaces | Create works | `genie list-spaces` |

CREATE CATALOG at the metastore is **not** available via CLI
("Metastore storage root URL does not exist" — Default Storage limit). This
is the only hard constraint; we work entirely inside `mfg_mc_se_sa`.

### 4.1 Cut order (if time runs short)

Preserve in this order (first bullet is highest priority):

1. **Doc intelligence pipeline** (the hero: parse → extract → classify → compliance-judge → findings table + ground-truth comparison in `evidence/`).
2. **Chat UI** (home route of the App; Genie answer + sources + "AI-generated — verify").
3. **Genie Agent** (space over `gold_pm.*` with 10 verified sample questions and a committed transcript).
4. **Lakebase sync** (one synced table minimum, powering the KPI strip).
5. **ML risk forecast** (`ai_forecast` + metrics JSON).
6. **Governance polish** (row filters, extra tags beyond the minimum).
7. **Extra app pages** (schedule / cost / safety detail pages beyond the home + compliance + PDF viewer).

Each of the six FE Bar boxes still needs *something* committed; the cut is in
depth, not presence.

---

## 5. The Product

### 5.1 User

A **project manager** on the Blue Ridge LNG Phase 2 build. Not an engineer, not a
QA/QC reviewer — the senior person accountable for schedule, cost, safety, and
quality across the whole project. Non-technical w/r/t Databricks; comfortable
with a chat UI.

### 5.2 Scene

The PM opens the app in the morning. A seeded "Daily Brief" message is waiting
with the state of Phase 2. KPIs sit above the chat for glance value (schedule,
budget, safety, open NCRs). The PM can:

- Read the brief, click into any item.
- Type a free-form question ("why am I slipping?" / "which drawings failed?").
- Hit one of the **Suggested Action** buttons in the right rail
  ("Analyze this week's failed drawings", "Where am I at risk of slipping?",
  "Explain the budget variance", "Summarize open NCRs by discipline").

Each AI response contains:

- A plain-English answer.
- **Source citations** (specific drawings from the Volume, with page + section).
- A collapsible **"Generated SQL"** card.
- An **identity chip** showing the signed-in user (OBO when scoped).
- A **"AI-generated — verify"** footer disclaimer.

Clicking a drawing citation opens the PDF with the regulatory violation
highlighted and the citation (ASME / OSHA / IBC) displayed.

### 5.3 Surfaces (in-scope for this build)

| Surface | Purpose | Fidelity |
|---|---|---|
| **AI Co-Pilot (chat)** | Primary daily tool | Fully built, hero |
| **Document Compliance page** | Jump into the 24 flagged drawings | Fully built |
| **Dashboards (schedule, cost, safety)** | Jump-off tiles, deeper detail | Static mocks or thin AI/BI dashboard embed |
| **Settings / Admin** | Not in scope | — |

The home route is the chat. Everything else is one click away.

### 5.4 Mockup references (brainstorming session)

The visual direction is captured in `evidence/mockups/`:
- `dashboard-v3-chat.html` — chat-first (final direction)
- `dashboard-v2.html` — dashboard-first (superseded)
- `dashboard-strawman.html` — initial (superseded)

---

## 6. Architecture

### 6.1 One-glance

```
PDFs (synth)                   Project data (synth, batch)
     │                               │
     │ Auto Loader                   │ Auto Loader (batch)
     ▼                               ▼
bronze_drawings.raw_files      bronze_project.{schedule,cost,ncrs,
                                                 change_orders,safety_log,
                                                 daily_reports}
     │                               │
     │ ai_parse_document             │ cleaning, DQ
     │ ai_extract                    │
     │ ai_classify                   │
     ▼                               ▼
silver_engineering.parsed      silver_engineering.{schedule,...}
     │
     │ ai_query(parsed, rules)
     ▼
gold_pm.compliance_findings  ◄── Vector Search index on
                                  ASME/OSHA/IBC excerpts
     │
     ├── gold_pm.kpi_daily          (schedule, budget, safety, NCRs)
     ├── gold_pm.risk_forecast      (ai_forecast on milestone delays)
     └── gold_pm.daily_brief        (ai_query narrator)
            │
            ├── Lakebase synced tables (hot KPI strip)
            └── Genie Agent (one agent, all gold_pm.*)
                      │
                      ▼
                 Genie One MCP
                      │
                      ▼
             React + FastAPI App
```

### 6.2 Component-by-component

#### 6.2.1 Lakeflow ingestion

- **DLT pipeline** `pipeline_project` ingests the synthetic project tables from
  files in `/Volumes/bluerridge_lng/landing/project/` using Auto Loader (batch).
- **DLT pipeline** `pipeline_drawings` ingests PDFs from
  `/Volumes/bluerridge_lng/landing/drawings/` using Auto Loader streaming. The
  bronze table carries the binary + metadata; silver carries parsed/extracted
  structured representation.
- DQ constraints at silver (DROP ROW for missing drawing_id, FAIL UPDATE for
  missing revision, etc.), mirroring the RCM reference's pattern.

#### 6.2.2 Unity Catalog

**Catalog: `mfg_mc_se_sa`** (user-owned, write-enabled). CREATE CATALOG is
blocked at this workspace by Default Storage — we don't need our own catalog.
All schemas live under `mfg_mc_se_sa` with the `bluerridge_` prefix to isolate
this build's objects.

| Schema | Purpose | Example tables |
|---|---|---|
| `mfg_mc_se_sa.bluerridge_landing` | Volumes for raw files | `drawings/` (Volume), `project/` (Volume) |
| `mfg_mc_se_sa.bluerridge_bronze_drawings` | Raw PDF binaries + Auto Loader metadata | `raw_files` |
| `mfg_mc_se_sa.bluerridge_bronze_project` | Raw project tables | `schedule_raw`, `cost_raw`, `ncrs_raw`, `change_orders_raw`, `safety_log_raw`, `daily_reports_raw` |
| `mfg_mc_se_sa.bluerridge_silver_engineering` | Cleaned, parsed, extracted | `drawings_parsed`, `drawings_extracted`, `schedule`, `cost`, `ncrs`, `change_orders`, `safety_log` |
| `mfg_mc_se_sa.bluerridge_gold_pm` | PM-facing aggregates | `compliance_findings`, `kpi_daily`, `risk_forecast`, `daily_brief` |
| `mfg_mc_se_sa.bluerridge_agents` | Genie Agent artifacts, prompt configs | `genie_config`, `prompts` |
| `mfg_mc_se_sa.bluerridge_app` | App-only working tables (if any) | — |

Governance:

- **Tags**: `sensitivity={LOW,MED,HIGH}`, `data_class={ENGINEERING,FINANCIAL,SAFETY}`, `layer={bronze,silver,gold,landing,agents,app}`.
- **Grants**: `pm_group` reads gold; `engineer_group` reads silver + gold; app service principal reads gold + Lakebase. Mirrors the RCM access-control pattern but with construction-shaped groups.
- **Row filter** (demonstrative): drawings table filtered by `discipline` so a
  mechanical engineer only sees mechanical drawings in that specific view.

#### 6.2.3 Document intelligence (GenAI)

Four AI Functions chained inside a notebook/job:

1. `ai_parse_document(binary)` on each `.pdf` → markdown representation.
2. `ai_extract(parsed_markdown, schema)` → `drawing_id`, `discipline`, `revision`, `spec_citations[]`, `title_block_fields`.
3. `ai_classify(parsed_markdown, labels=['ISO','PID','GA','SPEC','OTHER'])`.
4. `ai_query(parsed_markdown, 'Does this drawing comply with ASME B16.5 and B31.3? …')` → structured JSON array of findings:
   `[{finding_id, status: PASS|FAIL|REVIEW, reason, citation, severity, page_num, bbox:[x,y,w,h]}]`.
   A single drawing can produce multiple findings (one row per finding, not per
   drawing).

Results land in `gold_pm.compliance_findings` with grain `(drawing_id, finding_id)`
plus the Volume path + `page_num` + `bbox` so the UI can open the PDF and draw
a highlight rectangle. Because the drawings are synthetic, the generator plants
each flaw at known coordinates and emits a `ground_truth_findings` sidecar; the
pipeline's output is scored against ground truth and the evidence folder commits
both LLM-detected findings and the ground-truth comparison (demo-quality
accuracy, not production).

**Vector Search index** `spec_citations_vs` is built from a corpus of code /
standard text. **Copyright constraint:** ASME and IBC codes are copyrighted —
we store **paraphrased summaries with clause citations only**, never verbatim
excerpts. OSHA regulations (29 CFR 1910.*) are federal and public domain, so
OSHA text may be stored verbatim. The app uses the index on-click to resolve a
citation ID → paraphrased summary so the PM can see *why* the drawing failed.

#### 6.2.4 ML — risk forecast

`gold_pm.risk_forecast` produced by `ai_forecast` on `silver_engineering.schedule`
milestone delay history. Keeps the ML box honest without a full AutoML
production. Metrics (MAE, bias) committed to `evidence/risk_model_metrics.json`.

#### 6.2.5 Genie Agent

A single **Genie Space** over `gold_pm.*` (per `databricks-genie` skill), curated
with:

- 10 verified sample questions covering compliance ("how many drawings failed
  this week?"), schedule ("which milestones slipped?"), cost ("explain the
  budget variance"), risk ("where am I at risk?"), NCRs.
- Table and column descriptions (synonyms for construction jargon — "ISO" vs
  "isometric", "NCR" vs "nonconformance", "RFI" vs "request for information").
- Example SQL answers for the trickier questions.

The space is defined in `resources/genie-space.yml` and the sample questions in
`06_genie_agent/sample_qa.md`.

#### 6.2.6 Lakebase

A Lakebase Postgres project `bluerridge_pm` with synced tables from `gold_pm`
for the KPI strip:

- `gold_pm.kpi_daily` → `kpi_daily` (synced, 5-min refresh)
- `gold_pm.compliance_findings` → `compliance_findings` (synced)
- `gold_pm.risk_forecast` → `risk_forecast` (synced)

The app reads from Lakebase for the KPI strip (low latency), from Databricks SQL
for everything else, and calls Genie One MCP for chat.

#### 6.2.7 Databricks App

**Stack (mirrors RCM reference):**

- Frontend: React 18 + Vite + TypeScript + Tailwind + Zustand + framer-motion +
  TanStack React Query + Lucide + Recharts.
- Backend: Python FastAPI (Uvicorn), Databricks SDK (user-identity-forwarded
  for Genie, SP for everything else), Databricks SQL connector for warehouse,
  psycopg for Lakebase.
- Chat endpoint calls Genie One MCP under the hood (or the Genie Conversation
  API directly if MCP isn't practical from inside a Databricks App — see §11).

**Auth: On-Behalf-Of (OBO) for Genie.** Required wiring per
`databricks-app-design`:

1. `app.yaml` declares `user_api_scopes: [dashboards.genie]`.
2. Backend `/api/whoami` reads `x-forwarded-email` + `x-forwarded-user` headers
   and returns the signed-in user; frontend shows a `Badge` with it.
3. Genie API calls pass the user's forwarded token (or use the SDK's OBO
   mechanism) so the query runs as the PM, not the SP.
4. SP continues to serve non-Genie requests (warehouse reads, Lakebase).
5. Identity chip in the chat header **truthfully** reflects OBO vs SP per
   endpoint — if a given answer ran as SP, the chip says so.

**Research requirement before implementing auth** (per user request): the
builder MUST consult current Databricks App OBO documentation and at least
one working public Databricks App repo that implements OBO before writing
auth code. Historical pain points with App auth justify extra care here.
Suggested starting points to validate at build time:

- Current Databricks docs: "Databricks Apps — authorization" / "user_api_scopes" / "on-behalf-of".
- Known public reference: the `databricks-solutions` org on GitHub has example
  apps; validate at build time which currently demonstrates OBO cleanly.
- The RCM reference in this user's Downloads shows the SP pattern (contrast
  only — RCM does *not* use OBO).

**Pages:**
- `/` — AI Co-Pilot (chat center stage)
- `/compliance` — Full compliance workqueue
- `/schedule` — Schedule & Risk (jumps back to chat)
- `/cost` — Cost & Budget
- `/safety` — Safety & Quality
- `/drawings/:id` — PDF viewer with highlighted violation

**Visual language** must mirror the RCM reference:
- Dark gradient sidebar (`linear-gradient(180deg,#0f172a 0%,#1e293b 50%,#0f172a 100%)`).
- White top bar with breadcrumb + search + project selector + bell + avatar.
- Inter font (JetBrains Mono for drawing IDs / SQL).
- Emerald/teal brand accent (`#10b981` → `#0d9488`).
- Rounded-xl cards (`metric-card`, `chart-container`), subtle shadow, hover lift.
- Status pills using `bg-50 / text-700 / border-200` triple per color family.
- Live-data pulse dot (emerald, animate-pulse) in page header.
- Framer-motion stagger on load (0.08s per item).
- Compliance badge color conventions: FAIL critical = red, FAIL high = red,
  REVIEW = amber, PASS = emerald.

### 6.3 Packaging (DAB)

Everything above is one Databricks Asset Bundle (`databricks.yml`) with
resources under `resources/`. One `databricks bundle deploy` lays down:

- Both DLT pipelines
- The two orchestration jobs (synthetic data gen; doc intelligence)
- The risk forecast job
- The Vector Search endpoint + index
- The Genie Space
- The Lakebase project + synced tables
- The App

**End-to-end single-command deploy.** Several resources have ordering
dependencies that `bundle deploy` doesn't natively solve — notably: Lakebase
database must exist before synced-table resources, and the App's service
principal needs Postgres grants after Lakebase is up (otherwise first boot
fails with `42501 permission denied`). We handle this with the DAB
`scripts:` block:

- `pre_deploy`: ensures the Lakebase project exists (or create-if-missing).
- `post_deploy`: issues the Postgres grants to the App SP; executes
  `05_governance/grants.sql` for UC grants; triggers an initial run of the
  synthetic-data job so the pipelines have something to ingest.

If any of these can't be made single-command for a given target workspace,
the fallback sequence is documented in `docs/BUILD.md` and §13 Goal 4
is marked satisfied by the documented sequence rather than a single command.

---

## 7. Data Model (key tables)

### `gold_pm.compliance_findings`

Grain: **one row per finding** (a drawing may have multiple findings).

| col | type | notes |
|---|---|---|
| `drawing_id` | STRING | FK to `silver_engineering.drawings_extracted` |
| `finding_id` | STRING | PK component; UUID emitted by the compliance job |
| `volume_path` | STRING | `/Volumes/bluerridge_lng/landing/drawings/…` |
| `page_num` | INT | page where the violation sits |
| `bbox` | ARRAY<DOUBLE> | `[x, y, w, h]` normalized to page size; drives the UI highlight |
| `discipline` | STRING | mechanical, electrical, structural, piping, instr |
| `revision` | STRING | drawing revision |
| `drawing_type` | STRING | from `ai_classify` |
| `status` | STRING | PASS \| FAIL \| REVIEW |
| `severity` | STRING | critical \| high \| medium \| low |
| `reason` | STRING | LLM-judge reason (short, PM-readable) |
| `citation` | STRING | e.g. 'ASME B16.5 §4.2' |
| `matched_ground_truth` | BOOLEAN | did the LLM finding match a planted flaw? |
| `generated_at` | TIMESTAMP | used to filter "this week" (`>= today - 7 days`) |

Primary key: `(drawing_id, finding_id)`. "This week" everywhere in the UI
means `generated_at >= current_date() - INTERVAL 7 DAYS`.

### `gold_pm.kpi_daily`

Daily snapshot keyed by `(project_id, date)` with columns for schedule status,
budget EAC, safety TRIR, open NCRs, counts.

### `gold_pm.risk_forecast`

Milestone-level predicted slip probability over the next 90 days.

### `gold_pm.daily_brief`

Narrator-generated short Markdown blurbs produced by `ai_query` nightly, keyed
by date. The chat seeds this as the first message of the day.

### Synthetic data volumes

| Entity | Count | Shape |
|---|---|---|
| Drawings (PDFs) | 1,200 total | Mix of ISO, P&ID, GA, Spec; ~20% carry at least one planted flaw |
| Compliance findings — cumulative | ~240 | ~20% of 1,200 drawings × avg 1 finding each |
| Compliance findings — "this week" | ~24 | Last 7 days by `generated_at`; this is the 24 shown in the UI |
| Project schedule rows | ~500 milestones | 2-year horizon, dependencies |
| Cost / change orders | ~120 line items + 20 COs | |
| NCRs | ~80 | 24 open, matching the UI's "open NCRs" tile |
| Safety log entries | ~400 | |
| Daily reports | ~180 | Free text, used for narrator generation |
| Code / standard excerpts (VS corpus) | ~50 | Paraphrased ASME/IBC + verbatim OSHA; each with clause citation |

---

## 8. Repo Structure

```
hobbs_fe/
├── README.md                                 # one-page scan
├── databricks.yml                            # DAB
├── resources/
│   ├── pipeline-project.yml
│   ├── pipeline-drawings.yml
│   ├── job-synthetic-data.yml
│   ├── job-doc-intelligence.yml
│   ├── job-risk-forecast.yml
│   ├── genie-space.yml
│   ├── vector-search.yml
│   ├── lakebase.yml
│   └── app.yml
├── 01_synthetic_data/
│   ├── 01_generate_project_data.ipynb        # executed, outputs visible
│   ├── 02_generate_drawings.ipynb            # produces ~1200 PDFs → Volume
│   └── outputs/                              # row counts, sample preview
├── 02_pipelines/
│   ├── pipeline_project.py                   # DLT definitions
│   ├── pipeline_drawings.py
│   └── outputs/
│       └── pipeline_run_summary.md           # pipeline_id, duration, DQ counts
├── 03_doc_intelligence/
│   ├── 01_parse_drawings.ipynb               # ai_parse_document
│   ├── 02_extract_fields.ipynb               # ai_extract
│   ├── 03_classify_drawings.ipynb            # ai_classify
│   ├── 04_compliance_check.ipynb             # ai_query LLM-judge
│   ├── 05_vector_index.ipynb                 # build VS index on code excerpts
│   └── outputs/
│       ├── sample_parsed.md                  # one drawing fully parsed
│       ├── sample_extracted.jsonl
│       └── sample_findings.jsonl
├── 04_ml_risk/
│   ├── 01_risk_forecast.ipynb                # ai_forecast
│   └── outputs/
│       └── risk_model_metrics.json
├── 05_governance/
│   ├── tags.sql
│   ├── grants.sql
│   ├── row_filters.sql
│   └── outputs/
│       └── grant_listing.md                  # `SHOW GRANTS` output
├── 06_genie_agent/
│   ├── space_config.yml
│   ├── sample_questions.md
│   └── outputs/
│       └── sample_qa.md                      # 10 Q→SQL→result rows
├── 07_lakebase_sync/
│   ├── sync_config.yml
│   └── outputs/
│       └── synced_tables_listing.md
├── 08_app/
│   ├── frontend/
│   ├── backend/
│   ├── app.yaml
│   └── requirements.txt
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD.md                              # how to deploy
│   ├── TALK_TRACK.md                         # presenter notes for roleplay
│   └── superpowers/specs/                    # this doc lives here
└── evidence/
    ├── 00_READ_ME_FIRST.md                   # tour of proof per FE Bar box
    ├── mockups/                              # dashboard-v3-chat.html etc.
    ├── pipeline_run_logs/
    │   ├── pipeline_project_run.json
    │   └── pipeline_drawings_run.json
    ├── notebook_html_exports/                # .html exports of every executed notebook
    ├── sample_compliance_outputs/            # end-to-end JSON per sample drawing
    ├── genie_qa_transcript.md                # live transcript from the Genie Space
    ├── risk_model_metrics.json
    ├── app_screenshots/
    │   ├── 01_copilot_home.png
    │   ├── 02_compliance_page.png
    │   ├── 03_pdf_viewer_highlighted.png
    │   └── ...
    └── app_demo.mp4                          # 60-90s screen recording
```

---

## 9. Evidence Requirements (per component)

| FE Bar box | Evidence artifact(s) | Lives in |
|---|---|---|
| Lakeflow ingestion | DLT pipeline run summary (JSON): record counts, DQ assertions | `evidence/pipeline_run_logs/` + `02_pipelines/outputs/` |
| Unity Catalog governance | `SHOW GRANTS` output + tags listing | `05_governance/outputs/grant_listing.md` |
| Lakebase | Synced-tables listing + sample query result | `07_lakebase_sync/outputs/synced_tables_listing.md` |
| GenAI (doc intel) | Executed notebooks with cell outputs + sample LLM responses as JSON | `03_doc_intelligence/outputs/` + `.html` exports |
| ML (risk) | Model metrics JSON + forecast chart PNG | `04_ml_risk/outputs/` |
| Genie Agent | 10-exchange Q→SQL→result transcript | `evidence/genie_qa_transcript.md` |
| Databricks App | Screenshots + 60-90s screen recording | `evidence/app_screenshots/` + `evidence/app_demo.mp4` |
| **Repo overview** | `evidence/00_READ_ME_FIRST.md` with a checklist mapping box → artifact | repo root |

`00_READ_ME_FIRST.md` is explicitly a grader-facing tour. It is the single most
important document for build grading.

---

## 10. Decisions already made (my calls)

Flagged so a planner knows what *not* to re-litigate:

- **Project**: Blue Ridge LNG Terminal — Phase 2 (fictional).
- **Primary user**: project manager (not engineer, not QA/QC).
- **Agent architecture**: **no MAS**. One Genie Space over `gold_pm.*`, called via
  Genie One MCP from the app.
- **Doc intel approach**: ingest-time batch (parse → extract → classify → judge)
  that materializes `compliance_findings` as a plain table the Genie Agent reads.
  Vector Search is used only on the UI click to retrieve clause text, not inline
  in the chat answer.
- **ML**: `ai_forecast` (not AutoML, not a notebook ML model) — keeps scope tight.
- **Catalog**: `mfg_mc_se_sa` (CREATE CATALOG blocked at the workspace); all our schemas use the `bluerridge_` prefix.
- **App framework**: React 18 + Vite + TypeScript + Tailwind + FastAPI, mirroring
  the RCM reference stack (confirmed by user).
- **Visual language**: mirror RCM reference exactly — see §6.2.7.
- **Packaging**: single DAB; `databricks bundle deploy -t demo` must work.
- **Visibility**: every notebook commits with executed outputs; every pipeline
  run commits a summary.
- **Grader-first**: `evidence/` folder structure above is non-negotiable.
- **Breadth-first scope**: six boxes equally, doc intel the hero.
- **Compliance findings grain**: one row per finding (not per drawing). A
  drawing may have multiple findings; each has its own `page_num` + `bbox`
  for the UI highlight.
- **Ground truth**: the synthetic drawing generator plants flaws at known
  coordinates and emits a `ground_truth_findings` sidecar; the pipeline
  scores LLM detections against it. Committed to `evidence/`.
- **Code copyright**: ASME + IBC are paraphrased with clause citations only
  (never verbatim). OSHA is federal and public domain, so verbatim is OK.
- **Deploy ordering**: handled by DAB `scripts:` pre/post-deploy hooks that
  create the Lakebase DB first and apply Postgres/UC grants after. If the
  hook model fails for a target workspace, fall back to a documented
  sequence in `docs/BUILD.md`.
- **Deadline**: 2026-11-20 (2 weeks from today). Solo build. User will run
  an overnight autonomous build after plan approval.
- **Lakeflow ingestion satisfied by**: Auto Loader + Spark Declarative
  Pipelines (SDP). No managed-connector requirement.
- **Auth**: OBO for Genie queries, SP for everything else. The identity chip
  is truthful per endpoint. Builder consults current docs + working public
  OBO example before implementing.
- **Cut order documented in §4.1.**

---

## 11. Left to the builder

Items a competent Databricks solutions engineer can and should decide:

- Exact Databricks Foundation Model choice for each AI Function
  (`ai_parse_document`, `ai_extract`, `ai_classify`, `ai_query`) — pick the
  smallest model that meets the quality bar on sample drawings.
- Exact Python tooling for generating synthetic PDFs with intentional errors
  (ReportLab? WeasyPrint? Programmatic drawing with matplotlib + annotations?).
  Any that produces readable multi-page PDFs is fine.
- Exact DLT syntax (Python vs SQL) per pipeline file — pick what reads cleanest.
- Specific column schemas inside each silver table beyond what §7 lists.
- Specific Lakebase schema and index strategy for synced tables.
- Final React component boundaries; names of hooks and store slices.
- Whether Genie One MCP is called directly from the App backend, or whether we
  call the Genie Conversation API directly from the backend and label it as
  "equivalent to Genie One MCP" in the architecture doc. Pick whichever works
  cleanly from inside a Databricks App's service principal context.
- Exact Vector Search embedding model + chunking strategy.
- Workspace / profile for deployment — the user will supply at build time.
- Whether to include tests (and how many) — recommended but not required by
  the FE Bar; builder judgment.

---

## 12. Risks

- **AI Function cost / latency** on 1,200 drawings. Mitigation: cap at ~1,200
  via the generator; run doc intel as a single batch job once at build time;
  commit the output table as parquet/CSV sample so re-running isn't needed.
- **Genie One MCP reachability from inside a Databricks App.** May require
  calling the Genie Conversation API directly instead. §11 flags this; the
  builder decides.
- **OBO auth complexity.** The user has hit auth issues in prior Databricks
  App builds. Mitigation: §6.2.7 mandates a research pass against current
  docs + a working public OBO reference before writing auth code; auth is
  implemented and verified **before** the chat endpoint is wired, not after.
  Build a `/api/whoami` endpoint first and verify the headers come through
  as a smoke test.
- **Two-week solo deadline.** Mitigation: cut order in §4.1 is explicit;
  builder stops polishing lower-priority items once the hero and chat work.
- **Evidence drift.** Every rebuild risks diverging outputs vs. committed
  artifacts. Mitigation: a top-level `make evidence` script that regenerates
  all `evidence/*` files from a fresh deploy run.
- **Scope creep on the app.** The reference RCM app has 6+ pages; we only need
  3 built out well (home chat, compliance page, PDF viewer). Resist adding more.

---

## 13. Success

The build is done when:

1. `databricks bundle validate` passes.
2. `databricks bundle deploy -t demo` deploys cleanly.
3. `databricks bundle run` on each resource succeeds.
4. The app loads, the chat answers at least 5 of the 10 sample questions
   correctly, and the compliance page lists real `gold_pm.compliance_findings`
   rows.
5. Every box in §9 has a committed artifact.
6. `evidence/00_READ_ME_FIRST.md` is written as the grader-facing tour.
7. The repo passes a one-pass read by a Databricks SA who has never seen it.
