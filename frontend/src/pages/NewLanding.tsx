/**
 * 新首页（期权优先版本）
 * 核心理念：收益 = 基本面 + 情绪
 * 主推期权功能，展示热门推荐
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Helmet } from 'react-helmet-async';
import { Menu, X, TrendingUp, Calculator, BarChart3, ArrowRight, Sparkles, Target, Shield, Zap } from 'lucide-react';
import FeedbackButton from '@/components/FeedbackButton';
import PrivacyPolicy from '@/components/PrivacyPolicy';
import HotRecommendations from '@/components/HotRecommendations';
// import SimulatedPortfolio from '@/components/SimulatedPortfolio'; // Hidden until we have data

// 样式
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

    .hero-glow {
        position: absolute;
        width: 800px;
        height: 800px;
        background: radial-gradient(circle, rgba(13, 155, 151, 0.12) 0%, rgba(9, 9, 11, 0) 70%);
        top: -200px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 0;
        pointer-events: none;
    }

    .landing-nav {
        background: rgba(9, 9, 11, 0.85) !important;
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
        transition: all 0.2s;
    }

    .btn-primary:hover {
        background-color: var(--brand-primary-light) !important;
        box-shadow: 0 4px 12px rgba(13, 155, 151, 0.4);
        transform: translateY(-1px);
    }

    .btn-secondary {
        background: transparent;
        border: 1px solid var(--bg-tertiary);
        color: var(--text-secondary);
        transition: all 0.2s;
    }

    .btn-secondary:hover {
        border-color: var(--brand-primary);
        color: var(--brand-primary);
    }

    .formula-box {
        background: linear-gradient(135deg, rgba(13, 155, 151, 0.15) 0%, rgba(24, 24, 27, 0.8) 100%);
        border: 1px solid rgba(13, 155, 151, 0.3);
        border-radius: 16px;
        padding: 24px 40px;
        display: inline-flex;
        align-items: center;
        gap: 16px;
    }

    .formula-text {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    .formula-highlight {
        color: var(--brand-primary);
    }

    .quick-action-card {
        background: rgba(24, 24, 27, 0.6);
        border: 1px solid rgba(39, 39, 42, 0.8);
        border-radius: 12px;
        padding: 20px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .quick-action-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
        transform: translateY(-3px);
        box-shadow: 0 10px 30px -10px rgba(13, 155, 151, 0.25);
    }

    .quick-action-card.featured {
        border-color: rgba(13, 155, 151, 0.4);
        background: linear-gradient(135deg, rgba(13, 155, 151, 0.1) 0%, rgba(24, 24, 27, 0.6) 100%);
    }

    .icon-box {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .icon-box.primary {
        background: rgba(13, 155, 151, 0.2);
        color: var(--brand-primary);
    }

    .icon-box.green {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }

    .icon-box.purple {
        background: rgba(139, 92, 246, 0.2);
        color: #8B5CF6;
    }

    .icon-box.orange {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
    }

    .philosophy-card {
        background: rgba(24, 24, 27, 0.8);
        border: 1px solid rgba(39, 39, 42, 0.8);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
    }

    .philosophy-icon {
        width: 64px;
        height: 64px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 16px;
    }

    .section-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .section-subtitle {
        color: var(--text-muted);
        margin-bottom: 2rem;
    }

    @media (max-width: 640px) {
        .formula-box {
            padding: 16px 24px;
            flex-direction: column;
            gap: 8px;
        }

        .formula-text {
            font-size: 1.25rem;
        }

        .section-title {
            font-size: 1.5rem;
        }
    }
`;

export default function NewLanding() {
    const { i18n } = useTranslation();
    const navigate = useNavigate();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const isZh = i18n.language.startsWith('zh');

    const toggleLang = () => {
        i18n.changeLanguage(isZh ? 'en' : 'zh');
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    // 快速入口配置（3个主要入口）
    const quickActions = [
        {
            icon: TrendingUp,
            iconClass: 'primary',
            title: isZh ? '期权研究' : 'Options Research',
            desc: isZh ? '智能期权链分析与推荐' : 'Smart options chain analysis',
            link: '/options',
            featured: true,
        },
        {
            icon: Calculator,
            iconClass: 'green',
            title: isZh ? '反向查分' : 'Reverse Score',
            desc: isZh ? '输入期权参数获取评分' : 'Get score for any option',
            link: '/options/reverse',
            featured: false,
        },
        {
            icon: BarChart3,
            iconClass: 'purple',
            title: isZh ? '股票分析' : 'Stock Analysis',
            desc: isZh ? '基本面 + 情绪深度分析' : 'Fundamentals + Sentiment',
            link: '/stock',
            featured: false,
        },
    ];

    // 理念说明
    const philosophyItems = [
        {
            icon: Target,
            color: 'rgba(16, 185, 129, 0.2)',
            iconColor: '#10B981',
            title: isZh ? '基本面' : 'Fundamentals',
            desc: isZh
                ? '公司财务健康、盈利能力、估值水平、行业地位'
                : 'Financial health, profitability, valuation, industry position',
        },
        {
            icon: Zap,
            color: 'rgba(245, 158, 11, 0.2)',
            iconColor: '#F59E0B',
            title: isZh ? '情绪' : 'Sentiment',
            desc: isZh
                ? '市场趋势、技术指标、资金流向、投资者情绪'
                : 'Market trend, technicals, fund flows, investor mood',
        },
        {
            icon: Shield,
            color: 'rgba(139, 92, 246, 0.2)',
            iconColor: '#8B5CF6',
            title: isZh ? '风险控制' : 'Risk Control',
            desc: isZh
                ? 'ATR安全边际、支撑阻力位、趋势匹配度'
                : 'ATR safety margin, support/resistance, trend alignment',
        },
    ];

    // 期权优势
    const optionBenefits = [
        {
            title: isZh ? '高收益潜力' : 'High Yield Potential',
            desc: isZh ? '年化收益可达 30-120%' : 'Up to 30-120% annualized',
        },
        {
            title: isZh ? '风险可控' : 'Controlled Risk',
            desc: isZh ? '明确的最大损失边界' : 'Clear max loss boundaries',
        },
        {
            title: isZh ? '策略多样' : 'Diverse Strategies',
            desc: isZh ? '看涨看跌，买入卖出' : 'Bull/bear, buy/sell options',
        },
        {
            title: isZh ? 'AI 智能评分' : 'AI Smart Scoring',
            desc: isZh ? '多维度综合评估' : 'Multi-dimensional analysis',
        },
    ];

    return (
        <>
            <Helmet>
                <title>{isZh ? 'AlphaGBM - 智能期权分析平台 | AI驱动的股票期权研究工具' : 'AlphaGBM - AI Options Analysis Platform | Smart Options Research Tool'}</title>
                <meta name="description" content={isZh
                    ? 'AlphaGBM 是一款 AI 驱动的智能期权分析平台，提供实时期权评分、策略推荐、风险分析。支持美股期权研究，帮助投资者做出更明智的交易决策。'
                    : 'AlphaGBM is an AI-powered options analysis platform offering real-time scoring, strategy recommendations, and risk analysis for US stock options trading.'}
                />
                <link rel="canonical" href="https://alphagbm.com/" />
                <meta property="og:url" content="https://alphagbm.com/" />
                <meta property="og:title" content={isZh ? 'AlphaGBM - 智能期权分析平台' : 'AlphaGBM - AI Options Analysis Platform'} />
            </Helmet>
            <style>{styles}</style>

            {/* 导航栏 */}
            <nav className="fixed w-full z-50 landing-nav">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <div className="flex items-center gap-2">
                            <img src="/logo.png" alt="AlphaGBM" className="h-8 w-8" />
                            <span className="font-bold text-xl tracking-tight">
                                Alpha<span style={{ color: '#0D9B97' }}>GBM</span>
                            </span>
                        </div>

                        {/* Desktop Navigation */}
                        <div className="hidden md:flex items-center gap-8">
                            <div className="flex items-baseline space-x-6">
                                <Link to="/options" className="hover:text-[#0D9B97] transition-colors text-sm text-[var(--text-secondary)]">
                                    {isZh ? '期权研究' : 'Options'}
                                </Link>
                                <Link to="/options/reverse" className="hover:text-[#0D9B97] transition-colors text-sm text-[var(--text-secondary)]">
                                    {isZh ? '反向查分' : 'Reverse Score'}
                                </Link>
                                <Link to="/stock" className="hover:text-[#0D9B97] transition-colors text-sm text-[var(--text-secondary)]">
                                    {isZh ? '股票分析' : 'Stock'}
                                </Link>
                                <Link to="/pricing" className="hover:text-[#0D9B97] transition-colors text-sm text-[var(--text-secondary)]">
                                    {isZh ? '定价' : 'Pricing'}
                                </Link>
                            </div>

                            <div className="flex items-center gap-4">
                                <button
                                    onClick={toggleLang}
                                    className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors"
                                >
                                    {isZh ? 'EN' : '中文'}
                                </button>
                                <Link
                                    to="/options"
                                    className="btn-primary rounded-full px-4 py-2 text-sm font-semibold"
                                >
                                    {isZh ? '开始分析' : 'Start Analysis'}
                                </Link>
                            </div>
                        </div>

                        {/* Mobile Menu Button */}
                        <button
                            className="md:hidden p-2 text-[var(--text-secondary)] hover:text-[#0D9B97] transition-colors"
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
                                <Link to="/options" className="block text-sm text-[var(--text-secondary)] hover:text-[#0D9B97] py-2" onClick={closeMobileMenu}>
                                    {isZh ? '期权研究' : 'Options'}
                                </Link>
                                <Link to="/options/reverse" className="block text-sm text-[var(--text-secondary)] hover:text-[#0D9B97] py-2" onClick={closeMobileMenu}>
                                    {isZh ? '反向查分' : 'Reverse Score'}
                                </Link>
                                <Link to="/stock" className="block text-sm text-[var(--text-secondary)] hover:text-[#0D9B97] py-2" onClick={closeMobileMenu}>
                                    {isZh ? '股票分析' : 'Stock'}
                                </Link>
                                <Link to="/pricing" className="block text-sm text-[var(--text-secondary)] hover:text-[#0D9B97] py-2" onClick={closeMobileMenu}>
                                    {isZh ? '定价' : 'Pricing'}
                                </Link>
                                <div className="border-t border-slate-700 pt-4 mt-4 space-y-4">
                                    <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded">
                                        {isZh ? 'EN' : '中文'}
                                    </button>
                                    <Link to="/options" className="btn-primary rounded-full px-4 py-2 text-sm font-semibold block text-center" onClick={closeMobileMenu}>
                                        {isZh ? '开始分析' : 'Start Analysis'}
                                    </Link>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-28 sm:pt-36 pb-12 px-4 sm:px-6 overflow-hidden">
                <div className="hero-glow"></div>
                <div className="max-w-4xl mx-auto text-center relative z-10">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700 text-[#0D9B97] text-xs font-medium mb-6">
                        <Sparkles size={14} />
                        {isZh ? 'AI 驱动的智能期权分析' : 'AI-Powered Options Analysis'}
                    </div>

                    {/* Title */}
                    <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-6">
                        <span className="gradient-text">AlphaGBM</span>
                    </h1>

                    {/* Core Formula */}
                    <div className="formula-box mb-8">
                        <span className="formula-text">
                            <span className="formula-highlight">{isZh ? '收益' : 'Return'}</span>
                            {' = '}
                            <span>{isZh ? '基本面' : 'Fundamentals'}</span>
                            {' + '}
                            <span>{isZh ? '情绪' : 'Sentiment'}</span>
                        </span>
                    </div>

                    {/* Subtitle */}
                    <p className="text-lg text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
                        {isZh
                            ? '基于我们的核心算法，为你发现最优期权交易机会。无论是稳健收益还是高风险高回报，都能找到匹配的策略。'
                            : 'Based on our core algorithm, we find the best options trading opportunities for you. Whether steady income or high risk/reward, we have matching strategies.'}
                    </p>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link
                            to="/options"
                            className="btn-primary rounded-full px-8 py-3 text-lg font-medium gap-2"
                        >
                            {isZh ? '开始分析期权' : 'Start Options Analysis'}
                            <ArrowRight size={18} />
                        </Link>
                        <Link
                            to="/options/reverse"
                            className="btn-secondary rounded-full px-8 py-3 text-lg font-medium"
                        >
                            {isZh ? '反向查分' : 'Reverse Score'}
                        </Link>
                    </div>
                </div>
            </section>

            {/* Hot Recommendations Section */}
            <section className="py-12 sm:py-16 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-7xl mx-auto">
                    <HotRecommendations maxItems={5} showMarketSummary={true} />
                </div>
            </section>

            {/* Quick Actions Section */}
            <section className="py-12 sm:py-16 px-4 sm:px-6">
                <div className="max-w-5xl mx-auto">
                    <h2 className="section-title text-center">
                        {isZh ? '快速开始' : 'Quick Start'}
                    </h2>
                    <p className="section-subtitle text-center">
                        {isZh ? '选择你想要的分析方式' : 'Choose your analysis method'}
                    </p>

                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {quickActions.map((action, idx) => {
                            const IconComponent = action.icon;
                            return (
                                <div
                                    key={idx}
                                    className={`quick-action-card ${action.featured ? 'featured' : ''}`}
                                    onClick={() => navigate(action.link)}
                                >
                                    <div className={`icon-box ${action.iconClass}`}>
                                        <IconComponent size={24} />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white mb-1">{action.title}</h3>
                                        <p className="text-sm text-[var(--text-muted)]">{action.desc}</p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Simulated Portfolio Section - Hidden until we have data */}
            {/* <section className="py-12 sm:py-16 px-4 sm:px-6">
                <div className="max-w-5xl mx-auto">
                    <SimulatedPortfolio />
                    <div className="text-center mt-6 text-xs text-[var(--text-muted)]">
                        {isZh
                            ? '* 以上为算法推荐的模拟交易，过往表现不代表未来收益。投资有风险，入市需谨慎。'
                            : '* Simulated trades based on algorithm recommendations. Past performance does not guarantee future results.'}
                    </div>
                </div>
            </section> */}

            {/* Philosophy Section */}
            <section className="py-12 sm:py-16 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-5xl mx-auto">
                    <h2 className="section-title text-center">
                        {isZh ? '我们的分析理念' : 'Our Analysis Philosophy'}
                    </h2>
                    <p className="section-subtitle text-center">
                        {isZh ? '收益来自多个维度的综合评估，基于自研算法和数据库，实时动态分析' : 'Multi-dimensional analysis based on proprietary algorithms and real-time data'}
                    </p>

                    <div className="grid md:grid-cols-3 gap-6">
                        {philosophyItems.map((item, idx) => {
                            const IconComponent = item.icon;
                            return (
                                <div key={idx} className="philosophy-card">
                                    <div
                                        className="philosophy-icon"
                                        style={{ backgroundColor: item.color }}
                                    >
                                        <IconComponent size={32} color={item.iconColor} />
                                    </div>
                                    <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                                    <p className="text-[var(--text-secondary)]">{item.desc}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Why Options Section */}
            <section className="py-12 sm:py-16 px-4 sm:px-6">
                <div className="max-w-5xl mx-auto">
                    <h2 className="section-title text-center">
                        {isZh ? '为什么选择期权?' : 'Why Options?'}
                    </h2>
                    <p className="section-subtitle text-center">
                        {isZh ? '期权交易的独特优势' : 'Unique advantages of options trading'}
                    </p>

                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {optionBenefits.map((benefit, idx) => (
                            <div
                                key={idx}
                                className="text-center p-6 bg-slate-800/30 rounded-xl border border-slate-700/50"
                            >
                                <h3 className="font-semibold text-white mb-2">{benefit.title}</h3>
                                <p className="text-sm text-[var(--text-muted)]">{benefit.desc}</p>
                            </div>
                        ))}
                    </div>

                    <div className="text-center mt-10">
                        <Link
                            to="/options"
                            className="btn-primary rounded-full px-8 py-3 text-lg font-medium gap-2 inline-flex"
                        >
                            {isZh ? '立即体验' : 'Try Now'}
                            <ArrowRight size={18} />
                        </Link>
                    </div>
                </div>
            </section>

            {/* Trust Signals */}
            <section className="py-12 sm:py-16 px-4 sm:px-6 bg-[var(--bg-secondary)]">
                <div className="max-w-5xl mx-auto">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                        <div>
                            <div className="text-3xl font-bold font-mono text-[#0D9B97]">50,000+</div>
                            <div className="text-sm text-[var(--text-muted)] mt-1">
                                {isZh ? '累计分析次数' : 'Total Analyses'}
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold font-mono text-[#10B981]">72%</div>
                            <div className="text-sm text-[var(--text-muted)] mt-1">
                                {isZh ? '用户胜率提升' : 'Win Rate Improvement'}
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold font-mono text-[#0D9B97]">4.8/5</div>
                            <div className="text-sm text-[var(--text-muted)] mt-1">
                                {isZh ? '用户满意度' : 'User Satisfaction'}
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-bold font-mono text-[#0D9B97]">3</div>
                            <div className="text-sm text-[var(--text-muted)] mt-1">
                                {isZh ? '支持市场 (US/HK/CN)' : 'Markets Supported'}
                            </div>
                        </div>
                    </div>
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
                            <Link to="/options" className="text-[var(--text-muted)] hover:text-[#0D9B97] text-sm">
                                {isZh ? '期权研究' : 'Options'}
                            </Link>
                            <Link to="/options/reverse" className="text-[var(--text-muted)] hover:text-[#0D9B97] text-sm">
                                {isZh ? '反向查分' : 'Reverse Score'}
                            </Link>
                            <Link to="/stock" className="text-[var(--text-muted)] hover:text-[#0D9B97] text-sm">
                                {isZh ? '股票分析' : 'Stock'}
                            </Link>
                            <Link to="/pricing" className="text-[var(--text-muted)] hover:text-[#0D9B97] text-sm">
                                {isZh ? '定价' : 'Pricing'}
                            </Link>
                            <PrivacyPolicy />
                        </div>
                    </div>
                    <div className="mt-6 text-center text-[var(--text-muted)] text-xs">
                        FLAT 1503 15/F CARNIVAL COMMERCIAL BUILDING 18 JAVA ROAD NORTH POINT HK
                    </div>
                    <div className="mt-4 text-center text-[var(--text-muted)] text-xs">
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
