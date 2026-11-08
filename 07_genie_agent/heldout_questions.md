# Held-out Genie questions (NOT loaded into the space)

Five questions phrased differently from the curated ten and covering other angles. They are **never** added to the space (not as examples, sample questions or instructions) and the space was not tuned toward them: they measure how well the space generalizes. The SQL is the verified answer key only. Results below come from running it on 2026-11-06 data. All data is synthetic.

## 1. Which discipline has the most failed drawings this week?

**Verified SQL**

```sql
SELECT discipline, COUNT(DISTINCT drawing_id) AS failed_drawings
FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings
WHERE status = 'FAIL' AND review_date BETWEEN '2026-10-31' AND '2026-11-06'
GROUP BY discipline
ORDER BY failed_drawings DESC
LIMIT 1
```

**Result of running it (as of 2026-11-06)**

| discipline | failed_drawings |
|---|---|
| piping | 27 |

**Expected answer:** piping has the most failed drawings this week (27).

**Scoring rule:** discipline = piping with 27 failed drawings.

## 2. Is the cryogenic tank milestone on schedule?

**Verified SQL**

```sql
SELECT milestone_id, name, planned_end, days_late
FROM mfg_mc_se_sa.bluerridge_gold_pm.schedule_overdue
WHERE name LIKE '%Cryogenic%'
```

**Result of running it (as of 2026-11-06)**

| days_late | milestone_id | name | planned_end |
|---|---|---|---|
| 4 | MS-281 | Cryogenic Tank T-203 Install Complete | 2026-11-02 |

**Expected answer:** No. MS-281 (Cryogenic Tank T-203 Install Complete) was due 2026-11-02 and is 4 days late.

**Scoring rule:** MS-281 identified, 4 days late, and the word 'late'.

## 3. How many change orders are there and what is their total value?

**Verified SQL**

```sql
SELECT COUNT(*) AS change_orders, SUM(amount_usd) AS total_amount_usd
FROM mfg_mc_se_sa.bluerridge_silver_engineering.change_orders
```

**Result of running it (as of 2026-11-06)**

| change_orders | total_amount_usd |
|---|---|
| 20 | 5282000 |

**Expected answer:** 20 change orders totalling $5,282,000 (approved $3,475,000, pending $1,448,000, rejected $359,000).

**Scoring rule:** numeric equality on 20 change orders and $5,282,000 across all statuses (an approved-only total is a miss).

## 4. Which code citation does the AI judge miss most often?

**Verified SQL**

```sql
SELECT citation, ROUND(recall * 100, 1) AS recall_pct, fn AS missed_flaws
FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_eval
WHERE prompt_version = 'v3_final' AND eval_column = 'C' AND citation <> 'ALL'
ORDER BY recall ASC
LIMIT 1
```

**Result of running it (as of 2026-11-06)**

| citation | missed_flaws | recall_pct |
|---|---|---|
| OSHA 1910.147 | 27 | 54.2 |

**Expected answer:** OSHA 1910.147: lowest recall (54.2%), 27 missed flaws.

**Scoring rule:** citation OSHA 1910.147 with recall 54.2% (fraction accepted).

## 5. How many P&IDs are in the drawing register?

**Verified SQL**

```sql
SELECT COUNT(*) AS pid_drawings
FROM mfg_mc_se_sa.bluerridge_gold_pm.drawing_register
WHERE drawing_type = 'PID'
```

**Result of running it (as of 2026-11-06)**

| pid_drawings |
|---|
| 373 |

**Expected answer:** 373 P&ID drawings are in the register.

**Scoring rule:** numeric equality on 373.
