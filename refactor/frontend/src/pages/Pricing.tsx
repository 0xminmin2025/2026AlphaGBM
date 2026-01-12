import { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Check, Loader2, Sparkles, Zap, Crown } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';

// Modern pricing page styles
const styles = `
    .pricing-card {
        background: linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 1.5rem;
        padding: 2rem;
        position: relative;
        transition: all 0.3s ease;
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
        padding: 1.5rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.3s ease;
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

type SubscriptionInfo = {
    has_subscription: boolean;
    plan_tier: string;
    status: string;
};

export default function Pricing() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { pricing, credits, pricingLoading, creditsLoading } = useUserData();
    const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
    const [currentPlan, setCurrentPlan] = useState<string>('free');

    const success = searchParams.get('success');

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
            const response = await api.post('/payment/create-checkout-session', {
                price_key: priceKey,
                success_url: window.location.origin + '/pricing?success=true',
                cancel_url: window.location.origin + '/pricing?canceled=true'
            });
            window.location.href = response.data.checkout_url;
        } catch (err) {
            console.error(err);
            alert("Failed to start checkout");
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
            <div className="text-center mb-16">
                <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
                    选择适合您的方案
                </h1>
                <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                    无论您是刚入门还是专业投资者，我们都有适合您的智能分析工具
                </p>
            </div>

            {/* Success Message */}
            {success && (
                <div className="success-banner max-w-4xl mx-auto">
                    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Check className="w-5 h-5 text-green-500" />
                    </div>
                    <div>
                        <div className="font-semibold text-green-400">订阅成功！</div>
                        <div className="text-sm text-slate-400">您的会员已激活，感谢您的支持</div>
                    </div>
                </div>
            )}

            {/* Pricing Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-16">
                {/* Free Plan */}
                <div className={`pricing-card ${currentPlan === 'free' ? 'current' : ''}`}>
                    {currentPlan === 'free' && <div className="current-badge">当前方案</div>}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                            <Sparkles className="w-6 h-6 text-slate-400" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{pricing.plans.free.name}</h3>
                            <p className="text-sm text-slate-500">免费体验</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        <span className="price-tag">¥0</span>
                        <span className="text-slate-500 ml-2">永久免费</span>
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.free.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{f}</span>
                            </div>
                        ))}
                    </div>

                    <button className="subscribe-btn outline" disabled>
                        {currentPlan === 'free' ? '当前方案' : '免费版'}
                    </button>
                </div>

                {/* Plus Plan - Featured */}
                <div className={`pricing-card featured ${currentPlan === 'plus' ? 'current' : ''}`}>
                    {currentPlan === 'plus' ? (
                        <div className="current-badge">当前方案</div>
                    ) : (
                        <div className="featured-badge">🔥 最受欢迎</div>
                    )}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-[#0D9B97]/20 flex items-center justify-center">
                            <Zap className="w-6 h-6 text-[#0D9B97]" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{pricing.plans.plus.name}</h3>
                            <p className="text-sm text-slate-500">适合认真投资者</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        <span className="price-tag">¥{pricing.plans.plus.monthly.price}</span>
                        <span className="text-slate-500 ml-2">/月</span>
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.plus.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{f}</span>
                            </div>
                        ))}
                    </div>

                    {currentPlan === 'plus' ? (
                        <button className="subscribe-btn outline" disabled>当前方案</button>
                    ) : (
                        <Button
                            className="subscribe-btn primary"
                            onClick={() => handleSubscribe('plus_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {checkoutLoading === 'plus_monthly' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            立即订阅
                        </Button>
                    )}
                </div>

                {/* Pro Plan */}
                <div className={`pricing-card ${currentPlan === 'pro' ? 'current' : ''}`}>
                    {currentPlan === 'pro' && <div className="current-badge">当前方案</div>}
                    <div className="flex items-center gap-3 mb-6 mt-2">
                        <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
                            <Crown className="w-6 h-6 text-amber-500" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">{pricing.plans.pro.name}</h3>
                            <p className="text-sm text-slate-500">专业级体验</p>
                        </div>
                    </div>

                    <div className="mb-6">
                        <span className="price-tag">¥{pricing.plans.pro.monthly.price}</span>
                        <span className="text-slate-500 ml-2">/月</span>
                    </div>

                    <div className="space-y-1 mb-8">
                        {pricing.plans.pro.features.map((f: string) => (
                            <div key={f} className="feature-item">
                                <div className="feature-icon">
                                    <Check className="w-3 h-3 text-green-500" />
                                </div>
                                <span>{f}</span>
                            </div>
                        ))}
                    </div>

                    {currentPlan === 'pro' ? (
                        <button className="subscribe-btn outline" disabled>当前方案</button>
                    ) : (
                        <Button
                            className="subscribe-btn primary"
                            onClick={() => handleSubscribe('pro_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {checkoutLoading === 'pro_monthly' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            立即订阅
                        </Button>
                    )}
                </div>
            </div>

            {/* Top-up Section */}
            <div className="max-w-2xl mx-auto">
                <h2 className="text-2xl font-bold text-center mb-6">按量充值</h2>
                <div className="topup-card">
                    <div>
                        <div className="font-semibold text-lg">{pricing.topups['100'].name}</div>
                        <div className="text-sm text-slate-500">{pricing.topups['100'].validity}</div>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="text-2xl font-bold">¥{pricing.topups['100'].price}</div>
                        <Button
                            variant="outline"
                            onClick={() => handleSubscribe('topup_100')}
                            disabled={!!checkoutLoading}
                            className="border-[#0D9B97] text-[#0D9B97] hover:bg-[#0D9B97]/10"
                        >
                            {checkoutLoading === 'topup_100' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            充值
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
