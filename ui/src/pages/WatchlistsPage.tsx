import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Watchlist } from '../types';

const inputCls = 'bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full text-sm';

function parseTickers(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map(t => t.trim().toUpperCase())
    .filter(Boolean);
}

export default function WatchlistsPage() {
  const navigate = useNavigate();
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // New watchlist form
  const [showNewForm, setShowNewForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTickers, setNewTickers] = useState('');

  // Edit form
  const [editId, setEditId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editTickers, setEditTickers] = useState('');

  useEffect(() => {
    api.listWatchlists()
      .then(wls => {
        setWatchlists(wls);
        if (wls.length > 0) setSelectedId(wls[0].id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const selected = watchlists.find(w => w.id === selectedId) ?? null;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const tickers = parseTickers(newTickers);
    if (!newName.trim() || tickers.length === 0) return;
    try {
      const wl = await api.createWatchlist(newName.trim(), tickers);
      setWatchlists(prev => [...prev, wl]);
      setSelectedId(wl.id);
      setNewName('');
      setNewTickers('');
      setShowNewForm(false);
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editId) return;
    const tickers = parseTickers(editTickers);
    if (!editName.trim()) return;
    try {
      const wl = await api.updateWatchlist(editId, editName.trim(), tickers);
      setWatchlists(prev => prev.map(w => w.id === editId ? wl : w));
      setEditId(null);
    } catch (err: any) {
      alert(err.message);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this watchlist?')) return;
    try {
      await api.deleteWatchlist(id);
      setWatchlists(prev => prev.filter(w => w.id !== id));
      if (selectedId === id) setSelectedId(watchlists.find(w => w.id !== id)?.id ?? null);
    } catch (err: any) {
      alert(err.message);
    }
  }

  function startEdit(wl: Watchlist) {
    setEditId(wl.id);
    setEditName(wl.name);
    setEditTickers(wl.tickers.join('\n'));
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-zinc-100">Watchlists</h1>
        <button
          onClick={() => setShowNewForm(v => !v)}
          className="bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          + New Watchlist
        </button>
      </div>

      {/* New watchlist form */}
      {showNewForm && (
        <form onSubmit={handleCreate} className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 mb-5 space-y-3">
          <h2 className="text-sm font-medium text-zinc-300">Create Watchlist</h2>
          <input
            type="text"
            placeholder="Name (e.g. Tech Giants)"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            className={inputCls}
          />
          <textarea
            placeholder="Tickers — one per line or comma-separated&#10;AAPL&#10;MSFT&#10;GOOGL"
            value={newTickers}
            onChange={e => setNewTickers(e.target.value)}
            rows={4}
            className={`${inputCls} font-mono resize-none`}
          />
          <div className="flex gap-2">
            <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white text-sm px-4 py-1.5 rounded-md">
              Create
            </button>
            <button type="button" onClick={() => setShowNewForm(false)} className="text-zinc-500 hover:text-zinc-300 text-sm px-4 py-1.5">
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-zinc-500 text-sm">Loading…</p>
      ) : watchlists.length === 0 ? (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center">
          <p className="text-zinc-500">No watchlists yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="flex gap-5">
          {/* Left panel — watchlist list */}
          <div className="w-48 flex-shrink-0 space-y-1">
            {watchlists.map(wl => (
              <button
                key={wl.id}
                onClick={() => setSelectedId(wl.id)}
                className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors ${
                  selectedId === wl.id
                    ? 'bg-zinc-800 text-emerald-400'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60'
                }`}
              >
                <div className="font-medium truncate">{wl.name}</div>
                <div className="text-xs text-zinc-600 mt-0.5">{wl.tickers.length} ticker{wl.tickers.length !== 1 ? 's' : ''}</div>
              </button>
            ))}
          </div>

          {/* Right panel — selected watchlist */}
          {selected && (
            <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              {editId === selected.id ? (
                <form onSubmit={handleUpdate} className="space-y-3">
                  <input
                    type="text"
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    className={inputCls}
                  />
                  <textarea
                    value={editTickers}
                    onChange={e => setEditTickers(e.target.value)}
                    rows={6}
                    className={`${inputCls} font-mono resize-none`}
                  />
                  <div className="flex gap-2">
                    <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white text-sm px-4 py-1.5 rounded-md">
                      Save
                    </button>
                    <button type="button" onClick={() => setEditId(null)} className="text-zinc-500 hover:text-zinc-300 text-sm px-4 py-1.5">
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-medium text-zinc-100">{selected.name}</h2>
                    <div className="flex gap-2">
                      <button
                        onClick={() => startEdit(selected)}
                        className="text-zinc-500 hover:text-zinc-300 text-xs px-3 py-1.5 rounded-md hover:bg-zinc-800 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(selected.id)}
                        className="bg-red-900 hover:bg-red-800 text-red-200 px-3 py-1.5 rounded-md text-xs"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {selected.tickers.length === 0 ? (
                    <p className="text-zinc-500 text-sm">No tickers. Edit to add some.</p>
                  ) : (
                    <div className="space-y-2">
                      {selected.tickers.map(ticker => (
                        <div
                          key={ticker}
                          className="flex items-center justify-between bg-zinc-800 rounded-md px-3 py-2"
                        >
                          <span className="font-mono text-zinc-100 font-medium text-sm">{ticker}</span>
                          <button
                            onClick={() => navigate(`/new?ticker=${encodeURIComponent(ticker)}`)}
                            className="bg-emerald-700 hover:bg-emerald-600 text-emerald-100 text-xs px-3 py-1 rounded-md transition-colors"
                          >
                            ▶ Run
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
