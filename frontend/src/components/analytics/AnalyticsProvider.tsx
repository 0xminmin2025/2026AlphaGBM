/**
 * Analytics Provider
 *
 * React context provider that integrates analytics with auth state.
 * Automatically tracks user information and page views.
 */

import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import { initAnalytics, setAnalyticsUser, trackPageView } from '@/lib/analytics';
import type { UserTier } from '@/lib/analytics';

interface AnalyticsProviderProps {
  children: React.ReactNode;
}

/**
 * Determine user tier based on auth and subscription state
 */
const getUserTier = (
  user: { id: string } | null,
  hasSubscription: boolean,
  planTier: string
): UserTier => {
  if (!user) return 'guest';
  if (!hasSubscription) return 'free';

  // Map subscription plan tier to analytics tier
  const tierMap: Record<string, UserTier> = {
    plus: 'plus',
    pro: 'pro',
  };

  return tierMap[planTier?.toLowerCase()] || 'free';
};

export function AnalyticsProvider({ children }: AnalyticsProviderProps) {
  const { user } = useAuth();
  const { credits } = useUserData();
  const location = useLocation();
  const prevPathRef = useRef<string>('');
  const isInitializedRef = useRef(false);

  // Initialize analytics on mount
  useEffect(() => {
    if (!isInitializedRef.current) {
      initAnalytics();
      isInitializedRef.current = true;
    }
  }, []);

  // Update analytics user when auth state changes
  useEffect(() => {
    const userTier = getUserTier(
      user ? { id: user.id } : null,
      credits?.subscription?.has_subscription || false,
      credits?.subscription?.plan_tier || ''
    );

    setAnalyticsUser(user?.id, userTier);
  }, [user, credits?.subscription?.has_subscription, credits?.subscription?.plan_tier]);

  // Track page views when location changes
  useEffect(() => {
    // Only track if the path has actually changed
    if (location.pathname !== prevPathRef.current) {
      prevPathRef.current = location.pathname;

      // Add a small delay to ensure the page has rendered
      const timer = setTimeout(() => {
        trackPageView(location.pathname);
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [location.pathname]);

  return <>{children}</>;
}

export default AnalyticsProvider;
