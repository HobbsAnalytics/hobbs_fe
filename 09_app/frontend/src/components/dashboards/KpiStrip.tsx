import React from 'react';
import { AlertCircle, Clock, DollarSign, ShieldCheck } from 'lucide-react';
import { useKpis } from '../../hooks/useKpis';
import MetricCard, { type Tone } from '../shared/MetricCard';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';
import { formatNumber, formatSignedPct, formatUsdCompact, sentenceCase } from '../../lib/format';
import type { KpiToday } from '../../types/api';

// Semantic tone rules (presentation only; every value comes from GET /api/kpi/today):
//  schedule: on_track -> good, at_risk -> warn, anything else -> bad
//  budget:   EAC <= 0% -> good, <= 5% -> warn, > 5% -> bad
//  safety:   0 recordables in 28 days -> good, otherwise bad
//  NCRs:     0 open -> good, otherwise bad (mockup)
function scheduleTone(s: string): Tone {
  if (s === 'on_track') return 'good';
  if (s === 'at_risk') return 'warn';
  return 'bad';
}

function budgetTone(pct: number): Tone {
  if (pct <= 0) return 'good';
  if (pct <= 5) return 'warn';
  return 'bad';
}

export function kpiCards(k: KpiToday) {
  const s = k.schedule;
  const slipped = s.slipped_milestone_id && s.slipped_days ? ` · ${s.slipped_milestone_id} ${s.slipped_days}d late` : '';
  return [
    {
      id: 'schedule',
      label: 'Schedule',
      value: sentenceCase(s.status),
      sub: `${s.milestones_hit} of ${s.milestones_total} key milestones hit${slipped}`,
      icon: <Clock size={18} />,
      tone: scheduleTone(s.status),
    },
    {
      id: 'budget',
      label: 'Budget (EAC)',
      value: formatSignedPct(k.budget.eac_pct),
      sub: `${formatUsdCompact(k.budget.overrun_usd)} over ${formatUsdCompact(k.budget.total_usd)} budget`,
      icon: <DollarSign size={18} />,
      tone: budgetTone(k.budget.eac_pct),
    },
    {
      id: 'safety',
      label: 'Safety',
      value: `${k.safety.trir_28d.toFixed(1)} TRIR`,
      sub: `${formatNumber(k.safety.days_without_incident)} days without incident`,
      icon: <ShieldCheck size={18} />,
      tone: (k.safety.recordables_28d === 0 ? 'good' : 'bad') as Tone,
    },
    {
      id: 'ncrs',
      label: 'Open NCRs',
      value: formatNumber(k.open_ncrs.total),
      sub: `${k.open_ncrs.compliance} compliance · ${k.open_ncrs.workmanship} workmanship`,
      icon: <AlertCircle size={18} />,
      tone: (k.open_ncrs.total === 0 ? 'good' : 'bad') as Tone,
    },
  ];
}

const KpiStrip: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useKpis();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3" aria-busy="true" aria-label="Loading KPIs">
        <LoadingSkeleton type="kpi" count={4} />
      </div>
    );
  }
  if (isError) return <ErrorAlert title="KPIs unavailable" error={error} onRetry={() => refetch()} />;
  if (!data) {
    return (
      <div className="rail-card">
        <EmptyState compact title="No KPI snapshot for today yet" description="The KPI job runs daily. Check back after the next refresh." />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3" data-testid="kpi-strip">
      {kpiCards(data).map((c, i) => (
        <MetricCard
          key={c.id}
          index={i}
          label={c.label}
          value={c.value}
          sub={c.sub}
          icon={c.icon}
          tone={c.tone}
          testId="kpi-card"
          dataKpi={c.id}
        />
      ))}
    </div>
  );
};

export default KpiStrip;
