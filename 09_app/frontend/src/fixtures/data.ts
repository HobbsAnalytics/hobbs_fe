// DEV/TEST ONLY. Shaped exactly like 09_app/API.md, filled with live values read from the gold tables on 2026-11-08.
// Never imported by production code paths: main.tsx loads it only behind the compile-time __USE_FIXTURES__ flag,
// and scripts/check-no-fixtures.mjs fails the build if FIXTURE_MARKER (or any fixture id) reaches dist/.
import type {
  CitationHit,
  ComplianceSummary,
  DailyBrief,
  DrawingDetail,
  Finding,
  FindingsPage,
  KpiToday,
  RiskTop,
  ScheduleOverdue,
  Whoami,
} from '../types/api';

export const FIXTURE_MARKER = '__BLUERRIDGE_FIXTURE__';
export const FIXTURE_CONVERSATION_ID = 'fixture-conv-0001';

export const whoamiObo: Whoami = {
  email: 'joseph.hobbs@databricks.com',
  user_name: 'joseph.hobbs@databricks.com',
  auth_mode: 'OBO',
};
export const whoamiSp: Whoami = { email: null, user_name: null, auth_mode: 'SP' };

export const kpiToday: KpiToday = {
  project_id: 'BRL-PH2',
  snapshot_date: '2026-11-06',
  schedule: { status: 'on_track', milestones_hit: 6, milestones_total: 11, slipped_milestone_id: 'MS-281', slipped_days: 4 },
  budget: { total_usd: 208700000, overrun_usd: 4800000, eac_pct: 2.3 },
  safety: { days_without_incident: 28, recordables_28d: 0, trir_28d: 0.0 },
  open_ncrs: { total: 24, compliance: 9, workmanship: 15 },
  compliance_week: { reviewed: 238, passed: 187, failed: 51 },
};

export const complianceSummary: ComplianceSummary = {
  week: { start: '2026-10-31', end: '2026-11-06' },
  reviewed: 238,
  passed: 187,
  failed: 51,
  review: 0,
  fails_by_citation: [
    { citation: 'ASME B31.3 §322', count: 30 },
    { citation: 'OSHA 1910.147', count: 25 },
    { citation: 'ASME B16.5 §4.2', count: 15 },
    { citation: 'IBC 1005.1', count: 8 },
    { citation: 'ASME B31.3 §341', count: 7 },
  ],
};

export const findings: Finding[] = [
  {
    drawing_id: 'BRL-INS-PID-0580', finding_id: 'BRL-INS-PID-0580-C01', status: 'FAIL', severity: 'critical',
    citation: 'ASME B31.3 §322',
    reason: 'Vessel V-2206 (surge drum, DP 1125 PSIG) has no clearly associated pressure relief device. PSV-2206 and PSV-2207 are shown but their association with V-2206 versus V-2207 is ambiguous in the schematic text.',
    evidence_text: 'V-2206 SURGE DRUM DP 1125 PSIG', page_num: 0, bbox: [0.0312, 0.4587, 0.6295, 0.2374],
    bbox_source: 'parse_element', review_date: '2026-11-06',
  },
  {
    drawing_id: 'BRL-INS-PID-0580', finding_id: 'BRL-INS-PID-0580-C02', status: 'FAIL', severity: 'critical',
    citation: 'ASME B31.3 §322',
    reason: 'Vessel V-2207 (surge drum, DP 1125 PSIG) has no clearly associated pressure relief device. PSV-2206 and PSV-2207 are shown but their association with V-2207 versus V-2206 is ambiguous in the schematic text.',
    evidence_text: 'V-2207 SURGE DRUM DP 1125 PSIG', page_num: 0, bbox: [0.0312, 0.4587, 0.6295, 0.2374],
    bbox_source: 'parse_element', review_date: '2026-11-06',
  },
  {
    drawing_id: 'BRL-PIP-PID-0813', finding_id: 'BRL-PIP-PID-0813-C01', status: 'FAIL', severity: 'critical',
    citation: 'ASME B31.3 §322',
    reason: 'Vessel V-2701 (knockout drum, DP 405 PSIG) has no pressure relief device shown. Note 4 requires every pressure vessel to be protected by a PSV with tag and set pressure shown on the vessel.',
    evidence_text: 'V-2701 KNOCKOUT DRUM DP 405 PSIG', page_num: 1, bbox: [0.0312, 0.1515, 0.6295, 0.2383],
    bbox_source: 'parse_element', review_date: '2026-11-06',
  },
  {
    drawing_id: 'BRL-PIP-SPC-0390', finding_id: 'BRL-PIP-SPC-0390-C01', status: 'FAIL', severity: 'critical',
    citation: 'ASME B31.3 §322',
    reason: 'Vessel V-3203 (KNOCKOUT DRUM) has no relief device tag listed in Table 3. The PSV TAG, SET PRESS, and ORIFICE columns are all empty for this vessel.',
    evidence_text: 'V-3203 KNOCKOUT DRUM 105 PSIG [empty cells]', page_num: 0, bbox: [0.0221, 0.5088, 0.6454, 0.0328],
    bbox_source: 'ground_truth', review_date: '2026-11-06',
  },
  {
    drawing_id: 'BRL-STR-GA-0534', finding_id: 'BRL-STR-GA-0534-C01', status: 'FAIL', severity: 'high',
    citation: 'IBC 1005.1',
    reason: 'EXIT 3 on page 1 serves an occupant load of 48 which exceeds 50, requiring minimum 44 IN clear width per the general notes, but only 36 IN is provided.',
    evidence_text: 'EXIT 3 MAIN HALL 48 36 36', page_num: 1, bbox: [0, 0, 1, 1], bbox_source: 'page', review_date: '2026-11-06',
  },
  {
    drawing_id: 'BRL-PIP-ISO-0664', finding_id: 'BRL-PIP-ISO-0664-C01', status: 'FAIL', severity: 'medium',
    citation: 'ASME B31.3 §341',
    reason: 'Weld W3 is a fillet weld (FW) but the drawing states that socket and fillet welds are not permitted for class B3S cold service.',
    evidence_text: 'W3 FW VT', page_num: 0, bbox: [0.2623, 0.4377, 0.0426, 0.0301], bbox_source: 'ground_truth',
    review_date: '2026-11-05',
  },
  {
    drawing_id: 'BRL-PIP-PID-0143', finding_id: 'BRL-PIP-PID-0143-C01', status: 'FAIL', severity: 'critical',
    citation: 'ASME B31.3 §322',
    reason: 'Vessel V-2403 (SURGE DRUM) has no pressure relief device shown. The drawing shows PSV-2401 and PSV-2402 but no PSV-2403 for V-2403.',
    evidence_text: 'V-2403 SURGE DRUM DP 575 PSIG', page_num: 0, bbox: [0.4948, 0.1503, 0.0975, 0.2378],
    bbox_source: 'ground_truth', review_date: '2026-11-05',
  },
];

export function findingsPage(scope: 'week' | 'all', status: 'FAIL' | 'REVIEW', limit: number, offset: number): FindingsPage {
  const all = findings.filter((f) => f.status === status);
  return { items: all.slice(offset, offset + limit), total: all.length, limit, offset, scope, status };
}

export const riskTop: RiskTop = {
  items: [
    { milestone_id: 'MS-335', name: 'Loop check - Train 4 (WP-315)', discipline: 'instr', criticality: 1, planned_end: '2027-01-25', risk_band: 'High', risk_rank: 1, projected_slip_days: 8.2997, forecast_confidence_lower: 0.7259, forecast_confidence_upper: 14.8065, upstream_delay_days: 0, upstream_milestone_id: null },
    { milestone_id: 'MS-351', name: 'Loop check - Tank T-203 (WP-364)', discipline: 'instr', criticality: 3, planned_end: '2027-01-21', risk_band: 'High', risk_rank: 2, projected_slip_days: 8.0804, forecast_confidence_lower: 0.5066, forecast_confidence_upper: 14.5193, upstream_delay_days: 0, upstream_milestone_id: null },
    { milestone_id: 'MS-352', name: 'Calibrate transmitters - Jetty 2 (WP-333)', discipline: 'instr', criticality: 3, planned_end: '2027-01-24', risk_band: 'High', risk_rank: 3, projected_slip_days: 8.0804, forecast_confidence_lower: 0.5066, forecast_confidence_upper: 14.5193, upstream_delay_days: 0, upstream_milestone_id: null },
  ],
  risk_counts: { High: 26, Medium: 27, Low: 11 },
};

export const scheduleOverdue: ScheduleOverdue = {
  items: [
    { milestone_id: 'MS-271', name: 'Install heat exchanger - Main Substation (WP-281)', discipline: 'mechanical', criticality: 4, planned_end: '2026-10-22', days_late: 15, downstream_open_count: 60, status: 'late' },
    { milestone_id: 'MS-277', name: 'Align rotating equipment - Train 3 (WP-286)', discipline: 'mechanical', criticality: 3, planned_end: '2026-10-26', days_late: 11, downstream_open_count: 19, status: 'late' },
    { milestone_id: 'MS-278', name: 'Hydrotest line - Pipe Rack South (WP-282)', discipline: 'piping', criticality: 3, planned_end: '2026-11-01', days_late: 5, downstream_open_count: 42, status: 'late' },
    { milestone_id: 'MS-279', name: 'Weld and inspect - Utilities Block (WP-264)', discipline: 'piping', criticality: 1, planned_end: '2026-11-02', days_late: 4, downstream_open_count: 0, status: 'late' },
    { milestone_id: 'MS-281', name: 'Cryogenic Tank T-203 Install Complete', discipline: 'mechanical', criticality: 5, planned_end: '2026-11-02', days_late: 4, downstream_open_count: 37, status: 'late' },
    { milestone_id: 'MS-287', name: 'Pull instrument cable - Train 4 (WP-290)', discipline: 'instr', criticality: 1, planned_end: '2026-11-04', days_late: 2, downstream_open_count: 0, status: 'late' },
    { milestone_id: 'MS-274', name: 'Align rotating equipment - Tank T-204 (WP-277)', discipline: 'mechanical', criticality: 3, planned_end: '2026-11-06', days_late: 0, downstream_open_count: 27, status: 'due_today' },
  ],
  total: 7,
  late: 6,
  due_today: 1,
};

export const dailyBrief: DailyBrief = {
  brief_md:
    'Blue Ridge LNG Terminal Phase 2 is tracking a $4.8M overrun and schedule pressure from late milestones, though safety remains strong.\n\n' +
    '- **Schedule:** 6 milestones are already late and 1 due today. MS-271 is already late by 15 days, MS-277 by 11 days, and MS-281 by 4 days.\n\n' +
    '- **Budget:** The project shows a $4.8M overrun against the $208.7M total budget.\n\n' +
    '- **Safety:** 28 days without an incident and a 28-day TRIR of 0.0.\n\n' +
    '- **Compliance:** 51 of 238 drawings flagged for engineer review this week. ASME B31.3 §322 leads with 30 findings, followed by OSHA 1910.147 with 25. 24 NCRs remain open.\n\n' +
    '- **Risk:** 26 milestones are High risk in the next 90 days; the top 3 are MS-335, MS-351, and MS-352.\n\n' +
    'Where would you like to focus first?',
  brief_date: '2026-11-06',
  validation_status: 'pass',
  prompt_version: 'v3',
  generated_at: '2026-11-08T17:31:08.689Z',
};

export const drawingDetail: DrawingDetail = {
  drawing_id: 'BRL-PIP-ISO-0664',
  discipline: 'piping',
  revision: 'D',
  drawing_type: 'ISO',
  volume_path: '/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/BRL-PIP-ISO-0664.pdf',
  latest_review_date: '2026-11-05',
  latest_status: 'FAIL',
  fail_count: 1,
  pdf_url: '/api/drawings/BRL-PIP-ISO-0664/pdf',
  findings: findings.filter((f) => f.drawing_id === 'BRL-PIP-ISO-0664'),
};

export function drawingDetailFor(id: string): DrawingDetail {
  const fs = findings.filter((f) => f.drawing_id === id);
  if (id === drawingDetail.drawing_id) return drawingDetail;
  return { ...drawingDetail, drawing_id: id, fail_count: fs.length, pdf_url: `/api/drawings/${id}/pdf`, findings: fs };
}

export const citations: Record<string, CitationHit> = {
  'OSHA 1910.147': {
    citation_id: 'osha-1910-147', citation_label: 'OSHA 1910.147', title: 'Control of hazardous energy: lockout and tagout',
    source: 'OSHA 29 CFR 1910', is_paraphrase: true,
    text: 'Control of hazardous energy: lockout and tagout. Before anyone services or maintains a machine or piece of equipment, the equipment must be isolated from all sources of hazardous energy and locked or tagged out so that it cannot start up or release stored energy.',
    related: [],
  },
  'ASME B31.3 §341': {
    citation_id: 'asme-b31-3-341', citation_label: 'ASME B31.3 §341', title: 'Weld examination and joint requirements',
    source: 'ASME B31.3', is_paraphrase: true,
    text: 'Weld examination and joint requirements. Welds in process piping must be examined to a defined extent, and the examination method and amount depend on the fluid service and the weld type.',
    related: [],
  },
};

/** Canned SSE frames for "Which drawings failed this week and why?" (one FAIL finding per source row, so a drawing
 *  repeats; a drawing with no FAIL finding carries nulls; `running` repeats after `conversation`). */
export const chatFramesFailedDrawings: string[] = [
  'data: {"type":"status","value":"running"}\n\n',
  `data: {"type":"conversation","conversation_id":"${FIXTURE_CONVERSATION_ID}"}\n\n`,
  ': keep-alive comment\n\n',
  'data: {"type":"status","value":"running"}\n\n',
  'data: {"type":"answer","text":"**51** drawings failed review this week. The most common citation is ASME B31.3 §322 (missing pressure relief on vessels), followed by OSHA 1910.147."}\n\n',
  'data: {"type":"sql","query":"SELECT drawing_id, citation, severity\\nFROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings\\nWHERE status = \'FAIL\' AND review_date BETWEEN \'2026-10-31\' AND \'2026-11-06\'\\nORDER BY severity"}\n\n',
  'data: {"type":"result","columns":["drawing_id","citation","severity"],"rows":[["BRL-INS-PID-0580","ASME B31.3 §322","critical"],["BRL-INS-PID-0580","ASME B31.3 §322","critical"],["BRL-PIP-ISO-0664","ASME B31.3 §341","medium"],["BRL-ELE-GA-0023","OSHA 1910.147","high"]],"row_count":85,"truncated":true}\n\n',
  'data: {"type":"sources","items":[' +
    '{"kind":"drawing","drawing_id":"BRL-INS-PID-0580","finding_id":"BRL-INS-PID-0580-C01","page_num":0,"bbox":[0.0312,0.4587,0.6295,0.2374],"citation":"ASME B31.3 §322"},' +
    '{"kind":"drawing","drawing_id":"BRL-INS-PID-0580","finding_id":"BRL-INS-PID-0580-C02","page_num":0,"bbox":[0.0312,0.4587,0.6295,0.2374],"citation":"ASME B31.3 §322"},' +
    '{"kind":"drawing","drawing_id":"BRL-PIP-ISO-0664","finding_id":"BRL-PIP-ISO-0664-C01","page_num":0,"bbox":[0.2623,0.4377,0.0426,0.0301],"citation":"ASME B31.3 §341"},' +
    '{"kind":"drawing","drawing_id":"BRL-ELE-GA-0023","finding_id":null,"page_num":null,"bbox":null,"citation":null},' +
    '{"kind":"citation","label":"ASME B31.3 §322","url":"/api/citations/ASME%20B31.3%20%C2%A7322"},' +
    '{"kind":"citation","label":"OSHA 1910.147","url":"/api/citations/OSHA%201910.147"}' +
    ']}\n\n',
  'data: {"type":"status","value":"done","transport":"mcp"}\n\n',
];

/** Graceful empty answer: no SQL, no rows, no sources event, no transport on done. */
export const chatFramesEmpty: string[] = [
  'data: {"type":"status","value":"running"}\n\n',
  `data: {"type":"conversation","conversation_id":"${FIXTURE_CONVERSATION_ID}"}\n\n`,
  'data: {"type":"answer","text":"I\'m not sure which milestones you mean — try naming a discipline or specifying \'this week\'."}\n\n',
  'data: {"type":"status","value":"done"}\n\n',
];

export const chatFramesError: string[] = [
  'data: {"type":"status","value":"running"}\n\n',
  'data: {"type":"status","value":"error","message":"Genie did not answer within 110 seconds. Try a narrower question.","transport":"mcp"}\n\n',
];
