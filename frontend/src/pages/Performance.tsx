/**
 * Performance Page - Paper Trading Strategy Performance Display
 *
 * Shows equity curve, KPI metrics, positions, and trade log
 * for the automated paper trading system.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';
import {
    TrendingUp, TrendingDown, DollarSign, BarChart3,
    Target, Clock, RefreshCw, ChevronLeft, ChevronRight,
    Activity
} from 'lucide-react';
import Chart from 'chart.js/auto';
import api from '@/lib/api';

// Types
interface PerformanceData {
    date: string;
    nav: number;
    daily_return: number;
    cumulative_return: number;
    drawdown: number;
    max_drawdown: number;
    benchmark_return: number;
    position_count: number;
    cash_balance: number;
}

interface PerformanceSummary {
    cumulative_return: number;
    annualized_return: number;
    max_drawdown: number;
    sharpe_ratio: number;
    win_rate: number;
    total_trades: number;
    running_days: number;
    account_value: number;
}

interface Position {
    id: number;
    ticker: string;
    security_type: string;
    strategy: string;
    quantity: number;
    avg_cost: number;
    current_price: number | null;
    unrealized_pnl: number | null;
    pnl_pct: number;
    expiry: string | null;
    strike: number | null;
    option_right: string | null;
    stop_loss: number | null;
}

interface Trade {
    id: number;
    timestamp: string;
    ticker: string;
    security_type: string;
    action: string;
    quantity: number;
    price: number;
    strategy: string;
    pnl: number | null;
    notes: string | null;
}

interface TradingStatus {
    engine_running: boolean;
    initial_capital: number;
    account_value: number;
    cash_balance: number;
    open_positions: number;
    total_trades: number;
    last_trade_date: string | null;
    last_performance_date: string | null;
}

export default function Performance() {
    const { t, i18n } = useTranslation();
    const isZh = i18n.language === 'zh';

    const [summary, setSummary] = useState<PerformanceSummary | null>(null);
    const [perfData, setPerfData] = useState<PerformanceData[]>([]);
    const [positions, setPositions] = useState<Position[]>([]);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [status, setStatus] = useState<TradingStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedStrategy, setSelectedStrategy] = useState('combined');
    const [selectedPeriod, setSelectedPeriod] = useState('all');
    const [tradePage, setTradePage] = useState(0);
    const [tradeTotal, setTradeTotal] = useState(0);

    const chartRef = useRef<HTMLCanvasElement>(null);
    const chartInstance = useRef<Chart | null>(null);

    const TRADES_PER_PAGE = 20;

    // Fetch all data
    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [summaryRes, perfRes, posRes, tradeRes, statusRes] = await Promise.all([
                api.get('/trading/performance/summary'),
                api.get(`/trading/performance?strategy=${selectedStrategy}&period=${selectedPeriod}`),
                api.get('/trading/positions'),
                api.get(`/trading/trades?limit=${TRADES_PER_PAGE}&offset=${tradePage * TRADES_PER_PAGE}`),
                api.get('/trading/status'),
            ]);

            if (summaryRes.data.success) setSummary(summaryRes.data);
            if (perfRes.data.success) setPerfData(perfRes.data.data);
            if (posRes.data.success) setPositions(posRes.data.positions);
            if (tradeRes.data.success) {
                setTrades(tradeRes.data.trades);
                setTradeTotal(tradeRes.data.total);
            }
            if (statusRes.data.success) setStatus(statusRes.data);
        } catch (err) {
            console.error('Failed to fetch trading data:', err);
        } finally {
            setLoading(false);
        }
    }, [selectedStrategy, selectedPeriod, tradePage]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Render chart
    useEffect(() => {
        if (!chartRef.current || perfData.length === 0) return;

        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        if (!ctx) return;

        chartInstance.current = new Chart(ctx, {
            type: 'line',
            data: {
                labels: perfData.map(d => d.date),
                datasets: [
                    {
                        label: isZh ? '策略净值' : 'Strategy NAV',
                        data: perfData.map(d => d.nav),
                        borderColor: '#0D9B97',
                        backgroundColor: 'rgba(13, 155, 151, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: isZh ? 'SPY 基准' : 'SPY Benchmark',
                        data: perfData.map(d => 1 + (d.benchmark_return || 0) / 100),
                        borderColor: '#6B7280',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 1.5,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: {
                        labels: { color: '#94A3B8' },
                    },
                    tooltip: {
                        backgroundColor: '#1E293B',
                        titleColor: '#F8FAFC',
                        bodyColor: '#CBD5E1',
                        borderColor: '#334155',
                        borderWidth: 1,
                    },
                },
                scales: {
                    x: {
                        ticks: { color: '#64748B', maxTicksLimit: 10 },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                    },
                    y: {
                        ticks: { color: '#64748B' },
                        grid: { color: 'rgba(255,255,255,0.05)' },
                    },
                },
            },
        });

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
        };
    }, [perfData, isZh]);

    const formatCurrency = (val: number) => `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const formatPct = (val: number) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
    const pnlColor = (val: number) => val >= 0 ? 'text-emerald-400' : 'text-red-400';

    const strategies = [
        { key: 'combined', label: isZh ? '综合' : 'Combined' },
        { key: 'momentum', label: isZh ? '动量' : 'Momentum' },
        { key: 'options_seller', label: isZh ? '期权卖方' : 'Options' },
    ];
    const periods = [
        { key: '1m', label: '1M' },
        { key: '3m', label: '3M' },
        { key: '6m', label: '6M' },
        { key: '1y', label: '1Y' },
        { key: 'all', label: 'All' },
    ];

    return (
        <>
            <Helmet>
                <title>{isZh ? '策略实盘 - AlphaGBM' : 'Performance - AlphaGBM'}</title>
            </Helmet>

            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">
                            {isZh ? 'AI 量化策略模拟盘' : 'AI Quantitative Paper Trading'}
                        </h1>
                        <p className="text-sm text-slate-400 mt-1">
                            {isZh
                                ? '动量选股 + 期权卖方策略 · 自动化模拟交易'
                                : 'Momentum Stock + Options Seller Strategy · Automated Paper Trading'}
                        </p>
                    </div>
                    <button
                        onClick={fetchData}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        {isZh ? '刷新' : 'Refresh'}
                    </button>
                </div>

                {/* Status Bar */}
                {status && (
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full ${status.engine_running ? 'bg-emerald-400' : 'bg-red-400'}`} />
                            {status.engine_running ? (isZh ? '运行中' : 'Running') : (isZh ? '已停止' : 'Stopped')}
                        </span>
                        <span>{isZh ? '持仓' : 'Positions'}: {status.open_positions}</span>
                        <span>{isZh ? '总交易' : 'Trades'}: {status.total_trades}</span>
                        {status.last_trade_date && (
                            <span>{isZh ? '最近交易' : 'Last trade'}: {new Date(status.last_trade_date).toLocaleDateString()}</span>
                        )}
                    </div>
                )}

                {/* KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    <KpiCard
                        icon={<TrendingUp size={16} />}
                        label={isZh ? '累计收益' : 'Total Return'}
                        value={summary ? formatPct(summary.cumulative_return) : '--'}
                        color={summary && summary.cumulative_return >= 0 ? 'emerald' : 'red'}
                    />
                    <KpiCard
                        icon={<BarChart3 size={16} />}
                        label={isZh ? '年化收益' : 'Annualized'}
                        value={summary ? formatPct(summary.annualized_return) : '--'}
                        color={summary && summary.annualized_return >= 0 ? 'emerald' : 'red'}
                    />
                    <KpiCard
                        icon={<TrendingDown size={16} />}
                        label={isZh ? '最大回撤' : 'Max Drawdown'}
                        value={summary ? formatPct(summary.max_drawdown) : '--'}
                        color="red"
                    />
                    <KpiCard
                        icon={<Activity size={16} />}
                        label={isZh ? 'Sharpe' : 'Sharpe Ratio'}
                        value={summary ? summary.sharpe_ratio.toFixed(2) : '--'}
                        color="blue"
                    />
                    <KpiCard
                        icon={<Target size={16} />}
                        label={isZh ? '胜率' : 'Win Rate'}
                        value={summary ? `${summary.win_rate.toFixed(1)}%` : '--'}
                        color="amber"
                    />
                    <KpiCard
                        icon={<DollarSign size={16} />}
                        label={isZh ? '账户价值' : 'Account Value'}
                        value={summary ? formatCurrency(summary.account_value) : '--'}
                        color="slate"
                    />
                </div>

                {/* Equity Curve */}
                <div className="bg-slate-900/50 border border-white/10 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-semibold">{isZh ? '净值曲线' : 'Equity Curve'}</h2>
                        <div className="flex items-center gap-2">
                            {/* Strategy toggle */}
                            <div className="flex bg-slate-800 rounded-lg p-0.5">
                                {strategies.map(s => (
                                    <button
                                        key={s.key}
                                        onClick={() => setSelectedStrategy(s.key)}
                                        className={`px-3 py-1 text-xs rounded-md transition-colors ${selectedStrategy === s.key ? 'bg-[#0D9B97] text-white' : 'text-slate-400 hover:text-slate-200'}`}
                                    >
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                            {/* Period toggle */}
                            <div className="flex bg-slate-800 rounded-lg p-0.5">
                                {periods.map(p => (
                                    <button
                                        key={p.key}
                                        onClick={() => setSelectedPeriod(p.key)}
                                        className={`px-2 py-1 text-xs rounded-md transition-colors ${selectedPeriod === p.key ? 'bg-slate-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                                    >
                                        {p.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                    <div className="h-[300px]">
                        {perfData.length > 0 ? (
                            <canvas ref={chartRef} />
                        ) : (
                            <div className="flex items-center justify-center h-full text-slate-500 text-sm">
                                {loading ? (isZh ? '加载中...' : 'Loading...') : (isZh ? '暂无数据，等待首次交易执行' : 'No data yet. Waiting for first trade execution.')}
                            </div>
                        )}
                    </div>
                </div>

                {/* Positions & Trades Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Current Positions */}
                    <div className="bg-slate-900/50 border border-white/10 rounded-xl p-4">
                        <h2 className="text-sm font-semibold mb-3">
                            {isZh ? '当前持仓' : 'Current Positions'} ({positions.length})
                        </h2>
                        {positions.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr className="text-slate-500 border-b border-white/5">
                                            <th className="text-left py-2 pr-2">{isZh ? '标的' : 'Ticker'}</th>
                                            <th className="text-left py-2 pr-2">{isZh ? '策略' : 'Strategy'}</th>
                                            <th className="text-right py-2 pr-2">{isZh ? '数量' : 'Qty'}</th>
                                            <th className="text-right py-2 pr-2">{isZh ? '成本' : 'Cost'}</th>
                                            <th className="text-right py-2 pr-2">{isZh ? '现价' : 'Price'}</th>
                                            <th className="text-right py-2">{isZh ? '盈亏%' : 'P&L%'}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {positions.map(p => (
                                            <tr key={p.id} className="border-b border-white/5 hover:bg-white/5">
                                                <td className="py-2 pr-2 font-medium">
                                                    {p.ticker}
                                                    {p.security_type === 'OPTION' && (
                                                        <span className="text-slate-500 ml-1">
                                                            {p.strike}{p.option_right?.[0]}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="py-2 pr-2">
                                                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${p.strategy === 'momentum' ? 'bg-blue-500/20 text-blue-300' : 'bg-purple-500/20 text-purple-300'}`}>
                                                        {p.strategy === 'momentum' ? (isZh ? '动量' : 'MOM') : (isZh ? '期权' : 'OPT')}
                                                    </span>
                                                </td>
                                                <td className="py-2 pr-2 text-right">{p.quantity}</td>
                                                <td className="py-2 pr-2 text-right">${p.avg_cost.toFixed(2)}</td>
                                                <td className="py-2 pr-2 text-right">{p.current_price ? `$${p.current_price.toFixed(2)}` : '--'}</td>
                                                <td className={`py-2 text-right font-medium ${pnlColor(p.pnl_pct)}`}>
                                                    {formatPct(p.pnl_pct)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-8">
                                {isZh ? '暂无持仓' : 'No open positions'}
                            </p>
                        )}
                    </div>

                    {/* Trade Log */}
                    <div className="bg-slate-900/50 border border-white/10 rounded-xl p-4">
                        <h2 className="text-sm font-semibold mb-3">
                            {isZh ? '交易记录' : 'Trade Log'} ({tradeTotal})
                        </h2>
                        {trades.length > 0 ? (
                            <>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs">
                                        <thead>
                                            <tr className="text-slate-500 border-b border-white/5">
                                                <th className="text-left py-2 pr-2">{isZh ? '时间' : 'Date'}</th>
                                                <th className="text-left py-2 pr-2">{isZh ? '标的' : 'Ticker'}</th>
                                                <th className="text-left py-2 pr-2">{isZh ? '操作' : 'Action'}</th>
                                                <th className="text-right py-2 pr-2">{isZh ? '数量' : 'Qty'}</th>
                                                <th className="text-right py-2 pr-2">{isZh ? '价格' : 'Price'}</th>
                                                <th className="text-right py-2">{isZh ? '盈亏' : 'P&L'}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {trades.map(t => (
                                                <tr key={t.id} className="border-b border-white/5 hover:bg-white/5">
                                                    <td className="py-2 pr-2 text-slate-400">
                                                        {new Date(t.timestamp).toLocaleDateString()}
                                                    </td>
                                                    <td className="py-2 pr-2 font-medium">{t.ticker}</td>
                                                    <td className="py-2 pr-2">
                                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${t.action === 'BUY' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                                                            {t.action}
                                                        </span>
                                                    </td>
                                                    <td className="py-2 pr-2 text-right">{t.quantity}</td>
                                                    <td className="py-2 pr-2 text-right">${t.price.toFixed(2)}</td>
                                                    <td className={`py-2 text-right ${t.pnl !== null ? pnlColor(t.pnl) : 'text-slate-500'}`}>
                                                        {t.pnl !== null ? formatCurrency(t.pnl) : '--'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                {/* Pagination */}
                                {tradeTotal > TRADES_PER_PAGE && (
                                    <div className="flex items-center justify-center gap-4 mt-3">
                                        <button
                                            onClick={() => setTradePage(p => Math.max(0, p - 1))}
                                            disabled={tradePage === 0}
                                            className="p-1 rounded hover:bg-slate-700 disabled:opacity-30"
                                        >
                                            <ChevronLeft size={16} />
                                        </button>
                                        <span className="text-xs text-slate-400">
                                            {tradePage + 1} / {Math.ceil(tradeTotal / TRADES_PER_PAGE)}
                                        </span>
                                        <button
                                            onClick={() => setTradePage(p => p + 1)}
                                            disabled={(tradePage + 1) * TRADES_PER_PAGE >= tradeTotal}
                                            className="p-1 rounded hover:bg-slate-700 disabled:opacity-30"
                                        >
                                            <ChevronRight size={16} />
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-8">
                                {isZh ? '暂无交易记录' : 'No trades yet'}
                            </p>
                        )}
                    </div>
                </div>

                {/* Disclaimer */}
                <div className="text-center text-[10px] text-slate-600 py-4">
                    {isZh
                        ? '* 模拟盘数据仅供参考，不构成投资建议。历史收益不代表未来表现。初始资金 $100,000。'
                        : '* Paper trading results are for reference only and do not constitute investment advice. Past performance does not guarantee future results. Starting capital: $100,000.'}
                </div>
            </div>
        </>
    );
}

// KPI Card Component
function KpiCard({ icon, label, value, color }: {
    icon: React.ReactNode;
    label: string;
    value: string;
    color: string;
}) {
    const colorMap: Record<string, string> = {
        emerald: 'text-emerald-400',
        red: 'text-red-400',
        blue: 'text-blue-400',
        amber: 'text-amber-400',
        slate: 'text-slate-300',
    };

    return (
        <div className="bg-slate-900/50 border border-white/10 rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-slate-500 mb-1">
                {icon}
                <span className="text-[10px] font-medium uppercase tracking-wider">{label}</span>
            </div>
            <p className={`text-lg font-bold ${colorMap[color] || 'text-slate-300'}`}>
                {value}
            </p>
        </div>
    );
}
