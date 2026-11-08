# Daily Brief, 2026-11-06

Blue Ridge LNG Terminal Phase 2 remains on track overall, though 7 milestones are now overdue and budget variance has reached $4.8M.

**Schedule**: 7 milestones are already late; MS-271 (heat exchanger install) is 15 days overdue with 60 downstream tasks at risk. MS-281 (Tank T-203) slipped 4 days this period. 3 instrumentation milestones (MS-335, MS-351, MS-352) show High risk through January.

**Budget**: Current overrun stands at $4.8M against the $208.7M total budget (2.3% EAC).

**Safety**: 28 days without a recordable incident; 0.0 TRIR over the past 28 days.

**Compliance**: 51 of 238 drawings flagged for engineer review this week. 85 findings led by ASME B31.3 §322 (30 findings, primarily missing pressure relief devices on vessels) and OSHA 1910.147 (25 findings).

**Risk**: 24 open NCRs (9 compliance, 15 workmanship).

Would you like me to drill into the MS-271 delay or the pressure relief device findings?

## How this was grounded

- Validation status: **pass** (1 model call; a failed first draft would be kept in `validation_detail`)
- Model: `databricks-claude-sonnet-4-5`, prompt version `v2`
- Generated at: 2026-11-08 17:19:00.914863 UTC, job run `438698467007318`
- Source: `mfg_mc_se_sa.bluerridge_gold_pm.daily_brief`, key `(BRL-PH2, 2026-11-06)`
- Validator checks (`05_gold/brief_lib.py`, `validate_brief`), run on the stored brief against the stored context:
  - Numbers: every number matches a number in the context: PASS
  - IDs: every milestone and drawing ID exists in the context: PASS
  - No probabilities: no probability wording, no percentage next to risk wording: PASS
  - Length: 144 words (limit 150): PASS
- Risk is shown by band only. The heuristic risk score is not in the context, so the model could not quote it.
- Compliance is triage: drawings flagged for engineer review, not a verdict.

<details><summary>Context JSON the model was given</summary>

```json
{
  "as_of_date": "2026-11-06",
  "compliance_this_week": {
    "fail_findings_by_citation": [
      {
        "citation": "ASME B31.3 \u00a7322",
        "fail_findings": 30
      },
      {
        "citation": "OSHA 1910.147",
        "fail_findings": 25
      },
      {
        "citation": "ASME B16.5 \u00a74.2",
        "fail_findings": 15
      },
      {
        "citation": "IBC 1005.1",
        "fail_findings": 8
      },
      {
        "citation": "ASME B31.3 \u00a7341",
        "fail_findings": 7
      }
    ],
    "fail_findings_total": 85,
    "flagged_drawings": 51,
    "passed_drawings": 187,
    "review_unusable_drawings": 0,
    "reviewed_drawings": 238,
    "top_fail_findings": [
      {
        "citation": "ASME B31.3 \u00a7322",
        "drawing_id": "BRL-INS-PID-0018",
        "reason": "Vessel V-2102 (SUCTION DRUM) has no pressure relief device shown. General Note 4 requires every pressure vessel to be protected by a PSV...",
        "severity": "critical"
      },
      {
        "citation": "ASME B31.3 \u00a7322",
        "drawing_id": "BRL-INS-PID-0036",
        "reason": "Separator vessel V-2404 has no pressure relief device shown. Note 4 requires every pressure vessel to be protected by a PSV with its tag...",
        "severity": "critical"
      },
      {
        "citation": "ASME B31.3 \u00a7322",
        "drawing_id": "BRL-INS-PID-0184",
        "reason": "Pressure vessel V-2302 (SUCTION DRUM, DP 370 PSIG) requires a pressure relief device per note 4, but PSV-2302 is shown on K-2301 instead of...",
        "severity": "critical"
      },
      {
        "citation": "ASME B31.3 \u00a7322",
        "drawing_id": "BRL-INS-PID-0580",
        "reason": "Vessel V-2206 (surge drum, DP 1125 PSIG) has no clearly associated pressure relief device. PSV-2206 and PSV-2207 are shown but their...",
        "severity": "critical"
      },
      {
        "citation": "ASME B31.3 \u00a7322",
        "drawing_id": "BRL-INS-PID-0580",
        "reason": "Vessel V-2207 (surge drum, DP 1125 PSIG) has no clearly associated pressure relief device. PSV-2206 and PSV-2207 are shown but their...",
        "severity": "critical"
      }
    ],
    "window": "2026-10-31 to 2026-11-06"
  },
  "kpi": {
    "budget_eac_pct": 2.3,
    "budget_overrun_usd": 4800000.0,
    "budget_total_usd": 208700000.0,
    "milestones_hit": 6,
    "milestones_total": 11,
    "open_ncrs": 24,
    "open_ncrs_compliance": 9,
    "open_ncrs_workmanship": 15,
    "project_id": "BRL-PH2",
    "recordables_28d": 0,
    "safety_days_without_incident": 28,
    "schedule_status": "on_track",
    "slipped_days": 4,
    "slipped_milestone_id": "MS-281",
    "snapshot_date": "2026-11-06",
    "trir_28d": 0.0
  },
  "project": "Blue Ridge LNG Terminal, Phase 2",
  "risk_forecast_top3": [
    {
      "discipline": "instr",
      "milestone_id": "MS-335",
      "name": "Loop check - Train 4 (WP-315)",
      "planned_end": "2027-01-25",
      "risk_band": "High"
    },
    {
      "discipline": "instr",
      "milestone_id": "MS-351",
      "name": "Loop check - Tank T-203 (WP-364)",
      "planned_end": "2027-01-21",
      "risk_band": "High"
    },
    {
      "discipline": "instr",
      "milestone_id": "MS-352",
      "name": "Calibrate transmitters - Jetty 2 (WP-333)",
      "planned_end": "2027-01-24",
      "risk_band": "High"
    }
  ],
  "schedule_already_late": 6,
  "schedule_due_today": 1,
  "schedule_overdue_top3": [
    {
      "days_late": 4,
      "downstream_open_count": 37,
      "milestone_id": "MS-281",
      "name": "Cryogenic Tank T-203 Install Complete"
    },
    {
      "days_late": 15,
      "downstream_open_count": 60,
      "milestone_id": "MS-271",
      "name": "Install heat exchanger - Main Substation (WP-281)"
    },
    {
      "days_late": 11,
      "downstream_open_count": 19,
      "milestone_id": "MS-277",
      "name": "Align rotating equipment - Train 3 (WP-286)"
    }
  ],
  "schedule_overdue_total": 7
}
```

</details>
