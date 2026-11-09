import React, { useState } from 'react';
import { useScheduleOverdue } from '../../hooks/useProjectData';
import StatusBadge from '../shared/StatusBadge';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';

const COLLAPSED = 5;

/** "Late or due today" from GET /api/schedule/overdue (status late | due_today). */
const LateMilestonesCard: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useScheduleOverdue();
  const [expanded, setExpanded] = useState(false);
  const items = data?.items ?? [];
  const shown = expanded ? items : items.slice(0, COLLAPSED);

  return (
    <div className="rail-card" data-testid="late-card">
      <div className="flex items-baseline justify-between">
        <div className="rail-title">Late or due today</div>
        {data && data.total > 0 && (
          <span className="text-[10px] text-slate-400">
            {data.late} late · {data.due_today} due today
          </span>
        )}
      </div>
      {isLoading ? (
        <LoadingSkeleton type="list" rows={3} />
      ) : isError ? (
        <ErrorAlert compact error={error} onRetry={() => refetch()} />
      ) : items.length === 0 ? (
        <EmptyState compact title="Nothing late or due today" description="Ask the Co-Pilot what is due this week." />
      ) : (
        <>
          <ul className="divide-y divide-slate-100">
            {shown.map((m) => (
              <li key={m.milestone_id} className="py-2 flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <span className="font-mono text-xs font-semibold text-slate-800">{m.milestone_id}</span>
                  <p className="text-xs text-slate-600 truncate" title={m.name}>{m.name}</p>
                </div>
                <StatusBadge status={m.status} label={m.status === 'late' ? `${m.days_late}d late` : 'Due today'} />
              </li>
            ))}
          </ul>
          {items.length > COLLAPSED && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="mt-1 text-xs font-medium text-emerald-700 hover:text-emerald-800"
            >
              {expanded ? 'Show fewer' : `Show all ${items.length}`}
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default LateMilestonesCard;
