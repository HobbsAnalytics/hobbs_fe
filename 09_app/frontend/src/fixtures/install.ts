// DEV ONLY (`VITE_USE_FIXTURES=true npm run dev`). Replaces window.fetch for /api/* with the fixtures in ./data.
// Loaded from main.tsx behind the compile-time __USE_FIXTURES__ flag, which vite.config.ts pins to false for
// production builds, so this module and the sample PDF are dropped from dist/ (checked by scripts/check-no-fixtures.mjs).
import samplePdfUrl from './sample-drawing.pdf?url';
import * as fx from './data';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function sseResponse(frames: string[], delayMs = 350): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const f of frames) {
        await new Promise((r) => setTimeout(r, delayMs));
        controller.enqueue(enc.encode(f));
      }
      controller.close();
    },
  });
  return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
}

export function installFixtureFetch(): void {
  const realFetch = window.fetch.bind(window);
  console.info(`[fixtures] ${fx.FIXTURE_MARKER}: serving /api/* from src/fixtures`);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(raw, window.location.origin);
    if (!url.pathname.startsWith('/api/')) return realFetch(input, init);
    const p = url.pathname;
    const q = url.searchParams;

    if (p === '/api/whoami') return json(fx.whoamiObo);
    if (p === '/api/kpi/today') return json(fx.kpiToday);
    if (p === '/api/compliance/summary') return json(fx.complianceSummary);
    if (p === '/api/compliance/findings') {
      const scope = (q.get('scope') as 'week' | 'all') ?? 'week';
      const status = (q.get('status') as 'FAIL' | 'REVIEW') ?? 'FAIL';
      return json(fx.findingsPage(scope, status, Number(q.get('limit') ?? 50), Number(q.get('offset') ?? 0)));
    }
    if (p === '/api/risk/top') return json(fx.riskTop);
    if (p === '/api/schedule/overdue') return json(fx.scheduleOverdue);
    if (p === '/api/brief/today') return json(fx.dailyBrief);
    const pdf = /^\/api\/drawings\/([^/]+)\/pdf$/.exec(p);
    if (pdf) return realFetch(samplePdfUrl, init);
    const dwg = /^\/api\/drawings\/([^/]+)$/.exec(p);
    if (dwg) return json(fx.drawingDetailFor(decodeURIComponent(dwg[1])));
    const cite = /^\/api\/citations\/(.+)$/.exec(p);
    if (cite) {
      const hit = fx.citations[decodeURIComponent(cite[1])];
      return hit ? json(hit) : json({ error: 'not_found', detail: 'Unknown citation label' }, 404);
    }
    if (p === '/api/chat' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body ?? '{}')) as { message?: string };
      const m = (body.message ?? '').toLowerCase();
      if (m.includes('error')) return sseResponse(fx.chatFramesError);
      if (m.includes('which milestones') || m.includes('unclear')) return sseResponse(fx.chatFramesEmpty);
      return sseResponse(fx.chatFramesFailedDrawings);
    }
    return json({ error: 'not_found', detail: 'Not found' }, 404);
  };
}
