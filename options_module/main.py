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
# 2. 期权策略选择引擎（全新版本）
# ==========================================

class OptionsStrategySelector:
    """
    AlphaGBM 期权策略选择器
    基于 G=B+M 模型的智能期权策略选择系统
    """
    
    def __init__(self):
        """初始化策略选择器"""
        self.min_premium = 0.05  # 最小权利金，过滤噪音
        self.min_dte = 7  # 最小到期日，避免过短周期
        self.max_dte = 90  # 最大到期日，避免过长周期
    
    def select_strategies(
        self,
        contracts: List[OptionContract],
        g_result: AlphaGScore,
        current_price: float
    ) -> List[StrategyResult]:
        """
        核心方法：选择最优期权策略
        
        Args:
            contracts: 期权合约列表
            g_result: AlphaG分析结果
            current_price: 当前股价
            
        Returns:
            策略结果列表，按优先级排序
        """
        strategies = []
        
        for contract in contracts:
            # 基础过滤
            if not self._is_valid_contract(contract):
                continue
            
            # 计算基础指标
            metrics = self._calculate_metrics(contract, current_price)
            if not metrics:
                continue
            
            # 策略评估
            strategy = self._evaluate_strategy(
                contract, g_result, current_price, metrics
            )
            
            if strategy:
                strategies.append(strategy)
        
        # 排序：优先推荐的排前面，其次按年化收益，最后低风险优先
        strategies.sort(key=lambda x: (
            not x.is_recommended,
            -x.annualized_return,
            x.risk_level == "Low"
        ))
        
        return strategies
    
    def _is_valid_contract(self, contract: OptionContract) -> bool:
        """验证合约是否有效"""
        if contract.bid < self.min_premium:
            return False
        
        # 检查到期日
        try:
            expiry_date = datetime.strptime(contract.expiry, "%Y-%m-%d")
            dte = (expiry_date - datetime.now()).days
            if dte < self.min_dte or dte > self.max_dte:
                return False
        except:
            return False
        
        return True
    
    def _calculate_metrics(
        self, 
        contract: OptionContract, 
        current_price: float
    ) -> Optional[dict]:
        """计算期权关键指标"""
        try:
            expiry_date = datetime.strptime(contract.expiry, "%Y-%m-%d")
            dte = max((expiry_date - datetime.now()).days, 1)
            
            mid_price = (contract.bid + contract.ask) / 2
            collateral = contract.strike * 100
            
            # 年化收益率
            annualized_return = ((mid_price * 100) / collateral) * (365 / dte)
            
            # 价格差异百分比
            price_diff_percent = (current_price - contract.strike) / current_price
            
            return {
                'dte': dte,
                'mid_price': mid_price,
                'collateral': collateral,
                'annualized_return': annualized_return,
                'price_diff_percent': price_diff_percent,
            }
        except Exception as e:
            print(f"计算指标失败: {e}")
            return None
    
    def _evaluate_strategy(
        self,
        contract: OptionContract,
        g_result: AlphaGScore,
        current_price: float,
        metrics: dict
    ) -> Optional[StrategyResult]:
        """评估单个合约的策略"""
        
        if contract.type == 'put':
            return self._evaluate_put_strategy(
                contract, g_result, current_price, metrics
            )
        elif contract.type == 'call':
            return self._evaluate_call_strategy(
                contract, g_result, current_price, metrics
            )
        
        return None
    
    def _evaluate_put_strategy(
        self,
        contract: OptionContract,
        g_result: AlphaGScore,
        current_price: float,
        metrics: dict
    ) -> Optional[StrategyResult]:
        """评估 Sell Put 策略"""
        
        option_action = "Sell Put"
        required_condition = f"💵 现金 ${metrics['collateral']:,.0f}"
        tag = "Neutral"
        risk_level = "Medium"
        is_recommended = False
        
        # ========== 熔断规则 ==========
        # B分数太低（垃圾股），严禁卖Put
        if g_result.b_score < 3:
            tag = "⛔ 禁止操作: 基本面恶化"
            risk_level = "Critical"
            return StrategyResult(
                **contract.dict(),
                annualized_return=metrics['annualized_return'],
                premium_income=metrics['mid_price'] * 100,
                price_diff_percent=metrics['price_diff_percent'],
                g_strategy_tag=tag,
                is_recommended=False,
                option_action=option_action,
                required_condition=required_condition,
                risk_level=risk_level
            )
        
        # ========== 策略A: 安全建仓 ==========
        # 条件：B高(>=6) + 行权价在支撑位附近(<=支撑位*1.02) + 年化收益>=15%
        if (g_result.b_score >= 6 and 
            contract.strike <= g_result.support_level * 1.02 and
            metrics['annualized_return'] >= 0.15):
            tag = "🛡️ Sell Put: 安全建仓"
            risk_level = "Low"
            is_recommended = True
            
        # ========== 策略B: 价值挖掘 ==========
        # 条件：B中高(>=5) + 深度虚值(价格差异>8%) + 年化收益>=20%
        elif (g_result.b_score >= 5 and 
              metrics['price_diff_percent'] > 0.08 and
              metrics['annualized_return'] >= 0.20):
            tag = "💎 Sell Put: 价值挖掘"
            risk_level = "Medium"
            is_recommended = metrics['annualized_return'] >= 0.25
        
        # ========== 策略C: 温和建仓 ==========
        # 条件：B中等(>=4) + 行权价在支撑位下方 + 年化收益>=12%
        elif (g_result.b_score >= 4 and
              contract.strike < g_result.support_level and
              metrics['annualized_return'] >= 0.12):
            tag = "📊 Sell Put: 温和建仓"
            risk_level = "Medium"
            is_recommended = metrics['annualized_return'] >= 0.18
        
        # 如果没有匹配的策略，返回None
        if tag == "Neutral":
            return None
        
        return StrategyResult(
            **contract.dict(),
            annualized_return=round(metrics['annualized_return'], 2),
            premium_income=round(metrics['mid_price'] * 100, 2),
            price_diff_percent=round(metrics['price_diff_percent'], 2),
            g_strategy_tag=tag,
            is_recommended=is_recommended,
            option_action=option_action,
            required_condition=required_condition,
            risk_level=risk_level
        )
    
    def _evaluate_call_strategy(
        self,
        contract: OptionContract,
        g_result: AlphaGScore,
        current_price: float,
        metrics: dict
    ) -> Optional[StrategyResult]:
        """评估 Sell Call 策略（Covered Call）"""
        
        option_action = "Sell Call"
        required_condition = "📊 持有 100 股"
        tag = "Neutral"
        risk_level = "Medium"
        is_recommended = False
        
        # Covered Call 必须是虚值（行权价 > 当前价）
        if contract.strike <= current_price:
            return None
        
        # ========== 策略D: Covered Call - 高位增收 ==========
        # 条件：B高(>=6) + M高(>=7) + 价格在高位(>支撑位*1.15) + 年化收益>=8%
        if (g_result.b_score >= 6 and 
            g_result.m_score >= 7 and
            current_price > g_result.support_level * 1.15 and
            metrics['annualized_return'] >= 0.08):
            tag = "📤 Sell Call (Covered): 高位增收"
            risk_level = "Low"
            is_recommended = metrics['annualized_return'] >= 0.12
        
        # ========== 策略E: 高风险做空 ==========
        # 条件：B低(<5) + M高(>=7) + 年化收益>=25%
        elif (g_result.b_score < 5 and 
              g_result.m_score >= 7 and
              metrics['annualized_return'] >= 0.25):
            tag = "⚠️ Sell Call: 高风险做空（垃圾股炒高）"
            risk_level = "High"
            required_condition = "📊 持有 100 股 + ⚠️ 极高风险"
            is_recommended = metrics['annualized_return'] >= 0.30
        
        # ========== 策略F: 适度增收 ==========
        # 条件：B中高(>=5) + M中等(>=5) + 年化收益>=6%
        elif (g_result.b_score >= 5 and
              g_result.m_score >= 5 and
              metrics['annualized_return'] >= 0.06):
            tag = "💼 Sell Call (Covered): 适度增收"
            risk_level = "Medium"
            is_recommended = metrics['annualized_return'] >= 0.10
        
        # 如果没有匹配的策略，返回None
        if tag == "Neutral":
            return None
        
        return StrategyResult(
            **contract.dict(),
            annualized_return=round(metrics['annualized_return'], 2),
            premium_income=round(metrics['mid_price'] * 100, 2),
            price_diff_percent=round(metrics['price_diff_percent'], 2),
            g_strategy_tag=tag,
            is_recommended=is_recommended,
            option_action=option_action,
            required_condition=required_condition,
            risk_level=risk_level
        )

# ==========================================
# 3. 数据模型
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

# ==========================================
# 4. 初始化
# ==========================================

alpha_g_engine = AlphaGEngine()
polygon_api_key = os.getenv('POLYGON_API_KEY', '')
provider = PolygonDataProvider(polygon_api_key)
strategy_selector = OptionsStrategySelector() 

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
    
    # 4. 使用新的策略选择器（基于 G=B+M 模型）
    strategies = strategy_selector.select_strategies(
        contracts=raw_chain,
        g_result=g_result,
        current_price=current_price
    )
    
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

