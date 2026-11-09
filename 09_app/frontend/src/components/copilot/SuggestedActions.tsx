import React from 'react';

export const SUGGESTED_PROMPTS: { prompt: string; sub: string }[] = [
  { prompt: 'Which drawings failed this week and why?', sub: 'Compliance findings · grouped by citation' },
  { prompt: 'Which milestones are late or due today?', sub: 'Schedule · late or due today' },
  { prompt: 'What are the top High-risk milestones in the next 90 days?', sub: 'ML risk forecast · by band' },
  { prompt: 'What does OSHA 1910.147 require?', sub: 'Code excerpts · lockout/tagout' },
];

const SuggestedActions: React.FC<{ onAsk: (prompt: string) => void; disabled: boolean }> = ({ onAsk, disabled }) => (
  <div className="rail-card">
    <div className="rail-title">Suggested Actions</div>
    <div className="space-y-2">
      {SUGGESTED_PROMPTS.map((s) => (
        <button key={s.prompt} type="button" className="action-btn" disabled={disabled} onClick={() => onAsk(s.prompt)}>
          {s.prompt}
          <span className="action-sub">{s.sub}</span>
        </button>
      ))}
    </div>
  </div>
);

export default SuggestedActions;
