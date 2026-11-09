import React from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

/** A Response whose body emits the given string chunks (to exercise partial-frame buffering). */
export function sseResponse(chunks: (string | Uint8Array)[]): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(typeof c === 'string' ? enc.encode(c) : c);
      controller.close();
    },
  });
  return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
}

type Handler = unknown | ((url: URL, init?: RequestInit) => Response | Promise<Response>);

/** Stub global fetch. Keys are exact pathnames, or a prefix ending in '*'. Unmatched paths get a JSON 404. */
export function mockFetch(routes: Record<string, Handler>) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(raw, 'http://localhost');
    for (const [key, handler] of Object.entries(routes)) {
      const hit = key.endsWith('*') ? url.pathname.startsWith(key.slice(0, -1)) : url.pathname === key;
      if (hit) return typeof handler === 'function' ? (handler as (u: URL, i?: RequestInit) => Response)(url, init) : jsonResponse(handler);
    }
    return jsonResponse({ error: 'not_found', detail: 'Not found' }, 404);
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

export const never = () => new Promise<Response>(() => {});

export function renderWithProviders(ui: React.ReactElement, opts: { route?: string; path?: string } = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[opts.route ?? '/']}>
        {opts.path ? (
          <Routes>
            <Route path={opts.path} element={ui} />
          </Routes>
        ) : (
          ui
        )}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export function calledUrls(fn: ReturnType<typeof mockFetch>): URL[] {
  return fn.mock.calls.map(([input]) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url;
    return new URL(raw, 'http://localhost');
  });
}
