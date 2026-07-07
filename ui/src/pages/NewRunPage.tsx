import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';

const PROVIDER_DEFAULTS: Record<string, { quick: string; deep: string }> = {
  openai:    { quick: 'gpt-5.4-mini',              deep: 'gpt-5.4' },
  anthropic: { quick: 'claude-sonnet-4-6',          deep: 'claude-opus-4-8' },
  google:    { quick: 'gemini-2.5-flash-preview',   deep: 'gemini-2.5-pro-preview' },
  mistral:   { quick: 'mistral-small-latest',       deep: 'mistral-large-latest' },
  ollama:    { quick: 'llama3.2',                   deep: 'llama3.1:70b' },
};

const ANALYSTS = [
  { key: 'market',       label: 'Market' },
  { key: 'social',       label: 'Sentiment' },
  { key: 'news',         label: 'News' },
  { key: 'fundamentals', label: 'Fundamentals' },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

const inputCls = 'bg-zinc-800 border border-zinc-700 text-zinc-100 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full';
const labelCls = 'block text-sm font-medium text-zinc-300 mb-1.5';

export default function NewRunPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [ticker, setTicker] = useState(searchParams.get('ticker') ?? '');
  const [date, setDate] = useState(todayIso());
  const [assetType, setAssetType] = useState<'stock' | 'crypto'>('stock');
  const [analysts, setAnalysts] = useState<string[]>(['market', 'social', 'news', 'fundamentals']);
  const [provider, setProvider] = useState('openai');
  const [quickLlm, setQuickLlm] = useState(PROVIDER_DEFAULTS.openai.quick);
  const [deepLlm, setDeepLlm] = useState(PROVIDER_DEFAULTS.openai.deep);
  const [debateRounds, setDebateRounds] = useState(1);
  const [riskRounds, setRiskRounds] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const defaults = PROVIDER_DEFAULTS[provider] ?? PROVIDER_DEFAULTS.openai;
    setQuickLlm(defaults.quick);
    setDeepLlm(defaults.deep);
  }, [provider]);

  function toggleAnalyst(key: string) {
    setAnalysts(prev =>
      prev.includes(key) ? prev.filter(a => a !== key) : [...prev, key]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (!ticker.trim()) { setError('Ticker is required.'); return; }
    if (analysts.length === 0) { setError('Select at least one analyst.'); return; }

    setLoading(true);
    try {
      const { run_id } = await api.createRun({
        ticker: ticker.trim().toUpperCase(),
        date,
        llm_provider: provider,
        deep_think_llm: deepLlm,
        quick_think_llm: quickLlm,
        max_debate_rounds: debateRounds,
        max_risk_discuss_rounds: riskRounds,
        analysts,
        asset_type: assetType,
      });
      navigate(`/runs/${run_id}`);
    } catch (err: any) {
      setError(err.message ?? 'Failed to start run.');
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-semibold text-zinc-100 mb-6">New Analysis</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Ticker + Date */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <div>
            <label className={labelCls}>Ticker Symbol</label>
            <input
              type="text"
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL, BTC-USD, 7203.T"
              className={`${inputCls} text-xl font-mono tracking-widest`}
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Analysis Date</label>
              <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                className={inputCls}
              />
            </div>

            <div>
              <label className={labelCls}>Asset Type</label>
              <div className="flex gap-3 mt-2">
                {(['stock', 'crypto'] as const).map(t => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value={t}
                      checked={assetType === t}
                      onChange={() => setAssetType(t)}
                      className="accent-emerald-500"
                    />
                    <span className="text-zinc-300 text-sm capitalize">{t}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Analysts */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <label className={labelCls}>Analysts</label>
          <div className="flex flex-wrap gap-3">
            {ANALYSTS.map(({ key, label }) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={analysts.includes(key)}
                  onChange={() => toggleAnalyst(key)}
                  className="accent-emerald-500 w-4 h-4"
                />
                <span className="text-zinc-300 text-sm">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* LLM Config */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">LLM Configuration</h2>

          <div>
            <label className={labelCls}>Provider</label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              className={inputCls}
            >
              {Object.keys(PROVIDER_DEFAULTS).map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Quick Think LLM</label>
              <input
                type="text"
                value={quickLlm}
                onChange={e => setQuickLlm(e.target.value)}
                className={`${inputCls} font-mono text-sm`}
              />
              <p className="text-xs text-zinc-600 mt-1">Used by analysts & researchers</p>
            </div>
            <div>
              <label className={labelCls}>Deep Think LLM</label>
              <input
                type="text"
                value={deepLlm}
                onChange={e => setDeepLlm(e.target.value)}
                className={`${inputCls} font-mono text-sm`}
              />
              <p className="text-xs text-zinc-600 mt-1">Used by managers</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Investment Debate Rounds</label>
              <input
                type="number"
                min={1} max={5}
                value={debateRounds}
                onChange={e => setDebateRounds(Number(e.target.value))}
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Risk Debate Rounds</label>
              <input
                type="number"
                min={1} max={5}
                value={riskRounds}
                onChange={e => setRiskRounds(Number(e.target.value))}
                className={inputCls}
              />
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-950 border border-red-800 text-red-300 rounded-md px-4 py-3 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-lg px-6 py-3 rounded-md transition-colors"
        >
          {loading ? 'Starting…' : '▶ Run Analysis'}
        </button>
      </form>
    </div>
  );
}
