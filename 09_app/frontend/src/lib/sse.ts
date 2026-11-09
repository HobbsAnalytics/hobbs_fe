// Minimal Server-Sent Events frame parser for a fetch() ReadableStream (POST /api/chat cannot use EventSource).
//
// Feed it decoded text in arbitrary chunks; it buffers partial frames and calls onData once per complete
// `data: <json>\n\n` frame. Comment lines (starting with ':'), `event:`/`id:`/`retry:` fields and frames that are
// not valid JSON are ignored. CRLF and CR line endings are normalized, including a CR split across two chunks.

export interface SseParser {
  push(chunk: string): void;
  /** Call once at end of stream to parse a final frame that lacks its trailing blank line. */
  flush(): void;
}

export function createSseParser(onData: (data: unknown) => void): SseParser {
  let buf = '';

  const handleFrame = (frame: string) => {
    const dataLines: string[] = [];
    for (const line of frame.split('\n')) {
      if (line === '' || line.startsWith(':')) continue;
      if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
    }
    if (dataLines.length === 0) return;
    try {
      onData(JSON.parse(dataLines.join('\n')));
    } catch {
      // malformed frame: skip it rather than break the stream
    }
  };

  return {
    push(chunk: string) {
      let s = buf + chunk;
      const trailingCR = s.endsWith('\r');
      if (trailingCR) s = s.slice(0, -1);
      s = s.replace(/\r\n?/g, '\n');
      let idx: number;
      while ((idx = s.indexOf('\n\n')) >= 0) {
        handleFrame(s.slice(0, idx));
        s = s.slice(idx + 2);
      }
      buf = s + (trailingCR ? '\r' : '');
    },
    flush() {
      const rest = buf.replace(/\r\n?/g, '\n');
      buf = '';
      if (rest.trim()) handleFrame(rest);
    },
  };
}

/** Read a fetch body to the end, decoding UTF-8 across chunk boundaries, and parse its SSE frames. */
export async function readSseStream(
  body: ReadableStream<Uint8Array>,
  onData: (data: unknown) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8');
  const parser = createSseParser(onData);
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      if (value) parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.flush();
  } finally {
    reader.releaseLock?.();
  }
}
