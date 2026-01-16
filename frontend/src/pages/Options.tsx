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
        transition: background-color 0.2s;
    }

    .option-table th:hover {
        background-color: rgba(13, 155, 151, 0.2);
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
        padding: 0.4rem 0.8rem;
        border-radius: 0.375rem;
        border: 1px solid var(--border);
        background: var(--muted);
        color: var(--foreground);
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.875rem;
        font-weight: 500;
        white-space: nowrap;
    }

    .strategy-btn:hover { 
        background: var(--primary); 
        color: white; 
        border-color: var(--primary);
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(13, 155, 151, 0.2);
    }
    .strategy-btn.active { 
        background: var(--primary); 
        color: white; 
        border-color: var(--primary);
        box-shadow: 0 2px 6px rgba(13, 155, 151, 0.3);
    }

    .form-control, .form-select {
        background: var(--muted);
        border: 1px solid var(--border);
        color: var(--foreground);
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
    }

    .form-control::placeholder {
        color: var(--muted-foreground);
        opacity: 0.7;
    }

    .form-control:focus, .form-select:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(13, 155, 151, 0.2);
        outline: none;
    }

    .philosophy-card {
        background: var(--card);
        border: 1px solid var(--primary);
        border-radius: 8px;
    }

    .philosophy-formula {
        display: inline-block;
        background: var(--primary);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        margin: 0 0.25rem;
    }

    .philosophy-formula.bull { background: var(--bull); }
    .philosophy-formula.warning { background: var(--warning); }

    .pillar-item {
        background: var(--muted);
        border-left: 3px solid var(--primary);
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        transition: all 0.2s;
    }

    .pillar-item:hover {
        background: var(--card-hover);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }

    .style-badge {
        background: var(--muted);
        border: 1px solid var(--border);
        padding: 0.4rem 0.9rem;
        border-radius: 24px;
        font-size: 0.8rem;
        text-align: center;
        transition: all 0.2s;
    }

    .style-badge:hover {
        border-color: var(--primary);
        background: rgba(13, 155, 151, 0.1);
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
    'sell_put': 'Sell Put (卖出看跌)',
    'buy_put': 'Buy Put (买入看跌)',
    'sell_call': 'Sell Call (卖出看涨)',
    'buy_call': 'Buy Call (买入看涨)'
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

    // Sorting state
    const [sortColumn, setSortColumn] = useState<string>('score');
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

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
        // 选择到期日后立即运行分析（此时策略和股票代码都已选择）
        if (expiry && strategy && ticker) {
            fetchChain(expiry);
        }
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

        // Sort based on selected column and direction
        options.sort((a, b) => {
            let valueA: number | null = null;
            let valueB: number | null = null;

            switch (sortColumn) {
                case 'strike':
                    valueA = a.strike;
                    valueB = b.strike;
                    break;
                case 'latest':
                    valueA = a.latest_price || 0;
                    valueB = b.latest_price || 0;
                    break;
                case 'bid':
                    valueA = a.bid_price || 0;
                    valueB = b.bid_price || 0;
                    break;
                case 'ask':
                    valueA = a.ask_price || 0;
                    valueB = b.ask_price || 0;
                    break;
                case 'volume':
                    valueA = a.volume || 0;
                    valueB = b.volume || 0;
                    break;
                case 'open_interest':
                    valueA = a.open_interest || 0;
                    valueB = b.open_interest || 0;
                    break;
                case 'iv':
                    valueA = a.implied_vol || 0;
                    valueB = b.implied_vol || 0;
                    break;
                case 'delta':
                    valueA = a.delta || 0;
                    valueB = b.delta || 0;
                    break;
                case 'annualized_return':
                    valueA = a.scores?.annualized_return || 0;
                    valueB = b.scores?.annualized_return || 0;
                    break;
                case 'score':
                default:
                    valueA = getOptionScore(a);
                    valueB = getOptionScore(b);
                    break;
            }

            if (valueA === null && valueB === null) return 0;
            if (valueA === null) return 1;
            if (valueB === null) return -1;

            const diff = valueA - valueB;
            return sortDirection === 'asc' ? diff : -diff;
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

    // Handle column header click for sorting
    const handleSort = (column: string) => {
        if (sortColumn === column) {
            // Toggle direction if clicking the same column
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            // Set new column and default to descending
            setSortColumn(column);
            setSortDirection('desc');
        }
    };

    // Get sort indicator for table header
    const getSortIndicator = (column: string) => {
        if (sortColumn !== column) return null;
        return sortDirection === 'asc' ? ' ↑' : ' ↓';
    };

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
            {/* Error Alert */}
            {error && (
                <div className="mb-4 p-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--bear)', color: 'var(--bear)' }}>
                    {error}
                </div>
            )}

            {/* Controls */}
            <div className="controls-section">
                <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
                    <i className="bi bi-graph-up"></i>
                    期权智能分析
                </h5>

                {/* Step 1: 选择股票代码 - 占一行 */}
                <div className="mb-4 flex items-center gap-3">
                    <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                        <span style={{ color: ticker ? 'var(--primary)' : 'var(--muted-foreground)' }}>步骤1：</span> 录入股票代码（Symbol)
                    </label>
                    <Input
                        type="text"
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        placeholder="如 AAPL, NVDA"
                        className="form-control flex-1"
                    />
                </div>

                {/* Step 2: 选择策略 - 占一行 */}
                <div className="mb-4">
                    <div className="flex items-center gap-3 flex-wrap">
                        <label className="flex-shrink-0" style={{ color: 'var(--foreground)', fontSize: '0.95rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            <span style={{ color: strategy ? 'var(--primary)' : (ticker ? 'var(--warning)' : 'var(--muted-foreground)') }}>步骤2：</span> 选择策略（Strategy)
                        </label>
                        <div className="flex gap-2 flex-1 flex-wrap" style={{ minWidth: 0 }}>
                        {(Object.keys(strategyLabels) as Strategy[]).map(s => (
                            <button
                                key={s}
                                className={`strategy-btn ${strategy === s ? 'active' : ''}`}
                                onClick={() => setStrategy(s)}
                                disabled={!ticker}
                                style={{ 
                                    opacity: ticker ? 1 : 0.5, 
                                    cursor: ticker ? 'pointer' : 'not-allowed',
                                    flex: '1 1 0',
                                    minWidth: '100px'
                                }}
                            >
                                {strategyLabels[s]}
                            </button>
                        ))}
                        </div>
                    </div>
                </div>

                {/* Step 3 & 4: 加载日期 + 选择到期日 - 占一行 */}
                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                    <div className="flex-1 min-w-[200px] flex items-center gap-3">
                        <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                            <span style={{ color: expirations.length > 0 ? 'var(--primary)' : (ticker && strategy ? 'var(--warning)' : 'var(--muted-foreground)') }}>步骤3：</span> 点击加载到期日（Load)
                        </label>
                        <Button 
                            onClick={fetchExpirations} 
                            disabled={expirationsLoading || !ticker || !strategy} 
                            className="btn-primary flex-1"
                        >
                            {expirationsLoading ? (
                                <i className="bi bi-arrow-clockwise mr-2"></i>
                            ) : expirations.length > 0 ? (
                                <i className="bi bi-check-circle mr-2"></i>
                            ) : (
                                <i className="bi bi-arrow-clockwise mr-2"></i>
                            )}
                            {expirationsLoading ? '加载中...' : '加载日期'}
                        </Button>
                    </div>

                    <div className="flex-1 min-w-[200px] flex items-center gap-3">
                        <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                            <span style={{ color: selectedExpiry ? 'var(--primary)' : (expirations.length > 0 ? 'var(--warning)' : 'var(--muted-foreground)') }}>步骤4：</span> 选择到期日(Expiration)
                        </label>
                        <select
                            value={selectedExpiry}
                            onChange={(e) => handleExpirySelect(e.target.value)}
                            className="form-select flex-1"
                            disabled={expirations.length === 0}
                        >
                            <option value="">{expirations.length > 0 ? '请选择到期日' : '请先完成步骤 3'}</option>
                            {expirations.map(exp => (
                                <option key={exp.date} value={exp.date}>
                                    {exp.date} {exp.period_tag === 'm' ? '(月权)' : '(周权)'}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Header */}
            <div className="header-section" style={{ marginTop: '1.5rem', marginBottom: '1rem', padding: '1rem' }}>
                {/* 期权分析五大支柱 */}
                <div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-1.5 sm:gap-2">
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>流动性优先</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>优先选择高成交量、高持仓量的期权</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>IV分析</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>评估隐含波动率的历史分位数，寻找IV异常</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>风险调整</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>计算年化收益与风险比，设置止损点</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>策略匹配</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>根据市场环境选择合适的多空策略</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>实时监控</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>开市期间实时查看数据，避免依赖过时信息</div></div>
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
                        <div className="text-center">
                            <h2 style={{ fontSize: '1.3rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                                分析结果: <span style={{ color: 'var(--primary)' }}>{displayChain.symbol}</span>
                            </h2>
                            <div style={{ color: 'var(--muted-foreground)' }}>
                                当前价格: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>${displayStockPrice?.toFixed(2) || '-'}</span>
                                <span className="mx-3">|</span>
                                到期日: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>{displayChain.expiry_date || selectedExpiry}</span>
                                <span className="mx-3">|</span>
                                策略: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>{strategyLabels[strategy]}</span>
                                {isHistoricalView && (
                                    <>
                                        <span className="mx-3">|</span>
                                        <span style={{ color: 'var(--muted-foreground)', fontWeight: 600 }}>历史数据</span>
                                    </>
                                )}
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

                    {/* Risk Warning */}
                    <div className="card p-4" style={{
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        border: '2px solid var(--warning)',
                        borderRadius: '0.5rem',
                        marginBottom: '1.5rem'
                    }}>
                        <div className="flex items-start gap-3">
                            <i className="bi bi-exclamation-triangle-fill" style={{
                                color: 'var(--warning)',
                                fontSize: '1.5rem',
                                flexShrink: 0,
                                marginTop: '0.2rem'
                            }}></i>
                            <div style={{ flex: 1 }}>
                                <h3 style={{
                                    fontSize: '1.1rem',
                                    fontWeight: 600,
                                    color: 'var(--warning)',
                                    marginBottom: '0.75rem'
                                }}>
                                    期权交易风险提示
                                </h3>
                                <div style={{ color: 'var(--foreground)', lineHeight: 1.8 }}>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>高风险警告：</strong>期权交易具有极高的风险，可能导致全部本金损失。期权价格波动剧烈，杠杆效应显著，不适合风险承受能力较低的投资者。请充分了解期权交易的风险特性，谨慎决策。
                                    </p>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>财报前后高风险期：</strong>财报发布前后（通常为财报日前3-5天至财报日后1-2天）是期权交易的极高风险期。在此期间，股价可能出现剧烈波动，隐含波动率（IV）通常会显著上升，期权价格波动幅度可能远超预期。建议在财报期间避免或大幅减少期权交易，或使用更保守的策略。
                                    </p>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>数据说明：</strong>当前分析结果基于历史数据和实时市场数据计算得出，仅供参考。期权市场瞬息万变，数据具有时效性。
                                    </p>
                                    <p style={{ marginBottom: 0, fontWeight: 600, color: 'var(--warning)' }}>
                                        <strong>实盘操作建议：</strong>实盘交易时，请务必在开市期间直接查看实时行情，结合最新市场动态进行决策。建议一边查看实时数据，一边进行操作，避免依赖过时数据。
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

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
                                        <th 
                                            onClick={() => handleSort('strike')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            Strike (行权价){getSortIndicator('strike')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('latest')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            Latest (最新价){getSortIndicator('latest')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('bid')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            Bid/Ask (买/卖价){getSortIndicator('bid')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('volume')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            Vol/OI (成交量/持仓量){getSortIndicator('volume')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('iv')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            IV (隐含波动率){getSortIndicator('iv')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('delta')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            Delta (Delta值){getSortIndicator('delta')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('annualized_return')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            年化收益 (Annualized Return){getSortIndicator('annualized_return')}
                                        </th>
                                        <th 
                                            onClick={() => handleSort('score')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            评分 (Score){getSortIndicator('score')}
                                        </th>
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
                        
                        // Check if data exists
                        if (!optionData) {
                            console.error('No option data provided');
                            setError('无法加载历史分析数据：数据为空');
                            return;
                        }
                        
                        // The backend returns the complete analysis response directly
                        // It might be wrapped in 'data' field, or it might be the chain data itself
                        // Check both possibilities
                        let chainData = optionData.data;
                        
                        // If no 'data' field, the optionData itself might be the chain data
                        // Check if it has chain-like properties (symbol, calls, puts, etc.)
                        if (!chainData && (optionData.symbol || optionData.calls || optionData.puts)) {
                            chainData = optionData;
                        }
                        
                        if (!chainData) {
                            console.error('No chain data found in optionData:', optionData);
                            console.error('Available keys:', Object.keys(optionData));
                            setError('无法加载历史分析数据：缺少期权链数据');
                            return;
                        }
                        
                        // Verify it has the required chain structure
                        if (!chainData.symbol && !chainData.calls && !chainData.puts) {
                            console.error('Invalid chain data structure:', chainData);
                            console.error('Available keys:', Object.keys(chainData));
                            setError('无法加载历史分析数据：数据格式不正确');
                            return;
                        }
                        
                        // Set the historical chain data
                        setHistoricalChain(chainData);
                        setIsHistoricalView(true);
                        setActiveTab('analysis');
                        
                        // Extract ticker and other info from historical data
                        const symbol = optionData.history_metadata?.symbol || chainData.symbol;
                        const expiryDate = optionData.history_metadata?.expiry_date || chainData.expiry_date;
                        
                        if (symbol) {
                            setTicker(symbol);
                        }
                        if (expiryDate) {
                            setSelectedExpiry(expiryDate);
                        }
                        if (chainData?.real_stock_price) {
                            setStockPrice(chainData.real_stock_price);
                        }
                        
                        // Try to extract strategy from chain data if available
                        if (chainData.strategy) {
                            setStrategy(chainData.strategy as Strategy);
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
