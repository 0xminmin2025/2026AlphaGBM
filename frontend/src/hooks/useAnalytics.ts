/**
 * Analytics Hook
 *
 * React hook for easy access to analytics tracking functions.
 * Provides convenient methods for tracking various user events.
 */

import { useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import {
  trackEvent,
  trackPageView,
} from '@/lib/analytics';
import type { AnalyticsEventType, UserTier } from '@/lib/analytics';

interface UseAnalyticsReturn {
  // Core tracking
  track: (eventType: AnalyticsEventType, properties?: Record<string, unknown>) => void;
  trackPageView: (pageName?: string) => void;

  // Stock analysis tracking
  trackStockAnalysisStart: (ticker: string) => void;
  trackStockAnalysisComplete: (ticker: string, duration?: number) => void;
  trackStockAnalysisError: (ticker: string, error: string) => void;

  // Option analysis tracking
  trackOptionAnalysisStart: (ticker: string, expiry: string, strategy?: string) => void;
  trackOptionAnalysisComplete: (ticker: string, expiry: string, optionCount: number) => void;
  trackOptionAnalysisError: (ticker: string, error: string) => void;

  // Reverse score tracking
  trackReverseScoreStart: (inputMode: 'manual' | 'upload') => void;
  trackReverseScoreComplete: (symbol: string, strategy: string) => void;
  trackReverseScoreError: (error: string) => void;

  // Recommendation tracking
  trackRecommendationView: (symbol: string, position: number, type: 'stock' | 'option') => void;
  trackRecommendationClick: (symbol: string, strategy?: string, type?: 'stock' | 'option') => void;

  // Conversion tracking
  trackUnlockModalShow: (feature: string, userTier: UserTier) => void;
  trackCtaClick: (ctaType: string, location: string) => void;
  trackPricingView: (source: string) => void;
  trackCheckoutStart: (plan: string) => void;
  trackCheckoutComplete: (plan: string, amount: number) => void;

  // Error tracking
  trackError: (errorType: string, message: string, context?: Record<string, unknown>) => void;
}

export function useAnalytics(): UseAnalyticsReturn {
  const location = useLocation();

  // Core tracking
  const track = useCallback(
    (eventType: AnalyticsEventType, properties?: Record<string, unknown>) => {
      trackEvent(eventType, {
        ...properties,
        current_path: location.pathname,
      });
    },
    [location.pathname]
  );

  const trackPage = useCallback(
    (pageName?: string) => {
      trackPageView(pageName || location.pathname);
    },
    [location.pathname]
  );

  // Stock analysis tracking
  const trackStockAnalysisStart = useCallback(
    (ticker: string) => {
      track('stock_analysis_start', { ticker });
    },
    [track]
  );

  const trackStockAnalysisComplete = useCallback(
    (ticker: string, duration?: number) => {
      track('stock_analysis_complete', { ticker, duration_ms: duration });
    },
    [track]
  );

  const trackStockAnalysisError = useCallback(
    (ticker: string, error: string) => {
      track('stock_analysis_error', { ticker, error });
    },
    [track]
  );

  // Option analysis tracking
  const trackOptionAnalysisStart = useCallback(
    (ticker: string, expiry: string, strategy?: string) => {
      track('option_analysis_start', { ticker, expiry, strategy });
    },
    [track]
  );

  const trackOptionAnalysisComplete = useCallback(
    (ticker: string, expiry: string, optionCount: number) => {
      track('option_analysis_complete', { ticker, expiry, option_count: optionCount });
    },
    [track]
  );

  const trackOptionAnalysisError = useCallback(
    (ticker: string, error: string) => {
      track('option_analysis_error', { ticker, error });
    },
    [track]
  );

  // Reverse score tracking
  const trackReverseScoreStart = useCallback(
    (inputMode: 'manual' | 'upload') => {
      track('reverse_score_start', { input_mode: inputMode });
    },
    [track]
  );

  const trackReverseScoreComplete = useCallback(
    (symbol: string, strategy: string) => {
      track('reverse_score_complete', { symbol, strategy });
    },
    [track]
  );

  const trackReverseScoreError = useCallback(
    (error: string) => {
      track('reverse_score_error', { error });
    },
    [track]
  );

  // Recommendation tracking
  const trackRecommendationView = useCallback(
    (symbol: string, position: number, type: 'stock' | 'option') => {
      track('recommendation_view', { symbol, position, type });
    },
    [track]
  );

  const trackRecommendationClick = useCallback(
    (symbol: string, strategy?: string, type: 'stock' | 'option' = 'option') => {
      track('recommendation_click', { symbol, strategy, type });
    },
    [track]
  );

  // Conversion tracking
  const trackUnlockModalShow = useCallback(
    (feature: string, userTier: UserTier) => {
      track('unlock_modal_show', { feature, user_tier: userTier });
    },
    [track]
  );

  const trackCtaClick = useCallback(
    (ctaType: string, location: string) => {
      track('cta_click', { cta_type: ctaType, location });
    },
    [track]
  );

  const trackPricingView = useCallback(
    (source: string) => {
      track('pricing_view', { source });
    },
    [track]
  );

  const trackCheckoutStart = useCallback(
    (plan: string) => {
      track('checkout_start', { plan });
    },
    [track]
  );

  const trackCheckoutComplete = useCallback(
    (plan: string, amount: number) => {
      track('checkout_complete', { plan, amount });
    },
    [track]
  );

  // Error tracking
  const trackError = useCallback(
    (errorType: string, message: string, context?: Record<string, unknown>) => {
      track('error_occurred', { error_type: errorType, message, ...context });
    },
    [track]
  );

  return {
    track,
    trackPageView: trackPage,
    trackStockAnalysisStart,
    trackStockAnalysisComplete,
    trackStockAnalysisError,
    trackOptionAnalysisStart,
    trackOptionAnalysisComplete,
    trackOptionAnalysisError,
    trackReverseScoreStart,
    trackReverseScoreComplete,
    trackReverseScoreError,
    trackRecommendationView,
    trackRecommendationClick,
    trackUnlockModalShow,
    trackCtaClick,
    trackPricingView,
    trackCheckoutStart,
    trackCheckoutComplete,
    trackError,
  };
}
