import React from 'react';
import { AlertTriangle, RotateCw } from 'lucide-react';

interface ErrorAlertProps {
  title?: string;
  error?: unknown;
  message?: string;
  onRetry?: () => void;
  compact?: boolean;
}

function toMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong loading this data.';
}

/** Inline error: never a blank panel, never a stack trace. ApiError messages are already user-safe sentences. */
const ErrorAlert: React.FC<ErrorAlertProps> = ({ title, error, message, onRetry, compact }) => (
  <div
    role="alert"
    className={`flex items-start gap-2.5 rounded-lg border border-red-200 bg-red-50 text-red-700 ${compact ? 'px-3 py-2 text-xs' : 'px-4 py-3 text-sm'}`}
  >
    <AlertTriangle size={compact ? 14 : 16} className="flex-shrink-0 mt-0.5" />
    <div className="flex-1 min-w-0">
      {title && <p className="font-semibold">{title}</p>}
      <p className={title ? 'mt-0.5 text-red-600' : ''}>{message ?? toMessage(error)}</p>
    </div>
    {onRetry && (
      <button
        type="button"
        onClick={onRetry}
        className="flex items-center gap-1 text-xs font-medium text-red-700 hover:text-red-800 px-2 py-1 rounded-md hover:bg-red-100 transition-colors flex-shrink-0"
      >
        <RotateCw size={12} /> Retry
      </button>
    )}
  </div>
);

export default ErrorAlert;
