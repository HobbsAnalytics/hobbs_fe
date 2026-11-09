import React from 'react';
import { useRiskTop } from '../../hooks/useProjectData';
import StatusBadge from '../shared/StatusBadge';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';
import { formatShortDate } from '../../lib/format';

// Risk is communicated by band only (High / Medium / Low) and rank. Never a percentage or probability: the API does not
// return slip_probability, and this card renders only the named fields below, so an extra field can't leak through.
const RiskForecastCard: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useRiskTop(3);

  return (
    <div className="rail-card" data-testid="risk-card">
      <div className="flex items-baseline justify-between">
        <div className="rail-title">Schedule Risk</div>
        <span className="text-[10px] text-slate-400">ML forecast · by band</span>
      </div>
      {isLoading ? (
        <LoadingSkeleton type="list" rows={3} />
      ) : isError ? (
        <ErrorAlert compact error={error} onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState compact title="No milestones in the risk forecast" description="The forecast refreshes daily." />
      ) : (
        <>
          <div className="flex gap-1.5 mb-2.5 text-[11px] text-slate-600">
            <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">{data.risk_counts.High} High</span>
            <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">{data.risk_counts.Medium} Medium</span>
            <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">{data.risk_counts.Low} Low</span>
          </div>
          <ul className="divide-y divide-slate-100">
            {data.items.map((r) => (
              <li key={r.milestone_id} className="py-2 flex items-start gap-2.5">
                <span className="text-[11px] text-slate-400 w-4 pt-0.5">{r.risk_rank}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-slate-800">{r.milestone_id}</span>
                    <StatusBadge status={r.risk_band} />
                  </div>
                  <p className="text-xs text-slate-600 truncate mt-0.5" title={r.name}>{r.name}</p>
                  <p className="text-[11px] text-slate-400">Planned end {formatShortDate(r.planned_end)}</p>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

export default RiskForecastCard;
