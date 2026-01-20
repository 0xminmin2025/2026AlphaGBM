import { useState, useEffect, useMemo, useRef } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import OptionsAnalysisHistory from '@/components/OptionsAnalysisHistory';
import HistoryStorage from '@/lib/historyStorage';
import { useTaskPolling } from '@/hooks/useTaskPolling';
import StockSearchInput from '@/components/ui/StockSearchInput';
import { KlineChart, type OHLCData } from '@/components/ui/KlineChart';
import { useTranslation } from 'react-i18next';

// Declare global types for Chart.js
declare global {
    interface Window {
        Chart: any;
    }
}

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
            font-size: 0.7rem;
        }

        .option-table th {
            font-size: 0.65rem;
            padding: 0.4rem 0.2rem;
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
        font-size: 0.75rem;
        font-weight: 500;
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

    /* 风险收益风格标签样式 */
    .style-tag {
        font-size: 0.65rem;
        padding: 0.15rem 0.4rem;
        border-radius: 0.25rem;
        display: inline-block;
        margin-top: 0.25rem;
        font-weight: 500;
        border: 1px solid transparent;
    }

    .style-tag-green {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border-color: rgba(16, 185, 129, 0.3);
    }

    .style-tag-yellow {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border-color: rgba(245, 158, 11, 0.3);
    }

    .style-tag-orange {
        background-color: rgba(249, 115, 22, 0.15);
        color: #F97316;
        border-color: rgba(249, 115, 22, 0.3);
    }

    .style-tag-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border-color: rgba(239, 68, 68, 0.3);
    }

    .style-info {
        font-size: 0.6rem;
        color: var(--muted-foreground);
        margin-top: 0.1rem;
    }

    .win-prob {
        font-size: 0.65rem;
        color: #10B981;
        font-weight: 600;
    }

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

    .form-control::placeholder,
    input::placeholder {
        color: #64748b !important; /* slate-500 - 浅浅的灰色 */
        opacity: 0.5;
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

    /* Range filter styles - yellow sliders with continuous appearance */
    .range-filter {
        -webkit-appearance: none;
        appearance: none;
        height: 6px;
        background: rgba(255, 215, 0, 0.3);
        border-radius: 3px;
        outline: none;
        margin: 0;
    }

    .range-filter::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        background: #FFD700;
        border: 2px solid #FFA500;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(255, 215, 0, 0.4);
    }

    .range-filter::-moz-range-thumb {
        width: 18px;
        height: 18px;
        background: #FFD700;
        border: 2px solid #FFA500;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(255, 215, 0, 0.4);
    }

    .range-filter::-webkit-slider-track {
        height: 6px;
        background: rgba(255, 215, 0, 0.3);
        border-radius: 3px;
    }

    .range-filter::-moz-range-track {
        height: 6px;
        background: rgba(255, 215, 0, 0.3);
        border-radius: 3px;
    }

    .range-filter:hover::-webkit-slider-thumb {
        background: #FFED4E;
        box-shadow: 0 3px 6px rgba(255, 215, 0, 0.6);
        transform: scale(1.1);
    }

    .range-filter:hover::-moz-range-thumb {
        background: #FFED4E;
        box-shadow: 0 3px 6px rgba(255, 215, 0, 0.6);
        transform: scale(1.1);
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

    /* Option Detail Modal - Compact */
    .option-modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        padding: 0.75rem;
    }

    .option-modal {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        max-width: 480px;
        width: 100%;
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
        position: relative;
    }

    .option-modal-header {
        padding: 0.75rem 1rem;
        border-bottom: 1px solid var(--border);
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: sticky;
        top: 0;
        background: var(--card);
        z-index: 10;
    }

    .option-modal-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--foreground);
    }

    .option-modal-close {
        background: transparent;
        border: none;
        color: var(--muted-foreground);
        font-size: 1.25rem;
        cursor: pointer;
        padding: 0;
        width: 28px;
        height: 28px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 5px;
        transition: all 0.2s;
    }

    .option-modal-close:hover {
        background: var(--muted);
        color: var(--foreground);
    }

    .option-modal-content {
        padding: 0.875rem 1rem;
    }

    .option-info-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    .option-info-item {
        background: var(--muted);
        padding: 0.5rem;
        border-radius: 6px;
        border-left: 2px solid var(--primary);
    }

    .option-info-label {
        font-size: 0.65rem;
        color: var(--muted-foreground);
        margin-bottom: 0.125rem;
    }

    .option-info-value {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--foreground);
    }

    .option-max-loss {
        background: var(--bear);
        color: white;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .option-max-loss-label {
        font-size: 0.75rem;
        opacity: 0.9;
    }

    .option-max-loss-value {
        font-size: 1rem;
        font-weight: 700;
    }

    .option-chart-container {
        margin-top: 0.5rem;
        padding: 0.5rem;
        background: var(--muted);
        border-radius: 6px;
        position: relative;
        height: 160px;
    }
`;

// 风险收益风格标签类型
type RiskReturnProfile = {
    style: string;              // 'steady_income', 'high_risk_high_reward', 'balanced', 'hedge'
    style_label: string;        // 中英双语标签
    style_label_cn: string;     // 纯中文标签
    style_label_en: string;     // 纯英文标签
    risk_level: string;         // 'low', 'moderate', 'high', 'very_high'
    risk_color: string;         // 前端显示颜色
    max_loss_pct: number;
    max_profit_pct: number;
    win_probability: number;
    risk_reward_ratio: number;
    summary: string;
    summary_cn: string;
    strategy_type: string;      // 'buyer' or 'seller'
    time_decay_impact: string;  // 'positive', 'negative', 'neutral'
    volatility_impact: string;  // 'positive', 'negative', 'neutral'
};

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
    premium?: number;
    risk_return_profile?: RiskReturnProfile;  // 兼容旧格式
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
        risk_return_profile?: RiskReturnProfile;  // 新增：风险收益风格标签
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

// Strategy labels will be set inside the component using translations

export default function Options() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const { t } = useTranslation();

    // Strategy labels with translations
    const strategyLabels: Record<Strategy, string> = {
        'sell_put': `Sell Put (${t('options.strategy.sellPut')})`,
        'buy_put': `Buy Put (${t('options.strategy.buyPut')})`,
        'sell_call': `Sell Call (${t('options.strategy.sellCall')})`,
        'buy_call': `Buy Call (${t('options.strategy.buyCall')})`
    };

    const [ticker, setTicker] = useState('');
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

    // Filter state
    const [strikeRange, setStrikeRange] = useState<[number, number]>([0, 0]);
    const [returnRange, setReturnRange] = useState<[number, number]>([0, 0]);

    // Task progress state
    const [taskProgress, setTaskProgress] = useState(0);
    const [taskStep, setTaskStep] = useState('');

    // Option detail modal state
    const [selectedOption, setSelectedOption] = useState<OptionData | null>(null);
    const [stockHistory, setStockHistory] = useState<{ dates: string[], prices: number[] } | null>(null);
    const [stockHistoryOHLC, setStockHistoryOHLC] = useState<OHLCData[] | null>(null);
    const [loadingHistory, setLoadingHistory] = useState(false);

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
            setTaskStep(t('options.taskComplete'));

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
            setError(t('options.form.enterTicker'));
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
                setTaskStep(t('options.taskCreated'));

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
        // 后端已直接返回 0-100 分数，不需要再乘以 100
        switch (strategy) {
            case 'sell_put': return opt.scores.sprv || 0;
            case 'buy_put': return opt.scores.bprv || 0;
            case 'sell_call': return opt.scores.scrv || 0;
            case 'buy_call': return opt.scores.bcrv || 0;
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

        // Apply filters
        try {
            if (strikeRange[0] > 0 && strikeRange[1] > 0) {
                const minStrike = Math.min(strikeRange[0], strikeRange[1]);
                const maxStrike = Math.max(strikeRange[0], strikeRange[1]);
                if (isFinite(minStrike) && isFinite(maxStrike)) {
                    options = options.filter(opt => {
                        const strike = opt.strike;
                        return isFinite(strike) && strike >= minStrike && strike <= maxStrike;
                    });
                }
            }

            if (returnRange[0] !== 0 || returnRange[1] !== 0) {
                const minReturn = Math.min(returnRange[0], returnRange[1]);
                const maxReturn = Math.max(returnRange[0], returnRange[1]);
                if (isFinite(minReturn) && isFinite(maxReturn)) {
                    options = options.filter(opt => {
                        const annualReturn = opt.scores?.annualized_return || 0;
                        return isFinite(annualReturn) && annualReturn >= minReturn && annualReturn <= maxReturn;
                    });
                }
            }
        } catch (error) {
            console.error('Error applying filters:', error);
        }

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

            // Ensure values are finite
            if (!isFinite(valueA) || !isFinite(valueB)) {
                if (!isFinite(valueA) && !isFinite(valueB)) return 0;
                if (!isFinite(valueA)) return 1;
                return -1;
            }

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

    // Use historical chain data if viewing history, otherwise use current chain
    const displayChain = isHistoricalView ? historicalChain : chain;
    const displayStockPrice = isHistoricalView ? (historicalChain?.real_stock_price || stockPrice) : stockPrice;

    // Handle option click to show detail modal
    const handleOptionClick = async (option: OptionData) => {
        setSelectedOption(option);
        setLoadingHistory(true);

        // Fetch stock history (1 month)
        try {
            const response = await api.get(`/options/history/${ticker}`, {
                params: { days: 30 }
            });

            console.log('Stock history API response:', response.data);

            if (response.data && response.data.data && Array.isArray(response.data.data)) {
                // API returns: {symbol: string, data: [{time, open, high, low, close}]}
                const data = response.data.data;

                // Build OHLC data for KlineChart
                const ohlcData: OHLCData[] = data
                    .filter((item: any) => item.time && item.open && item.high && item.low && item.close)
                    .map((item: any) => ({
                        time: item.time,
                        open: typeof item.open === 'number' ? item.open : parseFloat(item.open),
                        high: typeof item.high === 'number' ? item.high : parseFloat(item.high),
                        low: typeof item.low === 'number' ? item.low : parseFloat(item.low),
                        close: typeof item.close === 'number' ? item.close : parseFloat(item.close),
                    }));

                // Build dates/prices for Chart.js line chart
                const dates = data.map((item: any) => {
                    if (item.time) {
                        const date = new Date(item.time * 1000);
                        return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
                    }
                    return '';
                }).filter((d: string) => d);

                const prices = data.map((item: any) => {
                    const price = item.close || item.price || 0;
                    return typeof price === 'number' ? price : parseFloat(price);
                }).filter((p: number) => !isNaN(p) && p > 0);

                if (ohlcData.length > 0 && dates.length > 0 && prices.length > 0) {
                    console.log('Setting stock history:', { ohlcCount: ohlcData.length, lineCount: prices.length });
                    setStockHistoryOHLC(ohlcData);
                    setStockHistory({ dates, prices });
                } else {
                    console.error('No valid data found');
                    setStockHistoryOHLC(null);
                    setStockHistory(null);
                }
            } else {
                setStockHistoryOHLC(null);
                setStockHistory(null);
            }
        } catch (error) {
            console.error('Error fetching stock history:', error);
            setStockHistoryOHLC(null);
            setStockHistory(null);
        } finally {
            setLoadingHistory(false);
        }
    };

    // Close modal
    const closeModal = () => {
        setSelectedOption(null);
        setStockHistory(null);
        setStockHistoryOHLC(null);
    };

    // Calculate max loss for option
    const calculateMaxLoss = (option: OptionData, currentStockPrice: number): number => {
        const premium = option.premium || ((option.bid_price + option.ask_price) / 2) || option.latest_price || 0;
        
        if (strategy === 'sell_put') {
            // Sell Put: Max loss = Strike - Premium (if stock goes to 0)
            return option.strike - premium;
        } else if (strategy === 'sell_call') {
            // Sell Call: Max loss is unlimited, but we calculate theoretical max at 2x current price
            return (currentStockPrice * 2) - option.strike - premium;
        } else if (strategy === 'buy_call') {
            // Buy Call: Max loss = Premium paid
            return premium;
        } else { // buy_put
            // Buy Put: Max loss = Premium paid
            return premium;
        }
    };

    // Calculate stop loss price
    const calculateStopLoss = (option: OptionData, currentStockPrice: number): number => {
        const premium = option.premium || ((option.bid_price + option.ask_price) / 2) || option.latest_price || 0;
        
        if (strategy === 'sell_put') {
            // Sell Put: Stop loss when stock price drops below strike - premium * 2
            return Math.max(0, option.strike - (premium * 2));
        } else if (strategy === 'sell_call') {
            // Sell Call: Stop loss when stock price rises above strike + premium * 2
            return option.strike + (premium * 2);
        } else if (strategy === 'buy_call') {
            // Buy Call: Stop loss at 50% of premium
            return currentStockPrice; // Stop loss is based on option price, not stock price
        } else { // buy_put
            // Buy Put: Stop loss at 50% of premium
            return currentStockPrice; // Stop loss is based on option price, not stock price
        }
    };

    // Get all options using useMemo to avoid recalculating on every render
    // IMPORTANT: All hooks must be called before any early returns
    const allOptions = useMemo((): OptionData[] => {
        if (!displayChain) return [];

        let options: OptionData[] = [];
        if (strategy === 'sell_put' || strategy === 'buy_put') {
            options = Array.isArray(displayChain.puts) ? [...displayChain.puts] : [];
        } else {
            options = Array.isArray(displayChain.calls) ? [...displayChain.calls] : [];
        }
        return options;
    }, [displayChain, strategy]);

    // Calculate ranges for filters
    useEffect(() => {
        if (!displayChain || allOptions.length === 0) {
            setStrikeRange([0, 0]);
            setReturnRange([0, 0]);
            return;
        }

        try {
            const strikes = allOptions.map(opt => opt.strike).filter(s => s > 0 && !isNaN(s) && isFinite(s));
            const returns = allOptions
                .map(opt => opt.scores?.annualized_return || 0)
                .filter(r => r !== 0 && !isNaN(r) && isFinite(r));

            if (strikes.length > 0) {
                const minStrike = Math.min(...strikes);
                const maxStrike = Math.max(...strikes);
                if (isFinite(minStrike) && isFinite(maxStrike) && minStrike < maxStrike) {
                    setStrikeRange([minStrike, maxStrike]);
                }
            } else {
                setStrikeRange([0, 0]);
            }

            if (returns.length > 0) {
                const minReturn = Math.min(...returns);
                const maxReturn = Math.max(...returns);
                if (isFinite(minReturn) && isFinite(maxReturn) && minReturn < maxReturn) {
                    setReturnRange([minReturn, maxReturn]);
                }
            } else {
                setReturnRange([0, 0]);
            }
        } catch (error) {
            console.error('Error calculating filter ranges:', error);
            setStrikeRange([0, 0]);
            setReturnRange([0, 0]);
        }
    }, [displayChain?.symbol, displayChain?.expiry_date, strategy, allOptions.length]);

    // Early returns after all hooks
    // Add timeout for auth loading to prevent infinite loading
    useEffect(() => {
        if (authLoading) {
            const timeout = setTimeout(() => {
                console.warn("Auth loading timeout in Options page");
            }, 10000); // 10 second warning
            return () => clearTimeout(timeout);
        }
    }, [authLoading]);

    if (authLoading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="text-center">
                    <div className="spinner mx-auto mb-4"></div>
                    <p className="text-white">{t('common.loading')}</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 text-white">
                <h2 className="text-2xl font-bold">{t('options.loginRequired')}</h2>
                <Button onClick={() => navigate('/login')} className="btn-primary">
                    {t('auth.login')}
                </Button>
            </div>
        );
    }

    const filteredOptions = getFilteredOptions();

    // 推荐期权：按评分排序，取前3-4个
    const getTopRecommendations = () => {
        if (filteredOptions.length === 0) return [];

        // 按评分降序排序
        const sorted = [...filteredOptions].sort((a, b) => getOptionScore(b) - getOptionScore(a));

        // 取评分最高的期权（最多4个，且评分 > 0）
        const recommendations = sorted
            .filter(opt => getOptionScore(opt) > 0)
            .slice(0, 4);

        return recommendations;
    };

    const topRecommendations = getTopRecommendations();

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
                        {t('options.tab.analysis')}
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
                        {t('options.tab.history')}
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
                    {t('options.form.title')}
                </h5>

                {/* Step 1: Enter Stock Symbol */}
                <div className="mb-4 flex items-center gap-3">
                    <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                        <span style={{ color: ticker ? 'var(--primary)' : 'var(--muted-foreground)' }}>{t('options.form.step1')}</span> {t('options.form.step1Label')}
                    </label>
                    <div className="flex-1">
                        <StockSearchInput
                            value={ticker}
                            onChange={setTicker}
                            placeholder={t('options.form.tickerPlaceholder')}
                        />
                    </div>
                </div>

                {/* Step 2: Select Strategy */}
                <div className="mb-4">
                    <div className="flex items-center gap-3 flex-wrap">
                        <label className="flex-shrink-0" style={{ color: 'var(--foreground)', fontSize: '0.95rem', fontWeight: 600, whiteSpace: 'nowrap' }}>
                            <span style={{ color: strategy ? 'var(--primary)' : (ticker ? 'var(--warning)' : 'var(--muted-foreground)') }}>{t('options.form.step2')}</span> {t('options.form.step2Label')}
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

                {/* Step 3 & 4: Load Dates + Select Expiry */}
                <div className="flex flex-col sm:flex-row gap-4 mb-4">
                    <div className="flex-1 min-w-[200px] flex items-center gap-3">
                        <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                            <span style={{ color: expirations.length > 0 ? 'var(--primary)' : (ticker && strategy ? 'var(--warning)' : 'var(--muted-foreground)') }}>{t('options.form.step3')}</span> {t('options.form.step3Label')}
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
                            {expirationsLoading ? t('options.form.loading') : t('options.form.loadDates')}
                        </Button>
                    </div>

                    <div className="flex-1 min-w-[200px] flex items-center gap-3">
                        <label className="flex-shrink-0" style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem', whiteSpace: 'nowrap' }}>
                            <span style={{ color: selectedExpiry ? 'var(--primary)' : (expirations.length > 0 ? 'var(--warning)' : 'var(--muted-foreground)') }}>{t('options.form.step4')}</span> {t('options.form.step4Label')}
                        </label>
                        <select
                            value={selectedExpiry}
                            onChange={(e) => handleExpirySelect(e.target.value)}
                            className="form-select flex-1"
                            disabled={expirations.length === 0}
                        >
                            <option value="">{expirations.length > 0 ? t('options.form.selectExpiry') : t('options.form.completeStep3')}</option>
                            {expirations.map(exp => (
                                <option key={exp.date} value={exp.date}>
                                    {exp.date} {exp.period_tag === 'm' ? t('options.form.monthly') : t('options.form.weekly')}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Header */}
            <div className="header-section" style={{ marginTop: '1.5rem', marginBottom: '1rem', padding: '1rem' }}>
                {/* Five Pillars of Options Analysis */}
                <div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-1.5 sm:gap-2">
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>{t('options.pillar.liquidity')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>{t('options.pillar.liquidityDesc')}</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>{t('options.pillar.iv')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>{t('options.pillar.ivDesc')}</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>{t('options.pillar.risk')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>{t('options.pillar.riskDesc')}</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>{t('options.pillar.strategy')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>{t('options.pillar.strategyDesc')}</div></div>
                        <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.8rem' }}>{t('options.pillar.realtime')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>{t('options.pillar.realtimeDesc')}</div></div>
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
                                <span style={{ color: 'var(--muted-foreground)' }}>{t('options.progress')}</span>
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
                        <p style={{ color: 'var(--muted-foreground)' }}>{t('options.analyzing')}</p>
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
                                {t('options.historical.title')}
                            </span>
                            <span className="text-muted ml-3" style={{ fontSize: '0.9rem' }}>
                                {t('options.historical.viewData')}
                            </span>
                        </div>
                        <div className="ml-auto">
                            <span className="badge-primary">
                                <i className="bi bi-archive mr-1"></i>
                                {t('options.historical.badge')}
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
                                {t('options.results.title')}: <span style={{ color: 'var(--primary)' }}>{displayChain.symbol}</span>
                            </h2>
                            <div style={{ color: 'var(--muted-foreground)' }}>
                                {t('options.results.currentPrice')}: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>${displayStockPrice?.toFixed(2) || '-'}</span>
                                <span className="mx-3">|</span>
                                {t('options.results.expiry')}: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>{displayChain.expiry_date || selectedExpiry}</span>
                                <span className="mx-3">|</span>
                                {t('options.results.strategy')}: <span style={{ fontWeight: 600, color: 'var(--muted-foreground)' }}>{strategyLabels[strategy]}</span>
                                {isHistoricalView && (
                                    <>
                                        <span className="mx-3">|</span>
                                        <span style={{ color: 'var(--muted-foreground)', fontWeight: 600 }}>{t('options.results.historicalData')}</span>
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
                                {t('options.recommended')}
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
                                {topRecommendations.map(opt => {
                                    // 支持两种数据格式：scores.risk_return_profile 或 risk_return_profile
                                    const profile = opt.scores?.risk_return_profile || opt.risk_return_profile;
                                    const styleColorClass = profile?.risk_color
                                        ? `style-tag-${profile.risk_color}`
                                        : 'style-tag-yellow';

                                    // Calculate feature tags (multi-tag, independent evaluation)
                                    const featureTags: { label: string; color: string }[] = [];
                                    const assignmentProb = opt.scores?.assignment_probability ?? 100;
                                    const annualReturn = opt.scores?.annualized_return ?? 0;
                                    const premium = opt.bid_price ?? opt.latest_price ?? 0;
                                    const stockPrice = displayChain?.stock_price ?? 100;
                                    const premiumPct = stockPrice > 0 ? (premium / stockPrice) * 100 : 0;

                                    // Low exercise probability: < 30%
                                    if (assignmentProb < 30) {
                                        featureTags.push({ label: t('options.tag.lowExercise'), color: '#22c55e' });
                                    }
                                    // High annualized: > 30%
                                    if (annualReturn > 30) {
                                        featureTags.push({ label: t('options.tag.highAnnualized'), color: '#f59e0b' });
                                    }
                                    // High premium: premium/stock price > 3%
                                    if (premiumPct > 3) {
                                        featureTags.push({ label: t('options.tag.highPremium'), color: '#3b82f6' });
                                    }

                                    return (
                                        <div
                                            key={opt.identifier}
                                            className="p-4 rounded cursor-pointer transition-all hover:scale-105"
                                            style={{
                                                backgroundColor: 'rgba(13, 155, 151, 0.15)',
                                                border: '1px solid var(--primary)'
                                            }}
                                            onClick={() => handleOptionClick(opt)}
                                        >
                                            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)' }}>
                                                ${opt.strike}
                                            </div>
                                            <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                                {opt.put_call}
                                            </div>

                                            {/* 风格标签 */}
                                            {profile && (
                                                <div className={`style-tag ${styleColorClass}`} style={{ marginTop: '0.5rem' }}>
                                                    {profile.style_label_cn || profile.style_label}
                                                </div>
                                            )}

                                            {/* 特性标签（多标签） */}
                                            {featureTags.length > 0 && (
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '0.5rem' }}>
                                                    {featureTags.map((tag, idx) => (
                                                        <span
                                                            key={idx}
                                                            style={{
                                                                fontSize: '0.7rem',
                                                                padding: '2px 6px',
                                                                borderRadius: '4px',
                                                                backgroundColor: `${tag.color}20`,
                                                                color: tag.color,
                                                                border: `1px solid ${tag.color}40`,
                                                                fontWeight: 500
                                                            }}
                                                        >
                                                            {tag.label}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            <div className="flex justify-between mt-2">
                                                <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>Score</span>
                                                <span className={`score-badge ${getScoreClass(getOptionScore(opt))}`}>
                                                    {getOptionScore(opt).toFixed(1)}
                                                </span>
                                            </div>
                                            <div className="flex justify-between mt-1">
                                                <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>{t('options.card.premiumPerContract')}</span>
                                                <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '0.9rem' }}>
                                                    ${(premium * 100).toFixed(0)}
                                                </span>
                                            </div>
                                            <div className="flex justify-between mt-1">
                                                <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>{t('options.card.annualizedReturn')}</span>
                                                <span style={{ color: 'var(--bull)', fontWeight: 600, fontSize: '0.9rem' }}>
                                                    {opt.scores?.annualized_return?.toFixed(1) || (premiumPct * 365 / (opt.days_to_expiry || 30)).toFixed(1)}%
                                                </span>
                                            </div>

                                            {/* Win Rate Display */}
                                            {profile?.win_probability && (
                                                <div className="flex justify-between mt-1">
                                                    <span style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem' }}>{t('options.card.winRate')}</span>
                                                    <span className="win-prob">
                                                        {(profile.win_probability * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
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
                                    {t('options.risk.title')}
                                </h3>
                                <div style={{ color: 'var(--foreground)', lineHeight: 1.8 }}>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>{t('options.risk.highRisk')}</strong>{t('options.risk.highRiskDesc')}
                                    </p>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>{t('options.risk.earnings')}</strong>{t('options.risk.earningsDesc')}
                                    </p>
                                    <p style={{ marginBottom: '0.5rem' }}>
                                        <strong>{t('options.risk.dataNote')}</strong>{t('options.risk.dataDesc')}
                                    </p>
                                    <p style={{ marginBottom: 0, fontWeight: 600, color: 'var(--warning)' }}>
                                        <strong>{t('options.risk.liveAdvice')}</strong>{t('options.risk.liveAdviceDesc')}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Options Table */}
                    <div className="option-col-section">
                        <div className={strategy.includes('call') ? 'header-calls' : 'header-puts'}>
                            {strategy.includes('call') ? t('options.table.calls') : t('options.table.puts')} - {strategyLabels[strategy]}
                        </div>
                        
                        {/* Filter Controls */}
                        {(() => {
                            try {
                                if (!allOptions || allOptions.length === 0) return null;
                                
                                const strikes = allOptions
                                    .map(o => o?.strike)
                                    .filter(s => s != null && s > 0 && !isNaN(s) && isFinite(s));
                                const returns = allOptions
                                    .map(o => o?.scores?.annualized_return || 0)
                                    .filter(r => r !== 0 && !isNaN(r) && isFinite(r));
                                
                                if (strikes.length === 0 || returns.length === 0) {
                                    return null;
                                }
                                
                                const strikeMin = Math.min(...strikes);
                                const strikeMax = Math.max(...strikes);
                                const returnMin = Math.min(...returns);
                                const returnMax = Math.max(...returns);
                                
                                // Ensure valid ranges
                                if (!isFinite(strikeMin) || !isFinite(strikeMax) || !isFinite(returnMin) || !isFinite(returnMax)) {
                                    return null;
                                }
                                
                                // Ensure min < max
                                if (strikeMin >= strikeMax || returnMin >= returnMax) {
                                    return null;
                                }
                                
                                const currentStrikeMin = Math.min(strikeRange[0], strikeRange[1]);
                                const currentStrikeMax = Math.max(strikeRange[0], strikeRange[1]);
                                const currentReturnMin = Math.min(returnRange[0], returnRange[1]);
                                const currentReturnMax = Math.max(returnRange[0], returnRange[1]);
                                
                                return (
                                    <div className="p-4" style={{ borderBottom: '1px solid var(--border)', background: 'var(--muted)' }}>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {/* Strike Price Filter */}
                                            <div>
                                                <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                                                    {t('options.filter.strikeRange')}: ${currentStrikeMin.toFixed(2)} - ${currentStrikeMax.toFixed(2)}
                                                </label>
                                                <div className="flex items-center gap-1">
                                                    <input
                                                        type="range"
                                                        min={strikeMin}
                                                        max={strikeMax}
                                                        step={Math.max(0.01, (strikeMax - strikeMin) / 100)}
                                                        value={Math.max(strikeMin, Math.min(strikeMax, strikeRange[0]))}
                                                        onChange={(e) => {
                                                            const val = parseFloat(e.target.value);
                                                            setStrikeRange([val, Math.max(val, strikeRange[1])]);
                                                        }}
                                                        className="flex-1 range-filter"
                                                        style={{ accentColor: '#FFD700', cursor: 'pointer' }}
                                                    />
                                                    <input
                                                        type="range"
                                                        min={strikeMin}
                                                        max={strikeMax}
                                                        step={Math.max(0.01, (strikeMax - strikeMin) / 100)}
                                                        value={Math.max(strikeMin, Math.min(strikeMax, strikeRange[1]))}
                                                        onChange={(e) => {
                                                            const val = parseFloat(e.target.value);
                                                            setStrikeRange([Math.min(val, strikeRange[0]), val]);
                                                        }}
                                                        className="flex-1 range-filter"
                                                        style={{ accentColor: '#FFD700', cursor: 'pointer' }}
                                                    />
                                                </div>
                                            </div>

                                            {/* Annualized Return Filter */}
                                            <div>
                                                <label className="block mb-2 text-sm font-medium" style={{ color: 'var(--foreground)' }}>
                                                    {t('options.filter.annualizedRange')}: {currentReturnMin.toFixed(1)}% - {currentReturnMax.toFixed(1)}%
                                                </label>
                                                <div className="flex items-center gap-1">
                                                    <input
                                                        type="range"
                                                        min={returnMin}
                                                        max={returnMax}
                                                        step={Math.max(0.1, (returnMax - returnMin) / 100)}
                                                        value={Math.max(returnMin, Math.min(returnMax, returnRange[0]))}
                                                        onChange={(e) => {
                                                            const val = parseFloat(e.target.value);
                                                            setReturnRange([val, Math.max(val, returnRange[1])]);
                                                        }}
                                                        className="flex-1 range-filter"
                                                        style={{ accentColor: '#FFD700', cursor: 'pointer' }}
                                                    />
                                                    <input
                                                        type="range"
                                                        min={returnMin}
                                                        max={returnMax}
                                                        step={Math.max(0.1, (returnMax - returnMin) / 100)}
                                                        value={Math.max(returnMin, Math.min(returnMax, returnRange[1]))}
                                                        onChange={(e) => {
                                                            const val = parseFloat(e.target.value);
                                                            setReturnRange([Math.min(val, returnRange[0]), val]);
                                                        }}
                                                        className="flex-1 range-filter"
                                                        style={{ accentColor: '#FFD700', cursor: 'pointer' }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            } catch (error) {
                                console.error('Error rendering filter controls:', error);
                                return null;
                            }
                        })()}

                        <div style={{ overflowX: 'auto' }}>
                            <div className="table-container">
                                <table className="option-table">
                                <thead>
                                    <tr>
                                        <th
                                            onClick={() => handleSort('strike')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.strike')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Strike{getSortIndicator('strike')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('latest')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.latest')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Latest{getSortIndicator('latest')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('bid')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.bidAsk')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Bid/Ask{getSortIndicator('bid')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('volume')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.volOI')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Vol/OI{getSortIndicator('volume')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('iv')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.iv')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>IV{getSortIndicator('iv')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('delta')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.delta')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Delta{getSortIndicator('delta')}</div>
                                        </th>
                                        <th
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.exerciseProb')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Exercise Prob.</div>
                                        </th>
                                        <th
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.priceDiff')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Price Diff.</div>
                                        </th>
                                        <th
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.premium')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Premium×100</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('annualized_return')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.annualized')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Annualized{getSortIndicator('annualized_return')}</div>
                                        </th>
                                        <th
                                            onClick={() => handleSort('score')}
                                            style={{ cursor: 'pointer', userSelect: 'none' }}
                                        >
                                            <div>{t('options.table.score')}</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginTop: '2px' }}>Score{getSortIndicator('score')}</div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredOptions.length === 0 ? (
                                        <tr>
                                            <td colSpan={11} style={{ textAlign: 'center', padding: '2rem', color: 'var(--muted-foreground)' }}>
                                                {t('options.table.noData')}
                                            </td>
                                        </tr>
                                    ) : (
                                        filteredOptions.map(opt => {
                                            const totalScore = getOptionScore(opt);
                                            const isRecommended = totalScore >= 60;
                                            
                                            // 计算行权概率：优先使用assignment_probability（已是0-100%格式），否则用delta的绝对值
                                            const exerciseProb = opt.scores?.assignment_probability
                                                ? opt.scores.assignment_probability  // 已经是百分比格式，不需要再乘100
                                                : (opt.delta ? Math.abs(opt.delta) * 100 : 0);
                                            
                                            // 计算价格差百分比：CALL是(strike - stockPrice)/stockPrice，PUT是(stockPrice - strike)/stockPrice
                                            const stockPrice = displayStockPrice || 0;
                                            const priceDiffPercent = stockPrice > 0 
                                                ? (opt.put_call === 'CALL' 
                                                    ? ((opt.strike - stockPrice) / stockPrice) * 100
                                                    : ((stockPrice - opt.strike) / stockPrice) * 100)
                                                : 0;
                                            
                                            // 计算权利金：优先使用premium，否则用中间价
                                            const premium = opt.premium ||
                                                ((opt.bid_price && opt.ask_price)
                                                    ? (opt.bid_price + opt.ask_price) / 2
                                                    : opt.latest_price || 0);

                                            return (
                                                <tr
                                                    key={opt.identifier}
                                                    className={isRecommended ? 'recommended-row' : ''}
                                                    onClick={() => handleOptionClick(opt)}
                                                    style={{ cursor: 'pointer' }}
                                                >
                                                    <td style={{ fontWeight: 600 }}>
                                                        ${opt.strike}
                                                    </td>
                                                    <td>${formatNumber(opt.latest_price)}</td>
                                                    <td><small>${formatNumber(opt.bid_price)} / ${formatNumber(opt.ask_price)}</small></td>
                                                    <td><small>{opt.volume} / {opt.open_interest}</small></td>
                                                    <td>{formatPercent(opt.implied_vol)}</td>
                                                    <td>{formatNumber(opt.delta, 3)}</td>
                                                    <td style={{ color: exerciseProb > 50 ? 'var(--warning)' : 'inherit' }}>
                                                        {exerciseProb.toFixed(1)}%
                                                    </td>
                                                    <td style={{ color: priceDiffPercent > 0 ? 'var(--bull)' : priceDiffPercent < 0 ? 'var(--bear)' : 'inherit' }}>
                                                        {priceDiffPercent >= 0 ? '+' : ''}{formatNumber(priceDiffPercent, 2)}%
                                                    </td>
                                                    <td style={{ fontWeight: 500, color: 'var(--primary)' }}>
                                                        ${formatNumber(premium * 100, 0)}
                                                    </td>
                                                    <td style={{ color: totalScore >= 50 ? 'var(--bull)' : 'inherit', fontWeight: totalScore >= 50 ? 600 : 400 }}>
                                                        {opt.scores?.annualized_return?.toFixed(1) || ((premium / (opt.strike || 1) * 100) / (opt.days_to_expiry || 30) * 365).toFixed(1)}%
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
                    <p>{t('options.empty')}</p>
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
                            setError(t('options.error.emptyData'));
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
                            setError(t('options.error.noChainData'));
                            return;
                        }
                        
                        // Verify it has the required chain structure
                        if (!chainData.symbol && !chainData.calls && !chainData.puts) {
                            console.error('Invalid chain data structure:', chainData);
                            console.error('Available keys:', Object.keys(chainData));
                            setError(t('options.error.invalidFormat'));
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
                    symbolFilter={''}
                />
            </div>

            {/* Option Detail Modal */}
            {selectedOption && (
                <OptionDetailModal
                    option={selectedOption}
                    stockPrice={displayStockPrice || 0}
                    strategy={strategy}
                    stockHistory={stockHistory}
                    stockHistoryOHLC={stockHistoryOHLC}
                    loadingHistory={loadingHistory}
                    onClose={closeModal}
                />
            )}
        </div>
    );
}

// Option Detail Modal Component
function OptionDetailModal({
    option,
    stockPrice,
    strategy,
    stockHistory,
    stockHistoryOHLC,
    loadingHistory,
    onClose,
}: {
    option: OptionData;
    stockPrice: number;
    strategy: Strategy;
    stockHistory: { dates: string[], prices: number[] } | null;
    stockHistoryOHLC: OHLCData[] | null;
    loadingHistory: boolean;
    onClose: () => void;
}) {
    const { t } = useTranslation();
    // Chart type state for tab switching
    const [chartType, setChartType] = useState<'kline' | 'line'>('kline');
    // Create refs inside the modal component
    const chartRef = useRef<HTMLCanvasElement>(null);
    const chartInstance = useRef<any>(null);
    const strategyLabels: Record<Strategy, string> = {
        'sell_put': `${t('options.strategy.sellPut')} (Sell Put)`,
        'sell_call': `${t('options.strategy.sellCall')} (Sell Call)`,
        'buy_call': `${t('options.strategy.buyCall')} (Buy Call)`,
        'buy_put': `${t('options.strategy.buyPut')} (Buy Put)`
    };

    // Calculate premium correctly
    const premium = option.premium || 
        ((option.bid_price != null && option.ask_price != null) 
            ? (option.bid_price + option.ask_price) / 2 
            : (option.latest_price || 0));
    
    console.log('Option detail modal data:', {
        option: {
            strike: option.strike,
            bid_price: option.bid_price,
            ask_price: option.ask_price,
            latest_price: option.latest_price,
            premium: option.premium
        },
        calculatedPremium: premium,
        stockPrice,
        strategy
    });
    
    // Calculate max loss (per contract = 100 shares)
    const calculateMaxLoss = (): number => {
        if (strategy === 'sell_put') {
            // Sell Put: Max loss = (Strike - Premium) * 100 (if stock goes to 0)
            return Math.max(0, (option.strike - premium) * 100);
        } else if (strategy === 'sell_call') {
            // Sell Call: Max loss is unlimited, show theoretical max at 2x current price
            return Math.max(0, ((stockPrice * 2) - option.strike - premium) * 100);
        } else if (strategy === 'buy_call' || strategy === 'buy_put') {
            // Buy Call/Put: Max loss = Premium paid * 100
            return premium * 100;
        }
        return 0;
    };

    const maxLoss = calculateMaxLoss();
    
    // Calculate stop loss price
    const calculateStopLoss = (): number => {
        if (strategy === 'sell_put') {
            // Sell Put: Stop loss when stock price drops below strike - premium * 2
            return Math.max(0, option.strike - (premium * 2));
        } else if (strategy === 'sell_call') {
            // Sell Call: Stop loss when stock price rises above strike + premium * 2
            return option.strike + (premium * 2);
        } else if (strategy === 'buy_call' || strategy === 'buy_put') {
            // Buy Call/Put: Stop loss is based on option price (50% loss)
            // For display purposes, show stock price where option would be worthless
            return stockPrice;
        }
        return stockPrice;
    };

    const stopLossPrice = calculateStopLoss();

    // Render Chart.js line chart (only when chartType is 'line')
    useEffect(() => {
        if (chartType !== 'line' || !stockHistory || !chartRef.current) {
            return;
        }

        // Wait for Chart.js to be available
        if (!window.Chart) {
            console.log('Chart.js not loaded yet');
            const checkChart = setInterval(() => {
                if (window.Chart) {
                    clearInterval(checkChart);
                    setTimeout(() => {
                        if (stockHistory && chartRef.current) {
                            renderChart();
                        }
                    }, 100);
                }
            }, 100);
            return () => clearInterval(checkChart);
        }

        renderChart();

        function renderChart() {
            if (!stockHistory || !chartRef.current || !window.Chart) return;

            if (chartInstance.current) {
                chartInstance.current.destroy();
            }

            const ctx = chartRef.current.getContext('2d');
            if (!ctx) {
                console.error('Could not get canvas context');
                return;
            }

            // Ensure prices are numbers
            const prices = stockHistory.prices
                .map((p: number | string) => typeof p === 'number' ? p : parseFloat(p))
                .filter((p: number) => !isNaN(p) && p > 0);

            if (prices.length === 0) {
                console.error('No valid prices in stockHistory:', stockHistory);
                return;
            }

            const dates = stockHistory.dates.slice(0, prices.length);

            const allPrices = [...prices, stockPrice, option.strike, stopLossPrice].filter(p => p > 0 && !isNaN(p));
            if (allPrices.length === 0) return;

            const minPrice = Math.min(...allPrices);
            const maxPrice = Math.max(...allPrices);
            const priceRange = maxPrice - minPrice;
            const padding = priceRange > 0 ? priceRange * 0.1 : maxPrice * 0.05;

            try {
                chartInstance.current = new window.Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: t('options.modal.chartStockPrice'),
                                data: prices,
                                borderColor: 'hsl(178, 78%, 32%)',
                                backgroundColor: 'rgba(13, 155, 151, 0.1)',
                                fill: true,
                                tension: 0.4,
                                pointRadius: 0,
                                borderWidth: 1.5,
                                spanGaps: false
                            },
                            {
                                label: t('options.modal.chartStrikePrice'),
                                data: Array(dates.length).fill(option.strike),
                                borderColor: 'hsl(38, 92%, 50%)',
                                borderDash: [5, 5],
                                borderWidth: 1.5,
                                pointRadius: 0,
                                fill: false,
                                spanGaps: false
                            },
                            {
                                label: t('options.modal.chartCurrentPrice'),
                                data: Array(dates.length).fill(stockPrice),
                                borderColor: 'hsl(142, 76%, 36%)',
                                borderDash: [5, 5],
                                borderWidth: 1.5,
                                pointRadius: 0,
                                fill: false,
                                spanGaps: false
                            },
                            {
                                label: t('options.modal.chartStopLoss'),
                                data: Array(dates.length).fill(stopLossPrice),
                                borderColor: 'hsl(0, 72%, 51%)',
                                borderDash: [5, 5],
                                borderWidth: 1.5,
                                pointRadius: 0,
                                fill: false,
                                spanGaps: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'bottom',
                                labels: {
                                    color: 'hsl(240, 5%, 64.9%)',
                                    font: { size: 9 },
                                    usePointStyle: true,
                                    padding: 8,
                                    boxWidth: 10,
                                    boxHeight: 10
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                borderColor: 'hsl(178, 78%, 32%)',
                                borderWidth: 1,
                                titleFont: { size: 10 },
                                bodyFont: { size: 9 },
                                padding: 8
                            }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    color: 'hsl(240, 5%, 64.9%)',
                                    font: { size: 8 },
                                    maxRotation: 45,
                                    minRotation: 45,
                                    padding: 4
                                },
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                }
                            },
                            y: {
                                min: Math.max(0, minPrice - padding),
                                max: maxPrice + padding,
                                ticks: {
                                    color: 'hsl(240, 5%, 64.9%)',
                                    font: { size: 8 },
                                    padding: 4,
                                    callback: function(value: number) {
                                        return '$' + value.toFixed(2);
                                    }
                                },
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                }
                            }
                        }
                    }
                });
            } catch (error) {
                console.error('Error creating chart:', error);
            }
        }

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
                chartInstance.current = null;
            }
        };
    }, [chartType, stockHistory, stockPrice, option.strike, stopLossPrice]);

    return (
        <div className="option-modal-overlay" onClick={onClose}>
            <div className="option-modal" onClick={(e) => e.stopPropagation()}>
                <div className="option-modal-header">
                    <div className="option-modal-title">
                        {strategyLabels[strategy]} - ${option.strike}
                    </div>
                    <button className="option-modal-close" onClick={onClose}>
                        ×
                    </button>
                </div>
                <div className="option-modal-content">
                    {/* Important Info Grid */}
                    <div className="option-info-grid">
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.strike')}</div>
                            <div className="option-info-value">${option.strike.toFixed(2)}</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.stockPrice')}</div>
                            <div className="option-info-value">${stockPrice.toFixed(2)}</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.optionPrice')}</div>
                            <div className="option-info-value">${premium.toFixed(2)}</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.premium')}</div>
                            <div className="option-info-value" style={{ color: 'var(--primary)', fontWeight: 600 }}>${(premium * 100).toFixed(0)}</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.iv')}</div>
                            <div className="option-info-value">{(option.implied_vol * 100).toFixed(1)}%</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.delta')}</div>
                            <div className="option-info-value">{option.delta.toFixed(3)}</div>
                        </div>
                        <div className="option-info-item">
                            <div className="option-info-label">{t('options.modal.expiry')}</div>
                            <div className="option-info-value">{option.expiry_date}</div>
                        </div>
                    </div>

                    {/* Max Loss */}
                    <div className="option-max-loss">
                        <span className="option-max-loss-label">{t('options.modal.maxLoss')}</span>
                        <span className="option-max-loss-value">${maxLoss.toFixed(0)}</span>
                    </div>

                    {/* Chart */}
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--muted-foreground)' }}>
                                {t('options.modal.chartTitle')}
                            </div>
                            {/* Chart Type Toggle */}
                            <div style={{ display: 'flex', gap: '4px', background: 'var(--muted)', borderRadius: '6px', padding: '2px' }}>
                                <button
                                    onClick={() => setChartType('kline')}
                                    style={{
                                        padding: '4px 10px',
                                        fontSize: '11px',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        background: chartType === 'kline' ? 'var(--primary)' : 'transparent',
                                        color: chartType === 'kline' ? 'white' : 'var(--muted-foreground)',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {t('options.modal.klineChart')}
                                </button>
                                <button
                                    onClick={() => setChartType('line')}
                                    style={{
                                        padding: '4px 10px',
                                        fontSize: '11px',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        background: chartType === 'line' ? 'var(--primary)' : 'transparent',
                                        color: chartType === 'line' ? 'white' : 'var(--muted-foreground)',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {t('options.modal.lineChart')}
                                </button>
                            </div>
                        </div>
                        {loadingHistory ? (
                            <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <div className="spinner" style={{ width: '24px', height: '24px' }}></div>
                            </div>
                        ) : chartType === 'kline' && stockHistoryOHLC && stockHistoryOHLC.length > 0 ? (
                            <KlineChart
                                data={stockHistoryOHLC}
                                currentPrice={stockPrice}
                                strikePrice={option.strike}
                                stopLossPrice={stopLossPrice}
                                height={200}
                            />
                        ) : chartType === 'line' && stockHistory ? (
                            <div className="option-chart-container">
                                <canvas ref={chartRef}></canvas>
                            </div>
                        ) : (stockHistory || stockHistoryOHLC) ? (
                            // Fallback: show whichever chart has data
                            stockHistoryOHLC && stockHistoryOHLC.length > 0 ? (
                                <KlineChart
                                    data={stockHistoryOHLC}
                                    currentPrice={stockPrice}
                                    strikePrice={option.strike}
                                    stopLossPrice={stopLossPrice}
                                    height={200}
                                />
                            ) : stockHistory ? (
                                <div className="option-chart-container">
                                    <canvas ref={chartRef}></canvas>
                                </div>
                            ) : null
                        ) : (
                            <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>
                                {t('options.modal.noHistory')}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
