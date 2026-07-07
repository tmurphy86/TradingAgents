export interface RunRequest {
  ticker: string;
  date: string;
  llm_provider: string;
  deep_think_llm: string;
  quick_think_llm: string;
  max_debate_rounds: number;
  max_risk_discuss_rounds: number;
  analysts: string[];
  asset_type: 'stock' | 'crypto';
}

export interface RunRecord {
  run_id: string;
  ticker: string;
  date: string;
  status: 'running' | 'complete' | 'error';
  started_at: string;
  completed_at: string | null;
  config: RunRequest;
  result: RunResult | null;
  error: string | null;
}

export interface RunResult {
  decision: string;
  market_report: string;
  sentiment_report: string;
  news_report: string;
  fundamentals_report: string;
  investment_plan: string;
  trader_investment_plan: string;
  final_trade_decision: string;
  investment_debate_state: Record<string, string>;
  risk_debate_state: Record<string, string>;
}

export interface Watchlist {
  id: string;
  name: string;
  tickers: string[];
  created_at: string;
}

export interface AgentEntry {
  key: string;
  name: string;
  phase: string;
  field: string;
  content: string;
  status: 'pending' | 'running' | 'complete';
}
