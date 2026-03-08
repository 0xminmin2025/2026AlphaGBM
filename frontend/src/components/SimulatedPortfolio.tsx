/**
 * 模拟投资组合组件
 * 展示老虎证券模拟账户的持仓和收益情况
 * 初始资金：$100,000
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Wallet,
    TrendingUp,
    TrendingDown,
    DollarSign,
    PieChart,
    Clock,
    ChevronDown,
    ChevronUp,
    ExternalLink,
    RefreshCw
} from 'lucide-react';

// 模拟持仓数据类型
interface Position {
    id: string;
    symbol: string;
    optionType: 'CALL' | 'PUT';
    strategy: 'BUY' | 'SELL';
    strike: number;
    expiry: string;
    quantity: number;
    costBasis: number;      // 每份成本
    currentPrice: number;   // 当前价格
    stockPrice: number;     // 标的股价
    openDate: string;
    pnl: number;            // 盈亏金额
    pnlPercent: number;     // 盈亏百分比
}

// 账户汇总数据
interface AccountSummary {
    totalValue: number;         // 账户总价值
    cashBalance: number;        // 现金余额
    positionsValue: number;     // 持仓价值
    initialCapital: number;     // 初始资金
    totalPnl: number;           // 总盈亏
    totalPnlPercent: number;    // 总盈亏百分比
    dayPnl: number;             // 当日盈亏
    dayPnlPercent: number;      // 当日盈亏百分比
    lastUpdated: string;        // 最后更新时间
}

// 模拟数据（后续可替换为真实API数据）
const mockSummary: AccountSummary = {
    totalValue: 103250.80,
    cashBalance: 85420.50,
    positionsValue: 17830.30,
    initialCapital: 100000,
    totalPnl: 3250.80,
    totalPnlPercent: 3.25,
    dayPnl: 485.20,
    dayPnlPercent: 0.47,
    lastUpdated: new Date().toISOString()
};

const mockPositions: Position[] = [
    {
        id: '1',
        symbol: 'NVDA',
        optionType: 'PUT',
        strategy: 'SELL',
        strike: 130,
        expiry: '2025-02-21',
        quantity: 2,
        costBasis: 3.85,
        currentPrice: 2.10,
        stockPrice: 138.50,
        openDate: '2025-01-15',
        pnl: 350,
        pnlPercent: 45.45
    },
    {
        id: '2',
        symbol: 'AAPL',
        optionType: 'CALL',
        strategy: 'SELL',
        strike: 250,
        expiry: '2025-02-14',
        quantity: 3,
        costBasis: 2.20,
        currentPrice: 1.85,
        stockPrice: 229.80,
        openDate: '2025-01-10',
        pnl: 105,
        pnlPercent: 15.91
    },
    {
        id: '3',
        symbol: 'TSLA',
        optionType: 'CALL',
        strategy: 'BUY',
        strike: 420,
        expiry: '2025-01-31',
        quantity: 5,
        costBasis: 8.50,
        currentPrice: 12.30,
        stockPrice: 428.60,
        openDate: '2025-01-08',
        pnl: 1900,
        pnlPercent: 44.71
    },
    {
        id: '4',
        symbol: 'META',
        optionType: 'PUT',
        strategy: 'SELL',
        strike: 590,
        expiry: '2025-02-07',
        quantity: 1,
        costBasis: 5.80,
        currentPrice: 4.20,
        stockPrice: 612.40,
        openDate: '2025-01-17',
        pnl: 160,
        pnlPercent: 27.59
    },
    {
        id: '5',
        symbol: 'GOOGL',
        optionType: 'CALL',
        strategy: 'BUY',
        strike: 200,
        expiry: '2025-02-28',
        quantity: 2,
        costBasis: 4.60,
        currentPrice: 3.80,
        stockPrice: 198.20,
        openDate: '2025-01-20',
        pnl: -160,
        pnlPercent: -17.39
    }
];

// 组件样式
const componentStyles = `
    .portfolio-card {
        background: rgba(24, 24, 27, 0.8);
        border: 1px solid rgba(39, 39, 42, 0.8);
        border-radius: 16px;
        overflow: hidden;
    }

    .portfolio-header {
        background: linear-gradient(135deg, rgba(13, 155, 151, 0.15) 0%, rgba(24, 24, 27, 0.8) 100%);
        border-bottom: 1px solid rgba(39, 39, 42, 0.8);
        padding: 24px;
    }

    .stat-box {
        background: rgba(9, 9, 11, 0.6);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }

    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
    }

    .stat-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-top: 4px;
    }

    .position-row {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
        gap: 16px;
        padding: 16px 24px;
        border-bottom: 1px solid rgba(39, 39, 42, 0.5);
        align-items: center;
        transition: background 0.2s;
    }

    .position-row:hover {
        background: rgba(13, 155, 151, 0.05);
    }

    .position-header {
        background: rgba(9, 9, 11, 0.4);
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .position-header:hover {
        background: rgba(9, 9, 11, 0.4);
    }

    .strategy-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .strategy-badge.sell-put {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }

    .strategy-badge.sell-call {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
    }

    .strategy-badge.buy-call {
        background: rgba(59, 130, 246, 0.2);
        color: #3B82F6;
    }

    .strategy-badge.buy-put {
        background: rgba(239, 68, 68, 0.2);
        color: #EF4444;
    }

    .pnl-positive {
        color: #10B981;
    }

    .pnl-negative {
        color: #EF4444;
    }

    .refresh-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        background: rgba(13, 155, 151, 0.15);
        border: 1px solid rgba(13, 155, 151, 0.3);
        border-radius: 8px;
        color: #0D9B97;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .refresh-btn:hover {
        background: rgba(13, 155, 151, 0.25);
        border-color: rgba(13, 155, 151, 0.5);
    }

    .refresh-btn.loading svg {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @media (max-width: 768px) {
        .position-row {
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .position-row > div:nth-child(n+3) {
            display: none;
        }

        .stat-value {
            font-size: 1.25rem;
        }
    }
`;

interface SimulatedPortfolioProps {
    summary?: AccountSummary;
    positions?: Position[];
    onRefresh?: () => void;
    isLoading?: boolean;
}

export default function SimulatedPortfolio({
    summary = mockSummary,
    positions = mockPositions,
    onRefresh,
    isLoading = false
}: SimulatedPortfolioProps) {
    const { i18n } = useTranslation();
    const isZh = i18n.language.startsWith('zh');
    const [showAllPositions, setShowAllPositions] = useState(false);

    const displayPositions = showAllPositions ? positions : positions.slice(0, 3);

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(value);
    };

    const formatPercent = (value: number) => {
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    };

    const getStrategyBadge = (strategy: 'BUY' | 'SELL', optionType: 'CALL' | 'PUT') => {
        const strategyKey = `${strategy.toLowerCase()}-${optionType.toLowerCase()}`;
        const labels: Record<string, { zh: string; en: string }> = {
            'sell-put': { zh: '卖出看跌', en: 'Sell Put' },
            'sell-call': { zh: '卖出看涨', en: 'Sell Call' },
            'buy-call': { zh: '买入看涨', en: 'Buy Call' },
            'buy-put': { zh: '买入看跌', en: 'Buy Put' }
        };
        return {
            className: strategyKey,
            label: isZh ? labels[strategyKey].zh : labels[strategyKey].en
        };
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(isZh ? 'zh-CN' : 'en-US', {
            month: 'short',
            day: 'numeric'
        });
    };

    const getDaysToExpiry = (expiry: string) => {
        const today = new Date();
        const expiryDate = new Date(expiry);
        const diffTime = expiryDate.getTime() - today.getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
    };

    return (
        <>
            <style>{componentStyles}</style>

            <div className="portfolio-card">
                {/* Header with Account Summary */}
                <div className="portfolio-header">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-[rgba(13,155,151,0.2)] flex items-center justify-center">
                                <Wallet className="text-[#0D9B97]" size={24} />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white">
                                    {isZh ? '模拟投资组合' : 'Simulated Portfolio'}
                                </h3>
                                <p className="text-sm text-[var(--text-muted)]">
                                    {isZh ? '基于算法推荐的实盘模拟' : 'Live simulation based on algorithm recommendations'}
                                </p>
                            </div>
                        </div>
                        <button
                            className={`refresh-btn ${isLoading ? 'loading' : ''}`}
                            onClick={onRefresh}
                            disabled={isLoading}
                        >
                            <RefreshCw size={16} />
                            {isZh ? '刷新' : 'Refresh'}
                        </button>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        {/* Total Value */}
                        <div className="stat-box">
                            <div className="flex items-center justify-center gap-2 mb-1">
                                <DollarSign size={18} className="text-[#0D9B97]" />
                            </div>
                            <div className="stat-value text-white">
                                {formatCurrency(summary.totalValue)}
                            </div>
                            <div className="stat-label">
                                {isZh ? '账户总值' : 'Total Value'}
                            </div>
                        </div>

                        {/* Total P&L */}
                        <div className="stat-box">
                            <div className="flex items-center justify-center gap-2 mb-1">
                                {summary.totalPnl >= 0 ? (
                                    <TrendingUp size={18} className="text-green-500" />
                                ) : (
                                    <TrendingDown size={18} className="text-red-500" />
                                )}
                            </div>
                            <div className={`stat-value ${summary.totalPnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {formatCurrency(summary.totalPnl)}
                            </div>
                            <div className="stat-label">
                                {isZh ? '总收益' : 'Total P&L'} ({formatPercent(summary.totalPnlPercent)})
                            </div>
                        </div>

                        {/* Day P&L */}
                        <div className="stat-box">
                            <div className="flex items-center justify-center gap-2 mb-1">
                                <Clock size={18} className="text-[var(--text-muted)]" />
                            </div>
                            <div className={`stat-value ${summary.dayPnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {formatCurrency(summary.dayPnl)}
                            </div>
                            <div className="stat-label">
                                {isZh ? '今日收益' : 'Today\'s P&L'} ({formatPercent(summary.dayPnlPercent)})
                            </div>
                        </div>

                        {/* Positions Count */}
                        <div className="stat-box">
                            <div className="flex items-center justify-center gap-2 mb-1">
                                <PieChart size={18} className="text-purple-500" />
                            </div>
                            <div className="stat-value text-white">
                                {positions.length}
                            </div>
                            <div className="stat-label">
                                {isZh ? '持仓数量' : 'Open Positions'}
                            </div>
                        </div>
                    </div>

                    {/* Cash / Positions Breakdown */}
                    <div className="mt-4 flex items-center gap-4 text-sm">
                        <span className="text-[var(--text-muted)]">
                            {isZh ? '现金:' : 'Cash:'} <span className="text-white font-medium">{formatCurrency(summary.cashBalance)}</span>
                        </span>
                        <span className="text-[var(--text-muted)]">|</span>
                        <span className="text-[var(--text-muted)]">
                            {isZh ? '持仓市值:' : 'Positions:'} <span className="text-white font-medium">{formatCurrency(summary.positionsValue)}</span>
                        </span>
                    </div>
                </div>

                {/* Positions Table */}
                <div className="overflow-x-auto">
                    {/* Table Header */}
                    <div className="position-row position-header">
                        <div>{isZh ? '持仓' : 'Position'}</div>
                        <div>{isZh ? '成本/现价' : 'Cost/Current'}</div>
                        <div className="hidden sm:block">{isZh ? '到期日' : 'Expiry'}</div>
                        <div className="hidden sm:block">{isZh ? '数量' : 'Qty'}</div>
                        <div>{isZh ? '盈亏' : 'P&L'}</div>
                    </div>

                    {/* Position Rows */}
                    {displayPositions.map((position) => {
                        const badge = getStrategyBadge(position.strategy, position.optionType);
                        const daysToExpiry = getDaysToExpiry(position.expiry);

                        return (
                            <div key={position.id} className="position-row">
                                {/* Symbol & Strategy */}
                                <div>
                                    <div className="font-bold text-white text-lg">{position.symbol}</div>
                                    <span className={`strategy-badge ${badge.className}`}>
                                        {badge.label}
                                    </span>
                                    <div className="text-xs text-[var(--text-muted)] mt-1">
                                        ${position.strike} {position.optionType}
                                    </div>
                                </div>

                                {/* Cost / Current Price */}
                                <div>
                                    <div className="text-[var(--text-muted)] text-sm">
                                        {isZh ? '成本' : 'Cost'}: ${position.costBasis.toFixed(2)}
                                    </div>
                                    <div className="text-white font-medium">
                                        {isZh ? '现价' : 'Now'}: ${position.currentPrice.toFixed(2)}
                                    </div>
                                    <div className="text-xs text-[var(--text-muted)]">
                                        {isZh ? '股价' : 'Stock'}: ${position.stockPrice.toFixed(2)}
                                    </div>
                                </div>

                                {/* Expiry */}
                                <div className="hidden sm:block">
                                    <div className="text-white">{formatDate(position.expiry)}</div>
                                    <div className={`text-xs ${daysToExpiry <= 7 ? 'text-yellow-500' : 'text-[var(--text-muted)]'}`}>
                                        {daysToExpiry > 0
                                            ? (isZh ? `${daysToExpiry}天后到期` : `${daysToExpiry}d to expiry`)
                                            : (isZh ? '已到期' : 'Expired')
                                        }
                                    </div>
                                </div>

                                {/* Quantity */}
                                <div className="hidden sm:block">
                                    <div className="text-white font-medium">{position.quantity}</div>
                                    <div className="text-xs text-[var(--text-muted)]">
                                        {isZh ? '合约' : 'contracts'}
                                    </div>
                                </div>

                                {/* P&L */}
                                <div>
                                    <div className={`font-bold text-lg ${position.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                        {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                                    </div>
                                    <div className={`text-sm ${position.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                        {formatPercent(position.pnlPercent)}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Show More / Less Button */}
                {positions.length > 3 && (
                    <div className="p-4 border-t border-[rgba(39,39,42,0.5)]">
                        <button
                            onClick={() => setShowAllPositions(!showAllPositions)}
                            className="w-full flex items-center justify-center gap-2 py-2 text-[#0D9B97] hover:text-[#10B5B0] transition-colors text-sm font-medium"
                        >
                            {showAllPositions ? (
                                <>
                                    <ChevronUp size={18} />
                                    {isZh ? '收起' : 'Show Less'}
                                </>
                            ) : (
                                <>
                                    <ChevronDown size={18} />
                                    {isZh ? `查看全部 ${positions.length} 个持仓` : `View All ${positions.length} Positions`}
                                </>
                            )}
                        </button>
                    </div>
                )}

                {/* Footer */}
                <div className="px-6 py-4 bg-[rgba(9,9,11,0.4)] border-t border-[rgba(39,39,42,0.5)]">
                    <div className="flex flex-col sm:flex-row justify-between items-center gap-3 text-xs text-[var(--text-muted)]">
                        <div className="flex items-center gap-2">
                            <span>{isZh ? '初始资金:' : 'Initial Capital:'}</span>
                            <span className="text-white font-medium">{formatCurrency(summary.initialCapital)}</span>
                            <span className="mx-2">|</span>
                            <span>{isZh ? '更新时间:' : 'Last Updated:'}</span>
                            <span className="text-white">
                                {new Date(summary.lastUpdated).toLocaleString(isZh ? 'zh-CN' : 'en-US', {
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </span>
                        </div>
                        <a
                            href="https://www.tigersecurities.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-[#0D9B97] hover:text-[#10B5B0] transition-colors"
                        >
                            <span>{isZh ? '老虎证券模拟账户' : 'Tiger Securities Paper Trading'}</span>
                            <ExternalLink size={12} />
                        </a>
                    </div>
                </div>
            </div>
        </>
    );
}
