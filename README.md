# Blue Ridge LNG — Project Manager Co-Pilot

> **Grader? Start at [`evidence/00_READ_ME_FIRST.md`](evidence/00_READ_ME_FIRST.md).** It maps each of the six FE Bar boxes (box 4, ML or GenAI, is shown as two rows) to the committed files that prove it ran: executed notebooks, pipeline event-log summaries and app logs. You do not have to run anything to check it.

## What it is

An end-to-end Databricks build for the project manager of a fictional LNG build, **Blue Ridge LNG Terminal, Phase 2**, modeled on the EPC work Bechtel runs.

Drawing audits eat billable engineering hours. In this build, GenAI reads 1,200 synthetic engineering drawings and checks them against five code rules¹. A Databricks App then puts the results in front of the PM. Each morning the app opens on a grounded daily brief, a KPI strip, a risk card and a Genie chat that answers as the signed-in user. Every flagged drawing opens as a PDF, with the violation highlighted and the code clause beside it.

The build covers the six FE Bar boxes: Lakeflow ingestion, Unity Catalog governance, Lakebase serving, ML or GenAI (one box, evidenced twice: a schedule-risk forecast, and document intelligence plus the daily brief), a Genie Agent and a Databricks App. It deploys as one Declarative Automation Bundle plus a short documented sequence.

All data is synthetic. No real customer or Bechtel data is used.

## Architecture in six lines

1. **Ingest:** PDFs and CSVs land in Unity Catalog Volumes. Auto Loader and Spark Declarative Pipelines build the bronze and silver layers, with data-quality expectations ([`02_pipelines/`](02_pipelines/)).
2. **Understand:** `ai_parse_document`, then `ai_extract` and `ai_classify`, then an `ai_query` compliance judge (Claude Sonnet 4.5), then deterministic guardrails. The judge is scored against 274 planted flaws: precision 58.1%, recall 81.0% ([`03_doc_intelligence/`](03_doc_intelligence/)).
3. **Gold:** daily KPIs, an `ai_forecast` schedule-risk model shown as risk bands, and an `ai_query` daily brief checked by a validator. Vector Search indexes the code clauses ([`05_gold/`](05_gold/), [`04_vector_search/`](04_vector_search/)).
4. **Govern:** Unity Catalog tags, lineage and a real row filter on `drawing_register`. The app's service principal (SP) gets least-privilege grants ([`06_governance/`](06_governance/)).
5. **Serve:** five gold tables are synced to Lakebase Postgres for millisecond point reads (p50 3 ms, against 428 ms on the SQL warehouse). A Genie space scored 10/10 on curated questions and 5/5 on held-out ones ([`08_lakebase/`](08_lakebase/), [`07_genie_agent/`](07_genie_agent/)).
6. **App:** React + FastAPI. Genie runs on behalf of the signed-in user (OBO) and fails closed without the user's token. It uses the managed Genie MCP server, with a guarded fallback to the Conversation API. MCP is verified as the app service principal; in the one live signed-in session, MCP returned 403 and the chat answered via the Conversation API fallback (still OBO). The data routes run as the SP, so in the app's own pages every user sees every discipline; only chat answers are row-filtered per user ([`09_app/`](09_app/)).

For details, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Deploy

[`docs/BUILD.md`](docs/BUILD.md#deploy-order) has the deploy order, prerequisites, costs and teardown. In short:

1. Run `databricks bundle validate`.
2. Build the single-page app (SPA).
3. Run `databricks bundle deploy -t demo`.
4. Run the notebooks in order.
5. Run `databricks bundle run pm_copilot_app`.
6. Run `scripts/post_deploy_grants.sh`.

Always pass `--profile`. The final verification run is in [`evidence/deploy_transcript.md`](evidence/deploy_transcript.md).

## Documents

| Document | For |
|---|---|
| [`evidence/00_READ_ME_FIRST.md`](evidence/00_READ_ME_FIRST.md) | Graders: each box and its proof, plus honest limitations |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The system as built: data flow, identities, the Lakebase hot path, where governance sits |
| [`docs/BUILD.md`](docs/BUILD.md) | Building and deploying, running a notebook as evidence, costs and teardown |
| [`docs/TALK_TRACK.md`](docs/TALK_TRACK.md) | Presenter notes for the roleplay |
| [`09_app/API.md`](09_app/API.md) | The app's endpoints and the chat event stream |
| [Design spec](docs/superpowers/specs/2026-11-06-bluerridge-pm-copilot-design.md), [implementation plan](docs/superpowers/plans/2026-11-06-bluerridge-pm-copilot.md) | Why it is built this way |

## Repo map

| Path | What is in it |
|---|---|
| `databricks.yml`, `resources/` | The bundle (`bluerridge_pm_copilot`, target `demo`) and its resource definitions |
| `00_setup/` | Creates the `bluerridge_*` schemas and landing Volumes in catalog `mfg_mc_se_sa` |
| `01_synthetic_data/` | Synthetic project data, and drawing PDFs with planted flaws and their ground truth |
| `02_pipelines/` | Auto Loader + Spark Declarative Pipelines (bronze and silver) |
| `03_doc_intelligence/` | Parse, extract, classify, compliance judge, guardrails, ground-truth scoring |
| `04_vector_search/` | Code-excerpt corpus and Vector Search index |
| `05_gold/` | Daily KPIs, risk forecast, daily brief |
| `06_governance/` | Unity Catalog tags, grants and row filter |
| `07_genie_agent/` | Genie space and its benchmark |
| `08_lakebase/` | Lakebase project and synced tables |
| `09_app/` | React + FastAPI Databricks App |
| `scripts/` | Notebook-evidence tool, post-deploy grants |
| `evidence/` | The grader tour, plus committed proof of every run |
| `docs/` | Architecture, build guide, talk track, spec, plan |

Each numbered folder keeps the results of its notebooks in an `outputs/` subfolder. HTML exports of every executed notebook are in `evidence/notebook_html_exports/`.

---

¹ **Citation labels are illustrative.** The five labels (`ASME B16.5 §4.2`, `OSHA 1910.147`, `IBC 1005.1`, `ASME B31.3 §341`, `ASME B31.3 §322`) are fixed project labels, and their clause numbers are not authoritative. For example, real ASME B16.5 pressure-temperature ratings are in section 2, not 4.2. The code excerpts are plain-language paraphrases, not quotes of the codes. See [`04_vector_search/code_excerpts/README.md`](04_vector_search/code_excerpts/README.md).
