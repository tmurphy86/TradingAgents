import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api';
import type { RunRecord } from '../types';

const PIPELINE = [
  { key: 'market_analyst',      name: 'Market Analyst',      phase: 'Analysis',          field: 'market_report' },
  { key: 'sentiment_analyst',   name: 'Sentiment Analyst',   phase: 'Analysis',          field: 'sentiment_report' },
  { key: 'news_analyst',        name: 'News Analyst',        phase: 'Analysis',          field: 'news_report' },
  { key: 'fundamentals_analyst',name: 'Fundamentals Analyst',phase: 'Analysis',          field: 'fundamentals_report' },
  { key: 'bull_researcher',     name: 'Bull Researcher',     phase: 'Investment Debate', field: 'investment_debate_state.bull_history' },
  { key: 'bear_researcher',     name: 'Bear Researcher',     phase: 'Investment Debate', field: 'investment_debate_state.bear_history' },
  { key: 'research_manager',    name: 'Research Manager',    phase: 'Research Synthesis',field: 'investment_plan' },
  { key: 'trader',              name: 'Trader',              phase: 'Trade Planning',    field: 'trader_investment_plan' },
  { key: 'aggressive_analyst',  name: 'Aggressive Analyst',  phase: 'Risk Debate',       field: 'risk_debate_state.aggressive_history' },
  { key: 'conservative_analyst',name: 'Conservative Analyst',phase: 'Risk Debate',       field: 'risk_debate_state.conservative_history' },
  { key: 'neutral_analyst',     name: 'Neutral Analyst',     phase: 'Risk Debate',       field: 'risk_debate_state.neutral_history' },
  { key: 'portfolio_manager',   name: 'Portfolio Manager',   phase: 'Final Decision',    field: 'final_trade_decision' },
];

const FIELD_TO_KEY: Record<string, string> = {
  'market_report':                               'market_analyst',
  'sentiment_report':                            'sentiment_analyst',
  'news_report':                                 'news_analyst',
  'fundamentals_report':                         'fundamentals_analyst',
  'investment_debate_state.bull_history':        'bull_researcher',
  'investment_debate_state.bear_history':        'bear_researcher',
  'investment_plan':                             'research_manager',
  'trader_investment_plan':                      'trader',
  'risk_debate_state.aggressive_history':        'aggressive_analyst',
  'risk_debate_state.conservative_history':      'conservative_analyst',
  'risk_debate_state.neutral_history':           'neutral_analyst',
  'final_trade_decision':                        'portfolio_manager',
};

type AgentStatus = 'pending' | 'running' | 'complete' | 'error';

interface AgentState {
  content: string;
  status: AgentStatus;
}

function decisionColor(text: string) {
  const upper = text.toUpperCase();
  if (upper.includes('BUY') || upper.includes('OVERWEIGHT')) return 'text-emerald-400 bg-emerald-950 border-emerald-800';
  if (upper.includes('SELL') || upper.includes('UNDERWEIGHT')) return 'text-red-400 bg-red-950 border-red-800';
  return 'text-amber-400 bg-amber-950 border-amber-800';
}

function decisionLabel(text: string) {
  const upper = text.toUpperCase();
  if (upper.includes('BUY')) return 'BUY';
  if (upper.includes('OVERWEIGHT')) return 'OVERWEIGHT';
  if (upper.includes('SELL')) return 'SELL';
  if (upper.includes('UNDERWEIGHT')) return 'UNDERWEIGHT';
  if (upper.includes('HOLD')) return 'HOLD';
  return 'DECISION';
}

function elapsed(startedAt: string) {
  const ms = Date.now() - new Date(startedAt).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${s % 60}s`;
}

function StatusDot({ status }: { status: AgentStatus }) {
  if (status === 'complete') return <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 flex-shrink-0" />;
  if (status === 'running') return <span className="w-2.5 h-2.5 rounded-full bg-blue-400 flex-shrink-0 animate-pulse" />;
  if (status === 'error') return <span className="w-2.5 h-2.5 rounded-full bg-red-400 flex-shrink-0" />;
  return <span className="w-2.5 h-2.5 rounded-full bg-zinc-600 flex-shrink-0" />;
}

function AgentCard({
  name, phase, status, content, expanded, onToggle,
}: {
  name: string; phase: string; status: AgentStatus; content: string; expanded: boolean; onToggle: () => void;
}) {
  const borderColor =
    status === 'complete' ? 'border-l-emerald-500' :
    status === 'running'  ? 'border-l-blue-500' :
    status === 'error'    ? 'border-l-red-500' :
    'border-l-zinc-700';

  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-lg border-l-2 ${borderColor} overflow-hidden`}>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-zinc-800/50 transition-colors"
      >
        <StatusDot status={status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-zinc-100 text-sm font-medium">{name}</span>
            {status === 'running' && (
              <span className="text-xs text-blue-400 font-medium">Running…</span>
            )}
          </div>
          <span className="text-xs text-zinc-500">{phase}</span>
        </div>
        {content && (
          <svg
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
            className={`w-4 h-4 text-zinc-500 flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        )}
      </button>

      {expanded && content && (
        <div className="px-4 pb-4 border-t border-zinc-800">
          <pre className="whitespace-pre-wrap text-xs text-zinc-300 mt-3 leading-relaxed overflow-x-auto">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function RunPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunRecord | null>(null);
  const [agents, setAgents] = useState<Record<string, AgentState>>(() =>
    Object.fromEntries(PIPELINE.map(p => [p.key, { content: '', status: 'pending' as AgentStatus }]))
  );
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [finalDecision, setFinalDecision] = useState('');
  const [runStatus, setRunStatus] = useState<'running' | 'complete' | 'error' | 'loading'>('loading');
  const [errorMsg, setErrorMsg] = useState('');
  const [tick, setTick] = useState(0);
  const esRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Tick every second for elapsed timer
  useEffect(() => {
    if (runStatus !== 'running') return;
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, [runStatus]);

  const markAgentComplete = useCallback((field: string, content: string) => {
    const key = FIELD_TO_KEY[field];
    if (!key) return;

    setAgents(prev => {
      const next = { ...prev, [key]: { content, status: 'complete' as AgentStatus } };
      // Set the next pending agent to 'running'
      const idx = PIPELINE.findIndex(p => p.key === key);
      for (let i = idx + 1; i < PIPELINE.length; i++) {
        if (next[PIPELINE[i].key]?.status === 'pending') {
          next[PIPELINE[i].key] = { ...next[PIPELINE[i].key], status: 'running' };
          break;
        }
      }
      return next;
    });

    // Auto-expand
    setExpanded(prev => ({ ...prev, [key]: true }));

    // Scroll to bottom
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }), 50);
  }, []);

  useEffect(() => {
    if (!runId) return;

    // Mark first agent as running initially
    setAgents(prev => ({
      ...prev,
      market_analyst: { ...prev.market_analyst, status: 'running' },
    }));

    const es = api.streamRun(runId);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);

        if (event.type === 'agent_update') {
          markAgentComplete(event.field, event.content);
        } else if (event.type === 'run_complete') {
          setFinalDecision(event.decision ?? '');
          // Fetch the run record to get metadata
          api.getRun(runId).then(setRun).catch(() => {});
          setRunStatus('complete');
          // Mark all agents with content as complete
          if (event.result) {
            setAgents(prev => {
              const next = { ...prev };
              for (const p of PIPELINE) {
                if (next[p.key]?.content) {
                  next[p.key] = { ...next[p.key], status: 'complete' };
                }
              }
              return next;
            });
          }
        } else if (event.type === 'run_error') {
          setErrorMsg(event.message ?? 'Run failed');
          setRunStatus('error');
        } else if (event.type === 'stream_end') {
          es.close();
        }
      } catch {}
    };

    es.onerror = () => {
      setRunStatus(prev => prev === 'loading' ? 'error' : prev);
      es.close();
    };

    // Also fetch run metadata
    api.getRun(runId)
      .then(r => {
        setRun(r);
        setRunStatus(r.status === 'running' ? 'running' : r.status);
      })
      .catch(() => setRunStatus('error'));

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [runId, markAgentComplete]);

  function toggleExpand(key: string) {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  }

  const statusBadge = {
    running: 'bg-blue-950 text-blue-400 border border-blue-800',
    complete: 'bg-emerald-950 text-emerald-400 border border-emerald-800',
    error: 'bg-red-950 text-red-400 border border-red-800',
    loading: 'bg-zinc-800 text-zinc-400 border border-zinc-700',
  }[runStatus];

  const filteredPipeline = run?.config?.analysts
    ? PIPELINE.filter(p => {
        const analystKeys = ['market_analyst', 'sentiment_analyst', 'news_analyst', 'fundamentals_analyst'];
        const analystMap: Record<string, string> = {
          market_analyst: 'market',
          sentiment_analyst: 'social',
          news_analyst: 'news',
          fundamentals_analyst: 'fundamentals',
        };
        if (!analystKeys.includes(p.key)) return true;
        return run.config.analysts.includes(analystMap[p.key]);
      })
    : PIPELINE;

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-semibold text-zinc-100 font-mono">
              {run?.ticker ?? '…'}
            </h1>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge}`}>
              {runStatus === 'loading' ? 'Loading' : runStatus}
            </span>
          </div>
          <p className="text-zinc-500 text-sm">
            {run?.date}
            {runStatus === 'running' && run?.started_at && (
              <span className="ml-2 text-blue-400">{elapsed(run.started_at)}</span>
            )}
            {runStatus === 'complete' && run?.started_at && run?.completed_at && (
              <span className="ml-2 text-zinc-600">
                completed in {elapsed(run.started_at)}
              </span>
            )}
          </p>
        </div>
        <Link to="/history" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
          ← History
        </Link>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="bg-red-950 border border-red-800 text-red-300 rounded-md px-4 py-3 text-sm mb-4">
          {errorMsg}
        </div>
      )}

      {/* Pipeline cards */}
      <div className="space-y-2">
        {filteredPipeline.map(({ key, name, phase }) => (
          <AgentCard
            key={key}
            name={name}
            phase={phase}
            status={agents[key]?.status ?? 'pending'}
            content={agents[key]?.content ?? ''}
            expanded={!!expanded[key]}
            onToggle={() => toggleExpand(key)}
          />
        ))}
      </div>

      {/* Final Decision */}
      {finalDecision && (
        <div className={`mt-6 border rounded-lg p-5 ${decisionColor(finalDecision)}`}>
          <div className="flex items-center gap-3 mb-3">
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${decisionColor(finalDecision)}`}>
              {decisionLabel(finalDecision)}
            </span>
            <span className="text-sm font-semibold">Final Portfolio Decision</span>
          </div>
          <pre className="whitespace-pre-wrap text-sm leading-relaxed opacity-90">
            {finalDecision}
          </pre>
        </div>
      )}

      <div ref={bottomRef} className="h-8" />
    </div>
  );
}
