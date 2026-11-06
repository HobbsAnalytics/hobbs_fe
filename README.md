# Blue Ridge LNG — Project Manager Co-Pilot

An end-to-end Databricks demo for the project manager of a fictional large LNG build (**Blue Ridge LNG Terminal — Phase 2**, modeled on the EPC work Bechtel runs). It audits synthetic engineering drawings against regulatory codes: PDFs land in a Unity Catalog Volume, Auto Loader and Spark Declarative Pipelines ingest them, and a GenAI chain (`ai_parse_document`, `ai_extract`, `ai_classify`, an LLM compliance judge) emits one row per finding, scored against planted ground truth. Gold KPIs, an `ai_forecast` schedule-risk model, Vector Search over code clauses, a Genie Space and Lakebase-synced tables back a React + FastAPI Databricks App whose Co-Pilot chat answers through Genie with on-behalf-of (OBO) auth. It covers all six FE Bar components and deploys as a single Declarative Automation Bundle.

> **Grader? Start at [`evidence/00_READ_ME_FIRST.md`](evidence/00_READ_ME_FIRST.md).**
> The app cannot be run from a read-through of the repo, so every component commits proof that it ran, and that file maps each FE Bar box to the exact artifact that proves it.

All data is synthetic. No real customer or Bechtel data is used.

## Documents

- Design spec: [`docs/superpowers/specs/2026-11-06-bluerridge-pm-copilot-design.md`](docs/superpowers/specs/2026-11-06-bluerridge-pm-copilot-design.md)
- Implementation plan: [`docs/superpowers/plans/2026-11-06-bluerridge-pm-copilot.md`](docs/superpowers/plans/2026-11-06-bluerridge-pm-copilot.md)
- Build and deploy guide: [`docs/BUILD.md`](docs/BUILD.md)

## Repo map

| Path | What is in it |
|---|---|
| `databricks.yml`, `resources/` | The bundle (`bluerridge_pm_copilot`, target `demo`) and its resource definitions |
| `00_setup/` | Creates the `bluerridge_*` schemas and landing Volumes in catalog `mfg_mc_se_sa` |
| `01_synthetic_data/` | Synthetic project data and drawing PDFs with planted, ground-truthed flaws |
| `02_pipelines/` | Auto Loader + Spark Declarative Pipelines (bronze and silver) |
| `03_doc_intelligence/` | Parse, extract, classify, compliance judge, ground-truth scoring |
| `04_vector_search/` | Code-excerpt corpus and Vector Search index |
| `05_gold/` | Daily KPIs, risk forecast, daily brief |
| `06_governance/` | Unity Catalog tags, grants and row filter |
| `07_genie_agent/` | Genie Space and its sample Q&A |
| `08_lakebase/` | Lakebase instance and synced tables |
| `09_app/` | React + FastAPI Databricks App (OBO chat) |
| `evidence/` | The grader tour plus committed proof of every run |
| `docs/` | Spec, plan and build guide |

Each numbered folder keeps the results of its notebooks in an `outputs/` subfolder; HTML exports of every executed notebook are in `evidence/notebook_html_exports/`.
