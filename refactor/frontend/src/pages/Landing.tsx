import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Chart from 'chart.js/auto';
import { Menu, X } from 'lucide-react';
import axios from 'axios';

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
    const { i18n } = useTranslation();
    const [expandedPortfolio, setExpandedPortfolio] = useState<string | null>(null);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Portfolio data state
    const [portfolioData, setPortfolioData] = useState<any>(null);
    const [portfolioLoading, setPortfolioLoading] = useState(true);
    const [portfolioError, setPortfolioError] = useState<string | null>(null);

    const toggleLang = () => {
        i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    // Strict content mapping
    const content = {
        nav: {
            home: i18n.language === 'zh' ? "首页" : "Home",
            portfolio: i18n.language === 'zh' ? "实盘追踪" : "Live Tracking",
            styles: i18n.language === 'zh' ? "模型理念" : "Model Philosophy",
            contact: i18n.language === 'zh' ? "关注我们" : "Follow Us",
            cta: i18n.language === 'zh' ? "立即体验" : "Try Now",
            lang: i18n.language === 'zh' ? "EN" : "中"
        },
        portfolio: {
            title: i18n.language === 'zh' ? "四大风格投资组合实盘追踪" : "Four-Style Portfolio Live Tracking",
            description: i18n.language === 'zh' ? "四种投资风格组合（质量、价值、成长、趋势），每个组合 25 万美元，共 100 万美元实盘追踪" : "Four investment style portfolios (Quality, Value, Growth, Momentum), each with $250K, total $1M live tracking",
            quality: i18n.language === 'zh' ? "质量组合" : "Quality Portfolio",
            value: i18n.language === 'zh' ? "价值组合" : "Value Portfolio",
            growth: i18n.language === 'zh' ? "成长组合" : "Growth Portfolio",
            momentum: i18n.language === 'zh' ? "趋势组合" : "Momentum Portfolio",
            performanceChart: i18n.language === 'zh' ? "累计收益走势图" : "Cumulative Return",
            viewHoldings: i18n.language === 'zh' ? "查看持仓" : "View Holdings",
            hideHoldings: i18n.language === 'zh' ? "收起持仓" : "Hide Holdings",
            stock: i18n.language === 'zh' ? "股票" : "Stock",
            shares: i18n.language === 'zh' ? "持仓股数" : "Shares",
            costPrice: i18n.language === 'zh' ? "成本价" : "Cost",
            currentPrice: i18n.language === 'zh' ? "当前价" : "Current",
            allocation: i18n.language === 'zh' ? "占比" : "Weight",
            profitPercent: i18n.language === 'zh' ? "收益率" : "Return",
            dailyChange: i18n.language === 'zh' ? "今日变化" : "Daily Change",
            initialCapital: i18n.language === 'zh' ? "初始资金" : "Initial Capital"
        },
        hero: {
            badge: "Powered by LLM",
            titleSub: i18n.language === 'zh' ? "AI 驱动的机构级投资操作系统" : "AI-Driven Institutional Investment Operating System",
            subtitle: i18n.language === 'zh' ? "融合股票模型、期权策略与全自动智能体。不预测未来，只计算概率。" : "Integrating stock models, options strategies, and fully autonomous agents. We don't predict the future; we calculate probabilities.",
            cta_primary: i18n.language === 'zh' ? "立即开启 AI 投资" : "Start AI Investing Now",
            limit_notice: i18n.language === 'zh' ? "注册即送每日 2 次分析机会" : "Register for 2 free analyses daily"
        },
        valueProposition: {
            title: i18n.language === 'zh' ? "三大引擎" : "Three Engines",
            items: [
                { icon: "chart-line-up", title: i18n.language === 'zh' ? "股票" : "Stocks", badge: "", desc: i18n.language === 'zh' ? "覆盖美/港/A股，精准识别价值与趋势。" : "Covering US/HK/A-shares, precisely identifying value and trends.", link: "/stock" },
                { icon: "sigma", title: i18n.language === 'zh' ? "期权" : "Options", badge: "New", desc: i18n.language === 'zh' ? "寻找高概率非对称收益机会。" : "Finding high-probability asymmetric return opportunities.", link: "/options" },
                { icon: "robot", title: i18n.language === 'zh' ? "智能体" : "Agent", badge: "Coming Soon", desc: i18n.language === 'zh' ? "24/7个性化专业投资助理" : "Your 24/7 personalized professional investment assistant", link: null }
            ]
        },
        styles: {
            title: i18n.language === 'zh' ? "投资理念与四大风格" : "Model Philosophy & 4 Styles",
            desc: i18n.language === 'zh' ? "基于G=B+M模型，系统自动适配您的投资风格" : "Based on G=B+M Model, adapting to your investment style",
            cards: [
                { name: i18n.language === 'zh' ? "质量策略" : "Quality", color: "text-emerald-400", desc: i18n.language === 'zh' ? "护城河深、财务稳健。适合长期持有。" : "Wide moat, strong financials. Long-term." },
                { name: i18n.language === 'zh' ? "价值策略" : "Value", color: "text-blue-400", desc: i18n.language === 'zh' ? "低估值、安全边际。寻找错杀机会。" : "Undervalued, safety margin. Mid-term." },
                { name: i18n.language === 'zh' ? "成长策略" : "Growth", color: "text-purple-400", desc: i18n.language === 'zh' ? "高营收增速。容忍高估值换取成长。" : "High revenue growth. High risk tolerance." },
                { name: i18n.language === 'zh' ? "趋势策略" : "Momentum", color: "text-orange-400", desc: i18n.language === 'zh' ? "价格动量驱动。快进快出跟随趋势。" : "Price action driven. Short-term trading." }
            ]
        },
        features: {
            title: i18n.language === 'zh' ? "核心能力" : "Core Capabilities",
            items: [
                { title: i18n.language === 'zh' ? "深度研报生成" : "Deep Report Generation", desc: "Powered by LLM" },
                { title: i18n.language === 'zh' ? "风险量化" : "Risk Quantification", desc: "VIX + Greeks" },
                { title: i18n.language === 'zh' ? "智能仓位管理" : "Smart Position Management", desc: i18n.language === 'zh' ? "凯利公式 + 波动率加权" : "Kelly Formula + Volatility Weighting" }
            ]
        },
        faq: {
            title: i18n.language === 'zh' ? "常见问题" : "FAQ",
            items: [
                { question: "AlphaGBM 的股票分析功能如何使用？", answer: "输入股票代码（如 AAPL、600519.SS、0700.HK），选择投资风格（质量、价值、成长、趋势），系统即可生成包含基本面分析、技术面分析、风险评估和仓位建议的完整投资报告。基于 G=B+M 模型，提供机构级的量化分析服务。" },
                { question: "AlphaGBM 支持哪些市场的股票分析？", answer: "AlphaGBM 支持三大市场：美股（AAPL、TSLA）、港股（0700.HK、2525.HK）、A股（600519、000001）。系统自动识别市场类型，无需手动添加后缀。覆盖全市场数据，打破信息壁垒，一站式完成多市场投资分析。" },
                { question: "AlphaGBM 的 G=B+M 模型是什么？", answer: "G=B+M 是 AlphaGBM 的核心投资模型，G (Gain) 代表收益，B (Basics) 代表基本面，M (Momentum) 代表动量。模型将股票收益解构为基本面支撑与市场动量的叠加，通过量化分析识别收益与内在价值的偏离，帮助投资者发现投资机会。适用于所有投资风格。" },
                { question: "AlphaGBM 的期权分析功能有哪些？", answer: "AlphaGBM 期权分析模块提供专业的期权策略分析，包括波动率分析、希腊字母（Greeks）计算、期权链数据、隐含波动率（IV）分析等。系统基于概率计算，帮助您寻找非对称收益机会。支持多种策略构建，为期权交易提供量化决策支持。" },
                { question: "AlphaGBM 如何进行风险量化评估？", answer: "AlphaGBM 采用 0-10 分动态风险评级系统，综合评估基本面风险（营收增长、利润率、估值水平）、技术面风险（价格位置、成交量异常）、市场情绪风险（VIX 恐慌指数、Put/Call 比率）、宏观风险（利率、汇率、经济指标）等多个维度。结合 VIX 和 Greeks 等量化指标，精准识别危险信号。" }
            ]
        },
        cta: {
            title: i18n.language === 'zh' ? "加入 Alpha GBM 社区" : "Join Alpha GBM Community",
            desc: i18n.language === 'zh' ? "获取内测资格、最新模型更新及深度投资策略。" : "Get Beta access, model updates, and deep strategies.",
            scan_text: i18n.language === 'zh' ? "扫码关注公众号体验" : "Scan to Follow"
        },
        footer: {
            disclaimer: i18n.language === 'zh' ? "免责声明：本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。" : "Disclaimer: This system is for educational purposes only and does not constitute investment advice.",
            copy: "© 2025 Alpha GBM. 基于 G=B+M 投资框架"
        }
    };

    // API functions
    const fetchPortfolioData = async () => {
        try {
            setPortfolioLoading(true);
            setPortfolioError(null);

            // Use environment variable API URL or fallback to localhost
            const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002';
            const response = await axios.get(`${apiUrl}/portfolio/holdings`);

            if (response.data.success) {
                setPortfolioData(response.data.data);
                console.log('Portfolio data loaded:', response.data.data);
            } else {
                throw new Error(response.data.error || 'Failed to fetch portfolio data');
            }
        } catch (error: any) {
            console.error('Failed to fetch portfolio data:', error.message);
            setPortfolioError(error.message);
        } finally {
            setPortfolioLoading(false);
        }
    };


    // Load portfolio data on component mount
    useEffect(() => {
        fetchPortfolioData();
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

                    {/* Portfolio Section */}
                    <section id="portfolio" className="my-12 sm:my-20 px-4 sm:px-0">
                        <div className="text-center mb-8 sm:mb-12">
                            <h2 className="text-2xl sm:text-3xl font-bold mb-4">{content.portfolio.title}</h2>
                            <p className="text-[var(--text-secondary)] max-w-2xl mx-auto text-sm sm:text-base px-4 sm:px-0 leading-relaxed">{content.portfolio.description}</p>
                        </div>

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
                                    <p className="text-sm text-slate-400 mt-1">正在使用模拟数据</p>
                                </div>
                                <button
                                    onClick={fetchPortfolioData}
                                    className="px-4 py-2 bg-brand text-white rounded-lg hover:bg-brand/80 transition-colors"
                                >
                                    重新加载
                                </button>
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
                                                                            <div className="font-medium text-white">{holding.name} ({holding.ticker})</div>
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
                                                                    <div className="font-medium text-white text-sm">{holding.name}</div>
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
                </div>

                {/* Styles Section */}
                <section id="styles" className="py-12 sm:py-20 bg-slate-900/30 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-10 sm:mb-16">
                            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight lg:text-4xl mb-4">{content.styles.title}</h2>
                            <p className="text-[var(--text-secondary)] text-sm sm:text-base">{content.styles.desc}</p>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                            {content.styles.cards.map((style, index) => (
                                <div key={index} className="glass-card p-4 sm:p-6 rounded-xl relative overflow-hidden group">
                                    <div className={`absolute top-0 left-0 w-1 h-full ${style.color.replace('text', 'bg').replace('-400', '-500')}`}></div>
                                    <h3 className={`text-lg sm:text-xl font-bold mb-2 ${style.color}`}>{style.name}</h3>
                                    <p className="text-[var(--text-secondary)] text-sm leading-relaxed">{style.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Features Section */}
                <section id="features" className="py-12 sm:py-20 px-4 sm:px-0">
                    <div className="max-w-5xl mx-auto">
                        <div className="text-center mb-8 sm:mb-12">
                            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight lg:text-4xl mb-6 sm:mb-8">{content.features.title}</h2>
                        </div>
                        <div className="glass-card rounded-xl p-4 sm:p-8">
                            <div className="space-y-3 sm:space-y-4">
                                {content.features.items.map((feature, idx) => (
                                    <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-3 border-b border-slate-700/50 last:border-b-0 gap-2 sm:gap-0">
                                        <div className="flex-1">
                                            <span className="text-base sm:text-lg font-semibold text-white">{feature.title}</span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-slate-500 hidden sm:inline">|</span>
                                            <span className="text-[var(--text-secondary)] font-mono text-xs sm:text-sm">{feature.desc}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>

                {/* FAQ */}
                <section id="faq" className="py-12 sm:py-20 px-4 sm:px-0">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-8 sm:mb-12">
                            <h2 className="text-2xl sm:text-3xl font-bold mb-4">{content.faq.title}</h2>
                        </div>
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                            {content.faq.items.map((item, idx) => (
                                <div key={idx} className="glass-card rounded-xl p-4 sm:p-6">
                                    <h3 className="text-base sm:text-lg font-semibold text-white mb-3">{item.question}</h3>
                                    <p className="text-[var(--text-secondary)] leading-relaxed text-sm sm:text-base">{item.answer}</p>
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
                                <div className="w-32 h-32 sm:w-48 sm:h-48 bg-white rounded-xl flex items-center justify-center overflow-hidden border-4 border-white shadow-lg relative">
                                    <div className="text-slate-900 font-bold text-sm sm:text-base">QR CODE</div>
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
                        <p className="text-slate-600 text-xs sm:text-sm max-w-2xl mx-auto mb-4 leading-relaxed px-4 sm:px-0">{content.footer.disclaimer}</p>
                        <p className="text-slate-700 text-xs sm:text-sm">{content.footer.copy}</p>
                    </div>
                </footer>
            </main>
        </div>
    );
}
