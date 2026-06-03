import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="TradingAgents API", version="0.2.5", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    ticker: str
    date: str
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.4"
    quick_think_llm: str = "gpt-5.4-mini"
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    analysts: list[str] = ["market", "sentiment", "news", "fundamentals"]
    asset_type: str = "stock"


class AnalyzeResponse(BaseModel):
    ticker: str
    date: str
    decision: str


def _run_analysis(req: AnalyzeRequest) -> str:
    config = DEFAULT_CONFIG.copy()
    config.update(
        {
            "llm_provider": req.llm_provider,
            "deep_think_llm": req.deep_think_llm,
            "quick_think_llm": req.quick_think_llm,
            "max_debate_rounds": req.max_debate_rounds,
            "max_risk_discuss_rounds": req.max_risk_discuss_rounds,
            "analyst_selection": req.analysts,
        }
    )
    ta = TradingAgentsGraph(debug=False, config=config)
    _, decision = ta.propagate(req.ticker.upper(), req.date)
    return decision


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    try:
        decision = await asyncio.to_thread(_run_analysis, req)
        return AnalyzeResponse(ticker=req.ticker.upper(), date=req.date, decision=decision)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
