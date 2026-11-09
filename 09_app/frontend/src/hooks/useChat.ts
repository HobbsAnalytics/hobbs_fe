// Co-Pilot chat: POST /api/chat and consume its SSE stream (API.md "Chat (Task 20)").
//
// fetch + ReadableStream reader + TextDecoder (EventSource cannot POST). Each `data: {json}` frame is reduced into
// the current assistant message by applyChatEvent. Quirks handled:
//  - status:running is sent first and again every 15 s (also after `conversation`): idempotent, never reopens a
//    finished message;
//  - `sources` may be absent; drawing items repeat once per FAIL finding, so they are grouped by drawing_id; items for
//    drawings without a FAIL finding carry null page_num/bbox/citation and stay clickable;
//  - `transport` on done/error may be absent;
//  - error events carry a fixed, safe `message`, which is rendered as-is;
//  - an HTTP error, a network failure or a stream that ends without done/error becomes an inline error message.
import { useCallback, useEffect, useRef, useState } from 'react';
import { messageForStatus } from '../lib/api';
import { readSseStream } from '../lib/sse';
import type {
  BBox,
  ChatEvent,
  ChatResult,
  CitationSourceItem,
  SourceItem,
  Transport,
} from '../types/api';

export type ChatStatus = 'running' | 'done' | 'error';

export interface DrawingFindingRef {
  finding_id: string;
  page_num: number | null;
  bbox: BBox | null;
  citation: string | null;
}

export interface DrawingSourceGroup {
  drawing_id: string;
  findings: DrawingFindingRef[];
}

export interface GroupedSources {
  drawings: DrawingSourceGroup[];
  citations: CitationSourceItem[];
}

export interface UserChatMessage {
  id: string;
  role: 'user';
  text: string;
  createdAt: Date;
}

export interface AssistantChatMessage {
  id: string;
  role: 'assistant';
  status: ChatStatus;
  text: string;
  sql: string | null;
  result: ChatResult | null;
  sources: GroupedSources;
  conversationId: string | null;
  transport: Transport | null;
  errorMessage: string | null;
  createdAt: Date;
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

let seq = 0;
const nextId = (p: string) => `${p}-${Date.now().toString(36)}-${(seq++).toString(36)}`;

export function newAssistantMessage(): AssistantChatMessage {
  return {
    id: nextId('a'),
    role: 'assistant',
    status: 'running',
    text: '',
    sql: null,
    result: null,
    sources: { drawings: [], citations: [] },
    conversationId: null,
    transport: null,
    errorMessage: null,
    createdAt: new Date(),
  };
}

/** Group drawing items by drawing_id (first-seen order), de-duplicate findings and citation labels. */
export function groupSources(items: SourceItem[], into: GroupedSources = { drawings: [], citations: [] }): GroupedSources {
  const drawings = into.drawings.map((d) => ({ ...d, findings: [...d.findings] }));
  const citations = [...into.citations];
  for (const it of items ?? []) {
    if (!it || typeof it !== 'object') continue;
    if (it.kind === 'drawing' && typeof it.drawing_id === 'string') {
      let g = drawings.find((d) => d.drawing_id === it.drawing_id);
      if (!g) {
        g = { drawing_id: it.drawing_id, findings: [] };
        drawings.push(g);
      }
      if (it.finding_id && !g.findings.some((f) => f.finding_id === it.finding_id)) {
        g.findings.push({ finding_id: it.finding_id, page_num: it.page_num ?? null, bbox: it.bbox ?? null, citation: it.citation ?? null });
      }
    } else if (it.kind === 'citation' && typeof it.label === 'string') {
      if (!citations.some((c) => c.label === it.label)) citations.push(it);
    }
  }
  return { drawings, citations };
}

const isTransport = (t: unknown): t is Transport => t === 'mcp' || t === 'conversation_api';

/** Pure reducer: one SSE event into the assistant message. Unknown events are ignored. */
export function applyChatEvent(m: AssistantChatMessage, e: ChatEvent): AssistantChatMessage {
  if (!e || typeof e !== 'object') return m;
  switch (e.type) {
    case 'status':
      if (e.value === 'running') return m; // first event and the 15 s keep-alive: no change
      if (e.value === 'done') {
        if (m.status === 'error') return m;
        return { ...m, status: 'done', transport: isTransport(e.transport) ? e.transport : m.transport };
      }
      if (e.value === 'error') {
        return {
          ...m,
          status: 'error',
          errorMessage: typeof e.message === 'string' && e.message ? e.message : 'Genie could not answer. Try again.',
          transport: isTransport(e.transport) ? e.transport : m.transport,
        };
      }
      return m;
    case 'conversation':
      return typeof e.conversation_id === 'string' ? { ...m, conversationId: e.conversation_id } : m;
    case 'answer':
      if (typeof e.text !== 'string') return m;
      return { ...m, text: m.text ? `${m.text}\n\n${e.text}` : e.text };
    case 'sql':
      return typeof e.query === 'string' ? { ...m, sql: e.query } : m;
    case 'result':
      return {
        ...m,
        result: {
          columns: Array.isArray(e.columns) ? e.columns : [],
          rows: Array.isArray(e.rows) ? e.rows : [],
          row_count: typeof e.row_count === 'number' ? e.row_count : Array.isArray(e.rows) ? e.rows.length : 0,
          truncated: !!e.truncated,
        },
      };
    case 'sources':
      return Array.isArray(e.items) ? { ...m, sources: groupSources(e.items, m.sources) } : m;
    default:
      return m;
  }
}

const NETWORK_ERROR = "Couldn't reach the Co-Pilot service. Check your connection and try again.";
const EARLY_END = 'The answer stream ended before Genie finished. Try asking again.';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const convRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text || streamingRef.current) return;
    streamingRef.current = true;
    setIsStreaming(true);

    const user: UserChatMessage = { id: nextId('u'), role: 'user', text, createdAt: new Date() };
    let asst = newAssistantMessage();
    const id = asst.id;
    setMessages((ms) => [...ms, user, asst]);
    const commit = (next: AssistantChatMessage) => {
      asst = next;
      setMessages((ms) => ms.map((m) => (m.id === id ? next : m)));
    };

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify({ message: text, conversation_id: convRef.current }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) {
        let detail: string | undefined;
        try {
          const b = await res.json();
          if (b && typeof b.detail === 'string') detail = b.detail;
        } catch {
          /* non-JSON */
        }
        commit({ ...asst, status: 'error', errorMessage: res.ok ? EARLY_END : messageForStatus(res.status, res.status === 422 ? detail : undefined) });
        return;
      }
      await readSseStream(res.body, (data) => {
        const next = applyChatEvent(asst, data as ChatEvent);
        if (next === asst) return;
        if (next.conversationId && next.conversationId !== convRef.current) {
          convRef.current = next.conversationId;
          setConversationId(next.conversationId);
        }
        commit(next);
      });
      if (asst.status === 'running') commit({ ...asst, status: 'error', errorMessage: EARLY_END });
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return;
      commit({ ...asst, status: 'error', errorMessage: asst.status === 'running' && asst.text ? EARLY_END : NETWORK_ERROR });
    } finally {
      if (abortRef.current === ctrl) abortRef.current = null;
      streamingRef.current = false;
      setIsStreaming(false);
    }
  }, []);

  /** Start a fresh Genie conversation (the Daily Brief seed stays; it is rendered by the page, not stored here). */
  const reset = useCallback(() => {
    abortRef.current?.abort();
    convRef.current = null;
    setConversationId(null);
    setMessages([]);
  }, []);

  return { messages, send, isStreaming, conversationId, reset };
}
