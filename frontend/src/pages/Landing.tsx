import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Chart from 'chart.js/auto';
import { Menu, X } from 'lucide-react';
import axios from 'axios';
import FeedbackButton from '@/components/FeedbackButton';
import PrivacyPolicy from '@/components/PrivacyPolicy';
import { translateStockName } from '@/lib/i18n';

// Original CSS from home/index.html
const originalStyles = `
    /* ==================== Alpha GBM 设计系统 ==================== */
    :root {
        /* 品牌色 - 深青色 */
        --brand-primary: #0D9B97;
        --brand-primary-rgb: 13, 155, 151;
        --brand-primary-light: #10B5B0;
        --brand-primary-dark: #0A7D7A;

        /* 背景色 */
        --bg-primary: #09090B;
        --bg-secondary: #18181B;
        --bg-tertiary: #27272A;

        /* 文字色 */
        --text-primary: #FAFAFA;
        --text-secondary: #A1A1AA;
        --text-muted: #71717A;

        /* 金融色 */
        --color-bull: #10B981;
        --color-bear: #EF4444;
    }

    body {
        font-family: 'Inter', 'Noto Sans SC', sans-serif;
        background-color: var(--bg-primary);
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        margin: 0; 
    }

    .font-mono {
        font-family: 'JetBrains Mono', monospace;
    }

    /* 渐变文字 - 使用品牌色 */
    .gradient-text {
        background: linear-gradient(to right, var(--brand-primary), var(--brand-primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* 玻璃卡片效果 */
    .glass-card {
        background: rgba(24, 24, 27, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(39, 39, 42, 0.8);
        transition: all 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
        transform: translateY(-5px);
        box-shadow: 0 10px 30px -10px rgba(13, 155, 151, 0.3);
    }

    /* 英雄区光晕 - 使用品牌色 */
    .hero-glow {
        position: absolute;
        width: 600px;
        height: 600px;
        background: radial-gradient(circle, rgba(13, 155, 151, 0.15) 0%, rgba(9, 9, 11, 0) 70%);
        top: -100px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 0;
        pointer-events: none;
    }

    /* Beta 徽章脉冲动画 */
    .beta-pulse {
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0% { box-shadow: 0 0 0 0 rgba(13, 155, 151, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(13, 155, 151, 0); }
        100% { box-shadow: 0 0 0 0 rgba(13, 155, 151, 0); }
    }

    /* 导航栏优化 */
    .landing-nav {
         background: rgba(9, 9, 11, 0.8) !important;
         backdrop-filter: blur(12px);
         border-bottom: 1px solid rgba(39, 39, 42, 0.8);
    }

    /* 按钮优化 - 关键：使用 original HTML 提供的 .btn-primary */
    .btn-primary {
        background-color: var(--brand-primary) !important;
        color: white !important;
        box-shadow: 0 2px 4px rgba(13, 155, 151, 0.3);
        /* Tailwind defaults might override padding/radius if not careful, but we use tailwind classes for layout */
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }

    .btn-primary:hover {
        background-color: var(--brand-primary-light) !important;
        box-shadow: 0 4px 8px rgba(13, 155, 151, 0.4);
    }

    /* Brand utilities */
    .text-brand { color: var(--brand-primary) !important; }
    .bg-brand { background-color: var(--brand-primary) !important; }
    .bg-brand\\/5 { background-color: rgba(13, 155, 151, 0.05) !important; }
    .bg-brand\\/10 { background-color: rgba(13, 155, 151, 0.1) !important; }
    .border-brand { border-color: var(--brand-primary) !important; }
    .border-brand\\/10 { border-color: rgba(13, 155, 151, 0.1) !important; }
    .hover\\:text-brand:hover { color: var(--brand-primary) !important; }
    .hover\\:bg-brand:hover { background-color: var(--brand-primary) !important; }
    .shadow-brand { box-shadow: 0 0 20px rgba(13, 155, 151, 0.3); }

    /* Override standard link styles to match landing */
    a { text-decoration: none; }
`;

export default function Landing() {
    const { i18n, t } = useTranslation();
    const [expandedPortfolio, setExpandedPortfolio] = useState<string | null>(null);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Portfolio data state
    const [portfolioData, setPortfolioData] = useState<any>(null);
    const [portfolioLoading, setPortfolioLoading] = useState(true);
    const [portfolioError, setPortfolioError] = useState<string | null>(null);
    const [isDataFromCache, setIsDataFromCache] = useState(false);
    
    // Rebalance history state
    const [rebalanceHistory, setRebalanceHistory] = useState<any[]>([]);
    const [_rebalanceLoading, setRebalanceLoading] = useState(false);
    const [expandedRebalance, setExpandedRebalance] = useState<number | null>(null);

    const toggleLang = () => {
        i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    // Strict content mapping
    const content = {
        nav: {
            home: t('landing.nav.home'),
            portfolio: t('landing.nav.portfolio'),
            styles: t('landing.nav.styles'),
            contact: t('landing.nav.contact'),
            cta: t('landing.nav.cta'),
            lang: t('landing.nav.lang')
        },
        portfolio: {
            title: t('landing.portfolio.title'),
            description: t('landing.portfolio.description'),
            quality: t('landing.portfolio.quality'),
            value: t('landing.portfolio.value'),
            growth: t('landing.portfolio.growth'),
            momentum: t('landing.portfolio.momentum'),
            performanceChart: t('landing.portfolio.performanceChart'),
            viewHoldings: t('landing.portfolio.viewHoldings'),
            hideHoldings: t('landing.portfolio.hideHoldings'),
            stock: t('landing.portfolio.stock'),
            shares: t('landing.portfolio.shares'),
            costPrice: t('landing.portfolio.costPrice'),
            currentPrice: t('landing.portfolio.currentPrice'),
            allocation: t('landing.portfolio.allocation'),
            profitPercent: t('landing.portfolio.profitPercent'),
            dailyChange: t('landing.portfolio.dailyChange'),
            initialCapital: t('landing.portfolio.initialCapital')
        },
        hero: {
            badge: "Powered by LLM",
            titleSub: t('landing.hero.titleSub'),
            subtitle: t('landing.hero.subtitle'),
            cta_primary: t('landing.hero.cta_primary'),
            limit_notice: t('landing.hero.limit_notice')
        },
        valueProposition: {
            title: t('landing.engines.title'),
            items: [
                { icon: "chart-line-up", title: t('landing.engines.stocks.title'), badge: "", desc: t('landing.engines.stocks.desc'), link: "/stock" },
                { icon: "sigma", title: t('landing.engines.options.title'), badge: "New", desc: t('landing.engines.options.desc'), link: "/options" },
                { icon: "robot", title: t('landing.engines.agent.title'), badge: "Coming Soon", desc: t('landing.engines.agent.desc'), link: null }
            ]
        },
        styles: {
            title: t('landing.styles.title'),
            desc: "", // Removed: "基于G=B+M模型，系统自动适配您的投资风格"
            cards: [
                { name: t('landing.styles.quality.name'), color: "text-emerald-400", desc: t('landing.styles.quality.desc') },
                { name: t('landing.styles.value.name'), color: "text-blue-400", desc: t('landing.styles.value.desc') },
                { name: t('landing.styles.growth.name'), color: "text-purple-400", desc: t('landing.styles.growth.desc') },
                { name: t('landing.styles.momentum.name'), color: "text-orange-400", desc: t('landing.styles.momentum.desc') }
            ]
        },
        features: {
            title: t('landing.capabilities.title'),
            items: [
                { title: t('landing.capabilities.report.title'), desc: "Powered by LLM" },
                { title: t('landing.capabilities.risk.title'), desc: "VIX + Greeks" },
                { title: t('landing.capabilities.position.title'), desc: t('landing.capabilities.position.desc') }
            ]
        },
        faq: {
            title: t('landing.faq.title'),
            items: [
                { question: t('landing.faq.q1.question'), answer: t('landing.faq.q1.answer') },
                { question: t('landing.faq.q2.question'), answer: t('landing.faq.q2.answer') },
                { question: t('landing.faq.q3.question'), answer: t('landing.faq.q3.answer') },
                { question: t('landing.faq.q4.question'), answer: t('landing.faq.q4.answer') },
                { question: t('landing.faq.q5.question'), answer: t('landing.faq.q5.answer') },
                { question: t('landing.faq.q6.question'), answer: t('landing.faq.q6.answer') }
            ]
        },
        cta: {
            title: t('landing.community.title'),
            desc: t('landing.community.desc'),
            scan_text: t('landing.community.scan_text')
        },
        footer: {
            disclaimer: t('landing.footer.disclaimer'),
            copy: t('landing.footer.copy')
        }
    };

    // Cache management constants
    const CACHE_KEY = 'alphaGBM_portfolio_data';
    const CACHE_TIMESTAMP_KEY = 'alphaGBM_portfolio_timestamp';
    const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

    // Check if cache is valid (not expired)
    const isCacheValid = () => {
        const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
        if (!timestamp) return false;

        const cacheTime = parseInt(timestamp);
        const now = Date.now();
        return (now - cacheTime) < CACHE_DURATION;
    };

    // Get cached data if valid, clean expired cache
    const getCachedData = () => {
        if (!isCacheValid()) {
            // Clean expired cache
            localStorage.removeItem(CACHE_KEY);
            localStorage.removeItem(CACHE_TIMESTAMP_KEY);
            return null;
        }

        const cachedData = localStorage.getItem(CACHE_KEY);
        if (!cachedData) return null;

        try {
            return JSON.parse(cachedData);
        } catch (error) {
            console.warn('Failed to parse cached portfolio data:', error);
            // Clean corrupted cache
            localStorage.removeItem(CACHE_KEY);
            localStorage.removeItem(CACHE_TIMESTAMP_KEY);
            return null;
        }
    };

    // Get cache info for display
    const getCacheInfo = () => {
        const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
        if (!timestamp) return null;

        const cacheTime = parseInt(timestamp);
        const now = Date.now();
        const hoursAgo = Math.floor((now - cacheTime) / (1000 * 60 * 60));
        const minutesAgo = Math.floor((now - cacheTime) / (1000 * 60));

        if (hoursAgo > 0) {
            return `${hoursAgo}小时前`;
        } else if (minutesAgo > 0) {
            return `${minutesAgo}分钟前`;
        } else {
            return '刚刚';
        }
    };

    // Save data to cache
    const setCacheData = (data: any) => {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(data));
            localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
            console.log('Portfolio data cached successfully');
        } catch (error) {
            console.warn('Failed to cache portfolio data:', error);
        }
    };

    // API functions
    const fetchPortfolioData = async (forceRefresh = false) => {
        try {
            setPortfolioLoading(true);
            setPortfolioError(null);
            setIsDataFromCache(false);

            // Check cache first (unless force refresh)
            if (!forceRefresh) {
                const cachedData = getCachedData();
                if (cachedData) {
                    setPortfolioData(cachedData);
                    setIsDataFromCache(true);
                    setPortfolioLoading(false);
                    console.log('Portfolio data loaded from cache');
                    return;
                }
            }

            // Use environment variable API URL or fallback to localhost
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002';
            const response = await axios.get(`${apiUrl}/portfolio/holdings`);

            if (response.data.success) {
                const portfolioData = response.data.data;
                setPortfolioData(portfolioData);
                setIsDataFromCache(false);
                setCacheData(portfolioData); // Cache the new data
                console.log('Portfolio data loaded from API and cached');
            } else {
                throw new Error(response.data.error || 'Failed to fetch portfolio data');
            }
        } catch (error: any) {
            console.error('Failed to fetch portfolio data:', error.message);
            setPortfolioError(error.message);

            // If API fails, try to use cache as fallback
            const cachedData = getCachedData();
            if (cachedData) {
                setPortfolioData(cachedData);
                setIsDataFromCache(true);
                console.log('Using cached data as fallback due to API error');
            }
        } finally {
            setPortfolioLoading(false);
        }
    };


    // Fetch rebalance history
    const fetchRebalanceHistory = async () => {
        try {
            setRebalanceLoading(true);
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002';
            const response = await axios.get(`${apiUrl}/api/portfolio/rebalance-history`);
            
            if (response.data.success) {
                setRebalanceHistory(response.data.data || []);
            }
        } catch (error: any) {
            console.error('Failed to fetch rebalance history:', error);
            setRebalanceHistory([]);
        } finally {
            setRebalanceLoading(false);
        }
    };

    // Load portfolio data and rebalance history on component mount
    useEffect(() => {
        fetchPortfolioData();
        fetchRebalanceHistory();
    }, []);

    // Initialize chart with real data
    useEffect(() => {
        const ctx = document.getElementById('portfolio-chart') as HTMLCanvasElement;
        if (!ctx || !portfolioData) return;

        const chartData = portfolioData.chart_data || [];

        // Prepare chart labels and data
        const labels = chartData.map((item: any) => item.date);
        const qualityData = chartData.map((item: any) => item.quality || 0);
        const valueData = chartData.map((item: any) => item.value || 0);
        const growthData = chartData.map((item: any) => item.growth || 0);
        const momentumData = chartData.map((item: any) => item.momentum || 0);

        const myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Quality', data: qualityData, borderColor: '#10B981', backgroundColor: 'rgba(16, 185, 129, 0.1)', tension: 0.4 },
                    { label: 'Value', data: valueData, borderColor: '#3B82F6', backgroundColor: 'rgba(59, 130, 246, 0.1)', tension: 0.4 },
                    { label: 'Growth', data: growthData, borderColor: '#A78BFA', backgroundColor: 'rgba(167, 139, 250, 0.1)', tension: 0.4 },
                    { label: 'Momentum', data: momentumData, borderColor: '#F59E0B', backgroundColor: 'rgba(245, 158, 11, 0.1)', tension: 0.4 },
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: '#A1A1AA', font: { size: 12 }, padding: 15, usePointStyle: true } },
                    tooltip: {
                        backgroundColor: 'rgba(24, 24, 27, 0.95)', titleColor: '#FAFAFA', bodyColor: '#A1A1AA', borderColor: '#27272A', borderWidth: 1,
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y || 0;
                                return context.dataset.label + (value >= 0 ? '+' : '') + value.toFixed(1) + '%';
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: 'rgba(39, 39, 42, 0.5)' }, ticks: { color: '#71717A', font: { size: 11 } } },
                    y: {
                        grid: { color: 'rgba(39, 39, 42, 0.5)' },
                        ticks: {
                            color: '#71717A',
                            font: { size: 11 },
                            callback: function (value: any) {
                                return (value >= 0 ? '+' : '') + value.toFixed(1) + '%';
                            }
                        }
                    }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });

        return () => myChart.destroy();
    }, [portfolioData]);

    const toggleHoldings = (key: string) => {
        setExpandedPortfolio(expandedPortfolio === key ? null : key);
    };

    // Currency symbol helper function
    const getCurrencySymbol = (currency: string) => {
        switch (currency?.toUpperCase()) {
            case 'USD':
                return '$';
            case 'HKD':
                return 'HK$';
            case 'CNY':
                return '¥';
            default:
                return '$';
        }
    };

    // Exchange rates (should ideally come from API, using approximation for now)
    const exchangeRates = {
        'USD': 1,
        'HKD': 0.128, // 1 HKD = 0.128 USD
        'CNY': 0.139  // 1 CNY = 0.139 USD
    };

    // Convert to USD for allocation calculation
    const convertToUSD = (amount: number, currency: string) => {
        const rate = exchangeRates[currency?.toUpperCase() as keyof typeof exchangeRates] || 1;
        return amount * rate;
    };

    return (
        <div className="min-h-screen relative overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)] font-sans">
            <style>{originalStyles}</style>

            {/* Background Grid */}
            <div className="absolute inset-0 z-0 pointer-events-none" style={{
                backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)',
                backgroundSize: '40px 40px'
            }}></div>

            {/* Hero Glow */}
            <div className="hero-glow"></div>

            {/* Mobile-Responsive Navbar */}
            <nav className="fixed w-full z-50 landing-nav">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-xl tracking-tight">
                                Alpha<span style={{ color: '#0D9B97' }}>GBM</span>
                            </span>
                        </div>

                        {/* Desktop Navigation */}
                        <div className="hidden md:flex items-center gap-8">
                            <div className="flex items-baseline space-x-8">
                                <a href="#" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{content.nav.home}</a>
                                <a href="#portfolio" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{content.nav.portfolio}</a>
                                <a href="#styles" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{content.nav.styles}</a>
                                <a href="#contact" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{content.nav.contact}</a>
                            </div>

                            <div className="flex items-center gap-4">
                                <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                    {content.nav.lang}
                                </button>
                                <a href="/stock" className="btn-primary rounded-full px-4 py-2 text-sm font-semibold hover:bg-opacity-90 transition-colors shadow-brand">
                                    {content.nav.cta}
                                </a>
                            </div>
                        </div>

                        {/* Mobile Menu Button */}
                        <button
                            className="md:hidden p-2 text-[var(--text-secondary)] hover:text-brand transition-colors"
                            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                            aria-label="Toggle mobile menu"
                        >
                            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>

                    {/* Mobile Navigation Menu */}
                    {isMobileMenuOpen && (
                        <div className="md:hidden bg-[rgba(24,24,27,0.95)] backdrop-blur-md border-t border-slate-700">
                            <div className="px-4 py-4 space-y-4">
                                <a href="#" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {content.nav.home}
                                </a>
                                <a href="#portfolio" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {content.nav.portfolio}
                                </a>
                                <a href="#styles" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {content.nav.styles}
                                </a>
                                <a href="#contact" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {content.nav.contact}
                                </a>

                                <div className="border-t border-slate-700 pt-4 mt-4 space-y-4">
                                    <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                        {content.nav.lang}
                                    </button>
                                    <a href="/stock" className="btn-primary rounded-full px-4 py-2 text-sm font-semibold hover:bg-opacity-90 transition-colors shadow-brand block text-center" onClick={closeMobileMenu}>
                                        {content.nav.cta}
                                    </a>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </nav>

            {/* Hero Section */}
            <main className="relative z-10 pt-20 sm:pt-32 pb-8 sm:pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
                <div className="text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-brand text-xs font-medium mb-4 sm:mb-6">
                        <i className="ph ph-sparkle-fill"></i>
                        {content.hero.badge}
                    </div>
                    <h1 className="text-3xl sm:text-5xl md:text-7xl font-extrabold tracking-tight mb-4 sm:mb-6">
                        AlphaGBM
                        <br />
                        <span className="text-2xl sm:text-4xl md:text-6xl leading-tight">{content.hero.titleSub}</span>
                    </h1>
                    <h2 className="mt-3 sm:mt-4 max-w-2xl mx-auto text-base sm:text-xl text-[var(--text-secondary)] font-normal px-4 leading-relaxed">
                        {content.hero.subtitle}
                    </h2>

                    <div className="mt-8 sm:mt-10 flex flex-col items-center">
                        <a href="/stock" className="btn-primary beta-pulse px-6 sm:px-8 py-3 rounded-lg font-bold transition-all shadow-brand text-white text-sm sm:text-base">
                            {content.hero.cta_primary}
                        </a>
                        <div className="mt-4 text-xs text-[var(--text-muted)] bg-slate-800/50 px-4 py-2 rounded-full border border-slate-700 text-center">
                            {content.hero.limit_notice}
                        </div>
                    </div>

                    {/* Value Proposition */}
                    <section id="value-proposition" className="my-12 sm:my-20">
                        <div className="text-center mb-8 sm:mb-12">
                            <h2 className="text-2xl sm:text-3xl font-bold mb-4 px-4">{content.valueProposition.title}</h2>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 max-w-6xl mx-auto px-4 sm:px-0">
                            {content.valueProposition.items.map((item, idx) => (
                                <a key={idx} href={item.link || '#'} className="block no-underline h-full">
                                    <div className="glass-card rounded-xl p-4 sm:p-6 text-center transition-all hover:border-[var(--brand-primary)]/50 hover:transform hover:scale-105 cursor-pointer h-full">
                                        <div className="flex items-center justify-center mb-3 sm:mb-4 text-brand">
                                            <i className={`ph ph-${item.icon} text-3xl sm:text-4xl`}></i>
                                        </div>
                                        <div className="flex flex-col sm:flex-row items-center justify-center gap-2 mb-3">
                                            <h3 className="text-lg sm:text-xl font-bold text-white">{item.title}</h3>
                                            {item.badge && <span className="px-2 py-1 text-xs font-semibold bg-brand/20 text-brand rounded-full border border-brand/30">{item.badge}</span>}
                                        </div>
                                        <p className="text-[var(--text-secondary)] text-sm leading-relaxed">{item.desc}</p>
                                    </div>
                                </a>
                            ))}
                        </div>
                    </section>

                    {/* Styles Section - Moved before Portfolio */}
                    <section id="styles" className="py-6 sm:py-8 bg-slate-900/30 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8">
                        <div className="max-w-7xl mx-auto">
                            <div className="text-center mb-6 sm:mb-8">
                                <h2 className="text-xl sm:text-2xl font-bold tracking-tight mb-2">{content.styles.title}</h2>
                                {content.styles.desc && (
                                    <p className="text-[var(--text-secondary)] text-sm sm:text-base">{content.styles.desc}</p>
                                )}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                                {content.styles.cards.map((style, index) => (
                                    <div key={index} className="glass-card p-3 sm:p-4 rounded-xl relative overflow-hidden group">
                                        <h3 className={`text-base sm:text-lg font-bold mb-1.5 ${style.color}`}>{style.name}</h3>
                                        <p className="text-[var(--text-secondary)] text-xs sm:text-sm leading-relaxed">{style.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* Portfolio Section */}
                    <section id="portfolio" className="my-12 sm:my-20 px-4 sm:px-0">
                        <div className="text-center mb-8 sm:mb-12">
                            <div className="flex items-center justify-center mb-4 gap-3">
                                <h2 className="text-2xl sm:text-3xl font-bold">{content.portfolio.title}</h2>
                                {false && !portfolioLoading && portfolioData && (
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => fetchPortfolioData(true)}
                                            className="p-2 text-slate-400 hover:text-brand transition-colors"
                                            title="刷新数据"
                                        >
                                            <i className="ph ph-arrow-clockwise text-lg"></i>
                                        </button>
                                        <div
                                            className={`text-xs px-2 py-1 rounded-full cursor-help ${isDataFromCache ? 'bg-yellow-500/20 text-yellow-400' : 'bg-emerald-500/20 text-emerald-400'}`}
                                            title={isDataFromCache ? `缓存数据：${getCacheInfo()}` : '实时数据'}
                                        >
                                            {isDataFromCache ? `缓存 (${getCacheInfo()})` : '实时'}
                                        </div>
                                    </div>
                                )}
                            </div>
                            <p className="text-[var(--text-secondary)] max-w-2xl mx-auto text-sm sm:text-base px-4 sm:px-0 leading-relaxed">{content.portfolio.description}</p>
                        </div>

                        {/* Total Portfolio Summary - Cumulative Profit */}
                        {portfolioData && portfolioData.style_stats && (
                            <div className="glass-card rounded-2xl p-4 sm:p-6 mb-6 sm:mb-8 border border-brand/30">
                                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                                    <div className="text-center sm:text-left">
                                        <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
                                            <i className="ph ph-wallet text-brand"></i>
                                            {i18n.language === 'zh' ? '投资组合总览' : 'Portfolio Summary'}
                                        </h3>
                                        <p className="text-xs text-[var(--text-secondary)] mt-1">
                                            {i18n.language === 'zh' ? '初始投资: $1,000,000 (4×$250K)' : 'Initial Investment: $1,000,000 (4×$250K)'}
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap items-center justify-center sm:justify-end gap-4 sm:gap-8">
                                        {/* Total Market Value */}
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {i18n.language === 'zh' ? '当前市值' : 'Market Value'}
                                            </div>
                                            <div className="text-lg sm:text-xl font-bold text-white">
                                                ${(Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.market_value || 0), 0) / 1000).toFixed(0)}K
                                            </div>
                                        </div>
                                        {/* Total Cumulative Profit */}
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {i18n.language === 'zh' ? '累积收益' : 'Cumulative Profit'}
                                            </div>
                                            {(() => {
                                                const totalInvestment = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.investment || 0), 0);
                                                const totalMarketValue = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.market_value || 0), 0);
                                                const totalProfit = totalMarketValue - totalInvestment;
                                                const totalProfitPercent = totalInvestment > 0 ? (totalProfit / totalInvestment) * 100 : 0;
                                                const isPositive = totalProfit >= 0;
                                                return (
                                                    <div className={`text-xl sm:text-2xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {isPositive ? '+' : ''}{totalProfitPercent.toFixed(1)}%
                                                        <span className="text-sm ml-1">
                                                            ({isPositive ? '+' : ''}${(totalProfit / 1000).toFixed(0)}K)
                                                        </span>
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                        {/* Today's Change */}
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {i18n.language === 'zh' ? '今日变化' : "Today's Change"}
                                            </div>
                                            {(() => {
                                                const todayChange = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => {
                                                    return sum + parseFloat(s.vsYesterdayPercent || '0');
                                                }, 0) / 4; // Average of 4 styles
                                                const isPositive = todayChange >= 0;
                                                return (
                                                    <div className={`text-lg sm:text-xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {isPositive ? '+' : ''}{todayChange.toFixed(2)}%
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="glass-card rounded-2xl p-4 sm:p-6 mb-6 sm:mb-8">
                            <h3 className="text-lg sm:text-xl font-bold mb-4 sm:mb-6 flex items-center gap-2">
                                <i className="ph ph-chart-line-up"></i>
                                {content.portfolio.performanceChart}
                            </h3>
                            <div className="w-full h-[300px] sm:h-[400px]">
                                <canvas id="portfolio-chart"></canvas>
                            </div>
                        </div>

                        {/* Portfolio Summary Cards */}
                        {portfolioLoading ? (
                            // Loading skeleton
                            <div className="space-y-4 sm:space-y-6 mb-6 sm:mb-8">
                                {[1, 2, 3, 4].map((i) => (
                                    <div key={i} className="glass-card rounded-2xl p-4 sm:p-6 animate-pulse">
                                        <div className="flex flex-col sm:flex-row items-center justify-between mb-4 gap-3 sm:gap-4">
                                            <div className="flex items-center gap-3 sm:gap-4 w-full sm:w-auto">
                                                <div className="w-1 h-10 sm:h-12 rounded-full bg-gray-600"></div>
                                                <div className="text-center sm:text-left">
                                                    <div className="h-6 bg-gray-600 rounded w-24 mb-2"></div>
                                                    <div className="h-4 bg-gray-700 rounded w-32"></div>
                                                </div>
                                            </div>
                                            <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 w-full sm:w-auto">
                                                <div className="text-center sm:text-right">
                                                    <div className="h-8 bg-gray-600 rounded w-20 mb-2"></div>
                                                    <div className="h-5 bg-gray-700 rounded w-24"></div>
                                                </div>
                                                <div className="h-8 bg-gray-600 rounded w-24"></div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : portfolioError ? (
                            // Error state
                            <div className="glass-card rounded-2xl p-4 sm:p-6 mb-6 sm:mb-8 text-center">
                                <div className="text-red-400 mb-4">
                                    <i className="ph ph-warning text-4xl mb-2" style={{ display: 'block' }}></i>
                                    <p>加载投资组合数据时出错</p>
                                    <p className="text-sm text-slate-400 mt-1">
                                        {portfolioData ? '正在使用缓存数据' : '无法获取数据'}
                                    </p>
                                </div>
                                <div className="flex justify-center gap-3">
                                    <button
                                        onClick={() => fetchPortfolioData(false)}
                                        className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors"
                                    >
                                        重新加载
                                    </button>
                                    <button
                                        onClick={() => fetchPortfolioData(true)}
                                        className="px-4 py-2 bg-brand text-white rounded-lg hover:bg-brand/80 transition-colors"
                                    >
                                        强制刷新
                                    </button>
                                </div>
                            </div>
                        ) : null}

                        <div className="space-y-4 sm:space-y-6 mb-6 sm:mb-8">
                            {[
                                { key: 'quality', name: content.portfolio.quality, color: 'emerald' },
                                { key: 'value', name: content.portfolio.value, color: 'blue' },
                                { key: 'growth', name: content.portfolio.growth, color: 'purple' },
                                { key: 'momentum', name: content.portfolio.momentum, color: 'orange' }
                            ].map((config, idx) => {
                                // Use real data from API
                                const stats = portfolioData?.style_stats?.[config.key];

                                // Skip rendering if no stats available
                                if (!stats) return null;

                                const isPositive = parseFloat(stats.vsYesterdayPercent) >= 0;

                                return (
                                    <div key={idx} className="glass-card rounded-2xl p-4 sm:p-6">
                                        <div className="flex flex-col sm:flex-row items-center justify-between mb-4 gap-3 sm:gap-4">
                                            <div className="flex items-center gap-3 sm:gap-4 w-full sm:w-auto">
                                                <div className={`w-1 h-10 sm:h-12 rounded-full bg-${config.color}-500`}></div>
                                                <div className="text-center sm:text-left">
                                                    <div className={`text-${config.color}-400 font-semibold text-base sm:text-lg`}>{config.name}</div>
                                                    <div className="text-xs text-[var(--text-secondary)]">{content.portfolio.initialCapital}: $250K</div>
                                                </div>
                                            </div>
                                            <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 w-full sm:w-auto">
                                                <div className="text-center sm:text-right">
                                                    <div className={`text-xl sm:text-2xl font-bold ${parseFloat(stats.profitLossPercent) >= 0 ? 'text-white' : 'text-red-400'}`}>
                                                        {parseFloat(stats.profitLossPercent) >= 0 ? '+' : ''}{stats.profitLossPercent}%
                                                    </div>
                                                    <div className={`text-sm ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {content.portfolio.dailyChange}: {isPositive ? '+' : ''}{stats.vsYesterdayPercent}%
                                                    </div>
                                                </div>
                                                <button onClick={() => toggleHoldings(config.key)} className="px-3 sm:px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-xs sm:text-sm transition-colors whitespace-nowrap">
                                                    {expandedPortfolio === config.key ? content.portfolio.hideHoldings : content.portfolio.viewHoldings}
                                                </button>
                                            </div>
                                        </div>

                                        {expandedPortfolio === config.key && (
                                            <div className="mt-4">
                                                {/* Desktop Table */}
                                                <div className="hidden sm:block overflow-x-auto">
                                                    <table className="w-full text-sm">
                                                        <thead>
                                                            <tr className="border-b border-slate-700">
                                                                <th className="text-left py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.stock}</th>
                                                                <th className="text-right py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.shares}</th>
                                                                <th className="text-right py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.costPrice}</th>
                                                                <th className="text-right py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.currentPrice}</th>
                                                                <th className="text-right py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.allocation}</th>
                                                                <th className="text-right py-3 px-2 text-[var(--text-secondary)] font-medium">{content.portfolio.profitPercent}</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {(portfolioData?.holdings_by_style?.[config.key] || []).map((holding: any, hidx: number) => {
                                                                const profit = ((holding.current - holding.cost) / holding.cost * 100).toFixed(2);
                                                                const marketValueUSD = convertToUSD(holding.current * holding.shares, holding.currency);
                                                                const totalPortfolioValueUSD = (portfolioData?.holdings_by_style?.[config.key] || [])
                                                                    .reduce((sum: number, h: any) => sum + convertToUSD(h.current * h.shares, h.currency), 0);
                                                                const allocation = totalPortfolioValueUSD > 0 ? ((marketValueUSD / totalPortfolioValueUSD) * 100).toFixed(1) : '0.0';
                                                                const currencySymbol = getCurrencySymbol(holding.currency);
                                                                return (
                                                                    <tr key={hidx} className="border-b border-slate-800 last:border-b-0">
                                                                        <td className="py-3 px-2">
                                                                            <div className="font-medium text-white">{translateStockName(holding.ticker, t, holding.name)} ({holding.ticker})</div>
                                                                        </td>
                                                                        <td className="py-3 px-2 text-right text-white">{holding.shares}</td>
                                                                        <td className="py-3 px-2 text-right text-white">{currencySymbol}{holding.cost}</td>
                                                                        <td className="py-3 px-2 text-right text-white">{currencySymbol}{holding.current}</td>
                                                                        <td className="py-3 px-2 text-right text-white">{allocation}%</td>
                                                                        <td className={`py-3 px-2 text-right font-medium ${parseFloat(profit) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                                            {parseFloat(profit) >= 0 ? '+' : ''}{profit}%
                                                                        </td>
                                                                    </tr>
                                                                )
                                                            })}
                                                        </tbody>
                                                    </table>
                                                </div>

                                                {/* Mobile Cards */}
                                                <div className="sm:hidden space-y-3">
                                                    {(portfolioData?.holdings_by_style?.[config.key] || []).map((holding: any, hidx: number) => {
                                                        const profit = ((holding.current - holding.cost) / holding.cost * 100).toFixed(2);
                                                        const marketValueUSD = convertToUSD(holding.current * holding.shares, holding.currency);
                                                        const totalPortfolioValueUSD = (portfolioData?.holdings_by_style?.[config.key] || [])
                                                            .reduce((sum: number, h: any) => sum + convertToUSD(h.current * h.shares, h.currency), 0);
                                                        const allocation = totalPortfolioValueUSD > 0 ? ((marketValueUSD / totalPortfolioValueUSD) * 100).toFixed(1) : '0.0';
                                                        const currencySymbol = getCurrencySymbol(holding.currency);
                                                        return (
                                                            <div key={hidx} className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                                                                <div className="flex justify-between items-center mb-2">
                                                                    <div className="font-medium text-white text-sm">{translateStockName(holding.ticker, t, holding.name)}</div>
                                                                    <div className="text-xs text-slate-400">({holding.ticker})</div>
                                                                </div>
                                                                <div className="grid grid-cols-2 gap-2 text-xs">
                                                                    <div className="flex justify-between">
                                                                        <span className="text-[var(--text-secondary)]">{content.portfolio.shares}:</span>
                                                                        <span className="text-white">{holding.shares}</span>
                                                                    </div>
                                                                    <div className="flex justify-between">
                                                                        <span className="text-[var(--text-secondary)]">{content.portfolio.costPrice}:</span>
                                                                        <span className="text-white">{currencySymbol}{holding.cost}</span>
                                                                    </div>
                                                                    <div className="flex justify-between">
                                                                        <span className="text-[var(--text-secondary)]">{content.portfolio.currentPrice}:</span>
                                                                        <span className="text-white">{currencySymbol}{holding.current}</span>
                                                                    </div>
                                                                    <div className="flex justify-between">
                                                                        <span className="text-[var(--text-secondary)]">{content.portfolio.allocation}:</span>
                                                                        <span className="text-white">{allocation}%</span>
                                                                    </div>
                                                                    <div className="flex justify-between col-span-2">
                                                                        <span className="text-[var(--text-secondary)]">{content.portfolio.profitPercent}:</span>
                                                                        <span className={`font-medium ${parseFloat(profit) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                                            {parseFloat(profit) >= 0 ? '+' : ''}{profit}%
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </section>

                    {/* Rebalance History Section */}
                    {rebalanceHistory.length > 0 && (
                        <div className="mt-8 sm:mt-10 px-4 sm:px-0">
                            <div className="text-center mb-4 sm:mb-6">
                                <h3 className="text-lg sm:text-xl font-bold mb-2">调仓历史 (每2周Review)</h3>
                                <p className="text-xs sm:text-sm text-[var(--text-secondary)]">查看历史调仓记录及调仓后的盈亏表现</p>
                            </div>
                            
                            <div className="space-y-3 sm:space-y-4 max-w-5xl mx-auto">
                                {rebalanceHistory.map((rebalance) => {
                                    const isExpanded = expandedRebalance === rebalance.id;
                                    const changes = rebalance.changes_detail || {};
                                    const added = changes.added || [];
                                    const removed = changes.removed || [];
                                    const adjusted = changes.adjusted || [];
                                    
                                    return (
                                        <div key={rebalance.id} className="glass-card rounded-xl p-3 sm:p-4">
                                            {/* Rebalance Header */}
                                            <div 
                                                className="flex items-center justify-between cursor-pointer"
                                                onClick={() => setExpandedRebalance(isExpanded ? null : rebalance.id)}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-2 h-2 rounded-full bg-brand"></div>
                                                    <div>
                                                        <div className="text-sm sm:text-base font-semibold text-white">
                                                            第{rebalance.rebalance_number}次调仓
                                                        </div>
                                                        <div className="text-xs text-[var(--text-secondary)]">
                                                            {rebalance.rebalance_date}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    {/* Latest P/L after rebalance */}
                                                    <div className="text-right">
                                                        <div className={`text-sm sm:text-base font-bold ${rebalance.total_profit_loss_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                            {rebalance.total_profit_loss_percent >= 0 ? '+' : ''}{rebalance.total_profit_loss_percent.toFixed(1)}%
                                                        </div>
                                                        <div className="text-xs text-[var(--text-secondary)]">调仓后盈亏</div>
                                                    </div>
                                                    {/* Changes Summary */}
                                                    <div className="flex items-center gap-2 text-xs">
                                                        {added.length > 0 && (
                                                            <span className="px-2 py-1 rounded bg-emerald-500/20 text-emerald-400">
                                                                +{added.length}
                                                            </span>
                                                        )}
                                                        {removed.length > 0 && (
                                                            <span className="px-2 py-1 rounded bg-red-500/20 text-red-400">
                                                                -{removed.length}
                                                            </span>
                                                        )}
                                                        {adjusted.length > 0 && (
                                                            <span className="px-2 py-1 rounded bg-yellow-500/20 text-yellow-400">
                                                                ~{adjusted.length}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <button className="text-[var(--text-secondary)] hover:text-white transition-colors">
                                                        <i className={`bi bi-chevron-${isExpanded ? 'up' : 'down'}`}></i>
                                                    </button>
                                                </div>
                                            </div>
                                            
                                            {/* Expanded Details */}
                                            {isExpanded && (
                                                <div className="mt-4 pt-4 border-t border-slate-700/50">
                                                    {/* Changes Details */}
                                                    {added.length > 0 && (
                                                        <div className="mb-3">
                                                            <div className="text-xs font-semibold text-emerald-400 mb-2">新增持仓 ({added.length})</div>
                                                            <div className="space-y-1.5">
                                                                {added.map((item: any, i: number) => (
                                                                    <div key={i} className="text-xs text-[var(--text-secondary)] pl-3 border-l-2 border-emerald-500/30">
                                                                        <span className="text-white font-medium">{item.name} ({item.ticker})</span>
                                                                        <span className="ml-2">{item.shares}股 @ ${item.buy_price?.toFixed(2)}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                    
                                                    {removed.length > 0 && (
                                                        <div className="mb-3">
                                                            <div className="text-xs font-semibold text-red-400 mb-2">移除持仓 ({removed.length})</div>
                                                            <div className="space-y-1.5">
                                                                {removed.map((item: any, i: number) => (
                                                                    <div key={i} className="text-xs text-[var(--text-secondary)] pl-3 border-l-2 border-red-500/30">
                                                                        <span className="text-white font-medium">{item.name} ({item.ticker})</span>
                                                                        <span className="ml-2">{item.shares}股</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                    
                                                    {adjusted.length > 0 && (
                                                        <div className="mb-3">
                                                            <div className="text-xs font-semibold text-yellow-400 mb-2">调整持仓 ({adjusted.length})</div>
                                                            <div className="space-y-1.5">
                                                                {adjusted.map((item: any, i: number) => (
                                                                    <div key={i} className="text-xs text-[var(--text-secondary)] pl-3 border-l-2 border-yellow-500/30">
                                                                        <span className="text-white font-medium">{item.name} ({item.ticker})</span>
                                                                        <span className="ml-2">
                                                                            {item.old_shares}股 → {item.new_shares}股
                                                                            {item.old_price && item.new_price && (
                                                                                <span className="ml-1">@ ${item.old_price?.toFixed(2)} → ${item.new_price?.toFixed(2)}</span>
                                                                            )}
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                    
                                                    {/* Style Stats after rebalance */}
                                                    {rebalance.style_stats && Object.keys(rebalance.style_stats).length > 0 && (
                                                        <div className="mt-4 pt-3 border-t border-slate-700/50">
                                                            <div className="text-xs font-semibold text-white mb-2">调仓后各风格盈亏</div>
                                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                                                {Object.entries(rebalance.style_stats).map(([style, stats]: [string, any]) => {
                                                                    const styleNames: Record<string, string> = {
                                                                        'quality': '质量',
                                                                        'value': '价值',
                                                                        'growth': '成长',
                                                                        'momentum': '趋势'
                                                                    };
                                                                    const pct = stats.profit_loss_percent || 0;
                                                                    return (
                                                                        <div key={style} className="text-xs">
                                                                            <div className="text-[var(--text-secondary)]">{styleNames[style] || style}</div>
                                                                            <div className={`font-semibold ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                                                {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </div>
                                                    )}
                                                    
                                                    {/* Notes */}
                                                    {rebalance.notes && (
                                                        <div className="mt-3 pt-3 border-t border-slate-700/50">
                                                            <div className="text-xs text-[var(--text-secondary)] italic">{rebalance.notes}</div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Features Section */}
                <section id="features" className="py-6 sm:py-8 px-4 sm:px-0">
                    <div className="max-w-5xl mx-auto">
                        <div className="text-center mb-4 sm:mb-6">
                            <h2 className="text-xl sm:text-2xl font-bold tracking-tight mb-2">{content.features.title}</h2>
                        </div>
                        <div className="glass-card rounded-xl p-3 sm:p-5">
                            <div className="space-y-2 sm:space-y-2.5">
                                {content.features.items.map((feature, idx) => (
                                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-2 border-b border-slate-700/50 last:border-b-0 gap-1.5 sm:gap-0">
                                        <div className="flex-1">
                                            <span className="text-sm sm:text-base font-semibold text-white">{feature.title}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-slate-500 hidden sm:inline text-xs">|</span>
                                            <span className="text-[var(--text-secondary)] font-mono text-xs">{feature.desc}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>

                {/* FAQ */}
                <section id="faq" className="py-6 sm:py-8 px-4 sm:px-0">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-4 sm:mb-6">
                            <h2 className="text-xl sm:text-2xl font-bold mb-2">{content.faq.title}</h2>
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4">
                            {content.faq.items.map((item, idx) => (
                                <div key={idx} className="glass-card rounded-xl p-3 sm:p-4">
                                    <h3 className="text-sm sm:text-base font-semibold text-white mb-2">{item.question}</h3>
                                    <p className="text-[var(--text-secondary)] leading-relaxed text-xs sm:text-sm">{item.answer}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* CTA Contact */}
                <section id="contact" className="py-12 sm:py-20 relative overflow-hidden px-4">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] sm:w-[500px] h-[300px] sm:h-[500px] bg-brand/10 blur-[100px] rounded-full pointer-events-none"></div>
                    <div className="max-w-4xl mx-auto relative z-10">
                        <div className="glass-card rounded-2xl p-6 sm:p-8 lg:p-12 text-center border border-slate-700/50 shadow-2xl">
                            <h2 className="text-2xl sm:text-3xl font-bold mb-4">{content.cta.title}</h2>
                            <p className="text-[var(--text-secondary)] mb-6 sm:mb-8 max-w-xl mx-auto text-sm sm:text-base">{content.cta.desc}</p>
                            <div className="flex flex-col items-center justify-center">
                                <div className="w-32 h-32 sm:w-48 sm:h-48 bg-white rounded-xl overflow-hidden border-4 border-white shadow-lg relative">
                                    <img
                                        src="/WeChat-QR-Code.jpg"
                                        alt="Alpha GBM WeChat QR Code"
                                        className="w-full h-full object-cover"
                                    />
                                </div>
                                <div className="mt-4 text-brand font-semibold text-xs sm:text-sm flex items-center gap-2">
                                    <i className="ph ph-qr-code"></i>
                                    {content.cta.scan_text}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-slate-800 bg-slate-950 py-8 sm:py-12 -mx-4 sm:-mx-6 lg:-mx-8">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                        <div className="flex items-center justify-center gap-2 mb-6 sm:mb-8">
                            <span className="font-bold text-lg sm:text-xl tracking-tight">Alpha<span style={{ color: '#0D9B97' }}>GBM</span></span>
                        </div>
                        <p className="text-slate-600 text-xs sm:text-sm mb-4">244 - 248 Des Voeux Rd Central, Central, Hong Kong</p>
                        <p className="text-slate-600 text-xs sm:text-sm max-w-2xl mx-auto mb-4 leading-relaxed px-4 sm:px-0">{content.footer.disclaimer}</p>
                        <div className="flex items-center gap-4 flex-wrap justify-center">
                            <p className="text-slate-700 text-xs sm:text-sm">{content.footer.copy}</p>
                            <span className="text-slate-700">|</span>
                            <PrivacyPolicy />
                        </div>
                    </div>
                </footer>
            </main>

            {/* Feedback Button */}
            <FeedbackButton />
        </div>
    );
}
