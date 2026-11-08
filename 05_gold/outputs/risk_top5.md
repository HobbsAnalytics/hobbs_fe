# Top 5 schedule risks, next 90 days (as of 2026-11-06)

**How much to trust this.** The score is a ranking signal from a trend forecast, not a calibrated probability. In the 8-week backtest the forecast's 80% intervals contained the actual value for only 14% of scored held-out weeks (target 80%), and the forecast ran 9.8 days low on average (MAE 10.6 days over 14 scored points). Scores near 0% or 100% are overconfident, so they are shown as bands and capped at ">95%".

From `mfg_mc_se_sa.bluerridge_gold_pm.risk_forecast`: 64 open milestones with a planned finish between 2026-11-07 and 2027-02-04. Bands (fixed cutoffs): High = score of 0.75 or more, Medium = 0.50 to under 0.75, Low = under 0.50. Count: 26 High, 27 Medium, 11 Low.

| Rank | Milestone | What | Discipline | Crit. | Planned finish | Band (score) | Projected slip days (80% range) | Inherited upstream delay |
|---|---|---|---|---|---|---|---|---|
| 1 | MS-335 | Loop check - Train 4 (WP-315) | instr | 1 | 2027-01-25 | **High** (93%) | 8.3 (0.7 to 14.8) | none |
| 2 | MS-351 | Loop check - Tank T-203 (WP-364) | instr | 3 | 2027-01-21 | **High** (93%) | 8.1 (0.5 to 14.5) | none |
| 3 | MS-352 | Calibrate transmitters - Jetty 2 (WP-333) | instr | 3 | 2027-01-24 | **High** (93%) | 8.1 (0.5 to 14.5) | none |
| 4 | MS-331 | Calibrate transmitters - Utilities Block (WP-327) | instr | 3 | 2027-01-13 | **High** (93%) | 7.9 (0.3 to 14.2) | none |
| 5 | MS-356 | Grout equipment - Flare and Vent (WP-325) | mechanical | 1 | 2027-01-27 | **High** (92%) | 17.0 (2.0 to 32.5) | none |

Inherited upstream delay counts only the part of a late predecessor's delay that exceeds the float between the predecessor's planned end and this milestone's planned start.

## Already late (open and past planned finish, from `mfg_mc_se_sa.bluerridge_gold_pm.schedule_overdue`)

| Milestone | What | Discipline | Crit. | Planned finish | Days late | Open milestones waiting on it |
|---|---|---|---|---|---|---|
| MS-271 | Install heat exchanger - Main Substation (WP-281) | mechanical | 4 | 2026-10-22 | 15 | 60 |
| MS-277 | Align rotating equipment - Train 3 (WP-286) | mechanical | 3 | 2026-10-26 | 11 | 19 |
| MS-278 | Hydrotest line - Pipe Rack South (WP-282) | piping | 3 | 2026-11-01 | 5 | 42 |
| MS-281 | Cryogenic Tank T-203 Install Complete | mechanical | 5 | 2026-11-02 | 4 | 37 |
| MS-279 | Weld and inspect - Utilities Block (WP-264) | piping | 1 | 2026-11-02 | 4 | 0 |
| MS-287 | Pull instrument cable - Train 4 (WP-290) | instr | 1 | 2026-11-04 | 2 | 0 |
| MS-274 | Align rotating equipment - Tank T-204 (WP-277) | mechanical | 3 | 2026-11-06 | 0 | 27 |

These are not in the forecast table; they are late today.

**Method in two sentences.** `ai_forecast` projects the weekly average slip of finished milestones for each discipline 13 weeks ahead; each open milestone takes its discipline's forecast for its planned-finish week plus any float-adjusted delay inherited from a late predecessor. The score is a normal-curve estimate of P(slip > 0) from the forecast interval, grouped into High / Medium / Low bands.
