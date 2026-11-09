import React, { useState } from 'react';
import { ChevronDown, Copy, Check } from 'lucide-react';

/** Collapsible "Generated SQL" card: the exact query Genie ran, never hidden. */
const GeneratedSqlCard: React.FC<{ sql: string }> = ({ sql }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="mt-3 border border-slate-200 rounded-lg bg-slate-50 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="flex items-center gap-2 text-[11px] text-slate-600 font-semibold uppercase tracking-[0.04em]">
          <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded-[10px] text-[10px] font-bold">SQL</span>
          Generated SQL
          <span className="normal-case font-normal tracking-normal text-slate-400">{open ? '— click to hide' : '— click to view'}</span>
        </span>
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="relative">
          <pre
            data-testid="sql-body"
            className="px-3 py-2.5 bg-slate-900 text-slate-300 font-mono text-[11.5px] leading-relaxed overflow-x-auto whitespace-pre"
          >
            {sql}
          </pre>
          <button
            type="button"
            onClick={copy}
            className="absolute top-1.5 right-1.5 p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700"
            aria-label="Copy SQL"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
        </div>
      )}
    </div>
  );
};

export default GeneratedSqlCard;
