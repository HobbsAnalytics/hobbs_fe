# Customer deck: Databricks × Bechtel

[`Bechtel_Databricks_PM_Copilot.pdf`](Bechtel_Databricks_PM_Copilot.pdf) is the business-facing deck: 13 slides at 16:9. [`speaker_notes.md`](speaker_notes.md) has a note for every slide.

The deck speaks to two audiences, each in its own language:

| Slides | Audience | Framing |
|---|---|---|
| 1–2 | Both | The problem: manual drawing audits; late violations become rework and slip |
| 3–7 | **Project manager** (the day-to-day owner) | What the PM needs; the Co-Pilot UI; the drawing-to-decision flow; the architecture; prototype results (51 of 238 drawings flagged, recall 81.0%, precision 58.1%, about 3 ms Lakebase reads) |
| 8–10 | **Executive sponsor** (the funding decision-maker: a Chief Project Officer or VP of Engineering) | **The investment case:** the same results in the sponsor's terms; rework avoided, about $3M per $1B of construction (base case); the pilot's break-even, a catch rate of about 3% on one $1B project; risk exposure reduced |
| 11–13 | Both | Trust and governance; why Databricks; a 6–8 week pilot with a week-8 go/no-go |

**Measured or modeled.** The operational numbers are measured on the synthetic prototype; see [`evidence/00_READ_ME_FIRST.md`](../evidence/00_READ_ME_FIRST.md). The dollar figures on slides 9–10 are modeled from cited public benchmarks, and their full derivation and sources are in [`docs/EXECUTIVE_VALUE_CASE.md`](../docs/EXECUTIVE_VALUE_CASE.md).

The PDF was rendered from HTML with headless Chrome. The HTML source is not committed, because it embeds base64 font files.
