import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, FileText } from 'lucide-react';
import type { GroupedSources } from '../../hooks/useChat';
import { DRAWING_ID_RE, drawingHref } from '../../lib/api';
import CitationPanel from './CitationPanel';

/** Drawings (grouped by drawing_id, one entry per drawing) open the PDF viewer at the first finding; citation chips
 *  open the code-excerpt panel. */
const SourcesCard: React.FC<{ sources: GroupedSources }> = ({ sources }) => {
  const [openCitation, setOpenCitation] = useState<string | null>(null);
  const drawings = sources.drawings.filter((d) => DRAWING_ID_RE.test(d.drawing_id));
  if (drawings.length === 0 && sources.citations.length === 0) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2.5">
      {drawings.length > 0 && (
        <>
          <div className="card-subtitle mb-2">Drawings from Volume</div>
          <div className="space-y-1.5">
            {drawings.map((d) => {
              const first = d.findings[0];
              const cites = Array.from(new Set(d.findings.map((f) => f.citation).filter(Boolean)));
              const n = d.findings.length;
              return (
                <Link
                  key={d.drawing_id}
                  to={drawingHref(d.drawing_id, first?.page_num, first?.finding_id)}
                  data-testid="drawing-chip"
                  className="flex justify-between items-center px-2.5 py-2 bg-slate-50 border border-slate-100 rounded-md text-xs hover:border-emerald-300 hover:bg-emerald-50/50 transition-colors"
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <FileText size={14} className={n > 0 ? 'text-red-500 flex-shrink-0' : 'text-slate-400 flex-shrink-0'} />
                    <span className="min-w-0">
                      <span className="block font-mono font-semibold text-slate-800">{d.drawing_id}</span>
                      <span className="block text-[11px] text-slate-500 truncate">
                        {n > 0
                          ? `${n} finding${n === 1 ? '' : 's'}${cites.length ? ` · ${cites.join(', ')}` : ''}${first?.page_num != null ? ` · sheet ${first.page_num + 1}` : ''}`
                          : 'No FAIL finding on record'}
                      </span>
                    </span>
                  </span>
                  <span className="text-emerald-600 font-medium flex-shrink-0 ml-2">Open PDF →</span>
                </Link>
              );
            })}
          </div>
        </>
      )}
      {sources.citations.length > 0 && (
        <div className={drawings.length > 0 ? 'mt-2.5' : ''}>
          <div className="card-subtitle mb-1.5">Code citations</div>
          <div className="flex flex-wrap gap-1.5">
            {sources.citations.map((c) => (
              <button
                type="button"
                key={c.label}
                onClick={() => setOpenCitation(openCitation === c.label ? null : c.label)}
                aria-expanded={openCitation === c.label}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full border text-[11px] font-mono transition-colors ${
                  openCitation === c.label
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-700'
                    : 'bg-white border-slate-200 text-slate-700 hover:border-emerald-300'
                }`}
              >
                <BookOpen size={11} aria-hidden="true" />
                {c.label}
              </button>
            ))}
          </div>
          {openCitation && <CitationPanel label={openCitation} onClose={() => setOpenCitation(null)} />}
        </div>
      )}
    </div>
  );
};

export default SourcesCard;
