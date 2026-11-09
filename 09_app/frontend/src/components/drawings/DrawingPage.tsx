import React, { useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Crosshair } from 'lucide-react';
import PageTransition from '../layout/PageTransition';
import PdfViewer from './PdfViewer';
import StatusBadge from '../shared/StatusBadge';
import ErrorAlert from '../shared/ErrorAlert';
import EmptyState from '../shared/EmptyState';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import { useDrawing } from '../../hooks/useCompliance';
import { pdfUrl } from '../../lib/api';
import { drawingCodes, formatShortDate, titleCase } from '../../lib/format';
import { bboxSourceLabel } from '../compliance/bboxSource';
import type { Finding } from '../../types/api';

/**
 * `/drawings/:id?page=<0-based page_num>&finding=<finding_id>`. The PDF comes from /api/drawings/:id/pdf, the findings
 * from /api/drawings/:id. `page` uses the API's 0-based page_num; the UI shows 1-based "Sheet n".
 */
const DrawingPage: React.FC = () => {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const detail = useDrawing(id);
  const [numPages, setNumPages] = useState<number | null>(null);

  const findings = detail.data?.findings ?? [];
  const selectedId = sp.get('finding');
  const selected = findings.find((f) => f.finding_id === selectedId) ?? null;
  const rawPage = Number.parseInt(sp.get('page') ?? '', 10);
  let pageIndex = Number.isFinite(rawPage) && rawPage >= 0 ? rawPage : (selected?.page_num ?? 0);
  if (numPages != null && pageIndex > numPages - 1) pageIndex = Math.max(0, numPages - 1);

  const goPage = (p: number) => {
    const next = new URLSearchParams(sp);
    next.set('page', String(p));
    setSp(next, { replace: true });
  };
  const select = (f: Finding) => {
    const next = new URLSearchParams(sp);
    if (f.page_num != null) next.set('page', String(f.page_num));
    next.set('finding', f.finding_id);
    setSp(next, { replace: true });
  };

  // A drawing with no violations still carries one PASS sentinel row; only FAIL/REVIEW rows count as findings.
  const violations = useMemo(() => findings.filter((f) => f.status === 'FAIL' || f.status === 'REVIEW'), [findings]);
  const sorted = useMemo(
    () => [...violations].sort((a, b) => (a.status === b.status ? a.finding_id.localeCompare(b.finding_id) : a.status === 'FAIL' ? -1 : 1)),
    [violations],
  );
  const codes = drawingCodes(id);

  return (
    <PageTransition>
      <div className="page-container" data-testid="page-drawing">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link to="/compliance" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-emerald-700 mb-1">
              <ArrowLeft size={12} /> Doc Compliance
            </Link>
            <h1 className="text-2xl font-bold text-slate-900 font-mono">{id}</h1>
            {detail.data && (
              <p className="text-sm text-slate-500 mt-1">
                {titleCase(detail.data.discipline) !== '—' ? titleCase(detail.data.discipline) : codes.discipline} ·{' '}
                {detail.data.drawing_type ?? codes.drawingType} · Rev {detail.data.revision ?? '—'} · last reviewed{' '}
                {formatShortDate(detail.data.latest_review_date)}
              </p>
            )}
          </div>
          {detail.data?.latest_status && <StatusBadge status={detail.data.latest_status} size="md" />}
        </div>

        {detail.isLoading ? (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5">
            <LoadingSkeleton type="card" />
            <LoadingSkeleton type="list" rows={4} />
          </div>
        ) : detail.isError ? (
          <ErrorAlert title={`Drawing ${id} couldn't be opened`} error={detail.error} onRetry={() => detail.refetch()} />
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-5 items-start">
            <div className="chart-container min-w-0">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label="Previous sheet"
                    disabled={pageIndex <= 0}
                    onClick={() => goPage(pageIndex - 1)}
                    className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="text-xs text-slate-600 tabular-nums" data-testid="sheet-label">
                    Sheet {pageIndex + 1}
                    {numPages != null ? ` of ${numPages}` : ''}
                  </span>
                  <button
                    type="button"
                    aria-label="Next sheet"
                    disabled={numPages == null || pageIndex >= numPages - 1}
                    onClick={() => goPage(pageIndex + 1)}
                    className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
                <span className="text-[11px] text-slate-400">Dashed outline = approximate location</span>
              </div>
              <div className="overflow-auto max-h-[calc(100vh-240px)] bg-slate-100 rounded-lg p-2">
                <PdfViewer
                  file={pdfUrl(id)}
                  pageIndex={pageIndex}
                  findings={findings}
                  selectedId={selectedId}
                  onSelect={select}
                  onNumPages={setNumPages}
                />
              </div>
            </div>

            <aside className="rail-card" aria-label="Findings on this drawing">
              <div className="rail-title">Findings ({violations.length})</div>
              {sorted.length === 0 ? (
                <EmptyState compact title="No violations found" description="It passed review. Ask the Co-Pilot about related drawings." />
              ) : (
                <ul className="space-y-2">
                  {sorted.map((f) => {
                    const active = f.finding_id === selectedId;
                    return (
                      <li key={f.finding_id}>
                        <button
                          type="button"
                          onClick={() => select(f)}
                          aria-pressed={active}
                          className={`w-full text-left p-3 rounded-lg border transition-colors ${
                            active ? 'border-red-300 bg-red-50/60' : 'border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <StatusBadge status={f.status} />
                            {f.severity && <StatusBadge status={f.severity} />}
                            {f.citation && <span className="font-mono text-[11px] text-slate-700">{f.citation}</span>}
                          </div>
                          <p className="text-xs text-slate-700 mt-1.5 line-clamp-3">{f.reason ?? '—'}</p>
                          <p className="text-[11px] text-slate-500 mt-1.5 flex items-center gap-1">
                            <Crosshair size={11} />
                            {f.page_num != null ? `Sheet ${f.page_num + 1} · ` : ''}
                            {bboxSourceLabel(f.bbox_source)}
                          </p>
                          {active && f.evidence_text && (
                            <p className="mt-1.5 font-mono text-[11px] text-slate-600 bg-white border border-slate-200 rounded px-2 py-1">
                              {f.evidence_text}
                            </p>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
              <p className="mt-3 text-[11px] text-slate-400 italic">AI-assisted review — verify on the drawing before action.</p>
            </aside>
          </div>
        )}
      </div>
    </PageTransition>
  );
};

export default DrawingPage;
