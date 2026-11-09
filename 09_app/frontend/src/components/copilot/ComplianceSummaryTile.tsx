import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useComplianceSummary } from '../../hooks/useProjectData';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';
import { formatNumber, formatShortDate } from '../../lib/format';

const ComplianceSummaryTile: React.FC = () => {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useComplianceSummary();

  return (
    <div className="rail-card" data-testid="compliance-tile">
      <div className="flex items-baseline justify-between">
        <div className="rail-title">Document Compliance</div>
        {data && (
          <span className="text-[10px] text-slate-400">
            {formatShortDate(data.week.start)} – {formatShortDate(data.week.end)}
          </span>
        )}
      </div>
      {isLoading ? (
        <LoadingSkeleton type="list" rows={2} />
      ) : isError ? (
        <ErrorAlert compact error={error} onRetry={() => refetch()} />
      ) : !data || data.reviewed === 0 ? (
        <EmptyState compact title="No drawings reviewed this week" description="Reviews run nightly; check back tomorrow." />
      ) : (
        <>
          <div className="flex gap-3 mb-2.5 p-2.5 bg-slate-50 rounded-lg">
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-slate-900">{formatNumber(data.reviewed)}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-[0.04em] mt-0.5">reviewed</div>
            </div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-emerald-600">{formatNumber(data.passed)}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-[0.04em] mt-0.5">passed</div>
            </div>
            <div className="flex-1 text-center">
              <div className="text-xl font-bold text-red-600">{formatNumber(data.failed)}</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-[0.04em] mt-0.5">failed</div>
            </div>
          </div>
          <button type="button" className="action-btn" onClick={() => navigate('/compliance')}>
            Dig into failed drawings
            <span className="action-sub">Findings, citations and highlighted PDFs</span>
          </button>
        </>
      )}
    </div>
  );
};

export default ComplianceSummaryTile;
