/**
 * 新首页（营销页） - New Landing Page
 * 核心目的：卖三大功能 + 引导购买 + 展示持仓业绩
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Menu, X, Sparkles, Zap, Crown } from 'lucide-react';
import axios from 'axios';
import FeedbackButton from '@/components/FeedbackButton';
import PrivacyPolicy from '@/components/PrivacyPolicy';
import { useUserData } from '@/components/auth/UserDataProvider';
import { translateStockName } from '@/lib/i18n';

// 复用 Landing 页面的样式
const styles = `
    :root {
        --brand-primary: #0D9B97;
        --brand-primary-rgb: 13, 155, 151;
        --brand-primary-light: #10B5B0;
        --brand-primary-dark: #0A7D7A;
        --bg-primary: #09090B;
        --bg-secondary: #18181B;
        --bg-tertiary: #27272A;
        --text-primary: #FAFAFA;
        --text-secondary: #A1A1AA;
        --text-muted: #71717A;
        --color-bull: #10B981;
        --color-bear: #EF4444;
    }

    body {
        font-family: 'Inter', 'Noto Sans SC', sans-serif;
        background-color: var(--bg-primary);
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
        margin: 0;
    }

    .gradient-text {
        background: linear-gradient(to right, var(--brand-primary), var(--brand-primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

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

    .beta-pulse {
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0% { box-shadow: 0 0 0 0 rgba(13, 155, 151, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(13, 155, 151, 0); }
        100% { box-shadow: 0 0 0 0 rgba(13, 155, 151, 0); }
    }

    .landing-nav {
        background: rgba(9, 9, 11, 0.8) !important;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(39, 39, 42, 0.8);
    }

    .btn-primary {
        background-color: var(--brand-primary) !important;
        color: white !important;
        box-shadow: 0 2px 4px rgba(13, 155, 151, 0.3);
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }

    .btn-primary:hover {
        background-color: var(--brand-primary-light) !important;
        box-shadow: 0 4px 8px rgba(13, 155, 151, 0.4);
    }

    .text-brand { color: var(--brand-primary) !important; }
    .bg-brand { background-color: var(--brand-primary) !important; }
    .border-brand { border-color: var(--brand-primary) !important; }
    .shadow-brand { box-shadow: 0 0 20px rgba(13, 155, 151, 0.3); }

    a { text-decoration: none; }

    .feature-card {
        background: rgba(24, 24, 27, 0.8);
        border: 1px solid rgba(39, 39, 42, 0.8);
        border-radius: 16px;
        padding: 32px;
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    .feature-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
        transform: translateY(-8px);
        box-shadow: 0 20px 40px -15px rgba(13, 155, 151, 0.3);
    }

    .feature-card.featured {
        border-color: rgba(13, 155, 151, 0.3);
        background: linear-gradient(135deg, rgba(13, 155, 151, 0.1) 0%, rgba(24, 24, 27, 0.8) 100%);
    }

    .pricing-card {
        background: rgba(24, 24, 27, 0.6);
        border: 1px solid rgba(39, 39, 42, 0.8);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .pricing-card.featured {
        border-color: var(--brand-primary);
        background: linear-gradient(135deg, rgba(13, 155, 151, 0.15) 0%, rgba(24, 24, 27, 0.8) 100%);
        transform: scale(1.05);
    }

    .pricing-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
    }

    .highlight-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        background: rgba(39, 39, 42, 0.8);
        border-radius: 20px;
        font-size: 13px;
        color: var(--text-secondary);
    }
`;

export default function NewLanding() {
    const { i18n, t } = useTranslation();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const isZh = i18n.language === 'zh';
    const { pricing } = useUserData();

    // Portfolio data
    const [portfolioData, setPortfolioData] = useState<any>(null);
    const [portfolioLoading, setPortfolioLoading] = useState(true);

    const toggleLang = () => {
        i18n.changeLanguage(isZh ? 'en' : 'zh');
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    // Fetch portfolio data
    useEffect(() => {
        const fetchPortfolio = async () => {
            try {
                const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002';
                const response = await axios.get(`${apiUrl}/portfolio/holdings`);
                if (response.data.success) {
                    setPortfolioData(response.data.data);
                }
            } catch (error) {
                console.error('Failed to fetch portfolio:', error);
            } finally {
                setPortfolioLoading(false);
            }
        };
        fetchPortfolio();
    }, []);

    // Navigation content (matching Landing.tsx)
    const navContent = {
        home: t('landing.nav.home'),
        portfolio: t('landing.nav.portfolio'),
        styles: t('landing.nav.styles'),
        contact: t('landing.nav.contact'),
        cta: t('landing.nav.cta'),
        lang: t('landing.nav.lang')
    };

    // 三大核心功能
    const features = [
        {
            icon: 'bi-broadcast',
            title: isZh ? '智能跟单' : 'Smart Copy Trading',
            subtitle: isZh ? '跟随投资大师，AI 发现叙事' : 'Follow the masters, AI discovers narratives',
            highlights: [
                isZh ? '巴菲特持仓' : 'Buffett Portfolio',
                isZh ? '木头姐 ARK' : 'Cathie Wood ARK',
                isZh ? 'AI 芯片主题' : 'AI Chips Theme',
                isZh ? '量子计算' : 'Quantum Computing',
            ],
            cta: isZh ? '开始跟单' : 'Start Following',
            link: '/stock?mode=narrative',
            featured: true,
        },
        {
            icon: 'bi-graph-up',
            title: isZh ? 'AI 深度分析' : 'AI Deep Analysis',
            subtitle: isZh ? '4种投资风格，100+维度报告' : '4 investment styles, 100+ dimension reports',
            highlights: [
                'Quality',
                'Value',
                'Growth',
                'Momentum',
            ],
            cta: isZh ? '开始分析' : 'Start Analysis',
            link: '/stock?mode=manual',
            featured: false,
        },
        {
            icon: 'bi-cash-stack',
            title: isZh ? '期权收入引擎' : 'Options Income Engine',
            subtitle: isZh ? '发现高收益期权，年化 30-120%' : 'High-yield options, 30-120% annualized',
            highlights: [
                'ZEBRA Strategy',
                'LEAPS Strategy',
                isZh ? '收入预览' : 'Income Preview',
                isZh ? '风险筛选' : 'Risk Filter',
            ],
            cta: isZh ? '发现期权' : 'Discover Options',
            link: '/options',
            featured: false,
        },
    ];

    // 价值主张
    const valueProps = [
        { icon: 'bi-globe', text: isZh ? '覆盖 US/HK/A 股' : 'US/HK/A-shares' },
        { icon: 'bi-robot', text: isZh ? 'AI 驱动分析' : 'AI-Powered' },
        { icon: 'bi-lightning-charge', text: isZh ? '实时期权数据' : 'Real-time Options' },
        { icon: 'bi-shield-check', text: isZh ? '专业级风控' : 'Pro Risk Control' },
        { icon: 'bi-translate', text: isZh ? '中英双语' : 'Bilingual' },
        { icon: 'bi-clock', text: '7×24' },
    ];

    // 定价套餐 - 从 API 获取或使用默认值
    const getPricingPlans = () => {
        if (pricing) {
            return [
                {
                    tier: 'Free',
                    icon: Sparkles,
                    iconColor: 'text-slate-400',
                    iconBg: 'bg-slate-800',
                    price: '$0',
                    period: '',
                    limit: isZh ? '5次/天' : '5/day',
                    cta: isZh ? '免费开始' : 'Start Free',
                    featured: false,
                    link: '/stock',
                },
                {
                    tier: 'Plus',
                    icon: Zap,
                    iconColor: 'text-[#0D9B97]',
                    iconBg: 'bg-[#0D9B97]/20',
                    price: `$${pricing.plans.plus.monthly.price}`,
                    period: isZh ? '/月' : '/mo',
                    limit: isZh ? '100次/天' : '100/day',
                    cta: isZh ? '升级 Plus' : 'Upgrade',
                    featured: true,
                    link: '/pricing',
                },
                {
                    tier: 'Pro',
                    icon: Crown,
                    iconColor: 'text-amber-500',
                    iconBg: 'bg-amber-500/20',
                    price: `$${pricing.plans.pro.monthly.price}`,
                    period: isZh ? '/月' : '/mo',
                    limit: isZh ? '无限' : 'Unlimited',
                    cta: isZh ? '升级 Pro' : 'Go Pro',
                    featured: false,
                    link: '/pricing',
                },
            ];
        }
        // 默认值
        return [
            {
                tier: 'Free',
                icon: Sparkles,
                iconColor: 'text-slate-400',
                iconBg: 'bg-slate-800',
                price: '$0',
                period: '',
                limit: isZh ? '5次/天' : '5/day',
                cta: isZh ? '免费开始' : 'Start Free',
                featured: false,
                link: '/stock',
            },
            {
                tier: 'Plus',
                icon: Zap,
                iconColor: 'text-[#0D9B97]',
                iconBg: 'bg-[#0D9B97]/20',
                price: '$9.9',
                period: isZh ? '/月' : '/mo',
                limit: isZh ? '100次/天' : '100/day',
                cta: isZh ? '升级 Plus' : 'Upgrade',
                featured: true,
                link: '/pricing',
            },
            {
                tier: 'Pro',
                icon: Crown,
                iconColor: 'text-amber-500',
                iconBg: 'bg-amber-500/20',
                price: '$29.9',
                period: isZh ? '/月' : '/mo',
                limit: isZh ? '无限' : 'Unlimited',
                cta: isZh ? '升级 Pro' : 'Go Pro',
                featured: false,
                link: '/pricing',
            },
        ];
    };

    const pricingPlans = getPricingPlans();

    // AlphaGBM 名称解释
    const gbmExplanation = {
        title: isZh ? '为什么叫 AlphaGBM?' : 'Why AlphaGBM?',
        items: [
            {
                letter: 'Alpha',
                meaning: isZh ? '超额收益' : 'Excess Returns',
                desc: isZh ? '追求超越市场的投资回报' : 'Seeking returns above market benchmarks'
            },
            {
                letter: 'G',
                meaning: 'Growth',
                desc: isZh ? '成长型投资策略' : 'Growth-oriented investment strategy'
            },
            {
                letter: 'B',
                meaning: 'Basics',
                desc: isZh ? '基本面分析驱动' : 'Fundamentals-driven analysis'
            },
            {
                letter: 'M',
                meaning: 'Momentum',
                desc: isZh ? '动量趋势跟踪' : 'Momentum trend following'
            }
        ]
    };

    return (
        <>
            <style>{styles}</style>

            {/* 导航栏 - 恢复原有样式 */}
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
                                <a href="#" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{navContent.home}</a>
                                <a href="#portfolio" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{navContent.portfolio}</a>
                                <a href="#features" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{navContent.styles}</a>
                                <a href="#pricing" className="hover:text-brand transition-colors text-sm text-[var(--text-secondary)]">{isZh ? '定价' : 'Pricing'}</a>
                            </div>

                            <div className="flex items-center gap-4">
                                <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                    {navContent.lang}
                                </button>
                                <Link to="/stock" className="btn-primary rounded-full px-4 py-2 text-sm font-semibold hover:bg-opacity-90 transition-colors shadow-brand">
                                    {navContent.cta}
                                </Link>
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
                                    {navContent.home}
                                </a>
                                <a href="#portfolio" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {navContent.portfolio}
                                </a>
                                <a href="#features" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {navContent.styles}
                                </a>
                                <a href="#pricing" className="block text-sm text-[var(--text-secondary)] hover:text-brand transition-colors py-2" onClick={closeMobileMenu}>
                                    {isZh ? '定价' : 'Pricing'}
                                </a>

                                <div className="border-t border-slate-700 pt-4 mt-4 space-y-4">
                                    <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                        {navContent.lang}
                                    </button>
                                    <Link to="/stock" className="btn-primary rounded-full px-4 py-2 text-sm font-semibold hover:bg-opacity-90 transition-colors shadow-brand block text-center" onClick={closeMobileMenu}>
                                        {navContent.cta}
                                    </Link>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-24 sm:pt-32 pb-12 px-4 sm:px-6 overflow-hidden">
                <div className="hero-glow"></div>
                <div className="max-w-4xl mx-auto text-center relative z-10">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-brand text-xs font-medium mb-4 sm:mb-6">
                        <i className="ph ph-sparkle-fill"></i>
                        Powered by LLM
                    </div>
                    <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4">
                        <span className="gradient-text">AlphaGBM</span>
                    </h1>
                    <p className="text-xl md:text-2xl text-[var(--text-secondary)] mb-3">
                        {isZh ? 'AI 驱动的智能投资平台' : 'AI-Powered Smart Investing Platform'}
                    </p>
                    <p className="text-base text-[var(--text-muted)] mb-8 max-w-2xl mx-auto">
                        {isZh
                            ? '让普通投资者也能用专业方法做投资'
                            : 'Professional investment methods for everyone'}
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link
                            to="/stock"
                            className="btn-primary beta-pulse rounded-full px-8 py-3 text-lg font-medium shadow-brand"
                        >
                            {isZh ? '免费试用' : 'Try Free'}
                        </Link>
                        <Link
                            to="/pricing"
                            className="px-8 py-3 text-lg font-medium border border-[var(--bg-tertiary)] rounded-full text-[var(--text-secondary)] hover:border-brand hover:text-brand transition-all"
                        >
                            {isZh ? '查看定价' : 'View Pricing'}
                        </Link>
                    </div>
                </div>
            </section>

            {/* AlphaGBM 名称解释 */}
            <section className="py-12 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-4xl mx-auto">
                    <h3 className="text-lg font-semibold text-center mb-6 text-[var(--text-secondary)]">
                        {gbmExplanation.title}
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {gbmExplanation.items.map((item, idx) => (
                            <div key={idx} className="text-center">
                                <div className="text-2xl font-bold text-brand mb-1">{item.letter}</div>
                                <div className="text-sm font-medium text-white mb-1">{item.meaning}</div>
                                <div className="text-xs text-[var(--text-muted)]">{item.desc}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Three Features Section */}
            <section id="features" className="py-16 sm:py-20 px-4 sm:px-6">
                <div className="max-w-6xl mx-auto">
                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-center mb-4">
                        {isZh ? '三大核心引擎' : 'Three Core Engines'}
                    </h2>
                    <p className="text-[var(--text-muted)] text-center mb-10 max-w-2xl mx-auto">
                        {isZh
                            ? '覆盖选股、分析、期权的完整投资工作流'
                            : 'Complete investment workflow: discovery, analysis, and options'}
                    </p>

                    <div className="grid md:grid-cols-3 gap-6">
                        {features.map((feature, idx) => (
                            <div
                                key={idx}
                                className={`feature-card ${feature.featured ? 'featured' : ''}`}
                            >
                                {feature.featured && (
                                    <span className="inline-block px-3 py-1 text-xs font-medium bg-brand/20 text-brand rounded-full mb-4 w-fit">
                                        {isZh ? '推荐' : 'Recommended'}
                                    </span>
                                )}
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-brand/10 flex items-center justify-center">
                                        <i className={`bi ${feature.icon} text-2xl text-brand`}></i>
                                    </div>
                                    <h3 className="text-xl font-bold">{feature.title}</h3>
                                </div>
                                <p className="text-[var(--text-secondary)] mb-6">{feature.subtitle}</p>
                                <div className="flex flex-wrap gap-2 mb-6 flex-grow">
                                    {feature.highlights.map((item, i) => (
                                        <span key={i} className="highlight-tag">
                                            <i className="bi bi-check-circle-fill text-brand text-xs"></i>
                                            {item}
                                        </span>
                                    ))}
                                </div>
                                <Link
                                    to={feature.link}
                                    className="btn-primary rounded-lg px-6 py-3 text-center font-medium w-full mt-auto"
                                >
                                    {feature.cta}
                                    <i className="bi bi-arrow-right ml-2"></i>
                                </Link>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Portfolio Performance Section - 简洁版 */}
            <section id="portfolio" className="py-16 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-6xl mx-auto">
                    <h2 className="text-2xl sm:text-3xl font-bold text-center mb-4">
                        {isZh ? '实盘组合表现' : 'Live Portfolio Performance'}
                    </h2>
                    <p className="text-[var(--text-muted)] text-center mb-8 max-w-2xl mx-auto">
                        {isZh
                            ? '四种投资风格，真实持仓，透明收益'
                            : 'Four investment styles, real holdings, transparent returns'}
                    </p>

                    {portfolioLoading ? (
                        <div className="glass-card rounded-xl p-6 animate-pulse">
                            <div className="h-20 bg-gray-700 rounded"></div>
                        </div>
                    ) : portfolioData?.style_stats ? (
                        <>
                            {/* Total Summary */}
                            <div className="glass-card rounded-xl p-4 sm:p-6 mb-6 border border-brand/30">
                                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                                    <div className="text-center sm:text-left">
                                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                            <i className="ph ph-wallet text-brand"></i>
                                            {isZh ? '投资组合总览' : 'Portfolio Summary'}
                                        </h3>
                                        <p className="text-xs text-[var(--text-secondary)] mt-1">
                                            {isZh ? '初始投资: $1,000,000' : 'Initial: $1,000,000'}
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap items-center justify-center sm:justify-end gap-6">
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {isZh ? '当前市值' : 'Market Value'}
                                            </div>
                                            <div className="text-xl font-bold text-white">
                                                ${(Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.market_value || 0), 0) / 1000).toFixed(0)}K
                                            </div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {isZh ? '累积收益' : 'Total Return'}
                                            </div>
                                            {(() => {
                                                const totalInvestment = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.investment || 0), 0);
                                                const totalMarketValue = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => sum + (s.market_value || 0), 0);
                                                const totalProfit = totalMarketValue - totalInvestment;
                                                const totalProfitPercent = totalInvestment > 0 ? (totalProfit / totalInvestment) * 100 : 0;
                                                const isPositive = totalProfit >= 0;
                                                return (
                                                    <div className={`text-xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {isPositive ? '+' : ''}{totalProfitPercent.toFixed(1)}%
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                        <div className="text-center">
                                            <div className="text-xs text-[var(--text-secondary)] mb-1">
                                                {isZh ? '今日变化' : "Today"}
                                            </div>
                                            {(() => {
                                                const todayChange = Object.values(portfolioData.style_stats).reduce((sum: number, s: any) => {
                                                    return sum + parseFloat(s.vsYesterdayPercent || '0');
                                                }, 0) / 4;
                                                const isPositive = todayChange >= 0;
                                                return (
                                                    <div className={`text-xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {isPositive ? '+' : ''}{todayChange.toFixed(2)}%
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Style Cards - Compact */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {[
                                    { key: 'quality', name: 'Quality', color: 'emerald' },
                                    { key: 'value', name: 'Value', color: 'blue' },
                                    { key: 'growth', name: 'Growth', color: 'purple' },
                                    { key: 'momentum', name: 'Momentum', color: 'orange' }
                                ].map((style) => {
                                    const stats = portfolioData.style_stats[style.key];
                                    if (!stats) return null;
                                    const isPositive = parseFloat(stats.profitLossPercent) >= 0;
                                    return (
                                        <div key={style.key} className="glass-card rounded-xl p-4 text-center">
                                            <div className={`text-${style.color}-400 font-semibold mb-2`}>{style.name}</div>
                                            <div className={`text-2xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {isPositive ? '+' : ''}{stats.profitLossPercent}%
                                            </div>
                                            <div className="text-xs text-[var(--text-muted)] mt-1">
                                                {isZh ? '今日' : 'Today'}: {parseFloat(stats.vsYesterdayPercent) >= 0 ? '+' : ''}{stats.vsYesterdayPercent}%
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Top Holdings Preview */}
                            <div className="mt-6 glass-card rounded-xl p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <h4 className="font-semibold text-white">{isZh ? '部分持仓' : 'Sample Holdings'}</h4>
                                    <Link to="/landing-old#portfolio" className="text-sm text-brand hover:underline">
                                        {isZh ? '查看全部' : 'View All'} →
                                    </Link>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    {Object.entries(portfolioData.holdings_by_style || {}).flatMap(([_style, holdings]: [string, any]) =>
                                        (holdings || []).slice(0, 1)
                                    ).slice(0, 4).map((holding: any, idx: number) => (
                                        <div key={idx} className="bg-slate-800/50 rounded-lg p-3">
                                            <div className="font-medium text-white text-sm truncate">
                                                {translateStockName(holding.ticker, t, holding.name)}
                                            </div>
                                            <div className="text-xs text-[var(--text-muted)]">{holding.ticker}</div>
                                            <div className={`text-sm font-semibold mt-1 ${((holding.current - holding.cost) / holding.cost * 100) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {((holding.current - holding.cost) / holding.cost * 100) >= 0 ? '+' : ''}
                                                {((holding.current - holding.cost) / holding.cost * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="text-center text-[var(--text-muted)]">
                            {isZh ? '暂无数据' : 'No data available'}
                        </div>
                    )}
                </div>
            </section>

            {/* Value Props Section */}
            <section className="py-12 px-4 sm:px-6">
                <div className="max-w-5xl mx-auto">
                    <div className="flex flex-wrap justify-center gap-6 md:gap-10">
                        {valueProps.map((prop, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-[var(--text-secondary)]">
                                <i className={`bi ${prop.icon} text-brand`}></i>
                                <span>{prop.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Pricing CTA Section */}
            <section id="pricing" className="py-16 sm:py-20 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-5xl mx-auto text-center">
                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4">
                        {isZh ? '开启你的智能投资之旅' : 'Start Your Smart Investing Journey'}
                    </h2>
                    <p className="text-[var(--text-muted)] mb-10">
                        {isZh ? '选择适合你的方案' : 'Choose the plan that fits you'}
                    </p>

                    <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                        {pricingPlans.map((plan, idx) => {
                            const IconComponent = plan.icon;
                            return (
                                <div key={idx} className={`pricing-card ${plan.featured ? 'featured' : ''}`}>
                                    {plan.featured && (
                                        <span className="inline-block px-3 py-1 text-xs font-medium bg-brand text-white rounded-full mb-3">
                                            {isZh ? '最受欢迎' : 'Most Popular'}
                                        </span>
                                    )}
                                    <div className={`w-10 h-10 rounded-xl ${plan.iconBg} flex items-center justify-center mx-auto mb-3`}>
                                        <IconComponent className={`w-5 h-5 ${plan.iconColor}`} />
                                    </div>
                                    <h3 className="text-xl font-bold mb-2">{plan.tier}</h3>
                                    <div className="mb-4">
                                        <span className="text-3xl font-bold">{plan.price}</span>
                                        <span className="text-[var(--text-muted)]">{plan.period}</span>
                                    </div>
                                    <p className="text-[var(--text-secondary)] mb-6">{plan.limit}</p>
                                    <Link
                                        to={plan.link}
                                        className={`block w-full py-3 rounded-lg font-medium transition-all ${
                                            plan.featured
                                                ? 'btn-primary'
                                                : 'border border-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:border-brand hover:text-brand'
                                        }`}
                                    >
                                        {plan.cta}
                                    </Link>
                                </div>
                            );
                        })}
                    </div>

                    <Link
                        to="/pricing"
                        className="inline-block mt-8 text-sm text-brand hover:underline"
                    >
                        {isZh ? '查看完整定价详情' : 'View full pricing details'} →
                    </Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 px-4 sm:px-6 border-t border-[var(--bg-tertiary)]">
                <div className="max-w-6xl mx-auto">
                    <div className="flex flex-col md:flex-row justify-between items-center gap-6">
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-xl">
                                Alpha<span style={{ color: '#0D9B97' }}>GBM</span>
                            </span>
                            <span className="text-[var(--text-muted)] text-sm">
                                © 2025
                            </span>
                        </div>
                        <div className="flex items-center gap-6">
                            <Link to="/stock" className="text-[var(--text-muted)] hover:text-brand text-sm">
                                {isZh ? '股票分析' : 'Stock'}
                            </Link>
                            <Link to="/options" className="text-[var(--text-muted)] hover:text-brand text-sm">
                                {isZh ? '期权' : 'Options'}
                            </Link>
                            <Link to="/pricing" className="text-[var(--text-muted)] hover:text-brand text-sm">
                                {isZh ? '定价' : 'Pricing'}
                            </Link>
                            <PrivacyPolicy />
                        </div>
                    </div>
                    <div className="mt-8 text-center text-[var(--text-muted)] text-xs">
                        {isZh
                            ? '免责声明：本平台仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。'
                            : 'Disclaimer: This platform is for educational and research purposes only. Not financial advice. Invest responsibly.'}
                    </div>
                </div>
            </footer>

            {/* Feedback Button */}
            <FeedbackButton />
        </>
    );
}
