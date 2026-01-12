
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Check, Loader2 } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

export default function Pricing() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [pricing, setPricing] = useState<any>(null);
    // Loading state removed as unused
    const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

    const success = searchParams.get('success');
    // canceled param removed as unused

    useEffect(() => {
        api.get('/payment/pricing').then(res => setPricing(res.data));
    }, []);

    const handleSubscribe = async (priceKey: string) => {
        if (!user) {
            navigate('/login');
            return;
        }

        setCheckoutLoading(priceKey);
        try {
            const response = await api.post('/payment/create-checkout-session', {
                price_key: priceKey,
                success_url: window.location.origin + '/dashboard?success=true',
                cancel_url: window.location.origin + '/pricing?canceled=true'
            });
            window.location.href = response.data.checkout_url;
        } catch (err) {
            console.error(err);
            alert("Failed to start checkout");
            setCheckoutLoading(null);
        }
    };

    if (!pricing) return <div>Loading...</div>;

    return (
        <div className="space-y-8 animate-in fade-in">
            <div className="text-center space-y-4">
                <h1 className="text-4xl font-bold tracking-tight">Simple, Transparent Pricing</h1>
                <p className="text-xl text-muted-foreground">Choose the plan that fits your trading style.</p>
            </div>

            {success && (
                <Alert className="bg-green-50 border-green-200">
                    <Check className="h-4 w-4 text-green-600" />
                    <AlertTitle>Success!</AlertTitle>
                    <AlertDescription>Your subscription has been active. Thank you!</AlertDescription>
                </Alert>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                {/* Free Plan */}
                <Card>
                    <CardHeader>
                        <CardTitle>{pricing.plans.free.name}</CardTitle>
                        <CardDescription>For getting started</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="text-3xl font-bold">Free</div>
                        <ul className="space-y-2">
                            {pricing.plans.free.features.map((f: string) => (
                                <li key={f} className="flex items-center gap-2">
                                    <Check className="h-4 w-4 text-green-500" /> {f}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                    <CardFooter>
                        <Button className="w-full" variant="outline" disabled>Current Plan</Button>
                    </CardFooter>
                </Card>

                {/* Plus Plan */}
                <Card className="border-primary shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 right-0 bg-primary text-primary-foreground px-3 py-1 text-xs font-bold transform rotate-0 rounded-bl-lg">
                        POPULAR
                    </div>
                    <CardHeader>
                        <CardTitle>{pricing.plans.plus.name}</CardTitle>
                        <CardDescription>For serious traders</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-bold">¥{pricing.plans.plus.monthly.price}</span>
                            <span className="text-muted-foreground">/mo</span>
                        </div>
                        <ul className="space-y-2">
                            {pricing.plans.plus.features.map((f: string) => (
                                <li key={f} className="flex items-center gap-2">
                                    <Check className="h-4 w-4 text-green-500" /> {f}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full"
                            onClick={() => handleSubscribe('plus_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {checkoutLoading === 'plus_monthly' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Subscribe Monthly
                        </Button>
                    </CardFooter>
                </Card>

                {/* Pro Plan */}
                <Card>
                    <CardHeader>
                        <CardTitle>{pricing.plans.pro.name}</CardTitle>
                        <CardDescription>For professionals</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-baseline gap-1">
                            <span className="text-3xl font-bold">¥{pricing.plans.pro.monthly.price}</span>
                            <span className="text-muted-foreground">/mo</span>
                        </div>
                        <ul className="space-y-2">
                            {pricing.plans.pro.features.map((f: string) => (
                                <li key={f} className="flex items-center gap-2">
                                    <Check className="h-4 w-4 text-green-500" /> {f}
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full"
                            onClick={() => handleSubscribe('pro_monthly')}
                            disabled={!!checkoutLoading}
                        >
                            {checkoutLoading === 'pro_monthly' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Subscribe Monthly
                        </Button>
                    </CardFooter>
                </Card>
            </div>

            <div className="mt-12 text-center">
                <h2 className="text-2xl font-bold mb-4">Pay as you go</h2>
                <Card className="max-w-md mx-auto">
                    <CardHeader>
                        <CardTitle>{pricing.topups['100'].name}</CardTitle>
                    </CardHeader>
                    <CardContent className="flex justify-between items-center">
                        <div className="text-xl font-bold">¥{pricing.topups['100'].price}</div>
                        <Button
                            variant="secondary"
                            onClick={() => handleSubscribe('topup_100')}
                            disabled={!!checkoutLoading}
                        >
                            {checkoutLoading === 'topup_100' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Top Up
                        </Button>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
