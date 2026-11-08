# Genie Space Q&A transcript

Space **Blue Ridge LNG — PM Co-Pilot (synthetic)** (`01f1db9edffa1a298195db2806ce45e3`), asked through the Genie Conversation API from a one-time serverless job run (run id `770421906253489`) as the submitting user, 2026-11-08 18:13 UTC. Data is synthetic and anchored to as-of date 2026-11-06.

## Summary

* **Curated: 10/10 correct** (0 partial, 0 wrong). Pass bar: 8/10.
* **Held-out: 5/5 correct** (0 partial, 0 wrong). Pass bar: 3/5. These five questions are not in the space.
* Result: **PASS**.
* Answers that present slip_probability as a percentage or chance: **0**.
* Genie is not deterministic: another run can produce different SQL or wording, so a score is one sample, not a guarantee. Each question is a fresh conversation and none is retried.
* Scoring is deterministic (key facts from the verified SQL found in Genie's answer or result rows; the rule is shown per question). Verified SQL and expected answers: `07_genie_agent/sample_questions.md` and `heldout_questions.md`.

| # | Set | Question | Verdict | Facts found |
|---|---|---|---|---|
| 1 | curated | How many drawings failed compliance review this week, out of how many reviewed? | correct | 2/2 |
| 2 | curated | Show failed compliance findings this week by code citation. | correct | 10/10 |
| 3 | curated | Which piping isometric drawings failed compliance this week? | correct | 5/5 |
| 4 | curated | Which milestones are already late, and by how many days? | correct | 11/11 |
| 5 | curated | What are the top 3 highest-risk milestones in the next 90 days? | correct | 3/3 |
| 6 | curated | Explain the budget variance: how far over budget are we? | correct | 3/3 |
| 7 | curated | How many open NCRs do we have, by category? | correct | 4/4 |
| 8 | curated | What is our safety record: TRIR and days without an incident? | correct | 2/2 |
| 9 | curated | What does OSHA 1910.147 require? | correct | 2/2 |
| 10 | curated | How accurate is the AI compliance judge? | correct | 2/2 |
| 1 | heldout | Which discipline has the most failed drawings this week? | correct | 2/2 |
| 2 | heldout | Is the cryogenic tank milestone on schedule? | correct | 3/3 |
| 3 | heldout | How many change orders are there and what is their total value? | correct | 2/2 |
| 4 | heldout | Which code citation does the AI judge miss most often? | correct | 2/2 |
| 5 | heldout | How many P&IDs are in the drawing register? | correct | 1/1 |

## Curated questions (loaded into the space as example SQL)

### curated 1. How many drawings failed compliance review this week, out of how many reviewed?

**Genie answer** (13.0s, status COMPLETED)

> You want to know how many unique drawings were reviewed for compliance this week, how many of those drawings failed the compliance review, and how many passed the compliance review during the same period.
> 
> This week, **51** drawings failed compliance review out of **238** drawings reviewed. The same result set shows **187** drawings passed review this week.

**Generated SQL**

```sql
SELECT COUNT(DISTINCT `drawing_id`) AS `drawings_reviewed`, COUNT(DISTINCT CASE WHEN `status` = 'FAIL' THEN `drawing_id` END) AS `drawings_failed`, COUNT(DISTINCT CASE WHEN `status` = 'PASS' THEN `drawing_id` END) AS `drawings_passed` FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_findings` WHERE `review_date` BETWEEN DATE '2026-10-31' AND DATE '2026-11-06'
```

**Result rows**

| drawings_reviewed | drawings_failed | drawings_passed |
|---|---|---|
| 238 | 51 | 187 |

**Expected answer:** 51 of 238 drawings failed this week (187 passed).

**Expected result (verified SQL)**

| drawings_failed | drawings_passed | drawings_reviewed |
|---|---|---|
| 51 | 187 | 238 |

**Verdict: CORRECT.** Rule: numeric equality on 51 (failed) and 238 (reviewed). Facts found: [51, 238]; missing: [].

### curated 2. Show failed compliance findings this week by code citation.

**Genie answer** (13.1s, status COMPLETED)

> You want to see the number of failed compliance findings and the number of unique drawings that failed, grouped by each code citation, for the week from October 31, 2026, to November 6, 2026.
> 
> This week, the failed compliance findings are led by **ASME B31.3 §322** with **30 findings across 19 drawings**, followed by **OSHA 1910.147** with **25 findings across 13 drawings**, **ASME B16.5 §4.2** with **15 findings across 10 drawings**, **IBC 1005.1** with **8 findings across 8 drawings**, and **ASME B31.3 §341** with **7 findings across 5 drawings**.
> 
> Across these **5 citations**, **ASME B31.3 §322** is the largest review priority this week because it has the highest failed finding count and the broadest drawing impact.

**Generated SQL**

```sql
SELECT `citation`, COUNT(*) AS `failed_findings`, COUNT(DISTINCT `drawing_id`) AS `drawings`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_findings`
WHERE `status` = 'FAIL'
  AND `review_date` BETWEEN '2026-10-31' AND '2026-11-06'
  AND `citation` IS NOT NULL
GROUP BY `citation`
ORDER BY `failed_findings` DESC
```

**Result rows**

| citation | failed_findings | drawings |
|---|---|---|
| ASME B31.3 §322 | 30 | 19 |
| OSHA 1910.147 | 25 | 13 |
| ASME B16.5 §4.2 | 15 | 10 |
| IBC 1005.1 | 8 | 8 |
| ASME B31.3 §341 | 7 | 5 |

**Expected answer:** Failed findings by citation: ASME B31.3 §322: 30; OSHA 1910.147: 25; ASME B16.5 §4.2: 15; IBC 1005.1: 8; ASME B31.3 §341: 7.

**Expected result (verified SQL)**

| citation | drawings | failed_findings |
|---|---|---|
| ASME B31.3 §322 | 19 | 30 |
| OSHA 1910.147 | 13 | 25 |
| ASME B16.5 §4.2 | 10 | 15 |
| IBC 1005.1 | 8 | 8 |
| ASME B31.3 §341 | 5 | 7 |

**Verdict: CORRECT.** Rule: the five citations and their finding counts (30, 25, 15, 8, 7) all appear. Facts found: ['ASME B31.3 §322', 30, 'OSHA 1910.147', 25, 'ASME B16.5 §4.2', 15, 'IBC 1005.1', 8, 'ASME B31.3 §341', 7]; missing: [].

### curated 3. Which piping isometric drawings failed compliance this week?

**Genie answer** (10.1s, status COMPLETED)

> You want to see the unique piping isometric drawings that failed compliance during the week from October 31, 2026, to November 6, 2026.
> 
> **5** piping isometric drawings failed compliance this week (review dates between **2026-10-31** and **2026-11-06**). 
> - **BRL-PIP-ISO-0066**
> - **BRL-PIP-ISO-0394**
> - **BRL-PIP-ISO-0438**
> - **BRL-PIP-ISO-0664**
> - **BRL-PIP-ISO-1197**
> These results show a **5-drawing triage list** for engineer review for this week’s piping isometric compliance failures.

**Generated SQL**

```sql
SELECT DISTINCT `drawing_id`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_findings`
WHERE `status` = 'FAIL'
  AND `discipline` IS NOT NULL
  AND `drawing_type` IS NOT NULL
  AND `drawing_id` IS NOT NULL
  AND `discipline` ILIKE '%piping%'
  AND `drawing_type` ILIKE '%ISO%'
  AND `review_date` BETWEEN '2026-10-31' AND '2026-11-06'
ORDER BY `drawing_id`
```

**Result rows**

| drawing_id |
|---|
| BRL-PIP-ISO-0066 |
| BRL-PIP-ISO-0394 |
| BRL-PIP-ISO-0438 |
| BRL-PIP-ISO-0664 |
| BRL-PIP-ISO-1197 |

**Expected answer:** 5 piping ISO drawings failed this week: BRL-PIP-ISO-0066, BRL-PIP-ISO-0394, BRL-PIP-ISO-0438, BRL-PIP-ISO-0664, BRL-PIP-ISO-1197.

**Expected result (verified SQL)**

| drawing_id |
|---|
| BRL-PIP-ISO-0066 |
| BRL-PIP-ISO-0394 |
| BRL-PIP-ISO-0438 |
| BRL-PIP-ISO-0664 |
| BRL-PIP-ISO-1197 |

**Verdict: CORRECT.** Rule: ID-set equality: all failing piping ISO drawing ids appear. Facts found: ['BRL-PIP-ISO-0066', 'BRL-PIP-ISO-0394', 'BRL-PIP-ISO-0438', 'BRL-PIP-ISO-0664', 'BRL-PIP-ISO-1197']; missing: [].

### curated 4. Which milestones are already late, and by how many days?

**Genie answer** (13.0s, status COMPLETED)

> You want to see a list of milestones that are currently late, including how many days each milestone is overdue, along with their names, disciplines, and planned end dates.
> 
> There are **6 milestones** already late, ranging from **2 to 15 days** overdue. Some of the most overdue milestones are:
> - **Install heat exchanger - Main Substation (WP-281)** — **15 days** late
> - **Align rotating equipment - Train 3 (WP-286)** — **11 days** late
> - **Hydrotest line - Pipe Rack South (WP-282)** — **5 days** late
> - **Weld and inspect - Utilities Block (WP-264)** — **4 days** late
> - **Cryogenic Tank T-203 Install Complete** — **4 days** late
> 
> The late items are concentrated in **mechanical** and **piping**, with mechanical accounting for **3 of the 6** overdue milestones.

**Generated SQL**

```sql
SELECT `milestone_id`, `name`, `discipline`, `planned_end`, `days_late`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`schedule_overdue`
WHERE `days_late` > 0
  AND `days_late` IS NOT NULL
ORDER BY `days_late` DESC
```

**Result rows**

| milestone_id | name | discipline | planned_end | days_late |
|---|---|---|---|---|
| MS-271 | Install heat exchanger - Main Substation (WP-281) | mechanical | 2026-10-22 | 15 |
| MS-277 | Align rotating equipment - Train 3 (WP-286) | mechanical | 2026-10-26 | 11 |
| MS-278 | Hydrotest line - Pipe Rack South (WP-282) | piping | 2026-11-01 | 5 |
| MS-279 | Weld and inspect - Utilities Block (WP-264) | piping | 2026-11-02 | 4 |
| MS-281 | Cryogenic Tank T-203 Install Complete | mechanical | 2026-11-02 | 4 |

(6 rows returned; first 5 shown, scoring used all 6)

**Expected answer:** 6 milestones are late: MS-271 15 days; MS-277 11 days; MS-278 5 days; MS-281 4 days; MS-279 4 days; MS-287 2 days. MS-274 is due today (0 days late) and is not late.

**Expected result (verified SQL)**

| days_late | discipline | milestone_id | name | planned_end |
|---|---|---|---|---|
| 15 | mechanical | MS-271 | Install heat exchanger - Main Substation (WP-281) | 2026-10-22 |
| 11 | mechanical | MS-277 | Align rotating equipment - Train 3 (WP-286) | 2026-10-26 |
| 5 | piping | MS-278 | Hydrotest line - Pipe Rack South (WP-282) | 2026-11-01 |
| 4 | mechanical | MS-281 | Cryogenic Tank T-203 Install Complete | 2026-11-02 |
| 4 | piping | MS-279 | Weld and inspect - Utilities Block (WP-264) | 2026-11-02 |

**Verdict: CORRECT.** Rule: ID+days equality for the 6 late milestones; MS-274 (due today) must not be in the result rows. Facts found: ['MS-271', 15, 'MS-277', 11, 'MS-278', 5, 'MS-281', 4, 'MS-279', 'MS-287', 2]; missing: [].

### curated 5. What are the top 3 highest-risk milestones in the next 90 days?

**Genie answer** (16.1s, status COMPLETED)

> You want to see the top 3 milestones that have the highest risk level within the next 90 days, specifically those classified as 'High' risk, ordered by their risk priority.
> 
> The top 3 highest-risk milestones shown in the next 90 days are all **High** risk and all in **instrumentation**. 
> 
> - **#1:** **Loop check - Train 4 (WP-315)** — Milestone **MS-335**, planned end **2027-01-25**
> - **#2:** **Loop check - Tank T-203 (WP-364)** — Milestone **MS-351**, planned end **2027-01-21**
> - **#3:** **Calibrate transmitters - Jetty 2 (WP-333)** — Milestone **MS-352**, planned end **2027-01-24**
> 
> Across these 3 results, the highest-risk work is concentrated in **instrumentation**, with planned end dates clustered between **2027-01-21** and **2027-01-25**.

**Generated SQL**

```sql
SELECT `milestone_id`, `name`, `discipline`, `planned_end`, `risk_band`, `risk_rank`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`risk_forecast`
WHERE `risk_band` = 'High'
ORDER BY `risk_rank`
LIMIT 3
```

**Result rows**

| milestone_id | name | discipline | planned_end | risk_band | risk_rank |
|---|---|---|---|---|---|
| MS-335 | Loop check - Train 4 (WP-315) | instr | 2027-01-25 | High | 1 |
| MS-351 | Loop check - Tank T-203 (WP-364) | instr | 2027-01-21 | High | 2 |
| MS-352 | Calibrate transmitters - Jetty 2 (WP-333) | instr | 2027-01-24 | High | 3 |

**Expected answer:** Top 3 by risk rank (all High): MS-335, MS-351, MS-352.

**Expected result (verified SQL)**

| discipline | milestone_id | name | planned_end | risk_band | risk_rank |
|---|---|---|---|---|---|
| instr | MS-335 | Loop check - Train 4 (WP-315) | 2027-01-25 | High | 1 |
| instr | MS-351 | Loop check - Tank T-203 (WP-364) | 2027-01-21 | High | 2 |
| instr | MS-352 | Calibrate transmitters - Jetty 2 (WP-333) | 2027-01-24 | High | 3 |

**Verdict: CORRECT.** Rule: ID-set equality on MS-335, MS-351, MS-352; MS-331 (rank 4) must not be in the rows. Facts found: ['MS-335', 'MS-351', 'MS-352']; missing: [].

### curated 6. Explain the budget variance: how far over budget are we?

**Genie answer** (10.2s, status COMPLETED)

> You want to see the current status of the project budget, including the total budget amount, how much the project is over or under budget in dollars, and the percentage variance of the estimate at completion compared to the budget.
> 
> The current budget is **$208,700,000**, and the estimate at completion is **$4,800,000 over budget**, which is **2.3%** above budget. Based on the current snapshot, the project is running **over budget**, not on budget.

**Generated SQL**

```sql
SELECT `budget_total_usd`, `budget_overrun_usd`, `budget_eac_pct`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`kpi_daily`
WHERE `is_current` = true
```

**Result rows**

| budget_total_usd | budget_overrun_usd | budget_eac_pct |
|---|---|---|
| 2.087E8 | 4800000.0 | 2.3 |

**Expected answer:** The estimate at completion is 2.3% over, $4,800,000 over the $208,700,000 budget.

**Expected result (verified SQL)**

| budget_eac_pct | budget_overrun_usd | budget_total_usd |
|---|---|---|
| 2.3 | 4800000.0 | 2.087E8 |

**Verdict: CORRECT.** Rule: numeric equality on 2.3 (% EAC), 4.8M overrun, 208.7M budget (M/million suffixes parsed). Facts found: [2.3, 4800000, 208700000]; missing: [].

### curated 7. How many open NCRs do we have, by category?

**Genie answer** (10.2s, status COMPLETED)

> You want to see the number of open nonconformance reports (NCRs) broken down by their category.
> 
> There are **24 open NCRs** in the results shown, split across **2 categories**: **workmanship (15)** and **compliance (9)**. **Workmanship** is the larger category, with **6 more** open NCRs than compliance.

**Generated SQL**

```sql
SELECT `category`, COUNT(*) AS `open_ncrs`
FROM `mfg_mc_se_sa`.`bluerridge_silver_engineering`.`ncrs`
WHERE `status` ILIKE '%open%'
  AND `category` IS NOT NULL
GROUP BY `category`
ORDER BY `open_ncrs` DESC
```

**Result rows**

| category | open_ncrs |
|---|---|
| workmanship | 15 |
| compliance | 9 |

**Expected answer:** Open NCRs by category: workmanship 15, compliance 9 (24 in total).

**Expected result (verified SQL)**

| category | open_ncrs |
|---|---|
| workmanship | 15 |
| compliance | 9 |

**Verdict: CORRECT.** Rule: workmanship=15 and compliance=9. Facts found: ['workmanship', 15, 'compliance', 9]; missing: [].

### curated 8. What is our safety record: TRIR and days without an incident?

**Genie answer** (13.0s, status COMPLETED)

> You want to see the current safety record of the project, including the total recordable incident rate (TRIR) over the last 28 days, the number of days without any incident, and the count of recordable incidents in the last 28 days.
> 
> The current safety record shows **TRIR = 0.0** and **28 days without an incident**. The same current snapshot also shows **recordables_28d = 0**, which aligns with the **TRIR = 0.0** result.

**Generated SQL**

```sql
SELECT `trir_28d`, `safety_days_without_incident`, `recordables_28d`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`kpi_daily`
WHERE `is_current` = true
```

**Result rows**

| trir_28d | safety_days_without_incident | recordables_28d |
|---|---|---|
| 0.0 | 28 | 0 |

**Expected answer:** TRIR (28-day) is 0.0, with 0 recordables and 28 days without an incident.

**Expected result (verified SQL)**

| recordables_28d | safety_days_without_incident | trir_28d |
|---|---|---|
| 0 | 28 | 0.0 |

**Verdict: CORRECT.** Rule: numeric equality on 28 days incident-free and TRIR 0. Facts found: [28, 0]; missing: [].

### curated 9. What does OSHA 1910.147 require?

**Genie answer** (10.0s, status COMPLETED)

> You want to see the title and paraphrased requirement text for the OSHA 1910.147 code clause.
> 
> **OSHA 1910.147** requires **control of hazardous energy through lockout and tagout**: before anyone services or maintains a machine or equipment, the equipment must be isolated from all hazardous energy sources and locked or tagged out so it cannot start up or release stored energy. The excerpt for **OSHA 1910.147** also says each machine needs identified isolation points—such as breakers, valves, and disconnects—where a lock or tag can be applied.

**Generated SQL**

```sql
SELECT `citation_label`, `title`, `text`
FROM `mfg_mc_se_sa`.`bluerridge_agents`.`code_excerpts`
WHERE `citation_label` = 'OSHA 1910.147'
```

**Result rows**

| citation_label | title | text |
|---|---|---|
| OSHA 1910.147 | Control of hazardous energy: lockout and tagout | Control of hazardous energy: lockout and tagout. Before anyone services or maintains a machine or piece of equipment, th |

**Expected answer:** Clause titled 'Control of hazardous energy: lockout and tagout': the paraphrased text says equipment must be isolated from hazardous energy and locked/tagged out before servicing (lockout/tagout).

**Expected result (verified SQL)**

| citation_label | text | title |
|---|---|---|
| OSHA 1910.147 | Control of hazardous energy: lockout and tagout. Before anyone services or maint | Control of hazardous energy: lockout and tagout |

**Verdict: CORRECT.** Rule: answer contains the clause title 'Control of hazardous energy' and 'lockout', and the SQL reads code_excerpts. Facts found: ['Control of hazardous energy', 'lockout']; missing: [].

### curated 10. How accurate is the AI compliance judge?

**Genie answer** (9.9s, status COMPLETED)

> You want to see how accurate the AI compliance judge is overall, using the latest version of the judge and the final scoring method.
> 
> For the headline AI compliance judge result, **prompt_version v3_final** with **eval_column C** and **citation ALL** shows **58.1% precision** and **81.0% recall**. As a quick read, the AI judge is catching more potential issues than it is confirming cleanly, so the output should be treated as a **triage list for engineer review**.

**Generated SQL**

```sql
SELECT `prompt_version`, `eval_column`, ROUND(`precision` * 100, 1) AS `precision_pct`, ROUND(`recall` * 100, 1) AS `recall_pct`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_eval`
WHERE `prompt_version` = 'v3_final'
  AND `eval_column` = 'C'
  AND `citation` = 'ALL'
```

**Result rows**

| prompt_version | eval_column | precision_pct | recall_pct |
|---|---|---|---|
| v3_final | C | 58.1 | 81.0 |

**Expected answer:** The v3 judge (column C, all citations) has precision 58.1% and recall 81.0%.

**Expected result (verified SQL)**

| eval_column | precision_pct | prompt_version | recall_pct |
|---|---|---|---|
| C | 58.1 | v3_final | 81.0 |

**Verdict: CORRECT.** Rule: precision 58.1% and recall 81.0% (a 0-1 fraction is accepted as the same value). Facts found: [58.1, 81.0]; missing: [].

## Held-out questions (NOT in the space)

### heldout 1. Which discipline has the most failed drawings this week?

**Genie answer** (13.0s, status COMPLETED)

> You want to know which engineering discipline had the highest number of drawings that failed compliance review during the week from October 31 to November 6, 2026.
> 
> **Piping** has the most failed drawings this week, with **27** distinct drawings marked **FAIL** between **2026-10-31** and **2026-11-06**. In the result shown, **piping** is the top-ranked discipline for failed drawings in this review window.

**Generated SQL**

```sql
WITH failed_by_discipline AS (
  SELECT
    `discipline`,
    COUNT(DISTINCT `drawing_id`) AS `failed_drawings`
  FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_findings`
  WHERE `review_date` BETWEEN DATE '2026-10-31' AND DATE '2026-11-06'
    AND `status` = 'FAIL'
    AND `discipline` IS NOT NULL
  GROUP BY `discipline`
), ranked AS (
  SELECT
    `discipline`,
    `failed_drawings`,
    RANK() OVER (ORDER BY `failed_drawings` DESC) AS `rnk`
  FROM failed_by_discipline
)
SELECT `discipline`, `failed_drawings`
FROM ranked
WHERE `rnk` <= 1
ORDER BY `failed_drawings` DESC, `discipline`
```

**Result rows**

| discipline | failed_drawings |
|---|---|
| piping | 27 |

**Expected answer:** piping has the most failed drawings this week (27).

**Expected result (verified SQL)**

| discipline | failed_drawings |
|---|---|
| piping | 27 |

**Verdict: CORRECT.** Rule: discipline = piping with 27 failed drawings. Facts found: ['piping', 27]; missing: [].

### heldout 2. Is the cryogenic tank milestone on schedule?

**Genie answer** (13.0s, status COMPLETED)

> You want to see the schedule status of the milestone related to the cryogenic tank. The result shows the milestone's planned and actual end dates, how many days it is late if any, and a status indicating if it is late, due today, or not currently overdue.
> 
> **No** — milestone **MS-281** (**Cryogenic Tank T-203 Install Complete**) is **Late**. Milestone **MS-281** is in **mechanical**, had a planned end date of **2026-11-02**, has **actual_end = null**, and is **4 days late**, so the cryogenic tank milestone is not on schedule.

**Generated SQL**

```sql
SELECT s.`milestone_id`, s.`name`, s.`discipline`, s.`planned_end`, s.`actual_end`, o.`days_late`, CASE WHEN o.`days_late` > 0 THEN 'Late' WHEN o.`days_late` = 0 THEN 'Due today' ELSE 'Not currently overdue' END AS `current_status` FROM `mfg_mc_se_sa`.`bluerridge_silver_engineering`.`schedule` s LEFT JOIN `mfg_mc_se_sa`.`bluerridge_gold_pm`.`schedule_overdue` o ON s.`milestone_id` = o.`milestone_id` WHERE s.`name` IS NOT NULL AND s.`name` ILIKE '%cryogenic tank%' AND s.`planned_end` IS NOT NULL ORDER BY s.`planned_end`
```

**Result rows**

| milestone_id | name | discipline | planned_end | actual_end | days_late | current_status |
|---|---|---|---|---|---|---|
| MS-281 | Cryogenic Tank T-203 Install Complete | mechanical | 2026-11-02 | None | 4 | Late |

**Expected answer:** No. MS-281 (Cryogenic Tank T-203 Install Complete) was due 2026-11-02 and is 4 days late.

**Expected result (verified SQL)**

| days_late | milestone_id | name | planned_end |
|---|---|---|---|
| 4 | MS-281 | Cryogenic Tank T-203 Install Complete | 2026-11-02 |

**Verdict: CORRECT.** Rule: MS-281 identified, 4 days late, and the word 'late'. Facts found: ['MS-281', 4, 'late']; missing: [].

### heldout 3. How many change orders are there and what is their total value?

**Genie answer** (13.0s, status COMPLETED)

> You want to know the total number of change orders and their combined value in US dollars.
> 
> There are **20** change orders with a total value of **$5,282,000**. Based on the single result returned, the full set counted in `change_orders` sums to **$5.282 million**.

**Generated SQL**

```sql
SELECT COUNT(*) AS `change_order_count`, COALESCE(SUM(`amount_usd`), 0) AS `total_value_usd`
FROM `mfg_mc_se_sa`.`bluerridge_silver_engineering`.`change_orders`
```

**Result rows**

| change_order_count | total_value_usd |
|---|---|
| 20 | 5282000 |

**Expected answer:** 20 change orders totalling $5,282,000 (approved $3,475,000, pending $1,448,000, rejected $359,000).

**Expected result (verified SQL)**

| change_orders | total_amount_usd |
|---|---|
| 20 | 5282000 |

**Verdict: CORRECT.** Rule: numeric equality on 20 change orders and $5,282,000 across all statuses (an approved-only total is a miss). Facts found: [20, 5282000]; missing: [].

### heldout 4. Which code citation does the AI judge miss most often?

**Genie answer** (13.0s, status COMPLETED)

> You want to know which specific code citation the AI compliance judge misses the most often, based on the highest number of false negatives.
> 
> The AI judge misses **OSHA 1910.147** most often, with **27** missed cases and a **54.24%** recall. In this result, **OSHA 1910.147** is the single worst-performing citation by missed cases for prompt version **v3_final** after guardrails.

**Generated SQL**

```sql
WITH ranked AS (
  SELECT
    `citation`,
    `fn`,
    `recall`,
    RANK() OVER (ORDER BY `fn` DESC, `citation` ASC) AS `rnk`
  FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`compliance_eval`
  WHERE `prompt_version` = 'v3_final'
    AND `eval_column` = 'C'
    AND `citation` <> 'ALL'
    AND `citation` IS NOT NULL
    AND `fn` IS NOT NULL
)
SELECT
  `citation`,
  `fn`,
  `recall`
FROM ranked
WHERE `rnk` <= 1
ORDER BY `fn` DESC, `citation` ASC
```

**Result rows**

| citation | fn | recall |
|---|---|---|
| OSHA 1910.147 | 27 | 0.5424 |

**Expected answer:** OSHA 1910.147: lowest recall (54.2%), 27 missed flaws.

**Expected result (verified SQL)**

| citation | missed_flaws | recall_pct |
|---|---|---|
| OSHA 1910.147 | 27 | 54.2 |

**Verdict: CORRECT.** Rule: citation OSHA 1910.147 with recall 54.2% (fraction accepted). Facts found: ['OSHA 1910.147', 54.2]; missing: [].

### heldout 5. How many P&IDs are in the drawing register?

**Genie answer** (13.0s, status COMPLETED)

> You want to know the total number of drawings classified as P&ID (Piping and Instrumentation Diagrams) in the drawing register.
> 
> The drawing register contains **373** P&IDs, based on rows where `drawing_type` matches **PID**. With the visible result set, the total count returned is **373**.

**Generated SQL**

```sql
SELECT COUNT(*) AS `pid_drawing_count`
FROM `mfg_mc_se_sa`.`bluerridge_gold_pm`.`drawing_register`
WHERE `drawing_type` ILIKE '%PID%'
```

**Result rows**

| pid_drawing_count |
|---|
| 373 |

**Expected answer:** 373 P&ID drawings are in the register.

**Expected result (verified SQL)**

| pid_drawings |
|---|
| 373 |

**Verdict: CORRECT.** Rule: numeric equality on 373. Facts found: [373]; missing: [].
