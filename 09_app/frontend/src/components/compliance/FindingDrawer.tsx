import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { BookOpen, Crosshair, X } from 'lucide-react';
import type { Finding } from '../../types/api';
import StatusBadge from '../shared/StatusBadge';
import CitationPanel from '../copilot/CitationPanel';
import { drawingHref } from '../../lib/api';
import { drawingCodes, formatShortDate } from '../../lib/format';
import { bboxSourceLabel } from './bboxSource';

/** Slide-over with one finding: reason, citation (+ code excerpt lookup), evidence text and the bbox provenance. */
const FindingDrawer: React.FC<{ finding: Finding | null; onClose: () => void }> = ({ finding, onClose }) => {
  const [showCitation, setShowCitation] = useState(false);

  useEffect(() => {
    setShowCitation(false);
  }, [finding?.finding_id]);

  useEffect(() => {
    if (!finding) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [finding, onClose]);

  return (
    <AnimatePresence>
      {finding && (
        <>
          <motion.div
            key="scrim"
            className="fixed inset-0 bg-slate-900/20 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            key="drawer"
            role="dialog"
            aria-modal="true"
            aria-label={`Finding ${finding.finding_id}`}
            className="fixed right-0 top-0 h-screen w-full max-w-md bg-white border-l border-slate-200 shadow-xl z-50 flex flex-col"
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 40, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          >
            <div className="px-5 h-16 flex items-center justify-between border-b border-slate-100 flex-shrink-0">
              <div className="min-w-0">
                <p className="font-mono text-sm font-semibold text-slate-900 truncate">{finding.drawing_id}</p>
                <p className="text-[11px] text-slate-500 font-mono">{finding.finding_id}</p>
              </div>
              <button type="button" onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={finding.status} />
                {finding.severity && <StatusBadge status={finding.severity} />}
                <span className="text-xs text-slate-500">
                  {drawingCodes(finding.drawing_id).discipline} · {drawingCodes(finding.drawing_id).drawingType} · reviewed{' '}
                  {formatShortDate(finding.review_date)}
                </span>
              </div>

              <section>
                <h4 className="card-subtitle mb-1.5">Reason</h4>
                <p className="text-slate-700 leading-relaxed">{finding.reason ?? '—'}</p>
              </section>

              <section>
                <h4 className="card-subtitle mb-1.5">Citation</h4>
                {finding.citation ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setShowCitation(!showCitation)}
                      aria-expanded={showCitation}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-200 text-xs font-mono text-slate-700 hover:border-emerald-300"
                    >
                      <BookOpen size={12} aria-hidden="true" />
                      {finding.citation}
                      <span className="font-sans text-slate-400">{showCitation ? '· hide excerpt' : '· look up'}</span>
                    </button>
                    {showCitation && <CitationPanel label={finding.citation} />}
                  </>
                ) : (
                  <p className="text-slate-500">No citation recorded.</p>
                )}
              </section>

              <section>
                <h4 className="card-subtitle mb-1.5">Evidence text</h4>
                {finding.evidence_text ? (
                  <pre className="font-mono text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 whitespace-pre-wrap text-slate-700">
                    {finding.evidence_text}
                  </pre>
                ) : (
                  <p className="text-slate-500">No evidence text recorded.</p>
                )}
              </section>

              <section>
                <h4 className="card-subtitle mb-1.5">Location</h4>
                <p className="flex items-center gap-1.5 text-slate-700">
                  <Crosshair size={14} className="text-slate-400" />
                  {bboxSourceLabel(finding.bbox_source)}
                </p>
                {finding.page_num != null && <p className="text-xs text-slate-500 mt-1">Sheet {finding.page_num + 1}</p>}
              </section>

              <p className="text-[11px] text-slate-400 italic">AI-assisted review — an engineer confirms every finding before action.</p>
            </div>

            <div className="p-4 border-t border-slate-100 flex-shrink-0">
              <Link
                to={drawingHref(finding.drawing_id, finding.page_num, finding.finding_id)}
                className="block text-center w-full px-4 py-2.5 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-white text-sm font-medium hover:opacity-95"
              >
                Open PDF →
              </Link>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default FindingDrawer;
