"""
叙事雷达服务 - Narrative Radar Service
AI 驱动的概念/叙事股票发现功能
"""

import google.generativeai as genai
import os
import json
import re

# 预设叙事配置
PRESET_NARRATIVES = {
    # 人物叙事
    'musk': {
        'name_zh': '马斯克概念',
        'name_en': 'Musk Plays',
        'type': 'person',
        'description_zh': '颠覆者叙事：关注其创办/投资的公司及供应链受益股',
        'description_en': 'Disruptor narrative: Companies founded/invested by Musk and supply chain beneficiaries'
    },
    'buffett': {
        'name_zh': '巴菲特持仓',
        'name_en': 'Buffett Portfolio',
        'type': 'institution',
        'description_zh': '价值投资叙事：伯克希尔核心持仓及新增买入',
        'description_en': 'Value investing: Berkshire core holdings and recent additions'
    },
    'ark': {
        'name_zh': '木头姐ARK',
        'name_en': 'ARK Invest',
        'type': 'institution',
        'description_zh': '颠覆性创新叙事：ARK基金重仓的创新科技股',
        'description_en': 'Disruptive innovation: ARK fund high-conviction holdings'
    },
    'dalio': {
        'name_zh': '达利欧桥水',
        'name_en': 'Ray Dalio',
        'type': 'institution',
        'description_zh': '宏观对冲叙事：桥水基金全天候策略持仓',
        'description_en': 'Macro hedge: Bridgewater All Weather strategy holdings'
    },
    'burry': {
        'name_zh': '大空头Burry',
        'name_en': 'Michael Burry',
        'type': 'institution',
        'description_zh': '逆向投资叙事：Scion Asset Management 持仓',
        'description_en': 'Contrarian investing: Scion Asset Management holdings'
    },
    # 主题叙事
    'ai_chips': {
        'name_zh': 'AI芯片',
        'name_en': 'AI Chips',
        'type': 'theme',
        'description_zh': '算力叙事：GPU、ASIC、AI加速器相关公司',
        'description_en': 'Compute narrative: GPU, ASIC, AI accelerator companies'
    },
    'glp1': {
        'name_zh': '减肥药GLP-1',
        'name_en': 'GLP-1 Weight Loss',
        'type': 'theme',
        'description_zh': '医疗创新叙事：GLP-1药物研发及受益产业链',
        'description_en': 'Medical innovation: GLP-1 drug developers and beneficiaries'
    },
    'quantum': {
        'name_zh': '量子计算',
        'name_en': 'Quantum Computing',
        'type': 'theme',
        'description_zh': '下一代计算叙事：量子硬件、软件及应用公司',
        'description_en': 'Next-gen computing: Quantum hardware, software, applications'
    },
    'robotics': {
        'name_zh': '机器人',
        'name_en': 'Robotics',
        'type': 'theme',
        'description_zh': '自动化叙事：工业机器人、人形机器人、自动化公司',
        'description_en': 'Automation narrative: Industrial, humanoid robots, automation companies'
    },
    'ev_battery': {
        'name_zh': '电池与储能',
        'name_en': 'EV Battery',
        'type': 'theme',
        'description_zh': '能源转型叙事：电池制造、材料、储能系统公司',
        'description_en': 'Energy transition: Battery manufacturing, materials, storage systems'
    }
}


def get_preset_narratives():
    """返回所有预设叙事"""
    return PRESET_NARRATIVES


# 备用数据 - 当 Gemini API 不可用时使用（支持中英文）
# 结构: { narrative_key: { 'zh': {...}, 'en': {...} } }
FALLBACK_DATA = {
    'musk': {
        'zh': {
            'narrative': {'name': '马斯克概念', 'type': 'person', 'thesis': '投资马斯克创办或深度参与的公司，利用其创新能力和市场影响力获取超额收益。', 'risk_factors': ['政策风险（如电动车补贴变化）', '高估值回调风险', '执行风险（如量产延迟）']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 98, 'reason': '马斯克创办并担任CEO的核心公司', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$250 Call + 卖出1张$300 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'relevance_score': 85, 'reason': 'Tesla AI训练核心GPU供应商', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$120 Call + 卖出1张$140 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$100 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'XPEV', 'name': 'XPeng Inc', 'relevance_score': 72, 'reason': '中国电动车竞争对手', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$12 Call (Delta 0.75)', 'leverage': '3x', 'theta_cost': '中'}}},
                {'symbol': 'RIVN', 'name': 'Rivian Automotive', 'relevance_score': 70, 'reason': '电动皮卡直接竞争对手', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$15 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': '中'}}},
                {'symbol': 'LI', 'name': 'Li Auto Inc', 'relevance_score': 68, 'reason': '中国新能源车企', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$30 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}}
            ],
            'summary': '马斯克概念以TSLA为核心，辐射电动车产业链和AI芯片。建议核心配置TSLA，利用ZEBRA策略获取2x杠杆同时控制时间价值损耗。'
        },
        'en': {
            'narrative': {'name': 'Musk Plays', 'type': 'person', 'thesis': 'Invest in companies founded or deeply involved by Musk, leveraging his innovation and market influence for alpha.', 'risk_factors': ['Policy risk (EV subsidies)', 'High valuation correction', 'Execution risk (production delays)']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 98, 'reason': 'Core company founded and led by Musk as CEO', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $250 Call + Sell 1x $300 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'relevance_score': 85, 'reason': 'Core GPU supplier for Tesla AI training', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $120 Call + Sell 1x $140 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $100 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'XPEV', 'name': 'XPeng Inc', 'relevance_score': 72, 'reason': 'Chinese EV competitor', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $12 Call (Delta 0.75)', 'leverage': '3x', 'theta_cost': 'Medium'}}},
                {'symbol': 'RIVN', 'name': 'Rivian Automotive', 'relevance_score': 70, 'reason': 'Direct EV truck competitor', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $15 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': 'Medium'}}},
                {'symbol': 'LI', 'name': 'Li Auto Inc', 'relevance_score': 68, 'reason': 'Chinese NEV company', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $30 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Musk plays centered on TSLA, extending to EV supply chain and AI chips. Core allocation in TSLA recommended, using ZEBRA strategy for 2x leverage while controlling theta decay.'
        }
    },
    'buffett': {
        'zh': {
            'narrative': {'name': '巴菲特持仓', 'type': 'institution', 'thesis': '跟随价值投资大师的核心持仓，投资护城河深厚、现金流稳定的优质企业。', 'risk_factors': ['持仓披露45天滞后', '巴菲特可能已减仓', '高估值买入风险']},
            'stocks': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'relevance_score': 95, 'reason': '伯克希尔第一大重仓股，占投资组合40%+', 'position_change': '持平', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$180 Call + 卖出1张$200 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'BAC', 'name': 'Bank of America', 'relevance_score': 88, 'reason': '金融板块核心持仓', 'position_change': '减持', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$35 Call + 卖出1张$40 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$32 Call (Delta 0.80)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'AXP', 'name': 'American Express', 'relevance_score': 85, 'reason': '优质金融服务公司', 'position_change': '持平', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$220 Call + 卖出1张$250 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$200 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'KO', 'name': 'Coca-Cola', 'relevance_score': 82, 'reason': '消费品核心持仓', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$58 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'CVX', 'name': 'Chevron Corp', 'relevance_score': 78, 'reason': '能源板块重仓股', 'position_change': '增持', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$145 Call + 卖出1张$160 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$140 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}}
            ],
            'summary': '巴菲特持仓以AAPL为绝对核心，金融和消费为辅。建议关注CVX等新增仓股票，利用LEAPS策略获取杠杆收益。'
        },
        'en': {
            'narrative': {'name': 'Buffett Portfolio', 'type': 'institution', 'thesis': 'Follow the value investing master\'s core holdings, investing in quality companies with deep moats and stable cash flows.', 'risk_factors': ['45-day disclosure lag', 'Buffett may have reduced positions', 'High valuation entry risk']},
            'stocks': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'relevance_score': 95, 'reason': 'Berkshire\'s #1 holding, 40%+ of portfolio', 'position_change': 'Hold', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $180 Call + Sell 1x $200 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'BAC', 'name': 'Bank of America', 'relevance_score': 88, 'reason': 'Core financial sector holding', 'position_change': 'Reduced', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $35 Call + Sell 1x $40 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $32 Call (Delta 0.80)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'AXP', 'name': 'American Express', 'relevance_score': 85, 'reason': 'Quality financial services company', 'position_change': 'Hold', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $220 Call + Sell 1x $250 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $200 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'KO', 'name': 'Coca-Cola', 'relevance_score': 82, 'reason': 'Core consumer staples holding', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $58 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'CVX', 'name': 'Chevron Corp', 'relevance_score': 78, 'reason': 'Major energy holding', 'position_change': 'Added', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $145 Call + Sell 1x $160 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $140 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Buffett portfolio centered on AAPL, with financials and consumer staples as supporting positions. Watch CVX for new additions, use LEAPS strategy for leveraged returns.'
        }
    },
    'ark': {
        'zh': {
            'narrative': {'name': '木头姐ARK', 'type': 'institution', 'thesis': '投资颠覆性创新公司，押注指数级增长的科技趋势。', 'risk_factors': ['高波动性', '成长股估值风险', '宏观利率敏感']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 95, 'reason': 'ARK旗舰基金ARKK第一大持仓', 'position_change': '持平', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$250 Call + 卖出1张$300 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'COIN', 'name': 'Coinbase Global', 'relevance_score': 88, 'reason': '加密货币基础设施核心标的', 'position_change': '增持', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$180 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': '中'}}},
                {'symbol': 'ROKU', 'name': 'Roku Inc', 'relevance_score': 82, 'reason': '流媒体平台核心持仓', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$60 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '中'}}},
                {'symbol': 'SQ', 'name': 'Block Inc', 'relevance_score': 80, 'reason': '金融科技核心标的', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$65 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'PATH', 'name': 'UiPath Inc', 'relevance_score': 75, 'reason': 'AI自动化软件公司', 'position_change': '增持', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$12 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': '中'}}}
            ],
            'summary': 'ARK持仓聚焦颠覆性创新，TSLA和COIN为核心。高波动特性适合使用LEAPS策略。'
        },
        'en': {
            'narrative': {'name': 'ARK Invest', 'type': 'institution', 'thesis': 'Invest in disruptive innovation, betting on exponential growth in technology trends.', 'risk_factors': ['High volatility', 'Growth stock valuation risk', 'Interest rate sensitivity']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 95, 'reason': '#1 holding in ARKK flagship fund', 'position_change': 'Hold', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $250 Call + Sell 1x $300 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'COIN', 'name': 'Coinbase Global', 'relevance_score': 88, 'reason': 'Core crypto infrastructure play', 'position_change': 'Added', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $180 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': 'Medium'}}},
                {'symbol': 'ROKU', 'name': 'Roku Inc', 'relevance_score': 82, 'reason': 'Core streaming platform holding', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $60 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Medium'}}},
                {'symbol': 'SQ', 'name': 'Block Inc', 'relevance_score': 80, 'reason': 'Core fintech play', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $65 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'PATH', 'name': 'UiPath Inc', 'relevance_score': 75, 'reason': 'AI automation software', 'position_change': 'Added', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $12 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': 'Medium'}}}
            ],
            'summary': 'ARK holdings focus on disruptive innovation, with TSLA and COIN as core. High volatility suits LEAPS strategy.'
        }
    },
    'ai_chips': {
        'zh': {
            'narrative': {'name': 'AI芯片', 'type': 'theme', 'thesis': '算力是AI时代的"石油"，GPU和专用AI芯片需求爆发式增长。', 'risk_factors': ['周期性风险', '竞争加剧', '客户集中度风险']},
            'stocks': [
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'relevance_score': 98, 'reason': 'AI训练GPU绝对龙头，市占率80%+', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$120 Call + 卖出1张$140 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$100 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'relevance_score': 90, 'reason': 'GPU第二大厂商，MI300芯片', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$150 Call + 卖出1张$170 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$130 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'TSM', 'name': 'Taiwan Semiconductor', 'relevance_score': 92, 'reason': 'AI芯片代工垄断者', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$180 Call + 卖出1张$200 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$160 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'AVGO', 'name': 'Broadcom Inc', 'relevance_score': 85, 'reason': '定制AI芯片供应商', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$180 Call + 卖出1张$200 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$160 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'MRVL', 'name': 'Marvell Technology', 'relevance_score': 78, 'reason': '数据中心AI芯片', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$70 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}}
            ],
            'summary': 'AI芯片赛道以NVDA为绝对龙头，TSM为产业链关键。建议核心配置NVDA+TSM。'
        },
        'en': {
            'narrative': {'name': 'AI Chips', 'type': 'theme', 'thesis': 'Compute is the "oil" of the AI era, with explosive demand for GPUs and specialized AI chips.', 'risk_factors': ['Cyclical risk', 'Intensifying competition', 'Customer concentration']},
            'stocks': [
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'relevance_score': 98, 'reason': 'Absolute leader in AI training GPUs, 80%+ market share', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $120 Call + Sell 1x $140 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $100 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'relevance_score': 90, 'reason': '#2 GPU maker, MI300 chip', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $150 Call + Sell 1x $170 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $130 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'TSM', 'name': 'Taiwan Semiconductor', 'relevance_score': 92, 'reason': 'AI chip foundry monopoly', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $180 Call + Sell 1x $200 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $160 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'AVGO', 'name': 'Broadcom Inc', 'relevance_score': 85, 'reason': 'Custom AI chip supplier', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $180 Call + Sell 1x $200 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $160 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'MRVL', 'name': 'Marvell Technology', 'relevance_score': 78, 'reason': 'Data center AI chips', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $70 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'AI chip sector led by NVDA, with TSM as key supply chain player. Core allocation in NVDA+TSM recommended.'
        }
    },
    'glp1': {
        'zh': {
            'narrative': {'name': '减肥药GLP-1', 'type': 'theme', 'thesis': 'GLP-1类药物是肥胖治疗的革命性突破，市场规模将达千亿美元。', 'risk_factors': ['竞争加剧', '产能瓶颈', '保险覆盖不确定性']},
            'stocks': [
                {'symbol': 'LLY', 'name': 'Eli Lilly', 'relevance_score': 98, 'reason': 'Mounjaro/Zepbound领先者', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$750 Call + 卖出1张$850 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$700 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'NVO', 'name': 'Novo Nordisk', 'relevance_score': 95, 'reason': 'Ozempic/Wegovy开创者', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$120 Call + 卖出1张$140 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$110 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'VKTX', 'name': 'Viking Therapeutics', 'relevance_score': 80, 'reason': '口服GLP-1研发', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$50 Call (Delta 0.65)', 'leverage': '4x', 'theta_cost': '高'}}},
                {'symbol': 'AMGN', 'name': 'Amgen Inc', 'relevance_score': 72, 'reason': 'MariTide长效GLP-1', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$280 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'PFE', 'name': 'Pfizer Inc', 'relevance_score': 65, 'reason': '口服GLP-1研发中', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$28 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}}
            ],
            'summary': 'GLP-1赛道双寡头格局（LLY+NVO）。建议核心配置LLY。'
        },
        'en': {
            'narrative': {'name': 'GLP-1 Weight Loss', 'type': 'theme', 'thesis': 'GLP-1 drugs are a revolutionary breakthrough in obesity treatment, market to reach $100B+.', 'risk_factors': ['Intensifying competition', 'Capacity bottleneck', 'Insurance coverage uncertainty']},
            'stocks': [
                {'symbol': 'LLY', 'name': 'Eli Lilly', 'relevance_score': 98, 'reason': 'Mounjaro/Zepbound leader', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $750 Call + Sell 1x $850 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $700 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'NVO', 'name': 'Novo Nordisk', 'relevance_score': 95, 'reason': 'Ozempic/Wegovy pioneer', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $120 Call + Sell 1x $140 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $110 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'VKTX', 'name': 'Viking Therapeutics', 'relevance_score': 80, 'reason': 'Oral GLP-1 development', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $50 Call (Delta 0.65)', 'leverage': '4x', 'theta_cost': 'High'}}},
                {'symbol': 'AMGN', 'name': 'Amgen Inc', 'relevance_score': 72, 'reason': 'MariTide long-acting GLP-1', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $280 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'PFE', 'name': 'Pfizer Inc', 'relevance_score': 65, 'reason': 'Oral GLP-1 in development', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $28 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'GLP-1 duopoly (LLY+NVO). Core allocation in LLY recommended.'
        }
    },
    'quantum': {
        'zh': {
            'narrative': {'name': '量子计算', 'type': 'theme', 'thesis': '量子计算是下一代计算革命，有望解决传统计算机无法处理的问题。', 'risk_factors': ['技术不成熟', '商业化路径不清晰', '高研发投入']},
            'stocks': [
                {'symbol': 'IONQ', 'name': 'IonQ Inc', 'relevance_score': 92, 'reason': '离子阱量子计算领先者', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$30 Call (Delta 0.60)', 'leverage': '4x', 'theta_cost': '高'}}},
                {'symbol': 'RGTI', 'name': 'Rigetti Computing', 'relevance_score': 85, 'reason': '超导量子计算公司', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$12 Call (Delta 0.55)', 'leverage': '5x', 'theta_cost': '高'}}},
                {'symbol': 'QBTS', 'name': 'D-Wave Quantum', 'relevance_score': 80, 'reason': '量子退火技术领先者', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$6 Call (Delta 0.55)', 'leverage': '5x', 'theta_cost': '高'}}},
                {'symbol': 'IBM', 'name': 'IBM', 'relevance_score': 75, 'reason': '量子计算研发巨头', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$200 Call + 卖出1张$220 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$180 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'relevance_score': 72, 'reason': 'Willow量子芯片', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$180 Call + 卖出1张$200 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': '低'}}}
            ],
            'summary': '量子计算处于早期阶段。建议小仓位投机IONQ，稳健配置IBM。'
        },
        'en': {
            'narrative': {'name': 'Quantum Computing', 'type': 'theme', 'thesis': 'Quantum computing is the next computing revolution, solving problems impossible for classical computers.', 'risk_factors': ['Immature technology', 'Unclear commercialization path', 'High R&D investment']},
            'stocks': [
                {'symbol': 'IONQ', 'name': 'IonQ Inc', 'relevance_score': 92, 'reason': 'Trapped-ion quantum computing leader', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $30 Call (Delta 0.60)', 'leverage': '4x', 'theta_cost': 'High'}}},
                {'symbol': 'RGTI', 'name': 'Rigetti Computing', 'relevance_score': 85, 'reason': 'Superconducting quantum computing', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $12 Call (Delta 0.55)', 'leverage': '5x', 'theta_cost': 'High'}}},
                {'symbol': 'QBTS', 'name': 'D-Wave Quantum', 'relevance_score': 80, 'reason': 'Quantum annealing leader', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $6 Call (Delta 0.55)', 'leverage': '5x', 'theta_cost': 'High'}}},
                {'symbol': 'IBM', 'name': 'IBM', 'relevance_score': 75, 'reason': 'Quantum computing R&D giant', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $200 Call + Sell 1x $220 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $180 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'relevance_score': 72, 'reason': 'Willow quantum chip', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $180 Call + Sell 1x $200 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Quantum computing in early stage. Small speculative position in IONQ, conservative allocation in IBM.'
        }
    },
    'robotics': {
        'zh': {
            'narrative': {'name': '机器人', 'type': 'theme', 'thesis': '人形机器人和工业自动化是AI落地的重要方向。', 'risk_factors': ['技术成熟度', '成本下降速度', '就业替代争议']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 90, 'reason': 'Optimus人形机器人研发', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$250 Call + 卖出1张$300 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'ISRG', 'name': 'Intuitive Surgical', 'relevance_score': 88, 'reason': '手术机器人绝对龙头', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$500 Call + 卖出1张$550 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$450 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'ABB', 'name': 'ABB Ltd', 'relevance_score': 82, 'reason': '工业机器人四大家族之一', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$50 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'FANUY', 'name': 'Fanuc Corp', 'relevance_score': 80, 'reason': '日本工业机器人龙头', 'position_change': '', 'options_strategy': {}},
                {'symbol': 'ROK', 'name': 'Rockwell Automation', 'relevance_score': 75, 'reason': '工业自动化软件', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$280 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': '低'}}}
            ],
            'summary': '机器人赛道分化明显。建议核心ISRG+投机TSLA。'
        },
        'en': {
            'narrative': {'name': 'Robotics', 'type': 'theme', 'thesis': 'Humanoid robots and industrial automation are key AI implementation areas.', 'risk_factors': ['Technology maturity', 'Cost reduction pace', 'Job displacement concerns']},
            'stocks': [
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'relevance_score': 90, 'reason': 'Optimus humanoid robot development', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $250 Call + Sell 1x $300 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $200 Call (Delta 0.85)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'ISRG', 'name': 'Intuitive Surgical', 'relevance_score': 88, 'reason': 'Surgical robotics leader', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $500 Call + Sell 1x $550 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $450 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'ABB', 'name': 'ABB Ltd', 'relevance_score': 82, 'reason': 'Top 4 industrial robotics maker', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $50 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'FANUY', 'name': 'Fanuc Corp', 'relevance_score': 80, 'reason': 'Japanese industrial robotics leader', 'position_change': '', 'options_strategy': {}},
                {'symbol': 'ROK', 'name': 'Rockwell Automation', 'relevance_score': 75, 'reason': 'Industrial automation software', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $280 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Robotics sector differentiated. Core ISRG + speculative TSLA recommended.'
        }
    },
    'ev_battery': {
        'zh': {
            'narrative': {'name': '电池与储能', 'type': 'theme', 'thesis': '电动车渗透率提升和储能需求爆发，锂电池产业链持续受益。', 'risk_factors': ['锂价波动', '产能过剩', '技术路线变化']},
            'stocks': [
                {'symbol': 'CATL', 'name': 'CATL', 'relevance_score': 95, 'reason': '全球动力电池龙头', 'position_change': '', 'options_strategy': {}},
                {'symbol': 'ALB', 'name': 'Albemarle Corp', 'relevance_score': 88, 'reason': '全球锂矿龙头', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$100 Call + 卖出1张$120 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$90 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'QS', 'name': 'QuantumScape', 'relevance_score': 75, 'reason': '固态电池技术领先者', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$6 Call (Delta 0.60)', 'leverage': '4x', 'theta_cost': '高'}}},
                {'symbol': 'ENPH', 'name': 'Enphase Energy', 'relevance_score': 78, 'reason': '储能逆变器龙头', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$80 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': '中'}}},
                {'symbol': 'BYDDY', 'name': 'BYD Company', 'relevance_score': 85, 'reason': '中国新能源车+电池龙头', 'position_change': '', 'options_strategy': {}}
            ],
            'summary': '电池产业链建议分散配置各环节。'
        },
        'en': {
            'narrative': {'name': 'EV Battery', 'type': 'theme', 'thesis': 'Rising EV penetration and energy storage demand benefit the lithium battery supply chain.', 'risk_factors': ['Lithium price volatility', 'Overcapacity', 'Technology route changes']},
            'stocks': [
                {'symbol': 'CATL', 'name': 'CATL', 'relevance_score': 95, 'reason': 'Global EV battery leader', 'position_change': '', 'options_strategy': {}},
                {'symbol': 'ALB', 'name': 'Albemarle Corp', 'relevance_score': 88, 'reason': 'Global lithium mining leader', 'position_change': '', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $100 Call + Sell 1x $120 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $90 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'QS', 'name': 'QuantumScape', 'relevance_score': 75, 'reason': 'Solid-state battery leader', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $6 Call (Delta 0.60)', 'leverage': '4x', 'theta_cost': 'High'}}},
                {'symbol': 'ENPH', 'name': 'Enphase Energy', 'relevance_score': 78, 'reason': 'Energy storage inverter leader', 'position_change': '', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $80 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': 'Medium'}}},
                {'symbol': 'BYDDY', 'name': 'BYD Company', 'relevance_score': 85, 'reason': 'China NEV + battery leader', 'position_change': '', 'options_strategy': {}}
            ],
            'summary': 'Diversified allocation across battery supply chain recommended.'
        }
    },
    'dalio': {
        'zh': {
            'narrative': {'name': '达利欧桥水', 'type': 'institution', 'thesis': '全天候策略配置，追求风险平价。', 'risk_factors': ['策略拥挤', '相关性风险', '杠杆风险']},
            'stocks': [
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'relevance_score': 92, 'reason': '桥水核心持仓', 'position_change': '持平', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$550 Call + 卖出1张$580 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$520 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'VWO', 'name': 'Vanguard FTSE EM ETF', 'relevance_score': 85, 'reason': '新兴市场配置', 'position_change': '增持', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$42 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'TLT', 'name': 'iShares 20+ Year Treasury', 'relevance_score': 88, 'reason': '长期国债配置', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$90 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'GLD', 'name': 'SPDR Gold Trust', 'relevance_score': 82, 'reason': '黄金配置', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$220 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'PG', 'name': 'Procter & Gamble', 'relevance_score': 78, 'reason': '消费品核心持仓', 'position_change': '持平', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$160 Call + 卖出1张$175 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$150 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': '低'}}}
            ],
            'summary': '桥水全天候策略强调资产配置分散化。'
        },
        'en': {
            'narrative': {'name': 'Ray Dalio', 'type': 'institution', 'thesis': 'All Weather strategy allocation, pursuing risk parity.', 'risk_factors': ['Strategy crowding', 'Correlation risk', 'Leverage risk']},
            'stocks': [
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'relevance_score': 92, 'reason': 'Bridgewater core holding', 'position_change': 'Hold', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $550 Call + Sell 1x $580 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $520 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'VWO', 'name': 'Vanguard FTSE EM ETF', 'relevance_score': 85, 'reason': 'Emerging markets allocation', 'position_change': 'Added', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $42 Call (Delta 0.75)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'TLT', 'name': 'iShares 20+ Year Treasury', 'relevance_score': 88, 'reason': 'Long-term treasury allocation', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $90 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'GLD', 'name': 'SPDR Gold Trust', 'relevance_score': 82, 'reason': 'Gold allocation', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $220 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'PG', 'name': 'Procter & Gamble', 'relevance_score': 78, 'reason': 'Consumer staples core holding', 'position_change': 'Hold', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $160 Call + Sell 1x $175 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $150 Call (Delta 0.80)', 'leverage': '2x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Bridgewater All Weather emphasizes diversified asset allocation.'
        }
    },
    'burry': {
        'zh': {
            'narrative': {'name': '大空头Burry', 'type': 'institution', 'thesis': '逆向投资，寻找被市场严重低估的机会。', 'risk_factors': ['时机风险', '逆市持仓压力', '换手频繁']},
            'stocks': [
                {'symbol': 'BABA', 'name': 'Alibaba Group', 'relevance_score': 88, 'reason': 'Scion最新重仓中概股', 'position_change': '新建仓', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$90 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': '中'}}},
                {'symbol': 'JD', 'name': 'JD.com Inc', 'relevance_score': 82, 'reason': '中概电商', 'position_change': '新建仓', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$35 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': '中'}}},
                {'symbol': 'GOOG', 'name': 'Alphabet Inc', 'relevance_score': 75, 'reason': '科技巨头', 'position_change': '减持', 'options_strategy': {'zebra': {'available': True, 'description': '买入2张$180 Call + 卖出1张$200 Call', 'leverage': '2x', 'theta_cost': '极低'}, 'leaps': {'available': True, 'description': '买入2026.01到期$170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': '低'}}},
                {'symbol': 'CVS', 'name': 'CVS Health', 'relevance_score': 72, 'reason': '医疗零售', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$55 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': '低'}}},
                {'symbol': 'ORLY', 'name': "O'Reilly Automotive", 'relevance_score': 70, 'reason': '汽车零部件零售', 'position_change': '持平', 'options_strategy': {'leaps': {'available': True, 'description': '买入2026.01到期$1100 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': '低'}}}
            ],
            'summary': 'Burry最新持仓转向中概股。建议小仓位参与。'
        },
        'en': {
            'narrative': {'name': 'Michael Burry', 'type': 'institution', 'thesis': 'Contrarian investing, finding severely undervalued opportunities.', 'risk_factors': ['Timing risk', 'Contrarian position pressure', 'Frequent turnover']},
            'stocks': [
                {'symbol': 'BABA', 'name': 'Alibaba Group', 'relevance_score': 88, 'reason': 'Scion\'s latest Chinese stock position', 'position_change': 'New', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $90 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': 'Medium'}}},
                {'symbol': 'JD', 'name': 'JD.com Inc', 'relevance_score': 82, 'reason': 'Chinese e-commerce', 'position_change': 'New', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $35 Call (Delta 0.70)', 'leverage': '3x', 'theta_cost': 'Medium'}}},
                {'symbol': 'GOOG', 'name': 'Alphabet Inc', 'relevance_score': 75, 'reason': 'Tech giant', 'position_change': 'Reduced', 'options_strategy': {'zebra': {'available': True, 'description': 'Buy 2x $180 Call + Sell 1x $200 Call', 'leverage': '2x', 'theta_cost': 'Very Low'}, 'leaps': {'available': True, 'description': 'Buy Jan 2026 $170 Call (Delta 0.85)', 'leverage': '2x', 'theta_cost': 'Low'}}},
                {'symbol': 'CVS', 'name': 'CVS Health', 'relevance_score': 72, 'reason': 'Healthcare retail', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $55 Call (Delta 0.70)', 'leverage': '2.5x', 'theta_cost': 'Low'}}},
                {'symbol': 'ORLY', 'name': "O'Reilly Automotive", 'relevance_score': 70, 'reason': 'Auto parts retail', 'position_change': 'Hold', 'options_strategy': {'leaps': {'available': True, 'description': 'Buy Jan 2026 $1100 Call (Delta 0.75)', 'leverage': '2x', 'theta_cost': 'Low'}}}
            ],
            'summary': 'Burry\'s latest holdings shift to Chinese stocks. Small position recommended.'
        }
    }
}


def analyze_narrative(concept: str, market: str = 'US', narrative_key: str = None, lang: str = 'zh') -> dict:
    """
    分析叙事相关股票并推荐期权策略

    Args:
        concept: 用户输入的概念（自定义搜索时使用）
        market: 市场（US/HK/CN）
        narrative_key: 预设叙事的key（如'musk', 'buffett'）
        lang: 语言（'zh' 或 'en'）

    Returns:
        dict: 包含叙事信息、股票列表和期权策略的结果
    """
    # 确保 lang 是有效值
    if lang not in ('zh', 'en'):
        lang = 'zh'

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # 没有 API key 时使用备用数据
        if narrative_key and narrative_key in FALLBACK_DATA:
            fallback = FALLBACK_DATA[narrative_key].get(lang, FALLBACK_DATA[narrative_key].get('zh', {})).copy()
            fallback['narrative_key'] = narrative_key
            fallback['_source'] = 'fallback'
            return fallback
        return {
            'narrative': {'name': concept or 'Unknown', 'type': 'custom'},
            'error': 'GOOGLE_API_KEY not configured',
            'stocks': []
        }

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    # 获取预设配置（根据语言选择名称和描述）
    preset = PRESET_NARRATIVES.get(narrative_key) if narrative_key else None
    name_key = 'name_en' if lang == 'en' else 'name_zh'
    desc_key = 'description_en' if lang == 'en' else 'description_zh'
    narrative_name = preset[name_key] if preset else concept
    narrative_desc = preset.get(desc_key, '') if preset else ''
    narrative_type = preset.get('type', 'theme') if preset else 'theme'

    # 根据语言选择市场上下文
    if lang == 'en':
        market_context = {
            'US': 'US stocks (NYSE/NASDAQ)',
            'HK': 'Hong Kong stocks',
            'CN': 'A-shares (China)'
        }.get(market, 'US stocks')
    else:
        market_context = {
            'US': '美股（NYSE/NASDAQ）',
            'HK': '港股',
            'CN': 'A股'
        }.get(market, '美股')

    # 根据叙事类型调整 prompt（根据语言）
    if lang == 'en':
        if narrative_type == 'institution':
            type_instruction = """
This is an institutional holdings narrative. Based on the institution's recent public disclosures (13F filings, etc.):
1. List their core holdings (top 5-8 stocks)
2. Note any recent quarter position changes (Added/Reduced)
3. Give higher relevance_score to newly added positions
"""
        elif narrative_type == 'person':
            type_instruction = """
This is a key person narrative. Analyze:
1. Companies founded/led by this person
2. Companies publicly invested or endorsed by this person
3. Supply chain beneficiaries
"""
        else:
            type_instruction = """
This is a theme/concept narrative. Analyze:
1. Core leading companies in this theme
2. Key supply chain companies
3. Beneficiary stocks driven by this theme
"""
    else:
        if narrative_type == 'institution':
            type_instruction = """
这是一个机构持仓跟踪叙事。请基于该机构最近公开披露的持仓信息（13F文件等）：
1. 列出其核心重仓股（前5-8只）
2. 标注最近季度是否有增减仓
3. 对于新增买入的股票给予更高的 relevance_score
"""
        elif narrative_type == 'person':
            type_instruction = """
这是一个关键人物叙事。请分析：
1. 该人物创办/担任高管的公司
2. 该人物公开投资或背书的公司
3. 产业链上下游受益公司
"""
        else:
            type_instruction = """
这是一个主题/概念叙事。请分析：
1. 该主题的核心龙头公司
2. 产业链关键环节公司
3. 受该主题驱动的受益股
"""

    # 根据语言构建 prompt
    if lang == 'en':
        prompt = f"""You are a senior quantitative investment analyst specializing in Narrative Investing and options strategies.

The user wants to analyze investment opportunities related to "{narrative_name}".
{f'Narrative description: {narrative_desc}' if narrative_desc else ''}

{type_instruction}

Please return the results in the following JSON format:

{{
  "narrative": {{
    "name": "{narrative_name}",
    "type": "{narrative_type}",
    "thesis": "Core investment thesis (1-2 sentences)",
    "risk_factors": ["Risk 1", "Risk 2", "Risk 3"]
  }},
  "stocks": [
    {{
      "symbol": "Stock ticker",
      "name": "Company name",
      "relevance_score": 0-100,
      "reason": "Why related to this narrative (1 sentence)",
      "position_change": "Added/Reduced/New/Hold (only for institutional narratives)",
      "options_strategy": {{
        "zebra": {{
          "available": true or false,
          "description": "Buy 2x $XXX Call + Sell 1x $YYY Call",
          "leverage": "2x",
          "theta_cost": "Very Low"
        }},
        "leaps": {{
          "available": true or false,
          "description": "Buy YYYY.MM expiry $XXX Call (Delta 0.80+)",
          "leverage": "2-3x",
          "theta_cost": "Low"
        }}
      }}
    }}
  ],
  "summary": "Summary and investment advice (2-3 sentences)"
}}

Requirements:
1. Return 5-8 most relevant {market_context} stocks
2. Sort by relevance_score from high to low
3. Scoring should be objective: core stocks 90+, related 70-90, peripheral 50-70
4. Only recommend options strategies for stocks with market cap >$10B and active options markets
5. Return only JSON, no other text
6. position_change field only for institutional narratives, leave empty string for others
"""
    else:
        prompt = f"""你是一位资深的量化投资分析师，专注于叙事投资（Narrative Investing）和期权策略。

用户想要分析"{narrative_name}"相关的投资机会。
{f'叙事描述：{narrative_desc}' if narrative_desc else ''}

{type_instruction}

请返回以下JSON格式的结果：

{{
  "narrative": {{
    "name": "{narrative_name}",
    "type": "{narrative_type}",
    "thesis": "这个叙事的核心投资逻辑（1-2句话）",
    "risk_factors": ["风险1", "风险2", "风险3"]
  }},
  "stocks": [
    {{
      "symbol": "股票代码",
      "name": "公司名称",
      "relevance_score": 0-100,
      "reason": "为什么与该叙事相关（1句话）",
      "position_change": "增持/减持/新建仓/持平（仅机构叙事填写）",
      "options_strategy": {{
        "zebra": {{
          "available": true或false,
          "description": "买入2张$XXX Call + 卖出1张$YYY Call",
          "leverage": "2x",
          "theta_cost": "极低"
        }},
        "leaps": {{
          "available": true或false,
          "description": "买入YYYY.MM到期$XXX Call (Delta 0.80+)",
          "leverage": "2-3x",
          "theta_cost": "低"
        }}
      }}
    }}
  ],
  "summary": "总结和投资建议（2-3句话）"
}}

要求：
1. 返回5-8只最相关的{market_context}股票
2. 按relevance_score从高到低排序
3. 评分要客观区分：核心股90+，相关股70-90，边缘股50-70
4. 期权策略只为市值>100亿美元且有活跃期权市场的股票推荐
5. 只返回JSON，不要其他文字
6. position_change 字段仅在机构叙事时填写，其他叙事留空字符串
"""

    try:
        response = model.generate_content(prompt)
        text = response.text

        # 提取JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json.loads(json_match.group())
            result['narrative_key'] = narrative_key
            return result
        else:
            # 如果解析失败，尝试使用备用数据
            if narrative_key and narrative_key in FALLBACK_DATA:
                fallback = FALLBACK_DATA[narrative_key].get(lang, FALLBACK_DATA[narrative_key].get('zh', {})).copy()
                fallback['narrative_key'] = narrative_key
                fallback['_source'] = 'fallback'
                return fallback
            return {
                'narrative': {'name': narrative_name, 'type': narrative_type},
                'error': 'Failed to parse AI response',
                'stocks': []
            }
    except Exception as e:
        # API 调用失败时使用备用数据
        error_str = str(e)
        if narrative_key and narrative_key in FALLBACK_DATA:
            fallback = FALLBACK_DATA[narrative_key].get(lang, FALLBACK_DATA[narrative_key].get('zh', {})).copy()
            fallback['narrative_key'] = narrative_key
            fallback['_source'] = 'fallback'
            # 如果是地理位置限制，不返回错误信息
            if 'location is not supported' not in error_str:
                fallback['_warning'] = f'Using cached data: {error_str}'
            return fallback

        # 对于自定义概念，没有备用数据
        return {
            'narrative': {'name': narrative_name, 'type': narrative_type},
            'error': error_str,
            'stocks': []
        }
