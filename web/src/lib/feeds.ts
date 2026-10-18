import { wikiFile } from "./site";

/**
 * Fetches a wiki-published feed (releases.json, upcoming.json, ...) through the base path, with
 * a bounded retry: up to `attempts` tries, waiting `baseDelayMs * 2^n` between them. A 4xx is
 * final (the file is not there); a network error or a 5xx is retried.
 */
export interface FeedResult {
  ok: boolean;
  status: number | null;
  ms: number;
  bytes: number;
  modified: string | null;
  attempts: number;
}

export async function fetchFeed(
  path: string,
  { attempts = 3, baseDelayMs = 400, signal }: { attempts?: number; baseDelayMs?: number; signal?: AbortSignal } = {},
): Promise<FeedResult> {
  const t0 = performance.now();
  let last: FeedResult = { ok: false, status: null, ms: 0, bytes: 0, modified: null, attempts: 0 };
  for (let n = 0; n < attempts; n++) {
    if (n > 0) await new Promise((r) => setTimeout(r, baseDelayMs * 2 ** (n - 1)));
    if (signal?.aborted) break;
    try {
      const res = await fetch(`${wikiFile(path)}?t=${Date.now()}`, { cache: "no-store", signal });
      const buf = await res.arrayBuffer();
      last = {
        ok: res.status === 200,
        status: res.status,
        ms: Math.round(performance.now() - t0),
        bytes: buf.byteLength,
        modified: res.headers.get("last-modified"),
        attempts: n + 1,
      };
      if (res.status < 500) return last;
    } catch {
      last = { ok: false, status: null, ms: Math.round(performance.now() - t0), bytes: 0, modified: null, attempts: n + 1 };
    }
  }
  return last;
}
