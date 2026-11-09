import React, { useEffect, useRef } from 'react';
import { Bot } from 'lucide-react';
import type { ChatSession } from './ChatContext';
import { useWhoami } from '../../hooks/useWhoami';
import { formatTime } from '../../lib/format';
import DailyBriefCard from '../dashboards/DailyBriefCard';
import AssistantMessage from './AssistantMessage';
import ChatInput from './ChatInput';
import IdentityChip from './IdentityChip';

const ChatPanel: React.FC<{ chat: ChatSession }> = ({ chat }) => {
  const { messages, send, isStreaming, reset } = chat;
  const whoami = useWhoami();
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const lastQuestion = [...messages].reverse().find((m) => m.role === 'user')?.text ?? null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl flex flex-col overflow-hidden min-h-0 h-full" style={{ boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-white flex-shrink-0">
            <Bot size={18} />
          </div>
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold text-slate-900">Project Co-Pilot</h3>
            <p className="text-[11px] text-slate-500 truncate">Genie · Blue Ridge project data and drawing findings</p>
          </div>
        </div>
        <IdentityChip />
      </div>

      <div ref={logRef} className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 bg-slate-50 min-h-0" data-testid="chat-log">
        <DailyBriefCard />
        {messages.map((m) =>
          m.role === 'user' ? (
            <div key={m.id} className="self-end max-w-[85%]">
              <div className="flex justify-end mb-1.5 text-[11px] text-slate-500">{formatTime(m.createdAt)}</div>
              <div className="msg-bubble-user">{m.text}</div>
            </div>
          ) : (
            <AssistantMessage key={m.id} message={m} authMode={whoami.data?.auth_mode} />
          ),
        )}
      </div>

      <ChatInput
        disabled={isStreaming}
        onSend={send}
        onNewConversation={reset}
        lastQuestion={lastQuestion}
        hasConversation={messages.length > 0}
      />
    </section>
  );
};

export default ChatPanel;
