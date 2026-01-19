"""
基础股票分析策略
实现不同投资风格的分析逻辑：成长型、价值型、平衡型
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

# 导入配置参数
try:
    from ....constants import (
        GROWTH_DISCOUNT_FACTOR, ATR_MULTIPLIER_BASE, MIN_DAILY_VOLUME_USD,
        FIXED_STOP_LOSS_PCT, PEG_THRESHOLD_BASE,
        MARKET_CONFIG, MARKET_STYLE_WEIGHTS,
        detect_market_from_ticker, get_market_config, get_market_style_weights
    )
except ImportError:
    # 如果constants不存在，使用默认值
    GROWTH_DISCOUNT_FACTOR = 0.6
    ATR_MULTIPLIER_BASE = 2.5
    MIN_DAILY_VOLUME_USD = 5_000_000
    FIXED_STOP_LOSS_PCT = 0.15
    PEG_THRESHOLD_BASE = 1.5
    MARKET_CONFIG = {'US': {}, 'CN': {}, 'HK': {}}
    MARKET_STYLE_WEIGHTS = {'US': {}, 'CN': {}, 'HK': {}}

    def detect_market_from_ticker(ticker): return 'US'
    def get_market_config(market): return {}
    def get_market_style_weights(market): return {}

logger = logging.getLogger(__name__)


class BasicAnalysisStrategy:
    """
    基础分析策略类
    根据不同的投资风格执行股票分析
    """

    def __init__(self):
        """初始化分析策略"""
        self.growth_discount_factor = GROWTH_DISCOUNT_FACTOR
        self.peg_threshold_base = PEG_THRESHOLD_BASE

    def analyze(self, data: Dict[str, Any], style: str, liquidity_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行基础分析

        参数:
            data: 市场数据
            style: 投资风格 ('growth', 'value', 'balanced', 'quality', 'momentum')
            liquidity_info: 流动性信息

        返回:
            分析结果字典
        """
        try:
            logger.info(f"开始基础分析，风格: {style}")

            # 1. 基础数据验证
            if not data or 'info' not in data:
                return {
                    'success': False,
                    'error': '缺少基础市场数据'
                }

            info = data['info']
            ticker = data.get('ticker', '')

            # 2. 识别市场并获取市场配置
            market = detect_market_from_ticker(ticker)
            market_config = get_market_config(market)
            style_weights = get_market_style_weights(market)

            # 3. 公司分类
            company_classification = self.classify_company(data)

            # 4. 风险分析（考虑市场差异）
            risk_result = self.analyze_risk_and_position(style, data, market_config)

            # 5. 根据风格调整分析
            if style == 'growth':
                analysis_result = self._analyze_growth_style(data, risk_result)
            elif style == 'value':
                analysis_result = self._analyze_value_style(data, risk_result)
            elif style == 'quality':
                analysis_result = self._analyze_quality_style(data, risk_result)
            elif style == 'momentum':
                analysis_result = self._analyze_momentum_style(data, risk_result)
            else:  # balanced
                analysis_result = self._analyze_balanced_style(data, risk_result)

            # 6. 应用市场风格权重调整
            if style in style_weights:
                style_multiplier = style_weights.get(style, 1.0)
                if 'score' in analysis_result:
                    analysis_result['score'] = analysis_result['score'] * style_multiplier
                # 更新风格特定的评分
                score_key = f'{style}_score'
                if score_key in analysis_result:
                    analysis_result[score_key] = analysis_result[score_key] * style_multiplier
                analysis_result['market_style_multiplier'] = style_multiplier

            # 7. 整合结果
            result = {
                'success': True,
                'analysis_style': style,
                'market': market,
                'market_name': market_config.get('name', market),
                'company_classification': company_classification,
                'risk_analysis': risk_result,
                'style_specific_analysis': analysis_result,
                'recommendation': self._generate_recommendation(analysis_result, risk_result, style),
                'confidence_score': self._calculate_confidence_score(data, analysis_result)
            }

            logger.info(f"基础分析完成，风格: {style}, 推荐: {result['recommendation']}")
            return result

        except Exception as e:
            logger.error(f"基础分析失败: {e}")
            return {
                'success': False,
                'error': f'分析失败: {str(e)}'
            }

    def classify_company(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        公司分类分析

        参数:
            data: 市场数据

        返回:
            公司分类结果
        """
        try:
            info = data.get('info', {})

            # 基本信息提取
            market_cap = info.get('marketCap', 0)
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            business_summary = info.get('longBusinessSummary', '')

            # 市值分类
            if market_cap >= 200_000_000_000:  # 2000亿美元
                cap_category = 'mega_cap'
                cap_description = '超大盘股'
            elif market_cap >= 10_000_000_000:  # 100亿美元
                cap_category = 'large_cap'
                cap_description = '大盘股'
            elif market_cap >= 2_000_000_000:  # 20亿美元
                cap_category = 'mid_cap'
                cap_description = '中盘股'
            elif market_cap >= 300_000_000:  # 3亿美元
                cap_category = 'small_cap'
                cap_description = '小盘股'
            else:
                cap_category = 'micro_cap'
                cap_description = '微盘股'

            # ETF检测
            is_etf = self._is_etf_or_fund(data)

            # 成长性vs价值性判断
            pe_ratio = info.get('trailingPE', 0)
            peg_ratio = info.get('pegRatio', 0)
            revenue_growth = info.get('revenueGrowth', 0)

            growth_vs_value = 'unknown'
            if pe_ratio and revenue_growth:
                if pe_ratio > 25 and revenue_growth > 0.15:
                    growth_vs_value = 'growth'
                elif pe_ratio < 15 and revenue_growth < 0.10:
                    growth_vs_value = 'value'
                else:
                    growth_vs_value = 'blend'

            result = {
                'market_cap': market_cap,
                'cap_category': cap_category,
                'cap_description': cap_description,
                'sector': sector,
                'industry': industry,
                'is_etf': is_etf,
                'growth_vs_value': growth_vs_value,
                'pe_ratio': pe_ratio,
                'revenue_growth': revenue_growth
            }

            logger.info(f"公司分类完成: {cap_description}, {sector}, {growth_vs_value}")
            return result

        except Exception as e:
            logger.error(f"公司分类失败: {e}")
            return {
                'error': str(e),
                'cap_category': 'unknown',
                'is_etf': False
            }

    def analyze_risk_and_position(self, style: str, data: Dict[str, Any], market_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        风险分析和仓位建议

        参数:
            style: 投资风格
            data: 市场数据

        返回:
            风险分析结果
        """
        try:
            info = data.get('info', {})
            history_prices = data.get('history_prices', [])

            risk_factors = []
            risk_score = 0  # 0-100，越高风险越大

            # 获取市场配置参数
            if market_config is None:
                market_config = {}
            risk_premium = market_config.get('risk_premium', 1.0)
            pe_high_threshold = market_config.get('pe_high_threshold', 40)
            volatility_adjustment = market_config.get('volatility_adjustment', 1.0)

            # 1. 波动率风险
            if len(history_prices) >= 30:
                price_changes = [history_prices[i] / history_prices[i-1] - 1 for i in range(1, len(history_prices))]
                volatility = np.std(price_changes) * np.sqrt(252)  # 年化波动率

                if volatility > 0.5:
                    risk_score += 25
                    risk_factors.append(f'高波动率 ({volatility:.1%})')
                elif volatility > 0.3:
                    risk_score += 15
                    risk_factors.append(f'中等波动率 ({volatility:.1%})')
                else:
                    risk_factors.append(f'低波动率 ({volatility:.1%})')
            else:
                volatility = 0

            # 2. 估值风险 (使用市场特定的PE阈值)
            pe_ratio = info.get('trailingPE', 0)
            if pe_ratio:
                if pe_ratio > pe_high_threshold * 1.5:  # 极高估值
                    risk_score += 20
                    risk_factors.append(f'极高估值 (PE={pe_ratio:.1f})')
                elif pe_ratio > pe_high_threshold:  # 高估值
                    risk_score += 10
                    risk_factors.append(f'高估值 (PE={pe_ratio:.1f})')
                elif pe_ratio < 8:
                    risk_score += 15
                    risk_factors.append(f'异常低估值 (PE={pe_ratio:.1f}，可能存在问题)')

            # 3. 财务风险
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity:
                if debt_to_equity > 200:  # 负债权益比超过200%
                    risk_score += 15
                    risk_factors.append(f'高负债比率 ({debt_to_equity:.0f}%)')
                elif debt_to_equity > 100:
                    risk_score += 8
                    risk_factors.append(f'中等负债比率 ({debt_to_equity:.0f}%)')

            # 4. 市值风险
            market_cap = info.get('marketCap', 0)
            if market_cap < 1_000_000_000:  # 10亿美元以下
                risk_score += 10
                risk_factors.append('小市值风险')

            # 5. 行业风险
            sector = info.get('sector', '')
            high_risk_sectors = ['Technology', 'Biotechnology', 'Energy']
            if sector in high_risk_sectors:
                risk_score += 5
                risk_factors.append(f'高风险行业 ({sector})')

            # 6. 宏观风险评估 + 市场风险溢价调整
            # 应用市场风险溢价系数
            if risk_premium > 1.0:
                market_risk_adjustment = (risk_premium - 1.0) * 20  # 额外风险加成
                risk_score += market_risk_adjustment
                if market_risk_adjustment > 5:
                    risk_factors.append(f'市场风险溢价 (+{market_risk_adjustment:.0f})')

            # 政策风险（A股特有）
            policy_risk_factor = market_config.get('policy_risk_factor', 1.0)
            if policy_risk_factor > 1.0:
                risk_factors.append('政策敏感性较高')

            # 风险等级分类
            if risk_score >= 60:
                risk_level = 'high'
                risk_description = '高风险'
                position_size_pct = 2  # 建议仓位2%
            elif risk_score >= 35:
                risk_level = 'medium'
                risk_description = '中等风险'
                position_size_pct = 3  # 建议仓位3%
            else:
                risk_level = 'low'
                risk_description = '低风险'
                position_size_pct = 5  # 建议仓位5%

            # 根据投资风格调整仓位
            if style == 'growth':
                position_size_pct = min(position_size_pct * 1.2, 8)  # 成长风格可适当增加仓位
            elif style == 'value':
                position_size_pct = min(position_size_pct * 1.1, 6)  # 价值风格稍微增加仓位

            # 风险调整因子（用于目标价格计算）
            risk_adjustment_factor = max(1 - (risk_score / 100) * 0.5, 0.5)  # 最低0.5

            result = {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_description': risk_description,
                'risk_factors': risk_factors,
                'volatility': volatility,
                'position_size_pct': position_size_pct,
                'risk_adjustment_factor': risk_adjustment_factor,
                'max_loss_tolerance': position_size_pct * 0.3  # 最大可接受亏损
            }

            logger.info(f"风险分析完成: {risk_description} (得分: {risk_score}), 建议仓位: {position_size_pct:.1f}%")
            return result

        except Exception as e:
            logger.error(f"风险分析失败: {e}")
            return {
                'risk_score': 50,
                'risk_level': 'medium',
                'risk_description': '中等风险',
                'error': str(e)
            }

    def _is_etf_or_fund(self, data: Dict[str, Any]) -> bool:
        """检测是否为ETF或基金"""
        try:
            info = data.get('info', {})

            # 检查关键指标
            quote_type = info.get('quoteType', '').lower()
            if 'etf' in quote_type or 'fund' in quote_type:
                return True

            # 检查公司名称
            short_name = info.get('shortName', '').lower()
            long_name = info.get('longName', '').lower()

            etf_keywords = ['etf', 'fund', 'trust', 'spdr', 'ishares', 'vanguard', 'index']
            for keyword in etf_keywords:
                if keyword in short_name or keyword in long_name:
                    return True

            return False
        except:
            return False

    def _analyze_growth_style(self, data: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        """成长型投资风格分析"""
        try:
            info = data.get('info', {})

            # 成长性指标
            revenue_growth = info.get('revenueGrowth', 0)
            earnings_growth = info.get('earningsGrowth', 0)
            peg_ratio = info.get('pegRatio', 0)

            growth_score = 0
            growth_factors = []

            # 收入增长评分
            if revenue_growth:
                if revenue_growth > 0.25:
                    growth_score += 30
                    growth_factors.append(f'极高收入增长 ({revenue_growth:.1%})')
                elif revenue_growth > 0.15:
                    growth_score += 20
                    growth_factors.append(f'高收入增长 ({revenue_growth:.1%})')
                elif revenue_growth > 0.08:
                    growth_score += 10
                    growth_factors.append(f'良好收入增长 ({revenue_growth:.1%})')
                else:
                    growth_factors.append(f'收入增长一般 ({revenue_growth:.1%})')

            # 利润增长评分
            if earnings_growth:
                if earnings_growth > 0.30:
                    growth_score += 25
                    growth_factors.append(f'利润高速增长 ({earnings_growth:.1%})')
                elif earnings_growth > 0.15:
                    growth_score += 15
                    growth_factors.append(f'利润良好增长 ({earnings_growth:.1%})')
                elif earnings_growth > 0:
                    growth_score += 5
                    growth_factors.append(f'利润正增长 ({earnings_growth:.1%})')
                else:
                    growth_factors.append(f'利润负增长 ({earnings_growth:.1%})')

            # PEG比率评分
            if peg_ratio:
                if peg_ratio < 1.0:
                    growth_score += 15
                    growth_factors.append(f'优秀PEG比率 ({peg_ratio:.2f})')
                elif peg_ratio < 1.5:
                    growth_score += 10
                    growth_factors.append(f'良好PEG比率 ({peg_ratio:.2f})')
                elif peg_ratio < 2.0:
                    growth_score += 5
                    growth_factors.append(f'可接受PEG比率 ({peg_ratio:.2f})')
                else:
                    growth_factors.append(f'偏高PEG比率 ({peg_ratio:.2f})')

            # 成长性评级
            if growth_score >= 50:
                growth_rating = 'excellent'
                growth_description = '优秀成长股'
            elif growth_score >= 30:
                growth_rating = 'good'
                growth_description = '良好成长股'
            elif growth_score >= 15:
                growth_rating = 'fair'
                growth_description = '一般成长股'
            else:
                growth_rating = 'poor'
                growth_description = '成长性较差'

            return {
                'style': 'growth',
                'growth_score': growth_score,
                'growth_rating': growth_rating,
                'growth_description': growth_description,
                'growth_factors': growth_factors,
                'revenue_growth': revenue_growth,
                'earnings_growth': earnings_growth,
                'peg_ratio': peg_ratio
            }

        except Exception as e:
            logger.error(f"成长型分析失败: {e}")
            return {
                'style': 'growth',
                'error': str(e)
            }

    def _analyze_value_style(self, data: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        """价值型投资风格分析"""
        try:
            info = data.get('info', {})

            # 价值指标
            pe_ratio = info.get('trailingPE', 0)
            pb_ratio = info.get('priceToBook', 0)
            dividend_yield = info.get('dividendYield', 0)

            value_score = 0
            value_factors = []

            # PE比率评分
            if pe_ratio:
                if pe_ratio < 10:
                    value_score += 25
                    value_factors.append(f'极低PE估值 ({pe_ratio:.1f})')
                elif pe_ratio < 15:
                    value_score += 20
                    value_factors.append(f'低PE估值 ({pe_ratio:.1f})')
                elif pe_ratio < 20:
                    value_score += 10
                    value_factors.append(f'合理PE估值 ({pe_ratio:.1f})')
                else:
                    value_factors.append(f'高PE估值 ({pe_ratio:.1f})')

            # PB比率评分
            if pb_ratio:
                if pb_ratio < 1.0:
                    value_score += 20
                    value_factors.append(f'破净值 (PB={pb_ratio:.2f})')
                elif pb_ratio < 1.5:
                    value_score += 15
                    value_factors.append(f'低PB值 (PB={pb_ratio:.2f})')
                elif pb_ratio < 2.5:
                    value_score += 10
                    value_factors.append(f'合理PB值 (PB={pb_ratio:.2f})')
                else:
                    value_factors.append(f'高PB值 (PB={pb_ratio:.2f})')

            # 股息收益率评分
            if dividend_yield:
                if dividend_yield > 0.04:  # 4%以上
                    value_score += 15
                    value_factors.append(f'高股息收益 ({dividend_yield:.1%})')
                elif dividend_yield > 0.02:  # 2%以上
                    value_score += 10
                    value_factors.append(f'良好股息收益 ({dividend_yield:.1%})')
                elif dividend_yield > 0:
                    value_score += 5
                    value_factors.append(f'有股息收益 ({dividend_yield:.1%})')
            else:
                value_factors.append('无股息')

            # 价值评级
            if value_score >= 45:
                value_rating = 'excellent'
                value_description = '优秀价值股'
            elif value_score >= 30:
                value_rating = 'good'
                value_description = '良好价值股'
            elif value_score >= 15:
                value_rating = 'fair'
                value_description = '一般价值股'
            else:
                value_rating = 'poor'
                value_description = '价值吸引力较低'

            return {
                'style': 'value',
                'value_score': value_score,
                'value_rating': value_rating,
                'value_description': value_description,
                'value_factors': value_factors,
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'dividend_yield': dividend_yield
            }

        except Exception as e:
            logger.error(f"价值型分析失败: {e}")
            return {
                'style': 'value',
                'error': str(e)
            }

    def _analyze_balanced_style(self, data: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        """平衡型投资风格分析"""
        try:
            # 平衡风格结合成长和价值的分析
            growth_analysis = self._analyze_growth_style(data, risk_result)
            value_analysis = self._analyze_value_style(data, risk_result)

            # 计算综合评分
            growth_score = growth_analysis.get('growth_score', 0)
            value_score = value_analysis.get('value_score', 0)

            # 平衡评分：两者的加权平均
            balanced_score = (growth_score * 0.6 + value_score * 0.4)

            # 综合评级
            if balanced_score >= 40:
                balanced_rating = 'excellent'
                balanced_description = '优秀平衡型股票'
            elif balanced_score >= 25:
                balanced_rating = 'good'
                balanced_description = '良好平衡型股票'
            elif balanced_score >= 15:
                balanced_rating = 'fair'
                balanced_description = '一般平衡型股票'
            else:
                balanced_rating = 'poor'
                balanced_description = '平衡性较差'

            return {
                'style': 'balanced',
                'balanced_score': balanced_score,
                'balanced_rating': balanced_rating,
                'balanced_description': balanced_description,
                'growth_component': growth_analysis,
                'value_component': value_analysis
            }

        except Exception as e:
            logger.error(f"平衡型分析失败: {e}")
            return {
                'style': 'balanced',
                'error': str(e)
            }

    def _analyze_quality_style(self, data: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        质量型投资风格分析
        关注企业盈利质量、财务稳健性和管理效率
        """
        try:
            info = data.get('info', {})

            quality_score = 0
            quality_factors = []

            # 1. ROE (净资产收益率) - 权重30%
            roe = info.get('returnOnEquity', 0)
            if roe:
                if roe > 0.25:
                    quality_score += 30
                    quality_factors.append(f'优秀ROE ({roe:.1%})')
                elif roe > 0.20:
                    quality_score += 25
                    quality_factors.append(f'很好ROE ({roe:.1%})')
                elif roe > 0.15:
                    quality_score += 20
                    quality_factors.append(f'良好ROE ({roe:.1%})')
                elif roe > 0.10:
                    quality_score += 12
                    quality_factors.append(f'一般ROE ({roe:.1%})')
                elif roe > 0:
                    quality_score += 5
                    quality_factors.append(f'偏低ROE ({roe:.1%})')
                else:
                    quality_factors.append(f'负ROE ({roe:.1%})')

            # 2. 毛利率稳定性 - 权重25%
            gross_margin = info.get('grossMargins', 0)
            operating_margin = info.get('operatingMargins', 0)

            if gross_margin:
                if gross_margin > 0.50:
                    quality_score += 20
                    quality_factors.append(f'高毛利率 ({gross_margin:.1%})')
                elif gross_margin > 0.40:
                    quality_score += 16
                    quality_factors.append(f'良好毛利率 ({gross_margin:.1%})')
                elif gross_margin > 0.30:
                    quality_score += 12
                    quality_factors.append(f'中等毛利率 ({gross_margin:.1%})')
                elif gross_margin > 0.20:
                    quality_score += 6
                    quality_factors.append(f'偏低毛利率 ({gross_margin:.1%})')
                else:
                    quality_factors.append(f'低毛利率 ({gross_margin:.1%})')

            # 营业利润率加分
            if operating_margin and operating_margin > 0.20:
                quality_score += 5
                quality_factors.append(f'高营业利润率 ({operating_margin:.1%})')

            # 3. 自由现金流质量 - 权重25%
            fcf = info.get('freeCashflow', 0)
            net_income = info.get('netIncomeToCommon', 0)
            operating_cashflow = info.get('operatingCashflow', 0)

            if fcf and net_income and net_income > 0:
                fcf_ratio = fcf / net_income
                if fcf_ratio > 1.0:
                    quality_score += 20
                    quality_factors.append(f'优秀现金流质量 (FCF/NI={fcf_ratio:.1f})')
                elif fcf_ratio > 0.8:
                    quality_score += 15
                    quality_factors.append(f'良好现金流质量 (FCF/NI={fcf_ratio:.1f})')
                elif fcf_ratio > 0.5:
                    quality_score += 10
                    quality_factors.append(f'一般现金流质量 (FCF/NI={fcf_ratio:.1f})')
                elif fcf_ratio > 0:
                    quality_score += 5
                    quality_factors.append(f'偏弱现金流 (FCF/NI={fcf_ratio:.1f})')
                else:
                    quality_factors.append('现金流为负')
            elif operating_cashflow and operating_cashflow > 0:
                quality_score += 8
                quality_factors.append('有正向经营现金流')

            # 4. 负债可控性 - 权重20%
            debt_to_equity = info.get('debtToEquity', 0)
            current_ratio = info.get('currentRatio', 0)

            if debt_to_equity is not None:
                if debt_to_equity < 30:
                    quality_score += 15
                    quality_factors.append(f'极低负债 (D/E={debt_to_equity:.0f}%)')
                elif debt_to_equity < 50:
                    quality_score += 12
                    quality_factors.append(f'低负债 (D/E={debt_to_equity:.0f}%)')
                elif debt_to_equity < 100:
                    quality_score += 8
                    quality_factors.append(f'适度负债 (D/E={debt_to_equity:.0f}%)')
                elif debt_to_equity < 150:
                    quality_score += 4
                    quality_factors.append(f'中等负债 (D/E={debt_to_equity:.0f}%)')
                else:
                    quality_factors.append(f'高负债 (D/E={debt_to_equity:.0f}%)')

            # 流动比率加分
            if current_ratio and current_ratio > 2.0:
                quality_score += 5
                quality_factors.append(f'充足流动性 (流动比率={current_ratio:.1f})')
            elif current_ratio and current_ratio > 1.5:
                quality_score += 3

            # 质量评级
            if quality_score >= 60:
                quality_rating = 'excellent'
                quality_description = '优秀质量股'
            elif quality_score >= 45:
                quality_rating = 'good'
                quality_description = '良好质量股'
            elif quality_score >= 30:
                quality_rating = 'fair'
                quality_description = '一般质量股'
            else:
                quality_rating = 'poor'
                quality_description = '质量较差'

            return {
                'style': 'quality',
                'quality_score': quality_score,
                'quality_rating': quality_rating,
                'quality_description': quality_description,
                'quality_factors': quality_factors,
                'roe': roe,
                'gross_margin': gross_margin,
                'operating_margin': operating_margin,
                'debt_to_equity': debt_to_equity
            }

        except Exception as e:
            logger.error(f"质量型分析失败: {e}")
            return {
                'style': 'quality',
                'quality_score': 0,
                'error': str(e)
            }

    def _analyze_momentum_style(self, data: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        动量型投资风格分析
        关注价格趋势、技术指标和市场动能
        """
        try:
            info = data.get('info', {})
            history = data.get('history', pd.DataFrame())
            history_prices = data.get('history_prices', [])

            momentum_score = 0
            momentum_factors = []

            # 如果没有足够的历史数据，尝试从history_prices构建
            if len(history_prices) >= 50:
                prices = np.array(history_prices)
            elif not history.empty and 'Close' in history.columns:
                prices = history['Close'].values
            else:
                return {
                    'style': 'momentum',
                    'momentum_score': 0,
                    'momentum_rating': 'unknown',
                    'momentum_description': '历史数据不足',
                    'momentum_factors': ['需要至少50天历史数据']
                }

            current_price = prices[-1] if len(prices) > 0 else 0

            # 1. 短期动量 - 5日涨幅 (权重30%)
            if len(prices) >= 5:
                change_5d = (prices[-1] / prices[-5] - 1) * 100
                if change_5d > 8:
                    momentum_score += 25
                    momentum_factors.append(f'强劲短期动量 (+{change_5d:.1f}% 5日)')
                elif change_5d > 5:
                    momentum_score += 20
                    momentum_factors.append(f'良好短期动量 (+{change_5d:.1f}% 5日)')
                elif change_5d > 2:
                    momentum_score += 15
                    momentum_factors.append(f'温和上涨 (+{change_5d:.1f}% 5日)')
                elif change_5d > -2:
                    momentum_score += 8
                    momentum_factors.append(f'震荡整理 ({change_5d:+.1f}% 5日)')
                elif change_5d > -5:
                    momentum_score += 3
                    momentum_factors.append(f'轻微回调 ({change_5d:.1f}% 5日)')
                else:
                    momentum_factors.append(f'短期下跌 ({change_5d:.1f}% 5日)')

            # 2. 中期趋势 - MA20 vs MA50 (权重30%)
            if len(prices) >= 50:
                ma20 = np.mean(prices[-20:])
                ma50 = np.mean(prices[-50:])

                ma_ratio = ma20 / ma50 if ma50 > 0 else 1

                if ma_ratio > 1.08:
                    momentum_score += 25
                    momentum_factors.append(f'强势趋势 (MA20 > MA50 +{(ma_ratio-1)*100:.1f}%)')
                elif ma_ratio > 1.03:
                    momentum_score += 20
                    momentum_factors.append(f'上升趋势 (MA20 > MA50)')
                elif ma_ratio > 0.98:
                    momentum_score += 12
                    momentum_factors.append('均线纠缠')
                elif ma_ratio > 0.93:
                    momentum_score += 5
                    momentum_factors.append('轻度走弱')
                else:
                    momentum_factors.append(f'下跌趋势 (MA20 < MA50 {(ma_ratio-1)*100:.1f}%)')

                # 价格在均线上方加分
                if current_price > ma20 > ma50:
                    momentum_score += 5
                    momentum_factors.append('价格在双均线上方')

            # 3. RSI指标 (权重25%)
            if len(prices) >= 14:
                rsi = self._calculate_rsi(prices, 14)
                if 60 <= rsi <= 70:
                    momentum_score += 20
                    momentum_factors.append(f'健康上涨 (RSI={rsi:.0f})')
                elif 50 <= rsi < 60:
                    momentum_score += 15
                    momentum_factors.append(f'温和看涨 (RSI={rsi:.0f})')
                elif 40 <= rsi < 50:
                    momentum_score += 10
                    momentum_factors.append(f'中性 (RSI={rsi:.0f})')
                elif rsi > 70:
                    momentum_score += 8
                    momentum_factors.append(f'超买区域 (RSI={rsi:.0f})，注意回调')
                elif rsi < 30:
                    momentum_score += 5
                    momentum_factors.append(f'超卖区域 (RSI={rsi:.0f})，可能反弹')
                else:
                    momentum_score += 3
                    momentum_factors.append(f'弱势 (RSI={rsi:.0f})')

            # 4. 成交量确认 (权重15%)
            if not history.empty and 'Volume' in history.columns:
                volumes = history['Volume'].values
                if len(volumes) >= 20:
                    vol_5d = np.mean(volumes[-5:])
                    vol_20d = np.mean(volumes[-20:])
                    vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1

                    if vol_ratio > 2.0:
                        momentum_score += 12
                        momentum_factors.append(f'放量 (量比={vol_ratio:.1f})')
                    elif vol_ratio > 1.5:
                        momentum_score += 10
                        momentum_factors.append(f'温和放量 (量比={vol_ratio:.1f})')
                    elif vol_ratio > 1.0:
                        momentum_score += 6
                        momentum_factors.append('成交量正常')
                    elif vol_ratio > 0.5:
                        momentum_score += 3
                        momentum_factors.append('缩量')
                    else:
                        momentum_factors.append('严重缩量')

            # 5. 52周位置 (额外加分)
            week_52_high = info.get('fiftyTwoWeekHigh', 0)
            week_52_low = info.get('fiftyTwoWeekLow', 0)

            if week_52_high and week_52_low and current_price:
                position = (current_price - week_52_low) / (week_52_high - week_52_low) if week_52_high > week_52_low else 0.5
                if position > 0.9:
                    momentum_score += 8
                    momentum_factors.append('接近52周新高')
                elif position > 0.7:
                    momentum_score += 5
                    momentum_factors.append('52周高位区域')

            # 动量评级
            if momentum_score >= 60:
                momentum_rating = 'excellent'
                momentum_description = '强劲动量'
            elif momentum_score >= 45:
                momentum_rating = 'good'
                momentum_description = '良好动量'
            elif momentum_score >= 30:
                momentum_rating = 'fair'
                momentum_description = '一般动量'
            else:
                momentum_rating = 'poor'
                momentum_description = '动量较弱'

            return {
                'style': 'momentum',
                'momentum_score': momentum_score,
                'momentum_rating': momentum_rating,
                'momentum_description': momentum_description,
                'momentum_factors': momentum_factors
            }

        except Exception as e:
            logger.error(f"动量型分析失败: {e}")
            return {
                'style': 'momentum',
                'momentum_score': 0,
                'error': str(e)
            }

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50  # 默认中性

            # 计算价格变化
            deltas = np.diff(prices)

            # 分离上涨和下跌
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            # 计算平均收益和损失
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            if avg_loss == 0:
                return 100

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return rsi

        except:
            return 50

    def _generate_recommendation(self, analysis_result: Dict[str, Any],
                               risk_result: Dict[str, Any], style: str) -> Dict[str, Any]:
        """生成投资建议"""
        try:
            # 获取评分
            style_key = f'{style}_score'
            score = analysis_result.get(style_key, 0)
            risk_level = risk_result.get('risk_level', 'medium')

            # 基础建议
            if score >= 40 and risk_level in ['low', 'medium']:
                action = 'BUY'
                confidence = 'high'
                reason = '高质量股票，风险可控'
            elif score >= 25 and risk_level == 'low':
                action = 'BUY'
                confidence = 'medium'
                reason = '质量尚可，低风险'
            elif score >= 25 and risk_level == 'medium':
                action = 'HOLD'
                confidence = 'medium'
                reason = '质量尚可，但需注意风险'
            elif score >= 15:
                action = 'HOLD'
                confidence = 'low'
                reason = '质量一般，谨慎观察'
            else:
                action = 'AVOID'
                confidence = 'high'
                reason = '质量较差或风险过高'

            # 高风险调整
            if risk_level == 'high':
                if action == 'BUY':
                    action = 'HOLD'
                    reason += '，但风险较高'
                elif action == 'HOLD':
                    action = 'AVOID'
                    reason = '风险过高'

            return {
                'action': action,
                'confidence': confidence,
                'reason': reason,
                'score': score,
                'risk_level': risk_level
            }

        except Exception as e:
            logger.error(f"生成建议失败: {e}")
            return {
                'action': 'HOLD',
                'confidence': 'low',
                'reason': '分析出错，建议观望'
            }

    def _calculate_confidence_score(self, data: Dict[str, Any], analysis_result: Dict[str, Any]) -> float:
        """计算分析信心度"""
        try:
            confidence = 0.5  # 基础信心度

            # 数据完整性检查
            info = data.get('info', {})
            history_prices = data.get('history_prices', [])

            # 财务数据完整性
            financial_fields = ['trailingPE', 'priceToBook', 'marketCap', 'revenueGrowth']
            available_fields = sum(1 for field in financial_fields if info.get(field))
            confidence += (available_fields / len(financial_fields)) * 0.2

            # 历史数据充分性
            if len(history_prices) >= 250:  # 一年数据
                confidence += 0.2
            elif len(history_prices) >= 60:
                confidence += 0.1

            # 分析结果质量
            if not analysis_result.get('error'):
                confidence += 0.1

            return min(confidence, 1.0)

        except:
            return 0.5


# 为独立测试提供主函数
if __name__ == "__main__":
    # 独立测试代码
    strategy = BasicAnalysisStrategy()

    # 模拟测试数据
    test_data = {
        'ticker': 'AAPL',
        'info': {
            'trailingPE': 25,
            'priceToBook': 8,
            'marketCap': 3000000000000,
            'revenueGrowth': 0.12,
            'earningsGrowth': 0.15,
            'pegRatio': 1.2,
            'dividendYield': 0.005,
            'sector': 'Technology',
            'shortName': 'Apple Inc.'
        },
        'history_prices': [150 + i + np.random.normal(0, 2) for i in range(100)]
    }

    test_liquidity = {
        'is_liquid': True,
        'avg_daily_volume_usd': 10000000000
    }

    print("=== 基础分析策略独立测试 ===")

    # 测试不同风格的分析
    for style in ['growth', 'value', 'balanced']:
        print(f"\n{style.upper()} 风格分析:")
        result = strategy.analyze(test_data, style, test_liquidity)
        if result.get('success'):
            recommendation = result.get('recommendation', {})
            print(f"  建议: {recommendation.get('action', 'N/A')}")
            print(f"  信心: {recommendation.get('confidence', 'N/A')}")
            print(f"  原因: {recommendation.get('reason', 'N/A')}")
        else:
            print(f"  分析失败: {result.get('error', 'Unknown')}")

    print("\n测试完成!")