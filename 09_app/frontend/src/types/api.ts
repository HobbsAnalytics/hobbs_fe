// Response shapes, mirrored from 09_app/API.md and 09_app/backend/routes/*.py. Read-only contract: the backend owns it.

export type AuthMode = 'OBO' | 'SP';

export interface Whoami {
  email: string | null;
  user_name: string | null;
  auth_mode: AuthMode;
}

export interface KpiToday {
  project_id: string;
  snapshot_date: string;
  schedule: {
    status: string;
    milestones_hit: number;
    milestones_total: number;
    slipped_milestone_id: string | null;
    slipped_days: number | null;
  };
  budget: { total_usd: number; overrun_usd: number; eac_pct: number };
  safety: { days_without_incident: number; recordables_28d: number; trir_28d: number };
  open_ncrs: { total: number; compliance: number; workmanship: number };
  compliance_week: { reviewed: number; passed: number; failed: number };
}

export interface ComplianceSummary {
  week: { start: string; end: string };
  reviewed: number;
  passed: number;
  failed: number;
  review: number;
  fails_by_citation: { citation: string; count: number }[];
}

/** Normalized [x, y, w, h], 0..1, top-left origin (project convention). */
export type BBox = [number, number, number, number];

/** ground_truth (generator's planted box), parse_element (approximate), page ([0,0,1,1]); null on PASS/REVIEW. */
export type BBoxSource = 'ground_truth' | 'parse_element' | 'page' | string | null;

export interface Finding {
  drawing_id: string;
  finding_id: string;
  status: 'FAIL' | 'REVIEW' | 'PASS' | string;
  severity: string | null;
  citation: string | null;
  reason: string | null;
  evidence_text: string | null;
  /** 0-based page index, like ai_parse_document page ids. */
  page_num: number | null;
  bbox: BBox | null;
  bbox_source: BBoxSource;
  review_date: string;
}

export type FindingScope = 'week' | 'all';
export type FindingStatus = 'FAIL' | 'REVIEW';

export interface FindingsPage {
  items: Finding[];
  total: number;
  limit: number;
  offset: number;
  scope: FindingScope;
  status: FindingStatus;
}

export interface RiskItem {
  milestone_id: string;
  name: string;
  discipline: string;
  criticality: number;
  planned_end: string;
  risk_band: 'High' | 'Medium' | 'Low' | string;
  risk_rank: number;
  projected_slip_days: number | null;
  forecast_confidence_lower: number | null;
  forecast_confidence_upper: number | null;
  upstream_delay_days: number | null;
  upstream_milestone_id: string | null;
}

export interface RiskTop {
  items: RiskItem[];
  risk_counts: { High: number; Medium: number; Low: number };
}

export interface OverdueItem {
  milestone_id: string;
  name: string;
  discipline: string;
  criticality: number;
  planned_end: string;
  days_late: number;
  downstream_open_count: number;
  status: 'late' | 'due_today';
}

export interface ScheduleOverdue {
  items: OverdueItem[];
  total: number;
  late: number;
  due_today: number;
}

export interface DailyBrief {
  brief_md: string;
  brief_date: string;
  validation_status: string;
  prompt_version: string;
  generated_at: string;
}

export interface DrawingDetail {
  drawing_id: string;
  discipline: string | null;
  revision: string | null;
  drawing_type: string | null;
  volume_path: string | null;
  latest_review_date: string | null;
  latest_status: string | null;
  fail_count: number | null;
  pdf_url: string;
  findings: Finding[];
}

export interface CitationHit {
  citation_id: string;
  citation_label: string;
  title: string | null;
  source: string | null;
  is_paraphrase: boolean | null;
  text: string | null;
  related: Omit<CitationHit, 'related'>[];
}

// ---- Chat SSE (POST /api/chat) ----

export type Transport = 'mcp' | 'conversation_api';

export interface ChatResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
}

export interface DrawingSourceItem {
  kind: 'drawing';
  drawing_id: string;
  finding_id: string | null;
  page_num: number | null;
  bbox: BBox | null;
  citation: string | null;
}

export interface CitationSourceItem {
  kind: 'citation';
  label: string;
  url: string;
}

export type SourceItem = DrawingSourceItem | CitationSourceItem;

export type ChatEvent =
  | { type: 'status'; value: 'running' }
  | { type: 'status'; value: 'done'; transport?: Transport }
  | { type: 'status'; value: 'error'; message?: string; transport?: Transport }
  | { type: 'conversation'; conversation_id: string }
  | { type: 'answer'; text: string }
  | { type: 'sql'; query: string }
  | ({ type: 'result' } & ChatResult)
  | { type: 'sources'; items: SourceItem[] };
