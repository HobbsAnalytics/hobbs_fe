import React, { useEffect, useRef, useState } from 'react';
import { Document, Page } from 'react-pdf';
import '../../lib/pdfWorker';
import BBoxOverlay, { type PageSize } from './BBoxOverlay';
import ErrorAlert from '../shared/ErrorAlert';
import { Pulse } from '../shared/LoadingSkeleton';
import type { Finding } from '../../types/api';

interface PdfViewerProps {
  file: string;
  /** 0-based page index (same convention as finding.page_num). */
  pageIndex: number;
  findings: Finding[];
  selectedId: string | null;
  onSelect: (f: Finding) => void;
  onNumPages: (n: number) => void;
}

const MAX_WIDTH = 1100;

/** react-pdf page plus one BBoxOverlay per finding on that page. Text/annotation layers are off: the overlay is the
 *  only thing drawn over the canvas. */
const PdfViewer: React.FC<PdfViewerProps> = ({ file, pageIndex, findings, selectedId, onSelect, onNumPages }) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [pageSize, setPageSize] = useState<PageSize | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const measure = () => {
      const w = Math.floor(el.clientWidth);
      if (w > 0) setWidth(Math.min(w, MAX_WIDTH));
    };
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setPageSize(null);
  }, [pageIndex, file]);

  useEffect(() => {
    if (pageSize && selectedRef.current) selectedRef.current.scrollIntoView?.({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  }, [selectedId, pageSize]);

  if (loadError) {
    return (
      <ErrorAlert
        title="The PDF couldn't be loaded"
        message="The drawing file may be missing from the Volume, or your session expired."
        onRetry={() => {
          setLoadError(false);
          setAttempt((a) => a + 1);
        }}
      />
    );
  }

  const onPage = findings.filter((f) => f.page_num === pageIndex && Array.isArray(f.bbox) && f.bbox.length === 4);

  return (
    <div ref={wrapRef} className="w-full">
      <Document
        key={attempt}
        file={file}
        onLoadSuccess={({ numPages }) => onNumPages(numPages)}
        onLoadError={() => setLoadError(true)}
        loading={<Pulse className="w-full h-[600px] rounded-lg" />}
        error={<span />}
      >
        <div className="relative inline-block shadow-sm border border-slate-200 bg-white">
          <Page
            pageNumber={pageIndex + 1}
            width={width}
            renderTextLayer={false}
            renderAnnotationLayer={false}
            loading={<Pulse className="w-full h-[600px]" style={{ width }} />}
            onLoadSuccess={(p) => setPageSize({ w: width, h: (width * p.originalHeight) / p.originalWidth })}
          />
          {pageSize && (
            <div className="absolute inset-0" style={{ width: pageSize.w, height: pageSize.h }} data-testid="overlay-layer">
              {onPage.map((f) => (
                <BBoxOverlay
                  key={f.finding_id}
                  ref={f.finding_id === selectedId ? selectedRef : undefined}
                  page={pageSize}
                  bbox={f.bbox!}
                  source={f.bbox_source}
                  selected={f.finding_id === selectedId}
                  label={f.citation ?? undefined}
                  onClick={() => onSelect(f)}
                />
              ))}
            </div>
          )}
        </div>
      </Document>
    </div>
  );
};

export default PdfViewer;
