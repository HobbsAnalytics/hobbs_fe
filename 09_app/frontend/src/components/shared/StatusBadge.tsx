import React from 'react';
import { motion } from 'framer-motion';

// RCM reference StatusBadge, construction vocabulary: bg-50 / text-700 / border-200 pills.
const statusStyles: Record<string, string> = {
  FAIL: 'bg-red-50 text-red-700 border-red-200',
  PASS: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  REVIEW: 'bg-amber-50 text-amber-700 border-amber-200',
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-slate-50 text-slate-600 border-slate-200',
  High: 'bg-red-50 text-red-700 border-red-200',
  Medium: 'bg-amber-50 text-amber-700 border-amber-200',
  Low: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  late: 'bg-red-50 text-red-700 border-red-200',
  due_today: 'bg-amber-50 text-amber-700 border-amber-200',
  OBO: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  SP: 'bg-blue-50 text-blue-700 border-blue-200',
};

interface StatusBadgeProps {
  status: string;
  label?: string;
  size?: 'sm' | 'md';
  animate?: boolean;
  className?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, size = 'sm', animate = false, className = '' }) => {
  const style = statusStyles[status] || 'bg-slate-50 text-slate-600 border-slate-200';
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';
  const badge = (
    <span className={`status-badge border font-medium whitespace-nowrap ${style} ${sizeClass} ${className}`}>
      {label ?? status}
    </span>
  );
  if (!animate) return badge;
  return (
    <motion.span initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="inline-block">
      {badge}
    </motion.span>
  );
};

export default StatusBadge;
