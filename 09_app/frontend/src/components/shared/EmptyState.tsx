import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: { label: string; onClick: () => void };
  compact?: boolean;
}

/** No data is not an error: say so, and offer the next step. */
const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon, action, compact }) => (
  <div
    className={`flex flex-col items-center justify-center text-center ${compact ? 'py-4 px-2' : 'py-10 px-6'}`}
    data-testid="empty-state"
  >
    <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3">
      {icon ?? <Inbox size={18} />}
    </div>
    <p className="text-sm font-medium text-slate-700">{title}</p>
    {description && <p className="text-xs text-slate-500 mt-1 max-w-xs">{description}</p>}
    {action && (
      <button
        type="button"
        onClick={action.onClick}
        className="mt-3 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-1.5 hover:bg-emerald-100 transition-colors"
      >
        {action.label}
      </button>
    )}
  </div>
);

export default EmptyState;
