import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { applyChatEvent, groupSources, newAssistantMessage, useChat } from '../src/hooks/useChat';
import { createSseParser } from '../src/lib/sse';
import * as fx from '../src/fixtures/data';
import { mockFetch, sseResponse } from './utils';

afterEach(() => vi.unstubAllGlobals());

describe('SSE parser', () => {
  it('buffers partial chunks, ignores comments and joins a frame split mid-JSON', () => {
    const got: unknown[] = [];
    const p = createSseParser((d) => got.push(d));
    p.push(': keep-alive\n\nda');
    p.push('ta: {"type":"status","val');
    p.push('ue":"running"}\n');
    expect(got).toHaveLength(0);
    p.push('\ndata: {"type":"answer","text":"hi"}\r\n\r');
    p.push('\n');
    expect(got).toEqual([
      { type: 'status', value: 'running' },
      { type: 'answer', text: 'hi' },
    ]);
  });

  it('skips a malformed frame and keeps going', () => {
    const got: unknown[] = [];
    const p = createSseParser((d) => got.push(d));
    p.push('data: {not json}\n\ndata: {"type":"sql","query":"SELECT 1"}\n\n');
    expect(got).toEqual([{ type: 'sql', query: 'SELECT 1' }]);
  });
});

describe('groupSources', () => {
  it('groups drawing items by drawing_id (one item per FAIL finding) and keeps null-finding drawings', () => {
    const g = groupSources([
      { kind: 'drawing', drawing_id: 'BRL-INS-PID-0580', finding_id: 'BRL-INS-PID-0580-C01', page_num: 0, bbox: [0, 0, 0.1, 0.1], citation: 'ASME B31.3 §322' },
      { kind: 'drawing', drawing_id: 'BRL-ELE-GA-0023', finding_id: null, page_num: null, bbox: null, citation: null },
      { kind: 'drawing', drawing_id: 'BRL-INS-PID-0580', finding_id: 'BRL-INS-PID-0580-C02', page_num: 1, bbox: [0, 0, 0.1, 0.1], citation: 'ASME B31.3 §322' },
      { kind: 'citation', label: 'OSHA 1910.147', url: '/api/citations/OSHA%201910.147' },
      { kind: 'citation', label: 'OSHA 1910.147', url: '/api/citations/OSHA%201910.147' },
    ]);
    expect(g.drawings.map((d) => d.drawing_id)).toEqual(['BRL-INS-PID-0580', 'BRL-ELE-GA-0023']);
    expect(g.drawings[0].findings.map((f) => f.finding_id)).toEqual(['BRL-INS-PID-0580-C01', 'BRL-INS-PID-0580-C02']);
    expect(g.drawings[1].findings).toEqual([]);
    expect(g.citations).toHaveLength(1);
  });
});

describe('applyChatEvent', () => {
  it('treats repeated running as idempotent and records transport from done', () => {
    let m = newAssistantMessage();
    m = applyChatEvent(m, { type: 'status', value: 'running' });
    m = applyChatEvent(m, { type: 'conversation', conversation_id: 'c1' });
    const before = m;
    m = applyChatEvent(m, { type: 'status', value: 'running' });
    expect(m).toEqual(before);
    m = applyChatEvent(m, { type: 'status', value: 'done', transport: 'conversation_api' });
    expect(m.status).toBe('done');
    expect(m.transport).toBe('conversation_api');
    expect(m.conversationId).toBe('c1');
  });

  it('a late running event never reopens a finished message', () => {
    let m = applyChatEvent(newAssistantMessage(), { type: 'status', value: 'done' });
    m = applyChatEvent(m, { type: 'status', value: 'running' });
    expect(m.status).toBe('done');
    expect(m.transport).toBeNull();
  });
});

describe('useChat', () => {
  it('parses a canned stream: running repeats, answer, sql, truncated result, grouped sources, done+transport', async () => {
    // Split the canned frames at awkward byte offsets, including inside the multi-byte "§".
    const whole = new TextEncoder().encode(fx.chatFramesFailedDrawings.join(''));
    const cuts = [7, 40, 41, 200, 333, whole.indexOf(0xc2) + 1, 900, whole.length - 3];
    const chunks: Uint8Array[] = [];
    let prev = 0;
    for (const c of [...cuts.filter((x) => x > 0 && x < whole.length).sort((a, b) => a - b), whole.length]) {
      if (c > prev) chunks.push(whole.slice(prev, c));
      prev = c;
    }
    const fetchFn = mockFetch({ '/api/chat': () => sseResponse(chunks) });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send('Which drawings failed this week and why?');
    });
    const [user, asst] = result.current.messages;
    expect(user).toMatchObject({ role: 'user', text: 'Which drawings failed this week and why?' });
    expect(asst.role).toBe('assistant');
    if (asst.role !== 'assistant') throw new Error('unreachable');
    expect(asst.status).toBe('done');
    expect(asst.transport).toBe('mcp');
    expect(asst.text).toContain('51');
    expect(asst.text).toContain('ASME B31.3 §322');
    expect(asst.sql).toContain('SELECT drawing_id');
    expect(asst.result).toMatchObject({ row_count: 85, truncated: true });
    expect(asst.result?.rows).toHaveLength(4);
    expect(asst.sources.drawings.map((d) => d.drawing_id)).toEqual(['BRL-INS-PID-0580', 'BRL-PIP-ISO-0664', 'BRL-ELE-GA-0023']);
    expect(asst.sources.drawings[0].findings).toHaveLength(2);
    expect(asst.sources.drawings[2].findings).toHaveLength(0);
    expect(asst.sources.citations.map((c) => c.label)).toEqual(['ASME B31.3 §322', 'OSHA 1910.147']);
    expect(result.current.conversationId).toBe(fx.FIXTURE_CONVERSATION_ID);
    expect(result.current.isStreaming).toBe(false);
    const [, init] = fetchFn.mock.calls[0];
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ message: 'Which drawings failed this week and why?', conversation_id: null });
  });

  it('reuses conversation_id for a follow-up', async () => {
    const fetchFn = mockFetch({ '/api/chat': () => sseResponse(fx.chatFramesFailedDrawings) });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send('first');
    });
    await act(async () => {
      await result.current.send('follow up');
    });
    const body = JSON.parse(String(fetchFn.mock.calls[1][1]?.body));
    expect(body).toEqual({ message: 'follow up', conversation_id: fx.FIXTURE_CONVERSATION_ID });
  });

  it('tolerates a missing sources event and missing transport (graceful empty answer)', async () => {
    mockFetch({ '/api/chat': () => sseResponse(fx.chatFramesEmpty) });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send('which milestones?');
    });
    const asst = result.current.messages[1];
    if (asst.role !== 'assistant') throw new Error('unreachable');
    expect(asst.status).toBe('done');
    expect(asst.text).toMatch(/I'm not sure which milestones you mean/);
    expect(asst.sources).toEqual({ drawings: [], citations: [] });
    expect(asst.sql).toBeNull();
    expect(asst.result).toBeNull();
    expect(asst.transport).toBeNull();
  });

  it('renders the error event message and its transport', async () => {
    mockFetch({ '/api/chat': () => sseResponse(fx.chatFramesError) });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send('make it error');
    });
    const asst = result.current.messages[1];
    if (asst.role !== 'assistant') throw new Error('unreachable');
    expect(asst.status).toBe('error');
    expect(asst.errorMessage).toBe('Genie did not answer within 110 seconds. Try a narrower question.');
    expect(asst.transport).toBe('mcp');
  });

  it('maps an HTTP 401 to a safe sign-in message, and a stream that ends early to an error', async () => {
    mockFetch({
      '/api/chat': (_u: URL, init?: RequestInit) =>
        JSON.parse(String(init?.body)).message === 'a'
          ? new Response(JSON.stringify({ error: 'unauthorized', detail: 'x' }), { status: 401 })
          : sseResponse(['data: {"type":"status","value":"running"}\n\n']),
    });
    const { result } = renderHook(() => useChat());
    await act(async () => {
      await result.current.send('a');
    });
    await act(async () => {
      await result.current.send('b');
    });
    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    const a = result.current.messages[1];
    const b = result.current.messages[3];
    if (a.role !== 'assistant' || b.role !== 'assistant') throw new Error('unreachable');
    expect(a.status).toBe('error');
    expect(a.errorMessage).toMatch(/session has expired/i);
    expect(b.status).toBe('error');
    expect(b.errorMessage).toMatch(/ended before Genie finished/i);
  });
});
