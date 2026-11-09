import React, { useRef, useState } from 'react';
import { MessageSquare, RotateCcw, Send, History } from 'lucide-react';

interface ChatInputProps {
  disabled: boolean;
  onSend: (text: string) => void;
  onNewConversation: () => void;
  lastQuestion: string | null;
  hasConversation: boolean;
}

/** Enter sends, Shift+Enter inserts a newline. Disabled while an answer is streaming. */
const ChatInput: React.FC<ChatInputProps> = ({ disabled, onSend, onNewConversation, lastQuestion, hasConversation }) => {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    setValue('');
  };

  return (
    <div className="border-t border-slate-100 px-5 py-3.5 bg-white">
      <div
        className={`flex items-end gap-2.5 bg-slate-50 border-[1.5px] border-slate-200 rounded-xl px-3.5 py-2.5 transition-colors focus-within:border-emerald-500 focus-within:bg-white ${disabled ? 'opacity-70' : ''}`}
      >
        <MessageSquare size={14} className="text-slate-400 mb-2 flex-shrink-0" />
        <textarea
          ref={ref}
          rows={1}
          aria-label="Ask the Co-Pilot"
          placeholder={disabled ? 'Genie is answering…' : 'Ask Co-Pilot anything about Blue Ridge Phase 2…'}
          value={value}
          disabled={disabled}
          maxLength={2000}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          className="flex-1 resize-none border-none outline-none bg-transparent text-sm text-slate-800 placeholder:text-slate-400 max-h-32 py-1 disabled:cursor-not-allowed"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send"
          className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Send size={14} />
        </button>
      </div>
      <div className="flex gap-1.5 mt-2.5 flex-wrap items-center">
        <button
          type="button"
          className="quick-pill inline-flex items-center gap-1"
          disabled={disabled || !lastQuestion}
          onClick={() => {
            if (lastQuestion) {
              setValue(lastQuestion);
              ref.current?.focus();
            }
          }}
        >
          <History size={12} /> Last question
        </button>
        <button
          type="button"
          className="quick-pill inline-flex items-center gap-1"
          disabled={disabled || !hasConversation}
          onClick={onNewConversation}
        >
          <RotateCcw size={12} /> New conversation
        </button>
        <span className="ml-auto text-[11px] text-slate-400">Enter to send · Shift+Enter for a new line</span>
      </div>
    </div>
  );
};

export default ChatInput;
