# The investment case: for the executive sponsor

This page frames the build for **the executive who funds the Databricks investment**: a Chief Project Officer, a VP of Engineering, or whoever signs off a multi-project rollout. It sits alongside the project manager's framing; it does not replace it.

| Audience | Their question | Where it is answered |
|---|---|---|
| **Project manager** (the day-to-day owner) | "Which drawings need my engineers this week, and what is late?" | [`TALK_TRACK.md` §(c)](TALK_TRACK.md#c-value-story-for-the-business-persona-triage), deck slides 3–7 |
| **Executive sponsor** (the funding decision-maker) | "What is this worth across my portfolio, what risk does it take off the table, and what does it take to find out?" | This page, [`TALK_TRACK.md` §(c2)](TALK_TRACK.md#c2-value-story-for-the-executive-sponsor-the-investment-case), deck slides 8–10 |

The customer deck is [`deck/Bechtel_Databricks_PM_Copilot.pdf`](../deck/Bechtel_Databricks_PM_Copilot.pdf) (13 slides), with [speaker notes](../deck/speaker_notes.md).

> **Read this first: measured or modeled.** Every operational number below is **measured** on the synthetic prototype, and each one links to its proof. Every **dollar** figure is **modeled** from public industry benchmarks plus assumptions that are stated as such. No dollar figure in this repo is measured. The pilot exists to replace each assumption with Bechtel's own data.

## 1. The same results in two languages

| What the project manager sees (measured, synthetic) | What the executive sponsor gets | Proof of the PM number |
|---|---|---|
| **51 of 238** drawings flagged for review this week, each opened at the violation | **Rework avoided:** design errors caught on the drawing, before they become field rework and change orders | [`kpi_today.md`](../05_gold/outputs/kpi_today.md) |
| **26** High-risk milestones in the next 90 days, and **6** already late | **Risk exposure reduced:** compliance, schedule and safety exposure seen weeks earlier | [`risk_top5.md`](../05_gold/outputs/risk_top5.md), [`daily_brief_today.md`](../05_gold/outputs/daily_brief_today.md) |
| Plain-English answers in seconds, with the SQL and the source drawing (Genie scored 15 of 15, 5 of them held out) | **A measured return before scaling:** a 6–8 week pilot with a go/no-go gate before any portfolio spend | [`genie_qa_transcript.md`](../evidence/genie_qa_transcript.md) |

## 2. The value model: rework avoided at scale

```
rework avoided = construction spend
               × direct rework rate
               × share of rework visible on drawings
               × share the Co-Pilot catches early
```

| Input | Base | Range | Basis | What the pilot replaces it with |
|---|---|---|---|---|
| Construction spend | $1B | (normalizer) | Per $1B, so the result scales to any project or portfolio | Bechtel's annual construction volume |
| Direct rework rate | **5%** | held at 5% | **Benchmark.** CII: direct field rework is "usually four to five percent of construction costs" [1]. Hwang et al. find direct rework often reaches 5% [2] | Bechtel's rework and NCR cost history |
| Share of rework visible on drawings | **30%** | 20–40% | **Assumption,** set well below the benchmark that design-induced rework is "more than 70% of the total amount of rework" [3]. That figure includes design changes no compliance check can catch | Root-cause the pilot project's historical NCRs: which ones trace to an error visible on a drawing? |
| Share caught early by the Co-Pilot | **20%** | 10–30% | **Assumption.** The prototype's 81.0% recall on planted violations is not used, because it is in-sample on synthetic data ([`compliance_eval_summary.md`](../evidence/sample_compliance_outputs/compliance_eval_summary.md)) | Run the Co-Pilot on a **closed** project's drawings and count how many of the NCRs that became rework it would have flagged |

### Scenarios

| Scenario | Visible on drawings | Caught early | Avoided per $1B | On an illustrative $10B of construction a year |
|---|---|---|---|---|
| Conservative | 20% | 10% | $1B × 5% × 20% × 10% = **$1.0M** | **$10M a year** |
| **Base** | **30%** | **20%** | $1B × 5% × 30% × 20% = **$3.0M** | **$30M a year** |
| Upside | 40% | 30% | $1B × 5% × 40% × 30% = **$6.0M** | **$60M a year** |

Context for the PM side of the story: FMI and PlanGrid estimate that poor project data and miscommunication cause 48% of US construction rework, $31.3B in 2018 [4]. That is the problem the PM's one-place, show-your-work view addresses.

## 3. Return on the pilot: the break-even

**The pilot budget is an assumption.** We assume a ceiling of **$0.5M all-in**: 6–8 weeks on one project, 2–3 Bechtel SMEs, platform consumption and delivery support. It is set high on purpose. It is not a Databricks quote, and the agreed budget replaces it.

```
break-even catch rate = pilot budget ÷ (project spend × rework rate × visible share)
```

| Pilot project size | Visible share | Rework visible on drawings | Break-even catch rate |
|---|---|---|---|
| $1B | 30% (base) | $15M | **3.3%** (the deck rounds this to ~3%) |
| $1B | 20% (conservative) | $10M | 5.0% |
| $1B | 40% (upside) | $20M | 2.5% |
| $208.7M (the prototype's synthetic budget, [`kpi_today.md`](../05_gold/outputs/kpi_today.md)) | 30% | $3.1M | 16% |

How to read it:
- **The bar is low.** The base case assumes a 20% catch rate, and break-even on a $1B project needs about 3%.
- **Size the pilot project.** The last row is why it should be **$1B or larger**. On a project the size of the synthetic one, the base case is only about $0.6M, close to the pilot budget, so the effect would be hard to measure.

**The portfolio return.** The base case is about **$30M a year** on an illustrative $10B of annual construction, against a one-time pilot of at most $0.5M. That figure does **not** net out two costs:
- **Run-rate platform cost.** The prototype's parse of 1,200 drawings (about 1,370 pages) is estimated at under $10 at list price. The judge and serving costs are not measured; see [`TALK_TRACK.md`](TALK_TRACK.md) "What does it cost?".
- **Rollout and change management.**

The pilot measures run-rate cost per 1,000 drawings so the net return can be stated.

## 4. Risk exposure reduced

| Exposure | What changes | What backs it, and its limits |
|---|---|---|
| **Compliance** | About $15M of rework per $1B (base) is visible on drawings. The Co-Pilot works that exposure at design review, not at inspection or in the field | Measured on synthetic data: recall 81.0%, precision 58.1%. An engineer confirms every flag ([`compliance_eval_summary.md`](../evidence/sample_compliance_outputs/compliance_eval_summary.md)) |
| **Schedule** | Milestone slip risk is ranked by band 90 days ahead, next to the drawing findings. McKinsey finds large projects typically finish 20% late and run up to 80% over budget [5] | The forecast is a v1 ranking signal. Its backtest error is about the same as a naive forecast (MAE 10.6 vs 10.9 days), so it is shown only as bands ([`risk_model_metrics.json`](../evidence/risk_model_metrics.json)) |
| **Safety** | Lockout/tagout (`OSHA 1910.147`) and egress (`IBC 1005.1`) issues are flagged before field work begins | Egress is the strongest rule (90% precision, 100% recall). Lockout/tagout is the weakest (34% precision, 54% recall) and is first on the roadmap. See [`TALK_TRACK.md` §(c)](TALK_TRACK.md#c-value-story-for-the-business-persona-triage) |

## 5. The decision: a week-8 go/no-go

Agree the criteria with the sponsor at kickoff. A suggested set:
1. **Catch rate.** On a closed project's known NCRs, the measured catch rate clears break-even (about 3% on a $1B project at the measured visible share).
2. **Accuracy.** Recall on real violations, and the false-alarm rate per rule.
3. **Hours.** Engineering review hours per drawing, before and after.
4. **Adoption.** Weekly active PMs and engineers on the pilot project.
5. **Run-rate cost.** Platform cost per 1,000 drawings, to net against the value.

If the criteria are met, scale to the next 3–5 projects on the same platform, governance model and bundle. If they are not, the pilot cost is capped and the shortfall is measured.

## 6. What this case does not claim

- **Every dollar figure is modeled, not measured.** That includes $3M per $1B, $30M a year, the $0.5M pilot budget and the 3% break-even.
- **It counts direct rework only.** Delay, claims and other indirect costs are excluded, which makes the case conservative on that axis.
- **Some inputs are examples, not Bechtel figures.** The $10B portfolio and the $0.5M pilot budget are illustrative.
- **The prototype's accuracy is in-sample on synthetic data.** It is not a generalization estimate. See [Honest limitations](../evidence/00_READ_ME_FIRST.md#honest-limitations).
- **The benchmarks are published industry averages and are historical.** Bechtel's own figures replace them in the pilot.

## Sources

1. Construction Industry Institute, *Making Zero Rework a Reality*, Research Summary 203-1 (2005), p. 1: direct field rework is "usually four to five percent of construction costs."
2. B.-G. Hwang, S. R. Thomas, C. T. Haas and C. H. Caldas, "Measuring the Impact of Rework on Construction Cost Performance," *Journal of Construction Engineering and Management* 135(3), 187–198 (2009). doi:10.1061/(ASCE)0733-9364(2009)135:3(187).
3. P. E. D. Love, D. J. Edwards and Z. Irani, "Forensic Project Management: An Exploratory Examination of the Causal Behavior of Design-Induced Rework," *IEEE Transactions on Engineering Management* 55(2), 234–247 (2008): "Design-induced rework has been reported to contribute more than 70% of the total amount of rework experienced in construction and engineering projects."
4. FMI and PlanGrid, *Construction Disconnected* (2018): poor project data (22%) and miscommunication (26%) account for 48% of US construction rework, about $31.3B.
5. McKinsey & Company, "Imagining construction's digital future" (2016): large projects "typically take 20 percent longer to finish than scheduled and are up to 80 percent over budget."
