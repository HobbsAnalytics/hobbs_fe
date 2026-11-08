#!/usr/bin/env python3
"""Single source of truth for the Blue Ridge Genie Space (Task 15).

Run locally (needs the CLI profile DEFAULT):  python3 -I 07_genie_agent/build_space.py

What it writes, next to this file:
  genie_space.geniespace.json  the serialized space (tables, descriptions, instructions, 10 example SQLs); the bundle resource
                               resources/genie-space.yml and 01_create_space.ipynb both read it
  sample_questions.md          the 10 curated Q->SQL pairs, each with the expected answer taken from RUNNING the verified SQL
  heldout_questions.md         the 5 held-out Q->SQL pairs (never loaded into the space), same treatment
  benchmark_expected.json      expected answers + the deterministic scoring rule per question (read by 02_run_sample_qa.ipynb)

Held-out questions live only in HELDOUT below and in the two held-out outputs; they are never written to the space JSON.
"""
import json, subprocess, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WH = "527214d7319cb124"
C = "mfg_mc_se_sa"
G = f"{C}.bluerridge_gold_pm"
S = f"{C}.bluerridge_silver_engineering"
A = f"{C}.bluerridge_agents"
WEEK = "review_date BETWEEN '2026-10-31' AND '2026-11-06'"

# --------------------------------------------------------------------------------------------------
# Curated questions: (question, sql, expected-answer template, scoring rule)
# rule: tokens = facts that must appear (numbers compared numerically, strings case-insensitively) in Genie's
#       result rows + answer text; pct = tokens given as percent that may also appear as a 0-1 fraction;
#       forbid_in_rows = values that must NOT appear in result rows; sql_contains = text the generated SQL must contain.
# --------------------------------------------------------------------------------------------------
CURATED = [
 dict(q="How many drawings failed compliance review this week, out of how many reviewed?",
  sql=f"""SELECT COUNT(DISTINCT drawing_id) AS drawings_reviewed,
       COUNT(DISTINCT CASE WHEN status = 'FAIL' THEN drawing_id END) AS drawings_failed,
       COUNT(DISTINCT CASE WHEN status = 'PASS' THEN drawing_id END) AS drawings_passed
FROM {G}.compliance_findings
WHERE {WEEK}""",
  exp="{drawings_failed} of {drawings_reviewed} drawings failed this week ({drawings_passed} passed).",
  rule=dict(desc="numeric equality on 51 (failed) and 238 (reviewed)", tokens=[51, 238])),
 dict(q="Show failed compliance findings this week by code citation.",
  sql=f"""SELECT citation, COUNT(*) AS failed_findings, COUNT(DISTINCT drawing_id) AS drawings
FROM {G}.compliance_findings
WHERE status = 'FAIL' AND {WEEK}
GROUP BY citation
ORDER BY failed_findings DESC""",
  exp="Failed findings by citation: " + "; ".join(["{r%d_citation}: {r%d_failed_findings}" % (i, i) for i in range(5)]) + ".",
  rule=dict(desc="the five citations and their finding counts (30, 25, 15, 8, 7) all appear", tokens=["ASME B31.3 §322", 30, "OSHA 1910.147", 25, "ASME B16.5 §4.2", 15, "IBC 1005.1", 8, "ASME B31.3 §341", 7])),
 dict(q="Which piping isometric drawings failed compliance this week?",
  sql=f"""SELECT DISTINCT drawing_id
FROM {G}.compliance_findings
WHERE status = 'FAIL' AND discipline = 'piping' AND drawing_type = 'ISO' AND {WEEK}
ORDER BY drawing_id""",
  exp="{n_rows} piping ISO drawings failed this week: {ids}.",
  rule=dict(desc="ID-set equality: all failing piping ISO drawing ids appear", tokens="__IDS__")),
 dict(q="Which milestones are already late, and by how many days?",
  sql=f"""SELECT milestone_id, name, discipline, planned_end, days_late
FROM {G}.schedule_overdue
WHERE days_late > 0
ORDER BY days_late DESC""",
  exp="{n_rows} milestones are late: " + "; ".join(["{r%d_milestone_id} %s{r%d_days_late} days" % (i, "", i) for i in range(6)]) + ". MS-274 is due today (0 days late) and is not late.",
  rule=dict(desc="ID+days equality for the 6 late milestones; MS-274 (due today) must not be in the result rows", tokens=["MS-271", 15, "MS-277", 11, "MS-278", 5, "MS-281", 4, "MS-279", "MS-287", 2], forbid_in_rows=["MS-274"])),
 dict(q="What are the top 3 highest-risk milestones in the next 90 days?",
  sql=f"""SELECT milestone_id, name, discipline, planned_end, risk_band, risk_rank
FROM {G}.risk_forecast
WHERE risk_band = 'High'
ORDER BY risk_rank
LIMIT 3""",
  exp="Top 3 by risk rank (all High): {r0_milestone_id}, {r1_milestone_id}, {r2_milestone_id}.",
  rule=dict(desc="ID-set equality on MS-335, MS-351, MS-352; MS-331 (rank 4) must not be in the rows", tokens=["MS-335", "MS-351", "MS-352"], forbid_in_rows=["MS-331"])),
 dict(q="Explain the budget variance: how far over budget are we?",
  sql=f"""SELECT budget_total_usd, budget_overrun_usd, budget_eac_pct
FROM {G}.kpi_daily
WHERE is_current""",
  exp="The estimate at completion is {budget_eac_pct}% over, ${budget_overrun_usd:,.0f} over the ${budget_total_usd:,.0f} budget.",
  rule=dict(desc="numeric equality on 2.3 (% EAC), 4.8M overrun, 208.7M budget (M/million suffixes parsed)", tokens=[2.3, 4800000, 208700000])),
 dict(q="How many open NCRs do we have, by category?",
  sql=f"""SELECT category, COUNT(*) AS open_ncrs
FROM {S}.ncrs
WHERE status = 'open'
GROUP BY category
ORDER BY open_ncrs DESC""",
  exp="Open NCRs by category: {r0_category} {r0_open_ncrs}, {r1_category} {r1_open_ncrs} (24 in total).",
  rule=dict(desc="workmanship=15 and compliance=9", tokens=["workmanship", 15, "compliance", 9])),
 dict(q="What is our safety record: TRIR and days without an incident?",
  sql=f"""SELECT trir_28d, safety_days_without_incident, recordables_28d
FROM {G}.kpi_daily
WHERE is_current""",
  exp="TRIR (28-day) is {trir_28d}, with {recordables_28d} recordables and {safety_days_without_incident} days without an incident.",
  rule=dict(desc="numeric equality on 28 days incident-free and TRIR 0", tokens=[28, 0])),
 dict(q="What does OSHA 1910.147 require?",
  sql=f"""SELECT citation_label, title, text
FROM {A}.code_excerpts
WHERE citation_label = 'OSHA 1910.147'""",
  exp="Clause titled '{title}': the paraphrased text says equipment must be isolated from hazardous energy and locked/tagged out before servicing (lockout/tagout).",
  rule=dict(desc="answer contains the clause title 'Control of hazardous energy' and 'lockout', and the SQL reads code_excerpts", tokens=["Control of hazardous energy", "lockout"], sql_contains="code_excerpts")),
 dict(q="How accurate is the AI compliance judge?",
  sql=f"""SELECT prompt_version, eval_column, ROUND(`precision` * 100, 1) AS precision_pct, ROUND(recall * 100, 1) AS recall_pct
FROM {G}.compliance_eval
WHERE prompt_version = 'v3_final' AND eval_column = 'C' AND citation = 'ALL'""",
  exp="The v3 judge (column C, all citations) has precision {precision_pct}% and recall {recall_pct}%.",
  rule=dict(desc="precision 58.1% and recall 81.0% (a 0-1 fraction is accepted as the same value)", tokens=[58.1, 81.0], pct=True)),
]

HELDOUT = [
 dict(q="Which discipline has the most failed drawings this week?",
  sql=f"""SELECT discipline, COUNT(DISTINCT drawing_id) AS failed_drawings
FROM {G}.compliance_findings
WHERE status = 'FAIL' AND {WEEK}
GROUP BY discipline
ORDER BY failed_drawings DESC
LIMIT 1""",
  exp="{r0_discipline} has the most failed drawings this week ({r0_failed_drawings}).",
  rule=dict(desc="discipline = piping with 27 failed drawings", tokens=["piping", 27])),
 dict(q="Is the cryogenic tank milestone on schedule?",
  sql=f"""SELECT milestone_id, name, planned_end, days_late
FROM {G}.schedule_overdue
WHERE name LIKE '%Cryogenic%'""",
  exp="No. {r0_milestone_id} ({r0_name}) was due {r0_planned_end} and is {r0_days_late} days late.",
  rule=dict(desc="MS-281 identified, 4 days late, and the word 'late'", tokens=["MS-281", 4, "late"])),
 dict(q="How many change orders are there and what is their total value?",
  sql=f"""SELECT COUNT(*) AS change_orders, SUM(amount_usd) AS total_amount_usd
FROM {S}.change_orders""",
  exp="{change_orders} change orders totalling ${total_amount_usd:,.0f} (approved $3,475,000, pending $1,448,000, rejected $359,000).",
  rule=dict(desc="numeric equality on 20 change orders and $5,282,000 across all statuses (an approved-only total is a miss)", tokens=[20, 5282000])),
 dict(q="Which code citation does the AI judge miss most often?",
  sql=f"""SELECT citation, ROUND(recall * 100, 1) AS recall_pct, fn AS missed_flaws
FROM {G}.compliance_eval
WHERE prompt_version = 'v3_final' AND eval_column = 'C' AND citation <> 'ALL'
ORDER BY recall ASC
LIMIT 1""",
  exp="{r0_citation}: lowest recall ({r0_recall_pct}%), {r0_missed_flaws} missed flaws.",
  rule=dict(desc="citation OSHA 1910.147 with recall 54.2% (fraction accepted)", tokens=["OSHA 1910.147", 54.2], pct=True)),
 dict(q="How many P&IDs are in the drawing register?",
  sql=f"""SELECT COUNT(*) AS pid_drawings
FROM {G}.drawing_register
WHERE drawing_type = 'PID'""",
  exp="{pid_drawings} P&ID drawings are in the register.",
  rule=dict(desc="numeric equality on 373", tokens=[373])),
]

# --------------------------------------------------------------------------------------------------
INSTRUCTIONS = """You answer questions for the Project Manager of the Blue Ridge LNG Terminal, Phase 2 (a Bechtel-style LNG build). ALL DATA IS SYNTHETIC; the code citation labels (for example 'ASME B31.3 §322', 'OSHA 1910.147') are illustrative project labels and the clause text is a paraphrase, not the standard.
DATES: 'Today' is 2026-11-06 (the as-of date); do not use the system date. 'This week' for compliance means review_date BETWEEN '2026-10-31' AND '2026-11-06' on compliance_findings.
COMPLIANCE: compliance_findings has one row per finding; a clean drawing has one PASS row. When asked 'how many drawings failed', COUNT(DISTINCT drawing_id) with status = 'FAIL' (a drawing fails if it has at least one FAIL row); 'findings' means rows. 'Reviewed' is the distinct drawings with a row in the window. Treat compliance answers as a TRIAGE LIST for engineer review, not a final determination; the AI judge has known false positives.
CODE CLAUSES: to explain a clause or citation, look it up in bluerridge_agents.code_excerpts with citation_label = the exact citation (for example WHERE citation_label = 'OSHA 1910.147'); summarize its title and text.
JUDGE ACCURACY: compliance_eval holds precision and recall per citation and prompt version. The headline judge result is prompt_version = 'v3_final', eval_column = 'C' (after guardrails), citation = 'ALL'. Quote precision and recall as percentages.
SCHEDULE: 'late' or 'overdue' means schedule_overdue.days_late > 0; days_late = 0 means 'due today', not late. Use schedule_overdue for what is late now. silver_engineering.schedule is the full milestone plan (planned and actual dates, dependencies).
RISK: risk_forecast covers open milestones in the next 90 days. Present risk as risk_band (High / Medium / Low) and order by risk_rank (1 = highest). NEVER state slip_probability as a percentage or a chance of slipping; it is an uncalibrated heuristic ranking score. Do not select it unless asked how the ranking is built, and then say it is only a ranking score.
COST: the project budget variance is in kpi_daily (budget_eac_pct = estimate at completion over budget, in percent; budget_overrun_usd; budget_total_usd). kpi_daily has one row per snapshot_date; use is_current (true) for the latest.
SAFETY AND NCRs: kpi_daily has trir_28d, recordables_28d, safety_days_without_incident and the open NCR counts. For NCR detail use silver_engineering.ncrs; 'open' means status = 'open'.
JOINS: join on drawing_id (compliance_findings, drawing_register) and milestone_id (schedule, schedule_overdue, risk_forecast, ncrs).
If the data cannot answer a question, say so instead of guessing."""

JARGON = {  # column synonyms keyed by (table, column)
 ("drawing_register", "drawing_type"): (["Drawing type: ISO = isometric (piping isometric), PID = P&ID = piping and instrumentation diagram, GA = general arrangement, SPEC = specification, OTHER."], ["ISO", "isometric", "P&ID", "PID", "piping and instrumentation diagram", "GA", "general arrangement", "drawing kind"]),
 ("compliance_findings", "drawing_type"): (["Drawing type: ISO = isometric, PID = P&ID = piping and instrumentation diagram, GA = general arrangement, SPEC = specification, OTHER."], ["ISO", "isometric", "P&ID", "PID", "piping and instrumentation diagram", "GA", "general arrangement"]),
 ("compliance_findings", "status"): (["Finding result: PASS (clean drawing sentinel row), FAIL (a possible code violation for engineer review), REVIEW (judge answer unusable)."], ["result", "outcome", "pass fail"]),
 ("compliance_findings", "citation"): (["Illustrative project code label of the clause checked; join to code_excerpts.citation_label. 'OSHA 1910.147' = lockout/tagout (LOTO)."], ["code", "clause", "standard", "code reference", "LOTO", "lockout tagout"]),
 ("compliance_findings", "review_date"): (["Date the drawing was reviewed. 'This week' = 2026-10-31 to 2026-11-06."], ["reviewed on", "check date"]),
 ("compliance_findings", "drawing_id"): (["Drawing identifier, e.g. BRL-PIP-ISO-0206 (project, discipline, type, number)."], ["drawing", "drawing number", "dwg"]),
 ("compliance_findings", "discipline"): (["Engineering discipline: piping, instr (instrumentation), mechanical, electrical, structural."], ["trade", "engineering discipline"]),
 ("compliance_findings", "severity"): (["Severity of a FAIL finding: critical, high, medium."], ["seriousness"]),
 ("compliance_eval", "citation"): (["Citation scored; the value 'ALL' is the overall row across every citation, not a clause."], ["code", "clause"]),
 ("compliance_eval", "prompt_version"): (["Version of the AI judge prompt: v1_baseline, v2_prompt_hints, v3_final. v3_final is the shipped judge."], ["judge version", "prompt"]),
 ("compliance_eval", "eval_column"): (["Scoring view: A = all raw judge entries, B = after the judge's self-check, C = after guardrails (the headline view)."], ["scoring column", "view"]),
 ("compliance_eval", "precision"): (["Fraction (0-1) of flagged FAILs that match planted flaws. Multiply by 100 for a percent."], ["accuracy", "judge accuracy"]),
 ("compliance_eval", "recall"): (["Fraction (0-1) of planted flaws the judge caught. Multiply by 100 for a percent."], ["hit rate", "catch rate", "sensitivity"]),
 ("risk_forecast", "risk_band"): (["Risk band for slipping: High, Medium or Low. Use this, not slip_probability."], ["risk level", "risk rating", "schedule risk"]),
 ("risk_forecast", "risk_rank"): (["Rank by risk, 1 = highest."], ["risk order", "priority"]),
 ("risk_forecast", "slip_probability"): (["Heuristic ranking score only. NOT a calibrated probability: never present it as a percentage or chance."], ["ranking score"]),
 ("schedule_overdue", "days_late"): (["Days past planned_end for an open milestone. > 0 = late; 0 = due today."], ["days overdue", "slipped days", "days behind"]),
 ("kpi_daily", "budget_eac_pct"): (["EAC = estimate at completion. Percent over (+) or under (-) the total budget."], ["EAC variance", "budget variance", "over budget"]),
 ("kpi_daily", "trir_28d"): (["TRIR = total recordable incident rate over the last 28 days."], ["TRIR", "total recordable incident rate", "safety rate"]),
 ("kpi_daily", "safety_days_without_incident"): (["Days since the last recordable incident."], ["days incident-free", "days without incident", "days since last incident"]),
 ("kpi_daily", "is_current"): (["True on the latest snapshot (2026-11-06)."], ["latest", "current"]),
 ("ncrs", "category"): (["NCR = nonconformance report. Category: compliance, workmanship, materials, documentation."], ["NCR type", "nonconformance category"]),
 ("ncrs", "status"): (["open or closed."], []),
 ("code_excerpts", "citation_label"): (["Exact citation label; matches compliance_findings.citation. Synthetic paraphrase of the requirement, not the standard text."], ["citation", "clause", "code reference"]),
 ("code_excerpts", "text"): (["Paraphrased requirement text for the clause. Mentions LOTO = lockout/tagout, PSV = pressure safety (relief) valve where relevant."], ["requirement", "what the code requires"]),
 ("change_orders", "amount_usd"): (["Change order value in US dollars."], ["CO value", "change order amount"]),
 ("schedule", "slip_days"): (["Days the milestone finished late (completed milestones)."], []),
}
TABLES = {  # identifier -> description
 f"{G}.compliance_findings": "AI compliance review of drawings: one row per finding, plus a PASS row for each clean drawing. Triage list for engineers, not a final determination.",
 f"{G}.kpi_daily": "Daily project KPI snapshot (budget, safety, NCR counts, compliance week counts). is_current marks the latest (2026-11-06).",
 f"{G}.risk_forecast": "Open milestones due in the next 90 days with a risk_band (High/Medium/Low) and risk_rank. slip_probability is a ranking score, not a chance.",
 f"{G}.schedule_overdue": "Open milestones past planned_end (days_late > 0) or due today (days_late = 0), with downstream impact counts.",
 f"{G}.drawing_register": "Register of all 1,200 drawings with discipline, type and latest review status. ISO = isometric, PID = P&ID, GA = general arrangement.",
 f"{G}.compliance_eval": "Precision/recall of the AI compliance judge per citation, prompt version and scoring column. Headline: v3_final, column C, citation ALL.",
 f"{G}.daily_brief": "The generated daily project brief (one row per day, markdown in brief_md).",
 f"{S}.schedule": "Full milestone schedule: planned and actual dates, discipline, dependencies, criticality.",
 f"{S}.ncrs": "NCR = nonconformance reports: category, severity, status (open/closed), area, dates, linked milestone.",
 f"{S}.change_orders": "Change orders with status (approved/pending/rejected), amount in USD and schedule impact.",
 f"{A}.code_excerpts": "One row per code clause (52), paraphrased requirement text, keyed by citation_label (synthetic).",
}

def hexid(prefix, n):
    return prefix + format(n, "031x")

def run_sql(sql):
    r = subprocess.run(["databricks", "experimental", "aitools", "tools", "query", "--warehouse", WH, "--profile", "DEFAULT", sql], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("SQL failed:\n" + sql + "\n" + r.stderr)
    return json.loads(r.stdout)

def build_space():
    tables = []
    for ident in sorted(TABLES):
        t = ident.split(".")[-1]
        cols = [dict(column_name=c, description=d, synonyms=s) for (tt, c), (d, s) in sorted(JARGON.items()) if tt == t]
        cols = [{k: v for k, v in c.items() if v} for c in cols]
        entry = dict(identifier=ident, description=[TABLES[ident]])
        if cols:
            entry["column_configs"] = sorted(cols, key=lambda c: c["column_name"])
        tables.append(entry)
    ex = []
    for i, c in enumerate(CURATED, 1):
        ex.append(dict(id=hexid("2", i), question=[c["q"]], sql=[line + "\n" for line in c["sql"].split("\n")[:-1]] + [c["sql"].split("\n")[-1]]))
    return {
        "version": 2,
        "config": {"sample_questions": [dict(id=hexid("1", i), question=[c["q"]]) for i, c in enumerate(CURATED, 1)]},
        "data_sources": {"tables": tables},
        "instructions": {
            "example_question_sqls": sorted(ex, key=lambda e: e["id"]),
            "text_instructions": [dict(id=hexid("3", 1), content=[l + "\n" for l in INSTRUCTIONS.split("\n")[:-1]] + [INSTRUCTIONS.split("\n")[-1]])],
        },
    }

def fmt_rows(rows):
    if not rows:
        return "(no rows)"
    cols = list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:160] for c in cols) + " |")
    return "\n".join(out)

def expected_text(item, rows):
    ctx = {}
    if rows:
        for k, v in rows[0].items():
            try:
                ctx[k] = float(v) if k.endswith(("usd", "_pct")) and False else v
            except Exception:
                ctx[k] = v
        for i, r in enumerate(rows):
            for k, v in r.items():
                ctx[f"r{i}_{k}"] = v
    ctx["n_rows"] = len(rows)
    ctx["ids"] = ", ".join(r.get("drawing_id", "") for r in rows)
    # numeric formatting helpers
    class F(dict):
        def __missing__(self, k): return "?"
    t = item["exp"]
    for k in ("budget_overrun_usd", "budget_total_usd", "total_amount_usd"):
        if k in ctx:
            ctx[k] = float(ctx[k])
    return t.format_map(F(ctx))

def main():
    space = build_space()
    json.dump(space, open(os.path.join(HERE, "genie_space.geniespace.json"), "w"), indent=2, ensure_ascii=False)
    bench = {"as_of_date": "2026-11-06", "curated": [], "heldout": []}
    docs = {}
    for kind, items in (("curated", CURATED), ("heldout", HELDOUT)):
        md = []
        for i, it in enumerate(items, 1):
            rows = run_sql(it["sql"])
            rule = dict(it["rule"])
            if rule["tokens"] == "__IDS__":
                rule["tokens"] = [r["drawing_id"] for r in rows]
            exp = expected_text(it, rows)
            bench[kind].append(dict(n=i, question=it["q"], sql=it["sql"], expected_rows=rows, expected_answer=exp, rule=rule))
            md.append(f"## {i}. {it['q']}\n\n**Verified SQL**\n\n```sql\n{it['sql']}\n```\n\n**Result of running it (as of 2026-11-06)**\n\n{fmt_rows(rows)}\n\n**Expected answer:** {exp}\n\n**Scoring rule:** {rule['desc']}.\n")
        docs[kind] = "\n".join(md)
    head_c = ("# Curated Genie questions (loaded into the space as example SQL)\n\n"
      "Ten question-to-SQL pairs for the Genie Space `Blue Ridge LNG — PM Co-Pilot (synthetic)`. Each SQL was run on warehouse `hobbs` "
      "(`527214d7319cb124`); the result table and the expected answer below come from that run, as of `2026-11-06`. The same ten pairs are loaded "
      "into the space as example SQL (`genie_space.geniespace.json`, generated by `build_space.py`). `02_run_sample_qa.ipynb` asks each question as a "
      "fresh Genie conversation and scores the answer against the result with the stated rule. All data is synthetic.\n\n")
    head_h = ("# Held-out Genie questions (NOT loaded into the space)\n\n"
      "Five questions phrased differently from the curated ten and covering other angles. They are **never** added to the space (not as examples, "
      "sample questions or instructions) and the space was not tuned toward them: they measure how well the space generalizes. The SQL is the verified "
      "answer key only. Results below come from running it on 2026-11-06 data. All data is synthetic.\n\n")
    open(os.path.join(HERE, "sample_questions.md"), "w").write(head_c + docs["curated"])
    open(os.path.join(HERE, "heldout_questions.md"), "w").write(head_h + docs["heldout"])
    json.dump(bench, open(os.path.join(HERE, "benchmark_expected.json"), "w"), indent=2, ensure_ascii=False, default=str)
    print("wrote space json, sample_questions.md, heldout_questions.md, benchmark_expected.json")

if __name__ == "__main__":
    main()
