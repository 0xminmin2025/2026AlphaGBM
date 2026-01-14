import { useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useNavigate } from 'react-router-dom';
import OptionsAnalysisHistory from '@/components/OptionsAnalysisHistory';
import HistoryStorage from '@/lib/historyStorage';
import { useTaskPolling } from '@/hooks/useTaskPolling';

// CSS matching original options.html
const styles = `
    :root {
        --bull: #10B981;
        --bear: #EF4444;
        --warning: hsl(38, 92%, 50%);
        --primary: hsl(178, 78%, 32%);
        --card: hsl(240, 6%, 10%);
        --border: hsl(240, 3.7%, 15.9%);
        --muted: hsl(240, 3.7%, 15.9%);
        --muted-foreground: hsl(240, 5%, 64.9%);
        --foreground: hsl(0, 0%, 98%);
    }

    .card {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
    }

    .header-section {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    @media (min-width: 640px) {
        .header-section {
            padding: 2rem;
            margin-bottom: 2rem;
        }
    }

    .controls-section {
        padding: 1rem;
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        margin-bottom: 1rem;
    }

    @media (min-width: 640px) {
        .controls-section {
            padding: 1.5rem;
        }
    }

    .option-col-section {
        background-color: var(--card);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        padding: 1rem;
        overflow: hidden;
    }

    .header-calls {
        background-color: var(--bull);
        color: white;
        padding: 0.5rem;
        text-align: center;
        border-radius: 0.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }

    .header-puts {
        background-color: var(--bear);
        color: white;
        padding: 0.5rem;
        text-align: center;
        border-radius: 0.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }

    .option-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }

    .table-container {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }

    @media (max-width: 640px) {
        .option-table {
            font-size: 0.75rem;
        }

        .option-table th,
        .option-table td {
            padding: 0.5rem 0.25rem;
            min-width: 60px;
        }
    }

    .option-table th {
        background-color: var(--muted);
        position: sticky;
        top: 0;
        z-index: 10;
        padding: 0.75rem 0.5rem;
        text-align: center;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--foreground);
    }

    .option-table td {
        padding: 0.75rem 0.5rem;
        text-align: center;
        border-bottom: 1px solid var(--border);
        font-size: 0.875rem;
        color: var(--foreground);
    }

    .option-table tbody tr:hover {
        background-color: rgba(13, 155, 151, 0.1);
        cursor: pointer;
    }

    .score-badge {
        font-weight: 600;
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        display: inline-block;
        min-width: 40px;
    }

    .score-high { background-color: var(--bull); color: white; }
    .score-medium { background-color: var(--warning); color: white; }
    .score-low { background-color: var(--bear); color: white; }

    .recommended-row {
        background-color: rgba(13, 155, 151, 0.2) !important;
        border-left: 3px solid var(--primary);
    }

    .strategy-btn {
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        border: 1px solid var(--border);
        background: var(--muted);
        color: var(--foreground);
        cursor: pointer;
        transition: all 0.2s;
    }

    .strategy-btn:hover { background: var(--primary); color: white; }
    .strategy-btn.active { background: var(--primary); color: white; border-color: var(--primary); }

    .form-control, .form-select {
        background: var(--muted);
        border: 1px solid var(--border);
        color: var(--foreground);
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
    }

    .form-control:focus, .form-select:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(13, 155, 151, 0.2);
        outline: none;
    }

    .btn-primary {
        background: var(--primary);
        border: none;
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        font-weight: 600;
    }

    .btn-primary:hover { filter: brightness(1.1); }
    .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

    .btn-outline {
        background: transparent;
        border: 1px solid var(--border);
        color: var(--foreground);
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
    }

    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 1s ease-in-out infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
`;

type OptionData = {
    identifier: string;
    strike: number;
    latest_price: number;
    bid_price: number;
    ask_price: number;
    volume: number;
    open_interest: number;
    implied_vol: number;
    delta: number;
    gamma?: number;
    theta?: number;
    vega?: number;
    put_call: string;
    expiry_date: string;
    scores?: {
        total_score?: number;
        annualized_return?: number;
        assignment_probability?: number;
        liquidity_factor?: number;
        sprv?: number;
        scrv?: number;
        bcrv?: number;
        bprv?: number;
        iv_rank?: number;
    };
};

type ExpirationDate = {
    date: string;
    period_tag?: string;
};

type OptionChainResponse = {
    symbol: string;
    expiry_date: string;
    calls: OptionData[];
    puts: OptionData[];
    real_stock_price?: number;
    data_source?: string;
};

// Strategy types
type Strategy = 'sell_put' | 'buy_put' | 'sell_call' | 'buy_call';

const strategyLabels: Record<Strategy, string> = {
    'sell_put': 'Sell Put',
    'buy_put': 'Buy Put',
    'sell_call': 'Sell Call',
    'buy_call': 'Buy Call'
};

export default function Options() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    const [ticker, setTicker] = useState('AAPL');
    const [expirations, setExpirations] = useState<ExpirationDate[]>([]);
    const [selectedExpiry, setSelectedExpiry] = useState('');
    const [chain, setChain] = useState<OptionChainResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [expirationsLoading, setExpirationsLoading] = useState(false);
    const [error, setError] = useState('');
    const [strategy, setStrategy] = useState<Strategy>('sell_put');
    const [stockPrice, setStockPrice] = useState<number | null>(null);
    const [activeTab, setActiveTab] = useState('analysis');
    const [historicalChain, setHistoricalChain] = useState<OptionChainResponse | null>(null);
    const [isHistoricalView, setIsHistoricalView] = useState(false);

    // Task progress state
    const [taskProgress, setTaskProgress] = useState(0);
    const [taskStep, setTaskStep] = useState('');

    // Initialize task polling hook
    const { startPolling } = useTaskPolling({
        onTaskComplete: (taskResult) => {
            console.log('Options task completed:', taskResult);
            setChain(taskResult);
            if (taskResult.real_stock_price) {
                setStockPrice(taskResult.real_stock_price);
            }
            setLoading(false);
            setTaskProgress(100);
            setTaskStep('期权分析完成！');

            // Save to browser history
            HistoryStorage.saveOptionAnalysis({
                symbol: ticker,
                expiryDate: selectedExpiry,
                analysisType: 'chain',
                data: taskResult
            });
        },
        onTaskError: (errorMsg) => {
            console.error('Options task failed:', errorMsg);
            setError(errorMsg);
            setLoading(false);
            setTaskProgress(0);
            setTaskStep('');
        },
        onTaskProgress: (progress, step) => {
            setTaskProgress(progress);
            setTaskStep(step);
        }
    });

    // Fetch Expirations
    const fetchExpirations = async () => {
        if (!ticker) {
            setError('请输入股票代码');
            return;
        }
        setExpirationsLoading(true);
        setError('');
        setExpirations([]);
        setSelectedExpiry('');
        setChain(null);

        try {
            const response = await api.get(`/options/expirations/${ticker}`);
            setExpirations(response.data.expirations || []);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.error || 'Failed to fetch expirations');
        } finally {
            setExpirationsLoading(false);
        }
    };

    // Fetch Chain
    const fetchChain = async (expiry: string) => {
        if (!ticker || !expiry) return;
        setLoading(true);
        setError('');
        setTaskProgress(0);
        setTaskStep('');

        // Clear historical view when fetching new data
        setIsHistoricalView(false);
        setHistoricalChain(null);

        try {
            // Create async task for options chain analysis
            const response = await api.post(`/options/chain/${ticker}/${expiry}`, {
                async: true // Use async mode
            });

            if (response.data.success && response.data.task_id) {
                console.log('Options task created:', response.data.task_id);
                setTaskStep('任务已创建，开始期权分析...');

                // Start polling for task status
                startPolling(response.data.task_id);
            } else {
                setError(response.data.error || 'Failed to create options analysis task');
                setLoading(false);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.error || 'Failed to start options analysis');
            setLoading(false);
        }
    };

    // When expiry selected, fetch chain
    const handleExpirySelect = (expiry: string) => {
        setSelectedExpiry(expiry);
        fetchChain(expiry);
    };

    // Get the appropriate score based on strategy
    const getOptionScore = (opt: OptionData): number => {
        if (!opt.scores) return 0;
        switch (strategy) {
            case 'sell_put': return (opt.scores.sprv || 0) * 100; // Normalize to 0-100 scale
            case 'buy_put': return (opt.scores.bprv || 0) * 100;
            case 'sell_call': return (opt.scores.scrv || 0) * 100;
            case 'buy_call': return (opt.scores.bcrv || 0) * 100;
            default: return 0;
        }
    };

    // Filter and sort options based on strategy
    const getFilteredOptions = (): OptionData[] => {
        if (!displayChain) {
            console.log('No chain data');
            return [];
        }

        console.log('Chain:', displayChain);
        console.log('Calls array:', displayChain.calls);
        console.log('Puts array:', displayChain.puts);

        let options: OptionData[] = [];

        if (strategy === 'sell_put' || strategy === 'buy_put') {
            options = Array.isArray(displayChain.puts) ? [...displayChain.puts] : [];
        } else {
            options = Array.isArray(displayChain.calls) ? [...displayChain.calls] : [];
        }

        console.log('Filtered options:', options.length);

        // Sort by score (highest first)
        options.sort((a, b) => {
            const scoreA = getOptionScore(a);
            const scoreB = getOptionScore(b);
            return scoreB - scoreA;
        });

        return options;
    };

    const getScoreClass = (score: number) => {
        if (score >= 60) return 'score-high';
        if (score >= 40) return 'score-medium';
        return 'score-low';
    };

    const formatNumber = (num: number | undefined | null, decimals = 2) => {
        return (num !== undefined && num !== null) ? num.toFixed(decimals) : '-';
    };

    const formatPercent = (num: number | undefined | null, decimals = 1) => {
        return (num !== undefined && num !== null) ? `${(num * 100).toFixed(decimals)}%` : '-';
    };

    if (authLoading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="spinner"></div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 text-white">
                <h2 className="text-2xl font-bold">请登录以访问期权分析</h2>
                <Button onClick={() => navigate('/login')} className="btn-primary">
                    登录
                </Button>
            </div>
        );
    }

    // Use historical chain data if viewing history, otherwise use current chain
    const displayChain = isHistoricalView ? historicalChain : chain;
    const displayStockPrice = isHistoricalView ? (historicalChain?.real_stock_price || stockPrice) : stockPrice;

    const filteredOptions = getFilteredOptions();
    const topRecommendations = filteredOptions.filter(o => getOptionScore(o) >= 60).slice(0, 5);

    return (
        <div className="animate-in fade-in" style={{ color: 'var(--foreground)' }}>
            <style>{styles}</style>

            {/* Custom Tabs */}
            <div className="card" style={{ padding: '0', marginBottom: '2rem' }}>
                <div className="flex border-b" style={{ borderColor: 'var(--border)' }}>
                    <button
                        onClick={() => setActiveTab('analysis')}
                        className={`flex-1 px-6 py-3 text-center font-medium transition-all duration-200 ${
                            activeTab === 'analysis'
                                ? 'border-b-2'
                                : 'hover:bg-opacity-10'
                        }`}
                        style={{
                            borderBottomColor: activeTab === 'analysis' ? 'var(--primary)' : 'transparent',
                            background: 'none',
                            border: 'none',
                            borderBottomWidth: '2px',
                            borderBottomStyle: 'solid',
                            fontSize: '1rem',
                            color: activeTab === 'analysis' ? 'var(--primary)' : 'var(--muted-foreground)'
                        }}
                    >
                        <i className="bi bi-graph-up mr-2"></i>
                        期权分析
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex-1 px-6 py-3 text-center font-medium transition-all duration-200 ${
                            activeTab === 'history'
                                ? 'border-b-2'
                                : 'hover:bg-opacity-10'
                        }`}
                        style={{
                            borderBottomColor: activeTab === 'history' ? 'var(--primary)' : 'transparent',
                            background: 'none',
                            border: 'none',
                            borderBottomWidth: '2px',
                            borderBottomStyle: 'solid',
                            fontSize: '1rem',
                            color: activeTab === 'history' ? 'var(--primary)' : 'var(--muted-foreground)'
                        }}
                    >
                        <i className="bi bi-clock-history mr-2"></i>
                        分析历史
                    </button>
                </div>
            </div>

            {/* Options Analysis Tab */}
            <div style={{ display: activeTab === 'analysis' ? 'block' : 'none' }}>
                    {/* Header */}
                    <div className="header-section">
                        <h1 style={{ fontSize: '2rem', fontWeight: 600, marginBottom: '0.5rem' }}>期权智能分析</h1>
                        <p style={{ color: 'var(--muted-foreground)' }}>基于 G = B + M 模型与波动率曲面的期权策略扫描</p>
                    </div>

            {/* Error Alert */}
            {error && (
                <div className="mb-4 p-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--bear)', color: 'var(--bear)' }}>
                    {error}
                </div>
            )}

            {/* Controls */}
            <div className="controls-section">
                <div className="flex flex-col sm:flex-row flex-wrap gap-4 items-stretch sm:items-end">
                    <div className="flex-1 min-w-[200px]">
                        <label className="block mb-2" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem' }}>股票代码 (Symbol)</label>
                        <div className="flex gap-2">
                            <Input
                                type="text"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                placeholder="如 AAPL, NVDA"
                                className="form-control flex-1"
                            />
                            <Button onClick={fetchExpirations} disabled={expirationsLoading} className="btn-primary">
                                <i className="bi bi-arrow-clockwise mr-2"></i>
                                {expirationsLoading ? '加载中...' : '加载日期'}
                            </Button>
                        </div>
                    </div>

                    <div className="flex-1 min-w-[200px]">
                        <label className="block mb-2" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem' }}>到期日 (Expiration)</label>
                        <select
                            value={selectedExpiry}
                            onChange={(e) => handleExpirySelect(e.target.value)}
                            className="form-select w-full"
                            disabled={expirations.length === 0}
                        >
                            <option value="">{expirations.length > 0 ? '请选择到期日' : '请先加载日期'}</option>
                            {expirations.map(exp => (
                                <option key={exp.date} value={exp.date}>
                                    {exp.date} {exp.period_tag === 'm' ? '(月权)' : '(周权)'}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Strategy Selector */}
                <div className="mt-6 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
                    <label className="block mb-3" style={{ color: 'var(--foreground)', fontSize: '1rem', fontWeight: 600 }}>
                        选择策略
                    </label>
                    <div className="grid grid-cols-2 sm:flex gap-2 sm:gap-3 flex-wrap">
                        {(Object.keys(strategyLabels) as Strategy[]).map(s => (
                            <button
                                key={s}
                                className={`strategy-btn ${strategy === s ? 'active' : ''}`}
                                onClick={() => setStrategy(s)}
                            >
                                {strategyLabels[s]}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Loading with Progress */}
            {loading && (
                <div className="text-center py-12">
                    <div className="spinner mx-auto mb-4"></div>
                    {/* Progress Bar */}
                    {taskProgress > 0 && (
                        <div className="max-w-md mx-auto mb-4">
                            <div className="flex justify-between text-sm mb-1">
                                <span style={{ color: 'var(--muted-foreground)' }}>分析进度</span>
                                <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{taskProgress}%</span>
                            </div>
                            <div style={{
                                width: '100%',
                                backgroundColor: 'var(--muted)',
                                borderRadius: '8px',
                                height: '8px',
                                overflow: 'hidden'
                            }}>
                                <div style={{
                                    width: `${taskProgress}%`,
                                    backgroundColor: 'var(--primary)',
                                    height: '100%',
                                    borderRadius: '8px',
                                    transition: 'width 0.3s ease-in-out'
                                }}></div>
                            </div>
                        </div>
                    )}
                    {/* Task Step */}
                    {taskStep && (
                        <p style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                            {taskStep}
                        </p>
                    )}
                    {!taskStep && (
                        <p style={{ color: 'var(--muted-foreground)' }}>正在获取期权数据并进行量化评分...</p>
                    )}
                </div>
            )}

            {/* Historical Analysis Indicator */}
            {isHistoricalView && historicalChain && (
                <div className="card shadow-lg mb-4" style={{
                    padding: '1rem 1.5rem',
                    background: 'linear-gradient(135deg, rgba(13, 155, 151, 0.1) 0%, rgba(13, 155, 151, 0.05) 100%)',
                    border: '1px solid rgba(13, 155, 151, 0.3)'
                }}>
                    <div className="flex items-center gap-3">
                        <i className="bi bi-clock-history text-primary" style={{ fontSize: '1.2rem' }}></i>
                        <div>
                            <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '1rem' }}>
                                历史期权分析报告
                            </span>
                            <span className="text-muted ml-3" style={{ fontSize: '0.9rem' }}>
                                查看历史数据
                            </span>
                        </div>
                        <div className="ml-auto">
                            <span className="badge-primary">
                                <i className="bi bi-archive mr-1"></i>
                                历史数据
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* Results */}
            {displayChain && !loading && (
                <div className="space-y-6">
                    {/* Results Header */}
                    <div className="card p-4">
                        <div className="flex justify-between items-center mb-4">
                            <div>
                                <h2 style={{ fontSize: '1.3rem', fontWeight: 600 }}>
                                    分析结果: <span style={{ color: 'var(--primary)' }}>{displayChain.symbol}</span>
                                </h2>
                                <div style={{ color: 'var(--muted-foreground)', marginTop: '0.5rem' }}>
                                    当前价格: <span style={{ fontWeight: 600, color: 'var(--foreground)' }}>${displayStockPrice?.toFixed(2) || '-'}</span>
                                    <span className="mx-3">|</span>
                                    到期日: <span style={{ fontWeight: 600, color: 'var(--foreground)' }}>{displayChain.expiry_date || selectedExpiry}</span>
                                    <span className="mx-3">|</span>
                                    策略: <span style={{ fontWeight: 600, color: 'var(--primary)' }}>{strategyLabels[strategy]}</span>
                                    {isHistoricalView && (
                                        <>
                                            <span className="mx-3">|</span>
                                            <span style={{ color: 'var(--primary)', fontWeight: 600 }}>历史数据</span>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Top Recommendations */}
                    {topRecommendations.length > 0 && (
                        <div className="card p-4">
                            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: 'var(--primary)' }}>
                                <i className="bi bi-star-fill mr-2"></i>
                                高评分推荐 (Score ≥ 60)
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
                                {topRecommendations.map(opt => (
                                    <div
                                        key={opt.identifier}
                                        className="p-4 rounded cursor-pointer transition-all hover:scale-105"
                                        style={{
                                            backgroundColor: 'rgba(13, 155, 151, 0.15)',
                                            border: '1px solid var(--primary)'
                                        }}
                                    >
                                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                                            ${opt.strike}
                                        </div>
                                        <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                            {opt.put_call}
                                        </div>
                                        <div className="flex justify-between mt-2">
                                            <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>Score</span>
                                            <span className={`score-badge ${getScoreClass(getOptionScore(opt))}`}>
                                                {getOptionScore(opt).toFixed(1)}
                                            </span>
                                        </div>
                                        <div className="flex justify-between mt-1">
                                            <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>年化收益</span>
                                            <span style={{ color: 'var(--bull)', fontWeight: 600, fontSize: '0.9rem' }}>
                                                {opt.scores?.annualized_return?.toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Options Table */}
                    <div className="option-col-section">
                        <div className={strategy.includes('call') ? 'header-calls' : 'header-puts'}>
                            {strategy.includes('call') ? 'CALLS (看涨)' : 'PUTS (看跌)'} - {strategyLabels[strategy]}
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                            <div className="table-container">
                                <table className="option-table">
                                <thead>
                                    <tr>
                                        <th>Strike</th>
                                        <th>Latest</th>
                                        <th>Bid/Ask</th>
                                        <th>Vol/OI</th>
                                        <th>IV</th>
                                        <th>Delta</th>
                                        <th>年化收益</th>
                                        <th>评分</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredOptions.length === 0 ? (
                                        <tr>
                                            <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted-foreground)' }}>
                                                没有符合条件的期权数据
                                            </td>
                                        </tr>
                                    ) : (
                                        filteredOptions.map(opt => {
                                            const totalScore = getOptionScore(opt);
                                            const isRecommended = totalScore >= 60;

                                            return (
                                                <tr
                                                    key={opt.identifier}
                                                    className={isRecommended ? 'recommended-row' : ''}
                                                >
                                                    <td style={{ fontWeight: 600 }}>${opt.strike}</td>
                                                    <td>${formatNumber(opt.latest_price)}</td>
                                                    <td><small>${formatNumber(opt.bid_price)} / ${formatNumber(opt.ask_price)}</small></td>
                                                    <td><small>{opt.volume} / {opt.open_interest}</small></td>
                                                    <td>{formatPercent(opt.implied_vol)}</td>
                                                    <td>{formatNumber(opt.delta, 3)}</td>
                                                    <td style={{ color: totalScore >= 50 ? 'var(--bull)' : 'inherit', fontWeight: totalScore >= 50 ? 600 : 400 }}>
                                                        {opt.scores?.annualized_return?.toFixed(1)}%
                                                    </td>
                                                    <td>
                                                        <span className={`score-badge ${getScoreClass(totalScore)}`}>
                                                            {totalScore.toFixed(1)}
                                                        </span>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!displayChain && !loading && (
                <div className="text-center py-20" style={{ color: 'var(--muted-foreground)' }}>
                    <i className="bi bi-graph-down text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
                    <p>输入股票代码，加载日期，选择到期日开始分析</p>
                </div>
            )}
            </div>

            {/* Analysis History Tab - Always Mounted but Hidden when Not Active */}
            <div style={{ display: activeTab === 'history' ? 'block' : 'none' }}>
                <OptionsAnalysisHistory
                    onSelectHistory={(symbol, _analysisType, _optionIdentifier, expiryDate) => {
                        setTicker(symbol);
                        setActiveTab('analysis');
                        // Try to load the expiry date if it matches available expirations
                        if (expiryDate && expirations.find(exp => exp.date === expiryDate)) {
                            setSelectedExpiry(expiryDate);
                            fetchChain(expiryDate);
                        }
                    }}
                    onViewFullReport={(optionData) => {
                        // Display historical option analysis data directly
                        console.log('Displaying historical options analysis:', optionData);
                        setHistoricalChain(optionData.data);
                        setIsHistoricalView(true);
                        setActiveTab('analysis');
                        // Extract ticker and other info from historical data
                        const symbol = optionData.history_metadata?.symbol;
                        const expiryDate = optionData.history_metadata?.expiry_date;
                        if (symbol) {
                            setTicker(symbol);
                        }
                        if (expiryDate) {
                            setSelectedExpiry(expiryDate);
                        }
                        if (optionData.data?.real_stock_price) {
                            setStockPrice(optionData.data.real_stock_price);
                        }
                        // Scroll to the top to show the analysis
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    symbolFilter={ticker}
                />
            </div>
        </div>
    );
}
