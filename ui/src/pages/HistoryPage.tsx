import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { RunRecord } from '../types';

function decisionColor(text: string) {
  if (!text) return 'text-zinc-500';
  const upper = text.toUpperCase();
  if (upper.includes('BUY') || upper.includes('OVERWEIGHT')) return 'text-emerald-400';
  if (upper.includes('SELL') || upper.includes('UNDERWEIGHT')) return 'text-red-400';
  return 'text-amber-400';
}

function decisionLabel(text: string) {
  if (!text) return '—';
  const upper = text.toUpperCase();
  if (upper.includes('BUY')) return 'BUY';
  if (upper.includes('OVERWEIGHT')) return 'OVERWEIGHT';
  if (upper.includes('SELL')) return 'SELL';
  if (upper.includes('UNDERWEIGHT')) return 'UNDERWEIGHT';
  if (upper.includes('HOLD')) return 'HOLD';
  return '—';
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    running:  'bg-blue-950 text-blue-400 border border-blue-800',
    complete: 'bg-emerald-950 text-emerald-400 border border-emerald-800',
    error:    'bg-red-950 text-red-400 border border-red-800',
  };
  return map[status] ?? 'bg-zinc-800 text-zinc-400';
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(e: React.MouseEvent, runId: string) {
    e.stopPropagation();
    try {
      await api.deleteRun(runId);
      setRuns(prev => prev.filter(r => r.run_id !== runId));
    } catch (err: any) {
      alert(err.message);
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-zinc-100">Run History</h1>
        <span className="text-sm text-zinc-500">{runs.length} run{runs.length !== 1 ? 's' : ''}</span>
      </div>

      {loading ? (
        <p className="text-zinc-500 text-sm">Loading…</p>
      ) : runs.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center">
          <p className="text-zinc-500 mb-2">No runs yet.</p>
          <button
            onClick={() => navigate('/new')}
            className="text-emerald-400 hover:text-emerald-300 text-sm"
          >
            Start your first analysis →
          </button>
        </div>
      ) : (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-left">
                <th className="px-4 py-3 text-zinc-400 font-medium">Ticker</th>
                <th className="px-4 py-3 text-zinc-400 font-medium">Date</th>
                <th className="px-4 py-3 text-zinc-400 font-medium">Decision</th>
                <th className="px-4 py-3 text-zinc-400 font-medium">Status</th>
                <th className="px-4 py-3 text-zinc-400 font-medium">Started</th>
                <th className="px-4 py-3 text-zinc-400 font-medium w-16"></th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr
                  key={run.run_id}
                  onClick={() => navigate(`/runs/${run.run_id}`)}
                  className="border-b border-zinc-800 last:border-0 cursor-pointer hover:bg-zinc-800/50 transition-colors"
                >
                  <td className="px-4 py-3 font-mono font-semibold text-zinc-100">{run.ticker}</td>
                  <td className="px-4 py-3 text-zinc-400">{run.date}</td>
                  <td className={`px-4 py-3 font-medium ${decisionColor(run.result?.decision ?? '')}`}>
                    {decisionLabel(run.result?.decision ?? '')}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusBadge(run.status)}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-500 text-xs">{formatDate(run.started_at)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={e => handleDelete(e, run.run_id)}
                      className="text-zinc-600 hover:text-red-400 transition-colors text-xs px-2 py-1 rounded hover:bg-red-950"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
