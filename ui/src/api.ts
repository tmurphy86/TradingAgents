import type { RunRequest, RunRecord, RunResult, Watchlist } from './types';

const BASE = (import.meta as any).env?.VITE_API_BASE ?? '';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  createRun: (req: RunRequest) =>
    request<{ run_id: string }>('/api/runs', { method: 'POST', body: JSON.stringify(req) }),

  listRuns: () => request<RunRecord[]>('/api/runs'),

  getRun: (id: string) => request<RunRecord>(`/api/runs/${id}`),

  deleteRun: (id: string) =>
    request<void>(`/api/runs/${id}`, { method: 'DELETE' }),

  // Cooperative: a 200 only means the request was accepted. The run stays
  // 'running' until the `run_cancelled` SSE event. 409 = already finished.
  cancelRun: (id: string) =>
    request<{ run_id: string; status: 'cancelling' }>(`/api/runs/${id}/cancel`, { method: 'POST' }),

  streamRun: (id: string): EventSource =>
    new EventSource(`${BASE}/api/runs/${id}/stream`),

  listWatchlists: () => request<Watchlist[]>('/api/watchlists'),

  createWatchlist: (name: string, tickers: string[]) =>
    request<Watchlist>('/api/watchlists', {
      method: 'POST',
      body: JSON.stringify({ name, tickers }),
    }),

  updateWatchlist: (id: string, name: string, tickers: string[]) =>
    request<Watchlist>(`/api/watchlists/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, tickers }),
    }),

  deleteWatchlist: (id: string) =>
    request<void>(`/api/watchlists/${id}`, { method: 'DELETE' }),
};
