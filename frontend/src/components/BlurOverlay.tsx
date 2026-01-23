/**
 * BlurOverlay Component
 *
 * A component that blurs sensitive content and shows a CTA button.
 * Used to hide premium information from non-logged-in or free users.
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Lock } from 'lucide-react';
import { useAnalytics } from '@/hooks/useAnalytics';

// User tier types
export type UserTier = 'guest' | 'free' | 'plus' | 'pro';

// Get current user tier
export const useUserTier = (): UserTier => {
  const { user } = useAuth();
  const { credits } = useUserData();

  if (!user) return 'guest';
  if (!credits?.subscription?.has_subscription) return 'free';

  const planTier = credits.subscription.plan_tier?.toLowerCase();
  if (planTier === 'plus') return 'plus';
  if (planTier === 'pro') return 'pro';

  return 'free';
};

// Check if user has access to a feature
export const useHasAccess = (requiredTier: UserTier): boolean => {
  const currentTier = useUserTier();

  const tierHierarchy: Record<UserTier, number> = {
    guest: 0,
    free: 1,
    plus: 2,
    pro: 3,
  };

  return tierHierarchy[currentTier] >= tierHierarchy[requiredTier];
};

interface BlurOverlayProps {
  children: React.ReactNode;
  requiredTier?: UserTier;
  feature?: string;
  blurAmount?: number;
  showButton?: boolean;
  ctaText?: string;
  className?: string;
}

export function BlurOverlay({
  children,
  requiredTier = 'free',
  feature = 'premium',
  blurAmount = 8,
  showButton = true,
  ctaText,
  className = '',
}: BlurOverlayProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const userTier = useUserTier();
  const hasAccess = useHasAccess(requiredTier);
  const { trackCtaClick } = useAnalytics();

  // If user has access, show content normally
  if (hasAccess) {
    return <>{children}</>;
  }

  // Determine CTA text based on user tier
  const getCtaText = (): string => {
    if (ctaText) return ctaText;

    if (userTier === 'guest') {
      return t('blur.ctaGuest', 'Sign up to unlock');
    }
    if (userTier === 'free') {
      return t('blur.ctaFree', 'Upgrade to unlock');
    }
    if (userTier === 'plus') {
      return t('blur.ctaPlus', 'Upgrade to Pro');
    }
    return t('blur.ctaDefault', 'Unlock');
  };

  // Handle CTA click
  const handleCtaClick = () => {
    trackCtaClick(feature, 'blur_overlay');

    if (userTier === 'guest') {
      navigate('/login');
    } else {
      navigate('/pricing');
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Blurred content */}
      <div
        className="select-none pointer-events-none"
        style={{ filter: `blur(${blurAmount}px)` }}
      >
        {children}
      </div>

      {/* Overlay with CTA */}
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 rounded-lg backdrop-blur-sm">
        <Lock className="w-6 h-6 text-white/80 mb-2" />
        {showButton && (
          <Button
            variant="default"
            size="sm"
            onClick={handleCtaClick}
            className="bg-[#0D9B97] hover:bg-[#10B5B0] text-white"
          >
            {getCtaText()}
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * BlurText - A simpler component for inline text blurring
 */
interface BlurTextProps {
  text: string;
  placeholder?: string;
  requiredTier?: UserTier;
  className?: string;
}

export function BlurText({
  text,
  placeholder = '???',
  requiredTier = 'free',
  className = '',
}: BlurTextProps) {
  const hasAccess = useHasAccess(requiredTier);

  if (hasAccess) {
    return <span className={className}>{text}</span>;
  }

  return (
    <span className={`text-slate-500 ${className}`} title="Unlock to view">
      {placeholder}
    </span>
  );
}

export default BlurOverlay;
