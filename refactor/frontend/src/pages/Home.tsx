import { useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useNavigate } from 'react-router-dom';

// Styling to match original templates/index.html
const styles = `
    .glass-card {
        background: rgba(24, 24, 27, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08); /* Lighter border for dark mode */
        border-radius: 0.75rem;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
        box-shadow: 0 10px 30px -10px rgba(13, 155, 151, 0.2);
    }
    .metric-label {
        color: #A1A1AA;
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .metric-value {
        font-size: 1.875rem;
        font-weight: 700;
        color: #FAFAFA;
        letter-spacing: -0.025em;
    }
    .text-brand { color: #0D9B97; }
    .bg-brand { background-color: #0D9B97; }
    .btn-primary {
        background-color: #0D9B97;
        color: white;
        border: none;
    }
    .btn-primary:hover {
        background-color: #0A7D7A;
    }
`;

export default function Home() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    const [ticker, setTicker] = useState('');
    const [style, setStyle] = useState('quality');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState('');

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!user) {
            navigate('/login');
            return;
        }

        setLoading(true);
        setError('');
        setResult(null);

        try {
            const response = await api.post('/stock/analyze', {
                ticker,
                style,
                onlyHistoryData: false // Default to full analysis
            });
            setResult(response.data);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.error || err.message || 'Analysis Failed');
        } finally {
            setLoading(false);
        }
    };

    if (authLoading) return <div className="p-8 text-white">Loading...</div>;

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4 text-white">
                <h1 className="text-4xl font-bold tracking-tight">AlphaGBM Stock Analysis</h1>
                <p className="text-lg text-slate-400 max-w-2xl">
                    Please login to access professional AI stock analysis.
                </p>
                <div className="flex gap-4">
                    <Button onClick={() => navigate('/login')} className="btn-primary" size="lg">Login</Button>
                </div>
            </div>
        )
    }

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 text-slate-50">
            <style>{styles}</style>

            {/* Search Section */}
            <div className="glass-card p-6 mb-8">
                <h5 className="text-xl font-semibold mb-6 flex items-center gap-2">
                    <i className="ph ph-magnifying-glass"></i>
                    Stock Intelligent Analysis
                </h5>
                <form onSubmit={handleAnalyze} className="grid grid-cols-1 md:grid-cols-[200px_1fr_auto] gap-4 items-end">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-400">Investment Style</label>
                        <select
                            value={style}
                            onChange={(e) => setStyle(e.target.value)}
                            className="w-full h-11 rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#0D9B97]"
                        >
                            <option value="quality">Quality</option>
                            <option value="value">Value</option>
                            <option value="growth">Growth</option>
                            <option value="momentum">Momentum</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-400">Ticker Symbol</label>
                        <Input
                            placeholder="Input Ticker, e.g., AAPL, 0700.HK, 600519.SS"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                            required
                            className="bg-slate-800 border-slate-700 text-white h-11 placeholder:text-slate-500"
                        />
                    </div>
                    <Button type="submit" disabled={loading} className="btn-primary h-11 px-8">
                        {loading ? 'Analyzing...' : 'Analyze'}
                    </Button>
                </form>
                {error && <div className="mt-4 text-red-400 text-sm">{error}</div>}
            </div>

            {/* Dashboard Results - Only show if we have data or if mocked/placeholder needed (keeping hidden initially like original) */}
            {result ? (
                <div className="space-y-8">
                    {/* Metrics Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {/* Price */}
                        <div className="glass-card p-6">
                            <div className="metric-label">
                                <i className="ph ph-currency-dollar"></i> Price (P)
                            </div>
                            <div className="metric-value text-white">
                                {result.data.currency} {result.data.price}
                            </div>
                            <div className="text-xs text-slate-500 mt-2">Current Market Price</div>
                        </div>

                        {/* Sentiment - Mocked if missing from API for now */}
                        <div className="glass-card p-6">
                            <div className="metric-label">
                                <i className="ph ph-smiley"></i> Sentiment (S)
                            </div>
                            <div className="metric-value text-white">
                                7.5
                            </div>
                            <div className="text-xs text-slate-500 mt-2">0-10 Score</div>
                        </div>

                        {/* Risk */}
                        <div className="glass-card p-6">
                            <div className="metric-label">
                                <i className="ph ph-shield-check"></i> Risk Level
                            </div>
                            <div className="metric-value text-emerald-400">
                                Low
                            </div>
                            <div className="text-xs text-slate-500 mt-2">Score: 2.5/10</div>
                        </div>

                        {/* Position */}
                        <div className="glass-card p-6 border-[#0D9B97] border-opacity-50">
                            <div className="metric-label text-[#0D9B97]">
                                <i className="ph ph-chart-pie-slice"></i> Suggested Position
                            </div>
                            <div className="metric-value text-[#0D9B97]">
                                18%
                            </div>
                            <div className="text-xs text-slate-500 mt-2">Model Limit: 20%</div>
                        </div>
                    </div>

                    {/* Report Content */}
                    <div className="grid grid-cols-1 lg:grid-cols-[4fr_6fr] gap-6">
                        {/* Left: Chart placeholder (since we don't have historical data hooked up fully in this view yet) */}
                        <div className="glass-card p-6 min-h-[400px]">
                            <h5 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <i className="ph ph-trend-up"></i> Price Trend
                            </h5>
                            <div className="h-full flex items-center justify-center text-slate-500">
                                [Chart Component Placeholder]
                            </div>
                        </div>

                        {/* Right: AI Report */}
                        <div className="glass-card p-6">
                            <div className="flex items-center justify-between mb-4 border-b border-slate-700 pb-4">
                                <h5 className="text-lg font-semibold flex items-center gap-2">
                                    <i className="ph ph-sparkle"></i> AI Analysis
                                </h5>
                                <span className="px-2 py-1 rounded bg-[#0D9B97]/20 text-[#0D9B97] text-xs font-mono">AI Generated</span>
                            </div>
                            <div className="prose prose-invert max-w-none text-slate-300 text-sm leading-relaxed">
                                {result.report?.analysis ? (
                                    <div className="whitespace-pre-wrap">{result.report.analysis}</div>
                                ) : (
                                    <p>Analysis data not available.</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                /* Placeholder / Empty State or Loading State could go here */
                <div className="text-center py-20 text-slate-500">
                    <i className="ph ph-chart-bar text-6xl mb-4 opacity-50 text-slate-700"></i>
                    <p>Enter a ticker symbol to start analysis.</p>
                </div>
            )}
        </div>
    );
}
