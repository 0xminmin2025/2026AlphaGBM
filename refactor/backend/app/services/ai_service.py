import os
import time
from dotenv import load_dotenv

# 尝试导入 google.generativeai，如果失败则设置为 None
try:
    import google.generativeai as genai
except ImportError:
    print("警告: 无法导入 google.generativeai 模块。某些功能可能不可用。")
    genai = None

load_dotenv()

# 导入ATR止损计算函数
from .analysis_engine import calculate_atr_stop_loss


# 配置 Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if genai is not None:
    if api_key:
        genai.configure(api_key=api_key)
    else:
        print("警告: 未找到 GOOGLE_API_KEY")


def get_fallback_analysis(ticker, style, data, risk_result):
    """
    备用分析函数（当 Gemini 不可用时使用）
    """
    style_names = {
        'quality': '质量 (Quality)',
        'value': '价值 (Value)',
        'growth': '成长 (Growth)',
        'momentum': '趋势 (Momentum)'
    }
    
    style_principles = {
        'quality': '关注财务稳健、盈利能力强、债务水平低、护城河深的优质公司',
        'value': '寻找被市场低估的股票，关注低PE、低PEG，追求安全边际',
        'growth': '追求高营收增长和盈利增长的公司，容忍较高估值但要求持续增长',
        'momentum': '跟随市场趋势和价格动量，快进快出，关注技术面突破'
    }
    
    # 计算价格位置（在所有情况下都需要）
    if data.get('week52_high') and data.get('week52_low') and data['week52_high'] > data['week52_low']:
        price_position = (data['price'] - data['week52_low']) / (data['week52_high'] - data['week52_low'])
        price_position = max(0, min(1, price_position))  # 确保在0-1范围内
    else:
        price_position = 0.5  # 默认中位值
    
    # 计算目标价格（如果建议仓位为0%，目标价格等于当前价格，表示不建议买入）
    if risk_result['suggested_position'] == 0:
        target_price = data['price']  # 风险过高，不建议买入，无目标价格
    else:
        # 基于52周区间和当前价格计算
        # week52_high = data.get('week52_high') or data['price'] * 1.2
        # target_price = week52_high * 0.9 if price_position < 0.5 else week52_high * 1.1
        target_price = data['target_price']
    
    # 使用动态止损价格（如果已计算），否则使用固定止损
    if 'stop_loss_price' in data and data['stop_loss_price']:
        stop_loss = data['stop_loss_price']
        stop_loss_method = data.get('stop_loss_method', '动态止损')
        stop_loss_pct = ((data['price'] - stop_loss) / data['price']) * 100
    else:
        # 回退到固定止损
        stop_loss = data['price'] * 0.85  # 15%止损
        stop_loss_method = '固定15%止损'
        stop_loss_pct = 15.0
    
    # 先计算PE和PEG的值
    pe_value = f"{data['pe']:.2f}" if data['pe'] and data['pe'] > 0 else "N/A"
    peg_value = f"{data['peg']:.2f}" if data['peg'] and data['peg'] > 0 else "N/A"
    
    analysis = f"""## 投资分析报告 - {data['name']} ({ticker})

### 投资风格与原则

**当前投资风格**: {style_names.get(style, style)}

**风格核心原则**: {style_principles.get(style, '')}

**仓位限制**: 根据{style_names.get(style, style)}风格，建议最大仓位为{risk_result['suggested_position']}%

---

### AlphaG (G=B+M) 模型分析

**G (收益 Gain)**: 当前价格 {data['currency_symbol']}{data['price']:.2f}，位于52周区间 {data['currency_symbol']}{data['week52_low']:.2f} - {data['currency_symbol']}{data['week52_high']:.2f} 的 {price_position*100:.1f}% 位置。

**B (基本面 Basics)**: 
- 营收增长率: {data['growth']*100:.2f}%
- 利润率: {data['margin']*100:.2f}%
- 基本面评估: {'良好' if data['growth'] > 0.1 and data['margin'] > 0.1 else '一般' if data['growth'] > 0 else '较差'}

**M (动量 Momentum)**: 
- 市盈率(PE): {pe_value}
- PEG比率: {peg_value}
- 估值评估: {'偏高' if data['pe'] and data['pe'] > 30 else '合理' if data['pe'] and data['pe'] > 15 else '偏低' if data['pe'] else '数据不足'}
"""
    
    # 添加期权市场数据（如果有）
    if data.get('options_data', {}).get('vix') is not None:
        analysis += f"- VIX恐慌指数: {data.get('options_data', {}).get('vix', 'N/A'):.2f}\n"
    if data.get('options_data', {}).get('vix_change') is not None:
        analysis += f"- VIX变化: {data.get('options_data', {}).get('vix_change', 0):.1f}%\n"
    if data.get('options_data', {}).get('put_call_ratio') is not None:
        analysis += f"- Put/Call比率: {data.get('options_data', {}).get('put_call_ratio', 'N/A'):.2f}\n"
    if data.get('options_data'):
        vix = data.get('options_data', {}).get('vix') or 0
        put_call_ratio = data.get('options_data', {}).get('put_call_ratio') or 0
        if vix > 30:
            risk_text = '⚠️ 高波动风险（VIX>30）'
        elif put_call_ratio > 1.2:
            risk_text = '⚠️ 负Gamma风险（P/C>1.2）'
        elif data.get('options_data', {}).get('vix') is not None:
            risk_text = '正常'
        else:
            risk_text = 'N/A'
        analysis += f"- 期权市场风险: {risk_text}\n"
    
    analysis += """
---

### 风险控制评估

**风险评分**: """ + f"{risk_result['score']}/10 ({risk_result['level']})" + """

**主要风险因素**:
"""
    
    if risk_result['flags']:
        analysis += '\n'.join(['- ' + flag for flag in risk_result['flags']]) + '\n'
    else:
        analysis += '- 经系统评估，当前无明显结构性风险\n'
    
    # 添加 EV 模型短期风险评估（如果有）
    ev_model = data.get('ev_model', {})
    if ev_model and not ev_model.get('error'):
        weighted_ev = ev_model.get('weighted_ev', 0)
        ev_recommendation = ev_model.get('recommendation', {})
        
        if abs(weighted_ev) > 0.03:  # 只有当 EV 显著时才显示
            analysis += f"\n**短期波动风险（基于期望值模型）**:\n"
            analysis += f"- 加权期望值: {weighted_ev:.2%}\n"
            analysis += f"- 风险评估: {ev_recommendation.get('reason', '短期方向不明确')}\n"
            
            if ev_model.get('ev_1week'):
                ev_1week = ev_model['ev_1week']
                prob_up = ev_1week.get('prob_up', 0.5)
                prob_down = ev_1week.get('prob_down', 0.5)
                analysis += f"- 短期概率分布: 上涨概率{prob_up*100:.0f}%，下跌概率{prob_down*100:.0f}%\n"
            
            style_name = style_names.get(style, style)
            if style == 'quality' or style == 'value':
                analysis += f"- **重要提示**: 这是短期（1周至3个月）的风险评估，对于{style_name}风格的中长期投资，短期波动不应过度影响决策，但需要作为风险提示纳入考量。\n"
            else:
                analysis += f"- **重要提示**: 这是短期（1周至3个月）的风险评估，对于{style_name}风格，需要重点关注这一短期风险指标。\n"
    
    analysis += "\n**风险控制建议**:\n"
    analysis += f"- 严格遵守仓位限制，不要超过{risk_result['suggested_position']}%\n"
    analysis += f"- 设置止损价格并严格执行\n"
    if risk_result['score'] >= 6:
        analysis += "- 由于风险评分较高，建议降低仓位或保持观望\n"
    elif risk_result['score'] >= 4:
        analysis += "- 风险处于中等水平，建议分批建仓以降低风险\n"
    
    analysis += """
---

### 交易策略建议

**操作建议**: """
    
    if risk_result['suggested_position'] == 0:
        analysis += '观望（不建议建仓）\n'
    elif risk_result['score'] >= 6:
        analysis += '观望\n'
    elif risk_result['score'] >= 4:
        analysis += '分批建仓\n'
    elif risk_result['score'] >= 2:
        analysis += '可以考虑建仓\n'
    else:
        analysis += '适合建仓\n'
    
    analysis += f"""
**目标价格**: {data['currency_symbol']}{target_price:.2f} {'（风险过高，不建议买入，无目标价格）' if risk_result['suggested_position'] == 0 else '(基于技术面和估值分析)'}

**止损价格**: {data['currency_symbol']}{stop_loss:.2f} ({stop_loss_method}，止损幅度: {stop_loss_pct:.1f}%)

**建议仓位**: {risk_result['suggested_position']}%

**建仓策略**: 
"""
    
    if risk_result['suggested_position'] == 0:
        analysis += f'当前风险评分过高（{risk_result["score"]}/10），不建议建仓。建议继续观望，等待风险降低或寻找其他投资机会。\n'
    else:
        analysis += f'- 如果风险评分 >= 4: 建议分3批建仓，每批间隔1-2周，每批约{risk_result["suggested_position"]/3:.1f}%\n'
        analysis += f'- 如果风险评分 < 4: 可以一次性建仓，但不超过建议仓位上限{risk_result["suggested_position"]}%\n'
    
    analysis += f"""
**持有周期**: 根据{style_names.get(style, style)}风格，建议持有{'长期(1-3年)' if style == 'quality' else '中期(6-12个月)' if style == 'value' else '中短期(3-6个月)' if style == 'growth' else '短期(1-3个月)'}

---

### 注意事项

1. 严格遵守仓位限制，不要超过{risk_result['suggested_position']}%
2. 设置止损价格 {data['currency_symbol']}{stop_loss:.2f}（{stop_loss_method}，止损幅度{stop_loss_pct:.1f}%），严格执行止损纪律
3. 定期复查基本面数据，如营收增长转负或利润率大幅下降，考虑减仓
4. 关注市场情绪变化，如PE倍数异常升高，警惕估值泡沫
"""
    return analysis


def get_gemini_analysis(ticker, style, data, risk_result):
    """
    发送数据给 Gemini 进行定性分析
    """
    # 如果 genai 模块未导入或没有 API 密钥，使用备用分析
    if genai is None or not api_key:
        return get_fallback_analysis(ticker, style, data, risk_result)

    # 风格说明
    style_names = {
        'quality': '质量 (Quality)',
        'value': '价值 (Value)',
        'growth': '成长 (Growth)',
        'momentum': '趋势 (Momentum)'
    }
    
    style_principles = {
        'quality': '关注财务稳健、盈利能力强、债务水平低、护城河深的优质公司，适合长期持有，最大仓位20%',
        'value': '寻找被市场低估的股票，关注低PE、低PEG，追求安全边际，最大仓位10%',
        'growth': '追求高营收增长和盈利增长的公司，容忍较高估值但要求持续增长，最大仓位15%',
        'momentum': '跟随市场趋势和价格动量，快进快出，关注技术面突破，最大仓位5%'
    }

    # 先计算PE和PEG的值用于prompt
    pe_value = f"{data['pe']:.2f}" if data['pe'] and data['pe'] > 0 else "N/A"
    peg_value = f"{data['peg']:.2f}" if data['peg'] and data['peg'] > 0 else "N/A"
    
    # 计算止损价格信息（如果未计算则使用固定止损）
    if 'stop_loss_price' in data and data['stop_loss_price']:
        stop_loss_price = data['stop_loss_price']
        stop_loss_method = data.get('stop_loss_method', 'ATR动态止损')
        stop_loss_pct = ((data['price'] - stop_loss_price) / data['price']) * 100
    else:
        stop_loss_price = data['price'] * 0.85
        stop_loss_method = '固定15%止损'
        stop_loss_pct = 15.0
    
    # 检查是否为ETF或基金
    is_fund = data.get('is_etf_or_fund', False)
    fund_type = data.get('fund_type', None)
    
    # 构建 Prompt (提示词工程)
    if is_fund and fund_type == 'ETF':
        # ETF专用分析框架
        prompt = f"""
你是一位精通"AlphaG投资模型(G=B+M)"和"五大支柱投资框架"的资深基金经理。请对 {data['name']} ({ticker}) 进行严格的投资分析。

### ⚠️ 重要提示：这是ETF（交易所交易基金）

**产品类型**: ETF (交易所交易基金)
**ETF特点**: 
- ETF是跟踪特定指数或资产组合的交易所交易基金
- ETF不涉及公司财务指标（如营收、利润、PE等），这些指标对ETF不适用
- ETF的分析重点在于：跟踪标的指数的表现、流动性、管理费率、跟踪误差、技术面表现
- 杠杆ETF（如3x、UltraPro等）具有高波动性和高风险，需要特别注意

### 重要：投资风格与原则

**当前投资风格**: {style_names.get(style, style)}
**风格核心原则**: {style_principles.get(style, '')}
**仓位限制**: 根据{style_names.get(style, style)}风格，建议最大仓位为{risk_result['suggested_position']}%

你必须严格按照以上投资风格和原则进行分析，所有建议必须符合该风格的特征。**特别注意：不要使用公司财务指标（营收、利润、PE等）来分析ETF，这些指标对ETF不适用。**

### 1. 上下文数据

- **当前价格 (P)**: {data['currency_symbol']}{data['price']:.2f} (52周区间: {data['currency_symbol']}{data['week52_low']:.2f} - {data['currency_symbol']}{data['week52_high']:.2f})
"""
        if is_fund and fund_type == 'ETF':
            prompt += "- **注意：这是ETF，不适用公司财务指标**\n"
        else:
            prompt += f"- **基本面 (B)**: 营收增长 {data['growth']:.1%}, 利润率 {data['margin']:.1%}\n"
            prompt += f"    - **情绪/估值 (M)**: PE {pe_value}, PEG {peg_value}\n"
        prompt += f"- **技术面**: 50日均线 {data['currency_symbol']}{data['ma50']:.2f}, 200日均线 {data['currency_symbol']}{data['ma200']:.2f}\n"
        if is_fund and fund_type == 'ETF' and data.get('beta'):
            prompt += f"- **Beta值**: {data.get('beta', 'N/A')} (波动率指标)\n"
        prompt += f"""
- **系统风控评分**: {risk_result['score']}/10 (等级: {risk_result['level']})
- **主要风险点**: {', '.join(risk_result['flags']) if risk_result['flags'] else '无明显风险'}
"""
    else:
        # 普通股票分析框架
        prompt = f"""
你是一位精通"AlphaG投资模型(G=B+M)"和"五大支柱投资框架"的资深基金经理。请对 {data['name']} ({ticker}) 进行严格的投资分析。

### 重要：投资风格与原则

**当前投资风格**: {style_names.get(style, style)}
**风格核心原则**: {style_principles.get(style, '')}
**仓位限制**: 根据{style_names.get(style, style)}风格，建议最大仓位为{risk_result['suggested_position']}%

你必须严格按照以上投资风格和原则进行分析，所有建议必须符合该风格的特征。

### 1. 上下文数据

- **当前价格 (P)**: {data['currency_symbol']}{data['price']:.2f} (52周区间: {data['currency_symbol']}{data['week52_low']:.2f} - {data['currency_symbol']}{data['week52_high']:.2f})
- **基本面 (B)**: 营收增长 {data['growth']:.1%}, 利润率 {data['margin']:.1%}
    - **情绪/估值 (M)**: PE {pe_value}, PEG {peg_value}
- **技术面**: 50日均线 {data['currency_symbol']}{data['ma50']:.2f}, 200日均线 {data['currency_symbol']}{data['ma200']:.2f}
- **系统风控评分**: {risk_result['score']}/10 (等级: {risk_result['level']})
- **主要风险点**: {', '.join(risk_result['flags']) if risk_result['flags'] else '无明显风险'}
"""
    
    # 添加期权市场数据
    if data.get('options_data', {}).get('vix') is not None:
        prompt += f"- **期权市场数据**: VIX恐慌指数 {data.get('options_data', {}).get('vix', 'N/A'):.2f}\n"
    if data.get('options_data', {}).get('vix_change') is not None:
        prompt += f"  - VIX变化: {data.get('options_data', {}).get('vix_change', 0):.1f}%\n"
    if data.get('options_data', {}).get('put_call_ratio') is not None:
        prompt += f"  - Put/Call比率: {data.get('options_data', {}).get('put_call_ratio', 'N/A'):.2f}\n"
    
    # 添加期权市场风险提示
    options_data = data.get('options_data', {})
    vix = options_data.get('vix') or 0
    put_call_ratio = options_data.get('put_call_ratio') or 0
    if options_data and (vix > 30 or put_call_ratio > 1.2):
        if vix > 30:
            risk_text = 'VIX处于高位，存在Vanna crush和负Gamma风险，可能导致市场加速下跌'
        else:
            risk_text = 'Put/Call比率偏高，看跌情绪强烈，做市商可能面临负Gamma压力'
        prompt += f"  - **⚠️ 期权市场风险提示**: {risk_text}\n"
    
    # 添加宏观经济环境数据
    macro_data = data.get('macro_data', {})
    if macro_data.get('treasury_10y') is not None:
        prompt += f"- **宏观经济环境**: 10年美债收益率 {macro_data.get('treasury_10y', 'N/A'):.2f}%\n"
    if macro_data.get('dxy') is not None:
        prompt += f"  - 美元指数: {macro_data.get('dxy', 'N/A'):.2f}\n"
    if macro_data.get('gold') is not None:
        prompt += f"  - 黄金: ${macro_data.get('gold', 'N/A'):.2f}\n"
    if macro_data.get('oil') is not None:
        prompt += f"  - 原油: ${macro_data.get('oil', 'N/A'):.2f}\n"
    
    # 添加成交量异常
    volume_anomaly = data.get('volume_anomaly', {})
    if volume_anomaly.get('is_anomaly'):
        if volume_anomaly.get('ratio', 0) > 2:
            prompt += "- **成交量异常**: 成交量异常放大\n"
        else:
            prompt += "- **成交量异常**: 成交量异常萎缩\n"
    
    # 添加财报日期（⚠️ 波动率事件 - Binary Event）
    earnings_dates = data.get('earnings_dates', [])
    if earnings_dates and len(earnings_dates) > 0:
        from datetime import datetime
        today = datetime.now().date()
        earnings_info = []
        for earnings_date in earnings_dates[:2]:  # 只显示最近2个财报日期
            try:
                earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                days_until = (earnings_dt - today).days
                if 0 <= days_until < 7:
                    warning_level = "⚠️ 高危"
                elif 7 <= days_until <= 14:
                    warning_level = "⚠️ 中危"
                else:
                    warning_level = "低危"
                earnings_info.append(f"{earnings_date} ({days_until}天后) [{warning_level}]")
            except:
                earnings_info.append(earnings_date)
        
        if earnings_info:
            prompt += f"- **⚠️ 财报日期（波动率事件 - Binary Event）**: {', '.join(earnings_info)}\n"
            # 检查是否有高危财报日期
            for earnings_date in earnings_dates[:1]:
                try:
                    earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                    days_until = (earnings_dt - today).days
                    if 0 <= days_until < 7:
                        prompt += f"  - **⚠️ 高危警告**: 财报将在{earnings_date}发布（{days_until}天后），波动率风险极高，强烈建议在财报前3天避险或减仓\n"
                    elif 7 <= days_until <= 14:
                        prompt += f"  - **⚠️ 中危提醒**: 财报将在{earnings_date}发布（{days_until}天后），建议提前规划，考虑在财报前适当减仓\n"
                except:
                    pass
    
    # 添加IPO与解禁监控（⚠️ 供给侧冲击风险）
    lockup_data = data.get('lockup_data', {})
    if lockup_data and lockup_data.get('days_until_lockup') is not None:
        days_until_lockup = lockup_data['days_until_lockup']
        lockup_expiry_date = lockup_data.get('lockup_expiry_date', '未知日期')
        ipo_date = lockup_data.get('ipo_date')
        
        if 0 <= days_until_lockup < 14:
            if days_until_lockup < 7:
                warning_level = "⚠️ 高危"
            else:
                warning_level = "⚠️ 中危"
            
            prompt += f"- **⚠️ 解禁期监控（供给侧冲击风险 - Lock-up Expiry）**: 解禁将在{lockup_expiry_date}到来（{days_until_lockup}天后）[{warning_level}]\n"
            if ipo_date:
                prompt += f"  - IPO日期: {ipo_date}\n"
            
            # A股显示解禁股数和比例
            if lockup_data.get('lockup_shares_ratio'):
                prompt += f"  - 解禁股数占总股本比例: {lockup_data['lockup_shares_ratio']:.2f}%\n"
            
            if days_until_lockup < 7:
                prompt += f"  - **⚠️ 高危警告**: 解禁即将到来，抛压风险极高，可能面临巨大抛压，强烈建议提前减仓或避险\n"
            elif 7 <= days_until_lockup < 14:
                prompt += f"  - **⚠️ 中危提醒**: 解禁临近，可能面临抛压，建议提前规划\n"
    
    # 添加美联储利率决议
    fed_meetings = macro_data.get('fed_meetings', [])
    if fed_meetings and len(fed_meetings) > 0:
        meetings_text = ', '.join([m['date'] + ' (' + str(m['days_until']) + '天后' + ('，含点阵图' if m.get('has_dot_plot') else '') + ')' for m in fed_meetings])
        prompt += f"- **美联储利率决议**: {meetings_text}\n"
    
    # 添加美国CPI数据发布
    cpi_releases = macro_data.get('cpi_releases', [])
    us_cpi = [c for c in cpi_releases if c.get('country') == 'US']
    if us_cpi and len(us_cpi) > 0:
        cpi_text = ', '.join([c['date'] + ' (' + str(c['days_until']) + '天后，发布' + c['data_month'] + '数据)' for c in us_cpi])
        prompt += f"- **美国CPI数据发布**: {cpi_text}\n"
    
    # 添加中国经济事件
    china_events = macro_data.get('china_events', [])
    if china_events and len(china_events) > 0:
        # 只显示未来30天内的重要事件
        upcoming_china_events = [e for e in china_events if e.get('days_until', 999) <= 30]
        if upcoming_china_events:
            events_text = ', '.join([
                e['type'] + ': ' + e['date'] + ' (' + str(e['days_until']) + '天后' + 
                (', ' + e.get('data_month', '') if e.get('data_month') else '') +
                (', ' + e.get('quarter', '') if e.get('quarter') else '') + ')'
                for e in upcoming_china_events[:5]  # 只显示前5个
            ])
            prompt += f"- **中国经济事件**: {events_text}\n"
    
    # 添加期权到期日
    options_expirations = macro_data.get('options_expirations', [])
    if options_expirations and len(options_expirations) > 0:
        exp_text = ', '.join([exp['date'] + ' (' + str(exp['days_until']) + '天后，' + exp.get('type', '月度到期日') + (', 四重到期日' if exp.get('is_quadruple_witching') else '') + ')' for exp in options_expirations])
        prompt += f"- **期权到期日（交割日）**: {exp_text}\n"
    
    # 添加地缘政治风险指数
    geopolitical_risk = macro_data.get('geopolitical_risk')
    if geopolitical_risk is not None:
        risk_level = '⚠️ 高风险' if geopolitical_risk >= 7 else '中等风险' if geopolitical_risk >= 5 else '低风险'
        prompt += f"- **地缘政治风险指数**: {geopolitical_risk}/10 {risk_level}\n"
    
    # 添加中国市场特有情绪数据（如果是A股或港股）
    symbol = data.get('symbol', '')
    is_cn_market = symbol.endswith('.SS') or symbol.endswith('.SZ')
    is_hk_market = symbol.endswith('.HK')
    
    if is_cn_market or is_hk_market:
        china_sentiment = data.get('china_sentiment', {})
        china_policy = data.get('china_policy', {})
        china_adjustments = data.get('china_sentiment_adjustments', [])
        
        if china_sentiment or china_policy:
            prompt += f"\n### 🇨🇳 中国市场特有情绪面 (China Specific Sentiment) - 权重最高！\n"
            prompt += f"**注意：对于A股/港股，政策面权重 > 基本面权重，这是中国市场的核心特征。**\n\n"
            
            # 1. 最新政策与舆情
            latest_news = china_sentiment.get('latest_news', [])
            if latest_news:
                prompt += f"**1. 最新政策与舆情**:\n"
                for news in latest_news[:5]:
                    if isinstance(news, dict):
                        title = news.get('title', news.get('title', str(news)))
                        date = news.get('date', '')
                        prompt += f"  - {date}: {title}\n"
                    else:
                        prompt += f"  - {news}\n"
                prompt += f"  *请分析：这些新闻中是否包含明显的政策利好（如\"国家队入场\"、\"降准降息\"、\"行业扶持\"）或监管利空？*\n\n"
            
            # 2. 主力资金流向
            main_inflow = china_sentiment.get('main_net_inflow', 0)
            retail_inflow = china_sentiment.get('retail_net_inflow', 0)
            if main_inflow != 0:
                prompt += f"**2. 主力资金流向**: 主力净流入 {main_inflow:,.0f} 元"
                if retail_inflow != 0:
                    prompt += f"，散户净流入 {retail_inflow:,.0f} 元"
                prompt += f"\n"
                prompt += f"  *请分析：主力资金是在吸筹还是出货？这与当前股价涨跌是否背离？*\n"
                prompt += f"  - 主力大幅净流入（>1亿）通常是强力买入信号\n"
                prompt += f"  - 主力大幅净流出（<-1亿）通常是危险信号\n\n"
            
            # 3. 龙虎榜数据
            dragon_tiger = china_sentiment.get('dragon_tiger_list')
            if dragon_tiger:
                prompt += f"**3. 龙虎榜数据**: {dragon_tiger.get('date', '最近')}上榜\n"
                prompt += f"  - 上榜理由: {dragon_tiger.get('reason', 'N/A')}\n"
                prompt += f"  - 买入额: {dragon_tiger.get('buy_amount', 0):,.0f} 元\n"
                prompt += f"  - 卖出额: {dragon_tiger.get('sell_amount', 0):,.0f} 元\n"
                prompt += f"  *请分析：游资是在炒作还是出货？*\n\n"
            
            # 4. 宏观政策风向
            important_news = china_policy.get('important_news', [])
            market_impact = china_policy.get('market_impact', 'neutral')
            if important_news:
                prompt += f"**4. 宏观政策风向** ({'利好' if market_impact == 'positive' else '利空' if market_impact == 'negative' else '中性'}):\n"
                for news in important_news[:5]:
                    title = news.get('title', '')
                    keywords = news.get('keywords', [])
                    prompt += f"  - {title}"
                    if keywords:
                        prompt += f" [关键词: {', '.join(keywords)}]"
                    prompt += f"\n"
                prompt += f"  *请分析：政策面整体是偏紧还是偏松？这对该股票的影响是什么？*\n"
                prompt += f"  - 如果出现\"国务院印发\"、\"央行宣布\"级别新闻，政策权重应高于P/E估值\n"
                prompt += f"  - 关键词触发器：\"印发\"、\"规划\"、\"立案调查\"等会直接影响市场情绪\n\n"
            
            # 5. 中国市场情绪评分调整
            if china_adjustments:
                prompt += f"**5. 中国市场情绪评分调整**:\n"
                for adj in china_adjustments:
                    prompt += f"  - {adj}\n"
                prompt += f"\n"
    
    # 继续构建提示词的分析任务部分
    prompt += """

### 2. 分析任务 (请使用 Markdown 输出，必须严格按照以下结构输出报告)

**⚠️ 重要：报告结构要求**
你必须严格按照以下7个部分的顺序和标题输出报告，每个部分都必须包含，不能省略或合并：
1. 第一部分：投资风格与原则重申
2. 第二部分：公司概况（新增：包含公司业务介绍和最新动态）
3. 第三部分：AlphaG (G=B+M) 深度解构
4. 第四部分：五大支柱检查
4.5. 第四.五部分：风险控制评估（新增：包含风险评分、主要风险因素和短期波动风险）
5. 第五部分：估值分析与交易策略（宏观环境分析作为估值分析的背景，不是单独部分）
6. 第六部分：卖出策略

**第一部分：投资风格与原则重申**

明确说明当前使用的投资风格({style_names.get(style, style)})及其核心原则，解释为什么选择这个风格来分析该股票。

**⚠️ 重要提示**：本分析报告必须包含完整的买入和卖出策略。卖出策略是风险控制的核心，不能省略或模糊表述。

**第二部分：公司概况（⚠️ 必须包含此部分，这是新增的重要部分）**

你必须使用Markdown二级标题格式输出：## 第二部分：公司概况

此部分必须包含以下两个子部分：

"""
    # 添加公司概况部分
    if is_fund and fund_type == 'ETF':
        prompt += "1. **ETF跟踪标的和特点**：请简要说明ETF的跟踪标的和特点。\n\n"
    else:
        # 公司业务介绍
        prompt += f"1. **公司业务介绍**：请用中文，不超过4句话简要介绍 {data['name']} 的主要业务。"
        if data.get('business_summary'):
            business_summary_text = data.get('business_summary', '')[:800]  # 增加到800字符
            prompt += f"\n\n系统提供的公司业务描述（可能是英文，请翻译成中文并概括，不超过4句话）：\n{business_summary_text}\n"
            prompt += "\n**重要**：即使原始描述是英文，你也必须用中文回答。"
        else:
            prompt += "\n\n（系统未提供公司业务描述，请根据公司名称和行业信息用中文进行合理推断）\n"
        
        # 最新动态
        prompt += "\n2. **最新动态**：请列出公司最近的重要新闻或动态（最多3-5条）。"
        if data.get('company_news') and len(data.get('company_news', [])) > 0:
            prompt += "\n\n系统提供的最新新闻：\n"
            for idx, news in enumerate(data.get('company_news', [])[:5], 1):
                prompt += f"   {idx}. {news.get('title', '')} ({news.get('publisher', '未知来源')})\n"
            prompt += "\n请基于这些新闻进行总结，列出最重要的3-5条动态。"
        else:
            prompt += "\n\n（系统未获取到最新新闻，请说明：当前无法获取到该公司的最新新闻动态）\n"
    
    prompt += """

**第三部分：AlphaG (G=B+M) 深度解构**

"""
    # 添加B（基本面）部分
    if is_fund and fund_type == 'ETF':
        prompt += "* **B (基本面 Basics)**: 对于ETF，不适用公司财务指标（营收、利润、PE等）。请分析：\n"
        prompt += "  - ETF跟踪的标的指数是什么？指数的构成和权重如何？\n"
        prompt += "  - ETF的跟踪误差如何？管理费率是多少（如果数据中有）？\n"
        prompt += "  - 如果是杠杆ETF（如3x、UltraPro），需要特别说明杠杆倍数和风险（杠杆ETF在震荡市场中会遭受时间衰减）\n"
        prompt += "  - ETF的流动性如何？日均成交量是否充足？\n\n"
    else:
        prompt += f"* **B (基本面 Basics)**: 当前处于行业周期的哪个阶段（复苏/过热/滞胀/衰退）？数据支撑是什么？是否符合{style_names.get(style, style)}风格的要求？\n\n"
    
    # 添加S（市场情绪）部分
    prompt += "* **M (动量 Momentum)**: 当前价格是否包含了过度的乐观或悲观情绪？"
    if is_fund and fund_type == 'ETF':
        prompt += "对于ETF，主要关注技术面指标（价格位置、均线、52周区间）和跟踪标的指数的市场情绪。\n\n"
    else:
        prompt += "PE和PEG是否合理？\n\n"
    
    prompt += """
"""
    
    # 添加期权市场情绪分析
    if options_data and (vix > 25 or put_call_ratio > 1.0):
        prompt += """
  - **期权市场情绪**: 如果VIX>30或快速上升，说明市场恐慌情绪加剧，存在Vanna crush风险（波动率下降时做市商需要调整对冲，可能加剧价格波动）。如果Put/Call比率>1.2，说明看跌情绪强烈，做市商可能面临负Gamma风险（价格下跌时需要卖出更多标的资产对冲，可能加速下跌）。这些期权市场动态会显著影响短期价格走势，必须纳入M维度的分析。
"""
    
    # 添加宏观经济环境分析
    if macro_data and (macro_data.get('treasury_10y') or macro_data.get('dxy')):
        prompt += """
  - **宏观经济环境**: 美债收益率上升通常意味着流动性收紧，对股市不利。美元走强可能导致资金流出新兴市场。黄金上涨反映避险情绪。原油价格波动影响通胀预期。必须结合这些宏观指标评估整体市场环境。
"""
    
    # 添加成交量异常分析
    if volume_anomaly.get('is_anomaly'):
        if volume_anomaly.get('ratio', 0) > 2:
            prompt += "  - **成交量异常**: 成交量异常放大，可能存在重大消息或资金异动，需密切关注。\n"
        else:
            prompt += "  - **成交量异常**: 成交量异常萎缩，市场关注度下降，流动性风险增加。\n"
    
    # 添加重要经济事件分析
    if fed_meetings or cpi_releases:
        prompt += """
  - **重要经济事件**: 美联储利率决议和CPI数据发布是市场最重要的两个事件。利率决议直接影响市场流动性和风险偏好，CPI数据影响通胀预期和货币政策。在这些事件前后，市场波动通常加剧，建议提前调整仓位或保持观望。
"""
    
    # 添加期权到期日分析
    if options_expirations and len(options_expirations) > 0:
        prompt += """
  - **期权到期日（市场级别风险）**: 期权到期日（特别是四重到期日）是市场级别的风险事件，会影响整个市场的波动性。接近到期日时，做市商需要大量调整对冲头寸，可能引发Gamma挤压或释放，导致市场波动显著增加。这是系统性的市场风险，而非个股风险，建议在期权到期日前降低整体仓位或保持观望。
"""
    
    # 添加地缘政治风险分析
    if geopolitical_risk is not None:
        if geopolitical_risk >= 7:
            prompt += """
  - **地缘政治风险**: 地缘政治风险指数较高，需密切关注国际局势变化。地缘政治事件可能导致市场避险情绪上升，黄金和美元走强，股市承压。建议降低风险敞口，增加防御性资产配置。
"""
        elif geopolitical_risk >= 5:
            prompt += """
  - **地缘政治风险**: 地缘政治风险处于中等水平，需保持警惕。
"""
    
    # 继续构建提示词的剩余部分
    prompt += """

* **G (价格差异)**: 现在的价格相对于内在价值是便宜还是贵？结合52周区间分析价格位置。

**第四部分：五大支柱检查**

* **怀疑主义 (Skepticism)**: 请充当"空头律师"，列出 2-3 个如果不买这只股票的理由。

* **事前验尸 (Pre-mortem)**: 假设我们现在买入，一年后亏损了 50%，最可能的原因是什么？

**第四.五部分：风险控制评估**

你必须使用Markdown二级标题格式输出：## 第四.五部分：风险控制评估

此部分必须包含以下内容：

1. **风险评分**: 系统综合评估风险评分为 {risk_result['score']}/10 (等级: {risk_result['level']})

2. **主要风险因素**:
"""
    
    # 添加风险因素
    if risk_result['flags']:
        prompt += '\n'.join(['   - ' + flag for flag in risk_result['flags']]) + '\n'
    else:
        prompt += '   - 经系统评估，当前无明显结构性风险\n'
    
    # 添加 EV 模型短期风险评估
    ev_model = data.get('ev_model', {})
    if ev_model and not ev_model.get('error'):
        weighted_ev = ev_model.get('weighted_ev', 0)
        ev_recommendation = ev_model.get('recommendation', {})
        
        if abs(weighted_ev) > 0.03:  # 只有当 EV 显著时才显示
            prompt += f"""
3. **短期波动风险（基于量化模型）**:
   - 加权期望值: {weighted_ev:.2%}
   - 风险评估: {ev_recommendation.get('reason', '短期方向不明确')}
"""
            if ev_model.get('ev_1week'):
                ev_1week = ev_model['ev_1week']
                prob_up = ev_1week.get('prob_up', 0.5)
                prob_down = ev_1week.get('prob_down', 0.5)
                prompt += f"   - 短期概率分布: 上涨概率{prob_up*100:.0f}%，下跌概率{prob_down*100:.0f}%\n"
            
            prompt += f"""   - **投资风格说明**: 这是短期（1周至3个月）的风险评估，"""
            if style == 'quality' or style == 'value':
                prompt += f"对于{style_names.get(style, style)}风格的中长期投资，短期波动不应过度影响核心决策，但需要作为风险提示纳入考量。\n"
            else:
                prompt += f"对于{style_names.get(style, style)}风格，需要重点关注这一短期风险指标。\n"
        else:
            prompt += """
3. **短期波动风险**: 短期市场方向不明显，建议关注基本面和长期趋势。
"""
    else:
        prompt += """
3. **短期波动风险**: 量化模型暂时无法评估短期波动风险。
"""
    
    prompt += """
4. **风险控制建议**: 请基于以上风险评分、主要风险因素和短期波动风险，给出2-3条具体的风险控制建议。必须包括：
   - 仓位限制建议
   - 止损设置建议
   - 在什么情况下应该降低仓位或退出

**第五部分：估值分析与交易策略（必须包含）**

**估值分析内容**：
- 基于PE、PEG、增长率等指标的估值评估
- 目标价格的计算依据和合理性
- 当前价格相对于合理估值的偏离程度
- **宏观环境对估值的影响**：美债收益率、美元指数、VIX等宏观指标如何影响该股票的估值水平（例如：高利率环境会降低成长股估值，VIX上升会增加风险溢价等）。**宏观环境分析应该作为估值分析的一部分，说明宏观环境如何影响估值，而不是单独的一个部分。**

**交易策略内容**：

* **操作建议**: 明确给出操作建议（强力买入 / 分批建仓 / 观望 / 减仓 / 卖出），并说明理由。
    - **重要**: 当前价格 {data['currency_symbol']}{data['price']:.2f}，目标价格 {data['currency_symbol']}{data['target_price']:.2f}
    - 如果当前价格 >= 目标价格：**绝对不能建议"增持"或"买入"**，应该建议"观望"、"减仓"或"卖出"
    - 如果当前价格 >= 目标价格 * 1.1：应该建议"减仓"或"卖出"，而不是"观望"
    - 如果当前价格 >= 目标价格 * 1.2：应该强烈建议"卖出"锁定利润
    - 操作建议必须与当前价格和目标价格的关系一致，不能矛盾

* **目标价格**: 系统计算的目标价格为 {data['currency_symbol']}{data['target_price']:.2f}，当前价格为 {data['currency_symbol']}{data['price']:.2f}。
    {('**注意**：由于当前价格已经大幅超过合理估值，系统已调整目标价格为当前价格的95%作为止盈参考点。原始估值模型计算的目标价格为 ' + data['currency_symbol'] + str(round(data.get('original_target_price', data['target_price']), 2)) + '，这表明当前价格可能被高估。' if data.get('original_target_price') else '')}
    - **⚠️ 周期定义**：必须明确说明"本目标价格为6-12个月的中期目标价"
      - 华尔街标准：基于基本面（PEG/PE）的目标价，华尔街的标准通常是12个月
      - AlphaGBM模型调整：考虑到模型结合了动量（M）维度，我们将目标价周期定义为"6-12个月的中期目标价"
      - 周期合理性：3-6个月太短，容易受短期噪音影响；基本面价值回归通常需要2个季度以上的验证周期
      - 提醒投资者：目标价不是短期交易信号，而是基于基本面价值回归的中期预期
    - 如果当前价格 < 目标价格：说明还有上涨空间，可以买入或持有，当价格达到目标价格时考虑止盈
    - 如果当前价格 >= 目标价格：**重要**：当前价格已经达到或超过目标价格，说明已经达到或超过合理估值，**不要建议等待价格达到目标价格再卖出**，应该立即评估是否需要止盈或减仓
    - 如果当前价格超过目标价格5%以上：建议考虑分批减仓（减仓30-50%），保留部分仓位继续观察
    - 如果当前价格超过目标价格20%以上：说明价格已经被严重高估，建议立即减仓50%以上或全部卖出锁定利润
    - 必须基于当前价格和目标价格的关系，给出合理的操作建议

* **止损价格**: 系统已计算止损价格为 {data['currency_symbol']}{stop_loss_price:.2f}（{stop_loss_method}，止损幅度{stop_loss_pct:.1f}%）。请在分析中说明这个止损价格的合理性，并解释为什么使用这种止损方法。

* **建仓策略**: 详细说明如何建仓（一次性还是分批，分批的话分几批，每批多少，时间间隔）。

* **持有周期**: 根据{style_names.get(style, style)}风格，建议持有多长时间。

* **仓位管理**: 重申建议仓位{risk_result['suggested_position']}%，并说明仓位管理原则。

* **⚠️ 财报日避险检查（强制规则）**:
  - 如果财报日期 < 7天（高危）：**强烈建议在财报前3天避险或减仓**
    - 理由：财报是二元事件（Binary Event），可能导致大幅波动，建议提前避险
    - 避险建议：财报前3天建议减仓30-50%，或全部卖出避险，待财报后再决定是否重新建仓
  - 如果财报日期 7-14天（中危）：**建议提前规划，考虑在财报前适当减仓**
  - 如果财报日期 > 14天（低危）：**正常持有，但需关注财报日期**
  - **例外情况**：如果基本面非常强劲且预期财报利好，可以保留部分仓位，但必须设置止损

**第六部分：卖出策略（⚠️ 必须包含，这是最重要的风险控制部分）**

**重要提示**：卖出策略是风险控制的核心，必须详细说明。请根据投资风格和个股情况，提供**无风险的卖出策略**，确保投资者能够及时止损和止盈，规避风险。必须包含以下所有内容：

* **止盈策略**: 
  - **重要**：当前价格 {data['currency_symbol']}{data['price']:.2f}，目标价格 {data['currency_symbol']}{data['target_price']:.2f}
  - 如果当前价格 < 目标价格：当价格达到目标价格时，如何操作？（一次性卖出 / 分批卖出）
  - 如果当前价格 >= 目标价格：**不要建议等待价格达到目标价格**，应该立即评估是否需要止盈或减仓。如果当前价格已经超过目标价格20%以上，建议立即减仓50%以上或全部卖出锁定利润
  - 如果当前价格 >= 目标价格但 < 目标价格 * 1.2：可以考虑分批减仓，保留部分仓位继续观察
  - 根据{style_names.get(style, style)}风格，给出具体的止盈点建议（必须考虑当前价格与目标价格的关系）

* **止损策略**: 
  - 系统已设置止损价格为 {data['currency_symbol']}{stop_loss_price:.2f}（{stop_loss_method}，止损幅度{stop_loss_pct:.1f}%）
  - 解释这个止损价格的合理性
  - 是否需要在止损前设置预警点？
  - 严格执行止损的纪律说明

* **分阶段卖出策略**: 
  - 如果采用分批建仓，对应的分批卖出策略是什么？
  - 建议在什么价位分阶段减仓？（例如：达到目标价格的80%/100%/120%分别卖出多少比例）
  - 根据{style_names.get(style, style)}风格的持有周期，何时应该完全退出？

* **特殊情况卖出**:
  - 基本面恶化（营收负增长、利润率大幅下降）时如何应对？
  - 估值过高（PE异常升高）时是否提前卖出？
  - 市场情绪变化（VIX飙升、市场系统性风险）时如何调整？

* **卖出时机建议**:
  - **⚠️ 财报日避险（强制规则）**：
    - **财报前3天强制检查**：如果财报日期 < 7天，必须评估是否在财报前3天避险
    - **避险建议**：
      - 如果财报日期 < 7天（高危）：**强烈建议在财报前3天减仓30-50%或全部卖出避险**
      - 如果财报日期 7-14天（中危）：**建议提前规划，考虑在财报前适当减仓**
      - 如果财报日期 > 14天（低危）：**正常持有，但需关注财报日期**
    - **避险理由**：财报是二元事件（Binary Event），可能导致大幅波动，提前避险是风险控制的核心
    - **例外情况**：如果基本面非常强劲且预期财报利好，可以保留部分仓位，但必须设置止损
  - 避免在期权到期日附近卖出（市场波动可能影响成交价格）
  - 根据重要经济事件（美联储会议、CPI发布等）调整卖出时机

* **风险规避原则**:
  - 严格执行止损，不要因为"再等等"而犹豫
  - 达到目标价格后，根据投资风格决定是全部卖出还是分批卖出
  - 如果市场出现系统性风险（VIX>30、地缘政治风险>7），建议提前减仓或全部卖出
  - 如果基本面恶化（营收转负、利润率大幅下降），立即卖出，不要等待
  - 如果估值过高（PE超过合理范围50%以上），考虑提前卖出锁定利润

**⚠️ 特别强调**：卖出策略必须具体、可执行，不能使用"根据情况决定"、"灵活调整"等模糊表述。必须给出具体的价格点位、时间节点和操作比例。

**语气要求**: 客观、专业、犀利、不论情面，严格遵守纪律。不要讲废话。所有数字必须具体，不要模糊表述。卖出策略必须清晰可执行，避免模糊的表述。**卖出策略是风险控制的核心，必须详细说明，不能省略。**

---

**⚠️ 最后强调：报告结构要求**

请务必严格按照以下7个部分的顺序和标题输出报告，使用Markdown格式的二级标题（## 第一部分：...）：

1. ## 第一部分：投资风格与原则重申
2. ## 第二部分：公司概况（必须包含：公司业务介绍 + 最新动态）
3. ## 第三部分：AlphaG (G=B+M) 深度解构
4. ## 第四部分：五大支柱检查
4.5. ## 第四.五部分：风险控制评估（必须包含：风险评分 + 主要风险因素 + 短期波动风险 + 风险控制建议）
5. ## 第五部分：估值分析与交易策略（宏观环境分析作为估值分析的背景，说明宏观环境如何影响估值）
6. ## 第六部分：卖出策略

**特别强调**：
- 每个部分都必须包含，不能省略、合并或改变顺序
- **第二部分：公司概况是新增的必需部分，绝不能省略**
- 第二部分必须包含两个子部分：（1）公司业务介绍（不超过4句话）和（2）最新动态（3-5条重要新闻）
- **第四.五部分：风险控制评估是新增的必需部分，绝不能省略**
- 第四.五部分必须包含：风险评分、主要风险因素、短期波动风险（基于EV模型）和风险控制建议
- 即使系统未提供新闻数据，也要说明"当前无法获取到最新新闻动态"
"""

    try:
        # models = genai.list_models()
        # for model in models:
        #     if 'generateContent' in model.supported_generation_methods:
        #         print(f"- {model.name} (支持 generateContent)")
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        start_time = time.time()
        response = model.generate_content(prompt)
        elapsed = time.time() - start_time
        print(f"[Gemini] generate_content 耗时: {elapsed:.2f}s")
        return response.text
    except Exception as e:
        print(f"Gemini API 连接失败: {str(e)}")
        print("使用备用分析功能...")
        return get_fallback_analysis(ticker, style, data, risk_result)

