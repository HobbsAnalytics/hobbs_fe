# Top 5 schedule risks, next 90 days (as of 2026-11-06)

From `mfg_mc_se_sa.bluerridge_gold_pm.risk_forecast`: 64 open milestones with a planned finish between 2026-11-07 and 2027-02-04.

| Rank | Milestone | What | Discipline | Crit. | Planned finish | Projected slip (80% range) | Slip probability |
|---|---|---|---|---|---|---|---|
| 1 | MS-299 | Terminate cables - Tank T-203 (WP-297) | electrical | 3 | 2026-12-04 | 17.0 days (13.5 to 22.9) | 100% |
| 2 | MS-297 | Hydrotest line - Flare and Vent (WP-269) | piping | 3 | 2026-11-19 | 16.2 days (13.6 to 28.1) | 99.8% |
| 3 | MS-303 | Calibrate transmitters - Train 4 (WP-310) | instr | 3 | 2027-01-03 | 12.4 days (4.8 to 18.6) | 98.9% |
| 4 | MS-335 | Loop check - Train 4 (WP-315) | instr | 1 | 2027-01-25 | 8.3 days (0.7 to 14.8) | 93.5% |
| 5 | MS-351 | Loop check - Tank T-203 (WP-364) | instr | 3 | 2027-01-21 | 8.1 days (0.5 to 14.5) | 93.0% |

Why the top three sit where they do: each depends on milestones that are still open and already late (MS-271 is 15 days late, MS-277 is 11), and the model adds that delay on top of the discipline's trend.

Not scored: the cryogenic tank gate MS-281 (4 days late) is already past its planned finish, so it is outside the 90-day window. The scored milestones that depend on it, MS-304 and MS-340, rank 29 and 30 with about 80% slip probability.

Method: `ai_forecast` projects the weekly average slip of finished milestones for each discipline 13 weeks ahead; each open milestone takes its discipline's forecast for its planned-finish week, plus any delay inherited from a late upstream milestone. The probability is a heuristic (a normal curve fitted to the forecast interval), so use it to rank risks, not as a literal chance; the 8-week backtest under-forecast slip (MAE 11.0 days, bias -10.1 days, 17% interval coverage), so the real slip may be larger than shown.
