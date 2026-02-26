import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { useTranslation } from 'react-i18next';
import { useUserTier, useHasAccess, BlurText } from '@/components/BlurOverlay';
import { useAnalytics } from '@/hooks/useAnalytics';
import { Button } from '@/components/ui/button';
import { Lock, ArrowRight } from 'lucide-react';

// Types
interface Recommendation {
    symbol: string;
    strategy: string;
    strike: number;
    expiry: string;
    score: number;
    style_label: string;
    trend: string;
    current_price: number;
    premium_yield: string;
    reason: string;
    risk_color?: string;
    // 市场信息
    market?: string;               // 'US' | 'HK' | 'CN' | 'COMMODITY'
    currency?: string;             // 'USD' | 'HKD' | 'CNY'
    // 期权评分系统优化
    symbol_quality?: number;       // 标的质量评分 (0-100)
    symbol_tier?: number;          // 标的等级 (1-5)
    symbol_description?: string;   // 标的描述
    price_trend?: string;          // 价格趋势 (up/down/sideways)
    trend_change_pct?: number;     // 趋势变化百分比
    timing_bonus?: number;         // 时机加分
    expiry_warning?: string;       // 临期风险警告
    is_daily_option?: boolean;     // 是否为日权
    days_to_expiry?: number;       // 距到期天数
}

interface MarketSummary {
    overall_trend: string;
    vix_level: number;
    recommended_strategies: string[];
}

interface RecommendationsResponse {
    success: boolean;
    recommendations: Recommendation[];
    market_summary: MarketSummary | null;
    updated_at: string;
    error?: string;
}

// CSS styles
const styles = `
    .hot-recommendations {
        margin-bottom: 2rem;
    }

    .recommendations-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
    }

    .recommendations-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }

    .update-time {
        font-size: 0.75rem;
        color: hsl(240, 5%, 50%);
    }

    .recommendations-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1rem;
    }

    @media (min-width: 768px) {
        .recommendations-grid {
            grid-template-columns: repeat(3, 1fr);
        }
    }

    @media (min-width: 1024px) {
        .recommendations-grid {
            grid-template-columns: repeat(5, 1fr);
        }
    }

    .recommendation-card {
        background-color: hsl(240, 6%, 10%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.75rem;
        padding: 1.25rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .recommendation-card:hover {
        border-color: hsl(178, 78%, 32%);
        transform: translateY(-2px);
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.75rem;
    }

    .symbol-info {
        display: flex;
        flex-direction: column;
    }

    .symbol {
        font-size: 1.25rem;
        font-weight: 700;
        color: white;
    }

    .current-price {
        font-size: 0.875rem;
        color: hsl(240, 5%, 64.9%);
    }

    .score-circle {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 700;
    }

    .score-high {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10B981;
        border: 2px solid #10B981;
    }

    .score-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 2px solid #F59E0B;
    }

    .score-low {
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        border: 2px solid #EF4444;
    }

    .strategy-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }

    .strategy-sell-put {
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
    }

    .strategy-sell-call {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }

    .strategy-buy-put {
        background-color: rgba(239, 68, 68, 0.3);
        color: #F87171;
    }

    .strategy-buy-call {
        background-color: rgba(16, 185, 129, 0.3);
        color: #34D399;
    }

    .option-details {
        display: flex;
        gap: 1rem;
        margin-bottom: 0.75rem;
        font-size: 0.875rem;
    }

    .detail-item {
        display: flex;
        flex-direction: column;
    }

    .detail-label {
        font-size: 0.7rem;
        color: hsl(240, 5%, 50%);
        text-transform: uppercase;
    }

    .detail-value {
        font-weight: 500;
        color: white;
    }

    .trend-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        margin-bottom: 0.5rem;
    }

    .trend-up {
        color: #10B981;
    }

    .trend-down {
        color: #EF4444;
    }

    .trend-sideways {
        color: #F59E0B;
    }

    .yield-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        background-color: rgba(13, 155, 151, 0.2);
        color: hsl(178, 78%, 45%);
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .reason-text {
        font-size: 0.75rem;
        color: hsl(240, 5%, 60%);
        line-height: 1.4;
        margin-top: 0.75rem;
        border-top: 1px solid hsl(240, 3.7%, 15.9%);
        padding-top: 0.75rem;
    }

    .market-summary {
        background-color: hsl(240, 6%, 8%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.75rem;
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        gap: 2rem;
        flex-wrap: wrap;
    }

    .summary-item {
        display: flex;
        flex-direction: column;
    }

    .summary-label {
        font-size: 0.75rem;
        color: hsl(240, 5%, 50%);
        margin-bottom: 0.25rem;
    }

    .summary-value {
        font-size: 1rem;
        font-weight: 600;
        color: white;
    }

    .loading-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem;
        color: hsl(240, 5%, 64.9%);
    }

    .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid hsl(240, 3.7%, 15.9%);
        border-top-color: hsl(178, 78%, 32%);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .error-state {
        text-align: center;
        padding: 2rem;
        color: hsl(240, 5%, 50%);
    }

    .empty-state {
        text-align: center;
        padding: 3rem;
        color: hsl(240, 5%, 50%);
    }

    /* 临期警告样式 */
    .expiry-warning {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.7rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        margin-top: 0.5rem;
    }

    .expiry-warning-high {
        background-color: rgba(239, 68, 68, 0.2);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .expiry-warning-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .expiry-warning-low {
        background-color: rgba(59, 130, 246, 0.2);
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    /* 标的质量等级徽章 */
    .quality-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.65rem;
        padding: 0.125rem 0.375rem;
        border-radius: 0.25rem;
        margin-left: 0.5rem;
    }

    .quality-tier-1 {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34D399;
    }

    .quality-tier-2 {
        background-color: rgba(59, 130, 246, 0.2);
        color: #93C5FD;
    }

    .quality-tier-3 {
        background-color: rgba(245, 158, 11, 0.2);
        color: #FBBF24;
    }

    .quality-tier-4,
    .quality-tier-5 {
        background-color: rgba(239, 68, 68, 0.2);
        color: #F87171;
    }

    /* 时机加分徽章 */
    .timing-bonus-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.65rem;
        color: #10B981;
        margin-left: 0.25rem;
    }

    /* 市场标签 */
    .market-badge {
        display: inline-block;
        font-size: 0.6rem;
        font-weight: 600;
        padding: 0.1rem 0.35rem;
        border-radius: 0.2rem;
        margin-left: 0.375rem;
        vertical-align: middle;
        background-color: rgba(245, 158, 11, 0.2);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
`;

// Strategy name mapping
const strategyNames: Record<string, { en: string; zh: string }> = {
    'sell_put': { en: 'Sell Put', zh: '卖出看跌' },
    'sell_call': { en: 'Sell Call', zh: '卖出看涨' },
    'buy_put': { en: 'Buy Put', zh: '买入看跌' },
    'buy_call': { en: 'Buy Call', zh: '买入看涨' },
};

// Trend names
const trendNames: Record<string, { en: string; zh: string }> = {
    'uptrend': { en: 'Uptrend', zh: '上升趋势' },
    'downtrend': { en: 'Downtrend', zh: '下降趋势' },
    'sideways': { en: 'Sideways', zh: '横盘震荡' },
    'mixed': { en: 'Mixed', zh: '混合' },
};

// Currency symbol helper
const getCurrencySymbol = (currency?: string): string => {
    switch (currency) {
        case 'HKD': return 'HK$';
        case 'CNY': return '¥';
        default: return '$';
    }
};

interface HotRecommendationsProps {
    maxItems?: number;
    showMarketSummary?: boolean;
}

// 静态示例数据（当API不可用时显示）
const FALLBACK_RECOMMENDATIONS: Recommendation[] = [
    {
        symbol: 'NVDA',
        strategy: 'sell_put',
        strike: 130,
        expiry: '2025-02-21',
        score: 85,
        style_label: '稳健收益',
        trend: 'uptrend',
        current_price: 138.50,
        premium_yield: '2.3%',
        reason: 'AI龙头，股价回调至支撑位，波动率适中',
        risk_color: '#10B981',
    },
    {
        symbol: 'AAPL',
        strategy: 'sell_call',
        strike: 250,
        expiry: '2025-02-14',
        score: 78,
        style_label: '稳健收益',
        trend: 'sideways',
        current_price: 237.80,
        premium_yield: '1.8%',
        reason: '股价在阻力位附近震荡，适合卖出看涨',
        risk_color: '#10B981',
    },
    {
        symbol: 'TSLA',
        strategy: 'buy_call',
        strike: 450,
        expiry: '2025-03-21',
        score: 72,
        style_label: '激进策略',
        trend: 'uptrend',
        current_price: 421.50,
        premium_yield: '8.5%',
        reason: '趋势向上，突破前高可能性大',
        risk_color: '#F59E0B',
    },
    {
        symbol: 'META',
        strategy: 'sell_put',
        strike: 580,
        expiry: '2025-02-21',
        score: 80,
        style_label: '稳健收益',
        trend: 'uptrend',
        current_price: 612.30,
        premium_yield: '1.9%',
        reason: '基本面强劲，支撑位明确',
        risk_color: '#10B981',
    },
    {
        symbol: 'AMD',
        strategy: 'sell_put',
        strike: 115,
        expiry: '2025-02-14',
        score: 76,
        style_label: '稳健收益',
        trend: 'sideways',
        current_price: 121.20,
        premium_yield: '2.1%',
        reason: 'AI芯片需求旺盛，估值合理',
        risk_color: '#10B981',
    },
    {
        symbol: '0700.HK',
        strategy: 'sell_put',
        strike: 380,
        expiry: '2025-03-27',
        score: 74,
        style_label: '稳健收益',
        trend: 'sideways',
        current_price: 412.60,
        premium_yield: '1.6%',
        reason: '港股科技龙头，估值处于合理区间',
        risk_color: '#10B981',
        market: 'HK',
        currency: 'HKD',
    },
    {
        symbol: 'au',
        strategy: 'sell_put',
        strike: 680,
        expiry: 'au2606',
        score: 73,
        style_label: '稳健收益',
        trend: 'uptrend',
        current_price: 715.80,
        premium_yield: '1.4%',
        reason: '黄金避险需求旺盛，支撑位稳固',
        risk_color: '#10B981',
        market: 'COMMODITY',
        currency: 'CNY',
    },
];

const FALLBACK_MARKET_SUMMARY: MarketSummary = {
    overall_trend: 'mixed',
    vix_level: 16.5,
    recommended_strategies: ['sell_put', 'sell_call'],
};

export default function HotRecommendations({
    maxItems = 5,
    showMarketSummary = true
}: HotRecommendationsProps) {
    const navigate = useNavigate();
    const { i18n, t } = useTranslation();
    const isZh = i18n.language.startsWith('zh');

    // User tier for tiered display
    const userTier = useUserTier();
    const hasFullAccess = useHasAccess('plus');  // Plus+ users see all details
    const { trackRecommendationView, trackRecommendationClick, trackCtaClick } = useAnalytics();

    const [data, setData] = useState<RecommendationsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [usingFallback, setUsingFallback] = useState(false);

    // Fetch recommendations
    useEffect(() => {
        const fetchRecommendations = async () => {
            try {
                setLoading(true);
                setUsingFallback(false);
                const response = await api.get(`/options/recommendations?count=${maxItems}`);
                if (response.data.success) {
                    setData(response.data);
                    setError('');
                } else {
                    // API 返回失败，使用备用数据
                    console.warn('API returned error, using fallback data');
                    setData({
                        success: true,
                        recommendations: FALLBACK_RECOMMENDATIONS.slice(0, maxItems),
                        market_summary: FALLBACK_MARKET_SUMMARY,
                        updated_at: new Date().toISOString(),
                    });
                    setUsingFallback(true);
                    setError('');
                }
            } catch (err: any) {
                console.error('Failed to fetch recommendations:', err);
                // API 请求失败，使用备用数据
                setData({
                    success: true,
                    recommendations: FALLBACK_RECOMMENDATIONS.slice(0, maxItems),
                    market_summary: FALLBACK_MARKET_SUMMARY,
                    updated_at: new Date().toISOString(),
                });
                setUsingFallback(true);
                setError('');
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [maxItems, isZh]);

    // Get score class
    const getScoreClass = (score: number) => {
        if (score >= 70) return 'score-high';
        if (score >= 50) return 'score-medium';
        return 'score-low';
    };

    // Get strategy class
    const getStrategyClass = (strategy: string) => {
        switch (strategy) {
            case 'sell_put': return 'strategy-sell-put';
            case 'sell_call': return 'strategy-sell-call';
            case 'buy_put': return 'strategy-buy-put';
            case 'buy_call': return 'strategy-buy-call';
            default: return '';
        }
    };

    // Get trend class
    const getTrendClass = (trend: string) => {
        switch (trend) {
            case 'uptrend': return 'trend-up';
            case 'downtrend': return 'trend-down';
            default: return 'trend-sideways';
        }
    };

    // Get trend arrow
    const getTrendArrow = (trend: string) => {
        switch (trend) {
            case 'uptrend': return '↑';
            case 'downtrend': return '↓';
            default: return '→';
        }
    };

    // Format update time
    const formatUpdateTime = (isoString: string) => {
        try {
            const date = new Date(isoString);
            return date.toLocaleString(isZh ? 'zh-CN' : 'en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return isoString;
        }
    };

    // Handle card click
    const handleCardClick = (rec: Recommendation, _index: number) => {
        trackRecommendationClick(rec.symbol, rec.strategy, 'option');

        // If user is guest, redirect to login
        if (userTier === 'guest') {
            trackCtaClick('recommendation_click', 'hot_recommendations');
            navigate('/login');
        } else {
            navigate(`/options?ticker=${rec.symbol}`);
        }
    };

    // Handle CTA click for non-authenticated users
    const handleCtaClick = () => {
        trackCtaClick('unlock_recommendations', 'hot_recommendations');
        if (userTier === 'guest') {
            navigate('/login');
        } else {
            navigate('/pricing');
        }
    };

    if (loading) {
        return (
            <>
                <style>{styles}</style>
                <div className="hot-recommendations">
                    <div className="loading-state">
                        <div className="spinner"></div>
                        <span>{isZh ? '加载热门推荐...' : 'Loading recommendations...'}</span>
                    </div>
                </div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <style>{styles}</style>
                <div className="hot-recommendations">
                    <div className="error-state">
                        <p>{error}</p>
                    </div>
                </div>
            </>
        );
    }

    if (!data || !data.recommendations || data.recommendations.length === 0) {
        return (
            <>
                <style>{styles}</style>
                <div className="hot-recommendations">
                    <div className="empty-state">
                        <p>{isZh ? '暂无推荐数据' : 'No recommendations available'}</p>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <style>{styles}</style>
            <div className="hot-recommendations">
                {/* Header */}
                <div className="recommendations-header">
                    <div>
                        <h2 className="recommendations-title">
                            {isZh ? '今日热门期权推荐' : 'Today\'s Hot Options'}
                        </h2>
                        {usingFallback && (
                            <span className="text-xs text-yellow-500 mt-1 block">
                                {isZh ? '(示例数据 - 请刷新获取实时推荐)' : '(Sample data - refresh for live recommendations)'}
                            </span>
                        )}
                    </div>
                    {data.updated_at && !usingFallback && (
                        <span className="update-time">
                            {isZh ? '更新于 ' : 'Updated '}{formatUpdateTime(data.updated_at)}
                        </span>
                    )}
                </div>

                {/* Market Summary */}
                {showMarketSummary && data.market_summary && (
                    <div className="market-summary">
                        <div className="summary-item">
                            <span className="summary-label">
                                {isZh ? '市场趋势' : 'Market Trend'}
                            </span>
                            <span className={`summary-value ${getTrendClass(data.market_summary.overall_trend)}`}>
                                {getTrendArrow(data.market_summary.overall_trend)}{' '}
                                {trendNames[data.market_summary.overall_trend]?.[isZh ? 'zh' : 'en'] || data.market_summary.overall_trend}
                            </span>
                        </div>
                        {data.market_summary.vix_level > 0 && (
                            <div className="summary-item">
                                <span className="summary-label">VIX</span>
                                <span className="summary-value">
                                    {data.market_summary.vix_level.toFixed(1)}
                                </span>
                            </div>
                        )}
                        {data.market_summary.recommended_strategies && data.market_summary.recommended_strategies.length > 0 && (
                            <div className="summary-item">
                                <span className="summary-label">
                                    {isZh ? '推荐策略' : 'Recommended'}
                                </span>
                                <span className="summary-value">
                                    {data.market_summary.recommended_strategies.map(s =>
                                        strategyNames[s]?.[isZh ? 'zh' : 'en'] || s
                                    ).join(', ')}
                                </span>
                            </div>
                        )}
                    </div>
                )}

                {/* Recommendations Grid */}
                <div className="recommendations-grid">
                    {data.recommendations.map((rec, index) => {
                        // Track view when card is rendered (first 3 visible)
                        if (index < 3) {
                            trackRecommendationView(rec.symbol, index, 'option');
                        }

                        // Determine if this card should show blurred info
                        // Guest: show first 2 cards with score only
                        // Free: show all cards but blur strike/expiry/yield
                        // Plus+: show everything
                        const showScore = true; // Everyone sees score
                        const showDetails = hasFullAccess || (userTier === 'free' && index < 3);

                        return (
                            <div
                                key={`${rec.symbol}-${rec.strategy}-${index}`}
                                className="recommendation-card"
                                onClick={() => handleCardClick(rec, index)}
                            >
                                {/* Header */}
                                <div className="card-header">
                                    <div className="symbol-info">
                                        <span className="symbol">
                                            {rec.symbol}
                                            {/* 市场标签（非US市场显示） */}
                                            {rec.market && rec.market !== 'US' && (
                                                <span className="market-badge">{rec.market === 'COMMODITY' ? '商品' : rec.market}</span>
                                            )}
                                            {/* 标的质量等级徽章 */}
                                            {rec.symbol_tier && rec.symbol_tier <= 2 && (
                                                <span className={`quality-badge quality-tier-${rec.symbol_tier}`}>
                                                    {rec.symbol_tier === 1 ? '优质' : '稳健'}
                                                </span>
                                            )}
                                        </span>
                                        <span className="current-price">{getCurrencySymbol(rec.currency)}{rec.current_price?.toFixed(2)}</span>
                                    </div>
                                    <div className={`score-circle ${getScoreClass(rec.score)}`}>
                                        {showScore ? (
                                            <>
                                                {rec.score.toFixed(0)}
                                                {/* 时机加分 */}
                                                {rec.timing_bonus && rec.timing_bonus > 0 && (
                                                    <span className="timing-bonus-badge">+{rec.timing_bonus}</span>
                                                )}
                                            </>
                                        ) : (
                                            <Lock size={16} />
                                        )}
                                    </div>
                                </div>

                                {/* Strategy Badge */}
                                <span className={`strategy-badge ${getStrategyClass(rec.strategy)}`}>
                                    {strategyNames[rec.strategy]?.[isZh ? 'zh' : 'en'] || rec.strategy}
                                </span>

                                {/* Option Details - Blur for non-Plus users */}
                                <div className="option-details">
                                    <div className="detail-item">
                                        <span className="detail-label">{isZh ? '执行价' : 'Strike'}</span>
                                        <span className="detail-value">
                                            {showDetails ? `${getCurrencySymbol(rec.currency)}${rec.strike}` : (
                                                <BlurText text={`${getCurrencySymbol(rec.currency)}${rec.strike}`} placeholder={`${getCurrencySymbol(rec.currency)}???`} requiredTier="plus" />
                                            )}
                                        </span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="detail-label">{isZh ? '到期日' : 'Expiry'}</span>
                                        <span className="detail-value">
                                            {showDetails ? rec.expiry : (
                                                <BlurText text={rec.expiry} placeholder="????-??-??" requiredTier="plus" />
                                            )}
                                        </span>
                                    </div>
                                </div>

                                {/* Trend */}
                                <div className={`trend-indicator ${getTrendClass(rec.trend)}`}>
                                    <span>{getTrendArrow(rec.trend)}</span>
                                    <span>
                                        {trendNames[rec.trend]?.[isZh ? 'zh' : 'en'] || rec.trend}
                                    </span>
                                    {rec.premium_yield && (
                                        <span className="yield-badge">
                                            {showDetails ? rec.premium_yield : '??.?%'}
                                        </span>
                                    )}
                                </div>

                                {/* Style Label */}
                                {rec.style_label && (
                                    <div
                                        className="text-xs mt-2"
                                        style={{ color: rec.risk_color || '#9CA3AF' }}
                                    >
                                        {rec.style_label}
                                    </div>
                                )}

                                {/* 临期警告 */}
                                {rec.expiry_warning && (
                                    <div className={`expiry-warning ${
                                        rec.expiry_warning.includes('⚠️') || rec.expiry_warning.includes('⛔')
                                            ? 'expiry-warning-high'
                                            : rec.expiry_warning.includes('⚡')
                                            ? 'expiry-warning-medium'
                                            : 'expiry-warning-low'
                                    }`}>
                                        {rec.expiry_warning}
                                    </div>
                                )}

                                {/* Reason - Only for Plus+ users */}
                                {rec.reason && showDetails && (
                                    <div className="reason-text">
                                        {rec.reason}
                                    </div>
                                )}

                                {/* Lock overlay for non-Plus users */}
                                {!showDetails && (
                                    <div className="reason-text flex items-center gap-2 text-slate-500">
                                        <Lock size={12} />
                                        <span>{t('blur.upgradePrompt')}</span>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* CTA for non-authenticated or free users */}
                {!hasFullAccess && (
                    <div className="mt-6 text-center">
                        <Button
                            onClick={handleCtaClick}
                            className="bg-[#0D9B97] hover:bg-[#10B5B0] text-white gap-2"
                        >
                            {userTier === 'guest'
                                ? t('landing.recommendations.signUpCta')
                                : t('landing.recommendations.upgradeCta')
                            }
                            <ArrowRight size={16} />
                        </Button>
                    </div>
                )}
            </div>
        </>
    );
}
