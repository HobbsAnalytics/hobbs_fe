import React from 'react';
import { motion } from 'framer-motion';

export type Tone = 'good' | 'warn' | 'bad' | 'neutral';

interface MetricCardProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  icon: React.ReactNode;
  tone?: Tone;
  index?: number;
  /** "compact" is the mockup's kpi-mini strip card; "full" is the RCM metric-card. */
  variant?: 'compact' | 'full';
  testId?: string;
  dataKpi?: string;
}

const toneClass: Record<Tone, string> = {
  good: 'kpi-icon-good',
  warn: 'kpi-icon-warn',
  bad: 'kpi-icon-bad',
  neutral: '',
};

const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  sub,
  icon,
  tone = 'neutral',
  index = 0,
  variant = 'compact',
  testId,
  dataKpi,
}) => {
  const motionProps = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, delay: index * 0.06, ease: [0.4, 0, 0.2, 1] },
    whileHover: { y: -2, boxShadow: '0 8px 30px rgba(0,0,0,0.08)' },
  };
  if (variant === 'full') {
    return (
      <motion.div {...motionProps} className="metric-card group" data-testid={testId} data-kpi={dataKpi}>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-500">{label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
            {sub && <p className="text-xs text-slate-500 mt-1.5">{sub}</p>}
          </div>
          <div className={`kpi-icon w-10 h-10 rounded-xl ${toneClass[tone]}`}>{icon}</div>
        </div>
      </motion.div>
    );
  }
  return (
    <motion.div {...motionProps} className="kpi-mini" data-testid={testId} data-kpi={dataKpi}>
      <div className={`kpi-icon ${toneClass[tone]}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value}</div>
        {sub && (
          <div className="kpi-sub truncate" title={typeof sub === 'string' ? sub : undefined}>
            {sub}
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default MetricCard;
