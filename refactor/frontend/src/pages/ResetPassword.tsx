import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';

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
            <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
                <Card className="w-[350px]">
                    <CardHeader>
                        <CardTitle>Verifying Reset Link</CardTitle>
                        <CardDescription>
                            Please wait while we verify your password reset link...
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-6">
                        <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                        <p className="text-sm text-gray-600">
                            Authenticating...
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (success) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
                <Card className="w-[350px]">
                    <CardHeader>
                        <CardTitle>Password Reset Successful</CardTitle>
                        <CardDescription>
                            Your password has been updated successfully
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-6">
                        <div className="text-green-600 mb-4">
                            ✅ Password Updated!
                        </div>
                        <p className="text-sm text-gray-600 mb-4">
                            You will be redirected to the login page automatically.
                        </p>
                        <Button onClick={() => navigate('/login')} className="w-full">
                            Go to Login
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Error state - invalid/expired link
    if (error && !hasValidSession) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
                <Card className="w-[350px]">
                    <CardHeader>
                        <CardTitle>Reset Link Error</CardTitle>
                        <CardDescription>
                            There was a problem with your password reset link
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center py-6">
                        <div className="text-red-600 mb-4">
                            ❌ {error}
                        </div>
                        <div className="space-y-3">
                            <Button onClick={() => navigate('/login')} className="w-full">
                                Request New Reset Link
                            </Button>
                            <Button variant="outline" onClick={() => window.location.reload()} className="w-full">
                                Try Again
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Main password reset form - only shown if we have a valid session
    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
            <Card className="w-[350px]">
                <CardHeader>
                    <CardTitle>Reset Your Password</CardTitle>
                    <CardDescription>
                        Enter your new password below
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {hasValidSession ? (
                        <>
                            {error && (
                                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                                    {error}
                                </div>
                            )}
                            <form onSubmit={handlePasswordReset}>
                                <div className="grid w-full items-center gap-4">
                                    <div className="flex flex-col space-y-1.5">
                                        <Label htmlFor="password">New Password</Label>
                                        <Input
                                            id="password"
                                            type="password"
                                            placeholder="Enter new password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            minLength={6}
                                        />
                                        <p className="text-xs text-gray-500">
                                            Password must be at least 6 characters long
                                        </p>
                                    </div>
                                    <div className="flex flex-col space-y-1.5">
                                        <Label htmlFor="confirmPassword">Confirm New Password</Label>
                                        <Input
                                            id="confirmPassword"
                                            type="password"
                                            placeholder="Confirm new password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            minLength={6}
                                        />
                                    </div>
                                </div>
                            </form>
                        </>
                    ) : (
                        <div className="text-center py-6">
                            <div className="text-yellow-600 mb-4">
                                ⚠️ Authentication Required
                            </div>
                            <p className="text-sm text-gray-600 mb-4">
                                You need a valid reset link to change your password.
                            </p>
                            <Button onClick={() => navigate('/login')} className="w-full">
                                Get Reset Link
                            </Button>
                        </div>
                    )}
                </CardContent>
                {hasValidSession && (
                    <CardFooter className="flex flex-col gap-2">
                        <Button
                            className="w-full"
                            onClick={handlePasswordReset}
                            disabled={loading}
                        >
                            {loading ? 'Updating Password...' : 'Update Password'}
                        </Button>
                        <Button variant="link" onClick={() => navigate('/login')}>
                            Back to Login
                        </Button>
                    </CardFooter>
                )}
            </Card>
        </div>
    );
}