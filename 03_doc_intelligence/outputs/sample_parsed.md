# Sample: `BRL-INS-PID-0052` as parsed by `ai_parse_document`

One row of `mfg_mc_se_sa.bluerridge_silver_engineering.drawings_parsed`, written by [`01_parse_drawings.ipynb`](../01_parse_drawings.ipynb). The text under "parsed_markdown" is that column's value, unedited; the element table at the end is read from the row's `parse_json`.

| column | value |
|---|---|
| drawing_id | `BRL-INS-PID-0052` |
| volume_path | `/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/BRL-INS-PID-0052.pdf` |
| parse_status | `ok` |
| parsed_at | 2026-11-07 04:28:57 UTC |
| pages / elements | 1 / 26 |
| size | parsed_markdown 2,971 characters, parse_json 7,079 characters |

## Why this drawing

It is one of the 240 flawed drawings: a P&ID with three planted flaws (`ground_truth_findings.jsonl`). Nothing in the text marks them; they show as missing or inconsistent labels.

| finding_id | flaw_type | citation | severity | page_num | ground-truth bbox [x, y, w, h] | parsed element holding it |
|---|---|---|---|---|---|---|
| BRL-INS-PID-0052-F01 | missing_loto_tag | OSHA 1910.147 | high | 0 | [0.3398, 0.2222, 0.0875, 0.1104] | id 1 (figure) |
| BRL-INS-PID-0052-F02 | missing_pressure_relief_notation | ASME B31.3 §322 | critical | 0 | [0.4948, 0.4533, 0.0975, 0.2378] | id 1 (figure) |
| BRL-INS-PID-0052-F03 | flange_rating_mismatch | ASME B16.5 §4.2 | critical | 0 | [0.235, 0.5532, 0.0334, 0.0365] | id 1 (figure) |

What the text gives a reader to work with:

- `missing_loto_tag`: the figure text has LOTO tags for `K-2501` and `P-2505A` (`LOTO-2501`, `LOTO-2505A`; the parser sometimes returns the O of LOTO as a zero) but none for compressor `K-2502` (BOG COMPRESSOR).
- `missing_pressure_relief_notation`: the figure text has vessels `V-2503`, `V-2504` and `V-2506`; the first two come with `PSV-2503 / SET 1890 PSIG` and `PSV-2504 / SET 500 PSIG`, knockout drum `V-2506` has no PSV tag or set pressure.
- `flange_rating_mismatch`: the figure text has a `FLG CL150` among lines tagged `10"-BOG-2551-B3S` (class code B3S = CL300 in the general notes, `DP 500 PSIG`), and the flange rating table in the same text gives CLASS 150 a maximum of 275 PSIG.

Parsing is done by a model, so it is not repeatable to the letter: parsing this PDF more than once during the build returned the same labels in a different order, boxes a few pixels apart and a differently spelled LOTO tag. The labels inside a `figure` are one block in the parser's own order, not the layout order, so a flaw inside a schematic cannot be placed more precisely than the figure's box.

## parsed_markdown

<!-- page_num: 0 -->

# PROCESS FLOW AND INSTRUMENTATION - FLARE AND VENT

```figure
PSV-2503
SET 1890 PSIG
M
O LOTO-2501
FIC
2560
FROM FEED GAS HEADER
FLG CL900
M
FLG CL900
HV-2571
TO STORAGE TANK
6"-NG-2550-D9S
DP 1890 PSIG
K-2501
REFRIGERANT COMPRESSOR
6"-NG-2550-D9S
DP 1890 PSIG
K-2502
BOG COMPRESSOR
V-2503
SEPARATOR
DP 1890 PSIG / -270 TO 140 F
PSV-2504
SET 500 PSIG
FIC
2561
FROM REFRIGERANT HEADER
FLG CL150
M
O LOTO-2505A
FLG CL300
HV-2573
TO FLARE HEADER
10"-BOG-2551-B3S
DP 500 PSIG
P-2505A
BOOSTER PUMP
10"-BOG-2551-B3S
DP 500 PSIG
V-2504
SURGE DRUM
DP 500 PSIG / -270 TO 140 F
V-2506
KNOCKOUT DRUM
DP 500 PSIG / -270 TO 140 F
```

## LEGEND

```figure
∞
```

HV MANUAL VALVE

FV CONTROL VALVE

```figure
PT
101
```

INSTRUMENT, TAGS PER ISA 5.1

```figure
II
```

FLG FLANGED JOINT

SEE NOTES FOR LINE CLASS CODES

PSV PRESSURE SAFETY VALVE

```figure
○ LOTO-0000
```

LOTO ENERGY ISOLATION TAG

DP DESIGN PRESSURE (PSIG)

## GENERAL NOTES

1. THIS DRAWING IS A SCHEMATIC. MATERIALS AND DETAILS ARE IN THE PIPING CLASS
SPECIFICATION.
2. LINE TAG FORMAT IS NPS-SERVICE-NUMBER-CLASS. CLASS CODES: A1S = CL150, B3S = CL300, C6S
= CL600, D9S = CL900, E15S = CL1500.
3. THE FLANGE CLASS AT EVERY FLANGED JOINT SHALL BE RATED FOR THE LINE DESIGN
PRESSURE (ASME B16.5); SEE FLANGE RATING REFERENCE.
4. EVERY PRESSURE VESSEL SHALL BE PROTECTED BY A PRESSURE RELIEF DEVICE (PSV). ITS TAG
AND SET PRESSURE ARE SHOWN ON THE VESSEL (ASME B31.3 PARA. 322).
5. EVERY PUMP AND COMPRESSOR SHALL CARRY A LOTO ENERGY ISOLATION TAG AT ITS MOTOR
(OSHA 29 CFR 1910.147).
6. INSTRUMENT TAGS PER ISA 5.1. CONTROL LOOP DETAILS ARE ON THE LOOP DIAGRAMS.

## REFERENCE CODES AND STANDARDS

- ASME B31.3 PROCESS PIPING
- ASME B16.5 PIPE FLANGES AND FLANGED FITTINGS
- OSHA 29 CFR 1910.147 LOCKOUT/TAGOUT
- ISA 5.1 INSTRUMENTATION SYMBOLS

## FLANGE RATING REFERENCE

ASME B16.5, SS GROUP 2.1, AT 100 F

<table><tr><th>FLANGE CLASS</th><th>MAX ALLOWABLE PRESSURE</th></tr><tr><td>CLASS 150</td><td>275 PSIG</td></tr><tr><td>CLASS 300</td><td>720 PSIG</td></tr><tr><td>CLASS 600</td><td>1440 PSIG</td></tr><tr><td>CLASS 900</td><td>2160 PSIG</td></tr><tr><td>CLASS 1500</td><td>3600 PSIG</td></tr></table>

<table><tr><th>REV</th><th>DATE</th><th>DESCRIPTION</th><th>BY</th><th>CHK</th></tr><tr><td>A</td><td>2025-05-08</td><td>ISSUED FOR REVIEW</td><td>SO</td><td>TC</td></tr><tr><td>B</td><td>2026-03-23</td><td>ISSUED FOR DESIGN</td><td>VS</td><td>AC</td></tr></table>

<table><tr><td colspan="4">PROJECT<br>BLUE RIDGE LNG TERMINAL - PHASE 2</td></tr><tr><td colspan="4">TITLE<br>PIPING AND INSTRUMENTATION DIAGRAM<br>FLARE AND VENT - PROCESS UNIT</td></tr><tr><td colspan="3">DRAWING NUMBER<br>BRL-INS-PID-0052</td><td>REV<br>B</td></tr><tr><td>SCALE<br>NTS</td><td>SHEET<br>1 OF 1</td><td>DATE<br>2026-03-23</td><td>DISCIPLINE<br>INSTR</td></tr><tr><td colspan="2">DRAWN BY<br>D. VINCENT</td><td colspan="2">CHECKED BY<br>P. HALL</td><td>APPROVED BY<br>E. O'BRIEN</td></tr></table>

## Elements in parse_json

Boxes are `[x1, y1, x2, y2]` in pixels of the rendered page image, origin top-left (3366 x 2178 px for these sheets). `figure` elements also carry a generated `description` in `parse_json`; it is not part of `parsed_markdown`.

| id | type | page_id | confidence | box (px) | text |
|---|---|---|---|---|---|
| 0 | title | 0 | 1 | [109, 106, 1034, 136] | PROCESS FLOW AND INSTRUMENTATION - FLARE AND VENT |
| 1 | figure | 0 | 0.9674 | [105, 330, 2227, 1514] | PSV-2503 / SET 1890 PSIG / M / O LOTO-2501 / FIC / 2560 / F… |
| 2 | section_header | 0 | 1 | [82, 1769, 177, 1791] | LEGEND |
| 3 | figure | 0 | 0.5266 | [99, 1828, 163, 1866] | ∞ |
| 4 | text | 0 | 1 | [177, 1839, 364, 1861] | HV MANUAL VALVE |
| 5 | figure | 0 | 0.6853 | [102, 1881, 163, 1940] |  |
| 6 | text | 0 | 1 | [177, 1912, 374, 1934] | FV CONTROL VALVE |
| 7 | figure | 0 | 0.9485 | [105, 1967, 163, 2022] | PT / 101 |
| 8 | text | 0 | 1 | [177, 1984, 473, 2006] | INSTRUMENT, TAGS PER ISA 5.1 |
| 9 | figure | 0 | 0.4402 | [119, 2044, 146, 2083] | II |
| 10 | text | 0 | 1 | [177, 2057, 377, 2079] | FLG FLANGED JOINT |
| 11 | text | 0 | 1 | [109, 2086, 422, 2108] | SEE NOTES FOR LINE CLASS CODES |
| 12 | figure | 0 | 0.1434 | [632, 1830, 680, 1925] |  |
| 13 | text | 0 | 1 | [717, 1890, 1010, 1912] | PSV PRESSURE SAFETY VALVE |
| 14 | figure | 0 | 0.6421 | [619, 1965, 748, 1993] | ○ LOTO-0000 |
| 15 | text | 0 | 1 | [785, 1967, 1078, 1989] | LOTO ENERGY ISOLATION TAG |
| 16 | text | 0 | 1 | [615, 2057, 898, 2079] | DP DESIGN PRESSURE (PSIG) |
| 17 | section_header | 0 | 1 | [2305, 73, 2526, 101] | GENERAL NOTES |
| 18 | text | 0 | 1 | [2305, 114, 3318, 422] | 1. THIS DRAWING IS A SCHEMATIC. MATERIALS AND DETAILS ARE I… |
| 19 | section_header | 0 | 1 | [2305, 436, 2785, 462] | REFERENCE CODES AND STANDARDS |
| 20 | text | 0 | 1 | [2305, 475, 2832, 572] | - ASME B31.3 PROCESS PIPING / - ASME B16.5 PIPE FLANGES AND… |
| 21 | section_header | 0 | 1 | [2305, 1243, 2638, 1267] | FLANGE RATING REFERENCE |
| 22 | text | 0 | 1 | [2305, 1272, 2632, 1294] | ASME B16.5, SS GROUP 2.1, AT 100 F |
| 23 | table | 0 | 0.9998 | [2305, 1296, 2893, 1476] | <table><tr><th>FLANGE CLASS</th><th>MAX ALLOWABLE PRESSURE<… |
| 24 | table | 0 | 0.9994 | [2292, 1525, 3339, 1643] | <table><tr><th>REV</th><th>DATE</th><th>DESCRIPTION</th><th… |
| 25 | table | 0 | 0.9305 | [2292, 1720, 3339, 2138] | <table><tr><td colspan="4">PROJECT<br>BLUE RIDGE LNG TERMIN… |
