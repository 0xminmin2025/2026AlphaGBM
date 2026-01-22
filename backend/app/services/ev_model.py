"""
EV（期望值）模型 - Expected Value Model

基于概率论和统计学的投资决策模型，计算每笔交易的数学期望值。

核心公式：
EV = (上涨概率 × 上涨幅度) + (下跌概率 × 下跌幅度)

多时间视界加权：
综合EV = 一周EV×50% + 一月EV×30% + 三月EV×20%

参考 WEIM 平台的实现逻辑，结合：
- 历史相似度匹配（概率估算）
- 隐含波动率/历史波动率（幅度估算）
- 技术面支撑/阻力位
- 基本面催化剂
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_historical_volatility(hist_prices, period=30):
    """
    计算历史波动率（年化）
    
    参数:
        hist_prices: 历史价格列表
        period: 计算周期（天数）
    
    返回:
        年化波动率（小数形式，如 0.25 表示 25%）
    """
    try:
        if not hist_prices or len(hist_prices) < 2:
            return 0.30  # 默认波动率 30%
        
        # 只取最近的period天数据
        recent_prices = hist_prices[-period:] if len(hist_prices) > period else hist_prices
        
        # 计算每日收益率
        prices = np.array(recent_prices)
        returns = np.diff(prices) / prices[:-1]
        
        # 计算标准差（日波动率）
        if len(returns) < 2:
            return 0.30
        
        daily_vol = np.std(returns)
        
        # 年化（假设一年252个交易日）
        annual_vol = daily_vol * np.sqrt(252)
        
        return float(annual_vol)
    except Exception as e:
        logger.error(f"计算历史波动率失败: {e}")
        return 0.30


def calculate_probability_from_features(data, risk_result, style):
    """
    基于特征工程计算上涨/下跌概率
    
    使用历史相似度匹配的简化版本：
    - 考虑当前价格位置（52周高低点）
    - 考虑技术面（均线关系）
    - 考虑基本面（PE、PEG、增长率）
    - 考虑风险评分
    - 考虑市场情绪
    
    参数:
        data: 市场数据
        risk_result: 风险分析结果
        style: 投资风格
    
    返回:
        (上涨概率, 下跌概率) - 元组，概率之和为1
    """
    try:
        # 基础概率（中性）
        base_prob_up = 0.50
        
        # === 特征1: 价格位置 ===
        price_position = 0.5
        if data.get('week52_high') and data.get('week52_low'):
            if data['week52_high'] > data['week52_low']:
                price_position = (data['price'] - data['week52_low']) / (data['week52_high'] - data['week52_low'])
        
        # 价格越低，上涨概率越高（均值回归逻辑）
        if price_position < 0.3:
            base_prob_up += 0.10  # 低位反弹概率高
        elif price_position > 0.8:
            base_prob_up -= 0.10  # 高位回调概率高
        
        # === 特征2: 技术面 ===
        price = data.get('price', 0)
        ma50 = data.get('ma50', 0)
        ma200 = data.get('ma200', 0)
        
        if price > 0 and ma50 > 0 and ma200 > 0:
            # 多头排列：价格 > MA50 > MA200
            if price > ma50 > ma200:
                base_prob_up += 0.12
            # 金叉：MA50 刚突破 MA200
            elif ma50 > ma200 and abs(ma50 - ma200) / ma200 < 0.05:
                base_prob_up += 0.08
            # 空头排列：价格 < MA50 < MA200
            elif price < ma50 < ma200:
                base_prob_up -= 0.12
            # 死叉：MA50 刚跌破 MA200
            elif ma50 < ma200 and abs(ma50 - ma200) / ma200 < 0.05:
                base_prob_up -= 0.08
        
        # === 特征3: 基本面质量 ===
        pe = data.get('pe', 0)
        peg = data.get('peg', 0)
        growth = data.get('growth', 0)
        
        # PEG < 1.0 是价值信号
        if peg > 0 and peg < 1.0:
            base_prob_up += 0.08
        elif peg > 2.0:
            base_prob_up -= 0.05
        
        # 高增长
        if growth > 0.20:  # 增长率 > 20%
            base_prob_up += 0.05
        elif growth < 0:  # 负增长
            base_prob_up -= 0.08
        
        # === 特征4: 风险评分 ===
        risk_score = risk_result.get('score', 0)
        
        # 风险越高，上涨概率越低
        if risk_score >= 4:
            base_prob_up -= 0.15
        elif risk_score >= 3:
            base_prob_up -= 0.10
        elif risk_score >= 2:
            base_prob_up -= 0.05
        elif risk_score <= 1:
            base_prob_up += 0.05
        
        # === 特征5: 市场情绪 ===
        market_sentiment = data.get('market_sentiment', 5.0)
        
        # 处理市场情绪可能是 dict 或 float 的情况
        if isinstance(market_sentiment, dict):
            sentiment_score = market_sentiment.get('综合情绪分数', 5.0)
        else:
            sentiment_score = market_sentiment if isinstance(market_sentiment, (int, float)) else 5.0
        
        # 情绪分数 0-10，5为中性
        sentiment_adjustment = (sentiment_score - 5.0) * 0.02  # 每差1分，调整2%
        base_prob_up += sentiment_adjustment
        
        # === 特征6: 投资风格调整 ===
        if style == 'momentum':
            # 趋势投资：如果已经在上涨，概率更高
            if price > ma50:
                base_prob_up += 0.05
        elif style == 'value':
            # 价值投资：低估时概率更高
            if pe > 0 and pe < 15:
                base_prob_up += 0.05
        
        # === 约束概率范围 ===
        prob_up = max(0.20, min(0.80, base_prob_up))  # 限制在 20%-80% 之间
        prob_down = 1.0 - prob_up
        
        logger.info(f"概率计算: 上涨={prob_up:.2%}, 下跌={prob_down:.2%}")
        
        return prob_up, prob_down
        
    except Exception as e:
        logger.error(f"计算概率失败: {e}")
        # 返回中性概率
        return 0.50, 0.50


def calculate_expected_move(data, time_horizon_days):
    """
    计算预期涨跌幅度
    
    优先使用期权隐含波动率（如果有），否则使用历史波动率
    
    参数:
        data: 市场数据
        time_horizon_days: 时间视界（天数）
    
    返回:
        (预期上涨幅度, 预期下跌幅度) - 元组，小数形式（如 0.15 表示 15%）
    """
    try:
        current_price = data.get('price', 0)
        if current_price <= 0:
            return 0.10, -0.10  # 默认 ±10%
        
        # 尝试从期权数据获取隐含波动率
        market_sentiment = data.get('market_sentiment', {})
        
        # 处理 market_sentiment 可能是 float 的情况
        if isinstance(market_sentiment, dict):
            options_data = market_sentiment.get('期权市场数据', {})
            implied_vol = options_data.get('implied_volatility') if isinstance(options_data, dict) else None
        else:
            implied_vol = None
        
        # 如果没有期权数据，使用历史波动率
        if not implied_vol:
            hist_prices = data.get('history_prices', [])
            implied_vol = calculate_historical_volatility(hist_prices)
        
        # 计算该时间视界下的预期波动
        # 波动率通常以年化表示，需要调整到指定时间周期
        # 公式：预期波动 = 年化波动率 × sqrt(天数/252)
        time_factor = np.sqrt(time_horizon_days / 252.0)
        expected_move_pct = implied_vol * time_factor
        
        # 考虑技术面的支撑和阻力
        week52_high = data.get('week52_high', 0)
        week52_low = data.get('week52_low', 0)
        
        # 上行空间（到52周高点）
        upside_to_high = 0
        if week52_high > current_price:
            upside_to_high = (week52_high - current_price) / current_price
        
        # 下行空间（到52周低点）
        downside_to_low = 0
        if week52_low > 0 and week52_low < current_price:
            downside_to_low = (week52_low - current_price) / current_price  # 负数
        
        # 上涨幅度：取预期波动和技术面上行空间的较小值（保守估计）
        upside = min(expected_move_pct, upside_to_high) if upside_to_high > 0 else expected_move_pct
        
        # 下跌幅度：取预期波动和技术面下行空间的较大值（保守估计）
        # 注意：downside_to_low是负数，expected_move_pct是正数
        downside = max(-expected_move_pct, downside_to_low) if downside_to_low < 0 else -expected_move_pct
        
        # 确保上涨幅度为正，下跌幅度为负
        upside = max(0.05, upside)  # 至少 5%
        downside = min(-0.05, downside)  # 至少 -5%
        
        logger.info(f"预期波动（{time_horizon_days}天）: 上涨={upside:.2%}, 下跌={downside:.2%}, IV={implied_vol:.2%}")
        
        return upside, downside
        
    except Exception as e:
        logger.error(f"计算预期波动失败: {e}")
        # 默认值
        return 0.10, -0.10


def calculate_ev_single_horizon(data, risk_result, style, time_horizon_days):
    """
    计算单个时间视界的 EV
    
    参数:
        data: 市场数据
        risk_result: 风险分析结果
        style: 投资风格
        time_horizon_days: 时间视界（天数）
    
    返回:
        EV 字典，包含详细信息
    """
    try:
        # 1. 计算概率
        prob_up, prob_down = calculate_probability_from_features(data, risk_result, style)
        
        # 2. 计算涨跌幅度
        upside, downside = calculate_expected_move(data, time_horizon_days)
        
        # 3. 计算 EV
        ev = (prob_up * upside) + (prob_down * downside)
        
        # 4. 计算盈亏比（Risk-Reward Ratio）
        risk_reward_ratio = abs(upside / downside) if downside != 0 else 0
        
        # 5. 计算夏普比率（简化版）
        # 夏普比率 = (EV - 无风险利率) / 波动率
        # 这里假设无风险利率为 0，波动率用上下幅度的平均绝对值
        volatility = (abs(upside) + abs(downside)) / 2
        sharpe_ratio = ev / volatility if volatility > 0 else 0
        
        return {
            'time_horizon_days': time_horizon_days,
            'probability_up': prob_up,
            'probability_down': prob_down,
            'upside_pct': upside,
            'downside_pct': downside,
            'ev': ev,
            'ev_pct': ev * 100,  # 百分比形式
            'risk_reward_ratio': risk_reward_ratio,
            'sharpe_ratio': sharpe_ratio
        }
        
    except Exception as e:
        logger.error(f"计算 EV 失败（{time_horizon_days}天）: {e}")
        return {
            'time_horizon_days': time_horizon_days,
            'probability_up': 0.5,
            'probability_down': 0.5,
            'upside_pct': 0.10,
            'downside_pct': -0.10,
            'ev': 0.0,
            'ev_pct': 0.0,
            'risk_reward_ratio': 1.0,
            'sharpe_ratio': 0.0,
            'error': str(e)
        }


def calculate_ev_model(data, risk_result, style):
    """
    计算完整的 EV 模型，包含多时间视界
    
    参数:
        data: 市场数据
        risk_result: 风险分析结果
        style: 投资风格
    
    返回:
        EV 模型字典，包含：
        - ev_1week: 1周 EV
        - ev_1month: 1月 EV
        - ev_3months: 3月 EV
        - ev_weighted: 加权综合 EV
        - recommendation: 基于 EV 的推荐
    """
    try:
        logger.info(f"开始计算 EV 模型，股票={data.get('symbol')}, 风格={style}")
        
        # 计算三个时间视界的 EV
        ev_1week = calculate_ev_single_horizon(data, risk_result, style, 7)
        ev_1month = calculate_ev_single_horizon(data, risk_result, style, 30)
        ev_3months = calculate_ev_single_horizon(data, risk_result, style, 90)
        
        # 加权计算综合 EV（参考 WEIM 平台的权重）
        # 短期权重更高，因为预测准确性随时间递减
        weight_1week = 0.50
        weight_1month = 0.30
        weight_3months = 0.20
        
        ev_weighted = (
            ev_1week['ev'] * weight_1week +
            ev_1month['ev'] * weight_1month +
            ev_3months['ev'] * weight_3months
        )
        
        # 基于 EV 生成推荐（传入data以便检查目标价格）
        recommendation = generate_ev_recommendation(ev_weighted, ev_1week, ev_1month, ev_3months, risk_result, data)
        
        # 计算 EV 评级（0-10 分）
        ev_score = calculate_ev_score(ev_weighted, risk_result)

        # 计算 EV 信心度评分
        confidence_result = calculate_ev_confidence(
            ev_1week['ev'],
            ev_1month['ev'],
            ev_3months['ev'],
            data
        )

        result = {
            'ev_1week': ev_1week,
            'ev_1month': ev_1month,
            'ev_3months': ev_3months,
            'ev_weighted': ev_weighted,
            'ev_weighted_pct': ev_weighted * 100,
            'weights': {
                '1week': weight_1week,
                '1month': weight_1month,
                '3months': weight_3months
            },
            'recommendation': recommendation,
            'ev_score': ev_score,
            'confidence': confidence_result
        }

        logger.info(f"EV 模型计算完成: 加权EV={ev_weighted:.2%}, 评分={ev_score:.1f}/10, 信心度={confidence_result['level']}")
        
        return result
        
    except Exception as e:
        logger.error(f"计算 EV 模型失败: {e}")
        return {
            'error': str(e),
            'ev_weighted': 0.0,
            'ev_score': 5.0,
            'recommendation': {
                'action': 'HOLD',
                'reason': 'EV 模型计算失败，建议观望',
                'confidence': 'low'
            }
        }


def generate_ev_recommendation(ev_weighted, ev_1week, ev_1month, ev_3months, risk_result, data=None):
    """
    基于 EV 生成交易推荐
    
    参数:
        ev_weighted: 加权综合 EV
        ev_1week, ev_1month, ev_3months: 各时间视界的 EV
        risk_result: 风险分析结果
        data: 市场数据（可选，用于检查目标价格）
    
    返回:
        推荐字典
    """
    try:
        # 基础推荐逻辑（使用更自然的表达，不提"期望值"、"EV"，不包含操作建议）
        if ev_weighted > 0.08:  # EV > 8%
            action = 'STRONG_BUY'
            reason = '短期上涨概率较高，技术面和情绪面较为积极'
            confidence = 'high'
        elif ev_weighted > 0.03:  # EV > 3%
            action = 'BUY'
            reason = '短期向上概率略高'
            confidence = 'medium'
        elif ev_weighted > -0.03:  # -3% < EV < 3%
            action = 'HOLD'
            reason = '短期方向不明确'
            confidence = 'medium'
        elif ev_weighted > -0.08:  # -8% < EV < -3%
            action = 'AVOID'
            reason = '短期下行风险偏高'
            confidence = 'medium'
        else:  # EV < -8%
            action = 'STRONG_AVOID'
            reason = '短期下行压力较大，技术面和情绪面偏弱'
            confidence = 'high'
        
        # 价格调整：如果目标价低于当前价，不应该建议增持
        if data:
            current_price = data.get('price', 0)
            target_price = data.get('target_price', 0)
            if current_price > 0 and target_price > 0 and target_price < current_price:
                # 目标价低于当前价，不应该建议增持
                if action in ['STRONG_BUY', 'BUY']:
                    action = 'HOLD'
                    reason = f'目标价({target_price:.2f})低于当前价({current_price:.2f})，不建议增持'
                    confidence = 'medium'
                    logger.info(f"目标价低于当前价，将推荐从{action}调整为HOLD")
        
        # 风险调整：如果风险过高，降级推荐
        risk_score = risk_result.get('score', 0)
        if risk_score >= 4 and action in ['STRONG_BUY', 'BUY']:
            action = 'HOLD'
            reason = f'风险评分偏高（{risk_score:.1f}/10）'
            confidence = 'low'
        
        # 时间一致性检查：如果三个时间视界方向不一致，降低信心度
        ev_signs = [
            1 if ev_1week['ev'] > 0 else -1,
            1 if ev_1month['ev'] > 0 else -1,
            1 if ev_3months['ev'] > 0 else -1
        ]
        if len(set(ev_signs)) > 1:  # 方向不一致
            confidence = 'low'
            reason = '短期和中期走势预期存在分歧'
        
        return {
            'action': action,
            'reason': reason,
            'confidence': confidence,
            'ev_threshold_used': '±3% / ±8%'
        }
        
    except Exception as e:
        logger.error(f"生成 EV 推荐失败: {e}")
        return {
            'action': 'HOLD',
            'reason': '信号不明确',
            'confidence': 'low'
        }


def calculate_ev_score(ev_weighted, risk_result):
    """
    将 EV 转换为 0-10 分的评分
    
    参数:
        ev_weighted: 加权综合 EV
        risk_result: 风险分析结果
    
    返回:
        0-10 的评分
    """
    try:
        # 基础分数：将 EV 从 [-20%, +20%] 映射到 [0, 10]
        # EV = 0% → 5分（中性）
        # EV = +10% → 7.5分
        # EV = +20% → 10分
        # EV = -10% → 2.5分
        # EV = -20% → 0分
        
        base_score = 5.0 + (ev_weighted * 25)  # EV每增加1%，得分+0.25
        base_score = max(0, min(10, base_score))  # 限制在 0-10
        
        # 风险调整：风险越高，扣分越多
        risk_score = risk_result.get('score', 0)
        risk_penalty = risk_score * 0.3  # 风险每增加1分，扣0.3分
        
        final_score = max(0, min(10, base_score - risk_penalty))
        
        return round(final_score, 1)
        
    except Exception as e:
        logger.error(f"计算 EV 评分失败: {e}")
        return 5.0  # 默认中性评分


def calculate_ev_confidence(ev_1week, ev_1month, ev_3months, data=None):
    """
    计算 EV 模型的信心度

    基于以下因素评估预测的可信度：
    1. 时间一致性：三个时间维度的EV方向是否一致
    2. 信号强度：EV绝对值是否足够大（弱信号信心低）
    3. 数据质量：是否有足够的历史数据支撑
    4. 波动率稳定性：近期波动率是否稳定

    参数:
        ev_1week: 1周EV值
        ev_1month: 1月EV值
        ev_3months: 3月EV值
        data: 市场数据（可选）

    返回:
        dict: {
            'level': 'HIGH'/'MEDIUM'/'LOW',
            'score': 0-100,
            'factors': [...],
            'description': '...'
        }
    """
    try:
        score = 50  # 基础分
        factors = []

        # 定义方向阈值（绝对值小于2%视为中性）
        neutral_threshold = 0.02

        def get_direction(ev):
            if ev > neutral_threshold:
                return 'up'
            elif ev < -neutral_threshold:
                return 'down'
            return 'neutral'

        dir_1week = get_direction(ev_1week)
        dir_1month = get_direction(ev_1month)
        dir_3months = get_direction(ev_3months)

        directions = [dir_1week, dir_1month, dir_3months]
        non_neutral = [d for d in directions if d != 'neutral']

        # 1. 时间一致性检查（权重40%）
        if len(non_neutral) == 0:
            # 全部中性
            score += 0
            factors.append('方向不明确（全部中性）')
        elif len(set(non_neutral)) == 1:
            # 非中性的方向完全一致
            score += 40
            factors.append(f'三个时间维度方向一致({non_neutral[0]})')
        elif len(non_neutral) == 2 and len(set(non_neutral)) == 1:
            # 两个有方向且一致
            score += 25
            factors.append('两个时间维度方向一致')
        else:
            # 方向存在分歧
            score -= 15
            factors.append('时间维度存在方向分歧')

        # 2. 信号强度（权重30%）
        avg_abs_ev = (abs(ev_1week) + abs(ev_1month) + abs(ev_3months)) / 3

        if avg_abs_ev > 0.10:  # 平均EV > 10%
            score += 30
            factors.append(f'信号强度高(平均EV={avg_abs_ev:.1%})')
        elif avg_abs_ev > 0.05:  # 平均EV 5-10%
            score += 20
            factors.append(f'信号强度中等(平均EV={avg_abs_ev:.1%})')
        elif avg_abs_ev > 0.02:  # 平均EV 2-5%
            score += 10
            factors.append(f'信号强度偏弱(平均EV={avg_abs_ev:.1%})')
        else:
            score -= 10
            factors.append(f'信号强度很弱(平均EV={avg_abs_ev:.1%})')

        # 3. 数据质量检查（权重20%）
        if data:
            hist_prices = data.get('history_prices', [])
            if len(hist_prices) >= 200:
                score += 20
                factors.append('历史数据充足(>200天)')
            elif len(hist_prices) >= 60:
                score += 10
                factors.append('历史数据中等(60-200天)')
            elif len(hist_prices) >= 20:
                score += 5
                factors.append('历史数据有限(20-60天)')
            else:
                score -= 10
                factors.append('历史数据不足(<20天)')

            # 4. 波动率稳定性（权重10%）
            # 近期波动率与历史波动率的比较
            if hist_prices and len(hist_prices) >= 60:
                recent_prices = hist_prices[-20:]
                older_prices = hist_prices[-60:-20]

                if len(recent_prices) >= 2 and len(older_prices) >= 2:
                    recent_returns = np.diff(recent_prices) / np.array(recent_prices[:-1])
                    older_returns = np.diff(older_prices) / np.array(older_prices[:-1])

                    recent_vol = np.std(recent_returns) if len(recent_returns) > 1 else 0
                    older_vol = np.std(older_returns) if len(older_returns) > 1 else 0

                    if older_vol > 0:
                        vol_ratio = recent_vol / older_vol
                        if 0.7 <= vol_ratio <= 1.3:
                            score += 10
                            factors.append('波动率稳定')
                        elif vol_ratio > 1.5:
                            score -= 5
                            factors.append('近期波动率显著上升')
                        elif vol_ratio < 0.5:
                            score += 5
                            factors.append('近期波动率下降')
        else:
            factors.append('无市场数据，无法评估数据质量')

        # 限制分数范围
        score = max(0, min(100, score))

        # 确定信心度等级
        if score >= 70:
            level = 'HIGH'
            description = '模型预测信心度高，三个时间维度方向一致，信号强度充足'
        elif score >= 40:
            level = 'MEDIUM'
            description = '模型预测信心度中等，部分维度存在分歧或信号较弱'
        else:
            level = 'LOW'
            description = '模型预测信心度低，方向不明确或数据不足'

        return {
            'level': level,
            'score': score,
            'factors': factors,
            'description': description,
            'directions': {
                '1week': dir_1week,
                '1month': dir_1month,
                '3months': dir_3months
            }
        }

    except Exception as e:
        logger.error(f"计算 EV 信心度失败: {e}")
        return {
            'level': 'LOW',
            'score': 30,
            'factors': ['计算过程出错'],
            'description': '无法计算信心度'
        }

