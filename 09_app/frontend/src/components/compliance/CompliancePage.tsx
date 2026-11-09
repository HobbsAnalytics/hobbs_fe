import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle2, ClipboardList, FileSearch } from 'lucide-react';
import PageTransition from '../layout/PageTransition';
import MetricCard from '../shared/MetricCard';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';
import FindingsTable from './FindingsTable';
import FindingDrawer from './FindingDrawer';
import { useComplianceSummary, useFindings } from '../../hooks/useCompliance';
import { formatNumber, formatShortDate } from '../../lib/format';
import type { Finding, FindingScope, FindingStatus } from '../../types/api';

const PAGE_SIZE = 25;

const Toggle = <T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) => (
  <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5" role="group" aria-label={label}>
    {options.map((o) => (
      <button
        key={o.value}
        type="button"
        aria-pressed={value === o.value}
        onClick={() => onChange(o.value)}
        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
          value === o.value ? 'bg-emerald-50 text-emerald-700' : 'text-slate-600 hover:bg-slate-50'
        }`}
      >
        {o.label}
      </button>
    ))}
  </div>
);

const SummaryTiles: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useComplianceSummary();
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <LoadingSkeleton type="metric" count={4} />
      </div>
    );
  }
  if (isError) return <ErrorAlert title="Compliance summary unavailable" error={error} onRetry={() => refetch()} />;
  if (!data) return null;
  const week = `${formatShortDate(data.week.start)} – ${formatShortDate(data.week.end)}`;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard variant="full" index={0} label="Drawings reviewed" value={formatNumber(data.reviewed)} sub={week} icon={<ClipboardList size={18} />} />
        <MetricCard variant="full" index={1} label="Passed" value={formatNumber(data.passed)} sub="No FAIL or REVIEW finding" icon={<CheckCircle2 size={18} />} tone="good" />
        <MetricCard variant="full" index={2} label="Failed" value={formatNumber(data.failed)} sub="At least one FAIL finding" icon={<AlertTriangle size={18} />} tone={data.failed > 0 ? 'bad' : 'good'} />
        <MetricCard variant="full" index={3} label="Needs review" value={formatNumber(data.review)} sub="Needs review (judge output unusable)" icon={<FileSearch size={18} />} tone={data.review > 0 ? 'warn' : 'neutral'} />
      </div>
      {data.fails_by_citation.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="card-subtitle">FAIL findings by citation this week</span>
          {data.fails_by_citation.map((c) => (
            <span key={c.citation} className="px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700">
              <span className="font-mono">{c.citation}</span> · {c.count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

/** `/compliance`: summary tiles + server-paginated findings + finding drawer. */
const CompliancePage: React.FC = () => {
  const navigate = useNavigate();
  const [scope, setScope] = useState<FindingScope>('week');
  const [status, setStatus] = useState<FindingStatus>('FAIL');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Finding | null>(null);
  const findings = useFindings({ scope, status, limit: PAGE_SIZE, offset });
  const close = useCallback(() => setSelected(null), []);

  const page = findings.data;

  return (
    <PageTransition>
      <div className="page-container" data-testid="page-compliance">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Document Compliance</h1>
          <p className="text-sm text-slate-500 mt-1">
            AI-assisted drawing review against ASME, OSHA and IBC excerpts · Blue Ridge LNG Terminal — Phase 2
          </p>
        </div>

        <SummaryTiles />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="section-header">Findings</h2>
          <div className="flex items-center gap-2">
            <Toggle
              label="Scope"
              value={scope}
              onChange={(v) => {
                setScope(v);
                setOffset(0);
              }}
              options={[
                { value: 'week', label: 'This week' },
                { value: 'all', label: 'All' },
              ]}
            />
            <Toggle
              label="Status"
              value={status}
              onChange={(v) => {
                setStatus(v);
                setOffset(0);
              }}
              options={[
                { value: 'FAIL', label: 'FAIL' },
                { value: 'REVIEW', label: 'REVIEW' },
              ]}
            />
          </div>
        </div>

        {findings.isLoading ? (
          <LoadingSkeleton type="table" rows={8} />
        ) : findings.isError ? (
          <ErrorAlert title="Findings unavailable" error={findings.error} onRetry={() => findings.refetch()} />
        ) : !page || page.total === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200">
            <EmptyState
              title={`No ${status} findings ${scope === 'week' ? 'this week' : 'on record'}`}
              description={scope === 'week' ? 'Widen the scope to all reviews, or ask the Co-Pilot about earlier weeks.' : 'Ask the Co-Pilot about drawing compliance.'}
              action={
                scope === 'week'
                  ? { label: 'Show all reviews', onClick: () => { setScope('all'); setOffset(0); } }
                  : { label: 'Ask the Co-Pilot', onClick: () => navigate('/') }
              }
            />
          </div>
        ) : (
          <FindingsTable
            items={page.items}
            total={page.total}
            limit={page.limit}
            offset={page.offset}
            onPage={setOffset}
            onSelect={setSelected}
            selectedId={selected?.finding_id}
            fetching={findings.isFetching}
          />
        )}
      </div>
      <FindingDrawer finding={selected} onClose={close} />
    </PageTransition>
  );
};

export default CompliancePage;
