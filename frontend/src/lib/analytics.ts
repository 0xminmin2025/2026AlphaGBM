/**
 * AlphaGBM Analytics Core Library
 *
 * A lightweight, self-built analytics system that stores events in Supabase.
 * Features:
 * - Batched event sending (every 5 seconds)
 * - sendBeacon for reliable page unload tracking
 * - Session and user tracking
 * - Important event immediate flushing
 */

// Event types
export type AnalyticsEventType =
  // Page events
  | 'page_view'
  // User events
  | 'user_register'
  | 'user_login'
  | 'user_logout'
  // Stock analysis events
  | 'stock_analysis_start'
  | 'stock_analysis_complete'
  | 'stock_analysis_error'
  // Option analysis events
  | 'option_analysis_start'
  | 'option_analysis_complete'
  | 'option_analysis_error'
  // Reverse score events
  | 'reverse_score_start'
  | 'reverse_score_complete'
  | 'reverse_score_error'
  // Recommendation events
  | 'recommendation_view'
  | 'recommendation_click'
  // Conversion events
  | 'unlock_modal_show'
  | 'cta_click'
  | 'pricing_view'
  | 'checkout_start'
  | 'checkout_complete'
  // Error events
  | 'error_occurred';

// User tier types
export type UserTier = 'guest' | 'free' | 'plus' | 'pro';

// Event interface
interface AnalyticsEvent {
  event_type: AnalyticsEventType;
  session_id: string;
  user_id?: string;
  user_tier: UserTier;
  properties: Record<string, unknown>;
  url: string;
  referrer: string;
  timestamp: string;
}

// Important events that should be sent immediately
const IMPORTANT_EVENTS: AnalyticsEventType[] = [
  'user_register',
  'user_login',
  'checkout_start',
  'checkout_complete',
  'error_occurred',
];

// Generate a unique session ID
const generateSessionId = (): string => {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 9);
  return `${timestamp}-${randomPart}`;
};

// Get or create session ID from sessionStorage
const getSessionId = (): string => {
  const stored = sessionStorage.getItem('alphagbm_session_id');
  if (stored) return stored;

  const newId = generateSessionId();
  sessionStorage.setItem('alphagbm_session_id', newId);
  return newId;
};

class Analytics {
  private static instance: Analytics;
  private eventQueue: AnalyticsEvent[] = [];
  private sessionId: string;
  private userId?: string;
  private userTier: UserTier = 'guest';
  private flushInterval?: ReturnType<typeof setInterval>;
  private apiEndpoint: string;
  private isInitialized = false;

  private constructor() {
    this.sessionId = getSessionId();
    // VITE_API_URL already includes /api, so just append the endpoint path
    this.apiEndpoint = `${import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002/api'}/analytics/events`;
  }

  static getInstance(): Analytics {
    if (!Analytics.instance) {
      Analytics.instance = new Analytics();
    }
    return Analytics.instance;
  }

  /**
   * Initialize the analytics system
   */
  init(): void {
    if (this.isInitialized) return;

    this.isInitialized = true;
    this.startFlushInterval();
    this.setupBeforeUnload();

    console.log('[Analytics] Initialized with session:', this.sessionId);
  }

  /**
   * Set the current user information
   */
  setUser(userId?: string, tier: UserTier = 'guest'): void {
    this.userId = userId;
    this.userTier = tier;
  }

  /**
   * Track an analytics event
   */
  track(eventType: AnalyticsEventType, properties: Record<string, unknown> = {}): void {
    if (!this.isInitialized) {
      console.warn('[Analytics] Not initialized. Call init() first.');
      return;
    }

    const event: AnalyticsEvent = {
      event_type: eventType,
      session_id: this.sessionId,
      user_id: this.userId,
      user_tier: this.userTier,
      properties,
      url: window.location.pathname,
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
    };

    this.eventQueue.push(event);

    // Flush immediately for important events
    if (IMPORTANT_EVENTS.includes(eventType)) {
      this.flush();
    }
  }

  /**
   * Track a page view
   */
  trackPageView(pageName?: string): void {
    this.track('page_view', {
      page_name: pageName || window.location.pathname,
      title: document.title,
    });
  }

  /**
   * Start the flush interval (every 5 seconds)
   */
  private startFlushInterval(): void {
    this.flushInterval = setInterval(() => {
      this.flush();
    }, 5000);
  }

  /**
   * Setup beforeunload handler to flush remaining events
   */
  private setupBeforeUnload(): void {
    window.addEventListener('beforeunload', () => {
      this.flush(true);
    });

    // Also handle visibility change (mobile tab switch)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        this.flush(true);
      }
    });
  }

  /**
   * Flush events to the server
   */
  async flush(useBeacon = false): Promise<void> {
    if (this.eventQueue.length === 0) return;

    const events = [...this.eventQueue];
    this.eventQueue = [];

    const payload = JSON.stringify({ events });

    try {
      if (useBeacon && navigator.sendBeacon) {
        // Use sendBeacon for reliable delivery on page unload
        navigator.sendBeacon(this.apiEndpoint, payload);
      } else {
        // Use fetch for normal operation
        await fetch(this.apiEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: payload,
        });
      }
    } catch (error) {
      // Re-queue events on failure
      this.eventQueue = [...events, ...this.eventQueue];
      console.error('[Analytics] Failed to send events:', error);
    }
  }

  /**
   * Cleanup the analytics instance
   */
  destroy(): void {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }
    this.flush(true);
    this.isInitialized = false;
  }
}

// Export singleton instance
export const analytics = Analytics.getInstance();

// Export convenient tracking functions
export const trackEvent = (
  eventType: AnalyticsEventType,
  properties?: Record<string, unknown>
): void => {
  analytics.track(eventType, properties);
};

export const trackPageView = (pageName?: string): void => {
  analytics.trackPageView(pageName);
};

export const setAnalyticsUser = (userId?: string, tier?: UserTier): void => {
  analytics.setUser(userId, tier);
};

export const initAnalytics = (): void => {
  analytics.init();
};
