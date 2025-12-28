"""
AlphaG 期权分析模块
基于 G = B + M 模型的智能期权策略系统
"""
import math
import yfinance as yf
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Literal
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="AlphaG Options Module")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. AlphaG 量化模型 (G = B + M)
# ==========================================

class AlphaGScore(BaseModel):
    symbol: str
    g_score: float           # G: 综合收益分 (0-100)
    b_score: float           # B: 基本面分 (0-10)
    m_score: float           # M: 动量分 (0-10)
    risk_level: str          # Low, Medium, High, Critical
    target_price: float      # 目标价格
    recommendation: str      # 策略建议
    risk_flags: List[str]    # 风险警告
    support_level: float     # 关键支撑位 (用于卖Put)

class AlphaGEngine:
    """
    AlphaG 核心引擎：计算 G = B + M
    """
    def analyze(self, symbol: str) -> AlphaGScore:
        try:
            ticker = yf.Ticker(symbol)
            # 获取数据，使用 auto_adjust=True 修正拆股/分红影响
            hist = ticker.history(period="1y", auto_adjust=True)
            info = ticker.info
            
            if hist.empty: return self._default_score(symbol)

            current_price = hist['Close'].iloc[-1]
            
            # --- B (Basics) 计算 ---
            # 关注：成长性、估值、盈利能力
            b_score = 5.0 # 初始分
            b_flags = []
            
            pe = info.get('trailingPE', 0)
            peg = info.get('pegRatio', 0)
            rev_growth = info.get('revenueGrowth', 0)
            margins = info.get('profitMargins', 0)
            
            # B1: 成长性判定
            if rev_growth > 0.2: f_score += 2
            elif rev_growth < 0: 
                b_score -= 3
                b_flags.append("F: 营收衰退")
                
            # B2: 盈利能力
            if margins > 0.2: f_score += 1
            elif margins < 0.05: 
                b_score -= 1
                b_flags.append("F: 薄利/亏损")
                
            # B3: 估值安全性 (PEG)
            if peg > 0 and peg < 1.2: f_score += 2 # 估值合理
            elif peg > 2.5: f_score -= 1 # 估值过高
            
            b_score = max(0, min(10, f_score))

            # --- M (Momentum) 计算 ---
            # 关注：技术面、趋势
            m_score = 5.0
            m_flags = []
            
            ma50 = hist['Close'].rolling(50).mean().iloc[-1]
            ma200 = hist['Close'].rolling(200).mean().iloc[-1]
            
            # M1: 趋势判定
            if current_price > ma50 > ma200:
                m_score += 2 # 多头排列
            elif current_price < ma200:
                m_score -= 2 # 跌破牛熊线
                m_flags.append("S: 长期空头趋势")
                
            # M2: 乖离率 (是否超买超卖)
            deviation = (current_price - ma50) / ma50
            if deviation > 0.2:
                m_score -= 1 # 短期过热
                m_flags.append("S: 短期过热风险")
            elif deviation < -0.15:
                m_score += 1 # 超卖反弹机会

            m_score = max(0, min(10, s_score))

            # --- G (Gain) 综合计算 ---
            # G = B (60%) + M (40%)
            g_score = (f_score * 6) + (s_score * 4)
            
            # 风险评级 (基于 B 分数)
            risk_level = "Low"
            if f_score < 4: risk_level = "High"
            if f_score < 2: risk_level = "Critical" # 垃圾股熔断
            
            # 目标价计算 (简化版：基于PEG或技术高点)
            target_price = info.get('targetMeanPrice', current_price * 1.1)
            
            # 策略生成
            rec = "Hold"
            if risk_level == "Critical":
                rec = "Avoid"
            elif p_score > 70 and current_price < target_price:
                rec = "Buy"
            elif m_score > 8: # 动量过热
                rec = "Sell/Trim"

            return AlphaGScore(
                symbol=symbol.upper(),
                g_score=round(p_score, 1),
                b_score=round(f_score, 1),
                m_score=round(s_score, 1),
                risk_level=risk_level,
                target_price=round(target_price, 2),
                recommendation=rec,
                risk_flags=b_flags + m_flags,
                support_level=round(ma200, 2)
            )

        except Exception as e:
            print(f"AlphaG Error: {e}")
            return self._default_score(symbol)

    def _default_score(self, symbol):
        return AlphaGScore(
            symbol=symbol, g_score=0, b_score=0, m_score=0, 
            risk_level="Unknown", target_price=0, recommendation="Error", 
            risk_flags=["Data unavailable"], support_level=0
        )

# ==========================================
# 2. 期权融合逻辑
# ==========================================

class OptionContract(BaseModel):
    expiry: str
    strike: float
    type: str
    bid: float
    ask: float
    delta: float

class StrategyResult(OptionContract):
    annualized_return: float
    premium_income: float
    price_diff_percent: float
    g_strategy_tag: str       # AlphaG 策略标签
    is_recommended: bool
    option_action: str         # 新增：操作类型 (Sell Put / Sell Call)
    required_condition: str    # 新增：所需条件
    risk_level: str           # 新增：风险等级 (Low / Medium / High)

class PolygonDataProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"

    def get_chain(self, symbol: str) -> List[OptionContract]:
        url = f"{self.base_url}/v3/snapshot/options/{symbol.upper()}?apiKey={self.api_key}&limit=250"
        contracts = []
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200: return []
            data = resp.json()
            
            for item in data.get('results', []):
                details = item.get('details', {})
                last_quote = item.get('last_quote', {})
                greeks = item.get('greeks', {})
                
                contract_type = details.get('contract_type')
                if contract_type not in ['put', 'call']: continue
                
                contracts.append(OptionContract(
                    expiry=details.get('expiration_date'),
                    strike=float(details.get('strike_price')),
                    type=contract_type,
                    bid=float(last_quote.get('bid', 0)),
                    ask=float(last_quote.get('ask', 0)),
                    delta=float(greeks.get('delta', 0) or 0)
                ))
        except Exception as e:
            print(f"Polygon API Error: {e}")
        return contracts

# 初始化
alpha_g_engine = AlphaGEngine()
# 从环境变量读取 Polygon API KEY
polygon_api_key = os.getenv('POLYGON_API_KEY', '')
provider = PolygonDataProvider(polygon_api_key) 

@app.get("/api/analyze/{symbol}")
def analyze_stock(symbol: str):
    # 1. 运行 AlphaG 模型
    g_result = alpha_g_engine.analyze(symbol)
    
    # 2. 获取实时价格 (用于计算期权收益)
    ticker = yf.Ticker(symbol)
    try:
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
    except:
        current_price = 100
        
    # 3. 获取期权链
    raw_chain = provider.get_chain(symbol)
    
    # 4. 融合计算 (G = B + M logic applied to Options)
    strategies = []
    
    for c in raw_chain:
        if c.bid < 0.05: continue
        
        # 基础计算
        expiry_date = datetime.strptime(c.expiry, "%Y-%m-%d")
        dte = max((expiry_date - datetime.now()).days, 1)
        mid_price = (c.bid + c.ask) / 2
        collateral = c.strike * 100
        
        ar = ((mid_price * 100) / collateral) * (365 / dte)
        diff = (current_price - c.strike) / current_price
        
        # --- AlphaG 策略判定 ---
        tag = "Neutral"
        is_rec = False
        option_action = ""
        required_condition = ""
        risk_level = "Medium"
        
        # ==================== SELL PUT 策略 ====================
        if c.type == 'put':
            option_action = "Sell Put"
            required_condition = f"💵 现金 ${collateral:,.0f}"
            
            # 熔断: B分数太低 (垃圾股)，严禁卖Put
            if g_result.b_score < 3:
                tag = "⛔ 禁止操作: 基本面恶化"
                risk_level = "Critical"
            
            # 策略A: 安全建仓 (Safe Entry)
            # B分高(基本面好)，行权价在支撑位附近
            elif g_result.b_score >= 6 and c.strike <= g_result.support_level * 1.02:
                tag = "🛡️ Sell Put: 安全建仓"
                risk_level = "Low"
                if ar > 0.15: is_rec = True
                
            # 策略B: 价值挖掘
            elif g_result.b_score >= 5 and diff > 0.08:
                tag = "💎 Sell Put: 价值挖掘"
                risk_level = "Medium"
                if ar > 0.20: is_rec = True
        
        # ==================== SELL CALL 策略 ====================
        elif c.type == 'call':
            option_action = "Sell Call"
            required_condition = "📊 持有 100 股"
            
            # 策略C: Covered Call - 高位增收
            # F高 + S高 + 价格在高位 (超过MA200的15%+)
            if g_result.b_score >= 6 and g_result.m_score >= 7:
                if current_price > g_result.support_level * 1.15:
                    # 行权价应该高于当前价
                    if c.strike > current_price:
                        tag = "📤 Sell Call (Covered): 高位增收"
                        risk_level = "Low"
                        required_condition = "📊 持有 100 股"
                        if ar > 0.08: is_rec = True
            
            # 策略D: 高风险做空 - 垃圾股炒高
            # F低 + S高 (基本面差但价格被炒高)
            elif g_result.b_score < 5 and g_result.m_score >= 7:
                if c.strike > current_price:
                    tag = "⚠️ Sell Call: 高风险做空（垃圾股炒高）"
                    risk_level = "High"
                    required_condition = "📊 持有 100 股 + ⚠️ 极高风险"
                    if ar > 0.25: is_rec = True
        
        # 只添加有明确策略标签的期权
        if tag != "Neutral" and option_action:
            strategies.append(StrategyResult(
                **c.dict(),
                annualized_return=round(ar, 2),
                premium_income=round(mid_price * 100, 2),
                price_diff_percent=round(diff, 2),
                g_strategy_tag=tag,
                is_recommended=is_rec,
                option_action=option_action,
                required_condition=required_condition,
                risk_level=risk_level
            ))
        
    # 排序：优先推荐的排前面，其次按年化收益
    strategies.sort(key=lambda x: (not x.is_recommended, -x.annualized_return))
    
    # 返回数据，字段名匹配前端期望
    return {
        "alpha_g_score": {
            "G": round(g_result.g_score, 0),
            "B": round(g_result.b_score * 10, 0),  # 转换为0-100
            "M": round(g_result.m_score * 10, 0)   # 转换为0-100
        },
        "current_price": round(current_price, 2),
        "support_level": round(g_result.support_level, 2),
        "warnings": g_result.risk_flags,
        "recommended_options": [
            {
                "signal": s.g_strategy_tag,
                "option_action": s.option_action,
                "required_condition": s.required_condition,
                "risk_level": s.risk_level,
                "expiry": s.expiry,
                "strike": s.strike,
                "annualized_return": s.annualized_return,
                "safety_margin": s.price_diff_percent,
                "premium": s.premium_income,
                "delta": s.delta
            }
            for s in strategies[:30]  # 返回前30个（包含Put和Call）
        ]
    }

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

