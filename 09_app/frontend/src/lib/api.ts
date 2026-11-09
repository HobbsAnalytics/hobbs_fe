// Thin fetch wrapper for the FastAPI backend. Errors are always JSON {error, detail} (see API.md), never a stack trace.

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** A short, safe sentence for the UI. Server `detail` is shown only for 404/422, which the backend words for users. */
export function messageForStatus(status: number, detail?: string): string {
  if (status === 401) return 'Your session has expired. Reload the page to sign in again.';
  if (status === 403) return "You don't have access to this data.";
  if ((status === 404 || status === 422) && detail) return detail;
  if (status === 404) return 'Not found.';
  if (status === 503) return 'The data service is unavailable right now. Try again in a minute.';
  return `The request failed (HTTP ${status}). Try again.`;
}

export async function readError(res: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body = await res.json();
    if (body && typeof body.detail === 'string') detail = body.detail;
  } catch {
    // non-JSON body: fall back to the status-based sentence
  }
  return new ApiError(res.status, messageForStatus(res.status, detail));
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { headers: { Accept: 'application/json' }, signal });
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') throw e;
    throw new ApiError(0, "Couldn't reach the app's API. Check your connection and try again.");
  }
  if (!res.ok) throw await readError(res);
  return (await res.json()) as T;
}

export const DRAWING_ID_RE = /^BRL-[A-Z]{3}-[A-Z]{2,4}-[0-9]{4}$/;

/** `/drawings/:id?page=<0-based page_num>&finding=<finding_id>`; page/finding omitted when unknown. */
export function drawingHref(drawingId: string, pageNum?: number | null, findingId?: string | null): string {
  const qs = new URLSearchParams();
  if (pageNum != null && Number.isFinite(pageNum)) qs.set('page', String(pageNum));
  if (findingId) qs.set('finding', findingId);
  const q = qs.toString();
  return `/drawings/${encodeURIComponent(drawingId)}${q ? `?${q}` : ''}`;
}

export function pdfUrl(drawingId: string): string {
  return `/api/drawings/${encodeURIComponent(drawingId)}/pdf`;
}

export function citationUrl(label: string): string {
  return `/api/citations/${encodeURIComponent(label)}`;
}
