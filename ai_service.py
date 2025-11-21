import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# 配置 Gemini
api_key = os.getenv("GOOGLE_API_KEY")
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
        week52_high = data.get('week52_high') or data['price'] * 1.2
        target_price = week52_high * 0.9 if price_position < 0.5 else week52_high * 1.1
    
    stop_loss = data['price'] * 0.85  # 15%止损
    
    analysis = f"""## 投资分析报告 - {data['name']} ({ticker})

### 投资风格与原则

**当前投资风格**: {style_names.get(style, style)}

**风格核心原则**: {style_principles.get(style, '')}

**仓位限制**: 根据{style_names.get(style, style)}风格，建议最大仓位为{risk_result['suggested_position']}%

---

### G=B+M 模型分析

**G (价格)**: 当前价格 ${data['price']:.2f}，位于52周区间 ${data['week52_low']:.2f} - ${data['week52_high']:.2f} 的 {price_position*100:.1f}% 位置。

**B (基本面)**: 
- 营收增长率: {data['growth']*100:.2f}%
- 利润率: {data['margin']*100:.2f}%
- 基本面评估: {'良好' if data['growth'] > 0.1 and data['margin'] > 0.1 else '一般' if data['growth'] > 0 else '较差'}

**M (市场情绪/估值)**:
- 市盈率(PE): {f"{data['pe']:.2f}" if data['pe'] and data['pe'] > 0 else 'N/A'}
- PEG比率: {f"{data['peg']:.2f}" if data['peg'] and data['peg'] > 0 else 'N/A'}
- 估值评估: {'偏高' if data['pe'] and data['pe'] > 30 else '合理' if data['pe'] and data['pe'] > 15 else '偏低' if data['pe'] else '数据不足'}
{f"- VIX恐慌指数: {data.get('options_data', {}).get('vix', 'N/A'):.2f}" if data.get('options_data', {}).get('vix') is not None else ""}
{f"- VIX变化: {data.get('options_data', {}).get('vix_change', 0):.1f}%" if data.get('options_data', {}).get('vix_change') is not None else ""}
{f"- Put/Call比率: {data.get('options_data', {}).get('put_call_ratio', 'N/A'):.2f}" if data.get('options_data', {}).get('put_call_ratio') is not None else ""}
{f"- 期权市场风险: {'⚠️ 高波动风险（VIX>30）' if (data.get('options_data', {}).get('vix') or 0) > 30 else '⚠️ 负Gamma风险（P/C>1.2）' if (data.get('options_data', {}).get('put_call_ratio') or 0) > 1.2 else '正常' if data.get('options_data', {}).get('vix') is not None else 'N/A'}" if data.get('options_data') else ""}

---

### 风险控制评估

**风险评分**: {risk_result['score']}/10 ({risk_result['level']})

**主要风险点**:
{chr(10).join(['- ' + flag for flag in risk_result['flags']]) if risk_result['flags'] else '- 无明显结构性风险'}

---

### 交易策略建议

**操作建议**: {'观望（不建议建仓）' if risk_result['suggested_position'] == 0 else '观望' if risk_result['score'] >= 6 else '分批建仓' if risk_result['score'] >= 4 else '可以考虑建仓' if risk_result['score'] >= 2 else '适合建仓'}

**目标价格**: ${target_price:.2f} ${'（风险过高，不建议买入，无目标价格）' if risk_result['suggested_position'] == 0 else '(基于技术面和估值分析)'}

**止损价格**: ${stop_loss:.2f} (建议止损幅度: 15%)

**建议仓位**: {risk_result['suggested_position']}%

**建仓策略**: 
{f'当前风险评分过高（{risk_result["score"]}/10），不建议建仓。建议继续观望，等待风险降低或寻找其他投资机会。' if risk_result['suggested_position'] == 0 else f'- 如果风险评分 >= 4: 建议分3批建仓，每批间隔1-2周，每批约{risk_result["suggested_position"]/3:.1f}%\n- 如果风险评分 < 4: 可以一次性建仓，但不超过建议仓位上限{risk_result["suggested_position"]}%'}

**持有周期**: 根据{style_names.get(style, style)}风格，建议持有{'长期(1-3年)' if style == 'quality' else '中期(6-12个月)' if style == 'value' else '中短期(3-6个月)' if style == 'growth' else '短期(1-3个月)'}

---

### 注意事项

1. 严格遵守仓位限制，不要超过{risk_result['suggested_position']}%
2. 设置止损价格 ${stop_loss:.2f}，严格执行止损纪律
3. 定期复查基本面数据，如营收增长转负或利润率大幅下降，考虑减仓
4. 关注市场情绪变化，如PE倍数异常升高，警惕估值泡沫
"""
    return analysis


def get_gemini_analysis(ticker, style, data, risk_result):
    """
    发送数据给 Gemini 进行定性分析
    """
    if not api_key:
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

    # 构建 Prompt (提示词工程)
    prompt = f"""
你是一位精通"胡猛投机模型(G=B+M)"和"五大支柱投资框架"的资深基金经理。请对 {data['name']} ({ticker}) 进行严格的投资分析。

### 重要：投资风格与原则

**当前投资风格**: {style_names.get(style, style)}
**风格核心原则**: {style_principles.get(style, '')}
**仓位限制**: 根据{style_names.get(style, style)}风格，建议最大仓位为{risk_result['suggested_position']}%

你必须严格按照以上投资风格和原则进行分析，所有建议必须符合该风格的特征。

### 1. 上下文数据

- **当前价格 (G)**: ${data['price']:.2f} (52周区间: ${data['week52_low']:.2f} - ${data['week52_high']:.2f})
- **基本面 (B)**: 营收增长 {data['growth']:.1%}, 利润率 {data['margin']:.1%}
    - **情绪/估值 (M)**: PE {f"{data['pe']:.2f}" if data['pe'] and data['pe'] > 0 else 'N/A'}, PEG {f"{data['peg']:.2f}" if data['peg'] and data['peg'] > 0 else 'N/A'}
- **技术面**: 50日均线 ${data['ma50']:.2f}, 200日均线 ${data['ma200']:.2f}
- **系统风控评分**: {risk_result['score']}/10 (等级: {risk_result['level']})
- **主要风险点**: {', '.join(risk_result['flags']) if risk_result['flags'] else '无明显风险'}
{f"- **期权市场数据**: VIX恐慌指数 {data.get('options_data', {}).get('vix', 'N/A'):.2f}" if data.get('options_data', {}).get('vix') is not None else ""}
{f"  - VIX变化: {data.get('options_data', {}).get('vix_change', 0):.1f}%" if data.get('options_data', {}).get('vix_change') is not None else ""}
{f"  - Put/Call比率: {data.get('options_data', {}).get('put_call_ratio', 'N/A'):.2f}" if data.get('options_data', {}).get('put_call_ratio') is not None else ""}
{f"  - **⚠️ 期权市场风险提示**: {'VIX处于高位，存在Vanna crush和负Gamma风险，可能导致市场加速下跌' if (data.get('options_data', {}).get('vix') or 0) > 30 else 'Put/Call比率偏高，看跌情绪强烈，做市商可能面临负Gamma压力' if (data.get('options_data', {}).get('put_call_ratio') or 0) > 1.2 else ''}" if data.get('options_data') and ((data.get('options_data', {}).get('vix') or 0) > 30 or (data.get('options_data', {}).get('put_call_ratio') or 0) > 1.2) else ""}
{f"- **宏观经济环境**: 10年美债收益率 {data.get('macro_data', {}).get('treasury_10y', 'N/A'):.2f}%" if data.get('macro_data', {}).get('treasury_10y') is not None else ""}
{f"  - 美元指数: {data.get('macro_data', {}).get('dxy', 'N/A'):.2f}" if data.get('macro_data', {}).get('dxy') is not None else ""}
{f"  - 黄金: ${data.get('macro_data', {}).get('gold', 'N/A'):.2f}" if data.get('macro_data', {}).get('gold') is not None else ""}
{f"  - 原油: ${data.get('macro_data', {}).get('oil', 'N/A'):.2f}" if data.get('macro_data', {}).get('oil') is not None else ""}
{f"- **成交量异常**: {'成交量异常放大' if data.get('volume_anomaly', {}).get('is_anomaly') and data.get('volume_anomaly', {}).get('ratio', 0) > 2 else '成交量异常萎缩' if data.get('volume_anomaly', {}).get('is_anomaly') else ''}" if data.get('volume_anomaly', {}).get('is_anomaly') else ""}
{f"- **财报日期**: {', '.join(data.get('earnings_dates', []))}" if data.get('earnings_dates') and len(data.get('earnings_dates', [])) > 0 else ""}
{f"- **美联储利率决议**: {', '.join([m['date'] + ' (' + str(m['days_until']) + '天后' + ('，含点阵图' if m.get('has_dot_plot') else '') + ')' for m in data.get('macro_data', {}).get('fed_meetings', [])])}" if data.get('macro_data', {}).get('fed_meetings') and len(data.get('macro_data', {}).get('fed_meetings', [])) > 0 else ""}
{f"- **CPI数据发布**: {', '.join([c['date'] + ' (' + str(c['days_until']) + '天后，发布' + c['data_month'] + '数据)' for c in data.get('macro_data', {}).get('cpi_releases', [])])}" if data.get('macro_data', {}).get('cpi_releases') and len(data.get('macro_data', {}).get('cpi_releases', [])) > 0 else ""}
{f"- **期权到期日（交割日）**: {', '.join([exp['date'] + ' (' + str(exp['days_until']) + '天后，' + exp.get('type', '月度到期日') + (', 四重到期日' if exp.get('is_quadruple_witching') else '') + ')' for exp in data.get('macro_data', {}).get('options_expirations', [])])}" if data.get('macro_data', {}).get('options_expirations') and len(data.get('macro_data', {}).get('options_expirations', [])) > 0 else ""}
{f"- **地缘政治风险指数**: {data.get('macro_data', {}).get('geopolitical_risk', 'N/A')}/10 {'⚠️ 高风险' if (data.get('macro_data', {}).get('geopolitical_risk') or 0) >= 7 else '中等风险' if (data.get('macro_data', {}).get('geopolitical_risk') or 0) >= 5 else '低风险' if data.get('macro_data', {}).get('geopolitical_risk') is not None else ''}" if data.get('macro_data', {}).get('geopolitical_risk') is not None else ""}

### 2. 分析任务 (请使用 Markdown 输出，必须包含以下所有部分)

**第一部分：投资风格与原则重申**

明确说明当前使用的投资风格({style_names.get(style, style)})及其核心原则，解释为什么选择这个风格来分析该股票。

**第二部分：G=B+M 深度解构**

* **B (基本面)**: 当前处于行业周期的哪个阶段（复苏/过热/滞胀/衰退）？数据支撑是什么？是否符合{style_names.get(style, style)}风格的要求？

* **M (市场情绪)**: 当前价格是否包含了过度的乐观或悲观情绪？PE和PEG是否合理？
{f"  - **期权市场情绪**: 如果VIX>30或快速上升，说明市场恐慌情绪加剧，存在Vanna crush风险（波动率下降时做市商需要调整对冲，可能加剧价格波动）。如果Put/Call比率>1.2，说明看跌情绪强烈，做市商可能面临负Gamma风险（价格下跌时需要卖出更多标的资产对冲，可能加速下跌）。这些期权市场动态会显著影响短期价格走势，必须纳入M维度的分析。" if data.get('options_data') and ((data.get('options_data', {}).get('vix') or 0) > 25 or (data.get('options_data', {}).get('put_call_ratio') or 0) > 1.0) else ""}
{f"  - **宏观经济环境**: 美债收益率上升通常意味着流动性收紧，对股市不利。美元走强可能导致资金流出新兴市场。黄金上涨反映避险情绪。原油价格波动影响通胀预期。必须结合这些宏观指标评估整体市场环境。" if data.get('macro_data') and (data.get('macro_data', {}).get('treasury_10y') or data.get('macro_data', {}).get('dxy')) else ""}
{f"  - **成交量异常**: {'成交量异常放大，可能存在重大消息或资金异动，需密切关注。' if data.get('volume_anomaly', {}).get('is_anomaly') and data.get('volume_anomaly', {}).get('ratio', 0) > 2 else '成交量异常萎缩，市场关注度下降，流动性风险增加。' if data.get('volume_anomaly', {}).get('is_anomaly') else ''}" if data.get('volume_anomaly', {}).get('is_anomaly') else ""}
{f"  - **重要经济事件**: {'美联储利率决议和CPI数据发布是市场最重要的两个事件。利率决议直接影响市场流动性和风险偏好，CPI数据影响通胀预期和货币政策。在这些事件前后，市场波动通常加剧，建议提前调整仓位或保持观望。' if (data.get('macro_data', {}).get('fed_meetings') or data.get('macro_data', {}).get('cpi_releases')) else ''}" if (data.get('macro_data', {}).get('fed_meetings') or data.get('macro_data', {}).get('cpi_releases')) else ""}
{f"  - **期权到期日（市场级别风险）**: {'期权到期日（特别是四重到期日）是市场级别的风险事件，会影响整个市场的波动性。接近到期日时，做市商需要大量调整对冲头寸，可能引发Gamma挤压或释放，导致市场波动显著增加。这是系统性的市场风险，而非个股风险，建议在期权到期日前降低整体仓位或保持观望。' if data.get('macro_data', {}).get('options_expirations') and len(data.get('macro_data', {}).get('options_expirations', [])) > 0 else ''}" if data.get('macro_data', {}).get('options_expirations') and len(data.get('macro_data', {}).get('options_expirations', [])) > 0 else ""}
{f"  - **地缘政治风险**: {'地缘政治风险指数较高，需密切关注国际局势变化。地缘政治事件可能导致市场避险情绪上升，黄金和美元走强，股市承压。建议降低风险敞口，增加防御性资产配置。' if (data.get('macro_data', {}).get('geopolitical_risk') or 0) >= 7 else '地缘政治风险处于中等水平，需保持警惕。' if (data.get('macro_data', {}).get('geopolitical_risk') or 0) >= 5 else ''}" if data.get('macro_data', {}).get('geopolitical_risk') is not None else ""}

* **G (价格差异)**: 现在的价格相对于内在价值是便宜还是贵？结合52周区间分析价格位置。

**第三部分：五大支柱检查**

* **怀疑主义 (Skepticism)**: 请充当"空头律师"，列出 2-3 个如果不买这只股票的理由。

* **事前验尸 (Pre-mortem)**: 假设我们现在买入，一年后亏损了 50%，最可能的原因是什么？

**第四部分：具体交易策略与目标价格（必须包含）**

* **操作建议**: 明确给出操作建议（强力买入 / 分批建仓 / 观望 / 卖出 / 做空），并说明理由。

* **目标价格**: 必须给出具体的买入目标价格和卖出目标价格（基于技术面、估值和{style_names.get(style, style)}风格的要求）。

* **止损价格**: 必须给出具体的止损价格（基于技术面或估值容忍度），并说明止损理由。

* **建仓策略**: 详细说明如何建仓（一次性还是分批，分批的话分几批，每批多少，时间间隔）。

* **持有周期**: 根据{style_names.get(style, style)}风格，建议持有多长时间。

* **仓位管理**: 重申建议仓位{risk_result['suggested_position']}%，并说明仓位管理原则。

**语气要求**: 客观、专业、犀利、不论情面，严格遵守纪律。不要讲废话。所有数字必须具体，不要模糊表述。
"""

    try:
        # 使用 gemini-1.5-flash 模型 (速度快，且免费额度够用)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API 连接失败: {str(e)}")
        print("使用备用分析功能...")
        return get_fallback_analysis(ticker, style, data, risk_result)

