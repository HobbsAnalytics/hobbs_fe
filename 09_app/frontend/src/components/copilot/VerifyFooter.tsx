import React from 'react';
import { Info } from 'lucide-react';

/** Persistent per-answer disclaimer, plus an optional execution note (who it ran as, which transport). */
const VerifyFooter: React.FC<{ note?: string; noteTestId?: string }> = ({ note, noteTestId }) => (
  <div className="mt-3 pt-2 border-t border-slate-100 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-400">
    <span className="flex items-center gap-1.5 italic">
      <Info size={12} />
      AI-generated — verify before action
    </span>
    {note && (
      <span className="not-italic text-slate-400" data-testid={noteTestId}>
        · {note}
      </span>
    )}
  </div>
);

export default VerifyFooter;
