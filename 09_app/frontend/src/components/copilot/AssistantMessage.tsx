import React from 'react';
import type { AssistantChatMessage } from '../../hooks/useChat';
import type { AuthMode } from '../../types/api';
import { AUTH_MODE_LABEL, TRANSPORT_LABEL, formatTime } from '../../lib/format';
import Markdown from '../shared/Markdown';
import ErrorAlert from '../shared/ErrorAlert';
import GeneratedSqlCard from './GeneratedSqlCard';
import ResultTable from './ResultTable';
import SourcesCard from './SourcesCard';
import VerifyFooter from './VerifyFooter';

export const TypingDots: React.FC<{ testId?: string }> = ({ testId }) => (
  <span className="typing-dots ml-1" data-testid={testId} aria-label="Genie is working">
    <span />
    <span />
    <span />
  </span>
);

/** "Genie · as you (OBO) · via MCP": who the answer ran as (from /api/whoami) and the transport from the done event. */
export function executionNote(authMode: AuthMode | undefined, transport: string | null): string {
  return ['Genie', authMode ? AUTH_MODE_LABEL[authMode] : null, transport ? TRANSPORT_LABEL[transport] ?? transport : null]
    .filter(Boolean)
    .join(' · ');
}

const AssistantMessage: React.FC<{ message: AssistantChatMessage; authMode?: AuthMode }> = ({ message: m, authMode }) => {
  const running = m.status === 'running';
  return (
    <div className="self-start max-w-[85%] w-full" data-testid="assistant-message">
      <div className="flex items-center gap-2 mb-1.5 text-[11px] text-slate-500">
        <span className="msg-meta-tag">Genie</span>
        <span>{formatTime(m.createdAt)}</span>
        {running && <TypingDots testId="typing-indicator" />}
      </div>
      <div className="msg-bubble" aria-live="polite" aria-busy={running}>
        {m.text ? (
          <Markdown>{m.text}</Markdown>
        ) : running ? (
          <p className="text-slate-500">Genie is working on it…</p>
        ) : null}
        {m.status === 'error' && (
          <div className={m.text ? 'mt-3' : ''}>
            <ErrorAlert compact message={m.errorMessage ?? 'Genie could not answer. Try again.'} />
          </div>
        )}
        {m.sql && <GeneratedSqlCard sql={m.sql} />}
        {m.result && <ResultTable result={m.result} />}
        <SourcesCard sources={m.sources} />
        {!running && <VerifyFooter note={executionNote(authMode, m.transport)} noteTestId="exec-note" />}
      </div>
    </div>
  );
};

export default AssistantMessage;
