import { useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useTranslation } from 'react-i18next';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [isSignUp, setIsSignUp] = useState(false);
    const [isResetPassword, setIsResetPassword] = useState(false);
    const [resetEmailSent, setResetEmailSent] = useState(false);
    const navigate = useNavigate();
    const { t } = useTranslation();

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
                alert('Check your email for the confirmation link!');
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
            alert(error.message);
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
            alert(error.message);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) {
            alert('Please enter your email address');
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
            alert(`Reset failed: ${error.message}`);
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
        <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
            <Card className="w-[350px]">
                <CardHeader>
                    <CardTitle>
                        {isResetPassword
                            ? t('auth.resetPassword')
                            : isSignUp
                            ? t('auth.signup')
                            : t('auth.login')}
                    </CardTitle>
                    <CardDescription>
                        {isResetPassword
                            ? t('auth.sendResetEmail')
                            : isSignUp
                            ? t('auth.signup')
                            : 'Welcome back to AlphaG'}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {resetEmailSent ? (
                        <div className="text-center py-4">
                            <div className="text-green-600 mb-4">
                                ✅ Password reset email sent!
                            </div>
                            <p className="text-sm text-gray-600 mb-4">
                                Check your email for a password reset link. The link will expire in 1 hour.
                            </p>
                            <Button variant="outline" onClick={resetForm} className="w-full">
                                {t('auth.backToLogin')}
                            </Button>
                        </div>
                    ) : (
                        <>
                            <form onSubmit={isResetPassword ? handleResetPassword : handleAuth}>
                                <div className="grid w-full items-center gap-4">
                                    <div className="flex flex-col space-y-1.5">
                                        <Label htmlFor="email">{t('auth.email')}</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            placeholder="name@example.com"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                        />
                                    </div>
                                    {!isResetPassword && (
                                        <div className="flex flex-col space-y-1.5">
                                            <div className="flex justify-between items-center">
                                                <Label htmlFor="password">{t('auth.password')}</Label>
                                                {!isSignUp && (
                                                    <Button
                                                        type="button"
                                                        variant="link"
                                                        className="p-0 h-auto text-xs text-blue-600"
                                                        onClick={() => setIsResetPassword(true)}
                                                    >
                                                        {t('auth.forgotPassword')}
                                                    </Button>
                                                )}
                                            </div>
                                            <Input
                                                id="password"
                                                type="password"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                required
                                            />
                                        </div>
                                    )}
                                </div>
                            </form>
                            {!isResetPassword && (
                                <div className="mt-4">
                                    <Button variant="outline" className="w-full" onClick={handleGoogleLogin} type="button">
                                        {t('auth.signInWithGoogle')}
                                    </Button>
                                </div>
                            )}
                        </>
                    )}
                </CardContent>
                <CardFooter className="flex flex-col gap-2">
                    {!resetEmailSent && (
                        <>
                            <Button
                                className="w-full"
                                onClick={isResetPassword ? handleResetPassword : handleAuth}
                                disabled={loading}
                            >
                                {loading
                                    ? t('auth.processing')
                                    : isResetPassword
                                    ? t('auth.sendResetEmail')
                                    : isSignUp
                                    ? t('auth.signup')
                                    : t('auth.login')}
                            </Button>
                            {isResetPassword ? (
                                <Button variant="link" onClick={() => setIsResetPassword(false)}>
                                    {t('auth.backToLogin')}
                                </Button>
                            ) : (
                                <Button variant="link" onClick={() => setIsSignUp(!isSignUp)}>
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
