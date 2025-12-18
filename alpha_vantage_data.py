"""
Alpha Vantage 数据获取模块
作为 Yahoo Finance 的备用数据源
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import requests

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from alpha_vantage.timeseries import TimeSeries
    from alpha_vantage.fundamentaldata import FundamentalData
    ALPHA_VANTAGE_AVAILABLE = True
except ImportError:
    ALPHA_VANTAGE_AVAILABLE = False
    TimeSeries = None
    FundamentalData = None

# 从环境变量或配置获取 API Key
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')


def normalize_ticker_for_av(ticker):
    """
    将股票代码标准化为 Alpha Vantage 格式
    Alpha Vantage 只支持美股，所以需要去掉后缀
    """
    # 去掉所有后缀（.HK, .SS, .SZ 等）
    normalized = ticker.upper()
    if '.' in normalized:
        normalized = normalized.split('.')[0]
    return normalized


def get_market_data_from_av(ticker, only_history=False, start_date=None):
    """
    从 Alpha Vantage 获取股票市场数据
    
    参数:
        ticker: 股票代码
        only_history: 是否只获取历史数据
        start_date: 开始日期（可选）
    
    返回:
        data: 包含市场数据的字典，格式与 Yahoo Finance 兼容
    """
    if not ALPHA_VANTAGE_AVAILABLE:
        raise Exception("Alpha Vantage 库未安装")
    
    if not ALPHA_VANTAGE_API_KEY:
        raise Exception("Alpha Vantage API Key 未配置，请在环境变量中设置 ALPHA_VANTAGE_API_KEY")
    
    normalized_ticker = normalize_ticker_for_av(ticker)
    
    # Alpha Vantage 只支持美股，如果不是美股则抛出异常
    if any(ticker.endswith(suffix) for suffix in ['.HK', '.SS', '.SZ', '.TW', '.KS']):
        raise Exception(f"Alpha Vantage 仅支持美股数据，不支持 {ticker}")
    
    try:
        ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        
        # Alpha Vantage 免费版有速率限制：每分钟5次请求，每天500次
        # 因此需要控制请求频率
        
        if only_history:
            # 获取日线数据（每日）
            # Alpha Vantage 提供：full（20年）或 compact（最近100个数据点）
            # 使用 get_daily 而不是 get_daily_adjusted（免费版支持）
            data, meta_data = ts.get_daily(symbol=normalized_ticker, outputsize='full')
            
            if data is None or data.empty:
                raise Exception("Alpha Vantage 返回空数据")
            
            # 转换为需要的格式（免费版使用 close 价格）
            history_dates = data.index.strftime('%Y-%m-%d').tolist()
            history_prices = data['4. close'].tolist()
            
            return {
                "history_dates": history_dates,
                "history_prices": [float(p) for p in history_prices],
            }
        
        # 获取实时数据
        # 使用 get_daily 获取最近的日线数据（免费版支持）
        try:
            # 使用日线数据获取当前价格（免费版）
            daily_data, _ = ts.get_daily(symbol=normalized_ticker, outputsize='compact')
            if daily_data is None or daily_data.empty:
                raise Exception("无法获取价格数据")
            latest_data = daily_data.iloc[-1]
            current_price = float(latest_data['4. close'])
        except Exception as e:
            # 如果 compact 失败，尝试 full
            daily_data, _ = ts.get_daily(symbol=normalized_ticker, outputsize='full')
            if daily_data is None or daily_data.empty:
                raise Exception(f"获取价格数据失败: {str(e)}")
            latest_data = daily_data.iloc[-1]
            current_price = float(latest_data['4. close'])
        
        # 获取日线数据用于历史价格和52周高低价
        if 'daily_data' not in locals() or len(daily_data) < 252:
            daily_data, _ = ts.get_daily(symbol=normalized_ticker, outputsize='full')
        
        if daily_data is None or daily_data.empty:
            raise Exception("无法获取历史数据")
        
        # 计算52周高低价（最近252个交易日约等于1年）
        recent_year = daily_data.tail(252)
        week52_high = float(recent_year['2. high'].max()) if '2. high' in recent_year.columns else current_price * 1.2
        week52_low = float(recent_year['3. low'].min()) if '3. low' in recent_year.columns else current_price * 0.8
        
        # 准备历史数据（使用 close 价格，因为免费版不支持 adjusted close）
        history_dates = daily_data.index.strftime('%Y-%m-%d').tolist()
        history_prices = daily_data['4. close'].tolist()
        
        # 计算移动平均线
        closes = daily_data['4. close']
        ma50 = float(closes.tail(50).mean()) if len(closes) >= 50 else current_price
        ma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else current_price
        
        # 计算成交量异常
        volume_anomaly = None
        if '6. volume' in daily_data.columns and len(daily_data) >= 30:
            volumes = daily_data['6. volume']
            recent_volume_avg = float(volumes.tail(5).mean())
            historical_volume_avg = float(volumes.tail(30).mean())
            if historical_volume_avg > 0:
                volume_ratio = recent_volume_avg / historical_volume_avg
                volume_anomaly = {
                    'ratio': float(volume_ratio),
                    'is_anomaly': bool(volume_ratio > 2.0 or volume_ratio < 0.3),
                    'recent_avg': recent_volume_avg,
                    'historical_avg': historical_volume_avg
                }
        
        # Alpha Vantage 不直接提供财务数据（PE, PEG等），需要通过 FundamentalData API
        # 但免费版不支持，所以这些值设为默认值或 None
        pe_ratio = 0
        forward_pe = 0
        peg_ratio = 0
        rev_growth = 0
        profit_margin = 0
        market_cap = 0
        beta = None
        
        # 尝试获取基本面数据（需要 Premium 版本）
        try:
            if FundamentalData:
                fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
                # 注意：免费版可能不支持这些功能
                # company_overview, _ = fd.get_company_overview(symbol=normalized_ticker)
                # 这里暂时跳过，因为免费版限制较多
        except:
            pass
        
        # 构建返回数据（格式与 Yahoo Finance 兼容）
        data = {
            "symbol": normalized_ticker,
            "currency_symbol": "$",
            "original_symbol": ticker,
            "name": normalized_ticker,  # Alpha Vantage 不提供公司名称，使用代码
            "sector": "Unknown",
            "industry": "Unknown",
            "price": float(current_price),
            "week52_high": float(week52_high),
            "week52_low": float(week52_low),
            "pe": float(pe_ratio),
            "forward_pe": float(forward_pe),
            "peg": float(peg_ratio),
            "growth": float(rev_growth),
            "margin": float(profit_margin),
            "ma50": float(ma50),
            "ma200": float(ma200),
            "market_cap": market_cap,
            "history_dates": history_dates,
            "history_prices": [float(p) for p in history_prices],
            "volume_anomaly": volume_anomaly,
            "earnings_dates": [],  # Alpha Vantage 免费版不提供
            "atr": None,  # 需要计算
            "beta": beta,
            "data_source": "Alpha Vantage"  # 标记数据来源
        }
        
        # 计算 ATR（如果有足够的历史数据）
        if len(daily_data) >= 15:
            try:
                from analysis_engine import calculate_atr
                # 重命名列以匹配 calculate_atr 的期望格式
                hist_for_atr = daily_data.rename(columns={
                    '2. high': 'High',
                    '3. low': 'Low',
                    '4. close': 'Close'
                })
                data['atr'] = calculate_atr(hist_for_atr, period=14)
            except Exception as e:
                print(f"计算 ATR 失败: {e}")
        
        return data
        
    except Exception as e:
        error_msg = str(e)
        # 检查是否是速率限制错误
        if "API call frequency" in error_msg or "Thank you for using Alpha Vantage" in error_msg:
            raise Exception(f"Alpha Vantage 速率限制：{error_msg}")
        raise Exception(f"从 Alpha Vantage 获取数据失败: {error_msg}")


def is_av_available():
    """
    检查 Alpha Vantage 是否可用（库已安装且 API Key 已配置）
    """
    return ALPHA_VANTAGE_AVAILABLE and bool(ALPHA_VANTAGE_API_KEY)


