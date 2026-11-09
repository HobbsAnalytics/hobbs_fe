import React from 'react';

interface LoadingSkeletonProps {
  type: 'card' | 'table' | 'text' | 'metric' | 'kpi' | 'list';
  count?: number;
  rows?: number;
}

export const Pulse: React.FC<{ className?: string; style?: React.CSSProperties }> = ({ className = '', style }) => (
  <div className={`animate-pulse bg-slate-200 rounded ${className}`} style={style} />
);

const MetricSkeleton: React.FC = () => (
  <div className="metric-card">
    <div className="flex items-start justify-between">
      <div className="flex-1 space-y-3">
        <Pulse className="h-4 w-24" />
        <Pulse className="h-8 w-20" />
        <Pulse className="h-4 w-16" />
      </div>
      <Pulse className="w-10 h-10 rounded-xl" />
    </div>
  </div>
);

const KpiSkeleton: React.FC = () => (
  <div className="kpi-mini" data-testid="kpi-skeleton">
    <Pulse className="w-9 h-9 rounded-[10px] flex-shrink-0" />
    <div className="flex-1 space-y-2">
      <Pulse className="h-3 w-16" />
      <Pulse className="h-5 w-20" />
      <Pulse className="h-3 w-28" />
    </div>
  </div>
);

const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden" data-testid="table-skeleton">
    <div className="px-5 py-3 border-b border-slate-100">
      <Pulse className="h-4 w-32" />
    </div>
    <div className="divide-y divide-slate-100">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-5 py-3 flex items-center gap-4">
          <Pulse className="h-4 w-28" />
          <Pulse className="h-4 w-20" />
          <Pulse className="h-4 w-24" />
          <Pulse className="h-6 w-16 rounded-full" />
          <Pulse className="h-4 flex-1" />
        </div>
      ))}
    </div>
  </div>
);

const CardSkeleton: React.FC = () => (
  <div className="bg-white rounded-xl border border-slate-200 p-5">
    <Pulse className="h-5 w-32 mb-3" />
    <Pulse className="h-4 w-full mb-2" />
    <Pulse className="h-4 w-3/4" />
  </div>
);

const TextSkeleton: React.FC = () => (
  <div className="space-y-2">
    <Pulse className="h-4 w-full" />
    <Pulse className="h-4 w-5/6" />
    <Pulse className="h-4 w-4/6" />
  </div>
);

const ListSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => (
  <div className="space-y-2" data-testid="list-skeleton">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex items-center gap-2">
        <Pulse className="h-4 w-14" />
        <Pulse className="h-4 flex-1" />
        <Pulse className="h-5 w-12 rounded-full" />
      </div>
    ))}
  </div>
);

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ type, count = 1, rows }) => {
  const one = () => {
    switch (type) {
      case 'metric':
        return <MetricSkeleton />;
      case 'kpi':
        return <KpiSkeleton />;
      case 'table':
        return <TableSkeleton rows={rows} />;
      case 'text':
        return <TextSkeleton />;
      case 'list':
        return <ListSkeleton rows={rows} />;
      default:
        return <CardSkeleton />;
    }
  };
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <React.Fragment key={i}>{one()}</React.Fragment>
      ))}
    </>
  );
};

export default LoadingSkeleton;
