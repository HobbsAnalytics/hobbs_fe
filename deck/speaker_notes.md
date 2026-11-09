# Speaker notes: Databricks × Bechtel, AI-assisted project intelligence for mega-projects

November 2026 · 13 slides

The deck speaks to two audiences, each in its own language:
- **Slides 3–7** are for the **project manager**, who runs the project day to day.
- **Slides 8–10** are **the investment case** for the **executive sponsor**, who funds a multi-project rollout (a Chief Project Officer or VP of Engineering).

Slides 11–13 (trust, why Databricks, path forward) serve both.

---

## 1. AI-assisted project intelligence for mega-projects

Thank you for the time. Today covers a problem every EPC mega-project has with drawing compliance and project visibility, and a working prototype on Databricks that addresses it.

We'll look at it twice:
- first through the eyes of the project manager who would use it every day;
- then as an investment case for the executive who would fund a pilot and a portfolio rollout.

We'll close with a concrete pilot proposal on one live Bechtel project.

## 2. Manual drawing audits are slow, and violations found late become rework and slip

An LNG terminal produces thousands of isometrics, P&IDs, general arrangements and specifications. Each one is checked by hand against codes such as ASME B16.5 and B31.3, OSHA 1910.147 and IBC 1005.1, on billable engineering hours.

When a violation surfaces late, it costs rework, schedule and safety exposure. Meanwhile the PM's view of the project is spread across separate tools.

This slide stays qualitative. The investment case on slides 9 and 10 puts public industry benchmarks on it, and the pilot replaces them with Bechtel's own figures.

## 3. One place to ask, plain-English answers, and evidence they can trust

This is the day-to-day owner's view. From the project manager's side, three things matter:
- **One place** for schedule, cost, safety, quality and compliance.
- **Plain-English answers.** They want to ask a question directly instead of filing a request with an analyst.
- **Evidence they can trust.** Every answer shows the drawing, the code clause and the query behind it.

## 4. Every answer comes with its evidence

This is the prototype UI showing the prototype's real values from the synthetic Blue Ridge project, so it matches the live app if we demo it.

The KPI strip reads:
- schedule on track at 6 of 11 key milestones;
- budget +2.3% EAC, $4.8M over;
- 0 TRIR, with 28 days incident-free;
- 24 open NCRs, 9 of them compliance-related;
- 26 High-risk milestones in the next 90 days, shown as a band, never a percentage.

The daily brief is written by AI from the project's own data, and every number in it is checked. The late list leads with MS-281, the cryogenic tank T-203 milestone, 4 days late.

Ask "Which drawings failed this week and why?" and Genie returns the answer, the generated SQL and the result: 85 findings on 51 drawings.

One click on BRL-ELE-GA-0842 opens the drawing at the evidence: Exit 4 is 48 in clear width against 60 in required under IBC 1005.1.

## 5. Every drawing is checked automatically, and engineers review the flagged ones first

Each drawing goes through four steps:
1. **Read.** AI Functions parse the drawing and capture the title block and drawing type.
2. **Check.** An LLM judge tests it against the rule set, with deterministic guardrails behind it.
3. **Explain.** Vector Search over plain-language clause summaries explains why a drawing failed.
4. **Triage.** Engineers work one queue of flagged drawings, each opened at the violation.

The AI prioritizes the work. It does not approve drawings, and an engineer makes every call.

## 6. Every layer runs inside one governed platform

Here is the whole stack:
- **Ingest** with Lakeflow.
- **Document intelligence** with AI Functions.
- **Knowledge** with Vector Search.
- **Gold KPI tables** and `ai_forecast`.
- **Genie** for natural-language questions.
- **Lakebase** for the app's fast path.
- **Databricks Apps** for a secure app with single sign-on.

The point of the slide is the frame around it. Unity Catalog governs every layer with one permission model, so there are no copies across vendors.

## 7. The prototype narrowed a week's 238 drawings to 51 for engineer review

Be clear up front: the prototype ran on representative synthetic data, not on Bechtel data. It is a fictional Blue Ridge LNG Terminal, Phase 2, with 1,200 synthetic drawings and synthetic schedule, cost, safety and NCR data. These are prototype measurements, not production guarantees.

What it did:
- read all 1,200 drawings with zero parse errors;
- flagged 51 of the 238 drawings in the week reviewed;
- served app data in about 3 ms;
- Genie answered all 15 benchmark questions correctly, including 5 it had never seen.

Be direct about accuracy. The AI judge caught about 81% of planted violations (recall 81.0%), and about 58% of its flags were real (precision 58.1%). So it is a triage assistant with an engineer in the loop, not an approver.

The pilot's job is to tune it on Bechtel's own standards and historical NCRs, and to measure recall on real violations.

## 8. The same results, in the executive sponsor's terms

Now the same outcome, said in the language of whoever signs off a multi-project rollout: a Chief Project Officer or a VP of Engineering. Each row pairs what the project manager sees with what the sponsor gets:
- **Rework avoided.** The PM sees 51 of 238 drawings flagged, each opened at the violation. The sponsor gets design errors caught on the drawing, before they become field rework and change orders.
- **Risk exposure reduced.** The PM sees 26 High-risk milestones and 6 already late. The sponsor gets compliance, schedule and safety exposure seen weeks earlier.
- **A measured return before scaling.** The PM gets answers in seconds. The sponsor gets a 6–8 week pilot with a go/no-go gate before any portfolio spend.

The next two slides put dollars on it, using public benchmarks until the pilot measures Bechtel's own numbers.

## 9. Catching design errors early is worth about $3M per $1B of construction

Walk the chain left to right:
1. **Per $1B of construction.** We start here so the number scales to any project or portfolio.
2. **Direct rework, 5%.** Direct rework typically runs 4–5% of construction cost (Construction Industry Institute RS 203-1; Hwang et al. 2009). That is about $50M per $1B, before any indirect cost.
3. **Visible on drawings, 30%.** We assume only 30% of that rework is visible on drawings as code or design errors. That is deliberately well below the more than 70% that research attributes to design-induced rework (Love, Edwards and Irani 2008), because that figure includes design changes a compliance check can't catch.
4. **Caught early, 20%.** Of the visible share, we assume the Co-Pilot catches 20% early, before the drawing reaches the field. The prototype caught 81% of planted violations, but on synthetic data, so we have not banked that.

The result is about $3M per $1B, direct cost only. The range is $1M conservative to $6M upside. On an illustrative $10B a year of construction, that is $10M to $60M a year, with $30M in the base case.

Say it plainly: this is a model built on public benchmarks, not a measured result. The pilot replaces each input with Bechtel's numbers.

If asked for context: FMI and PlanGrid (2018) attribute 48% of US construction rework to poor project data and miscommunication. That is the problem the PM's one-place view addresses.

## 10. The pilot pays for itself at a ~3% catch rate on one $1B project

This is the funding decision.

**The budget.** We assume a pilot budget ceiling of $0.5M all-in, including Bechtel's own SME time. It is set high on purpose, and the agreed budget replaces it.

**Break-even.** On one $1B project, about $15M of rework is visible on drawings ($1B × 5% × 30%). The pilot pays for itself if the Co-Pilot, left running on that project, catches about 3% of it early. If only 20% of rework is visible on drawings (the conservative case), the bar is 5%. The base case assumes a 20% catch rate, so the bar is low.

**The prize.** About $30M a year in the base case at portfolio scale, before run-rate platform cost, which the pilot measures.

**Pick a pilot project of $1B or more**, so the effect is large enough to measure. On the prototype's synthetic $209M project, the base case is about $0.6M.

**Risk exposure:**
- **Compliance.** Violations are caught at design review, not at inspection or in the field.
- **Schedule.** Slip risk is ranked 90 days ahead. McKinsey (2016) finds large projects typically finish 20% late and can run up to 80% over budget.
- **Safety.** Lockout/tagout and egress issues are flagged before field work begins.

Close the section: the week-8 readout replaces these assumptions with measured numbers, and the go/no-go decision rests on them.

## 11. Every answer is governed, shows its work, and leaves the decision to an engineer

Trust is designed in rather than added later.

**Governed data.**
- Unity Catalog applies one permission model, with lineage from raw drawing to KPI.
- Row-level security by discipline is a Unity Catalog row filter. In the prototype we demonstrated it on the drawing register through Genie, which answers as the signed-in user.
- The app's own pages run under the app's identity and show all disciplines. Extending per-user filtering to every app page is a pilot design decision.

**Checked AI, in the app.**
- Every answer shows its SQL.
- The daily brief's numbers are checked against the data.
- Every flag cites its clause and evidence.
- AI output is labeled "verify before action".

## 12. One platform for every piece, governed once

What makes this possible on Databricks is unification. Documents, structured data, AI, natural-language analytics, an operational database and app hosting run natively on one platform, under one catalog and one permission model.

Stitching point solutions together usually means:
- copying data between vendors;
- maintaining a permission model in each tool;
- losing lineage at every hand-off.

Keep the claim precise. We are not saying other tools can't do individual pieces. The difference is that here they share one governance model, with no copies across vendors.

For the sponsor, this is also what makes the rollout cheap to repeat: each new project reuses the same platform rather than adding another tool.

## 13. A 6–8 week pilot on one live Bechtel project

We propose a 6–8 week pilot on one live project's drawing set. Bechtel would provide the drawings, the applicable standards and checklists, and 2–3 SMEs.

We'd measure four things:
- recall on real violations;
- engineering review hours saved;
- PM adoption;
- rework avoided against the break-even from slide 10.

At week 8, the executive sponsor makes a go/no-go call on scaling across the portfolio, based on those measured numbers.

The ask today:
1. Book a pilot-selection workshop, with the sponsor in the room to agree the go/no-go criteria.
2. Set up data access.
3. Agree a kickoff date.
