# Talk track: the Yoodli roleplay

Presenter notes for showing the working app to a business persona (a project director or controls lead) and a technical persona (a data or platform architect). Every number here comes from a committed file, named in brackets the first time it appears, so any answer can be backed up on the spot. Speak in the PM's language first and the platform's second.

**Before you start.**
- Open `https://bluerridge-pm-copilot-7474644652812129.aws.databricksapps.com` in your managed Chrome profile, already signed in, at 1440 px wide or more so the right rail shows.
- Have [`evidence/00_READ_ME_FIRST.md`](../evidence/00_READ_ME_FIRST.md) open in a second tab.
- The data is anchored to **Friday 2026-11-06** ("this week" = 2026-10-31 to 2026-11-06).
- One drawing worth opening: **BRL-ELE-GA-0842**. It is a planted egress-width flaw (`IBC 1005.1`) with a tight, ground-truth highlight, and it is the drawing the live check opened ([`09_app/outputs/live_obo_chat.md`](../09_app/outputs/live_obo_chat.md)).

## (a) 30-second opener

> "On a build like Blue Ridge LNG Phase 2, drawing audits eat billable engineering hours. Every week a stack of drawings comes back from the designers. Before anything is built, someone has to check each one against the codes: flange ratings, relief valves, lockout tags, weld exams, exit widths. This week that stack was 238 drawings, and most of them were fine.
>
> What I'll show you is a Co-Pilot for the project manager. It reads every drawing overnight, flags the ones that look wrong, shows you *where* on the sheet and *which* code, and answers questions about the job in plain English, all on Databricks. Engineers spend their hours on the 51 drawings it flagged instead of all 238. I'll also show you exactly how often it's right, because that's the part that matters."

[238 / 187 / 51: [`05_gold/outputs/kpi_today.md`](../05_gold/outputs/kpi_today.md)]

## (b) Demo click path

The narration is in quotes. Point at the thing on screen before you talk about it.

1. **Home: the daily brief.**
   - The page opens on *Project Co-Pilot*, with "Live · snapshot … · Lakebase" top right and the KPI strip below it: Schedule *on track, 6 of 11 key milestones, MS-281 4 days late*; Budget (EAC) *+2.3%, $4.8M over $208.7M*; Safety *TRIR 0, 28 days*; Open NCRs *24 (9 compliance, 15 workmanship)*.
   - The chat's first message is the **Daily Brief**.
   - Say: "This was written by an LLM this morning, but every number in it was checked by code against the source tables before it was stored. Read the compliance line: *51 of 238 drawings flagged for engineer review this week.* It says *flagged for review*, not *failed*, on purpose."
   - [`05_gold/outputs/daily_brief_today.md`](../05_gold/outputs/daily_brief_today.md): validator PASS, 130 words, claim-by-claim trace.
2. **Ask the question.** Click the suggested action **"Which drawings failed this week and why?"** in the right rail, or type it. Say: "This goes to a Genie space, and it runs *as me*. My Unity Catalog permissions apply, not the app's."
3. **The answer and the SQL card.**
   - The answer streams in. Expand the **Generated SQL** card.
   - Say: "Nothing is a black box. This is the SQL Genie wrote, and this table is what it returned." The table shows at most 50 rows, with a "showing first N of M" note. In the live check, the user's question returned 85 rows, the week's 85 FAIL findings. The question text itself is not logged.
   - Point at the footer: *AI-generated — verify before action · Genie · as you (OBO) · via …*. It names the transport that answered. In the live check it read "via Conversation API" (see the technical Q&A on MCP).
4. **Open a drawing.**
   - In **Sources → Drawings from Volume**, click **BRL-ELE-GA-0842**. The PDF viewer opens on the right sheet, with a red box over the exit that is too narrow.
   - Say: "Here's the violation on the actual drawing." The findings rail shows the judge's reason, the verbatim evidence quote, and where the box came from: *Highlight: synthetic ground truth*.
   - Be upfront: "These tight boxes come from the planted flaws in the synthetic set. On real drawings the box comes from the parser and is labelled *approximate*."
5. **The code clause.**
   - Go back to the chat. Under **Code citations**, click **IBC 1005.1**. The citation panel opens with the clause in plain language and up to three related clauses, retrieved from Vector Search.
   - Say: "The labels are illustrative project labels. The clause numbers aren't authoritative, and the text is a paraphrase, not the code. In production this would point at the customer's licensed code library." [[`04_vector_search/code_excerpts/README.md`](../04_vector_search/code_excerpts/README.md)]
6. **The compliance page.**
   - Click **Doc Compliance** in the sidebar (badge **51**). The table is the week's FAIL findings, paginated on the server, with *week / all* and *FAIL / REVIEW* toggles.
   - Click a row. The finding drawer shows the citation panel and an honest label for where the highlight came from.
   - Say: "This is the engineer's work queue."
7. **Risk and the late list.**
   - Go back to **AI Co-Pilot**. In the right rail, point at **Schedule Risk** (*ML forecast · by band*): **26 High**, led by MS-335, MS-351 and MS-352.
   - Below it is **Late or due today**: **6 late · 1 due today**. The worst is MS-271, 15 days late, with 60 open milestones waiting on it.
   - Say: "Risk is shown as a band, not a percentage. I'll tell you why in a minute."
   - [[`05_gold/outputs/risk_top5.md`](../05_gold/outputs/risk_top5.md)]

If something fails live: the UI shows a plain error card instead of a stack trace. Switch to the evidence tab and show the same thing in [`chat_selftest.md`](../09_app/outputs/chat_selftest.md) and [`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md).

## (c) Value story for the business persona: triage

- **The ask is triage, not replacement.** "Your engineers review 51 flagged drawings instead of 238, about a fifth of the stack, and they start from a box on the sheet and a code reference instead of a blank page."
- **Be honest about the numbers before they ask.**
  - **Recall 81%.** Of the 274 code violations we planted across the 1,200-drawing set, it caught 222.
  - **Precision 58%.** Of what it flags, a bit more than half is real.
  - In this week's stack, 21 of the 51 flagged drawings carry a real planted flaw and 30 are false alarms. It missed 3 of the 24 flawed drawings.
  - "So a false alarm costs an engineer a few minutes to dismiss, and the misses are why you keep a light sample check on the passed pile."
  - [[`evidence/sample_compliance_outputs/compliance_eval_summary.md`](../evidence/sample_compliance_outputs/compliance_eval_summary.md), "Drawing level"]
- **Where it's already strong.** Exit widths (`IBC 1005.1`): 90% precision, 100% recall. Weld exam spec (`ASME B31.3 §341`): 100% precision, 88% recall. Pipe isometrics: 97% precision and recall. "Those you could nearly trust today."
- **Where it isn't yet.** Lockout/tagout tags (`OSHA 1910.147`): 34% precision, 54% recall. About a fifth of all false alarms come from the parser misreading tags like *LOTO* as *ROTO*. "That's a parser fix, not a model fix, and it's first on the roadmap."
- **What the hours are worth.** Don't quote a dollar figure: none is measured here. Ask instead: "How long does a discipline engineer spend checking one drawing against code? Multiply that by the 187 drawings this week that didn't need a second look." Their number is the business case.
- **The rest of the PM's morning.** The same screen carries schedule, budget, safety and NCRs, so the brief replaces the morning spreadsheet round. The KPIs are computed from the source tables and asserted against the project story: 6 of 11 milestones, MS-281 4 days late, +2.3% / $4.8M, TRIR 0, 24 open NCRs [[`kpi_today.md`](../05_gold/outputs/kpi_today.md)].

## (d) Technical persona Q&A

**"Walk me through the architecture."**
- PDFs and CSVs land in Unity Catalog Volumes. Auto Loader and Spark Declarative Pipelines build bronze and silver: 12 project tables, 15 expectations, 0 failed records, and a malformed-file test where a non-PDF is flagged and kept rather than crashing the run.
- AI functions run *in SQL over the lakehouse*: `ai_parse_document` (1,200 parsed, 0 errors), then `ai_extract` and `ai_classify`, then an `ai_query` judge on Claude Sonnet 4.5, then deterministic guardrails.
- The gold tables feed three serving paths: Lakebase for the app's point reads, the SQL warehouse for the governed table, and a Genie space for questions.
- One Declarative Automation Bundle deploys the pipelines, jobs, Vector Search, Genie space, Lakebase and the app.
- [[`docs/ARCHITECTURE.md`](ARCHITECTURE.md)]

**"How is it governed?"**
- **Row-level security.** There is a real UC row filter on `drawing_register`, by discipline, through a mapping table. A mechanical engineer sees 134 drawings, a piping lead 755 and an unmapped user none. That table is a simulation, asserted in [`grant_listing.md`](../evidence/grant_listing.md).
- **On-behalf-of for Genie.** The chat calls Genie with the signed-in user's token, so Genie's SQL obeys *their* permissions. It fails closed: no token means a 401, and there is no service-principal fallback.
- **Least-privilege service principal.** Everything else runs as the app's service principal, which gets only SELECT on gold, READ on the drawings Volume and SELECT on five Postgres tables.
- **Tags and lineage.** 112 tags (prefixed `br_`, because the account's governed tags own `layer` and `sensitivity`) and 29 lineage edges from system tables.
- **Say it before they find it.** The shared catalog grants `account users` read access by inheritance, so in this sandbox every table is readable account-wide. The row filter is the only control the build adds. That's fine for synthetic data and not acceptable for production.

**"Why Lakebase and not just the warehouse?"**
- The home screen makes five tiny point reads. On Lakebase, p50 is 3.0 ms. Through the warehouse's Statement API the same read is 428 ms [[`synced_tables_listing.md`](../08_lakebase/outputs/synced_tables_listing.md)].
- Five gold tables are synced as SNAPSHOT, and Postgres row counts equal the Unity Catalog counts.
- `drawing_register` is deliberately *not* synced, because UC row filters don't propagate to a Postgres copy. It stays on the warehouse, where the filter holds.

**"How do you know the judge is any good, and how is it guarded?"**
- **Ground truth.** The synthetic generator planted 274 flaws with page and box, so precision and recall are measured, not claimed.
- **Three scored stages.** Raw judge output scores 37.2% precision. The judge's own self-check takes that to 46.5%. Deterministic guardrails take it to 58.1%, with recall at 81.0%: they drop a rule that can't apply to the drawing type, and an entry whose own reason or the drawing text says it complies. The guardrails cost 2 true positives and removed 98 false ones.
- **Audit trail.** Every suppressed entry is kept in `compliance_suppressed`, with why it was removed.
- **Tracking.** The runs are logged to MLflow (`compliance_judge_eval`).
- **No re-billing to score.** The scores come from the *saved* judge answers.
- [[`03b_compliance_guardrails.ipynb`](../03_doc_intelligence/03b_compliance_guardrails.ipynb), "What each guardrail suppressed"]

**"Integrity: did you tune it to the test?"**
- "We caught ourselves doing exactly that." Prompt v2 contained hints derived from the dataset (the kind of tags and values the generator uses), and it scored better: 55.5% precision and 92.3% recall at the self-check stage. We marked it *superseded for integrity*, wrote a neutral v3 with a leakage test, and **reported the lower number**.
- The daily brief went through the same discipline. v1 said "three milestones are late" and v2 said "7 already late", and both passed the validator of their day. A human read caught both errors, and the validator was hardened.
- [[`compliance_eval_summary.md`](../evidence/sample_compliance_outputs/compliance_eval_summary.md), "Prompt lineage"; [`daily_brief_today.md`](../05_gold/outputs/daily_brief_today.md), "Prompt history"]

**"What are the forecast's limits?"**
- It's a v1 trend model: `ai_forecast` of weekly slip per discipline, plus delay inherited from late predecessors.
- In an 8-week backtest, its error (MAE 10.6 days) was about the same as just carrying the last value forward (10.9 days). The 80% interval covered only 14% of points, so it's overconfident.
- That's why the app and the brief show **bands only** (26 High / 27 Medium / 11 Low) as a ranking signal, never a probability.
- Next: milestone-level features (predecessor slips, crew, weather) and a calibrated model, judged by the same backtest.
- [[`risk_model_metrics.json`](../evidence/risk_model_metrics.json)]

**"What's MCP doing here?"**
- The chat's primary transport is the **managed Genie MCP server** for the space (Public Preview). It uses stateless JSON-RPC `tools/call` with no retries, so a question is never posted twice.
- There is a guarded fallback to the Genie Conversation API, used only when MCP refuses the *first* call before it can have accepted the question.
- Live, the service principal's self-test goes through MCP (`headline=51`). In the signed-in user's session, MCP returned 403 for the user token and the fallback answered. The footer said so.
- "That's the design working. Which scope the MCP endpoint wants for a user token is an open item."
- [[`live_obo_chat.md`](../09_app/outputs/live_obo_chat.md)]

**"And the Genie space itself?"**
- It scored 10 out of 10 on curated questions and 5 out of 5 on held-out questions that were never loaded into the space. The scoring is rule-based against verified SQL [[`genie_qa_transcript.md`](../evidence/genie_qa_transcript.md)].
- It's one sample, because Genie isn't deterministic.

## (e) Tough questions, honest answers

**"How many false alarms will my engineers chase?"**
- "This week, 30 of the 51 flagged drawings. Precision is 58%."
- "Most of those false alarms have a known cause. About 28% are flange-rating arithmetic, where the judge compares class against pressure differently from the key. About 20% are parser misreads of lockout tags."
- "The guardrails already removed 98 false positives for a cost of 2 real ones."
- "Next is a parser fix for the tag misreads, and a feedback button so engineers' dismissals train the rules."
- Show the "Why the false positives happen" table in the scorecard.

**"So is it 100% accurate? Can it sign off drawings?"**
- "No, and it shouldn't. Recall is 81%: this week it passed 3 drawings that had a planted flaw. It's a triage tool that puts engineers on the right 51 first, and a professional engineer still signs off."
- "Where you hear 100% in this demo, it's narrow and stated as such." The weld-spec rule had 100% precision on this set, and Genie scored 10 of 10 on one run of curated questions. "Neither is a guarantee."

**"Are those real code clauses? Is `ASME B16.5 §4.2` right?"**
- "They're illustrative project labels. The clause numbers aren't authoritative: the real B16.5 ratings live in section 2. The excerpts are paraphrases, because ASME and IBC text is copyrighted."
- "In a real deployment you'd index the customer's licensed codes and their own project specs. The retrieval and citation plumbing is the same."

**"This is all synthetic. Why should I believe it works on real drawings?"**
- "Synthetic is what let us *measure* it. We planted 274 flaws with their exact locations, so precision and recall are facts, not anecdotes."
- "Real drawings will be messier, and the numbers will move. The pilot I'd propose runs it on a closed project's drawing set where you already know the NCRs, and compares."

**"What does it cost?"**
- **Batch.** "The whole 1,200-drawing batch is a batch job in SQL. Parsing is about 1,370 pages, which the notebook estimates at under $10 at list price (a directional figure). On top of that are 2,400 extract and classify calls and 1,204 judge calls. The judge step ran in about 7 minutes (409 s). Nothing re-bills unless you re-run it on purpose."
- **Always-on.** "The always-on pieces are a 1 CU Lakebase endpoint, a Vector Search endpoint and the app's compute. All three are documented with stop and delete commands."
- **Don't** quote a total dollar figure for the judge or the serving tier: none is measured in the repo.
- [[`01_parse_drawings.ipynb`](../03_doc_intelligence/01_parse_drawings.ipynb), [`03_compliance_check.ipynb`](../03_doc_intelligence/03_compliance_check.ipynb), [`docs/BUILD.md`](BUILD.md#costs-and-teardown)]

**"Can a PM see drawings outside their discipline?"**
- "Not through the governed table: the row filter is enforced on the warehouse, and Genie runs as the PM."
- "In this sandbox the catalog's inherited `account users` grant would let anyone read the other tables directly. That's the first thing to close for production: grant per group and drop the inherited access."

**"Why is one of the brief's top findings a false positive?"**
- If they spot that BRL-INS-PID-0580 appears in both the brief's context and the scorecard's false-positive list, say: "Good catch. That's exactly why the brief says *flagged for engineer review*."

## (f) Close and next steps

> "What you've seen is an end-to-end path: drawings land, get read and checked overnight, and a PM gets a grounded brief, a triaged queue, the evidence on the sheet and a governed way to ask questions, all deployed from one bundle.
>
> What I'd propose next is a four-week pilot on one closed project's drawings, with three measures agreed up front: precision and recall against your known NCRs, engineer hours per drawing before and after, and the false-alarm rate per rule. Week one, we index your code library and specs. Week two, we run the batch. Weeks three and four, your engineers work the queue and we tune the guardrails on their feedback. Can we pick the project and name the discipline lead today?"

Leave-behind: [`evidence/00_READ_ME_FIRST.md`](../evidence/00_READ_ME_FIRST.md). Every claim above links to its proof there.
