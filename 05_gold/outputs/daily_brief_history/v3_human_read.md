# Human read of the final v3 brief (job run 1067568868183925)

Done after the run, line by line, against `context_json` and against a live query of the gold tables (queried 2026-11-08: `risk_forecast` High = 26; `schedule_overdue` days_late > 0 = 6 and days_late = 0 is 1; ASME B31.3 section 322 = 30 and OSHA 1910.147 = 25 FAIL findings for 2026-10-31 to 2026-11-06; top 3 by `risk_rank` = MS-335, MS-351, MS-352). This is the check the automated validator cannot do (paraphrase and tone). The earlier versions are in this folder: `v1.md`, `v2.md`, `v3_run1.md`.

| Line of the brief | Grounded in | Verdict |
|---|---|---|
| "tracking a $4.8M overrun" | `kpi.budget_overrun_usd` = 4,800,000 | Supported |
| "schedule pressure from late milestones" | `schedule_already_late` = 6 | Supported (wording is a mild characterization, no new fact) |
| "though safety remains strong" | `kpi.safety_days_without_incident` = 28, `trir_28d` = 0.0 | Judgement word, directionally supported; not a number or a trend claim |
| Schedule: "6 milestones are already late and 1 due today" | `schedule_already_late` = 6, `schedule_due_today` = 1 (live: 6 and 1) | Correct; fixes the v2 "7 already late" error |
| "MS-271 ... 15 days, MS-277 ... 11 days, MS-281 ... 4 days" | `schedule_overdue_top3[].days_late` 15, 11, 4 | Correct, each with its own ID |
| Budget: "$4.8M overrun against the $208.7M total budget" | `kpi.budget_overrun_usd`, `kpi.budget_total_usd` = 208,700,000 | Correct |
| Safety: "28 days without an incident and a 28-day TRIR of 0.0" | `kpi.safety_days_without_incident` = 28, `kpi.trir_28d` = 0.0 | Correct |
| Compliance: "51 of 238 drawings flagged for engineer review this week" | `flagged_drawings` = 51, `reviewed_drawings` = 238 | Correct, triage wording |
| "ASME B31.3 section 322 leads with 30 findings, followed by OSHA 1910.147 with 25" | `fail_findings_by_citation[0..1]` (live 30 and 25) | Correct; counts by citation only, no generalization from sample reasons |
| "24 NCRs remain open" | `kpi.open_ncrs` = 24 | Correct, and in the Compliance bullet, not Risk |
| Risk: "26 milestones are High risk in the next 90 days" | `risk_high_total` = 26 (live 26), window 90 days | Correct; fixes the v2 "3 ... High risk" error |
| "the top 3 are MS-335, MS-351, and MS-352" | `risk_forecast_top3` (live top 3 by `risk_rank`) | Correct |
| Closing question | none needed | Fine |

Not found: invented numbers, IDs, causes, dates, trends or probabilities. Residual wording risk: "schedule pressure" and "safety remains strong" are the model's own framing, not facts from the context. No percentages are used for risk.
