import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useTranslation } from 'react-i18next';

export default function ResetPassword() {
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const [sessionLoading, setSessionLoading] = useState(true);
    const [hasValidSession, setHasValidSession] = useState(false);
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { t } = useTranslation();

    useEffect(() => {
        let mounted = true;

        const handleAuthFlow = async () => {
            try {
                console.log('Starting password reset auth flow...');
                console.log('Current URL:', window.location.href);

                // Check if we have a hash in the URL (Supabase format)
                if (window.location.hash) {
                    console.log('Found hash params, letting Supabase handle auth callback...');
                    // Let Supabase handle the callback automatically
                    // It will trigger onAuthStateChange when done
                } else {
                    // No hash parameters, check if we already have a session
                    console.log('No hash params, checking existing session...');
                    const { data: { session }, error } = await supabase.auth.getSession();

                    if (error) {
                        console.error('Session check error:', error);
                        if (mounted) {
                            setError('Failed to check authentication status. Please try again.');
                            setSessionLoading(false);
                        }
                        return;
                    }

                    if (session) {
                        console.log('Found existing session, user can reset password');
                        if (mounted) {
                            setHasValidSession(true);
                            setSessionLoading(false);
                        }
                    } else {
                        console.log('No session found and no hash params');
                        if (mounted) {
                            setError('Invalid or expired reset link. Please request a new password reset.');
                            setSessionLoading(false);
                        }
                    }
                }
            } catch (error) {
                console.error('Auth flow error:', error);
                if (mounted) {
                    setError('Authentication error. Please try again.');
                    setSessionLoading(false);
                }
            }
        };

        // Listen to auth state changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
            console.log('Auth state change:', event, session?.user?.id);

            if (!mounted) return;

            if (event === 'PASSWORD_RECOVERY') {
                console.log('Password recovery event detected');
                setHasValidSession(true);
                setSessionLoading(false);
                setError('');
            } else if (event === 'SIGNED_IN' && session) {
                console.log('User signed in for password reset');
                setHasValidSession(true);
                setSessionLoading(false);
                setError('');
            } else if (event === 'TOKEN_REFRESHED' && session) {
                console.log('Token refreshed');
                setHasValidSession(true);
                setSessionLoading(false);
                setError('');
            } else if (!session && event !== 'INITIAL_SESSION') {
                console.log('No session available');
                setHasValidSession(false);
                setError('Authentication session expired. Please request a new password reset.');
                setSessionLoading(false);
            }
        });

        // Start the auth flow
        handleAuthFlow();

        return () => {
            mounted = false;
            subscription.unsubscribe();
        };
    }, []);

    const handlePasswordReset = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!password || !confirmPassword) {
            setError('Please fill in all fields');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters long');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const { error } = await supabase.auth.updateUser({
                password: password
            });

            if (error) throw error;

            setSuccess(true);

            // Redirect to login after successful password reset
            setTimeout(() => {
                navigate('/login');
            }, 3000);

        } catch (error: any) {
            setError(error.message || 'Failed to reset password. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // Loading state while checking authentication
    if (sessionLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-[#09090B] text-[#FAFAFA]">
                <Card className="w-[400px] bg-[#1c1c1e] border-white/20 shadow-2xl">
                    <CardHeader className="space-y-4">
                        {/* Brand Logo */}
                        <div className="flex justify-center mb-2">
                            <div className="flex items-center space-x-2">
                                <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                                    Alpha<span className="text-[#0D9B97]">GBM</span>
                                </span>
                            </div>
                        </div>

                        <CardTitle className="text-center text-[#FAFAFA] text-xl">验证重置链接</CardTitle>
                        <CardDescription className="text-center text-slate-400">
                            正在验证您的密码重置链接，请稍候...
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-8">
                        <div className="w-12 h-12 border-4 border-[#0D9B97]/30 border-t-[#0D9B97] rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-slate-400 text-sm">
                            正在验证身份...
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (success) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-[#09090B] text-[#FAFAFA]">
                <Card className="w-[400px] bg-[#1c1c1e] border-white/20 shadow-2xl">
                    <CardHeader className="space-y-4">
                        {/* Brand Logo */}
                        <div className="flex justify-center mb-2">
                            <div className="flex items-center space-x-2">
                                <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                                    Alpha<span className="text-[#0D9B97]">GBM</span>
                                </span>
                            </div>
                        </div>

                        <CardTitle className="text-center text-[#FAFAFA] text-xl">密码重置成功</CardTitle>
                        <CardDescription className="text-center text-slate-400">
                            您的密码已成功更新
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-8">
                        <div className="w-16 h-16 bg-[#0D9B97]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <div className="text-[#0D9B97] text-2xl">✓</div>
                        </div>
                        <h3 className="text-[#FAFAFA] font-semibold mb-2">密码更新完成</h3>
                        <p className="text-slate-400 text-sm mb-6">
                            您将自动跳转到登录页面
                        </p>
                        <Button
                            onClick={() => navigate('/login')}
                            className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white font-medium py-2.5"
                        >
                            前往登录
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Error state - invalid/expired link
    if (error && !hasValidSession) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-[#09090B] text-[#FAFAFA]">
                <Card className="w-[400px] bg-[#1c1c1e] border-white/20 shadow-2xl">
                    <CardHeader className="space-y-4">
                        {/* Brand Logo */}
                        <div className="flex justify-center mb-2">
                            <div className="flex items-center space-x-2">
                                <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                                    Alpha<span className="text-[#0D9B97]">GBM</span>
                                </span>
                            </div>
                        </div>

                        <CardTitle className="text-center text-[#FAFAFA] text-xl">重置链接错误</CardTitle>
                        <CardDescription className="text-center text-slate-400">
                            密码重置链接出现问题
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-8">
                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <div className="text-red-400 text-2xl">✗</div>
                        </div>
                        <div className="text-red-400 mb-6 text-sm">
                            {error}
                        </div>
                        <div className="space-y-3">
                            <Button
                                onClick={() => navigate('/login')}
                                className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white font-medium py-2.5"
                            >
                                请求新的重置链接
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => window.location.reload()}
                                className="w-full bg-transparent border-white/20 text-[#FAFAFA] hover:bg-white/10"
                            >
                                重试
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Main password reset form - only shown if we have a valid session
    return (
        <div className="flex items-center justify-center min-h-screen bg-[#09090B] text-[#FAFAFA]">
            <Card className="w-[400px] bg-[#1c1c1e] border-white/20 shadow-2xl">
                <CardHeader className="space-y-4">
                    {/* Brand Logo */}
                    <div className="flex justify-center mb-2">
                        <div className="flex items-center space-x-2">
                            <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                                Alpha<span className="text-[#0D9B97]">GBM</span>
                            </span>
                        </div>
                    </div>

                    <CardTitle className="text-center text-[#FAFAFA] text-xl">重置密码</CardTitle>
                    <CardDescription className="text-center text-slate-400">
                        请输入您的新密码
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {hasValidSession ? (
                        <>
                            {error && (
                                <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded mb-4 text-sm">
                                    {error}
                                </div>
                            )}
                            <form onSubmit={handlePasswordReset}>
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="password" className="text-[#FAFAFA] text-sm font-medium">
                                            新密码
                                        </Label>
                                        <Input
                                            id="password"
                                            type="password"
                                            placeholder="输入新密码"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            minLength={6}
                                            className="bg-[#27272a] border-white/20 text-[#FAFAFA] placeholder:text-slate-400 focus:border-[#0D9B97] focus:ring-[#0D9B97]/20"
                                        />
                                        <p className="text-xs text-slate-400">
                                            密码长度至少6个字符
                                        </p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="confirmPassword" className="text-[#FAFAFA] text-sm font-medium">
                                            确认新密码
                                        </Label>
                                        <Input
                                            id="confirmPassword"
                                            type="password"
                                            placeholder="再次输入新密码"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            minLength={6}
                                            className="bg-[#27272a] border-white/20 text-[#FAFAFA] placeholder:text-slate-400 focus:border-[#0D9B97] focus:ring-[#0D9B97]/20"
                                        />
                                    </div>
                                </div>
                            </form>
                        </>
                    ) : (
                        <div className="text-center py-6">
                            <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                <div className="text-yellow-400 text-2xl">⚠</div>
                            </div>
                            <h3 className="text-[#FAFAFA] font-semibold mb-2">需要身份验证</h3>
                            <p className="text-slate-400 text-sm mb-6">
                                您需要有效的重置链接才能更改密码
                            </p>
                            <Button
                                onClick={() => navigate('/login')}
                                className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white font-medium py-2.5"
                            >
                                获取重置链接
                            </Button>
                        </div>
                    )}
                </CardContent>
                {hasValidSession && (
                    <CardFooter className="flex flex-col gap-3 pt-6">
                        <Button
                            className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white font-medium py-2.5 transition-all duration-200"
                            onClick={handlePasswordReset}
                            disabled={loading}
                        >
                            {loading ? (
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                    更新密码中...
                                </div>
                            ) : (
                                '更新密码'
                            )}
                        </Button>
                        <Button
                            variant="link"
                            onClick={() => navigate('/login')}
                            className="text-slate-400 hover:text-[#FAFAFA] p-0"
                        >
                            返回登录
                        </Button>
                    </CardFooter>
                )}
            </Card>
        </div>
    );
}