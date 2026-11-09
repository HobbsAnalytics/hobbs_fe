import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { Finding } from '../../types/api';
import StatusBadge from '../shared/StatusBadge';
import { drawingCodes } from '../../lib/format';
import { drawingHref } from '../../lib/api';

interface FindingsTableProps {
  items: Finding[];
  total: number;
  limit: number;
  offset: number;
  onPage: (offset: number) => void;
  onSelect: (f: Finding) => void;
  selectedId?: string | null;
  fetching?: boolean;
}

/** Server-paginated findings (limit/offset/total from /api/compliance/findings); one page in the DOM at a time. */
const FindingsTable: React.FC<FindingsTableProps> = ({ items, total, limit, offset, onPage, onSelect, selectedId, fetching }) => {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + items.length, total);
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className={`overflow-x-auto transition-opacity ${fetching ? 'opacity-60' : ''}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50/80 text-left">
              {['Drawing', 'Discipline', 'Type', 'Citation', 'Severity', 'Reason', ''].map((h) => (
                <th key={h} className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((f) => {
              const codes = drawingCodes(f.drawing_id);
              return (
                <tr
                  key={f.finding_id}
                  onClick={() => onSelect(f)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelect(f);
                    }
                  }}
                  tabIndex={0}
                  aria-selected={selectedId === f.finding_id}
                  className={`table-row-hover cursor-pointer focus:outline-none focus:bg-emerald-50/60 ${selectedId === f.finding_id ? 'bg-emerald-50/60' : ''}`}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="font-mono text-xs font-semibold text-slate-800">{f.drawing_id}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{codes.discipline}</td>
                  <td className="px-4 py-3 text-slate-600 whitespace-nowrap">{codes.drawingType}</td>
                  <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-slate-700">{f.citation ?? '—'}</td>
                  <td className="px-4 py-3">{f.severity ? <StatusBadge status={f.severity} /> : '—'}</td>
                  <td className="px-4 py-3 text-slate-600 max-w-md">
                    <span className="line-clamp-2">{f.reason ?? '—'}</span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <Link
                      to={drawingHref(f.drawing_id, f.page_num, f.finding_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="text-emerald-600 hover:text-emerald-700 font-medium text-xs"
                    >
                      Open PDF →
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-xs text-slate-500">
        <span>
          {from}–{to} of {total.toLocaleString('en-US')}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Previous page"
            disabled={!hasPrev || fetching}
            onClick={() => onPage(Math.max(0, offset - limit))}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            aria-label="Next page"
            disabled={!hasNext || fetching}
            onClick={() => onPage(offset + limit)}
            className="p-1.5 rounded-md hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default FindingsTable;
