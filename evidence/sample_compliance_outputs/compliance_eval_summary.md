# Compliance judge scorecard: AI findings against the planted ground truth

> **Note added after generation (final review, 2026-11-08; the tables below are unchanged).**
> - **Precision and recall are in-sample.** Prompts v1 to v3 and both guardrail rounds were developed from error analysis on the same 1,200 drawings that are scored here. There is no held-out drawing split, so these are not generalization estimates.
> - **57 FAIL rows still contradict themselves.** 57 FAIL rows in `bluerridge_gold_pm.compliance_findings` carry hedging reasons such as "...appears compliant. However...". 49 of them are not planted flaws, and 6 fall in the as-of week (example: BRL-MEC-GA-0308). Cause: the `_admits` guardrail (`03_doc_intelligence/compliance_lib.py`) checks only the last sentence, and the 400-character reason truncation often cuts it (9 rows hit the limit). The guardrails were not re-tuned. `sample_findings.jsonl` skips hedging FAILs by a fixed rule, disclosed in a markdown cell of `03b_compliance_guardrails.ipynb`.

**Headline (final table, prompt v3, column C).** Of 274 planted code violations, the judge caught 222 (recall 81.0%). Of the 382 it flagged, 222 were real (precision 58.1%). F1 = 67.7%. 160 of the reported pairs are not planted flaws; 52 planted flaws were missed.

The judge is `databricks-claude-sonnet-4-5`, reading each drawing's parsed text with a fixed five-rule prompt (no ground truth, no dataset values in it). The ground truth is the 274 flaws the synthetic generator planted on 240 of 1,200 drawings (`bluerridge_silver_engineering.ground_truth_findings`); it is complete only for planted flaws, so a "false positive" is a reported pair that is not planted (a judge error, or at most an unplanted ambiguity), and the numbers describe this synthetic set, not production drawings.

## How it is scored

* **Key:** a `(drawing_id, citation)` pair. Predicted = a FAIL entry in the column being scored; true = a ground-truth row. TP = both, FP = predicted only, FN = planted only. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = their harmonic mean. Micro = counts summed over the five citations.
* **Page agreement** (secondary): of the TPs, the share whose predicted `page_num` equals the planted one.
* **REVIEW** rows (the judge's answer was unusable: 3 drawings in v3) are neither a prediction nor a PASS.
* **Columns:** `A` all raw judge entries; `B` after the judge's own `found_in_text` self-check; `C` after the guardrails (rule applicability + self-contradiction), which is what `compliance_findings` holds.

## Per flaw type (v3, column C)

| citation | flaw type | TP | FP | FN | precision | recall | F1 | page agreement | precision bar / recall bar (20 chars = 100%) |
|---|---|---|---|---|---|---|---|---|---|
| `ASME B16.5 §4.2` | flange_rating_mismatch | 54 | 44 | 9 | 55.1% | 85.7% | 67.1% | 100.0% | `###########         ` `#################   ` |
| `OSHA 1910.147` | missing_loto_tag | 32 | 62 | 27 | 34.0% | 54.2% | 41.8% | 96.9% | `#######             ` `###########         ` |
| `IBC 1005.1` | egress_width_under_code | 45 | 5 | 0 | 90.0% | 100.0% | 94.7% | 100.0% | `##################  ` `####################` |
| `ASME B31.3 §341` | weld_joint_spec_mismatch | 43 | 0 | 6 | 100.0% | 87.8% | 93.5% | 100.0% | `####################` `##################  ` |
| `ASME B31.3 §322` | missing_pressure_relief_notation | 48 | 49 | 10 | 49.5% | 82.8% | 61.9% | 100.0% | `##########          ` `#################   ` |
| **ALL (micro)** |  | 222 | 160 | 52 | **58.1%** | **81.0%** | **67.7%** | 99.6% |  |

## The three evaluation columns (v3 final prompt)

| col | what it is | flagged | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| `A` | all raw judge entries | 607 | 226 | 381 | 48 | 37.2% | 82.5% | 51.3% |
| `B` | after the judge's own found_in_text self-check | 482 | 224 | 258 | 50 | 46.5% | 81.8% | 59.3% |
| `C` | after the guardrails (final table) | 382 | 222 | 160 | 52 | 58.1% | 81.0% | 67.7% |

The guardrails (B to C) removed 98 false positives and cost 2 true positives; the judge's own self-check (A to B) is carried over from its output, not a guardrail effect.

## Prompt lineage (micro, column B unless noted)

| prompt version | what it is | col | flagged | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|---|
| `v1_baseline` | first prompt (plainer wording) | `B` | 898 | 268 | 630 | 6 | 29.8% | 97.8% | 45.7% |
| `v2_prompt_hints` | contained dataset-derived prompt hints; superseded for integrity | `B` | 456 | 253 | 203 | 21 | 55.5% | 92.3% | 69.3% |
| `v3_final` | final, neutral prompt (no value, tag or example that the generator draws) | `B` | 482 | 224 | 258 | 50 | 46.5% | 81.8% | 59.3% |
| `v3_final` | final, neutral prompt (no value, tag or example that the generator draws) | `C` | 382 | 222 | 160 | 52 | 58.1% | 81.0% | 67.7% |

**v2 integrity note.** `v2_prompt_hints` is labelled "contained dataset-derived prompt hints; superseded for integrity": its prompt named example tags and values of the kind the generator draws, so its recall (92.3%) and precision (55.5%) are inflated by knowledge a real drawing set would not give. v3 removed every such hint and added a leakage test, which is why the score falls from v2 to v3 (precision 55.5% to 46.5%, recall 92.3% to 81.8%, column B). v3 is the honest result; v1 is the first, plainer prompt (high recall, many false alarms). Column B for v1 and v2 is derived from their saved raw tables with the current `compliance_lib`; the v2 figure therefore differs slightly from the one in the Task 8 report, which used the self-check before it was scoped to the two presence rules.

## Drawing level (v3, column C)

A drawing FAILs when it has at least one finding (any rule). REVIEW = unusable judge answer.

All 1,200 drawings

| drawings | n | FAIL | PASS | REVIEW |
|---|---|---|---|---|
| planted-flawed | 240 | 202 | 35 | 3 |
| clean | 960 | 117 | 843 | 0 |

Of 240 planted-flawed drawings the final table fails 202 (84.2%); of 960 clean drawings it fails 117 (12.2%). Of the 319 failed drawings, 202 are flawed (63.3%).

As-of week (2026-10-31 to 2026-11-06, 238 drawings reviewed)

| drawings | n | FAIL | PASS | REVIEW |
|---|---|---|---|---|
| planted-flawed | 24 | 21 | 3 | 0 |
| clean | 214 | 30 | 184 | 0 |

The demo's as-of week has 24 planted-flawed drawings; the final table fails 51 drawings, 21 of them flawed and 30 clean (the false alarms). The story figure of 24 would need a perfect judge.

## By drawing type (v3, column C)

| drawing_type | drawings | planted flaws | TP | FP | FN | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|
| ISO | 397 | 60 | 58 | 2 | 2 | 96.7% | 96.7% | 96.7% |
| PID | 373 | 110 | 81 | 112 | 29 | 42.0% | 73.6% | 53.5% |
| GA | 269 | 67 | 50 | 17 | 17 | 74.6% | 74.6% | 74.6% |
| SPEC | 135 | 37 | 33 | 29 | 4 | 53.2% | 89.2% | 66.7% |
| OTHER | 26 | 0 | 0 | 0 | 0 | n/a | n/a | n/a |

The type is `drawings_extracted.drawing_type`. A rule only fires on sheet types where `compliance_lib.APPLICABILITY` allows it (the matrix mirrors the generator's sheet content, disclosed in 03b); `n/a` means nothing was planted or predicted there.

## Wins and losses (v3, column C; two per citation where available, fixed hash order)

### True positives (planted and reported)

| drawing_id | citation | judge's reason | ground-truth flaw type | note |
|---|---|---|---|---|
| BRL-PIP-ISO-0119 | ASME B16.5 §4.2 | Line 4"-LNG-1852-C6S has design pressure 1295 PSIG but one flange is marked CL150 RF, which is rated for only 275 PSIG per the drawing's flange rating table, well belo... | flange_rating_mismatch | page matches the planted page |
| BRL-PIP-ISO-1187 | ASME B16.5 §4.2 | The flange at the connection FROM V-1057 NOZZLE N2 is specified as CL150 RF WN. The design pressure is 335 PSIG, but CLASS 150 is rated for only 275 PSIG maximum allow... | flange_rating_mismatch | page matches the planted page |
| BRL-PIP-PID-0341 | OSHA 1910.147 | Compressor K-2604 (BOG COMPRESSOR) has no LOTO energy isolation tag. Every pump and compressor requires a LOTO tag per the drawing notes. | missing_loto_tag | page matches the planted page |
| BRL-PIP-PID-0539 | OSHA 1910.147 | Pump P-2105A is powered rotating equipment but has no LOTO energy isolation tag shown anywhere in the drawing. | missing_loto_tag | page matches the planted page |
| BRL-ELE-GA-0585 | IBC 1005.1 | EXIT 3 on page 0 requires 60 inches clear width but provides only 50 inches, which is less than required. | egress_width_under_code | page matches the planted page |
| BRL-MEC-GA-0645 | IBC 1005.1 | EXIT 1 provides only 54 inches clear width but requires 60 inches for its occupant load of 255. | egress_width_under_code | page matches the planted page |
| BRL-PIP-ISO-1197 | ASME B31.3 §341 | Line 8"-FG-1657-C6S class C6S requires full-penetration butt welds (BW) with 100% RT per the general notes, but weld W1 is shown as SW (socket weld) type in the weld t... | weld_joint_spec_mismatch | page matches the planted page |
| BRL-PIP-SPC-0065 | ASME B31.3 §341 | Class E15S (COMPRESSOR DISCHARGE, 2355 PSIG design pressure) specifies NONE for examination in Table 2, but General Note 3 requires 100% RT for all classes. | weld_joint_spec_mismatch | page matches the planted page |
| BRL-MEC-SPC-0366 | ASME B31.3 §322 | Vessel V-3607 (SCRUBBER) is listed in Table 3 but has no relief device tag, set pressure, or orifice data. The PSV TAG, SET PRESS, and ORIFICE columns are all empty fo... | missing_pressure_relief_notation | page matches the planted page |
| BRL-INS-PID-1026 | ASME B31.3 §322 | Vessel V-2304 (KNOCKOUT DRUM) has no pressure relief device shown. Note 4 requires every pressure vessel to be protected by a PSV with tag and set pressure. | missing_pressure_relief_notation | page matches the planted page |

### False positives (reported, not planted)

| drawing_id | citation | judge's reason | likely cause | note |
|---|---|---|---|---|
| BRL-PIP-SPC-0808 | ASME B16.5 §4.2 | Page 1, class A1S uses flange class 150 (rated 275 PSIG per the flange rating table) but has design pressure 220 PSIG. The rating of 275 PSIG exceeds the design pressu... | flange_arithmetic | the judge's flange class vs design pressure comparison disagrees with the key (arithmetic or derating); no planted flange flaw here |
| BRL-PIP-ISO-1031 | ASME B16.5 §4.2 | Line 6"-MR-1145-B3S has design pressure 595 PSIG but uses CL300 flanges rated for only 720 PSIG maximum allowable pressure at 100 F. At the design temperature of -270 ... | flange_arithmetic | the judge's flange class vs design pressure comparison disagrees with the key (arithmetic or derating); no planted flange flaw here |
| BRL-INS-PID-1078 | OSHA 1910.147 | Compressor K-2803 (REFRIGERANT COMPRESSOR) has no LOTO energy isolation tag. Note 5 requires every pump and compressor to carry a LOTO tag at its motor. | loto_ocr_misread | drawing text has the misread tag ROTO-2805; the judge flagged the LOTO rule |
| BRL-PIP-PID-0778 | OSHA 1910.147 | Compressor K-2402 is powered rotating equipment but has no LOTO energy isolation tag. Only LOTO-2401, LOTO-2403, and LOTO-2404A are present in the drawing. | other | no planted missing_loto_tag on this drawing; the judge's reading disagrees with the ground truth |
| BRL-STR-GA-0534 | IBC 1005.1 | EXIT 3 on page 1 serves an occupant load of 48 which exceeds 50, requiring minimum 44 IN clear width per the general notes, but only 36 IN is provided. | other | no planted egress_width_under_code on this drawing; the judge's reading disagrees with the ground truth |
| BRL-STR-GA-0912 | IBC 1005.1 | EXIT 4 on page 0 provides 60 inches clear width in the egress schedule but the plan shows only 44 inches. The provided width (44 in) is less than the required width (6... | other | no planted egress_width_under_code on this drawing; the judge's reading disagrees with the ground truth |
| BRL-MEC-SPC-1007 | ASME B31.3 §322 | Page 0 Table 3 lists vessel V-3106 (SUCTION DRUM) with relief device PSV-3106, but page 1 Table 3 does not include vessel V-3106 at all. Vessel V-3106 from page 0 is m... | other | no planted missing_pressure_relief_notation on this drawing; the judge's reading disagrees with the ground truth |
| BRL-PIP-PID-0512 | ASME B31.3 §322 | Vessel V-2701 (SURGE DRUM, DP 610 PSIG) has no pressure relief device shown. Note 4 requires every pressure vessel to be protected by a PSV with its tag and set pressure. | other | no planted missing_pressure_relief_notation on this drawing; the judge's reading disagrees with the ground truth |
| BRL-INS-PID-0580 | ASME B31.3 §322 | Vessel V-2206 (surge drum, DP 1125 PSIG) has no clearly associated pressure relief device. PSV-2206 and PSV-2207 are shown but their association with V-2206 versus V-2... | other | no planted missing_pressure_relief_notation on this drawing; the judge's reading disagrees with the ground truth |
| BRL-PIP-PID-0840 | ASME B31.3 §322 | Vessel V-2202 (SUCTION DRUM) has no pressure relief device shown. The drawing shows PSV-2201, PSV-2202, and PSV-2203, but there is no V-2204 vessel listed, suggesting ... | other | no planted missing_pressure_relief_notation on this drawing; the judge's reading disagrees with the ground truth |

### False negatives (planted, not reported)

| drawing_id | citation | ground truth | flaw type | note |
|---|---|---|---|---|
| BRL-PIP-PID-0286 | ASME B16.5 §4.2 | planted flange_rating_mismatch | flange_rating_mismatch | the judge flagged it, but a guardrail removed it |
| BRL-INS-PID-0055 | ASME B16.5 §4.2 | planted flange_rating_mismatch | flange_rating_mismatch | the judge never flagged this pair (the drawing was passed) |
| BRL-MEC-GA-0014 | OSHA 1910.147 | planted missing_loto_tag | missing_loto_tag | the judge flagged it, but a guardrail removed it |
| BRL-PIP-PID-1094 | OSHA 1910.147 | planted missing_loto_tag | missing_loto_tag | the judge never flagged this pair (the drawing was passed) |
| BRL-PIP-ISO-0878 | ASME B31.3 §341 | planted weld_joint_spec_mismatch | weld_joint_spec_mismatch | the judge never flagged this pair (the drawing was passed) |
| BRL-PIP-SPC-0441 | ASME B31.3 §341 | planted weld_joint_spec_mismatch | weld_joint_spec_mismatch | the judge never flagged this pair (the drawing was passed) |
| BRL-PIP-PID-0865 | ASME B31.3 §322 | planted missing_pressure_relief_notation | missing_pressure_relief_notation | the judge never flagged this pair (the drawing was passed) |
| BRL-PIP-PID-0957 | ASME B31.3 §322 | planted missing_pressure_relief_notation | missing_pressure_relief_notation | the judge never flagged this pair (the drawing was passed) |
| BRL-INS-PID-0564 | ASME B31.3 §322 | planted missing_pressure_relief_notation | missing_pressure_relief_notation | the judge never flagged this pair (it flagged other rules on the drawing: ['ASME B16.5 §4.2', 'OSHA 1910.147']) |
| BRL-MEC-GA-1150 | OSHA 1910.147 | planted missing_loto_tag | missing_loto_tag | the judge never flagged this pair (it flagged other rules on the drawing: ['IBC 1005.1']) |

## Why the false positives happen

| likely cause | false positives | share |
|---|---|---|
| LOTO OCR misread (ROTO-/LOT0- ...) | 32 | 20% |
| Flange arithmetic (class vs design pressure) | 44 | 28% |
| Other | 84 | 52% |
| **Total false positives** | 160 | 100% |

"Other" by citation: `ASME B31.3 §322` 49, `OSHA 1910.147` 30, `IBC 1005.1` 5. Causes are assigned by `scoring_lib.fp_cause`: a LOTO false positive counts as an OCR misread when the drawing's parsed text spells a LOTO tag with a misread prefix (ROTO-, LOT0-, LOTOTO- ...); every ASME B16.5 false positive counts as flange arithmetic; the rest is "other" (in the reasons read, the judge reports a vessel as lacking a relief device or a pump as lacking an isolation tag, or over-reads a tag convention, for example that an `A` suffix implies a missing `B` unit; the key does not plant these, and this notebook does not re-read each drawing to decide whether the item is really there). The counts sum to the 160 false positives.

Where the 52 misses are lost: 48 never flagged by the judge, 2 removed by a guardrail, 2 removed by the judge self-check.

## MLflow

Experiment `/Shared/bluerridge_pm_copilot/compliance_judge_eval` (id `4276059729056366`). One run per (prompt version, column); params `prompt_version`, `eval_column`, `judge_model=databricks-claude-sonnet-4-5`, `source_raw_table`; metrics micro and per-flaw-type precision / recall / F1.

| prompt version | column | run id |
|---|---|---|
| `v1_baseline` | `B` | `d83bc4f07be64cc6804b068b67e6a67d` |
| `v2_prompt_hints` | `B` | `75c49c17d8fd4fed81e70e1a6129e545` |
| `v3_final` | `A` | `5fca7dd43c884c6f8cd391af48272e7d` |
| `v3_final` | `B` | `a2f394aea28c43e6b7ac69f6aebb4b2a` |
| `v3_final` | `C` | `03b10341ce5e456aa631a3eae8dec5fd` |

## Non-determinism and what these numbers are from

`ai_parse_document` and the judge are model-based, so a fresh run of the AI steps would drift a little (a few findings either way). These numbers do not depend on such a re-run: they score the judge answers **saved** in `compliance_judge_raw` (v3; AI job run 649534681854336), `compliance_judge_raw_v2_prompt_hints` and `compliance_judge_raw_v1_baseline`, so re-running the scoring notebook gives identical figures. The committed numbers come from the scoring job run noted below and the MLflow runs above. No AI call was made by the scoring (checked: 9 query plans, 0 `AI Query` steps).

## Reproduce

* Notebook `03_doc_intelligence/04_ground_truth_scoring.ipynb`; pure functions `scoring_lib.entries_by_column`, `scoring_lib.score_pairs`, `scoring_lib.fp_cause`; the columns come from `compliance_lib.raw_entries` (A), `compliance_lib.flatten_judgement` (B) and `compliance_lib.judge_with_guardrails` (C). Unit tests: `03_doc_intelligence/tests/test_scoring.py`.
* Tables read: `mfg_mc_se_sa.bluerridge_silver_engineering.ground_truth_findings`, `mfg_mc_se_sa.bluerridge_gold_pm.compliance_judge_raw`, `mfg_mc_se_sa.bluerridge_gold_pm.compliance_judge_raw_v2_prompt_hints`, `mfg_mc_se_sa.bluerridge_gold_pm.compliance_judge_raw_v1_baseline`, `mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings` (cross-check), `mfg_mc_se_sa.bluerridge_silver_engineering.drawings_parsed` and `mfg_mc_se_sa.bluerridge_silver_engineering.drawings_extracted` (text and type). Table written: `mfg_mc_se_sa.bluerridge_gold_pm.compliance_eval`.
* The table behind this page:

```sql
SELECT prompt_version, eval_column, citation, tp, fp, fn, precision, recall, f1, page_agreement
FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_eval ORDER BY prompt_version, eval_column, citation;
```
* Guard on the answer key: `01_synthetic_data/tests/test_sidecars_match_generator.py` regenerates the 1,200 drawings (seed 42) and checks the committed ground truth and manifest are unchanged (it needs the pinned `reportlab==5.1.0 faker==40.44.0`, and skips with a named reason otherwise).
* Scoring job run: **63308297933870** (task run 197528256262427), a one-time `databricks jobs submit` on serverless with `disable_auto_optimization: true` (payload `03_doc_intelligence/outputs/submit_payloads/04_ground_truth_scoring_submit.json`), about 2 minutes, no AI call. An earlier run of the same notebook (434188899914061) was superseded by a wording fix; the MLflow runs above are from the final run (a re-run deletes the experiment's earlier runs first).
