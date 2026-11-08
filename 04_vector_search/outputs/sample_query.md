# Vector Search smoke test: `code_excerpts_vs`

> The five citation labels are fixed, illustrative project labels and clause numbers are not authoritative (in the real ASME B16.5, pressure-temperature ratings are in section 2, not 4.2). ASME and IBC entries are plain-language paraphrases, not quotes of the copyrighted codes.

Index `mfg_mc_se_sa.bluerridge_agents.code_excerpts_vs` on endpoint `bluerridge_vs`; Delta Sync, TRIGGERED, managed embeddings from `databricks-bge-large-en` on column `text`; 52 rows indexed (table has 52). Top 3 results per query; score is the index's similarity score.

## "flange pressure class too low for the line rating"

Expected primary citation: `ASME B16.5 §4.2` - **in top 3**

| Rank | citation_label | title | score |
|---|---|---|---|
| 1 | `ASME B16.5 §4.2` | Flange pressure class must suit design pressure and temperature | 0.7290 |
| 2 | `ASME B16.5 §4.4` | Allowable pressure drops at higher temperature | 0.6854 |
| 3 | `ASME B16.5 §4.1` | Flange pressure classes and what they mean | 0.6591 |

## "missing lockout tagout isolation tag on equipment"

Expected primary citation: `OSHA 1910.147` - **in top 3**

| Rank | citation_label | title | score |
|---|---|---|---|
| 1 | `OSHA 1910.147` | Control of hazardous energy: lockout and tagout | 0.6757 |
| 2 | `OSHA 1910.147(c)(5)` | Lockout and tagout devices must be durable and identifiable | 0.6543 |
| 3 | `OSHA 1910.147(d)` | Sequence for applying lockout: shut down, isolate, lock, release stored energy, verify | 0.6039 |

## "exit door too narrow for egress"

Expected primary citation: `IBC 1005.1` - **in top 3**

| Rank | citation_label | title | score |
|---|---|---|---|
| 1 | `IBC 1005.1` | Minimum width of the means of egress | 0.6319 |
| 2 | `IBC 1010.1.1` | Minimum clear width of an exit door | 0.6306 |
| 3 | `IBC 1010.1.9` | Door hardware must open without a key | 0.6017 |

## "weld examination less than required"

Expected primary citation: `ASME B31.3 §341` - **in top 3**

| Rank | citation_label | title | score |
|---|---|---|---|
| 1 | `ASME B31.3 §341` | Weld examination and joint requirements | 0.6633 |
| 2 | `ASME B31.3 §341.3` | Acceptance criteria for weld examination | 0.6576 |
| 3 | `ASME B31.3 §328` | Welder and procedure qualification | 0.6315 |

## "no pressure relief valve shown"

Expected primary citation: `ASME B31.3 §322` - **in top 3**

| Rank | citation_label | title | score |
|---|---|---|---|
| 1 | `ASME B31.3 §322` | Pressure-relief requirements | 0.6410 |
| 2 | `ASME B31.3 §322.5` | Thermal relief for blocked-in liquid lines | 0.5825 |
| 3 | `ASME B31.3 §322.3` | No block valve between the system and its relief device | 0.5730 |

**Pass bar:** matching primary citation in top 3 for 5/5 queries (need at least 4); flange query returns `ASME B16.5 §4.2` in top 3: yes.

## Exact-label lookup (how the app resolves a clicked citation)

Filter `citation_label = 'OSHA 1910.147'` returned 1 row.

- `citation_id`: `osha-1910-147`
- `title`: Control of hazardous energy: lockout and tagout
- `source`: OSHA 29 CFR 1910, `is_paraphrase`: True
- text: Control of hazardous energy: lockout and tagout. Before anyone services or maintains a machine or piece of equipment, the equipment must be isolated from all sources of hazardous energy and locked or tagged out so that it cannot start up or release stored energy. Each machine needs identified energy isolation points, such as breakers, valves and disconnects, where a lock or tag can be applied. A reviewer checks the drawing for lockout and tagout isolation points, tags or notes on each piece of equipment, and flags equipment that shows no lockout or isolation provision.
