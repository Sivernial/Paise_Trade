import asyncio
import os
import pydantic
from typing import List, Optional
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.types import TemplatedSystemInstructions

# Load environment variables (specifically GEMINI_API_KEY) from the root .env file
load_dotenv(dotenv_path="../.env")

# ==============================================================================
# SCHEMAS FOR STRUCTURED OUTPUT
# ==============================================================================

class TradeCandidate(pydantic.BaseModel):
    symbol: str
    direction: str
    confidence_score: int
    entry_zone: str
    stop_loss_pct: float
    target_1_pct: float
    target_2_pct: float
    reasoning: str

class MacroEnvironment(pydantic.BaseModel):
    theme: str
    catalyst: str
    fii_dii_flow: str

class Sectors(pydantic.BaseModel):
    strongest: List[str]
    weakest: List[str]

class AlgoRiskInstructions(pydantic.BaseModel):
    gap_up_logic: str
    mean_reversion_threshold_pct: float
    short_covering_warning: str

class DailyMarketReport(pydantic.BaseModel):
    report_date: str
    target_trading_date: str
    market_bias: str
    macro_environment: MacroEnvironment
    sectors: Sectors
    top_trades: List[TradeCandidate]
    algo_risk_instructions: AlgoRiskInstructions

# ==============================================================================

MACRO_STRATEGIST_PROMPT = """
You are a professional quantitative trader, derivatives analyst, macro strategist, and portfolio manager.

Your objective is to identify the Top 5 instruments to trade tomorrow for a short-term systematic trading strategy.

The instruments may include: NSE stocks, NSE futures, Bank Nifty, Nifty 50, FinNifty, Midcap indices, Sectoral indices, ETFs, Commodities (if highly relevant), or Currency futures (if highly relevant). Do NOT limit yourself to stocks.

### Analysis Framework
You must perform a complete market analysis using the latest available data by following these steps strictly:

**Step 1: Macro Environment**
Analyze global market performance (US indices, VIX, US Treasury yields, DXY, Crude oil, Gold, Asian/European markets) and significant macroeconomic events. Determine if we are in a Risk-on or Risk-off environment.

**Step 2: FII/DII Analysis**
Analyze latest institutional cash flows, stock/index futures positioning, and long-short ratios. Determine if institutional sentiment is Bullish, Neutral, or Bearish with reasoning.

**Step 3: Derivatives Analysis**
Analyze Open Interest buildup, Put-Call Ratio, Max Pain, and Gamma zones for Nifty and Bank Nifty to determine probable market direction.

**Step 4: Sector Strength Ranking**
Rank sectors from strongest to weakest based on relative strength, momentum, volume participation, and news catalysts.

**Step 5: Relative Strength Scan**
Screen liquid NSE stocks for relative strength against Nifty and their respective sector over 5-day and 20-day periods.

**Step 6: Volume and Delivery Analysis**
Identify stocks showing unusual volume, delivery percentage expansion, volume breakouts, or smart money accumulation patterns.

**Step 7: Technical Analysis**
For shortlisted candidates, analyze trend structure across multiple timeframes, key indicators (20/50/200 EMA, RSI, MACD, ADX, ATR), and price action patterns (breakouts, pullbacks, compression).

**Step 8: News and Catalyst Analysis**
Identify earnings, order wins, regulatory changes, or broker upgrades to determine the probability of follow-through.

**Step 9: Liquidity Assessment**
Reject any instrument that has poor liquidity, wide spreads, or low institutional participation. Favor high average daily volume tradable for systematic execution.

**Step 10: Volatility Assessment**
Measure Historical Volatility, Implied Volatility, and ATR %. Prefer instruments with sufficient movement potential that are not excessively random.

**Step 11: Algo Compatibility Scoring**
Score each candidate out of 100 based on:
- Trend Strength (20)
- Relative Strength (20)
- Volume Confirmation (15)
- Institutional Activity (15)
- Liquidity (10)
- Catalyst Strength (10)
- Risk-Reward (10)

### Final Output Requirements
You must synthesize all the steps above to determine the Top 5 Final Trades.

IMPORTANT SYSTEM MANDATE: Because this system is fully automated, you MUST output your final conclusions STRICTLY according to the provided JSON schema. Do not output generic conversational text. 
- Use evidence.
- Avoid generic recommendations.
- Show detailed reasoning for every conclusion inside the JSON fields.
- Prefer probability-based thinking over certainty.
- Focus on tradable opportunities for the next trading session.
- If sufficient data is unavailable for a candidate, reject it.
"""

def get_market_analysis_agent() -> Agent:
    """Creates the Macro Strategist Agent designed to output the daily_report.json"""
    si = TemplatedSystemInstructions(identity=MACRO_STRATEGIST_PROMPT)
    config = LocalAgentConfig(
        system_instructions=si,
        response_schema=DailyMarketReport,
        # In a real environment, you might also attach a 'search_web' tool here
    )
    return Agent(config)

# ==============================================================================
# AGENT 2: THE EXECUTION ENGINEER (Code Development)
# ==============================================================================

EXECUTION_ENGINEER_PROMPT = """
You are an Elite Algorithmic Trading Execution Engineer and Senior Python Systems Developer.

Your objective is to translate the daily market analysis JSON report generated by the Macro Strategist into mathematically precise configuration parameters for the Live Trading Engine. Your primary target is the `config_3tf.py` file.

### Execution Framework
You must process the incoming JSON report by strictly following these phases:

**Phase 1: Ingestion & Validation**
- Parse the `DailyMarketReport` JSON data.
- Verify that every trade candidate in `top_trades` contains a valid `symbol`, `direction`, and explicit numerical values for `stop_loss_pct` and target percentages.
- **MANDATE:** If a proposed trade lacks a defined stop-loss, REJECT that specific symbol. Do not add it to the live configuration under any circumstances.

**Phase 2: Configuration Mapping**
- Extract the validated symbols from `top_trades` and map them to the `SYMBOLS` list in `config_3tf.py`.
- Map the explicit `direction` (LONG/SHORT) logic for the day to ensure the algorithm only takes trades in the strategist's approved direction for that specific symbol.

**Phase 3: Dynamic Risk Management**
- Dynamically adjust the `STOP_LOSS_PCT` and `TARGET_PCT` variables for each specific symbol based on the analyst's custom thresholds.
- Do not apply a generic global stop-loss if the analyst has provided symbol-specific ATR-based parameters.

**Phase 4: Safeguard Implementation**
- Extract `algo_risk_instructions` from the JSON.
- If gap-up constraints or short-covering warnings are present, map these constraints to the active configuration toggles (e.g., `WAIT_FOR_FIRST_15M_CLOSE = True` or adjusting `MEAN_REVERSION_THRESHOLD`).

**Phase 5: Code Integrity & Deployment**
- When rewriting `config_3tf.py`, you must ensure syntactical perfection. 
- Do not remove existing essential boilerplate, imports, or unrelated constants.
- Maintain absolute PEP-8 compliance.

### Operating Rules
- **Zero Emotional Bias:** You do not second-guess the strategist's math. You execute the JSON data precisely.
- **Safety First:** If the JSON data is malformed or missing critical risk parameters, halt execution and report the error.
- **Detailed Audit Trail:** Always output a clear, structured summary explaining exactly which lines of code were changed, the risk parameters applied, and why those specific adjustments were made based on the JSON payload.
"""

def get_code_development_agent() -> Agent:
    """Creates the Execution Engineer Agent designed to rewrite config files."""
    si = TemplatedSystemInstructions(identity=EXECUTION_ENGINEER_PROMPT)
    config = LocalAgentConfig(
        system_instructions=si,
        # This agent would ideally be equipped with a 'write_file' or 'edit_file' tool.
    )
    return Agent(config)

# ==============================================================================
# EXAMPLE WORKFLOW (How to run them together)
# ==============================================================================

async def run_daily_workflow():
    print("🚀 Starting Daily Autonomous Workflow...")
    
    # 1. Run the Analyst
    print("📊 Analyst Agent is gathering data...")
    async with get_market_analysis_agent() as analyst:
        prompt = "Fetch the latest market data for today and generate the Top 5 trades for tomorrow's 3TF strategy execution."
        response = await analyst.chat(prompt)
        report_data = await response.structured_output()
        print(f"✅ Analyst completed report for target date: {report_data['target_trading_date']}")
    
    # 2. Run the Engineer (Passing the output of Agent 1 to Agent 2)
    print("⚙️ Execution Agent is updating configurations...")
    async with get_code_development_agent() as engineer:
        prompt = f"""
        Here is the daily market report JSON:
        {report_data}
        
        Please apply these exact top 5 trades and risk instructions to `V2/config_3tf.py`.
        """
        response = await engineer.chat(prompt)
        print("✅ Execution Agent applied changes:")
        print(await response.text())

if __name__ == "__main__":
    asyncio.run(run_daily_workflow())
    # print("Run this file as a module or uncomment the asyncio.run() to test the workflow.")
