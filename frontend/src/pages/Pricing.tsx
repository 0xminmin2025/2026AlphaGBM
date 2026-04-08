import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Check, Loader2, Sparkles, Zap, Crown, Bot } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18n from '@/lib/i18n';
import { useToastHelpers } from '@/components/ui/toast';

// Modern pricing page styles
const styles = `
    .pricing-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 1.5rem;
        padding: 1.5rem;
        position: relative;
        transition: all 0.3s ease;
    }

    @media (min-width: 640px) {
        .pricing-card {
            padding: 2rem;
        }
    }
    
    .pricing-card:hover {
        transform: translateY(-4px);
        border-color: rgba(13, 155, 151, 0.5);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3), 0 0 40px rgba(13, 155, 151, 0.1);
    }
    
    .pricing-card.featured {
        background: linear-gradient(145deg, rgba(13, 155, 151, 0.15) 0%, rgba(13, 155, 151, 0.05) 100%);
        border-color: rgba(13, 155, 151, 0.5);
    }
    
    .pricing-card.current {
        border: 2px solid #0D9B97;
    }
    
    .featured-badge {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #0D9B97 0%, #0a7a77 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 2rem;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 15px rgba(13, 155, 151, 0.4);
    }
    
    .current-badge {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 2rem;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .price-tag {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FAFAFA 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .feature-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0;
        color: #94a3b8;
        font-size: 0.95rem;
    }
    
    .feature-icon {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: rgba(16, 185, 129, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    
    .subscribe-btn {
        width: 100%;
        padding: 1rem;
        border-radius: 0.75rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .subscribe-btn.primary {
        background: linear-gradient(135deg, #0D9B97 0%, #0a7a77 100%);
        color: white;
        border: none;
    }
    
    .subscribe-btn.primary:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(13, 155, 151, 0.4);
    }
    
    .subscribe-btn.outline {
        background: transparent;
        color: #94a3b8;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .subscribe-btn.outline:hover {
        border-color: #0D9B97;
        color: #0D9B97;
    }
    
    .subscribe-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
    }
    
    .topup-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 1rem;
        padding: 1.25rem 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.3s ease;
    }

    @media (min-width: 640px) {
        .topup-card {
            padding: 1.5rem 2rem;
        }
    }
    
    .topup-card:hover {
        border-color: rgba(13, 155, 151, 0.5);
    }
    
    .success-banner {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(16, 185, 129, 0.1) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 1rem;
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2rem;
    }
`;


export default function Pricing() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const toast = useToastHelpers();
    const { t } = useTranslation();
    const { pricing, credits, pricingLoading, creditsLoading, refreshCredits } = useUserData();
    const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
    const [currentPlan, setCurrentPlan] = useState<string>('free');
    const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');

    // Helper function to translate plan name
    const translatePlanName = (planKey: string, backendName: string): string => {
        // Map backend plan names to translation keys
        const planNameMap: Record<string, string> = {
            '免费版': 'pricing.free.name',
            'Plus会员': 'pricing.plus.name',
            'Pro会员': 'pricing.pro.name',
            '企业客户': 'pricing.enterprise.name',
        };
        
        // Check if the backend name is in the map
        if (planNameMap[backendName]) {
            return t(planNameMap[backendName]);
        }
        
        // Fallback to translation key based on planKey
        const fallbackKeys: Record<string, string> = {
            'free': 'pricing.free.name',
            'plus': 'pricing.plus.name',
            'pro': 'pricing.pro.name',
            'enterprise': 'pricing.enterprise.name',
        };
        
        if (fallbackKeys[planKey]) {
            return t(fallbackKeys[planKey]);
        }
        
        // If no mapping found, return original
        return backendName;
    };

    // Helper function to translate feature text
    const translateFeature = (feature: string): string => {
        // Map backend feature text to translation keys
        const featureMap: Record<string, string> = {
            '每日2次': 'pricing.feature.daily2',
            '标的研究': 'pricing.feature.stockAnalysis',
            '行业报告': 'pricing.feature.industryReport',
            '1000次查询/月': 'pricing.feature.queries1000',
            '期权分析': 'pricing.feature.optionsAnalysis',
            '5000次查询/月': 'pricing.feature.queries5000',
            '智能体服务': 'pricing.feature.agentService',
            '投资回顾': 'pricing.feature.investmentReview',
            'API接入': 'pricing.feature.apiAccess',
            '定制化服务': 'pricing.feature.customService',
            '联系客服咨询': 'pricing.feature.contactSupport',
            '额度加油包（100次）': 'pricing.topup.name',
            // 新增期权优先版本的功能
            '每日2次期权分析': 'pricing.feature.dailyOptionsAnalysis',
            '热门推荐': 'pricing.feature.hotRecommendations',
            '标的研究摘要': 'pricing.feature.stockSummary',
            '期权智能评分': 'pricing.feature.optionsSmartScore',
            '反向查分': 'pricing.feature.reverseScore',
            '标的深度研究': 'pricing.feature.stockDeepAnalysis',
            '趋势分析': 'pricing.feature.trendAnalysis',
            'AI策略报告': 'pricing.feature.aiStrategyReport',
            'VIP客服支持': 'pricing.feature.vipSupport',
            '批量期权分析': 'pricing.feature.batchOptionsAnalysis',
            '定制化策略': 'pricing.feature.customStrategy',
            '专属客服': 'pricing.feature.dedicatedSupport',
        };
        const translationKey = featureMap[feature];
        if (translationKey) {
            return t(translationKey);
        }
        // If no mapping found, return original (might already be in target language)
        return feature;
    };

    // Helper function to get currency symbol and convert price
    const getCurrencyAndPrice = (price: number, currency: string = 'cny'): { symbol: string, price: string } => {
        const isEnglish = i18n.language === 'en';
        if (isEnglish && currency === 'cny') {
            return { symbol: t('pricing.currencyUSD'), price: (price / 7).toFixed(2) };
        }
        return { symbol: currency === 'cny' ? t('pricing.currencyCNY') : t('pricing.currencyUSD'), price: Number(price).toFixed(2) };
    };

    const success = searchParams.get('success');
    const sessionId = searchParams.get('session_id');

    // 支付成功回调：主动验证 session 同步订阅（防止 webhook 丢失）
    const verifiedRef = useRef(false);
    useEffect(() => {
        if (success && sessionId && !verifiedRef.current) {
            verifiedRef.current = true;
            api.post('/payment/verify-session', { session_id: sessionId })
                .then(() => refreshCredits?.())
                .catch((err: any) => console.warn('Verify session failed:', err));
        }
    }, [success, sessionId]);

    // Update current plan based on credits data
    useEffect(() => {
        if (credits?.subscription) {
            if (credits.subscription.has_subscription) {
                setCurrentPlan(credits.subscription.plan_tier);
            } else {
                setCurrentPlan('free');
            }
        } else if (!creditsLoading && user) {
            // Only set to free if we're not loading and user exists but no credits data
            setCurrentPlan('free');
        }
    }, [credits, creditsLoading, user]);

    const handleSubscribe = async (priceKey: string) => {
        if (!user) {
            navigate('/login');
            return;
        }

        setCheckoutLoading(priceKey);
        try {
            // 已有订阅 → 走升级流程，否则走新建 checkout
            if (credits?.subscription?.has_subscription) {
                const response = await api.post('/payment/upgrade', { price_key: priceKey });
                if (response.data.success) {
                    toast.success(
                        i18n.language === 'zh' ? '升级成功' : 'Upgrade Successful',
                        i18n.language === 'zh'
                            ? `已升级至 ${response.data.new_plan.toUpperCase()}，获得 ${response.data.credits_added} 额度`
                            : `Upgraded to ${response.data.new_plan.toUpperCase()} with ${response.data.credits_added} credits`
                    );
                    window.location.reload();
                }
            } else {
                const response = await api.post('/payment/create-checkout-session', {
                    price_key: priceKey,
                    success_url: window.location.origin + '/pricing?success=true&session_id={CHECKOUT_SESSION_ID}',
                    cancel_url: window.location.origin + '/pricing?canceled=true'
                });
                window.location.href = response.data.checkout_url;
            }
        } catch (err: any) {
            console.error(err);
            const errorMsg = err.response?.data?.error || t('pricing.checkoutFailed');
            toast.error(t('pricing.checkoutFailed'), errorMsg);
            setCheckoutLoading(null);
        }
    };

    if (pricingLoading || !pricing) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <Loader2 className="w-8 h-8 animate-spin text-[#0D9B97]" />
            </div>
        );
    }

    return (
        <div className="animate-in fade-in">
            <style>{styles}</style>

            {/* Header */}
            <div className="text-center mb-8 sm:mb-16 px-4">
                <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-4">
                    {t('pricing.title')}
                </h1>
                <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto">
                    {t('pricing.subtitle')}
                </p>
            </div>

            {/* Billing Cycle Toggle */}
            <div className="flex items-center justify-center gap-3 mb-8 sm:mb-12">
                <span className={`text-sm font-medium transition-colors ${billingCycle === 'monthly' ? 'text-white' : 'text-slate-500'}`}>
                    {i18n.language === 'zh' ? '月付' : 'Monthly'}
                </span>
                <button
                    onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
                    className={`relative w-14 h-7 rounded-full transition-colors ${billingCycle === 'yearly' ? 'bg-[#0D9B97]' : 'bg-slate-700'}`}
                >
                    <div className={`absolute top-0.5 w-6 h-6 rounded-full bg-white shadow transition-transform ${billingCycle === 'yearly' ? 'translate-x-7' : 'translate-x-0.5'}`} />
                </button>
                <span className={`text-sm font-medium transition-colors ${billingCycle === 'yearly' ? 'text-white' : 'text-slate-500'}`}>
                    {i18n.language === 'zh' ? '年付' : 'Yearly'}
                </span>
                {billingCycle === 'yearly' && (
                    <span className="text-xs font-semibold text-green-400 bg-green-500/10 border border-green-500/30 px-2 py-0.5 rounded-full">
                        {i18n.language === 'zh' ? '省17%' : 'Save 17%'}
                    </span>
                )}
            </div>

            {/* Success Message */}
            {success && (
                <div className="success-banner max-w-4xl mx-4 sm:mx-auto">
                    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Check className="w-5 h-5 text-green-500" />
                    </div>
                    <div>
                        <div className="font-semibold text-green-400">{t('pricing.subscriptionSuccess')}</div>
                        <div className="text-sm text-slate-400">{t('pricing.subscriptionSuccessDesc')}</div>
                    </div>
                </div>
            )}

            {/* Pricing Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 md:gap-8 max-w-7xl mx-4 sm:mx-auto mb-8 sm:mb-16">
                {/* Free Plan */}
                <div className={`pricing-card flex flex-col ${currentPlan === 'free' ? 'current' : ''}`}>
                    {currentPlan === 'free' && <div className="current-badge">{t('pricing.currentPlan')}</div>}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                            <Sparkles className="w-6 h-6 text-slate-400" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{translatePlanName('free', pricing.plans.free.name)}</h3>
                            <p className="text-sm text-slate-500">{t('pricing.free.desc')}</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        <span className="price-tag">{getCurrencyAndPrice(0).symbol}0</span>
                        <span className="text-slate-500 ml-2">{t('pricing.permanentFree')}</span>
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.free.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{translateFeature(f)}</span>
                            </div>
                        ))}
                    </div>

                    <button className="subscribe-btn outline mt-auto" disabled>
                        {currentPlan === 'free' ? t('pricing.currentPlan') : t('pricing.free.name')}
                    </button>
                </div>

                {/* Plus Plan - Featured */}
                <div className={`pricing-card featured flex flex-col ${currentPlan === 'plus' ? 'current' : ''}`}>
                    {currentPlan === 'plus' ? (
                        <div className="current-badge">{t('pricing.currentPlan')}</div>
                    ) : (
                        <div className="featured-badge">{t('pricing.mostPopular')}</div>
                    )}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-[#0D9B97]/20 flex items-center justify-center">
                            <Zap className="w-6 h-6 text-[#0D9B97]" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{translatePlanName('plus', pricing.plans.plus.name)}</h3>
                            <p className="text-sm text-slate-500">{t('pricing.plus.desc')}</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        {(() => {
                            const plan = billingCycle === 'yearly' && pricing.plans.plus.yearly
                                ? pricing.plans.plus.yearly
                                : pricing.plans.plus.monthly;
                            const display = getCurrencyAndPrice(
                                billingCycle === 'yearly' ? plan.price / 12 : plan.price,
                                plan.currency
                            );
                            return (
                                <div>
                                    <div className="flex items-baseline gap-2">
                                        <span className="price-tag">{display.symbol}{display.price}</span>
                                        <span className="text-slate-500">{t('pricing.perMonth')}</span>
                                    </div>
                                    {billingCycle === 'yearly' && (
                                        <div className="text-sm text-slate-400 mt-1">
                                            {(() => {
                                                const yearly = getCurrencyAndPrice(plan.price, plan.currency);
                                                return <span>{i18n.language === 'zh' ? `按年付 ${yearly.symbol}${yearly.price}/年` : `Billed ${yearly.symbol}${yearly.price}/year`}</span>;
                                            })()}
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.plus.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{translateFeature(f)}</span>
                            </div>
                        ))}
                    </div>

                    {currentPlan === 'plus' ? (
                        <button className="subscribe-btn outline mt-auto" disabled>{t('pricing.currentPlan')}</button>
                    ) : (
                        <Button
                            className="subscribe-btn primary mt-auto"
                            onClick={() => handleSubscribe(billingCycle === 'yearly' ? 'plus_yearly' : 'plus_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {(checkoutLoading === 'plus_monthly' || checkoutLoading === 'plus_yearly') && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {t('pricing.subscribe')}
                        </Button>
                    )}
                </div>

                {/* Pro Plan */}
                <div className={`pricing-card flex flex-col ${currentPlan === 'pro' ? 'current' : ''}`}>
                    {currentPlan === 'pro' && <div className="current-badge">{t('pricing.currentPlan')}</div>}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                            <Crown className="w-6 h-6 text-amber-500" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{translatePlanName('pro', pricing.plans.pro.name)}</h3>
                            <p className="text-sm text-slate-500">{t('pricing.pro.desc')}</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        {(() => {
                            const plan = billingCycle === 'yearly' && pricing.plans.pro.yearly
                                ? pricing.plans.pro.yearly
                                : pricing.plans.pro.monthly;
                            const display = getCurrencyAndPrice(
                                billingCycle === 'yearly' ? plan.price / 12 : plan.price,
                                plan.currency
                            );
                            return (
                                <div>
                                    <div className="flex items-baseline gap-2">
                                        <span className="price-tag">{display.symbol}{display.price}</span>
                                        <span className="text-slate-500">{t('pricing.perMonth')}</span>
                                    </div>
                                    {billingCycle === 'yearly' && (
                                        <div className="text-sm text-slate-400 mt-1">
                                            {(() => {
                                                const yearly = getCurrencyAndPrice(plan.price, plan.currency);
                                                return <span>{i18n.language === 'zh' ? `按年付 ${yearly.symbol}${yearly.price}/年` : `Billed ${yearly.symbol}${yearly.price}/year`}</span>;
                                            })()}
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.pro.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{translateFeature(f)}</span>
                            </div>
                        ))}
                    </div>

                    {currentPlan === 'pro' ? (
                        <button className="subscribe-btn outline mt-auto" disabled>{t('pricing.currentPlan')}</button>
                    ) : (
                        <Button
                            className="subscribe-btn primary mt-auto"
                            onClick={() => handleSubscribe(billingCycle === 'yearly' ? 'pro_yearly' : 'pro_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {(checkoutLoading === 'pro_monthly' || checkoutLoading === 'pro_yearly') && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {t('pricing.subscribe')}
                        </Button>
                    )}
                </div>

                {/* API & AI Agent Plan */}
                <div className="pricing-card flex flex-col">
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                            <Bot className="w-6 h-6 text-purple-500" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">API & AI Agent</h3>
                            <p className="text-sm text-slate-500">
                                {i18n.language === 'zh' ? '在你的AI助手中使用AlphaGBM' : 'Use AlphaGBM in your AI assistant'}
                            </p>
                        </div>
                    </div>

                    <div className="mb-6">
                        <span className="text-2xl font-bold text-slate-300">
                            {i18n.language === 'zh' ? '与套餐共享额度' : 'Shared Quota'}
                        </span>
                        <span className="text-slate-500 ml-2 text-sm">
                            {i18n.language === 'zh' ? '不额外收费' : 'No extra cost'}
                        </span>
                    </div>

                    <div className="space-y-1 mb-8">
                        {[
                            i18n.language === 'zh' ? 'RESTful API 接入' : 'RESTful API Access',
                            i18n.language === 'zh' ? '支持 OpenClaw / Claude Desktop / Cursor' : 'OpenClaw / Claude Desktop / Cursor',
                            i18n.language === 'zh' ? '股票分析 + 期权分析全部能力' : 'Full Stock & Options Analysis',
                            i18n.language === 'zh' ? 'API Key 管理（最多5个）' : 'API Key Management (up to 5)',
                            i18n.language === 'zh' ? '调用统计与监控' : 'Usage Stats & Monitoring',
                            i18n.language === 'zh' ? '开发者文档' : 'Developer Docs',
                        ].map((f) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{f}</span>
                            </div>
                        ))}
                    </div>

                    <Button
                        className="subscribe-btn outline mt-auto"
                        onClick={() => {
                            if (!user) { navigate('/login'); return; }
                            navigate('/api-keys');
                        }}
                    >
                        {i18n.language === 'zh' ? '获取 API Key →' : 'Get API Key →'}
                    </Button>

                    <p className="text-xs text-slate-600 mt-4 leading-relaxed">
                        {i18n.language === 'zh'
                            ? 'API调用与网站共享同一额度。免费用户每日2次股票+1次期权分析，升级Plus/Pro获取更多额度。'
                            : 'API calls share the same quota as the website. Free users get 2 stock + 1 options analysis daily. Upgrade for more.'}
                    </p>
                </div>
            </div>

            {/* Top-up Section */}
            <div className="max-w-2xl mx-4 sm:mx-auto">
                <h2 className="text-xl sm:text-2xl font-bold text-center mb-4 sm:mb-6">{t('pricing.topUpTitle')}</h2>
                <div className="topup-card flex-col sm:flex-row gap-4 sm:gap-6">
                    <div className="flex-1">
                        <div className="font-semibold text-lg">{translateFeature(pricing.topups['100'].name) || t('pricing.topup.name')}</div>
                        <div className="text-sm text-slate-500">{pricing.topups['100'].validity && pricing.topups['100'].validity.includes('3个月') ? t('pricing.topup.validity') : (pricing.topups['100'].validity || t('pricing.topup.validity'))}</div>
                    </div>
                    <div className="flex items-center gap-4 sm:gap-6 justify-between sm:justify-end">
                        {(() => {
                            const topupPrice = getCurrencyAndPrice(pricing.topups['100'].price, pricing.topups['100'].currency);
                            return <div className="text-xl sm:text-2xl font-bold">{topupPrice.symbol}{topupPrice.price}</div>;
                        })()}
                        <Button
                            variant="outline"
                            onClick={() => handleSubscribe('topup_100')}
                            disabled={!!checkoutLoading}
                            className="border-[#0D9B97] text-[#0D9B97] hover:bg-[#0D9B97]/10 whitespace-nowrap"
                        >
                            {checkoutLoading === 'topup_100' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {t('pricing.topUp')}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
