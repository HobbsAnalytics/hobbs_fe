// Display formatting only. Every value formatted here comes from an API response.

export function formatUsdCompact(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export function formatSignedPct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  return n.toLocaleString('en-US');
}

/** "joseph.hobbs@databricks.com" -> "JH"; falls back to the first two letters, then "?". */
export function initialsFromEmail(email: string | null | undefined): string {
  if (!email) return '?';
  const local = email.split('@')[0] ?? '';
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (local.slice(0, 2) || '?').toUpperCase();
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-11-06" -> "Nov 6" (date-only strings are not shifted by the local time zone). */
export function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}`;
}

export function formatTime(d: Date): string {
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

/** "on_track" -> "On track" (status enums from the API, sentence case like the mockup). */
export function sentenceCase(s: string | null | undefined): string {
  if (!s) return '—';
  const t = s.replace(/_/g, ' ').trim().toLowerCase();
  return t ? t[0].toUpperCase() + t.slice(1) : '—';
}

export function titleCase(s: string | null | undefined): string {
  if (!s) return '—';
  return s
    .replace(/_/g, ' ')
    .split(' ')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
}

// drawing_id = BRL-<discipline code>-<type code>-<nnnn>. The findings API carries no discipline/type columns, so the
// table derives them from the id; the code-to-name pairs below match drawing_register (checked 2026-11-08).
const DISCIPLINE_CODES: Record<string, string> = {
  ELE: 'Electrical',
  INS: 'Instrumentation',
  MEC: 'Mechanical',
  PIP: 'Piping',
  STR: 'Structural',
};
const TYPE_CODES: Record<string, string> = { DTL: 'Detail', GA: 'GA', PID: 'P&ID', SPC: 'Spec', ISO: 'Isometric' };

export function drawingCodes(drawingId: string): { discipline: string; drawingType: string } {
  const [, d = '', t = ''] = drawingId.split('-');
  return { discipline: DISCIPLINE_CODES[d] ?? d, drawingType: TYPE_CODES[t] ?? t };
}

export const AUTH_MODE_LABEL = {
  OBO: 'as you (OBO)',
  SP: 'as the app (service principal)',
} as const;

export const TRANSPORT_LABEL: Record<string, string> = {
  mcp: 'via MCP',
  conversation_api: 'via Conversation API',
};
