import React from 'react';
import { BookOpen, X } from 'lucide-react';
import { useCitation } from '../../hooks/useProjectData';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';

/** Small panel with the code excerpt for a citation label, from GET /api/citations/{label}. */
const CitationPanel: React.FC<{ label: string; onClose?: () => void }> = ({ label, onClose }) => {
  const { data, isLoading, isError, error, refetch } = useCitation(label);

  return (
    <div className="mt-2 border border-slate-200 rounded-lg bg-white p-3 text-xs" data-testid="citation-panel">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 font-semibold text-slate-800">
          <BookOpen size={13} className="text-emerald-600" />
          <span className="font-mono">{label}</span>
        </div>
        {onClose && (
          <button type="button" onClick={onClose} aria-label="Close citation" className="text-slate-400 hover:text-slate-600">
            <X size={13} />
          </button>
        )}
      </div>
      {isLoading ? (
        <div className="mt-2">
          <LoadingSkeleton type="text" />
        </div>
      ) : isError ? (
        <div className="mt-2">
          <ErrorAlert compact error={error} onRetry={() => refetch()} />
        </div>
      ) : data ? (
        <div className="mt-1.5 space-y-1.5">
          {data.title && <p className="font-medium text-slate-700">{data.title}</p>}
          <p className="text-slate-600 leading-relaxed">{data.text}</p>
          <p className="text-[10px] text-slate-400">
            {data.source}
            {data.is_paraphrase ? ' · paraphrased excerpt, not the code text' : ''}
          </p>
          {data.related?.length > 0 && (
            <p className="text-[10px] text-slate-500">Related: {data.related.map((r) => r.citation_label).join(', ')}</p>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default CitationPanel;
