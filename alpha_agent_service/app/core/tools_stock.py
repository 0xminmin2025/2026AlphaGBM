"""
股市工具：基于G=B+M模型的数据获取
支持A股（Tushare）、美股/港股（YFinance）
"""
import yfinance as yf
import tushare as ts
import os
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from app.config import settings

# 初始化 Tushare
if settings.TUSHARE_TOKEN:
    ts.set_token(settings.TUSHARE_TOKEN)
    pro = ts.pro_api()
else:
    pro = None


@tool
def get_stock_metrics(ticker: str) -> Dict[str, Any]:
    """
    获取股票的核心 G=B+M 指标。
    
    Args:
        ticker: 股票代码 (如 'AAPL', '600519', '0700.HK', '9988.HK')
    
    Returns:
        包含G=B+M指标的字典，或错误信息字符串
    """
    data: Dict[str, Any] = {}
    
    # --- A股处理逻辑 (Tushare) ---
    if ticker.isdigit() or ticker.endswith(('.SH', '.SZ')):
        if not pro:
            return {"error": "Tushare未配置，无法获取A股数据"}
        
        code = ticker
        if code.isdigit():
            # 自动判断市场
            if code.startswith(('6', '688')):
                code = f"{code}.SH"
            elif code.startswith(('0', '3')):
                code = f"{code}.SZ"
            else:
                return {"error": f"无法识别的A股代码: {ticker}"}
        
        try:
            # 1. 行情数据 (G - 价格位置)
            df_daily = pro.daily(ts_code=code, limit=1)
            
            # 2. 每日指标 (M - 估值指标)
            df_basic = pro.daily_basic(
                ts_code=code, 
                limit=1, 
                fields='ts_code,pe_ttm,pb,total_mv,turnover_rate'
            )
            
            # 3. 财务指标 (B - 基本面)
            df_fina = pro.fina_indicator(
                ts_code=code, 
                limit=1, 
                fields='tr_yoy,q_dt_roe,roe_avg,netprofit_yoy'
            )
            
            if not df_daily.empty:
                daily_data = df_daily.iloc[0]
                basic_data = df_basic.iloc[0] if not df_basic.empty else {}
                fina_data = df_fina.iloc[0] if not df_fina.empty else {}
                
                data = {
                    "market": "CN",
                    "ticker": code,
                    # G (价格位置)
                    "price": float(daily_data['close']),
                    "change_pct": float(daily_data['pct_chg']),
                    "high_52w": None,  # Tushare需要单独查询
                    "low_52w": None,
                    # M (估值/情绪)
                    "pe_ttm": float(basic_data.get('pe_ttm', 0)) if basic_data.get('pe_ttm') else None,
                    "pb": float(basic_data.get('pb', 0)) if basic_data.get('pb') else None,
                    "market_cap": float(basic_data.get('total_mv', 0)) if basic_data.get('total_mv') else None,
                    "turnover_rate": float(basic_data.get('turnover_rate', 0)) if basic_data.get('turnover_rate') else None,
                    # B (基本面)
                    "revenue_growth": float(fina_data.get('tr_yoy', 0)) if fina_data.get('tr_yoy') else None,
                    "roe": float(fina_data.get('q_dt_roe', 0)) if fina_data.get('q_dt_roe') else None,
                    "netprofit_growth": float(fina_data.get('netprofit_yoy', 0)) if fina_data.get('netprofit_yoy') else None,
                    "source": "Tushare Pro"
                }
            else:
                return {"error": f"未找到股票数据: {code}"}
                
        except Exception as e:
            return {"error": f"A股数据获取失败: {str(e)}"}

    # --- 美股/港股处理逻辑 (YFinance) ---
    else:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 获取历史数据计算52周高低
            hist = stock.history(period="1y")
            high_52w = float(hist['High'].max()) if not hist.empty else None
            low_52w = float(hist['Low'].min()) if not hist.empty else None
            
            # 补全 G=B+M 所需字段
            data = {
                "market": "Global",
                "ticker": ticker,
                # G (价格位置)
                "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                "change_pct": info.get('regularMarketChangePercent'),
                "high_52w": high_52w,
                "low_52w": low_52w,
                # M (估值/情绪)
                "pe_ttm": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),  # 重要的M指标
                "market_cap": info.get('marketCap'),
                # B (基本面)
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth'),
                "profit_margin": info.get('profitMargins'),
                "roe": info.get('returnOnEquity'),
                "eps": info.get('trailingEps'),
                "source": "Yahoo Finance"
            }
            
            # 清理None值
            data = {k: v for k, v in data.items() if v is not None}
            
        except Exception as e:
            return {"error": f"全球市场数据获取失败: {str(e)}"}

    return data


@tool
def get_stock_news(ticker: str, limit: int = 5) -> Dict[str, Any]:
    """
    获取股票相关新闻（用于M情绪分析）
    
    Args:
        ticker: 股票代码
        limit: 返回新闻数量
    
    Returns:
        新闻列表
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:limit]
        
        return {
            "ticker": ticker,
            "news": [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": item.get("providerPublishTime", 0)
                }
                for item in news
            ]
        }
    except Exception as e:
        return {"error": f"获取新闻失败: {str(e)}"}
