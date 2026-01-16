import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useNavigate } from 'react-router-dom';
import StockAnalysisHistory from '@/components/StockAnalysisHistory';
import CustomSelect from '@/components/ui/CustomSelect';
import { useTaskPolling } from '@/hooks/useTaskPolling';

// Declare global types for Chart.js and marked
declare global {
    interface Window {
        Chart: any;
        marked: any;
    }
}

// Price Chart Component using Chart.js
function PriceChart({ dates, prices }: { dates?: string[], prices?: number[] }) {
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
                <p>无历史数据</p>
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
                    {dates[0]} 至 {dates[dates.length - 1]}
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

// Style descriptions matching original
const styleDescriptions: Record<string, string> = {
    'quality': 'Quality (质量): 关注财务稳健、盈利能力强、债务水平低的优质公司，适合长期持有，最大仓位20%',
    'value': 'Value (价值): 寻找被市场低估的股票，关注低PE、低PEG，追求安全边际，最大仓位10%',
    'growth': 'Growth (成长): 追求高营收增长和盈利增长的公司，容忍较高估值，最大仓位15%',
    'momentum': 'Momentum (趋势): 跟随市场趋势和价格动量，快进快出，风险较高，最大仓位5%'
};

const styleNames: Record<string, string> = {
    'quality': '质量 (Quality)',
    'value': '价值 (Value)',
    'growth': '成长 (Growth)',
    'momentum': '趋势 (Momentum)'
};

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
    style: string,
    riskScore: number,
    suggestedPosition: number
): string {
    if (suggestedPosition === 0) {
        return '当前价格已超过目标价格，不建议建仓，建议观望或等待回调。';
    }

    const upsidePct = ((targetPrice - currentPrice) / currentPrice) * 100;
    
    // 如果当前价格高于目标价格
    if (upsidePct < 0) {
        return '当前价格已超过目标价格，不建议建仓，建议观望或等待回调至目标价格附近再考虑。';
    }

    // 根据上涨空间和风险评分决定建仓策略
    if (riskScore >= 6) {
        return '风险评分较高，建议保持观望，等待风险降低或价格回调后再考虑建仓。';
    } else if (riskScore >= 4) {
        // 高风险评分，分批建仓
        if (upsidePct < 5) {
            return '上涨空间有限且风险较高，建议分3批建仓，每批间隔2-3周，每批约' + (suggestedPosition / 3).toFixed(1) + '%，以降低市场波动风险。';
        } else {
            return '风险较高，建议分3批建仓，每批间隔1-2周，每批约' + (suggestedPosition / 3).toFixed(1) + '%，以降低市场波动风险。';
        }
    } else {
        // 低风险评分
        if (upsidePct < 5) {
            return '上涨空间有限，建议分2批建仓，每批间隔1-2周，每批约' + (suggestedPosition / 2).toFixed(1) + '%，谨慎控制仓位。';
        } else if (upsidePct < 10) {
            return '可考虑分2批建仓，每批间隔1周，每批约' + (suggestedPosition / 2).toFixed(1) + '%，或一次性建仓但需严格遵守仓位上限。';
        } else {
            return '可考虑一次性建仓，但需严格遵守仓位上限' + suggestedPosition + '%，并设置止损。';
        }
    }
}

// Helper to generate take profit strategy based on current price, target price and style
function generateTakeProfitStrategy(
    currentPrice: number,
    targetPrice: number,
    style: string,
    currencySymbol: string = '$'
): string {
    const upsidePct = ((targetPrice - currentPrice) / currentPrice) * 100;
    
    // 如果当前价格已经超过目标价格
    if (upsidePct < 0) {
        const overTargetPct = Math.abs(upsidePct);
        if (overTargetPct >= 20) {
            return `当前价格已超过目标价格${overTargetPct.toFixed(1)}%，建议立即减仓50%以上或全部卖出锁定利润。目标价格：${currencySymbol}${targetPrice.toFixed(2)}。`;
        } else if (overTargetPct >= 10) {
            return `当前价格已超过目标价格${overTargetPct.toFixed(1)}%，建议分批减仓：先减仓30-50%，保留部分仓位继续观察。目标价格：${currencySymbol}${targetPrice.toFixed(2)}。`;
        } else {
            return `当前价格已略高于目标价格${overTargetPct.toFixed(1)}%，建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}，可考虑分批止盈或全部止盈锁定利润。`;
        }
    }
    
    // 根据投资风格决定止盈策略
    if (style === 'quality' || style === 'value') {
        // 长期投资风格，可以分批止盈
        if (upsidePct >= 20) {
            return `建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}（目标价格）。当价格达到目标价格时，可考虑分批止盈：达到目标价格时止盈50%，超过目标价格10%时再止盈30%，超过目标价格20%时全部止盈。`;
        } else {
            return `建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}（目标价格）。当价格达到目标价格时，可考虑分批止盈或全部止盈锁定利润。如价格超过目标价格20%以上，建议立即减仓50%以上或全部卖出。`;
        }
    } else if (style === 'growth') {
        // 成长风格，中等持有期
        if (upsidePct >= 15) {
            return `建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}（目标价格）。当价格达到目标价格时，可考虑分批止盈：达到目标价格时止盈40%，超过目标价格15%时再止盈40%，超过目标价格25%时全部止盈。`;
        } else {
            return `建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}（目标价格）。当价格达到目标价格时，可考虑分批止盈或全部止盈锁定利润。如价格超过目标价格20%以上，建议立即减仓50%以上或全部卖出。`;
        }
    } else {
        // 趋势风格，短期持有
        return `建议设置止盈价格为${currencySymbol}${targetPrice.toFixed(2)}（目标价格）。当价格达到目标价格时，建议全部止盈锁定利润。如价格超过目标价格10%以上，建议立即全部卖出。`;
    }
}

// Investment Philosophy Component (constant)
function InvestmentPhilosophy() {
    const [expanded, setExpanded] = useState(true);

    return (
        <div className="philosophy-card shadow-md mb-4">
            <div
                className="cursor-pointer"
                style={{ padding: '0.9rem 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: expanded ? '1px solid var(--border)' : 'none' }}
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2" style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '1rem' }}>
                    <i className="bi bi-lightbulb-fill"></i>
                    <span>Alpha GBM 投资理念</span>
                </div>
                <div className="flex items-center gap-2 text-muted" style={{ fontSize: '0.8rem' }}>
                    <span>{expanded ? '收起' : '展开'}</span>
                    <i className={`bi bi-chevron-${expanded ? 'up' : 'down'}`}></i>
                </div>
            </div>
            {expanded && (
                <div style={{ padding: '1rem' }}>
                    {/* Core Model */}
                    <div style={{ marginBottom: '1.2rem' }}>
                        <div style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                            <strong style={{ color: 'var(--foreground)', fontSize: '0.85rem' }}>核心模型：<span className="philosophy-formula">G = B + M</span></strong>
                            。我们将股票收益<span className="philosophy-formula">G (Gain)</span>解构为基本面
                            <span className="philosophy-formula bull">B (Basics)</span>与市场动量
                            <span className="philosophy-formula warning">M (Momentum)</span>的叠加。通过量化分析识别收益与内在价值的偏离，寻找投资机会。
                        </div>
                    </div>

                    {/* Five Pillars */}
                    <div style={{ marginBottom: '1.2rem' }}>
                        <strong style={{ color: 'var(--foreground)', display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem' }}>五大支柱投资框架</strong>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 sm:gap-3 mt-2">
                            <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>怀疑主义</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>始终质疑，寻找不买入的理由</div></div>
                            <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>事前验尸</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>假设投资失败，提前识别风险点</div></div>
                            <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>严格风控</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>硬数据计算，设置仓位上限和止损</div></div>
                            <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>风格纪律</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>严格遵守投资风格，不偏离策略</div></div>
                            <div className="pillar-item"><strong style={{ color: 'var(--primary)', display: 'block', marginBottom: '0.3rem', fontSize: '0.8rem' }}>量化决策</strong><div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem' }}>用数据说话，减少情绪干扰</div></div>
                        </div>
                    </div>

                    {/* Investment Styles */}
                    <div>
                        <strong style={{ color: 'var(--foreground)', display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem' }}>投资风格</strong>
                        <div style={{ color: 'var(--muted-foreground)', fontSize: '0.75rem', marginBottom: '0.5rem', lineHeight: 1.4 }}>
                            系统支持四种投资风格，每种风格都有明确的选股标准和仓位限制：
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
                            <div className="style-badge"><strong style={{ color: 'var(--primary)', marginRight: '0.3rem', fontSize: '0.8rem' }}>Quality</strong><span style={{ fontSize: '0.75rem' }}>质量 - 财务稳健</span></div>
                            <div className="style-badge"><strong style={{ color: 'var(--primary)', marginRight: '0.3rem', fontSize: '0.8rem' }}>Value</strong><span style={{ fontSize: '0.75rem' }}>价值 - 寻找低估</span></div>
                            <div className="style-badge"><strong style={{ color: 'var(--primary)', marginRight: '0.3rem', fontSize: '0.8rem' }}>Growth</strong><span style={{ fontSize: '0.75rem' }}>成长 - 追求增长</span></div>
                            <div className="style-badge"><strong style={{ color: 'var(--primary)', marginRight: '0.3rem', fontSize: '0.8rem' }}>Momentum</strong><span style={{ fontSize: '0.75rem' }}>趋势 - 跟随动量</span></div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// Market Warnings Component
function MarketWarnings({ warnings }: { warnings?: any[] }) {
    if (!warnings || warnings.length === 0) return null;

    const levelColors: Record<string, { bg: string, border: string, text: string }> = {
        'high': { bg: '#7f1d1d', border: '#ef4444', text: '#fca5a5' },
        'medium': { bg: '#78350f', border: '#f59e0b', text: '#fcd34d' },
        'low': { bg: '#1e3a2f', border: '#10b981', text: '#6ee7b7' }
    };

    const urgencyLabels: Record<string, string> = {
        'immediate': '[紧急]',
        'soon': '[近期]',
        'monitor': '[监控]'
    };

    return (
        <div className="card shadow-lg p-4 mb-4 warning-card">
            <h5 className="mb-3 flex items-center gap-2" style={{ color: 'var(--bear)' }}>
                <i className="bi bi-exclamation-triangle-fill"></i>
                市场预警
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
                                    {urgencyLabels[warning.urgency] || '[监控]'}
                                </span>
                                <div style={{ flex: 1 }}>
                                    <strong style={{ color: colors.border }}>{warning.message}</strong>
                                    {warning.event_date && (
                                        <div style={{ fontSize: '0.85rem', marginTop: '0.2rem', opacity: 0.9 }}>
                                            事件日期: {warning.event_date}
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

    const [ticker, setTicker] = useState('');
    const [style, setStyle] = useState('quality');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('analysis');

    // Task progress state
    const [taskProgress, setTaskProgress] = useState(0);
    const [taskStep, setTaskStep] = useState('');

    // Initialize task polling hook
    const { taskStatus, startPolling } = useTaskPolling({
        onTaskComplete: (taskResult) => {
            console.log('Task completed:', taskResult);
            setResult(taskResult);
            setLoading(false);
            setTaskProgress(100);
            setTaskStep('分析完成！');
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

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
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
                setTaskStep('任务已创建，开始分析...');

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

    const getRiskClass = (score: number) => {
        if (score >= 6) return 'risk-high';
        if (score >= 4) return 'risk-med';
        return 'risk-low';
    };

    const getSentimentClass = (score: number) => {
        if (score >= 7) return 'text-warning';
        if (score >= 4) return 'text-success';
        return 'text-danger';
    };

    const getRating = (score: number) => {
        if (score >= 6) return { text: '观望', class: 'text-warning' };
        if (score >= 4) return { text: '中性', class: 'text-warning' };
        if (score >= 2) return { text: '增持', class: 'text-success' };
        return { text: '买入', class: 'text-success' };
    };

    if (authLoading) return <div className="p-8 text-white">Loading...</div>;

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4 text-white">
                <h1 className="text-4xl font-bold tracking-tight">AlphaGBM 股票分析</h1>
                <p className="text-lg text-slate-400 max-w-2xl">
                    请登录以访问期权分析
                </p>
                <div className="flex gap-4">
                    <Button onClick={() => navigate('/login')} className="btn-primary" size="lg">登录</Button>
                </div>
            </div>
        );
    }

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ color: 'var(--foreground)' }}>
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
                        股票分析
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
                        分析历史
                    </button>
                </div>
            </div>

            {/* Stock Analysis Tab */}
            <div style={{ display: activeTab === 'analysis' ? 'block' : 'none' }}>
                {/* 股票查询表单 */}
                <div className="card shadow-lg mb-4 p-4 sm:p-6">
                    <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.3rem', fontWeight: 600 }}>
                        <i className="bi bi-search"></i>
                        股票智能分析
                    </h5>

                    <form onSubmit={handleAnalyze} className="grid grid-cols-1 gap-4 sm:grid-cols-1 md:grid-cols-[1fr_2fr_auto] sm:gap-4">
                        <div>
                            <label className="block text-muted mb-2" style={{ fontSize: '0.95rem', fontWeight: 500 }}>投资风格</label>
                            <CustomSelect
                                options={[
                                    {
                                        value: 'quality',
                                        label: 'Quality (质量)',
                                        description: '关注财务稳健、盈利能力强、债务水平低的优质公司，适合长期持有，最大仓位20%'
                                    },
                                    {
                                        value: 'value',
                                        label: 'Value (价值)',
                                        description: '寻找被市场低估的股票，关注低PE、低PEG，追求安全边际，最大仓位10%'
                                    },
                                    {
                                        value: 'growth',
                                        label: 'Growth (成长)',
                                        description: '追求高营收增长和盈利增长的公司，容忍较高估值，最大仓位15%'
                                    },
                                    {
                                        value: 'momentum',
                                        label: 'Momentum (趋势)',
                                        description: '跟随市场趋势和价格动量，快进快出，风险较高，最大仓位5%'
                                    }
                                ]}
                                value={style}
                                onChange={setStyle}
                                placeholder="选择投资风格"
                                className="w-full"
                            />
                        </div>
                        <div>
                            <label className="block text-muted mb-2" style={{ fontSize: '0.95rem', fontWeight: 500 }}>股票代码</label>
                            <Input
                                placeholder="输入股票代码，如 AAPL, TSLA, 600519.SS"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                required
                                className="form-control w-full"
                            />
                        </div>
                        <div className="flex items-end">
                            <Button type="submit" disabled={loading} className="btn-primary h-11 px-6">
                                <i className="bi bi-graph-up mr-2"></i>
                                {loading ? '分析中...' : '分析'}
                            </Button>
                        </div>
                    </form>

                    <div className="mt-4 p-3 rounded" style={{ background: 'var(--muted)', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
                        {styleDescriptions[style]}
                    </div>

                    {error && (
                        <div className="mt-4 p-3 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                            <div className="font-semibold mb-2">❌ 分析失败</div>
                            <div className="whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                                {error.length > 500 ? (
                                    <>
                                        <div>{error.substring(0, 500)}...</div>
                                        <details className="mt-2">
                                            <summary className="cursor-pointer text-red-300 hover:text-red-200">
                                                查看完整错误信息
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
                                    <span className="text-muted">分析进度</span>
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
                            {taskStep || '正在连接 Gemini 进行深度推演...'}
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
                                    历史分析报告
                                </span>
                                {result.history_metadata.created_at && (
                                    <span className="text-muted ml-3" style={{ fontSize: '0.9rem' }}>
                                        分析时间：{new Date(result.history_metadata.created_at).toLocaleString('zh-CN')}
                                    </span>
                                )}
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

                {/* Dashboard Results */}
                {result && result.success && (() => {
                    const d = result.data;
                    const r = result.risk;
                    const sentiment = d.market_sentiment ?? 5.0;
                    const rating = getRating(r.score);
                    const styleName = styleNames[style] || '质量 (Quality)';
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
                                        当前价格 (P)
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
                                        市场情绪 (S)
                                    </div>
                                    <div className={`metric-value ${getSentimentClass(sentiment)}`}>{sentiment.toFixed(1)}</div>
                                    <small className="text-muted" style={{ fontSize: '0.85rem' }}>0-10分，越高越乐观</small>
                                </div>

                                {/* Risk Level */}
                                <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                    <div className="metric-label">
                                        <i className="bi bi-shield-check mr-2"></i>
                                        综合风控等级
                                    </div>
                                    <div className={`metric-value ${getRiskClass(r.score)}`}>{r.level}</div>
                                    <small className="text-danger" style={{ fontSize: '0.85rem' }}>Score: {r.score}/10</small>
                                </div>

                                {/* Suggested Position */}
                                <div className="card shadow-md border-primary" style={{ padding: '1.5rem', borderWidth: '2px' }}>
                                    <div className="metric-label text-primary">
                                        <i className="bi bi-pie-chart-fill mr-2"></i>
                                        建议仓位
                                    </div>
                                    <div className="metric-value text-primary">{r.suggested_position}%</div>
                                    <small className="text-muted" style={{ fontSize: '0.85rem' }}>基于模型限制</small>
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
                                            近12月价格趋势
                                        </h5>
                                        <PriceChart dates={d.history_dates} prices={d.history_prices} />
                                    </div>

                                    {/* Risk Flags */}
                                    <div className="card shadow-md" style={{ padding: '1.5rem' }}>
                                        <h5 className="mb-4 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                            <i className="bi bi-exclamation-triangle"></i>
                                            风险警示
                                        </h5>
                                        <ul>
                                            {r.flags && r.flags.length > 0 ? (
                                                r.flags.map((flag: string, idx: number) => (
                                                    <li key={idx} className="list-group-item text-danger">[警告] {flag}</li>
                                                ))
                                            ) : (
                                                <li className="list-group-item text-success">硬逻辑检测通过，无明显结构性风险。</li>
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
                                            AI投资分析
                                        </h5>
                                        <span className="badge-primary">AI Generated</span>
                                    </div>
                                    <div className="overflow-auto" style={{ maxHeight: '650px', padding: '1.5rem' }}>
                                        <div
                                            className="ai-summary"
                                            dangerouslySetInnerHTML={{ __html: renderMarkdown(result.report || '分析数据不可用') }}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Full Text Report */}
                            <div className="card shadow-md">
                                <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)' }}>
                                    <h5 className="mb-0 flex items-center gap-2" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
                                        <i className="bi bi-file-text"></i>
                                        ALPHAGBM 分析报告
                                    </h5>
                                </div>
                                <div style={{ padding: '1.5rem', lineHeight: 1.8, fontSize: '1rem' }}>
                                    {/* Report Header */}
                                    <div className="text-report-section" style={{ borderBottom: '2px solid var(--primary)', paddingBottom: '1.5rem' }}>
                                        <div className="text-center mb-4">
                                            <h3 style={{ color: 'var(--primary)', fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                                                {d.name} ({d.symbol}) 投资研究报告
                                            </h3>
                                            <p style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem' }}>
                                                报告日期：{new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}
                                            </p>
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>投资评级</div>
                                                <div className={rating.class} style={{ fontSize: '1.5rem', fontWeight: 700 }}>{rating.text}</div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>目标价格</div>
                                                <div style={{ color: r.suggested_position === 0 ? 'var(--bear)' : 'var(--primary)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {d.currency_symbol}{(d.target_price || d.price)?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>当前价格</div>
                                                <div style={{ color: 'var(--foreground)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {d.currency_symbol}{d.price?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div className="text-center">
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.85rem', marginBottom: '0.3rem' }}>建议仓位</div>
                                                <div style={{ color: 'var(--primary)', fontSize: '1.3rem', fontWeight: 600 }}>
                                                    {r.suggested_position}%
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Section 1: Core Analysis */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">一、核心观点</div>
                                        <div style={{ color: 'var(--muted-foreground)' }}>
                                            <p><strong style={{ color: 'var(--foreground)' }}>投资风格：</strong>{styleName}。</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>核心结论：</strong>基于G=B+M模型分析，当前价格位于52周区间的{pricePosition.toFixed(1)}%位置。
                                                {!d.is_etf_or_fund && d.growth !== undefined && `基本面数据显示营收增长率为${(d.growth * 100).toFixed(2)}%，利润率为${((d.margin || 0) * 100).toFixed(2)}%。`}
                                                综合风险评分为{r.score}/10，风险等级为{r.level}。
                                            </p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>投资建议：</strong>{rating.text}。建议仓位上限为{r.suggested_position}%。
                                                {r.suggested_position === 0 ? '当前风险过高，不建议建仓，建议观望。' : r.score >= 4 ? '建议分批建仓，控制风险。' : '可考虑一次性建仓，但需严格遵守仓位上限。'}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Section 2: Company Overview */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">二、{d.is_etf_or_fund ? 'ETF概况' : '公司概况'}</div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div><div className="text-report-label">股票代码</div><div className="text-report-value">{d.symbol}</div></div>
                                            <div><div className="text-report-label">全称</div><div className="text-report-value">{d.name}</div></div>
                                            {!d.is_etf_or_fund && (
                                                <>
                                                    <div><div className="text-report-label">所属行业</div><div className="text-report-value">{d.sector || '数据不足'}</div></div>
                                                    <div><div className="text-report-label">细分领域</div><div className="text-report-value">{d.industry || '数据不足'}</div></div>
                                                </>
                                            )}
                                        </div>
                                        {/* Company News */}
                                        {d.company_news && Array.isArray(d.company_news) && d.company_news.length > 0 && (
                                            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }}>
                                                <div style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '1rem', marginBottom: '0.8rem' }}>最新动态</div>
                                                <ul style={{ color: 'var(--muted-foreground)', lineHeight: 1.8, fontSize: '0.95rem', margin: 0, paddingLeft: '1.5rem' }}>
                                                    {d.company_news.slice(0, 5).map((news: any, idx: number) => (
                                                        <li key={idx} style={{ marginBottom: '0.8rem' }}>
                                                            <strong>{news.title || '无标题'}</strong>
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
                                            <div className="text-report-title">三、财务分析 (B - 基本面)</div>
                                            <p style={{ color: 'var(--muted-foreground)', marginBottom: '1rem' }}>基于最新财务数据，我们对公司基本面进行如下分析：</p>
                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-report-label">营收增长率 (YoY)</div>
                                                    <div className={`text-report-value ${d.growth < 0 ? 'text-danger' : d.growth > 0.2 ? 'text-success' : ''}`} style={{ fontSize: '1.1rem' }}>
                                                        {((d.growth || 0) * 100).toFixed(2)}%
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)' }}>{d.growth > 0.2 ? '增长强劲' : d.growth > 0 ? '稳定增长' : d.growth < 0 ? '负增长，需关注' : '数据不足'}</small>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">净利润率</div>
                                                    <div className={`text-report-value ${d.margin < 0.05 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem' }}>
                                                        {((d.margin || 0) * 100).toFixed(2)}%
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)' }}>{d.margin > 0.15 ? '盈利能力优秀' : d.margin > 0.1 ? '盈利能力良好' : d.margin > 0.05 ? '盈利能力一般' : '盈利能力较弱'}</small>
                                                </div>
                                            </div>
                                            <p style={{ color: 'var(--muted-foreground)', marginTop: '1rem' }}>
                                                <strong style={{ color: 'var(--foreground)' }}>财务健康度评估：</strong>
                                                {d.growth > 0.1 && d.margin > 0.1 ? '公司财务表现稳健，营收增长和盈利能力均处于良好水平，基本面支撑较强。' :
                                                    d.growth < 0 || d.margin < 0.05 ? '公司财务表现存在一定压力，需密切关注后续财务数据变化。' :
                                                        '公司财务表现基本稳定，但增长动力和盈利能力有待进一步提升。'}
                                            </p>
                                        </div>
                                    )}

                                    {/* Section 4: Valuation Analysis */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">四、估值分析 (M - 市场情绪)</div>
                                        
                                        {/* 价格与技术面 */}
                                        <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                                            <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>价格与技术面</div>
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                <div>
                                                    <div className="text-report-label">当前价格</div>
                                                    <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.currency_symbol}{d.price?.toFixed(2)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">52周区间</div>
                                                    <div className="text-report-value" style={{ fontSize: '0.95rem' }}>
                                                        {d.currency_symbol}{d.week52_low?.toFixed(2)} - {d.currency_symbol}{d.week52_high?.toFixed(2)}
                                                    </div>
                                                    <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>位于{pricePosition.toFixed(1)}%分位</small>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">技术趋势</div>
                                                    <div className="text-report-value" style={{ fontSize: '0.95rem', fontWeight: 500 }}>
                                                        {d.price > d.ma50 && d.ma50 > d.ma200 ? '多头排列' : d.price < d.ma200 ? '空头趋势' : '震荡整理'}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-report-label">均线系统</div>
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
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>估值指标</div>
                                                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                                    <div>
                                                        <div className="text-report-label">市盈率 (PE)</div>
                                                        <div className={`text-report-value ${d.pe && d.pe > 30 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                            {d.pe ? d.pe.toFixed(2) : 'N/A'}
                                                        </div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.pe && d.pe > 30 ? '估值偏高' : d.pe && d.pe > 15 ? '估值合理' : d.pe > 0 ? '估值偏低' : '数据不足'}
                                                        </small>
                                                    </div>
                                                    <div>
                                                        <div className="text-report-label">预期市盈率 (Forward PE)</div>
                                                        <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.forward_pe ? d.forward_pe.toFixed(2) : 'N/A'}</div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.forward_pe && d.forward_pe < d.pe ? '预期改善' : d.forward_pe && d.forward_pe > d.pe ? '预期恶化' : ''}
                                                        </small>
                                                    </div>
                                                    <div>
                                                        <div className="text-report-label">PEG 比率</div>
                                                        <div className="text-report-value" style={{ fontSize: '1.1rem', fontWeight: 600 }}>{d.peg ? d.peg.toFixed(2) : 'N/A'}</div>
                                                        <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                            {d.peg && d.peg < 1 ? '估值合理' : d.peg > 0 ? '估值偏高' : '数据不足'}
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* 市场情绪指标 */}
                                        {d.options_data && (d.options_data.vix !== null || d.options_data.put_call_ratio !== null) && (
                                            <div style={{ marginBottom: '1.5rem' }}>
                                                <div style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem', marginBottom: '0.8rem', fontWeight: 500 }}>市场情绪指标</div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    {d.options_data.vix !== null && (
                                                        <div>
                                                            <div className="text-report-label">VIX恐慌指数</div>
                                                            <div className={`text-report-value ${d.options_data.vix > 30 ? 'text-danger' : d.options_data.vix > 20 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                                {d.options_data.vix.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                                {d.options_data.vix_change ? (d.options_data.vix_change > 0 ? '↑' : '↓') + Math.abs(d.options_data.vix_change).toFixed(1) + '%' : ''} 
                                                                {d.options_data.vix > 30 ? ' | 高波动风险' : d.options_data.vix > 20 ? ' | 中等波动' : ' | 低波动'}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.options_data.put_call_ratio !== null && (
                                                        <div>
                                                            <div className="text-report-label">Put/Call比率</div>
                                                            <div className={`text-report-value ${d.options_data.put_call_ratio > 1.2 ? 'text-danger' : d.options_data.put_call_ratio > 1.0 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                                {d.options_data.put_call_ratio.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem' }}>
                                                                {d.options_data.put_call_ratio > 1.2 ? '看跌情绪强' : d.options_data.put_call_ratio > 1.0 ? '略偏看跌' : d.options_data.put_call_ratio < 0.8 ? '看涨情绪' : '中性'}
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Macro Data */}
                                        {d.macro_data && (d.macro_data.treasury_10y !== null || d.macro_data.dxy !== null || d.macro_data.gold !== null || d.macro_data.oil !== null) && (
                                            <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                                                <div className="text-report-title" style={{ fontSize: '1.1rem', marginBottom: '0.8rem' }}>宏观经济环境</div>
                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                    {d.macro_data.treasury_10y !== null && (
                                                        <div>
                                                            <div className="text-report-label">10年美债收益率</div>
                                                            <div className={`text-report-value ${d.macro_data.treasury_10y > 4.5 ? 'text-danger' : d.macro_data.treasury_10y > 3.5 ? 'text-warning' : 'text-success'}`} style={{ fontSize: '1rem' }}>
                                                                {d.macro_data.treasury_10y.toFixed(2)}%
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.treasury_10y_change ? (d.macro_data.treasury_10y_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.treasury_10y_change).toFixed(2) + '%' : ''} {d.macro_data.treasury_10y > 4.5 ? '流动性收紧' : '正常'}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.dxy !== null && (
                                                        <div>
                                                            <div className="text-report-label">美元指数</div>
                                                            <div className={`text-report-value ${d.macro_data.dxy > 105 ? 'text-warning' : ''}`} style={{ fontSize: '1rem' }}>
                                                                {d.macro_data.dxy.toFixed(2)}
                                                            </div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.dxy_change ? (d.macro_data.dxy_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.dxy_change).toFixed(2) + '%' : ''} {d.macro_data.dxy > 105 ? '强势美元' : '正常'}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.gold !== null && (
                                                        <div>
                                                            <div className="text-report-label">黄金价格</div>
                                                            <div className="text-report-value" style={{ fontSize: '1rem' }}>${d.macro_data.gold.toFixed(2)}</div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.gold_change ? (d.macro_data.gold_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.gold_change).toFixed(2) + '%' : ''} {d.macro_data.gold_change > 2 ? '避险情绪' : '正常'}
                                                            </small>
                                                        </div>
                                                    )}
                                                    {d.macro_data.oil !== null && (
                                                        <div>
                                                            <div className="text-report-label">原油价格</div>
                                                            <div className="text-report-value" style={{ fontSize: '1rem' }}>${d.macro_data.oil.toFixed(2)}</div>
                                                            <small style={{ color: 'var(--muted-foreground)' }}>
                                                                {d.macro_data.oil_change ? (d.macro_data.oil_change > 0 ? '↑' : '↓') + Math.abs(d.macro_data.oil_change).toFixed(2) + '%' : ''} 正常
                                                            </small>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Earnings Date Reminder */}
                                        {d.earnings_dates && Array.isArray(d.earnings_dates) && d.earnings_dates.length > 0 && (
                                            <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: '#1e293b', borderLeft: '3px solid var(--primary)', borderRadius: '4px' }}>
                                                <strong style={{ color: 'var(--primary)' }}>财报日期提醒：</strong>
                                                <span style={{ color: 'var(--muted-foreground)' }}>预计财报日期：{d.earnings_dates.join(', ')}。财报发布前后通常伴随较大波动，建议提前调整仓位。</span>
                                            </div>
                                        )}

                                        {/* Economic Events */}
                                        {d.macro_data && (d.macro_data.fed_meetings?.length > 0 || d.macro_data.cpi_releases?.length > 0 || d.macro_data.china_events?.length > 0) && (
                                            <div style={{ marginTop: '1rem', padding: '0.8rem', backgroundColor: '#1e293b', borderLeft: '3px solid #8b5cf6', borderRadius: '4px' }}>
                                                <strong style={{ color: '#8b5cf6' }}>重要经济事件提醒：</strong>
                                                <div style={{ color: 'var(--muted-foreground)', marginTop: '0.5rem' }}>
                                                    {d.macro_data.fed_meetings?.length > 0 && (
                                                        <div style={{ marginBottom: '0.5rem' }}>
                                                            <strong style={{ color: 'var(--primary)' }}>🇺🇸 美国：</strong>
                                                            <div style={{ marginLeft: '1rem', marginTop: '0.3rem' }}>
                                                                <div>美联储利率决议：{d.macro_data.fed_meetings.map((m: any) => `${m.date} (${m.days_until}天后${m.has_dot_plot ? '，含点阵图' : ''})`).join('、')}</div>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {d.macro_data.china_events?.length > 0 && (
                                                        <div style={{ marginBottom: '0.5rem' }}>
                                                            <strong style={{ color: 'var(--bear)' }}>🇨🇳 中国：</strong>
                                                            <div style={{ marginLeft: '1rem', marginTop: '0.3rem' }}>
                                                                {d.macro_data.china_events.map((e: any, idx: number) => (
                                                                    <div key={idx}>{e.type}：{e.date} ({e.days_until}天后{e.data_month ? `，${e.data_month}数据` : ''})</div>
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
                                                <strong style={{ color: d.macro_data.geopolitical_risk >= 7 ? 'var(--bear)' : d.macro_data.geopolitical_risk >= 5 ? 'var(--warning)' : 'var(--bull)' }}>地缘政治风险指数：</strong>
                                                <span style={{ color: 'var(--foreground)', fontSize: '1.1rem', fontWeight: 600, marginLeft: '0.5rem' }}>{d.macro_data.geopolitical_risk}/10</span>
                                                <span style={{ color: 'var(--muted-foreground)', marginLeft: '0.5rem' }}>
                                                    {d.macro_data.geopolitical_risk >= 7 ? '高风险 - 地缘政治紧张局势加剧' : d.macro_data.geopolitical_risk >= 5 ? '中等风险 - 需关注地缘政治动态' : '低风险 - 地缘政治环境相对稳定'}
                                                </span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Section 5: Risk Warning */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">五、风险提示</div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-report-label">综合风险评分</div>
                                                <div className={`text-report-value ${getRiskClass(r.score)}`} style={{ fontSize: '1.3rem', fontWeight: 700 }}>{r.score}/10</div>
                                            </div>
                                            <div>
                                                <div className="text-report-label">风险等级</div>
                                                <div className={`text-report-value ${getRiskClass(r.score)}`} style={{ fontSize: '1.1rem' }}>{r.level}</div>
                                            </div>
                                        </div>
                                        {r.flags && r.flags.length > 0 ? (
                                            <div style={{ marginTop: '1rem' }}>
                                                <p><strong style={{ color: 'var(--foreground)' }}>主要风险因素：</strong></p>
                                                <ul style={{ paddingLeft: '1.5rem', color: 'var(--muted-foreground)' }}>
                                                    {r.flags.map((flag: string, idx: number) => (
                                                        <li key={idx} style={{ marginBottom: '0.5rem' }}>{flag}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ) : (
                                            <div style={{ marginTop: '1rem', color: 'var(--bull)' }}>
                                                <p>经系统评估，当前无明显结构性风险，硬逻辑检测通过。</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Section 6: Investment Advice */}
                                    <div className="text-report-section">
                                        <div className="text-report-title">六、投资建议</div>
                                        <div style={{ color: 'var(--muted-foreground)' }}>
                                            <p><strong style={{ color: 'var(--foreground)' }}>投资评级：</strong><span className={rating.class} style={{ fontSize: '1.1rem', fontWeight: 600 }}>{rating.text}</span></p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>目标价格：</strong>{d.currency_symbol}{(d.target_price || d.price)?.toFixed(2)}（基于PE估值、增长率和技术面综合计算）</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>建议仓位：</strong><span style={{ color: r.suggested_position === 0 ? 'var(--bear)' : 'var(--primary)', fontSize: '1.1rem', fontWeight: 600 }}>{r.suggested_position}%</span>（基于{styleName}风格、风险评分和价格动态调整）</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>建仓策略：</strong>{generateEntryStrategy(d.price || 0, d.target_price || d.price || 0, style, r.score, r.suggested_position)}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>止盈建议：</strong>{generateTakeProfitStrategy(d.price || 0, d.target_price || d.price || 0, style, d.currency_symbol || '$')}</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>止损建议：</strong>建议设置止损价格为{d.currency_symbol}{d.stop_loss_price?.toFixed(2) || (d.price * 0.85).toFixed(2)}（{d.stop_loss_method || '动态止损'}），严格执行止损纪律。</p>
                                            <p><strong style={{ color: 'var(--foreground)' }}>持有周期：</strong>根据{styleName}风格，建议持有{style === 'quality' ? '长期（1-3年）' : style === 'value' ? '中期（6-12个月）' : style === 'growth' ? '中短期（3-6个月）' : '短期（1-3个月）'}。</p>
                                        </div>
                                    </div>

                                    {/* Disclaimer */}
                                    <div className="text-report-section" style={{ borderTop: '2px solid var(--bear)', paddingTop: '1.5rem', marginTop: '2rem' }}>
                                        <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--bear)', padding: '1rem', borderRadius: '4px' }}>
                                            <h5 style={{ color: 'var(--bear)', fontSize: '1rem', fontWeight: 600, marginBottom: '0.8rem' }}>重要风险提示</h5>
                                            <div style={{ color: 'var(--muted-foreground)', lineHeight: 1.8, fontSize: '0.9rem' }}>
                                                <p style={{ marginBottom: '0.5rem' }}><strong style={{ color: 'var(--foreground)' }}>免责声明：</strong>本报告所载信息、数据及分析结果仅供参考，不构成任何投资建议。</p>
                                                <p style={{ marginBottom: '0.5rem' }}><strong style={{ color: 'var(--foreground)' }}>投资风险：</strong>股票投资存在市场风险、信用风险、流动性风险等多种风险。过往业绩不代表未来表现。</p>
                                                <p style={{ marginBottom: '0' }}><strong style={{ color: 'var(--foreground)' }}>AI分析说明：</strong>AI生成的分析报告基于算法模型和历史数据，仅供参考，不应作为唯一投资依据。</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })()}

                {/* Empty State */}
                {!result && !loading && (
                    <div className="text-center py-20 text-muted">
                        <i className="bi bi-graph-up text-6xl mb-4 opacity-30" style={{ display: 'block' }}></i>
                        <p>输入股票代码开始分析</p>
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
