import React from 'react';
import type { ChatResult } from '../../types/api';

const MAX_ROWS = 50;
// The backend already strips these (API.md); dropping them here too keeps risk band-only even if that ever regresses.
const HIDDEN_COLUMN = /slip_probability/i;

function cell(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

/** Compact Genie result: at most 50 rows, with a "showing first N of M" note when truncated. */
const ResultTable: React.FC<{ result: ChatResult }> = ({ result }) => {
  const keep = result.columns.map((c, i) => ({ c, i })).filter(({ c }) => !HIDDEN_COLUMN.test(c));
  const rows = result.rows.slice(0, MAX_ROWS);
  if (keep.length === 0) return null;
  const truncated = result.truncated || result.row_count > rows.length;

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="card-subtitle">Result</span>
        <span className="text-[11px] text-slate-500">
          {truncated
            ? `Showing first ${rows.length} of ${result.row_count.toLocaleString('en-US')} rows`
            : `${result.row_count.toLocaleString('en-US')} row${result.row_count === 1 ? '' : 's'}`}
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-slate-500 border border-slate-200 rounded-lg px-3 py-2 bg-slate-50">The query returned no rows.</p>
      ) : (
        <div className="max-h-64 overflow-auto border border-slate-200 rounded-lg">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                {keep.map(({ c }) => (
                  <th key={c} className="px-2.5 py-1.5 text-left font-semibold text-slate-500 whitespace-nowrap">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r, ri) => (
                <tr key={ri} className="table-row-hover">
                  {keep.map(({ c, i }) => (
                    <td key={c} className={`px-2.5 py-1.5 text-slate-700 whitespace-nowrap ${/_id$/i.test(c) ? 'font-mono' : ''}`}>
                      {cell(Array.isArray(r) ? r[i] : undefined)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ResultTable;
