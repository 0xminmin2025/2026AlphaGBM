import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { useNavigate, useLocation } from 'react-router-dom';
import StockAnalysisHistory from '@/components/StockAnalysisHistory';
import CustomSelect from '@/components/ui/CustomSelect';
import StockSearchInput from '@/components/ui/StockSearchInput';
// import { NarrativeRadar } from '@/components/NarrativeRadar'; // 暂时隐藏叙事雷达功能
import { useTaskPolling } from '@/hooks/useTaskPolling';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import i18n from '@/lib/i18n';

// Declare global types for Chart.js and marked
declare global {
    interface Window {
        Chart: any;
        marked: any;
    }
}

// Price Chart Component using Chart.js
function PriceChart({ dates, prices }: { dates?: string[], prices?: number[] }) {
    const { t } = useTranslation();
    const chartRef = useRef<HTMLCanvasElement>(null);
    const chartInstance = useRef<any>(null);

    useEffect(() => {
        if (!chartRef.current || !dates || !prices || dates.length === 0) return;

        if (chartInstance.current) {
            chartInstance.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        if (!ctx || !window.Chart) return;

        chartInstance.current = new window.Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Price',
                    data: prices,
                    borderColor: '#0D9B97',
                    backgroundColor: 'rgba(13, 155, 151, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: {
                        grid: { color: '#27272A' },
                        ticks: { color: '#9CA3AF' }
                    }
                }
            }
        });

        return () => {
            if (chartInstance.current) {
                chartInstance.current.destroy();
            }
        };
    }, [dates, prices]);
    
    if (!dates || !prices || dates.length === 0) {
        return (
            <div className="h-48 flex items-center justify-center text-muted">
                <p>{t('stock.chart.noData')}</p>
            </div>
        );
    }

    return (
        <div>
            <div style={{ height: '200px' }}>
                <canvas ref={chartRef}></canvas>
            </div>
            <div className="mt-4 text-center">
                <small style={{ color: '#9CA3AF', fontWeight: 400, fontSize: '0.85rem' }}>
                    {t('stock.chart.dateRange', { start: dates[0], end: dates[dates.length - 1] })}
                </small>
            </div>
        </div>
    );
}

// CSS matching original design-system.css
const styles = `
    :root {
        --background: hsl(240, 10%, 3.9%);
        --background-secondary: hsl(240, 5%, 6%);
        --foreground: hsl(0, 0%, 98%);
        --card: hsl(240, 6%, 10%);
        --card-hover: hsl(240, 5%, 12%);
        --primary: hsl(178, 78%, 32%);
        --primary-rgb: 13, 155, 151;
        --muted: hsl(240, 3.7%, 15.9%);
        --muted-foreground: hsl(240, 5%, 64.9%);
        --border: hsl(240, 3.7%, 15.9%);
        --bull: hsl(142, 76%, 36%);
        --bear: hsl(0, 72%, 51%);
        --warning: hsl(38, 92%, 50%);
    }

    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        transition: all 0.3s ease;
    }

    .card:hover {
        border-color: var(--primary);
        box-shadow: 0 4px 12px rgba(13, 155, 151, 0.15);
    }

    .shadow-lg {
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }

    .shadow-md {
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }

    .metric-label {
        color: var(--muted-foreground);
        font-size: 0.9rem;
        font-weight: 500;
    }

    .text-primary { color: var(--primary) !important; }
    .text-success { color: var(--bull) !important; }
    .text-warning { color: var(--warning) !important; }
    .text-danger { color: var(--bear) !important; }
    .text-muted { color: var(--muted-foreground) !important; }

    .border-primary { border-color: var(--primary) !important; }

    /* Input placeholder styling */
    .form-control::placeholder,
    input::placeholder {
        color: #94a3b8 !important; /* slate-400 - 淡淡的灰色 */
        opacity: 0.7;
    }

    .risk-high { color: var(--bear) !important; }
    .risk-med { color: var(--warning) !important; }
    .risk-low { color: var(--bull) !important; }

    .badge-primary {
        background: rgba(13, 155, 151, 0.2);
        color: var(--primary);
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* Philosophy Card */
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
        font-weight: 700;
        font-size: 0.9rem;
        margin: 0 0.25rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    }

    .philosophy-formula.bull { background: var(--bull); }
    .philosophy-formula.warning { background: var(--warning); }

    .pillar-item {
        background: var(--muted);
        border-left: 3px solid var(--primary);
        padding: 0.6rem 0.9rem;
        border-radius: 6px;
        font-size: 0.8rem;
        line-height: 1.4;
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
        color: var(--foreground);
        text-align: center;
    }

    /* Warning Card */
    .warning-card {
        background: var(--card);
        border-left: 4px solid var(--bear) !important;
    }

    /* AI Summary - Compact and small font */
    .ai-summary {
        color: var(--muted-foreground);
        line-height: 1.4;
        font-size: 0.85rem;
    }

    .ai-summary h2 {
        color: var(--primary);
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0.5rem;
    }

    .ai-summary h3 {
        color: var(--foreground);
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }

    .ai-summary strong { color: var(--foreground); font-weight: 600; font-size: 0.87rem; }
    .ai-summary ul, .ai-summary ol { margin-left: 1.5rem; margin-bottom: 0.8rem; }
    .ai-summary li { margin-bottom: 0.3rem; font-size: 0.85rem; }
    .ai-summary p { margin-bottom: 0.6rem; }

    /* Text Report */
    .text-report-section {
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
    }

    .text-report-title {
        color: var(--primary);
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid var(--border);
    }

    .text-report-label {
        color: var(--muted-foreground);
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }

    .text-report-value {
        color: var(--foreground);
        font-weight: 500;
        font-size: 1rem;
    }

    .list-group-item {
        background: transparent;
        border: none;
        padding: 0.75rem 0;
    }

    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid var(--border);
        border-top-color: var(--primary);
        border-radius: 50%;
        animation: spin 1s ease-in-out infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .form-select, .form-control {
        background: var(--muted);
        border: 1px solid var(--border);
        color: var(--foreground);
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 1rem;
    }

    .form-select:focus, .form-control:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(13, 155, 151, 0.2);
        outline: none;
    }

    .btn-primary {
        background: var(--primary);
        border: none;
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }

    .btn-primary:hover {
        filter: brightness(1.1);
        transform: translateY(-1px);
    }

    .btn-primary:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
`;

// Style descriptions matching original - will be replaced with translations
// Keeping for now for backwards compatibility, will be replaced in component

// Helper to render markdown
function renderMarkdown(text: string): string {
    if (typeof window !== 'undefined' && window.marked) {
        return window.marked.parse(text);
    }
    return text.replace(/\n/g, '<br/>');
}

// Helper to generate entry strategy based on current price, target price, style and risk score
function generateEntryStrategy(
    currentPrice: number,
    targetPrice: number,
    _style: string, // prefixed with _ to indicate intentionally unused
    riskScore: number,
    suggestedPosition: number,
    t: (key: string, params?: any) => string
): string {
    if (suggestedPosition === 0) {
        return t('stock.entry.overTarget');
    }

    const upsidePct = ((targetPrice - currentPrice) / currentPrice) * 100;
    
    // 如果当前价格高于目标价格
    if (upsidePct < 0) {
        return t('stock.entry.overTargetNear');
    }

    // 根据上涨空间和风险评分决定建仓策略
    if (riskScore >= 6) {
        return t('stock.entry.highRisk');
    } else if (riskScore >= 4) {
        // 高风险评分，分批建仓
        if (upsidePct < 5) {
            return t('stock.entry.highRiskLimited', { percent: (suggestedPosition / 3).toFixed(1) });
        } else {
            return t('stock.entry.highRiskNormal', { percent: (suggestedPosition / 3).toFixed(1) });
        }
    } else {
        // 低风险评分
        if (upsidePct < 5) {
            return t('stock.entry.lowRiskLimited', { percent: (suggestedPosition / 2).toFixed(1) });
        } else if (upsidePct < 10) {
            return t('stock.entry.lowRiskMedium', { percent: (suggestedPosition / 2).toFixed(1) });
        } else {
            return t('stock.entry.lowRiskHigh', { percent: suggestedPosition });
        }
    }
}

// Helper to generate take profit strategy based on current price, target price and style
function generateTakeProfitStrategy(
    currentPrice: number,
    targetPrice: number,
    style: string,
    currencySymbol: string = '$',
    t: (key: string, params?: any) => string
): string {
    const upsidePct = ((targetPrice - currentPrice) / currentPrice) * 100;
    
    // 如果当前价格已经超过目标价格
    if (upsidePct < 0) {
        const overTargetPct = Math.abs(upsidePct);
        if (overTargetPct >= 20) {
            return t('stock.takeprofit.overTarget20', { percent: overTargetPct.toFixed(1), symbol: currencySymbol, price: targetPrice.toFixed(2) });
        } else if (overTargetPct >= 10) {
            return t('stock.takeprofit.overTarget10', { percent: overTargetPct.toFixed(1), symbol: currencySymbol, price: targetPrice.toFixed(2) });
        } else {
            return t('stock.takeprofit.overTargetLow', { percent: overTargetPct.toFixed(1), symbol: currencySymbol, price: targetPrice.toFixed(2) });
        }
    }
    
    // 根据投资风格决定止盈策略
    if (style === 'quality' || style === 'value') {
        // 长期投资风格，可以分批止盈
        if (upsidePct >= 20) {
            return t('stock.takeprofit.qualityHigh', { symbol: currencySymbol, price: targetPrice.toFixed(2) });
        } else {
            return t('stock.takeprofit.qualityNormal', { symbol: currencySymbol, price: targetPrice.toFixed(2) });
        }
    } else if (style === 'growth') {
        // 成长风格，中等持有期
        if (upsidePct >= 15) {
            return t('stock.takeprofit.growthHigh', { symbol: currencySymbol, price: targetPrice.toFixed(2) });
        } else {
            return t('stock.takeprofit.growthNormal', { symbol: currencySymbol, price: targetPrice.toFixed(2) });
        }
    } else {
        // 趋势风格，短期持有
        return t('stock.takeprofit.momentum', { symbol: currencySymbol, price: targetPrice.toFixed(2) });
    }
}

// Investment Philosophy Component (collapsible, default collapsed)
function InvestmentPhilosophy() {
    const { t } = useTranslation();
    // 默认收起，从 localStorage 读取用户偏好
    const [expanded, setExpanded] = useState(() => {
        return localStorage.getItem('stockPhilosophyExpanded') === 'true';
    });

    const handleToggle = () => {
        const newState = !expanded;
        setExpanded(newState);
        localStorage.setItem('stockPhilosophyExpanded', String(newState));
    };

    return (
        <div className="philosophy-card shadow-md mb-4 overflow-hidden">
            <div
                className="cursor-pointer transition-colors hover:bg-[rgba(13,155,151,0.05)]"
                style={{ padding: '0.75rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                onClick={handleToggle}
            >
                <div className="flex items-center gap-2" style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '0.95rem' }}>
                    <i className="bi bi-lightbulb-fill"></i>
                    <span>{t('stock.philosophy.title')}</span>
                </div>
                <div className="flex items-center gap-2 text-muted" style={{ fontSize: '0.75rem' }}>
                    <span>{expanded ? t('stock.philosophy.collapse') : t('stock.philosophy.expand')}</span>
                    <i className={`bi bi-chevron-${expanded ? 'up' : 'down'} transition-transform duration-200`}></i>
                </div>
            </div>
            {expanded && (
                <div
                    style={{
                        padding: '0.75rem 1rem',
                        borderTop: '1px solid var(--border)',
                        animation: 'slideDown 0.2s ease-out'
                    }}
                >
                    {/* Core Model - 更紧凑 */}
                    <div style={{ marginBottom: '0.8rem' }}>
                        <div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem', lineHeight: 1.4 }} dangerouslySetInnerHTML={{ __html: t('stock.philosophy.coreModel') }}>
                        </div>
                    </div>

                    {/* Five Pillars - 更紧凑的网格 */}
                    <div style={{ marginBottom: '0.8rem' }}>
                        <strong style={{ color: 'var(--foreground)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>{t('stock.philosophy.fivePillars')}</strong>
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-1.5 sm:gap-2 mt-1">
                            <div className="pillar-item" style={{ padding: '0.4rem 0.6rem' }}><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.7rem' }}>{t('stock.philosophy.pillar1.title')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', lineHeight: 1.3 }}>{t('stock.philosophy.pillar1.desc')}</div></div>
                            <div className="pillar-item" style={{ padding: '0.4rem 0.6rem' }}><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.7rem' }}>{t('stock.philosophy.pillar2.title')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', lineHeight: 1.3 }}>{t('stock.philosophy.pillar2.desc')}</div></div>
                            <div className="pillar-item" style={{ padding: '0.4rem 0.6rem' }}><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.7rem' }}>{t('stock.philosophy.pillar3.title')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', lineHeight: 1.3 }}>{t('stock.philosophy.pillar3.desc')}</div></div>
                            <div className="pillar-item" style={{ padding: '0.4rem 0.6rem' }}><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.7rem' }}>{t('stock.philosophy.pillar4.title')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', lineHeight: 1.3 }}>{t('stock.philosophy.pillar4.desc')}</div></div>
                            <div className="pillar-item" style={{ padding: '0.4rem 0.6rem' }}><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.2rem', fontSize: '0.7rem' }}>{t('stock.philosophy.pillar5.title')}</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', lineHeight: 1.3 }}>{t('stock.philosophy.pillar5.desc')}</div></div>
                        </div>
                    </div>

                    {/* Investment Styles - 更紧凑 */}
                    <div>
                        <strong style={{ color: 'var(--foreground)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>{t('stock.philosophy.styles')}</strong>
                        <div style={{ color: 'var(--muted-foreground)', fontSize: '0.65rem', marginBottom: '0.4rem', lineHeight: 1.3 }}>
                            {t('stock.philosophy.stylesDesc')}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 sm:gap-2">
                            <div className="style-badge" style={{ padding: '0.3rem 0.6rem' }}><strong style={{ color: 'var(--primary)', marginRight: '0.2rem', fontSize: '0.7rem' }}>Quality</strong><span style={{ fontSize: '0.65rem' }}>{t('stock.philosophy.style.quality')}</span></div>
                            <div className="style-badge" style={{ padding: '0.3rem 0.6rem' }}><strong style={{ color: 'var(--primary)', marginRight: '0.2rem', fontSize: '0.7rem' }}>Value</strong><span style={{ fontSize: '0.65rem' }}>{t('stock.philosophy.style.value')}</span></div>
                            <div className="style-badge" style={{ padding: '0.3rem 0.6rem' }}><strong style={{ color: 'var(--primary)', marginRight: '0.2rem', fontSize: '0.7rem' }}>Growth</strong><span style={{ fontSize: '0.65rem' }}>{t('stock.philosophy.style.growth')}</span></div>
                            <div className="style-badge" style={{ padding: '0.3rem 0.6rem' }}><strong style={{ color: 'var(--primary)', marginRight: '0.2rem', fontSize: '0.7rem' }}>Momentum</strong><span style={{ fontSize: '0.65rem' }}>{t('stock.philosophy.style.momentum')}</span></div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Market Warnings Component
function MarketWarnings({ warnings }: { warnings?: any[] }) {
    const { t } = useTranslation();
    if (!warnings || warnings.length === 0) return null;

    const levelColors: Record<string, { bg: string, border: string, text: string }> = {
        'high': { bg: '#7f1d1d', border: '#ef4444', text: '#fca5a5' },
        'medium': { bg: '#78350f', border: '#f59e0b', text: '#fcd34d' },
        'low': { bg: '#1e3a2f', border: '#10b981', text: '#6ee7b7' }
    };

    const urgencyLabels: Record<string, string> = {
        'immediate': t('stock.marketWarnings.urgency.immediate'),
        'soon': t('stock.marketWarnings.urgency.soon'),
        'monitor': t('stock.marketWarnings.urgency.monitor')
    };

    return (
        <div className="card shadow-lg p-4 mb-4 warning-card">
            <h5 className="mb-3 flex items-center gap-2" style={{ color: 'var(--bear)' }}>
                <i className="bi bi-exclamation-triangle-fill"></i>
                {t('stock.marketWarnings')}
            </h5>
            <div>
                {warnings.map((warning, idx) => {
                    const colors = levelColors[warning.level] || levelColors['low'];
                    return (
                        <div
                            key={idx}
                            className="mb-2 p-2 rounded"
                            style={{
                                backgroundColor: colors.bg,
                                borderLeft: `3px solid ${colors.border}`,
                                color: colors.text
                            }}
                        >
                            <div className="flex items-start">
                                <span style={{ fontSize: '0.85rem', marginRight: '0.5rem', fontWeight: 600, opacity: 0.9 }}>
                                    {urgencyLabels[warning.urgency] || t('stock.marketWarnings.urgency.monitor')}
                                </span>
                                <div style={{ flex: 1 }}>
                                    <strong style={{ color: colors.border }}>{warning.message}</strong>
                                    {warning.event_date && (
                                        <div style={{ fontSize: '0.85rem', marginTop: '0.2rem', opacity: 0.9 }}>
                                            {t('stock.marketWarnings.event')} {warning.event_date}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function Home() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const { t } = useTranslation();

    const [ticker, setTicker] = useState('');
    const [style, setStyle] = useState('quality');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('analysis');
    // 叙事雷达功能暂时隐藏
    // const [searchParams] = useSearchParams();
    // const initialMode = searchParams.get('mode') === 'narrative' ? 'narrative' : 'manual';
    // const [stockMode, setStockMode] = useState<'manual' | 'narrative'>(initialMode);

    // 监听路由变化：当导航到 /stock（无参数）时，重置分析状态
    // 使用 location.state.reset 来检测导航栏点击事件（即使已经在 /stock 页面）
    useEffect(() => {
        // 如果是纯净的 /stock 路径（没有查询参数），重置状态开始新分析
        if (location.pathname === '/stock' && !location.search) {
            setTicker('');
            setResult(null);
            setError('');
            setActiveTab('analysis');
            setTaskProgress(0);
            setTaskStep('');
        }
    }, [location.pathname, location.search, (location.state as any)?.reset]); // 监听 state.reset 变化

    // Task progress state
    const [taskProgress, setTaskProgress] = useState(0);
    const [taskStep, setTaskStep] = useState('');

    // Initialize task polling hook
    const { startPolling } = useTaskPolling({
        onTaskComplete: (taskResult) => {
            console.log('Task completed:', taskResult);
            setResult(taskResult);
            setLoading(false);
            setTaskProgress(100);
                setTaskStep(t('stock.taskComplete'));
        },
        onTaskError: (errorMsg) => {
            console.error('Task failed:', errorMsg);
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

    const handleAnalyze = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!user) {
            navigate('/login');
            return;
        }

        setLoading(true);
        setError('');
        setResult(null);
        setTaskProgress(0);
        setTaskStep('');

        try {
            // Create async task
            const response = await api.post('/stock/analyze', {
                ticker,
                style,
                async: true // Use async mode
            });

            if (response.data.success && response.data.task_id) {
                console.log('Task created:', response.data.task_id);
                setTaskStep(t('stock.taskCreated'));

                // Start polling for task status
                startPolling(response.data.task_id);
            } else {
                setError(response.data.error || 'Failed to create analysis task');
                setLoading(false);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.error || err.message || 'Failed to start analysis');
            setLoading(false);
        }
    };

    // 从叙事雷达选择股票后，切换到手动模式并触发分析 - 暂时隐藏
    // const handleSelectStockFromNarrative = (symbol: string) => {
    //     setTicker(symbol);
    //     setStockMode('manual');
    //     // 延迟触发分析，等待状态更新
    //     setTimeout(() => {
    //         handleAnalyze();
    //     }, 100);
    // };

    const getRiskClass = (score: number) => {
        if (score >= 6) return 'risk-high';
        if (score >= 4) return 'risk-med';
        return 'risk-low';
    };

    // Helper to translate risk level text
    const translateRiskLevel = (level: string | null | undefined): string => {
        if (!level) return '';
        const levelLower = level.toLowerCase();
        // If it's already a translation key format, try to translate it
        if (levelLower === 'overall risk level' || level === '综合风控等级' || level === 'Overall Risk Level') {
            return t('stock.risk.level.overall');
        }
        // Translate common risk level values
        if (levelLower === 'low' || level === '低') return t('stock.risk.level.low');
        if (levelLower === 'medium' || level === '中' || levelLower === 'moderate') return t('stock.risk.level.medium');
        if (levelLower === 'high' || level === '高') return t('stock.risk.level.high');
        // If no match, return original
        return level;
    };

    const getSentimentClass = (score: number) => {
        if (score >= 7) return 'text-warning';
        if (score >= 4) return 'text-success';
        return 'text-danger';
    };

    const getRating = (score: number) => {
        if (score >= 6) return { text: t('stock.rating.watch'), class: 'text-warning' };
        if (score >= 4) return { text: t('stock.rating.neutral'), class: 'text-warning' };
        if (score >= 2) return { text: t('stock.rating.add'), class: 'text-success' };
        return { text: t('stock.rating.buy'), class: 'text-success' };
    };

    // Add timeout for auth loading to prevent infinite loading
    useEffect(() => {
        if (authLoading) {
            const timeout = setTimeout(() => {
                console.warn("Auth loading timeout in Home page");
            }, 10000); // 10 second warning
            return () => clearTimeout(timeout);
        }
    }, [authLoading]);

    if (authLoading) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <div className="text-center">
                    <div className="spinner mx-auto mb-4"></div>
                    <p className="text-white">{t('stock.loading')}</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4 text-white">
                <h1 className="text-4xl font-bold tracking-tight">{t('stock.pageTitle')}</h1>
                <p className="text-lg text-slate-400 max-w-2xl">
                    {t('stock.loginRequired')}
                </p>
                <div className="flex gap-4">
                    <Button onClick={() => navigate('/login')} className="btn-primary" size="lg">{t('stock.login') || t('nav.login')}</Button>
                </div>
            </div>
        );
    }

    const isZh = i18n.language.startsWith('zh');

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ color: 'var(--foreground)' }}>
            <Helmet>
                <title>{isZh ? '股票分析 - AlphaGBM | AI智能选股工具' : 'Stock Analysis - AlphaGBM | AI Smart Stock Picker'}</title>
                <meta name="description" content={isZh
                    ? '使用 AlphaGBM AI 智能股票分析工具，获取基本面评分、情绪分析、目标价格预测。支持多种投资风格，帮助您做出明智的投资决策。'
                    : 'Use AlphaGBM AI stock analysis tool to get fundamental scoring, sentiment analysis, and price target predictions. Supports multiple investment styles.'}
                />
                <link rel="canonical" href="https://alphagbm.com/stock" />
                <meta property="og:url" content="https://alphagbm.com/stock" />
                <meta property="og:title" content={isZh ? '股票分析 - AlphaGBM' : 'Stock Analysis - AlphaGBM'} />
            </Helmet>
            <style>{styles}</style>

            {/* Custom Tabs */}
            <div className="card shadow-lg mb-4" style={{ padding: '0' }}>
                <div className="flex border-b" style={{ borderColor: 'var(--border)' }}>
                    <button
                        onClick={() => setActiveTab('analysis')}
                        className={`flex-1 px-3 sm:px-6 py-3 text-center font-medium transition-all duration-200 text-sm sm:text-base ${activeTab === 'analysis'
                            ? 'border-b-2 text-primary'
                            : 'text-muted-foreground hover:text-foreground'
                            }`}
                        style={{
                            borderBottomColor: activeTab === 'analysis' ? 'var(--primary)' : 'transparent',
                            background: 'none',
                            border: 'none',
                            borderBottomWidth: '2px',
                            borderBottomStyle: 'solid',
                            fontSize: '1rem'
                        }}
                    >
                        <i className="bi bi-graph-up mr-2"></i>
                        {t('stock.tab.analysis')}
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex-1 px-3 sm:px-6 py-3 text-center font-medium transition-all duration-200 text-sm sm:text-base ${activeTab === 'history'
                            ? 'border-b-2 text-primary'
                            : 'text-muted-foreground hover:text-foreground'
                            }`}
                        style={{
                            borderBottomColor: activeTab === 'history' ? 'var(--primary)' : 'transparent',
                            background: 'none',
                            border: 'none',
                            borderBottomWidth: '2px',
                            borderBottomStyle: 'solid',
                            fontSize: '1rem'
                        }}
                    >
                        <i className="bi bi-clock-history mr-2"></i>
                        {t('stock.tab.history')}
                    </button>
                </div>
            </div>

            {/* Stock Analysis Tab */}
            <div style={{ display: activeTab === 'analysis' ? 'block' : 'none' }}>
                {/* 选股模式切换 */}
                <div className="card shadow-lg mb-4 p-4 sm:p-6">
                    <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
                        <i className="bi bi-search"></i>
                        {t('stock.form.title')}
                    </h5>

                    {/* 模式切换按钮 - 叙事雷达暂时隐藏 */}
                    {/* <div className="flex gap-3 mb-5">
                        <button
                            onClick={() => setStockMode('manual')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg border transition-all ${
                                stockMode === 'manual'
                                    ? 'bg-[#0D9B97]/20 border-[#0D9B97] text-[#0D9B97]'
                                    : 'bg-[#1c1c1e] border-[#3f3f46] text-slate-400 hover:border-[#0D9B97]/50'
                            }`}
                        >
                            <i className="bi bi-pencil-square"></i>
                            <span className="font-medium">{i18n.language === 'zh' ? '自选股票' : 'Manual Selection'}</span>
                        </button>
                        <button
                            onClick={() => setStockMode('narrative')}
                            className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg border transition-all ${
                                stockMode === 'narrative'
                                    ? 'bg-[#0D9B97]/20 border-[#0D9B97] text-[#0D9B97]'
                                    : 'bg-[#1c1c1e] border-[#3f3f46] text-slate-400 hover:border-[#0D9B97]/50'
                            }`}
                        >
                            <i className="bi bi-broadcast"></i>
                            <span className="font-medium">{i18n.language === 'zh' ? '叙事雷达' : 'Narrative Radar'}</span>
                        </button>
                    </div> */}

                    {/* 自选股票模式 - 现在是唯一模式 */}
                    <form onSubmit={handleAnalyze} className="grid grid-cols-1 gap-4 sm:grid-cols-1 md:grid-cols-[1fr_2fr_auto] sm:gap-4">
                        <div>
                            <label className="block text-muted mb-2" style={{ fontSize: '0.95rem', fontWeight: 500 }}>{t('stock.form.style')}</label>
                            <CustomSelect
                                options={[
                                    {
                                        value: 'quality',
                                        label: i18n.language === 'zh' ? 'Quality (质量)' : 'Quality'
                                    },
                                    {
                                        value: 'value',
                                        label: i18n.language === 'zh' ? 'Value (价值)' : 'Value'
                                    },
                                    {
                                        value: 'growth',
                                        label: i18n.language === 'zh' ? 'Growth (成长)' : 'Growth'
                                    },
                                    {
                                        value: 'momentum',
                                        label: i18n.language === 'zh' ? 'Momentum (趋势)' : 'Momentum'
                                    }
                                ]}
                                value={style}
                                onChange={setStyle}
                                placeholder={t('stock.form.stylePlaceholder')}
                                className="w-full"
                            />
                        </div>
                        <div>
                            <label className="block text-muted mb-2" style={{ fontSize: '0.95rem', fontWeight: 500 }}>{t('stock.form.ticker')}</label>
                            <StockSearchInput
                                placeholder={t('stock.form.tickerPlaceholder')}
                                value={ticker}
                                onChange={setTicker}
                            />
                        </div>
                        <div className="flex items-end">
                            <Button type="submit" disabled={loading} className="btn-primary h-11 px-6">
                                <i className="bi bi-graph-up mr-2"></i>
                                {loading ? t('stock.form.analyzing') : t('stock.form.analyze')}
                            </Button>
                        </div>
                    </form>

                    <div className="mt-4 p-3 rounded" style={{ background: 'var(--muted)', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
                        {t(`stock.style.${style}.desc`)}
                    </div>

                    {/* 叙事雷达模式 - 暂时隐藏 */}
                    {/* {stockMode === 'narrative' && (
                        <NarrativeRadar
                            onSelectStock={handleSelectStockFromNarrative}
                            hideTitle={true}
                        />
                    )} */}

                    {error && (
                        <div className="mt-4 p-3 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                            <div className="font-semibold mb-2">{t('stock.error.title')}</div>
                            <div className="whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                                {error.length > 500 ? (
                                    <>
                                        <div>{error.substring(0, 500)}...</div>
                                        <details className="mt-2">
                                            <summary className="cursor-pointer text-red-300 hover:text-red-200">
                                                {t('stock.error.viewFull')}
                                            </summary>
                                            <div className="mt-2 p-2 bg-red-500/5 rounded text-xs">
                                                {error}
                                            </div>
                                        </details>
                                    </>
                                ) : (
                                    error
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Market Warnings */}
                {result && result.data?.market_warnings && (
                    <MarketWarnings warnings={result.data.market_warnings} />
                )}

                {/* Investment Philosophy */}
                <InvestmentPhilosophy />

                {/* Loading with Progress */}
                {loading && (
                    <div className="text-center py-12">
                        <div className="spinner mx-auto mb-4"></div>

                        {/* Progress Bar */}
                        {taskProgress > 0 && (
                            <div className="max-w-md mx-auto mb-4">
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="text-muted">{t('stock.loading.progress')}</span>
                                    <span className="text-primary font-semibold">{taskProgress}%</span>
                                </div>
                                <div style={{
                                    width: '100%',
                                    backgroundColor: 'var(--muted)',
                                    borderRadius: '8px',
                                    height: '8px',
                                    overflow: 'hidden'
                                }}>
                                    <div
                                        style={{
                                            width: `${taskProgress}%`,
                                            backgroundColor: 'var(--primary)',
                                            height: '100%',
                                            borderRadius: '8px',
                                            transition: 'width 0.3s ease'
                                        }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Current Step */}
                        <p className="text-muted">
                            {taskStep || t('stock.loading.connecting')}
                        </p>

                        {/* Task Status Info - Hidden per user request */}
                    </div>
                )}

                {/* Historical Analysis Indicator */}
                {result && result.history_metadata?.is_from_history && (
                    <div className="card shadow-lg mb-4" style={{
                        padding: '1rem 1.5rem',
                        background: 'linear-gradient(135deg, rgba(13, 155, 151, 0.1) 0%, rgba(13, 155, 151, 0.05) 100%)',
                        border: '1px solid rgba(13, 155, 151, 0.3)'
                    }}>
                        <div className="flex items-center gap-3">
                            <i className="bi bi-clock-history text-primary" style={{ fontSize: '1.2rem' }}></i>
                            <div>
                                <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '1rem' }}>
                                    {t('stock.history.title')}
                                </span>
                                {result.history_metadata.created_at && (
                                    <span className="text-muted ml-3" style={{ fontSize: '0.9rem' }}>
                                        {t('stock.history.analyzedAt')}{new Date(result.history_metadata.created_at).toLocaleString()}
                                    </span>
                                )}
                            </div>
                            <div className="ml-auto">
                                <span className="badge-primary">
                                    <i className="bi bi-archive mr-1"></i>
                                    {t('stock.report.historicalData')}
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Dashboard Results */}
                {result && result.success && (() => {
                    const d = result.data;
                    const r = result.risk;
                    const sentiment = d.market_sentiment ?? 5.0;
                    const rating = getRating(r.score);
                    const styleName = style === 'quality' ? t('landing.styles.quality.name') : 
                                     style === 'value' ? t('landing.styles.value.name') :
                                     style === 'growth' ? t('landing.styles.growth.name') :
                                     t('landing.styles.momentum.name');
                    const pricePosition = d.week52_high && d.week52_low && d.week52_high > d.week52_low
                        ? ((d.price - d.week52_low) / (d.week52_high - d.week52_low) * 100)
                        : 50;

                    return (
                        <div id="dashboard" className="space-y-6">
                            {/* Metrics Row - 4 cards */}
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {/* Price */}
                                <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                    <div className="metric-label">
                                        <i className="bi bi-graph-up mr-2"></i>
                                        {t('stock.metrics.price')}
                                    </div>
                                    <div className="metric-value">{d.currency_symbol}{d.price?.toFixed(2)}</div>
                                    <small className="text-muted" style={{ fontSize: '0.85rem' }}>
                                        52w: {d.currency_symbol}{d.week52_low?.toFixed(2)} - {d.currency_symbol}{d.week52_high?.toFixed(2)}
                                    </small>
                                </div>

                                {/* Sentiment */}
                                <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                    <div className="metric-label">
                                        <i className="bi bi-emoji-smile mr-2"></i>
                                        {t('stock.metrics.sentiment')}
                                    </div>
                                    <div className={`metric-value ${getSentimentClass(sentiment)}`}>{sentiment.toFixed(1)}</div>
                                    <small className="text-muted" style={{ fontSize: '0.85rem' }}>{t('stock.metrics.sentimentDesc')}</small>
                                </div>

                                {/* Risk Level */}
                                <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                    <div className="metric-label">
                                        <i className="bi bi-shield-check mr-2"></i>
                                        {t('stock.metrics.risk')}
                                    </div>
                                    <div className={`metric-value ${getRiskClass(r.score)}`}>{translateRiskLevel(r.level)}</div>
                                    <small className="text-danger" style={{ fontSize: '0.85rem' }}>Score: {r.score}/10</small>
                                </div>

                                {/* Suggested Position */}
                                <div className="card shadow-md border-primary" style={{ padding: '1.5rem', borderWidth: '2px' }}>
                                    <div className="metric-label text-primary">
                                        <i className="bi bi-pie-chart-fill mr-2"></i>
                                        {t('stock.metrics.position')}
                                    </div>
                                    <div className="metric-value text-primary">{r.suggested_position}%</div>
                                    <small className="text-muted" style={{ fontSize: '0.85rem' }}>{t('stock.metrics.positionDesc')}</small>
                                </div>
                            </div>

                            {/* Second Row: Chart + Risk | AI Report */}
                            <div className="grid grid-cols-1 lg:grid-cols-[5fr_7fr] gap-6">
                                {/* Left Column */}
                                <div className="space-y-4">
                                    {/* Price Chart */}
                                    <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                        <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                            <i className="bi bi-graph-up-arrow"></i>
                                            {t('stock.chart.title')}
                                        </h5>
                                        <PriceChart dates={d.history_dates} prices={d.history_prices} />
                                    </div>

                                    {/* Risk Flags */}
                                    <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                        <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                            <i className="bi bi-exclamation-triangle"></i>
                                            {t('stock.risks.title')}
                                        </h5>
                                        <ul>
                                            {r.flags && r.flags.length > 0 ? (
                                                r.flags.map((flag: string, idx: number) => (
                                                    <li key={idx} className="list-group-item text-danger">{t('stock.risks.warning')} {flag}</li>
                                                ))
                                            ) : (
                                                <li className="list-group-item text-success">{t('stock.risks.noRisk')}</li>
                                            )}
                                        </ul>
                                    </div>
                                </div>

                                {/* Right Column: AI Report */}
                                <div className="card shadow-md" style={{ display: 'flex', flexDirection: 'column' }}>
                                    <div style={{
                                        padding: '1.5rem',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        borderBottom: '1px solid var(--border)'
                                    }}>
                                        <h5 className="mb-0 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                            <i className="bi bi-stars"></i>
                                            {t('stock.aiReport.title')}
                                        </h5>
                                        <span className="badge-primary">{t('stock.aiReport.generated')}</span>
                                    </div>
                                    <div className="overflow-auto" style={{ maxHeight: '650px', padding: '1.5rem' }}>
                                        <div
                                            className="ai-summary"
                                            dangerouslySetInnerHTML={{ __html: renderMarkdown(result.report || t('stock.report.noDataAvailable')) }}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Full Text Report */}
                            <div className="card shadow-md">
                                <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }}>
                                    <h5 className="mb-0 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                        <i className="bi bi-file-text"></i>
                                        {t('stock.report.title')}
                                    </h5>
                                </div>
                                <div style={{ padding: '1.5rem', lineHeight: 1.8, fontSize: '1rem' }}>
                                    {/* Report Header */}
                                    <div className="text-report-section" style={{ borderBottom: '2px solid var(--primary)', paddingBottom: '1.5rem' }}>
                                        <div className="text-center mb-4">
                                            <h3 style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                                                {t('stock.report.fullTitle', { name: d.name, symbol: d.symbol })}
                                            </h3>
                                            <p style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem' }}>
                                                {t('stock.report.date')}{new Date().toLocaleDateString(i18n.language === 'zh' ? 'zh-CN' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                                            </p>
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>{t('stock.report.header.rating')}</div>
                                                <div className={rating.class} style={{ fontSize: '1.5rem', fontWeight: 700 }}>{rating.text}</div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>{t('stock.report.header.targetPrice')}</div>
                                                <div style={{ color: r.suggested_position === 0 ? 'var(--bear)' : 'var(--primary)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {d.currency_symbol}{(d.target_price || d.price)?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>{t('stock.report.header.currentPrice')}</div>
                                                <div style={{ color: 'var(--foreground)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {d.currency_symbol}{d.price?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>{t('stock.report.header.position')}</div>
                                                <div style={{ color: 'var(--primary)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {r.suggested_position}%
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Section 1: Core Analysis */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">{t('stock.report.section1')}</div>
                                        <div style={{ color: 'var(--muted-foreground)' }}>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.core.style')}</strong>{styleName}。</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.core.conclusion')}</strong>
                                                {!d.is_etf_or_fund && d.growth !== undefined ? 
                                                    t('stock.report.core.conclusionText', { 
                                                        position: pricePosition.toFixed(1), 
                                                        growth: (d.growth * 100).toFixed(2), 
                                                        margin: ((d.margin || 0) * 100).toFixed(2),
                                                        score: r.score,
                                                        level: r.level
                                                    }) :
                                                    t('stock.report.core.conclusionText', { 
                                                        position: pricePosition.toFixed(1), 
                                                        growth: 'N/A', 
                                                        margin: 'N/A',
                                                        score: r.score,
                                                        level: r.level
                                                    }).replace(/基本面数据显示营收增长率为.*?利润率为.*?。/g, '')
                                                }
                                            </p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.core.advice')}</strong>{rating.text}。{t('stock.report.advice.position')}{r.suggested_position}%。
                                                {r.suggested_position === 0 ? t('stock.report.core.adviceHigh') : r.score >= 4 ? t('stock.report.core.adviceMedium') : t('stock.report.core.adviceLow')}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Section 2: Company Overview */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">{t('stock.report.section2', { type: d.is_etf_or_fund ? t('stock.report.section2.etf') : t('stock.report.section2.company') })}</div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div><div className="text-report-label">{t('stock.report.overview.code')}</div><div className="text-report-value">{d.symbol}</div></div>
                                            <div><div className="text-report-label">{t('stock.report.overview.name')}</div><div className="text-report-value">{d.name}</div></div>
                                            {!d.is_etf_or_fund && (
                                                <>
                                                    <div><div className="text-report-label">{t('stock.report.overview.sector')}</div><div className="text-report-value">{d.sector || t('stock.report.overview.noData')}</div></div>
                                                    <div><div className="text-report-label">{t('stock.report.overview.industry')}</div><div className="text-report-value">{d.industry || t('stock.report.overview.noData')}</div></div>
                                                </>
                                            )}
                                        </div>
                                        {/* Company News */}
                                        {d.company_news && Array.isArray(d.company_news) && d.company_news.length > 0 && (
                                            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }}>
                                                <div style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '1rem', marginBottom: '0.8rem' }}>{t('stock.report.overview.news')}</div>
                                                <ul style={{ color: 'var(--muted-foreground)', lineHeight: 1.8, fontSize: '0.95rem', margin: 0, paddingLeft: '1.5rem' }}>
                                                    {d.company_news.slice(0, 5).map((news: any, idx: number) => (
                                                        <li key={idx} style={{ marginBottom: '0.8rem' }}>
                                                            <strong>{news.title || t('stock.report.overview.noTitle')}</strong>
                                                            {news.publisher && <span style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem' }}> - {news.publisher}</span>}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>

                                    {/* Section 3: Financial Analysis */}
                                    {!d.is_etf_or_fund && (
                                        <div className="text-report-section">
                                            <div className="text-report-title">{t('stock.report.section3')}</div>
                                            <p style={{ color: 'var(--muted-foreground)', marginBottom: '1rem' }}>{t('stock.report.financial.intro')}</p>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.financial.revenue')}</div>
                                                    <div className={`text-report-value ${d.growth < 0 ? 'text-danger' : d.growth > 0.2 ? 'text-success' : ''}`} style={{ fontSize: '1.1rem' }}>
                                                        {((d.growth || 0) * 100).toFixed(2)}%
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)' }}>{d.growth > 0.2 ? t('stock.report.financial.strong') : d.growth > 0 ? t('stock.report.financial.stable') : d.growth < 0 ? t('stock.report.financial.negative') : t('stock.report.overview.noData')}</small>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.financial.margin')}</div>
                                                    <div className={`text-report-value ${d.margin < 0.05 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem' }}>
                                                        {((d.margin || 0) * 100).toFixed(2)}%
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)' }}>{d.margin > 0.15 ? t('stock.report.financial.excellent') : d.margin > 0.1 ? t('stock.report.financial.good') : d.margin > 0.05 ? t('stock.report.financial.average') : t('stock.report.financial.weak')}</small>
                                                </div>
                                            </div>
                                            <p style={{ color: 'var(--muted-foreground)', marginTop: '1rem' }}>
                                                <strong style={{ color: 'var(--foreground)' }}>{t('stock.report.financial.assessment')}</strong>
                                                {d.growth > 0.1 && d.margin > 0.1 ? t('stock.report.financial.assessmentStrong') :
                                                    d.growth < 0 || d.margin < 0.05 ? t('stock.report.financial.assessmentWeak') :
                                                        t('stock.report.financial.assessmentNormal')}
                                            </p>
                                        </div>
                                    )}

                                    {/* Section 4: Valuation Analysis */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">{t('stock.report.section4')}</div>
                                        
                                        {/* 价格与技术面 */}
                                        <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                                            <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>{t('stock.report.valuation.price')}</div>
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.valuation.currentPrice')}</div>
                                                    <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.currency_symbol}{d.price?.toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.valuation.week52')}</div>
                                                    <div className="text-report-value" style={{ fontSize: '0.95rem' }}>
                                                        {d.currency_symbol}{d.week52_low?.toFixed(2)} - {d.currency_symbol}{d.week52_high?.toFixed(2)}
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>{t('stock.report.valuation.percentile', { percent: pricePosition.toFixed(1) })}</small>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.valuation.trend')}</div>
                                                    <div className="text-report-value" style={{ fontSize: '0.95rem', fontWeight: 500 }}>
                                                        {d.price > d.ma50 && d.ma50 > d.ma200 ? t('stock.report.valuation.trendBull') : d.price < d.ma200 ? t('stock.report.valuation.trendBear') : t('stock.report.valuation.trendSideways')}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">{t('stock.report.valuation.ma')}</div>
                                                    <div className="text-report-value" style={{ fontSize: '0.85rem' }}>
                                                        MA50: {d.currency_symbol}{d.ma50?.toFixed(2) || 'N/A'}<br/>
                                                        MA200: {d.currency_symbol}{d.ma200?.toFixed(2) || 'N/A'}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* 估值指标 */}
                                        {!d.is_etf_or_fund && (
                                            <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>{t('stock.report.valuation.indicators')}</div>
                                                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                                    <div>
                                                        <div className="text-report-label">{t('stock.report.valuation.pe')}</div>
                                                        <div className={`text-report-value ${d.pe && d.pe > 30 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                            {d.pe ? d.pe.toFixed(2) : 'N/A'}
                                                        </div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.pe && d.pe > 30 ? t('stock.report.valuation.expensive') : d.pe && d.pe > 15 ? t('stock.report.valuation.reasonable') : d.pe > 0 ? t('stock.report.valuation.cheap') : t('stock.report.overview.noData')}
                                                        </small>
                                                    </div>
                                                    <div>
                                                        <div className="text-report-label">{t('stock.report.valuation.forwardPe')}</div>
                                                        <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.forward_pe ? d.forward_pe.toFixed(2) : 'N/A'}</div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.forward_pe && d.forward_pe < d.pe ? t('stock.report.valuation.improving') : d.forward_pe && d.forward_pe > d.pe ? t('stock.report.valuation.deteriorating') : ''}
                                                        </small>
                                                    </div>
                                                    <div>
                                                        <div className="text-report-label">{t('stock.report.valuation.peg')}</div>
                                                        <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.peg ? d.peg.toFixed(2) : 'N/A'}</div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.peg && d.peg < 1 ? t('stock.report.valuation.reasonable') : d.peg > 0 ? t('stock.report.valuation.expensive') : t('stock.report.overview.noData')}
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* 市场情绪指标 */}
                                        {d.options_data && (d.options_data.vix !== null || d.options_data.put_call_ratio !== null) && (
                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>{t('stock.report.valuation.sentiment')}</div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    {d.options_data.vix !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.vix')}</div>
                                                            <div className={`text-report-value ${d.options_data.vix > 30 ? 'text-danger' : d.options_data.vix > 20 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                                {d.options_data.vix.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                                {d.options_data.vix_change ? (d.options_data.vix_change > 0 ? '↑' : '↓') + Math.abs(d.options_data.vix_change).toFixed(1) + '%' : ''} 
                                                                {d.options_data.vix > 30 ? t('stock.report.valuation.highVol') : d.options_data.vix > 20 ? t('stock.report.valuation.midVol') : t('stock.report.valuation.lowVol')}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.options_data.put_call_ratio !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.putCall')}</div>
                                                            <div className={`text-report-value ${d.options_data.put_call_ratio > 1.2 ? 'text-danger' : d.options_data.put_call_ratio > 1.0 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                                {d.options_data.put_call_ratio.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                                {d.options_data.put_call_ratio > 1.2 ? t('stock.report.valuation.bearish') : d.options_data.put_call_ratio > 1.0 ? t('stock.report.valuation.slightlyBearish') : d.options_data.put_call_ratio < 0.8 ? t('stock.report.valuation.bullish') : t('stock.report.valuation.neutral')}
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Macro Data */}
                                        {d.macro_data && (d.macro_data.treasury_10y !== null || d.macro_data.dxy !== null || d.macro_data.gold !== null || d.macro_data.oil !== null) && (
                                            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                                                <div className="text-report-title" style={{ fontSize: '1.1rem', marginBottom: '0.8rem' }}>{t('stock.report.valuation.macro')}</div>
                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                    {d.macro_data.treasury_10y !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.treasury')}</div>
                                                            <div className={`text-report-value ${d.macro_data.treasury_10y > 4.5 ? 'text-danger' : d.macro_data.treasury_10y > 3.5 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1rem' }}>
                                                                {d.macro_data.treasury_10y.toFixed(2)}%
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.treasury_10y_change ? (d.macro_data.treasury_10y_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.treasury_10y_change).toFixed(2) + '%' : ''} {d.macro_data.treasury_10y > 4.5 ? t('stock.report.valuation.tight') : t('stock.report.valuation.normal')}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.dxy !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.dxy')}</div>
                                                            <div className={`text-report-value ${d.macro_data.dxy > 105 ? 'text-warning' : ''}`} style={{ fontSize: '1rem' }}>
                                                                {d.macro_data.dxy.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.dxy_change ? (d.macro_data.dxy_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.dxy_change).toFixed(2) + '%' : ''} {d.macro_data.dxy > 105 ? t('stock.report.valuation.strongDollar') : t('stock.report.valuation.normal')}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.gold !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.gold')}</div>
                                                            <div className="text-report-value" style={{ fontSize: '1rem' }}>${d.macro_data.gold.toFixed(2)}</div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.gold_change ? (d.macro_data.gold_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.gold_change).toFixed(2) + '%' : ''} {d.macro_data.gold_change > 2 ? t('stock.report.valuation.safeHaven') : t('stock.report.valuation.normal')}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.oil !== null && (
                                                        <div>
                                                            <div className="text-report-label">{t('stock.report.valuation.oil')}</div>
                                                            <div className="text-report-value" style={{ fontSize: '1rem' }}>${d.macro_data.oil.toFixed(2)}</div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.oil_change ? (d.macro_data.oil_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.oil_change).toFixed(2) + '%' : ''} {t('stock.report.valuation.normal')}
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Earnings Date Reminder */}
                                        {d.earnings_dates && Array.isArray(d.earnings_dates) && d.earnings_dates.length > 0 && (
                                            <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: '#1e293b', borderLeft: '3px solid var(--primary)', borderRadius: '4px' }}>
                                                <strong style={{ color: 'var(--primary)' }}>{t('stock.report.valuation.earnings')}</strong>
                                                <span style={{ color: 'var(--muted-foreground)' }}>{t('stock.report.valuation.earningsText', { dates: d.earnings_dates.join(', ') })}</span>
                                            </div>
                                        )}

                                        {/* Economic Events */}
                                        {d.macro_data && (d.macro_data.fed_meetings?.length > 0 || d.macro_data.cpi_releases?.length > 0 || d.macro_data.china_events?.length > 0) && (
                                            <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: '#1e293b', borderLeft: '3px solid #8b5cf6', borderRadius: '4px' }}>
                                                <strong style={{ color: '#8b5cf6' }}>{t('stock.report.valuation.events')}</strong>
                                                <div style={{ color: 'var(--muted-foreground)', marginTop: '0.5rem' }}>
                                                    {d.macro_data.fed_meetings?.length > 0 && (
                                                        <div style={{ marginBottom: '0.5rem' }}>
                                                            <strong style={{ color: 'var(--primary)' }}>{t('stock.report.valuation.us')}</strong>
                                                            <div style={{ marginLeft: '1rem', marginTop: '0.3rem' }}>
                                                                <div>{t('stock.report.valuation.fed')}{d.macro_data.fed_meetings.map((m: any) => `${m.date} (${t('stock.report.valuation.daysLater', { days: m.days_until })}${m.has_dot_plot ? t('stock.report.valuation.hasDotPlot') : ''})`).join(i18n.language === 'zh' ? '、' : ', ')}</div>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {d.macro_data.china_events?.length > 0 && (
                                                        <div style={{ marginBottom: '0.5rem' }}>
                                                            <strong style={{ color: 'var(--bear)' }}>{t('stock.report.valuation.china')}</strong>
                                                            <div style={{ marginLeft: '1rem', marginTop: '0.3rem' }}>
                                                                {d.macro_data.china_events.map((e: any, idx: number) => (
                                                                    <div key={idx}>{e.type}：{e.date} ({t('stock.report.valuation.daysLater', { days: e.days_until })}{e.data_month ? t('stock.report.valuation.dataMonth', { month: e.data_month }) : ''})</div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Geopolitical Risk */}
                                        {d.macro_data?.geopolitical_risk !== null && d.macro_data?.geopolitical_risk !== undefined && (
                                            <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: '#1e293b', borderLeft: `3px solid ${d.macro_data.geopolitical_risk >= 7 ? 'var(--bear)' : d.macro_data.geopolitical_risk >= 5 ? 'var(--warning)' : 'var(--bull)'}`, borderRadius: '4px' }}>
                                                <strong style={{ color: d.macro_data.geopolitical_risk >= 7 ? 'var(--bear)' : d.macro_data.geopolitical_risk >= 5 ? 'var(--warning)' : 'var(--bull)' }}>{t('stock.report.valuation.geopolitical')}</strong>
                                                <span style={{ color: 'var(--foreground)', fontSize: '1.1rem', fontWeight: 600, marginLeft: '0.5rem' }}>{d.macro_data.geopolitical_risk}/10</span>
                                                <span style={{ color: 'var(--muted-foreground)', marginLeft: '0.5rem' }}>
                                                    {d.macro_data.geopolitical_risk >= 7 ? t('stock.report.valuation.geoHigh') : d.macro_data.geopolitical_risk >= 5 ? t('stock.report.valuation.geoMedium') : t('stock.report.valuation.geoLow')}
                                                </span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Section 5: Risk Warning */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">{t('stock.report.section5')}</div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-report-label">{t('stock.report.risk.score')}</div>
                                                <div className={`text-report-value ${getRiskClass(r.score)}`} style={{ fontSize: '1.3rem', fontWeight: 700 }}>{r.score}/10</div>
                                            </div>
                                            <div>
                                                <div className="text-report-label">{t('stock.report.risk.level')}</div>
                                                <div className={`text-report-value ${getRiskClass(r.score)}`} style={{ fontSize: '1.1rem' }}>{translateRiskLevel(r.level)}</div>
                                            </div>
                                        </div>
                                        {r.flags && r.flags.length > 0 ? (
                                            <div style={{ marginTop: '1rem' }}>
                                                <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.risk.factors')}</strong></p>
                                                <ul style={{ paddingLeft: '1.5rem', color: 'var(--muted-foreground)' }}>
                                                    {r.flags.map((flag: string, idx: number) => (
                                                        <li key={idx} style={{ marginBottom: '0.5rem' }}>{flag}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ) : (
                                            <div style={{ marginTop: '1rem', color: 'var(--bull)' }}>
                                                <p>{t('stock.report.risk.noRisk')}</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Section 6: Investment Advice */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">{t('stock.report.section6')}</div>
                                        <div style={{ color: 'var(--muted-foreground)' }}>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.rating')}</strong><span className={rating.class} style={{ fontSize: '1.1rem', fontWeight: 600 }}>{rating.text}</span></p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.targetPrice')}</strong>{d.currency_symbol}{(d.target_price || d.price)?.toFixed(2)}{t('stock.report.advice.targetPriceDesc')}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.position')}</strong><span style={{ color: r.suggested_position === 0 ? 'var(--bear)' : 'var(--primary)', fontSize: '1.1rem', fontWeight: 600 }}>{r.suggested_position}%</span>{t('stock.report.advice.positionDesc', { style: styleName })}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.entry')}</strong>{generateEntryStrategy(d.price || 0, d.target_price || d.price || 0, style, r.score, r.suggested_position, t)}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.takeprofit')}</strong>{generateTakeProfitStrategy(d.price || 0, d.target_price || d.price || 0, style, d.currency_symbol || '$', t)}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.stop')}</strong>{t('stock.report.advice.stopText', { symbol: d.currency_symbol, price: d.stop_loss_price?.toFixed(2) || (d.price * 0.85).toFixed(2), method: d.stop_loss_method || t('stock.report.advice.stopMethod') })}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.advice.holding')}</strong>{t('stock.report.advice.holdingText', { 
                                                style: styleName, 
                                                period: style === 'quality' ? t('stock.report.advice.holdingQuality') : 
                                                        style === 'value' ? t('stock.report.advice.holdingValue') : 
                                                        style === 'growth' ? t('stock.report.advice.holdingGrowth') : 
                                                        t('stock.report.advice.holdingMomentum')
                                            })}</p>
                                        </div>
                                    </div>

                                    {/* Disclaimer */}
                                    <div className="text-report-section" style={{ borderTop: '2px solid var(--bear)', paddingTop: '1.5rem', marginTop: '2rem' }}>
                                        <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--bear)', padding: '1rem', borderRadius: '4px' }}>
                                            <h5 style={{ color: 'var(--bear)', fontSize: '1rem', fontWeight: 600, marginBottom: '0.8rem' }}>{t('stock.report.disclaimer.title')}</h5>
                                            <div style={{ color: 'var(--muted-foreground)', lineHeight: 1.8, fontSize: '0.9rem' }}>
                                                <p style={{ marginBottom: '0.5rem' }}><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.disclaimer.disclaimer')}</strong>{t('stock.report.disclaimer.disclaimerText')}</p>
                                                <p style={{ marginBottom: '0.5rem' }}><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.disclaimer.risk')}</strong>{t('stock.report.disclaimer.riskText')}</p>
                                                <p style={{ marginBottom: '0' }}><strong style={{ color: 'var(--foreground)' }}>{t('stock.report.disclaimer.ai')}</strong>{t('stock.report.disclaimer.aiText')}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })()}

                {/* Option Trading Opportunities Guide */}
                {result && result.success && (() => {
                    const d = result.data;
                    // Determine trend based on price vs MA
                    const trend = d.price > d.ma50 && d.ma50 > d.ma200 ? 'uptrend' :
                                  d.price < d.ma200 ? 'downtrend' : 'sideways';

                    return (
                        <div className="option-opportunity-guide" style={{
                            marginTop: '2rem',
                            padding: '1.5rem',
                            background: 'linear-gradient(135deg, rgba(13, 155, 151, 0.1) 0%, rgba(13, 155, 151, 0.05) 100%)',
                            border: '1px solid rgba(13, 155, 151, 0.3)',
                            borderRadius: '12px'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                <i className="bi bi-lightning-charge-fill" style={{ fontSize: '1.5rem', color: 'var(--primary)' }}></i>
                                <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, color: 'var(--foreground)' }}>
                                    {t('stock.optionOpportunity.title')}
                                </h3>
                            </div>

                            <p style={{ color: 'var(--muted-foreground)', marginBottom: '1.25rem', fontSize: '0.95rem' }}>
                                {t('stock.optionOpportunity.desc')}
                            </p>

                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                                {trend === 'uptrend' && (
                                    <>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(34, 197, 94, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(34, 197, 94, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-graph-up-arrow" style={{ fontSize: '1.25rem', color: 'var(--bull)' }}></i>
                                                <strong style={{ color: 'var(--bull)' }}>Sell Put</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.sellPutDesc')}
                                            </p>
                                        </div>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(34, 197, 94, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(34, 197, 94, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-rocket-takeoff" style={{ fontSize: '1.25rem', color: 'var(--bull)' }}></i>
                                                <strong style={{ color: 'var(--bull)' }}>Buy Call</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.buyCallDesc')}
                                            </p>
                                        </div>
                                    </>
                                )}
                                {trend === 'downtrend' && (
                                    <>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(239, 68, 68, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(239, 68, 68, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-graph-down-arrow" style={{ fontSize: '1.25rem', color: 'var(--bear)' }}></i>
                                                <strong style={{ color: 'var(--bear)' }}>Sell Call</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.sellCallDesc')}
                                            </p>
                                        </div>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(239, 68, 68, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(239, 68, 68, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-shield-check" style={{ fontSize: '1.25rem', color: 'var(--bear)' }}></i>
                                                <strong style={{ color: 'var(--bear)' }}>Buy Put</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.buyPutDesc')}
                                            </p>
                                        </div>
                                    </>
                                )}
                                {trend === 'sideways' && (
                                    <>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(245, 158, 11, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(245, 158, 11, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-cash-stack" style={{ fontSize: '1.25rem', color: 'var(--warning)' }}></i>
                                                <strong style={{ color: 'var(--warning)' }}>Sell Put</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.sellPutSidewaysDesc')}
                                            </p>
                                        </div>
                                        <div style={{
                                            padding: '1rem',
                                            background: 'rgba(245, 158, 11, 0.1)',
                                            borderRadius: '8px',
                                            border: '1px solid rgba(245, 158, 11, 0.2)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                                <i className="bi bi-currency-dollar" style={{ fontSize: '1.25rem', color: 'var(--warning)' }}></i>
                                                <strong style={{ color: 'var(--warning)' }}>Sell Call</strong>
                                            </div>
                                            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>
                                                {t('stock.optionOpportunity.sellCallSidewaysDesc')}
                                            </p>
                                        </div>
                                    </>
                                )}
                            </div>

                            <Button
                                onClick={() => navigate(`/options?ticker=${d.symbol}`)}
                                className="btn-primary"
                                style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    background: 'var(--primary)',
                                    border: 'none'
                                }}
                            >
                                <i className="bi bi-arrow-right-circle"></i>
                                {t('stock.optionOpportunity.viewOptions', { symbol: d.symbol })}
                            </Button>
                        </div>
                    );
                })()}

                {/* Empty State */}
                {!result && !loading && (
                    <div className="text-center py-20 text-muted">
                        <i className="bi bi-graph-up text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
                        <p>{t('stock.empty')}</p>
                    </div>
                )}
            </div>

            {/* Analysis History Tab - Always Mounted but Hidden when Not Active */}
            <div style={{ display: activeTab === 'history' ? 'block' : 'none' }}>
                <StockAnalysisHistory
                    onSelectHistory={(ticker, style) => {
                        // Set ticker and style for re-analysis
                        setTicker(ticker);
                        setStyle(style);
                        setActiveTab('analysis');
                    }}
                    onViewFullReport={(analysisData) => {
                        // Display complete historical analysis (no network request needed!)
                        console.log('Displaying historical analysis from memory:', analysisData);
                        setResult(analysisData);
                        setActiveTab('analysis');

                        // Scroll to the top to show the analysis
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    tickerFilter={ticker}
                />
            </div>
        </div>
    );
}
