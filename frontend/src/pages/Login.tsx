import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useTranslation } from 'react-i18next';
import { useToastHelpers } from '@/components/ui/toast';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [isSignUp, setIsSignUp] = useState(false);
    const [isResetPassword, setIsResetPassword] = useState(false);
    const [resetEmailSent, setResetEmailSent] = useState(false);
    const navigate = useNavigate();
    const { t } = useTranslation();
    const toast = useToastHelpers();

    const handleAuth = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            if (isSignUp) {
                const { error } = await supabase.auth.signUp({
                    email,
                    password,
                });
                if (error) throw error;
                toast.success(t('auth.signupSuccess'), t('auth.checkEmailConfirm'));
            } else {
                const { error } = await supabase.auth.signInWithPassword({
                    email,
                    password,
                });
                if (error) throw error;
                // Wait a moment for the auth state listener to propagate
                navigate('/');
            }
        } catch (error: any) {
            toast.error(t('auth.authFailed'), error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleLogin = async () => {
        try {
            const { error } = await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: window.location.origin,
                }
            });
            if (error) throw error;
        } catch (error: any) {
            toast.error(t('auth.authFailed'), error.message);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) {
            toast.error(t('auth.emailRequired'), t('auth.pleaseEnterEmail'));
            return;
        }

        setLoading(true);
        try {
            const redirectUrl = `${window.location.origin}/reset-password`;
            console.log('Sending password reset to:', email, 'with redirect:', redirectUrl);

            const { error } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: redirectUrl,
            });

            if (error) throw error;

            setResetEmailSent(true);
        } catch (error: any) {
            console.error('Password reset error:', error);
            toast.error(t('auth.resetFailed'), error.message);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setIsSignUp(false);
        setIsResetPassword(false);
        setResetEmailSent(false);
        setEmail('');
        setPassword('');
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-[#09090B] text-[#FAFAFA] px-4 sm:px-6 lg:px-8">
            <Card className="w-full max-w-[400px] bg-[#1c1c1e] border-white/20 shadow-2xl">
                <CardHeader className="space-y-4">
                    {/* Brand Logo */}
                    <div className="flex justify-center mb-2">
                        <div className="flex items-center space-x-2">
                            <img src="/logo.png" alt="AlphaGBM" className="h-10 w-10" />
                            <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                                Alpha<span className="text-[#0D9B97]">GBM</span>
                            </span>
                        </div>
                    </div>

                    <CardTitle className="text-center text-[#FAFAFA] text-xl">
                        {isResetPassword
                            ? t('auth.resetPassword')
                            : isSignUp
                            ? t('auth.signup')
                            : t('auth.login')}
                    </CardTitle>
                    <CardDescription className="text-center text-slate-400">
                        {isResetPassword
                            ? t('auth.sendResetEmail')
                            : isSignUp
                            ? '创建新账户，开始您的投资之旅'
                            : '欢迎回到 AlphaGBM，请登录您的账户'}
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {resetEmailSent ? (
                        <div className="text-center py-6">
                            <div className="w-16 h-16 bg-[#0D9B97]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                <div className="text-[#0D9B97] text-2xl">✓</div>
                            </div>
                            <h3 className="text-[#FAFAFA] font-semibold mb-2">邮件已发送</h3>
                            <p className="text-slate-400 text-sm mb-6">
                                重置密码链接已发送至您的邮箱，请查收。链接将在1小时后过期。
                            </p>
                            <Button
                                variant="outline"
                                onClick={resetForm}
                                className="w-full bg-transparent border-white/20 text-[#FAFAFA] hover:bg-white/10"
                            >
                                {t('auth.backToLogin')}
                            </Button>
                        </div>
                    ) : (
                        <>
                            <form onSubmit={isResetPassword ? handleResetPassword : handleAuth}>
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="email" className="text-[#FAFAFA] text-sm font-medium">
                                            {t('auth.email')}
                                        </Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            placeholder="name@example.com"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="bg-[#27272a] border-white/20 text-[#FAFAFA] placeholder:text-slate-400 focus:border-[#0D9B97] focus:ring-[#0D9B97]/20"
                                        />
                                    </div>
                                    {!isResetPassword && (
                                        <div className="space-y-2">
                                            <div className="flex justify-between items-center">
                                                <Label htmlFor="password" className="text-[#FAFAFA] text-sm font-medium">
                                                    {t('auth.password')}
                                                </Label>
                                                {!isSignUp && (
                                                    <Button
                                                        type="button"
                                                        variant="link"
                                                        className="p-0 h-auto text-xs text-[#0D9B97] hover:text-[#0D9B97]/80"
                                                        onClick={() => setIsResetPassword(true)}
                                                    >
                                                        {t('auth.forgotPassword')}
                                                    </Button>
                                                )}
                                            </div>
                                            <Input
                                                id="password"
                                                type="password"
                                                placeholder="••••••••"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                                className="bg-[#27272a] border-white/20 text-[#FAFAFA] placeholder:text-slate-400 focus:border-[#0D9B97] focus:ring-[#0D9B97]/20"
                                            />
                                        </div>
                                    )}
                                </div>
                            </form>
                            {!isResetPassword && (
                                <div className="relative">
                                    <div className="absolute inset-0 flex items-center">
                                        <span className="w-full border-t border-white/20" />
                                    </div>
                                    <div className="relative flex justify-center text-xs uppercase">
                                        <span className="bg-[#1c1c1e] px-2 text-slate-400">或</span>
                                    </div>
                                </div>
                            )}
                            {!isResetPassword && (
                                <Button
                                    variant="outline"
                                    className="w-full bg-transparent border-white/20 text-[#FAFAFA] hover:bg-white/10"
                                    onClick={handleGoogleLogin}
                                    type="button"
                                >
                                    <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
                                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                    </svg>
                                    {t('auth.signInWithGoogle')}
                                </Button>
                            )}
                        </>
                    )}
                </CardContent>
                <CardFooter className="flex flex-col gap-3 pt-6">
                    {!resetEmailSent && (
                        <>
                            <Button
                                className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white font-medium py-2.5 transition-all duration-200"
                                onClick={isResetPassword ? handleResetPassword : handleAuth}
                                disabled={loading}
                            >
                                {loading ? (
                                    <div className="flex items-center gap-2">
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        {t('auth.processing')}
                                    </div>
                                ) : (
                                    isResetPassword
                                        ? t('auth.sendResetEmail')
                                        : isSignUp
                                        ? t('auth.signup')
                                        : t('auth.login')
                                )}
                            </Button>
                            {isResetPassword ? (
                                <Button
                                    variant="link"
                                    onClick={() => setIsResetPassword(false)}
                                    className="text-slate-400 hover:text-[#FAFAFA] p-0"
                                >
                                    {t('auth.backToLogin')}
                                </Button>
                            ) : (
                                <Button
                                    variant="link"
                                    onClick={() => setIsSignUp(!isSignUp)}
                                    className="text-slate-400 hover:text-[#FAFAFA] p-0"
                                >
                                    {isSignUp ? t('auth.alreadyHaveAccount') : t('auth.dontHaveAccount')}
                                </Button>
                            )}
                        </>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
}
