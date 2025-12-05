import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def normalize_ticker(ticker):
    """
    标准化股票代码格式
    自动识别市场并添加后缀
    """
    ticker = ticker.strip().upper()
    
    # 如果已经包含市场后缀，直接返回
    if '.' in ticker:
        return ticker
    
    # 判断市场类型
    # 港股：4-5位数字（港股代码范围通常是0001-9999）
    if ticker.isdigit() and (len(ticker) == 4 or len(ticker) == 5):
        # 港股代码通常是4-5位数字，优先识别为港股
        return f"{ticker}.HK"
    
    # A股：6位数字，上海600/601/603/688开头，深圳000/001/002/300开头
    if ticker.isdigit() and len(ticker) == 6:
        if ticker.startswith(('600', '601', '603', '688')):
            return f"{ticker}.SS"  # 上海
        elif ticker.startswith(('000', '001', '002', '300')):
            return f"{ticker}.SZ"  # 深圳
    
    # 美股：默认不加后缀，或者已经是标准格式
    return ticker


def get_ticker_price(ticker):
    """获取股票的当前价格"""
    try:
         # 标准化股票代码
        normalized_ticker = normalize_ticker(ticker)
        print(f"原始代码: {ticker}, 标准化后: {normalized_ticker}")
        
        stock = yf.Ticker(normalized_ticker)

        # 尝试从info获取
        info = stock.info
        if info and len(info) >= 5:
            # 从info获取价格
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose') or 0)
            if current_price > 0:
                return current_price
    except Exception as e:
        print(f"从info获取价格失败: {e}")
    
    return None


def get_market_data(ticker, onlyHistoryData=False, startDate=None):
    """获取 Yahoo Finance 数据并清洗"""
    try:
        # 标准化股票代码
        normalized_ticker = normalize_ticker(ticker)
        print(f"原始代码: {ticker}, 标准化后: {normalized_ticker}")
        
        stock = yf.Ticker(normalized_ticker)

        if onlyHistoryData :
            try:
                if startDate:
                    hist = stock.history(start=startDate, timeout=30)
                else:
                    hist = stock.history(period="1y", timeout=30)
            except Exception as e:
                print(f"获取历史数据失败: {e}")
                hist = pd.DataFrame()

            if not hist.empty :
                history_dates = hist.index.strftime('%Y-%m-%d').tolist()
                history_prices = hist['Close'].tolist()
            else:
                # 如果没有历史数据，至少提供一个当前价格点
                from datetime import datetime
                history_dates = [datetime.now().strftime('%Y-%m-%d')]
                history_prices = []
            
            data = {
                "history_dates": history_dates,
                "history_prices": [float(p) for p in history_prices],
            }
            return data
        
        # 尝试获取信息，设置超时
        try:
            info = stock.info
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            info = {}
        
        # 尝试获取历史数据
        try:
            if startDate:
                hist = stock.history(start=startDate, timeout=30)
            else:
                hist = stock.history(period="1y", timeout=30)
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            hist = pd.DataFrame()
        
        # 如果info为空或数据不足，尝试其他方式获取价格
        if not info or len(info) < 5:
            # 尝试快速获取
            try:
                fast_info = stock.fast_info
                if hasattr(fast_info, 'last_price') and fast_info.last_price:
                    current_price = fast_info.last_price
                elif not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
            except:
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                else:
                    return None
        else:
            # 从info或hist获取价格
            current_price = (info.get('currentPrice') or 
                           info.get('regularMarketPrice') or 
                           info.get('previousClose') or 0)
            
            if current_price == 0 and not hist.empty:
                current_price = hist['Close'].iloc[-1]
            
            if current_price == 0:
                return None

        # 计算技术指标（如果有足够的历史数据）
        if not hist.empty and len(hist) >= 50:
            ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        else:
            ma50 = current_price
        
        if not hist.empty and len(hist) >= 200:
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        else:
            ma200 = current_price
        
        # 处理可能缺失的字段，使用安全的默认值
        pe_ratio = info.get('trailingPE') or info.get('forwardPE') or 0
        forward_pe = info.get('forwardPE') or 0
        peg_ratio = info.get('pegRatio') or 0
        rev_growth = info.get('revenueGrowth') or 0
        profit_margin = info.get('profitMargins') or 0
        
        # 确保数值类型正确
        try:
            pe_ratio = float(pe_ratio) if pe_ratio else 0
            forward_pe = float(forward_pe) if forward_pe else 0
            peg_ratio = float(peg_ratio) if peg_ratio else 0
            rev_growth = float(rev_growth) if rev_growth else 0
            profit_margin = float(profit_margin) if profit_margin else 0
        except (ValueError, TypeError):
            pe_ratio = forward_pe = peg_ratio = rev_growth = profit_margin = 0
        
        # 处理历史数据
        if not hist.empty:
            history_dates = hist.index.strftime('%Y-%m-%d').tolist()
            history_prices = hist['Close'].tolist()
            
            # 检测成交量异常（最近5天平均成交量 vs 过去30天平均成交量）
            if 'Volume' in hist.columns and len(hist) >= 30:
                recent_volume_avg = hist['Volume'].tail(5).mean()
                historical_volume_avg = hist['Volume'].tail(30).mean()
                if historical_volume_avg > 0:
                    volume_ratio = recent_volume_avg / historical_volume_avg
                    volume_anomaly = {
                        'ratio': float(volume_ratio),
                        'is_anomaly': bool(volume_ratio > 2.0 or volume_ratio < 0.3),  # 超过2倍或低于30%视为异常
                        'recent_avg': float(recent_volume_avg),
                        'historical_avg': float(historical_volume_avg)
                    }
                else:
                    volume_anomaly = None
            else:
                volume_anomaly = None
        else:
            # 如果没有历史数据，至少提供一个当前价格点
            from datetime import datetime
            history_dates = [datetime.now().strftime('%Y-%m-%d')]
            history_prices = [current_price]
            volume_anomaly = None
        
        # 获取52周高低价
        week52_high = (info.get('fiftyTwoWeekHigh') or 
                       info.get('52WeekHigh') or 
                       (hist['High'].max() if not hist.empty else current_price))
        week52_low = (info.get('fiftyTwoWeekLow') or 
                     info.get('52WeekLow') or 
                     (hist['Low'].min() if not hist.empty else current_price))
        
        # 确保价格数据有效
        if week52_high < current_price:
            week52_high = current_price * 1.2
        if week52_low > current_price:
            week52_low = current_price * 0.8
        
        # 获取财报日期（如果有）
        earnings_dates = []
        try:
            if hasattr(stock, 'calendar') and stock.calendar is not None:
                calendar = stock.calendar
                if calendar is not None and len(calendar) > 0:
                    # 获取最近的财报日期
                    if 'Earnings Date' in calendar:
                        earnings_dates = calendar['Earnings Date'].dropna().tolist()
        except:
            pass
        
        # 如果没有从calendar获取，尝试从info获取
        if not earnings_dates:
            try:
                if 'earningsDate' in info and info['earningsDate']:
                    earnings_dates = info['earningsDate']
                    if isinstance(earnings_dates, list):
                        earnings_dates = [str(d) for d in earnings_dates]
            except:
                pass
        
        # 获取市值（如果有）
        market_cap = info.get('marketCap') or info.get('totalAssets') or 0
        try:
            market_cap = float(market_cap) if market_cap else 0
        except (ValueError, TypeError):
            market_cap = 0

        # 货币代码 → 货币符号映射
        currency_map = {
            'USD': '$',
            'CNY': '¥',
            'HKD': 'HK$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'KRW': '₩',
            'INR': '₹',
            'AUD': 'A$',
            'CAD': 'C$',
            'SGD': 'S$',
            'TWD': 'NT$',
        }
        
        # 根据normalized_ticker后缀判断货币代码
        if normalized_ticker.endswith('.HK'):
            currency_code = 'HKD'
        elif normalized_ticker.endswith('.SS'):
            currency_code = 'CNY'
        elif normalized_ticker.endswith('.SZ'):
            currency_code = 'CNY'
        else:
            # 默认美股
            currency_code = 'USD'
        
        currency_symbol = currency_map.get(currency_code, '$')  # 未映射的保持原代码
        
        # 计算ATR（用于动态止损）
        atr_value = None
        beta = None
        if not hist.empty and len(hist) >= 15:  # 至少需要15天数据计算ATR
            atr_value = calculate_atr(hist, period=14)
            # 尝试获取Beta值（用于调整ATR倍数）
            try:
                beta = info.get('beta')
                if beta:
                    beta = float(beta)
            except (ValueError, TypeError):
                beta = None
        
        data = {
            "symbol": normalized_ticker,
            "currency_symbol": currency_symbol,
            "original_symbol": ticker,
            "name": info.get('longName') or info.get('shortName') or info.get('name') or normalized_ticker,
            "sector": info.get('sector', 'Unknown'),
            "industry": info.get('industry', 'Unknown'),
            "price": float(current_price),
            "week52_high": float(week52_high),
            "week52_low": float(week52_low),
            "pe": float(pe_ratio),
            "forward_pe": float(forward_pe),
            "peg": float(peg_ratio),
            "growth": float(rev_growth), # 小数形式
            "margin": float(profit_margin),
            "ma50": float(ma50),
            "ma200": float(ma200),
            "market_cap": market_cap,  # 市值（美元）
            "history_dates": history_dates,
            "history_prices": [float(p) for p in history_prices],
            "volume_anomaly": volume_anomaly,
            "earnings_dates": earnings_dates[:2] if earnings_dates else [],  # 只保留最近2个财报日期
            "atr": atr_value,  # ATR值，用于动态止损
            "beta": beta  # Beta值，用于调整ATR倍数
        }
        return data
    except Exception as e:
        import traceback
        print(f"Data Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def get_fed_meeting_dates():
    """
    获取美联储利率决议日期
    返回未来3个月内的FOMC会议日期
    """
    # 2025年FOMC会议日期（根据美联储官方日程）
    fed_meetings_2025 = [
        datetime(2025, 1, 28),  # 1月28-29日
        datetime(2025, 3, 18),  # 3月18-19日（含点阵图）
        datetime(2025, 5, 6),   # 5月6-7日
        datetime(2025, 6, 17),  # 6月17-18日（含点阵图）
        datetime(2025, 7, 29),  # 7月29-30日
        datetime(2025, 9, 16),  # 9月16-17日（含点阵图）
        datetime(2025, 10, 28), # 10月28-29日
        datetime(2025, 12, 9), # 12月9-10日（含点阵图）
    ]
    
    # 2026年部分日期（如果需要）
    fed_meetings_2026 = [
        datetime(2026, 1, 28),
        datetime(2026, 3, 18),
    ]
    
    all_meetings = fed_meetings_2025 + fed_meetings_2026
    today = datetime.now().date()
    
    # 筛选未来90天内的会议
    upcoming_meetings = []
    for meeting_date in all_meetings:
        meeting_date_only = meeting_date.date()
        days_until = (meeting_date_only - today).days
        if 0 <= days_until <= 90:  # 未来90天内
            upcoming_meetings.append({
                'date': meeting_date_only.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'has_dot_plot': bool(meeting_date.month in [3, 6, 9, 12])  # 季度会议含点阵图
            })
    
    return sorted(upcoming_meetings, key=lambda x: x['days_until'])[:3]  # 返回最近3个


def get_cpi_release_dates():
    """
    获取CPI发布日期
    CPI通常在每月中旬（10-15日）发布前一个月的数据
    """
    today = datetime.now().date()
    cpi_dates = []
    
    # 计算未来3个月的CPI发布日期
    for i in range(1, 4):
        # 下个月的数据在这个月发布
        target_month = today + relativedelta(months=i)
        # CPI通常在每月10-15日之间发布，我们假设是12日
        cpi_date = datetime(target_month.year, target_month.month, 12).date()
        
        # 如果12日是周末，调整到下一个工作日
        while cpi_date.weekday() >= 5:  # 周六或周日
            cpi_date += timedelta(days=1)
        
        days_until = (cpi_date - today).days
        if days_until >= 0:
            cpi_dates.append({
                'date': cpi_date.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'data_month': (target_month - relativedelta(months=1)).strftime('%Y年%m月')
            })
    
    return cpi_dates[:3]  # 返回最近3个


def get_options_expiration_dates():
    """
    获取期权到期日（交割日）
    美股期权规则：
    - 月度期权：每月第三个星期五
    - 季度期权：3月、6月、9月、12月的第三个星期五（四重到期日，Quadruple Witching）
    - 周度期权：每周五（但重要性较低，这里主要关注月度）
    
    返回未来3个月内的期权到期日
    """
    today = datetime.now().date()
    expiration_dates = []
    
    # 计算未来3个月的期权到期日
    for i in range(0, 4):  # 包括当前月
        target_month = today + relativedelta(months=i)
        year = target_month.year
        month = target_month.month
        
        # 找到该月第一个星期五
        first_day = datetime(year, month, 1).date()
        # 计算到第一个星期五需要多少天（星期五是4）
        days_to_first_friday = (4 - first_day.weekday()) % 7
        if days_to_first_friday == 0 and first_day.weekday() != 4:
            days_to_first_friday = 7
        
        first_friday = first_day + timedelta(days=days_to_first_friday)
        
        # 第三个星期五 = 第一个星期五 + 14天
        third_friday = first_friday + timedelta(days=14)
        
        # 如果第三个星期五已经过去，计算下个月的
        if third_friday < today and i == 0:
            # 计算下个月的
            next_month = today + relativedelta(months=1)
            year = next_month.year
            month = next_month.month
            first_day = datetime(year, month, 1).date()
            days_to_first_friday = (4 - first_day.weekday()) % 7
            if days_to_first_friday == 0 and first_day.weekday() != 4:
                days_to_first_friday = 7
            first_friday = first_day + timedelta(days=days_to_first_friday)
            third_friday = first_friday + timedelta(days=14)
        
        days_until = (third_friday - today).days
        
        # 只添加未来的日期
        if days_until >= 0:
            # 判断是否为季度到期日（四重到期日）
            is_quadruple_witching = month in [3, 6, 9, 12]
            
            expiration_dates.append({
                'date': third_friday.strftime('%Y-%m-%d'),
                'days_until': int(days_until),
                'month': month,
                'is_quadruple_witching': is_quadruple_witching,
                'type': '四重到期日（季度）' if is_quadruple_witching else '月度到期日'
            })
    
    # 去重并排序
    seen_dates = set()
    unique_dates = []
    for exp_date in expiration_dates:
        if exp_date['date'] not in seen_dates:
            seen_dates.add(exp_date['date'])
            unique_dates.append(exp_date)
    
    return sorted(unique_dates, key=lambda x: x['days_until'])[:3]  # 返回最近3个


def get_market_warnings(macro_data, options_data, data):
    """
    生成市场预警信息
    提前提醒即将发生的风险和重要事件
    返回预警列表，每个预警包含：级别、类型、消息、距离天数（如果是事件）
    """
    warnings = []
    
    # 1. VIX预警（提前预警，而不是等它已经很高）
    if options_data.get('vix') is not None:
        vix = options_data['vix']
        vix_change = options_data.get('vix_change', 0)
        
        if vix >= 30:
            warnings.append({
                'level': 'high',
                'type': 'vix',
                'message': f'VIX已处于高位({vix:.1f})，市场恐慌情绪严重',
                'urgency': 'immediate'
            })
        elif vix >= 25:
            warnings.append({
                'level': 'medium',
                'type': 'vix',
                'message': f'VIX接近危险区域({vix:.1f})，距离30仅差{30-vix:.1f}点，需密切关注',
                'urgency': 'soon'
            })
        elif vix >= 20 and vix_change > 5:
            warnings.append({
                'level': 'medium',
                'type': 'vix',
                'message': f'VIX快速上升({vix_change:.1f}%)，当前{vix:.1f}，可能继续攀升',
                'urgency': 'soon'
            })
        elif vix >= 20:
            warnings.append({
                'level': 'low',
                'type': 'vix',
                'message': f'VIX处于中等偏高水平({vix:.1f})，需保持警惕',
                'urgency': 'monitor'
            })
    
    # 2. Put/Call比率预警
    if options_data.get('put_call_ratio') is not None:
        pc_ratio = options_data['put_call_ratio']
        if pc_ratio >= 1.5:
            warnings.append({
                'level': 'high',
                'type': 'options',
                'message': f'Put/Call比率极高({pc_ratio:.2f})，看跌情绪强烈，存在负Gamma风险',
                'urgency': 'immediate'
            })
        elif pc_ratio >= 1.2:
            warnings.append({
                'level': 'medium',
                'type': 'options',
                'message': f'Put/Call比率偏高({pc_ratio:.2f})，接近危险区域，需警惕',
                'urgency': 'soon'
            })
    
    # 3. 美债收益率预警
    if macro_data.get('treasury_10y') is not None:
        treasury = macro_data['treasury_10y']
        treasury_change = macro_data.get('treasury_10y_change', 0)
        
        if treasury >= 5.0:
            warnings.append({
                'level': 'high',
                'type': 'macro',
                'message': f'10年美债收益率极高({treasury:.2f}%)，流动性严重收紧',
                'urgency': 'immediate'
            })
        elif treasury >= 4.5:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'10年美债收益率偏高({treasury:.2f}%)，接近危险区域，流动性收紧',
                'urgency': 'soon'
            })
        elif treasury_change > 0.2:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'10年美债收益率快速上升(+{treasury_change:.2f}%)，流动性收紧信号',
                'urgency': 'soon'
            })
    
    # 4. 黄金避险情绪预警
    if macro_data.get('gold_change') is not None:
        gold_change = macro_data['gold_change']
        if gold_change > 3:
            warnings.append({
                'level': 'high',
                'type': 'macro',
                'message': f'黄金大幅上涨({gold_change:.2f}%)，避险情绪强烈，可能预示地缘政治风险',
                'urgency': 'immediate'
            })
        elif gold_change > 1.5:
            warnings.append({
                'level': 'medium',
                'type': 'macro',
                'message': f'黄金明显上涨({gold_change:.2f}%)，避险情绪上升',
                'urgency': 'soon'
            })
    
    # 5. 美联储会议预警（提前提醒）
    if macro_data.get('fed_meetings'):
        for meeting in macro_data['fed_meetings']:
            days_until = meeting['days_until']
            if days_until <= 3:
                warnings.append({
                    'level': 'high',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后）{"，含点阵图" if meeting["has_dot_plot"] else ""}',
                    'urgency': 'immediate',
                    'event_date': meeting['date']
                })
            elif days_until <= 7:
                warnings.append({
                    'level': 'medium',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后）{"，含点阵图" if meeting["has_dot_plot"] else ""}，建议提前调整仓位',
                    'urgency': 'soon',
                    'event_date': meeting['date']
                })
            elif days_until <= 14:
                warnings.append({
                    'level': 'low',
                    'type': 'event',
                    'message': f'美联储利率决议将在{meeting["date"]}举行（{days_until}天后），建议关注',
                    'urgency': 'monitor',
                    'event_date': meeting['date']
                })
    
    # 6. CPI发布预警
    if macro_data.get('cpi_releases'):
        for cpi in macro_data['cpi_releases']:
            days_until = cpi['days_until']
            if days_until <= 3:
                warnings.append({
                    'level': 'high',
                    'type': 'event',
                    'message': f'CPI数据将在{cpi["date"]}发布（{days_until}天后，{cpi["data_month"]}数据），市场波动可能加剧',
                    'urgency': 'immediate',
                    'event_date': cpi['date']
                })
            elif days_until <= 7:
                warnings.append({
                    'level': 'medium',
                    'type': 'event',
                    'message': f'CPI数据将在{cpi["date"]}发布（{days_until}天后，{cpi["data_month"]}数据），建议关注',
                    'urgency': 'soon',
                    'event_date': cpi['date']
                })
    
    # 7. 期权到期日（交割日）预警 - 市场级别风险
    # 期权到期日是市场级别的风险，会影响整个市场的波动性
    if macro_data.get('options_expirations'):
        for exp in macro_data['options_expirations']:
            days_until = exp['days_until']
            is_quadruple = exp.get('is_quadruple_witching', False)
            
            # 期权到期日会导致市场波动增加，这是市场级别的风险
            if days_until <= 1:
                # 当天或明天到期，市场波动风险最高
                warnings.append({
                    'level': 'high',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日，市场波动风险极高，做市商需要大量调整对冲头寸" if is_quadruple else " - 月度到期日，市场波动风险增加，做市商需要调整对冲"}',
                    'urgency': 'immediate',
                    'event_date': exp['date']
                })
            elif days_until <= 3:
                warnings.append({
                    'level': 'high',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日，市场波动风险高" if is_quadruple else " - 月度到期日，市场波动风险上升"}',
                    'urgency': 'immediate',
                    'event_date': exp['date']
                })
            elif days_until <= 7:
                warnings.append({
                    'level': 'medium',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日" if is_quadruple else " - 月度到期日"}，市场波动风险增加，建议降低仓位或保持观望',
                    'urgency': 'soon',
                    'event_date': exp['date']
                })
            elif days_until <= 14:
                warnings.append({
                    'level': 'low',
                    'type': 'market',
                    'message': f'期权到期日：{exp["date"]}（{days_until}天后）{" - 四重到期日" if is_quadruple else " - 月度到期日"}，市场波动风险上升，建议关注',
                    'urgency': 'monitor',
                    'event_date': exp['date']
                })
    
    # 8. 财报日期预警（个股级别）
    if data.get('earnings_dates'):
        for earnings_date in data['earnings_dates']:
            try:
                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                today = datetime.now().date()
                days_until = (earnings_dt - today).days
                
                if 0 <= days_until <= 3:
                    warnings.append({
                        'level': 'high',
                        'type': 'event',
                        'message': f'财报将在{earnings_date}发布（{days_until}天后），波动可能加剧',
                        'urgency': 'immediate',
                        'event_date': earnings_date
                    })
                elif 0 <= days_until <= 7:
                    warnings.append({
                        'level': 'medium',
                        'type': 'event',
                        'message': f'财报将在{earnings_date}发布（{days_until}天后），建议关注',
                        'urgency': 'soon',
                        'event_date': earnings_date
                    })
            except:
                pass
    
    # 9. 成交量异常预警
    if data.get('volume_anomaly') and data['volume_anomaly'].get('is_anomaly'):
        ratio = data['volume_anomaly'].get('ratio', 1)
        if ratio > 3:
            warnings.append({
                'level': 'high',
                'type': 'technical',
                'message': f'成交量异常放大({ratio:.2f}倍)，可能存在重大消息或资金异动',
                'urgency': 'immediate'
            })
        elif ratio > 2:
            warnings.append({
                'level': 'medium',
                'type': 'technical',
                'message': f'成交量明显放大({ratio:.2f}倍)，需密切关注',
                'urgency': 'soon'
            })
    
    # 10. 地缘政治风险预警
    if macro_data.get('geopolitical_risk') is not None:
        gpr = macro_data['geopolitical_risk']
        if gpr >= 7:
            warnings.append({
                'level': 'high',
                'type': 'geopolitical',
                'message': f'地缘政治风险指数极高({gpr}/10)，市场避险情绪强烈，建议降低风险敞口',
                'urgency': 'immediate'
            })
        elif gpr >= 6:
            warnings.append({
                'level': 'medium',
                'type': 'geopolitical',
                'message': f'地缘政治风险指数偏高({gpr}/10)，需保持警惕',
                'urgency': 'soon'
            })
    
    # 10. Polymarket预测市场预警
    if macro_data.get('polymarket'):
        polymarket_data = macro_data['polymarket']
        
        # 检查关键事件
        if polymarket_data.get('key_events'):
            key_events = polymarket_data['key_events']
            
            # 检查是否有高流动性的负面事件
            negative_keywords = ['recession', 'crash', 'crisis', 'war', 'conflict', 'sanction', 'default', 'bankruptcy']
            high_liquidity_negative = []
            
            for event in key_events:
                question = event.get('question', '').lower()
                liquidity = event.get('liquidity', 0)
                
                if any(keyword in question for keyword in negative_keywords) and liquidity > 10000:
                    high_liquidity_negative.append(event)
            
            if len(high_liquidity_negative) > 0:
                # 按流动性排序，取最重要的
                high_liquidity_negative.sort(key=lambda x: x.get('liquidity', 0), reverse=True)
                top_event = high_liquidity_negative[0]
                
                warnings.append({
                    'level': 'high',
                    'type': 'polymarket',
                    'message': f'Polymarket预测市场显示重大风险事件：{top_event.get("question", "")[:50]}...（流动性：${top_event.get("liquidity", 0):,.0f}）',
                    'urgency': 'immediate'
                })
        
        # 检查经济预测
        if polymarket_data.get('economic_predictions'):
            econ_events = polymarket_data['economic_predictions']
            # 检查是否有高流动性的经济衰退预测
            recession_events = [e for e in econ_events if 'recession' in e.get('question', '').lower() and e.get('liquidity', 0) > 5000]
            if len(recession_events) > 0:
                warnings.append({
                    'level': 'medium',
                    'type': 'polymarket',
                    'message': f'Polymarket显示经济衰退预测市场活跃（{len(recession_events)}个相关市场），需关注经济风险',
                    'urgency': 'soon'
                })
        
        # 检查美联储政策预测
        if polymarket_data.get('fed_policy_predictions'):
            fed_events = polymarket_data['fed_policy_predictions']
            high_liquidity_fed = [e for e in fed_events if e.get('liquidity', 0) > 10000]
            if len(high_liquidity_fed) > 0:
                warnings.append({
                    'level': 'medium',
                    'type': 'polymarket',
                    'message': f'Polymarket显示美联储政策预测市场活跃（{len(high_liquidity_fed)}个高流动性市场），可能预示政策变化',
                    'urgency': 'monitor'
                })
    
    # 按紧急程度和级别排序
    urgency_order = {'immediate': 0, 'soon': 1, 'monitor': 2}
    level_order = {'high': 0, 'medium': 1, 'low': 2}
    
    warnings.sort(key=lambda x: (
        urgency_order.get(x.get('urgency', 'monitor'), 2),
        level_order.get(x.get('level', 'low'), 2)
    ))
    
    return warnings


def calculate_geopolitical_risk(macro_data, options_data):
    """
    计算地缘政治风险指数
    基于多个代理指标：黄金价格、VIX、美元指数等
    返回0-10分，分数越高表示地缘政治风险越高
    """
    risk_score = 5.0  # 基准分
    
    # 1. 黄金价格变化（权重40%）
    # 地缘政治风险上升时，黄金通常上涨
    if macro_data.get('gold_change') is not None:
        gold_change = macro_data['gold_change']
        if gold_change > 3:
            gold_risk = 8.0  # 大幅上涨，风险高
        elif gold_change > 1.5:
            gold_risk = 6.5  # 明显上涨
        elif gold_change > 0.5:
            gold_risk = 5.5  # 略有上涨
        elif gold_change < -2:
            gold_risk = 3.0  # 大幅下跌，风险偏好上升
        else:
            gold_risk = 5.0  # 中性
        risk_score = gold_risk * 0.4
    else:
        risk_score = 5.0 * 0.4
    
    # 2. VIX恐慌指数（权重30%）
    # VIX上升可能反映地缘政治担忧
    if options_data.get('vix') is not None:
        vix = options_data['vix']
        if vix > 30:
            vix_risk = 8.5  # 高恐慌
        elif vix > 25:
            vix_risk = 7.0
        elif vix > 20:
            vix_risk = 5.5
        elif vix < 15:
            vix_risk = 3.5  # 低恐慌
        else:
            vix_risk = 5.0
        risk_score += vix_risk * 0.3
    else:
        risk_score += 5.0 * 0.3
    
    # 3. 美元指数（权重20%）
    # 地缘政治风险上升时，美元可能走强（避险）
    if macro_data.get('dxy') is not None:
        dxy = macro_data['dxy']
        dxy_change = macro_data.get('dxy_change', 0)
        
        # 美元走强且快速上升可能反映避险需求
        if dxy > 105 and dxy_change > 1:
            dxy_risk = 7.5
        elif dxy > 105:
            dxy_risk = 6.0
        elif dxy < 95:
            dxy_risk = 4.0  # 弱势美元，风险偏好
        else:
            dxy_risk = 5.0
        risk_score += dxy_risk * 0.2
    else:
        risk_score += 5.0 * 0.2
    
    # 4. 原油价格波动（权重10%）
    # 地缘政治事件通常影响原油供应
    if macro_data.get('oil_change') is not None:
        oil_change = abs(macro_data['oil_change'])
        if oil_change > 5:
            oil_risk = 7.0  # 大幅波动
        elif oil_change > 3:
            oil_risk = 6.0
        else:
            oil_risk = 5.0
        risk_score += oil_risk * 0.1
    else:
        risk_score += 5.0 * 0.1
    
    # 确保在0-10范围内
    risk_score = max(0, min(10, risk_score))
    
    return round(risk_score, 1)


def get_macro_market_data():
    """
    获取宏观经济和市场情绪指标
    包括：美债收益率、美元指数、黄金、原油等
    这些指标反映市场流动性、避险情绪和宏观经济环境
    """
    macro_data = {
        'treasury_10y': None,  # 10年期美债收益率
        'treasury_10y_change': None,
        'dxy': None,  # 美元指数
        'dxy_change': None,
        'gold': None,  # 黄金价格
        'gold_change': None,
        'oil': None,  # 原油价格
        'oil_change': None,
        'volume_anomaly': None,  # 成交量异常（需要结合个股数据）
        'fed_meetings': [],  # 美联储会议日期
        'cpi_releases': [],  # CPI发布日期
        'options_expirations': [],  # 期权到期日（交割日）
        'geopolitical_risk': None,  # 地缘政治风险指数
    }
    
    try:
        # 1. 10年期美债收益率 (^TNX) - 反映市场对利率和通胀的预期
        try:
            tnx = yf.Ticker('^TNX')
            tnx_hist = tnx.history(period='5d', timeout=10)
            if not tnx_hist.empty and len(tnx_hist) >= 2:
                treasury_current = float(tnx_hist['Close'].iloc[-1])
                treasury_prev = float(tnx_hist['Close'].iloc[-2])
                treasury_change = treasury_current - treasury_prev
                macro_data['treasury_10y'] = treasury_current
                macro_data['treasury_10y_change'] = treasury_change
        except Exception as e:
            print(f"获取美债收益率失败: {e}")
        
        # 2. 美元指数 (DX-Y.NYB 或 ^DXY) - 反映美元强弱，影响全球流动性
        try:
            dxy = yf.Ticker('DX-Y.NYB')
            dxy_hist = dxy.history(period='5d', timeout=10)
            if dxy_hist.empty:
                # 尝试备用代码
                dxy = yf.Ticker('^DXY')
                dxy_hist = dxy.history(period='5d', timeout=10)
            
            if not dxy_hist.empty and len(dxy_hist) >= 2:
                dxy_current = float(dxy_hist['Close'].iloc[-1])
                dxy_prev = float(dxy_hist['Close'].iloc[-2])
                dxy_change = ((dxy_current - dxy_prev) / dxy_prev) * 100
                macro_data['dxy'] = dxy_current
                macro_data['dxy_change'] = dxy_change
        except Exception as e:
            print(f"获取美元指数失败: {e}")
        
        # 3. 黄金价格 (GC=F) - 避险情绪指标
        try:
            gold = yf.Ticker('GC=F')
            gold_hist = gold.history(period='5d', timeout=10)
            if not gold_hist.empty and len(gold_hist) >= 2:
                gold_current = float(gold_hist['Close'].iloc[-1])
                gold_prev = float(gold_hist['Close'].iloc[-2])
                gold_change = ((gold_current - gold_prev) / gold_prev) * 100
                macro_data['gold'] = gold_current
                macro_data['gold_change'] = gold_change
        except Exception as e:
            print(f"获取黄金价格失败: {e}")
        
        # 4. 原油价格 (CL=F) - 通胀和经济增长预期
        try:
            oil = yf.Ticker('CL=F')
            oil_hist = oil.history(period='5d', timeout=10)
            if not oil_hist.empty and len(oil_hist) >= 2:
                oil_current = float(oil_hist['Close'].iloc[-1])
                oil_prev = float(oil_hist['Close'].iloc[-2])
                oil_change = ((oil_current - oil_prev) / oil_prev) * 100
                macro_data['oil'] = oil_current
                macro_data['oil_change'] = oil_change
        except Exception as e:
            print(f"获取原油价格失败: {e}")
        
        # 5. 获取美联储会议日期
        try:
            macro_data['fed_meetings'] = get_fed_meeting_dates()
        except Exception as e:
            print(f"获取美联储会议日期失败: {e}")
        
        # 6. 获取CPI发布日期
        try:
            macro_data['cpi_releases'] = get_cpi_release_dates()
        except Exception as e:
            print(f"获取CPI发布日期失败: {e}")
        
        # 7. 获取期权到期日（交割日）
        try:
            macro_data['options_expirations'] = get_options_expiration_dates()
        except Exception as e:
            print(f"获取期权到期日失败: {e}")
            
    except Exception as e:
        print(f"获取宏观经济数据时出错: {e}")
    
    return macro_data


def get_polymarket_data():
    """
    获取Polymarket预测市场的关键数据
    Polymarket是一个预测市场平台，可以反映市场对重大事件的预期
    返回关键预测市场数据，如选举、经济政策、市场事件等
    """
    polymarket_data = {
        'election_predictions': [],  # 选举预测
        'economic_predictions': [],  # 经济政策预测
        'market_event_predictions': [],  # 市场事件预测
        'geopolitical_predictions': [],  # 地缘政治预测
        'fed_policy_predictions': [],  # 美联储政策预测
        'overall_sentiment': None,  # 综合市场情绪（基于预测市场）
        'key_events': []  # 关键事件列表
    }
    
    try:
        # Polymarket公共API端点
        # 注意：这是公共API，可能需要根据实际API文档调整
        base_url = "https://clob.polymarket.com"
        
        # 尝试获取活跃市场数据
        try:
            # 获取市场列表（这里使用Polymarket的GraphQL API或REST API）
            # 由于Polymarket API可能有变化，我们使用一个通用的方法
            markets_url = f"{base_url}/markets"
            
            # 定义我们关注的关键市场类别
            key_categories = [
                'election',  # 选举
                'economics',  # 经济
                'policy',  # 政策
                'geopolitics',  # 地缘政治
                'fed',  # 美联储
                'crypto',  # 加密货币（可能影响市场）
                'regulation'  # 监管
            ]
            
            # 尝试从Polymarket获取数据
            # 注意：实际API可能需要认证或使用不同的端点
            # 这里提供一个框架，实际使用时需要根据Polymarket的最新API文档调整
            
            # 方法1：尝试使用公共GraphQL端点（如果可用）
            graphql_url = "https://clob.polymarket.com/graphql"
            
            # 查询关键市场
            query = """
            {
                markets(where: {active: true, closed: false}, orderBy: volume, orderDirection: desc, first: 20) {
                    id
                    question
                    conditionId
                    outcomes
                    volume
                    liquidity
                    endDate
                    image
                    active
                    closed
                    category
                }
            }
            """
            
            try:
                response = requests.post(
                    graphql_url,
                    json={'query': query},
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'markets' in data['data']:
                        markets = data['data']['markets']
                        
                        # 分类处理市场数据
                        for market in markets:
                            question = market.get('question', '').lower()
                            category = market.get('category', '').lower()
                            volume = float(market.get('volume', 0))
                            liquidity = float(market.get('liquidity', 0))
                            
                            # 只处理有足够流动性的市场
                            if liquidity < 1000:  # 流动性阈值
                                continue
                            
                            market_info = {
                                'question': market.get('question', ''),
                                'condition_id': market.get('conditionId', ''),
                                'volume': volume,
                                'liquidity': liquidity,
                                'end_date': market.get('endDate', ''),
                                'category': category
                            }
                            
                            # 根据关键词分类
                            if any(keyword in question or keyword in category for keyword in ['election', 'president', 'senate', 'house', 'vote']):
                                polymarket_data['election_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['gdp', 'inflation', 'cpi', 'unemployment', 'recession', 'economic']):
                                polymarket_data['economic_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['fed', 'federal reserve', 'interest rate', 'fomc', 'rate cut', 'rate hike']):
                                polymarket_data['fed_policy_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['war', 'conflict', 'sanction', 'trade', 'geopolitical', 'russia', 'china', 'iran']):
                                polymarket_data['geopolitical_predictions'].append(market_info)
                            elif any(keyword in question or keyword in category for keyword in ['market', 'crash', 'rally', 'sp500', 'dow', 'nasdaq']):
                                polymarket_data['market_event_predictions'].append(market_info)
                            
                            # 添加到关键事件列表（按流动性排序）
                            if liquidity > 5000:
                                polymarket_data['key_events'].append(market_info)
                        
                        # 按流动性排序
                        polymarket_data['key_events'].sort(key=lambda x: x.get('liquidity', 0), reverse=True)
                        polymarket_data['key_events'] = polymarket_data['key_events'][:10]  # 只保留前10个
                        
            except Exception as e:
                print(f"Polymarket GraphQL API请求失败: {e}")
                # 如果GraphQL失败，尝试使用REST API
                try:
                    # 尝试获取市场数据（使用REST端点，如果可用）
                    rest_url = f"{base_url}/markets"
                    rest_response = requests.get(rest_url, timeout=10)
                    if rest_response.status_code == 200:
                        # 处理REST API响应
                        # 这里需要根据实际的REST API格式调整
                        pass
                except Exception as rest_error:
                    print(f"Polymarket REST API请求也失败: {rest_error}")
            
            # 计算综合市场情绪（基于预测市场的概率）
            # 如果无法获取实时数据，使用默认值
            if len(polymarket_data['key_events']) > 0:
                # 基于关键事件的流动性加权平均
                total_liquidity = sum(event.get('liquidity', 0) for event in polymarket_data['key_events'])
                if total_liquidity > 0:
                    # 这里可以根据实际预测概率计算情绪
                    # 暂时使用一个基于事件数量的简单指标
                    polymarket_data['overall_sentiment'] = min(10, len(polymarket_data['key_events']) * 0.5)
            
        except Exception as e:
            print(f"获取Polymarket数据时出错: {e}")
    
    except Exception as e:
        print(f"Polymarket数据获取异常: {e}")
    
    return polymarket_data


def get_options_market_data(ticker):
    """
    获取期权市场相关数据
    包括VIX、期权持仓量、Put/Call比率等
    用于评估Vanna crush和负Gamma风险
    """
    options_data = {
        'vix': None,
        'vix_change': None,
        'put_call_ratio': None,
        'options_volume': None,
        'has_options': False  # 布尔值，JSON可以序列化
    }
    
    try:
        # 1. 获取VIX（恐慌指数）- 这是最重要的市场波动率指标
        try:
            vix_ticker = yf.Ticker('^VIX')
            vix_hist = vix_ticker.history(period='5d', timeout=10)
            if not vix_hist.empty and len(vix_hist) >= 2:
                vix_current = float(vix_hist['Close'].iloc[-1])
                vix_prev = float(vix_hist['Close'].iloc[-2])
                vix_change = ((vix_current - vix_prev) / vix_prev) * 100
                options_data['vix'] = float(vix_current)  # 确保是Python float
                options_data['vix_change'] = float(vix_change)  # 确保是Python float
        except Exception as e:
            print(f"获取VIX数据失败: {e}")
        
        # 2. 对于美股，尝试获取期权链数据
        # 判断是否为美股（不包含.HK, .SS, .SZ等后缀）
        normalized_ticker = normalize_ticker(ticker)
        is_us_stock = '.' not in normalized_ticker or normalized_ticker.endswith(('.US', ''))
        
        if is_us_stock:
            try:
                stock = yf.Ticker(normalized_ticker)
                # 获取最近的到期日期
                try:
                    expirations = stock.options
                    if expirations and len(expirations) > 0:
                        # 获取最近到期的期权链
                        nearest_exp = expirations[0]
                        opt_chain = stock.option_chain(nearest_exp)
                        
                        calls = opt_chain.calls
                        puts = opt_chain.puts
                        
                        # 计算Put/Call比率（持仓量）
                        if not calls.empty and not puts.empty:
                            put_volume = float(puts['openInterest'].sum() if 'openInterest' in puts.columns else puts['volume'].sum())
                            call_volume = float(calls['openInterest'].sum() if 'openInterest' in calls.columns else calls['volume'].sum())
                            
                            if call_volume > 0:
                                put_call_ratio = float(put_volume / call_volume)
                                options_data['put_call_ratio'] = put_call_ratio
                                options_data['options_volume'] = float(put_volume + call_volume)
                                options_data['has_options'] = True  # 布尔值，JSON可以序列化
                except Exception as e:
                    print(f"获取期权链数据失败: {e}")
            except Exception as e:
                print(f"期权数据获取异常: {e}")
    except Exception as e:
        print(f"获取期权市场数据时出错: {e}")
    
    return options_data


def calculate_atr(hist_data, period=14):
    """
    计算平均真实波幅（Average True Range, ATR）
    
    参数:
        hist_data: DataFrame，包含High, Low, Close列
        period: 计算ATR的周期（通常为14天）
    
    返回:
        ATR值（标量），如果数据不足则返回None
    """
    try:
        if hist_data.empty or len(hist_data) < period + 1:
            return None
        
        # 确保有High, Low, Close列
        if not all(col in hist_data.columns for col in ['High', 'Low', 'Close']):
            return None
        
        # 计算True Range的三个组成部分
        high_low = hist_data['High'] - hist_data['Low']
        high_close_prev = abs(hist_data['High'] - hist_data['Close'].shift(1))
        low_close_prev = abs(hist_data['Low'] - hist_data['Close'].shift(1))
        
        # True Range = max(high-low, high-close_prev, low-close_prev)
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR = True Range的移动平均
        atr = true_range.rolling(window=period).mean()
        
        # 返回最新的ATR值
        if not atr.empty and not pd.isna(atr.iloc[-1]):
            return float(atr.iloc[-1])
        else:
            return None
    except Exception as e:
        print(f"计算ATR时出错: {e}")
        return None


def calculate_dynamic_peg_threshold(treasury_10y, base_peg_threshold=1.0):
    """
    根据10年美债收益率动态调整PEG阈值
    
    逻辑:
    - 美债收益率高 -> 资金成本高 -> 对成长股要求更严格 -> PEG阈值降低
    - 美债收益率低 -> 资金成本低 -> 对成长股容忍度提高 -> PEG阈值提高
    
    参数:
        treasury_10y: 当前10年期美债收益率（百分比，如4.5表示4.5%），如果为None则返回基础阈值
        base_peg_threshold: 基准PEG阈值（通常为1.0）
    
    返回:
        调整后的PEG阈值
    """
    if treasury_10y is None:
        return base_peg_threshold
    
    # 基准利率假设为3.0%（历史平均）
    base_rate = 3.0
    
    # 计算利率偏离度
    rate_deviation = treasury_10y - base_rate
    
    # 调整系数：每1%的利率偏离，PEG阈值调整0.15
    # 利率上升1% -> PEG阈值降低0.15（更严格）
    # 利率下降1% -> PEG阈值提高0.15（更宽松）
    adjustment_factor = 1.0 - (rate_deviation * 0.15)
    
    # 限制调整范围：PEG阈值在0.5-2.0之间
    dynamic_peg_threshold = max(0.5, min(2.0, base_peg_threshold * adjustment_factor))
    
    return dynamic_peg_threshold


def calculate_atr_stop_loss(buy_price, hist_data, atr_period=14, atr_multiplier=2.5, min_stop_loss_pct=0.05, beta=None):
    """
    基于ATR计算动态止损价格
    
    参数:
        buy_price: 买入时的价格
        hist_data: DataFrame，包含High, Low, Close列
        atr_period: 计算ATR的周期（通常为14天）
        atr_multiplier: ATR的倍数（通常为2.0-3.0，波动率高的股票用更大倍数）
        min_stop_loss_pct: 最小止损幅度（如0.05表示5%，作为兜底）
        beta: 股票的Beta值（可选，如果提供则用于调整ATR倍数）
    
    返回:
        止损价格
    """
    # 根据Beta调整ATR倍数（如果提供）
    if beta is not None:
        if beta > 1.5:
            # 高Beta股票，使用更大的倍数（更宽止损）
            atr_multiplier = atr_multiplier * 1.2
        elif beta > 1.2:
            atr_multiplier = atr_multiplier * 1.1
        elif beta < 0.8:
            # 低Beta股票，使用更小的倍数（更窄止损）
            atr_multiplier = atr_multiplier * 0.8
        elif beta < 1.0:
            atr_multiplier = atr_multiplier * 0.9
        
        # 限制倍数范围（1.5-4.0）
        atr_multiplier = max(1.5, min(4.0, atr_multiplier))
    
    # 计算ATR
    atr = calculate_atr(hist_data, atr_period)
    
    if atr is None or atr <= 0:
        # 如果无法计算ATR，使用最小止损幅度
        stop_loss_price = buy_price * (1 - min_stop_loss_pct)
    else:
        # 基于ATR计算止损价格
        atr_stop_loss_price = buy_price - (atr * atr_multiplier)
        
        # 硬止损价格（最小止损幅度）
        hard_stop_loss_price = buy_price * (1 - min_stop_loss_pct)
        
        # 取两者中更保守的（止损价格更低）
        stop_loss_price = min(atr_stop_loss_price, hard_stop_loss_price)
    
    return stop_loss_price


def calculate_market_sentiment(data):
    """
    计算市场情绪评分 (M维度)
    返回0-10分，分数越高表示市场情绪越乐观
    现在包含期权市场情绪指标（VIX、Put/Call比率等）和宏观经济指标
    """
    sentiment_score = 5.0  # 基准分，中性
    
    # 获取期权市场数据
    options_data = get_options_market_data(data.get('original_symbol', data.get('symbol', '')))
    
    # 获取宏观经济数据
    macro_data = get_macro_market_data()
    
    # 获取Polymarket预测市场数据
    polymarket_data = get_polymarket_data()
    macro_data['polymarket'] = polymarket_data
    
    # 计算地缘政治风险指数（需要期权数据）
    if options_data:
        macro_data['geopolitical_risk'] = calculate_geopolitical_risk(macro_data, options_data)
    
    # 生成市场预警信息
    warnings = get_market_warnings(macro_data, options_data, data)
    data['market_warnings'] = warnings
    
    # 1. PE估值情绪 (权重30%，降低权重为期权指标让路)
    if data['pe'] and data['pe'] > 0:
        if data['pe'] < 10:
            pe_sentiment = 3.0  # 估值偏低，情绪悲观
        elif data['pe'] < 15:
            pe_sentiment = 4.0  # 估值合理偏低
        elif data['pe'] < 25:
            pe_sentiment = 5.0  # 估值合理
        elif data['pe'] < 40:
            pe_sentiment = 7.0  # 估值偏高，情绪乐观
        elif data['pe'] < 60:
            pe_sentiment = 8.5  # 估值很高，情绪很乐观
        else:
            pe_sentiment = 9.5  # 估值极高，情绪极度乐观（可能泡沫）
        sentiment_score = pe_sentiment * 0.3
    else:
        # 如果没有PE数据，使用中性分
        sentiment_score = 5.0 * 0.3
    
    # 2. PEG情绪调整 (权重15%) - 使用动态阈值
    if data['peg'] and data['peg'] > 0:
        # 获取10年美债收益率，用于动态调整PEG阈值
        treasury_10y = macro_data.get('treasury_10y')
        dynamic_peg_threshold = calculate_dynamic_peg_threshold(treasury_10y, base_peg_threshold=1.0)
        
        # 使用动态阈值计算PEG情绪分数
        if data['peg'] < dynamic_peg_threshold * 0.7:
            peg_sentiment = 8.0  # PEG很低，增长预期高，情绪乐观
        elif data['peg'] < dynamic_peg_threshold:
            peg_sentiment = 6.0  # PEG合理，增长匹配估值
        elif data['peg'] < dynamic_peg_threshold * 1.3:
            peg_sentiment = 5.0  # PEG略高，中性
        else:
            peg_sentiment = 3.0  # PEG过高，增长不匹配，情绪悲观
        
        # 存储动态PEG阈值供后续使用
        data['dynamic_peg_threshold'] = dynamic_peg_threshold
        
        sentiment_score += peg_sentiment * 0.15
    else:
        # 如果没有PEG数据，使用中性分
        sentiment_score += 5.0 * 0.15
    
    # 3. 价格位置情绪 (权重25%)
    if data.get('week52_high') and data.get('week52_low') and data['week52_high'] > data['week52_low']:
        price_position = (data['price'] - data['week52_low']) / (data['week52_high'] - data['week52_low'])
        # 确保price_position在合理范围内
        price_position = max(0, min(1, price_position))
        if price_position < 0.2:
            position_sentiment = 2.0  # 接近低点，情绪悲观
        elif price_position < 0.4:
            position_sentiment = 4.0  # 偏低位置
        elif price_position < 0.6:
            position_sentiment = 5.0  # 中间位置，中性
        elif price_position < 0.8:
            position_sentiment = 7.0  # 偏高位置，情绪乐观
        else:
            position_sentiment = 8.5  # 接近高点，情绪很乐观
        sentiment_score += position_sentiment * 0.25
    else:
        # 如果52周高低价相同，使用中性情绪
        sentiment_score += 5.0 * 0.25
    
    # 4. 技术面情绪 (权重10%)
    if data['price'] > data['ma50'] and data['ma50'] > data['ma200']:
        tech_sentiment = 7.0  # 多头排列，情绪偏乐观
    elif data['price'] < data['ma200']:
        tech_sentiment = 3.0  # 跌破长期均线，情绪偏悲观
    else:
        tech_sentiment = 5.0  # 震荡，中性
    sentiment_score += tech_sentiment * 0.1
    
    # 5. 期权市场情绪 (权重20%) - 新增！
    # 5.1 VIX恐慌指数 (权重12%)
    if options_data['vix'] is not None:
        vix = options_data['vix']
        vix_change = options_data.get('vix_change', 0)
        
        # VIX越高，市场恐慌情绪越高，情绪评分越低
        # VIX正常范围：10-20（低波动），20-30（中等波动），30+（高波动/恐慌）
        if vix < 15:
            vix_sentiment = 8.0  # 低波动，市场平静，情绪乐观
        elif vix < 20:
            vix_sentiment = 6.5  # 正常波动
        elif vix < 25:
            vix_sentiment = 5.0  # 中等偏高波动
        elif vix < 30:
            vix_sentiment = 3.5  # 高波动，情绪偏悲观
        elif vix < 40:
            vix_sentiment = 2.0  # 很高波动，恐慌情绪
        else:
            vix_sentiment = 1.0  # 极高波动，极度恐慌
        
        # VIX快速上升（>10%）表示恐慌加剧，进一步降低情绪
        if vix_change > 10:
            vix_sentiment = max(1.0, vix_sentiment - 1.5)  # 恐慌加剧
        elif vix_change > 5:
            vix_sentiment = max(1.0, vix_sentiment - 0.8)
        elif vix_change < -10:
            vix_sentiment = min(10.0, vix_sentiment + 1.0)  # 恐慌缓解
        
        sentiment_score += vix_sentiment * 0.12
    else:
        sentiment_score += 5.0 * 0.12
    
    # 5.2 Put/Call比率 (权重8%)
    # Put/Call比率高 -> 看跌情绪强 -> 市场情绪悲观
    if options_data['put_call_ratio'] is not None:
        pc_ratio = options_data['put_call_ratio']
        # 正常范围：0.7-1.0（中性），>1.0（看跌情绪强），<0.7（看涨情绪强）
        if pc_ratio < 0.7:
            pc_sentiment = 7.5  # 看涨情绪强
        elif pc_ratio < 0.9:
            pc_sentiment = 6.0  # 略偏看涨
        elif pc_ratio < 1.1:
            pc_sentiment = 5.0  # 中性
        elif pc_ratio < 1.3:
            pc_sentiment = 4.0  # 略偏看跌
        elif pc_ratio < 1.5:
            pc_sentiment = 3.0  # 看跌情绪较强
        else:
            pc_sentiment = 2.0  # 极度看跌（可能负Gamma风险）
        
        sentiment_score += pc_sentiment * 0.08
    else:
        sentiment_score += 5.0 * 0.08
    
    # 6. 宏观经济情绪调整 (权重10%) - 新增！
    # 6.1 美债收益率 (权重4%) - 收益率上升通常意味着流动性收紧，对股市不利
    if macro_data['treasury_10y'] is not None:
        treasury = macro_data['treasury_10y']
        treasury_change = macro_data.get('treasury_10y_change', 0)
        
        # 收益率在3-4%为正常，>4.5%表示紧缩，<2.5%表示宽松
        if treasury < 2.5:
            treasury_sentiment = 7.0  # 宽松环境，利好股市
        elif treasury < 3.5:
            treasury_sentiment = 6.0  # 正常偏低
        elif treasury < 4.5:
            treasury_sentiment = 5.0  # 正常
        elif treasury < 5.0:
            treasury_sentiment = 4.0  # 偏高，流动性收紧
        else:
            treasury_sentiment = 2.5  # 很高，严重收紧
        
        # 快速上升（>0.2%）进一步降低情绪
        if treasury_change > 0.2:
            treasury_sentiment = max(1.0, treasury_sentiment - 1.0)
        elif treasury_change < -0.2:
            treasury_sentiment = min(10.0, treasury_sentiment + 0.5)
        
        sentiment_score += treasury_sentiment * 0.04
    else:
        sentiment_score += 5.0 * 0.04
    
    # 6.2 美元指数 (权重3%) - 美元走强通常对美股不利（资金流出）
    if macro_data['dxy'] is not None:
        dxy = macro_data['dxy']
        dxy_change = macro_data.get('dxy_change', 0)
        
        # DXY正常范围：95-105，>105表示强势美元，<95表示弱势
        if dxy < 95:
            dxy_sentiment = 6.5  # 弱势美元，利好
        elif dxy < 105:
            dxy_sentiment = 5.0  # 正常
        else:
            dxy_sentiment = 3.5  # 强势美元，不利
        
        # 快速上升（>1%）进一步降低情绪
        if dxy_change > 1:
            dxy_sentiment = max(1.0, dxy_sentiment - 0.8)
        
        sentiment_score += dxy_sentiment * 0.03
    else:
        sentiment_score += 5.0 * 0.03
    
    # 6.3 黄金价格 (权重2%) - 避险情绪指标
    if macro_data['gold'] is not None:
        gold_change = macro_data.get('gold_change', 0)
        
        # 黄金上涨通常表示避险情绪上升，对股市不利
        if gold_change > 2:
            gold_sentiment = 3.0  # 避险情绪强烈
        elif gold_change > 0.5:
            gold_sentiment = 4.5  # 略有避险
        elif gold_change < -2:
            gold_sentiment = 7.0  # 风险偏好上升
        else:
            gold_sentiment = 5.0  # 中性
        
        sentiment_score += gold_sentiment * 0.02
    else:
        sentiment_score += 5.0 * 0.02
    
    # 6.4 原油价格 (权重1%) - 通胀和增长预期
    if macro_data['oil'] is not None:
        oil_change = macro_data.get('oil_change', 0)
        
        # 原油大幅上涨可能引发通胀担忧，但适度上涨表示需求增长
        if oil_change > 5:
            oil_sentiment = 4.0  # 通胀担忧
        elif oil_change < -5:
            oil_sentiment = 4.5  # 需求疲软
        else:
            oil_sentiment = 5.0  # 中性
        
        sentiment_score += oil_sentiment * 0.01
    else:
        sentiment_score += 5.0 * 0.01
    
    # 7. Polymarket预测市场情绪 (权重3%) - 反映市场对重大事件的预期
    if polymarket_data and polymarket_data.get('overall_sentiment') is not None:
        polymarket_sentiment = polymarket_data['overall_sentiment']
        sentiment_score += polymarket_sentiment * 0.03
    else:
        sentiment_score += 5.0 * 0.03
    
    # 7.1 基于Polymarket关键事件调整情绪
    if polymarket_data and polymarket_data.get('key_events'):
        key_events = polymarket_data['key_events']
        # 检查是否有负面事件（如经济衰退、市场崩盘等）
        negative_keywords = ['recession', 'crash', 'crisis', 'war', 'conflict', 'sanction']
        positive_keywords = ['rally', 'growth', 'recovery', 'peace', 'deal']
        
        negative_count = 0
        positive_count = 0
        
        for event in key_events:
            question = event.get('question', '').lower()
            if any(keyword in question for keyword in negative_keywords):
                negative_count += 1
            elif any(keyword in question for keyword in positive_keywords):
                positive_count += 1
        
        # 负面事件多于正面事件时，降低情绪
        if negative_count > positive_count:
            sentiment_score -= (negative_count - positive_count) * 0.2
        elif positive_count > negative_count:
            sentiment_score += (positive_count - negative_count) * 0.1
    
    # 7. 期权到期日对市场情绪的影响 (权重2%) - 市场级别风险
    # 期权到期日会导致市场波动增加，降低市场情绪
    if macro_data.get('options_expirations'):
        expiration_impact = 0
        for exp in macro_data['options_expirations']:
            days_until = exp['days_until']
            is_quadruple = exp.get('is_quadruple_witching', False)
            
            # 距离到期日越近，对市场情绪的影响越大
            # 期权到期日会导致做市商调整对冲，增加市场波动，降低市场情绪
            if days_until <= 1:
                # 当天或明天到期，市场波动风险最高
                impact = -2.0 if is_quadruple else -1.5  # 四重到期日影响更大
            elif days_until <= 3:
                impact = -1.5 if is_quadruple else -1.0
            elif days_until <= 7:
                impact = -1.0 if is_quadruple else -0.5
            elif days_until <= 14:
                impact = -0.5 if is_quadruple else -0.3
            else:
                impact = 0
            
            expiration_impact += impact
        
        # 限制最大影响（避免过度调整）
        expiration_impact = max(-2.0, min(0, expiration_impact))
        sentiment_score += expiration_impact * 0.02
    else:
        sentiment_score += 0.0 * 0.02
    
    # 将期权和宏观经济数据存储到data中，供前端和AI分析使用
    data['options_data'] = options_data
    data['macro_data'] = macro_data
    
    # 确保分数在0-10范围内
    sentiment_score = max(0, min(10, sentiment_score))
    
    return round(sentiment_score, 1)


def classify_company(data):
    """
    对公司进行分类
    返回：公司类别、行业特征、成长阶段等
    """
    sector = data.get('sector', 'Unknown').lower()
    industry = data.get('industry', 'Unknown').lower()
    growth = data.get('growth', 0)
    pe = data.get('pe', 0)
    market_cap = data.get('market_cap', 0)  # 市值（美元）
    
    # 1. 按行业分类
    industry_category = 'general'
    if any(keyword in sector or keyword in industry for keyword in ['technology', 'software', 'internet', 'semiconductor', 'tech']):
        industry_category = 'technology'
    elif any(keyword in sector or keyword in industry for keyword in ['financial', 'bank', 'insurance', 'finance']):
        industry_category = 'financial'
    elif any(keyword in sector or keyword in industry for keyword in ['healthcare', 'pharmaceutical', 'biotech', 'medical']):
        industry_category = 'healthcare'
    elif any(keyword in sector or keyword in industry for keyword in ['energy', 'oil', 'gas', 'petroleum']):
        industry_category = 'energy'
    elif any(keyword in sector or keyword in industry for keyword in ['consumer', 'retail', 'consumer goods']):
        industry_category = 'consumer'
    elif any(keyword in sector or keyword in industry for keyword in ['real estate', 'reit', 'property']):
        industry_category = 'real_estate'
    elif any(keyword in sector or keyword in industry for keyword in ['utility', 'utilities', 'electric']):
        industry_category = 'utility'
    
    # 2. 按成长阶段分类
    growth_stage = 'mature'
    if growth > 0.2:  # 营收增长>20%
        growth_stage = 'high_growth'
    elif growth > 0.1:  # 营收增长>10%
        growth_stage = 'growth'
    elif growth > 0:  # 正增长
        growth_stage = 'stable'
    else:  # 负增长或零增长
        growth_stage = 'declining'
    
    # 3. 按市值分类
    market_cap_category = 'mid_cap'
    if market_cap > 0:
        if market_cap > 100e9:  # >1000亿美元
            market_cap_category = 'large_cap'
        elif market_cap > 10e9:  # >100亿美元
            market_cap_category = 'mid_cap'
        else:
            market_cap_category = 'small_cap'
    
    return {
        'industry_category': industry_category,
        'growth_stage': growth_stage,
        'market_cap_category': market_cap_category,
        'sector': sector,
        'industry': industry
    }


def get_reasonable_pe_by_category(company_info, style):
    """
    根据公司类别和投资风格，确定合理的PE倍数
    """
    industry_category = company_info['industry_category']
    growth_stage = company_info['growth_stage']
    
    # 基础PE（根据行业）
    base_pe = {
        'technology': 25,
        'healthcare': 22,
        'financial': 12,
        'energy': 15,
        'consumer': 18,
        'real_estate': 15,
        'utility': 16,
        'general': 18
    }.get(industry_category, 18)
    
    # 根据成长阶段调整
    if growth_stage == 'high_growth':
        base_pe *= 1.3  # 高成长公司可以容忍更高PE
    elif growth_stage == 'growth':
        base_pe *= 1.15
    elif growth_stage == 'stable':
        base_pe *= 1.0
    elif growth_stage == 'declining':
        base_pe *= 0.7  # 衰退公司PE应该更低
    
    # 根据投资风格调整
    if style == 'value':
        base_pe *= 0.75  # 价值风格要求更低PE
    elif style == 'growth':
        base_pe *= 1.2  # 成长风格可以容忍更高PE
    elif style == 'quality':
        base_pe *= 1.0  # 质量风格保持基准
    elif style == 'momentum':
        base_pe *= 1.1  # 趋势风格略高
    
    return round(base_pe, 1)


def calculate_target_price(data, risk_result, style):
    """
    计算目标价格 - 成熟的多维度估值模型
    根据公司类别（行业、成长阶段、市值）采用不同的估值方法和权重
    """
    try:
        current_price = float(data.get('price', 0))
        if current_price <= 0:
            return 0.0
    except (ValueError, TypeError):
        return 0.0
    
    # 如果建议仓位为0%，风险极高，不建议买入
    if risk_result['suggested_position'] == 0:
        return round(current_price, 2)
    
    # 对公司进行分类
    company_info = classify_company(data)
    
    # 获取合理PE（根据公司类别和投资风格）
    reasonable_pe = get_reasonable_pe_by_category(company_info, style)
    
    prices = []
    methods_used = []
    
    # 方法1: PE/PEG估值法（适用于有盈利的公司）
    if data.get('pe') and data['pe'] > 0:
        pe = data['pe']
        forward_pe = data.get('forward_pe', 0)
        
        if forward_pe and forward_pe > 0:
            # 使用预期PE计算
            pe_based_price = current_price * (reasonable_pe / forward_pe)
        else:
            # 使用当前PE计算
            if pe > reasonable_pe * 1.5:
                # PE过高，目标价格下调
                pe_based_price = current_price * (reasonable_pe / pe)
            elif pe < reasonable_pe * 0.7:
                # PE偏低，有上涨空间
                pe_based_price = current_price * (reasonable_pe / pe) * 0.9
            else:
                # PE合理，给予适度溢价
                pe_based_price = current_price * (reasonable_pe / pe) * 0.95
        
        prices.append(pe_based_price)
        methods_used.append('PE估值')
    
    # 方法2: PEG估值法（适用于成长股）
    if data.get('peg') and data['peg'] > 0 and data.get('growth') and data['growth'] > 0:
        peg = data['peg']
        growth = data['growth']
        
        # 合理PEG通常在0.8-1.5之间
        reasonable_peg = 1.0
        if company_info['growth_stage'] == 'high_growth':
            reasonable_peg = 1.2  # 高成长可以容忍更高PEG
        elif company_info['growth_stage'] == 'declining':
            reasonable_peg = 0.8  # 衰退公司PEG应该更低
        
        if peg < reasonable_peg:
            # PEG偏低，有上涨空间
            peg_multiplier = reasonable_peg / peg
            peg_based_price = current_price * min(peg_multiplier, 1.5)  # 限制最大涨幅
            prices.append(peg_based_price)
            methods_used.append('PEG估值')
    
    # 方法3: 增长率折现法（适用于成长股）
    if data.get('growth') and data['growth'] > 0:
        growth = data['growth']
        margin = data.get('margin', 0)
        
        # 根据成长阶段给予不同的增长溢价
        if company_info['growth_stage'] == 'high_growth':
            # 高成长公司：给予未来1-2年的增长预期
            growth_multiplier = 1 + growth * 0.6  # 给予60%的增长溢价
        elif company_info['growth_stage'] == 'growth':
            growth_multiplier = 1 + growth * 0.4  # 给予40%的增长溢价
        elif company_info['growth_stage'] == 'stable':
            growth_multiplier = 1 + growth * 0.2  # 给予20%的增长溢价
        else:
            growth_multiplier = 1.0  # 衰退公司不给增长溢价
        
        # 如果利润率较高，可以给予更高估值
        if margin > 0.15:
            growth_multiplier *= 1.1
        
        growth_based_price = current_price * growth_multiplier
        prices.append(growth_based_price)
        methods_used.append('增长率折现')
    
    # 方法4: 技术面目标价（适用于所有公司，但权重较低）
    try:
        week52_high = float(data.get('week52_high') or current_price)
        week52_low = float(data.get('week52_low') or current_price)
        ma50 = float(data.get('ma50') or current_price)
        ma200 = float(data.get('ma200') or current_price)
        
        price_position = 0.5
        if week52_high and week52_low and week52_high > week52_low:
            price_position = (current_price - week52_low) / (week52_high - week52_low)
            price_position = max(0, min(1, price_position))
        
        # 根据价格位置和技术趋势确定目标价
        if price_position < 0.3:
            # 价格在低位
            if current_price > ma50 and ma50 > ma200:
                # 多头排列，目标价可以是52周高点
                tech_based_price = week52_high
            else:
                # 技术面一般，目标价保守（52周中位）
                tech_based_price = (week52_high + week52_low) / 2
        elif price_position < 0.7:
            # 价格在中位
            if current_price > ma50 and ma50 > ma200:
                tech_based_price = week52_high
            else:
                tech_based_price = current_price * 1.15
        else:
            # 价格在高位，目标价保守
            tech_based_price = current_price * 1.1
        
        prices.append(tech_based_price)
        methods_used.append('技术面分析')
    except (ValueError, TypeError, ZeroDivisionError) as e:
        print(f"计算技术面目标价格时出错: {e}")
    
    # 综合计算
    if not prices:
        # 如果都没有数据，使用保守估计
        target_price = current_price * 1.1
        methods_used = ['保守估计']
    else:
        # 根据公司类别和投资风格，给不同方法分配权重
        industry_category = company_info['industry_category']
        
        if industry_category in ['technology', 'healthcare']:
            # 科技和医疗：更重视增长率和PEG
            weights = {'PE估值': 0.25, 'PEG估值': 0.30, '增长率折现': 0.30, '技术面分析': 0.15}
        elif industry_category == 'financial':
            # 金融：更重视PE
            weights = {'PE估值': 0.50, 'PEG估值': 0.20, '增长率折现': 0.15, '技术面分析': 0.15}
        elif industry_category in ['energy', 'utility']:
            # 能源和公用事业：更重视PE和技术面
            weights = {'PE估值': 0.40, 'PEG估值': 0.15, '增长率折现': 0.20, '技术面分析': 0.25}
        else:
            # 其他行业：均衡权重
            weights = {'PE估值': 0.35, 'PEG估值': 0.25, '增长率折现': 0.25, '技术面分析': 0.15}
        
        # 计算加权平均
        weighted_sum = 0
        total_weight = 0
        for i, price in enumerate(prices):
            method = methods_used[i] if i < len(methods_used) else '其他'
            weight = weights.get(method, 0.25)  # 默认权重
            weighted_sum += price * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_price = weighted_sum / total_weight
        else:
            avg_price = sum(prices) / len(prices)
        
        # 根据风险评分调整
        risk_score = risk_result.get('score', 5)
        if risk_score >= 6:
            risk_adjustment = 0.85  # 高风险，目标价格下调15%
        elif risk_score >= 4:
            risk_adjustment = 0.95  # 中等风险，目标价格下调5%
        elif risk_score >= 2:
            risk_adjustment = 1.0   # 低风险，不调整
        else:
            risk_adjustment = 1.05  # 极低风险，可以稍微乐观
        
        target_price = avg_price * risk_adjustment
        
        # 根据投资风格进行最终调整
        if style == 'value':
            target_price *= 0.95  # 价值风格更保守
        elif style == 'growth':
            target_price *= 1.05  # 成长风格可以稍微乐观
        elif style == 'momentum':
            target_price *= 1.08  # 趋势风格可以更乐观
        
        # 确保目标价格在合理范围内
        # 最低不低于当前价格的80%，最高不超过当前价格的250%
        target_price = max(current_price * 0.8, min(target_price, current_price * 2.5))
    
    # 存储计算方法信息（用于前端显示）
    data['target_price_methods'] = methods_used
    data['target_price_reasonable_pe'] = reasonable_pe
    data['company_category'] = company_info
    
    return round(target_price, 2)


def analyze_risk_and_position(style, data):
    """
    基于胡猛模型和五大支柱进行硬逻辑计算
    """
    risk_score = 0 # 0-10分，越高风险越大
    risk_flags = []
    
    # --- 1. G=B+M 模型检测 ---
    
    # M (情绪) 检测: 估值过热
    if data['pe'] > 60 and data['growth'] < 0.3:
        risk_score += 3
        risk_flags.append("M: 估值过高且增长不匹配 (PE>60)")
    elif data['pe'] > 40:
        risk_score += 1
        
    # B (基本面) 检测: 财务健康度
    if data['growth'] < 0:
        risk_score += 3
        risk_flags.append("B: 营收负增长 (衰退迹象)")
    if data['margin'] < 0.05:
        risk_score += 1
        risk_flags.append("B: 利润率极低 (<5%)")

    # 技术面 (趋势) - 投机风控
    if data['price'] < data['ma200']:
        risk_score += 2
        risk_flags.append("技术: 价格跌破200日均线 (熊市趋势)")
    
    # --- 2. 投资风格适配 ---
    
    # 风格特定的红线
    if style == 'value' and data['pe'] > 25:
        risk_score += 2
        risk_flags.append("风格不符: 价值股 PE > 25")
    if style == 'growth' and data['growth'] < 0.15:
        risk_score += 2
        risk_flags.append("风格不符: 成长股增速 < 15%")

    # --- 3. 仓位计算 ---
    
    # 确定风险等级
    risk_level = "低"
    if risk_score >= 6: risk_level = "极高 (建议观望)"
    elif risk_score >= 4: risk_level = "高"
    elif risk_score >= 2: risk_level = "中"
    
    # 基础仓位上限 (根据你的文档)
    base_caps = {
        'value': 10,    # 10%
        'growth': 15,   # 15%
        'quality': 20,  # 20%
        'momentum': 5   # 5%
    }
    max_cap = base_caps.get(style, 10)
    
    # 风险调整系数
    adjustment = 1.0
    if risk_score >= 6: adjustment = 0.0 # 极高风险不买
    elif risk_score >= 4: adjustment = 0.4
    elif risk_score >= 2: adjustment = 0.7
    
    suggested_position = max_cap * adjustment
    
    return {
        "score": risk_score,
        "level": risk_level,
        "flags": risk_flags,
        "suggested_position": round(suggested_position, 1)
    }

