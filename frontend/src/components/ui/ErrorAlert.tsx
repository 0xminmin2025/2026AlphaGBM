import { AlertTriangle, RefreshCw, HelpCircle, X } from 'lucide-react';
import { Button } from './button';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

/**
 * 错误码映射到用户友好的消息和建议
 */
const errorMessages: Record<string, { messageKey: string; suggestionKeys: string[] }> = {
  // 期权相关错误
  'failed to fetch expirations': {
    messageKey: 'error.fetchExpirations',
    suggestionKeys: ['error.suggestion.checkSymbol', 'error.suggestion.checkNetwork', 'error.suggestion.tryLater']
  },
  'failed to start options analysis': {
    messageKey: 'error.startAnalysis',
    suggestionKeys: ['error.suggestion.checkSymbol', 'error.suggestion.selectExpiry']
  },
  'task failed': {
    messageKey: 'error.taskFailed',
    suggestionKeys: ['error.suggestion.tryAgain', 'error.suggestion.differentExpiry']
  },
  'analysis timeout': {
    messageKey: 'error.timeout',
    suggestionKeys: ['error.suggestion.checkNetwork', 'error.suggestion.tryFewerStocks']
  },
  'no common expiry': {
    messageKey: 'error.noCommonExpiry',
    suggestionKeys: ['error.suggestion.adjustSelection', 'error.suggestion.tryFewerStocks']
  },
  // 网络相关错误
  'network error': {
    messageKey: 'error.network',
    suggestionKeys: ['error.suggestion.checkNetwork', 'error.suggestion.tryLater']
  },
  'failed to check task status': {
    messageKey: 'error.taskStatusFailed',
    suggestionKeys: ['error.suggestion.checkNetwork', 'error.suggestion.tryAgain']
  },
  // 认证相关错误
  'unauthorized': {
    messageKey: 'error.unauthorized',
    suggestionKeys: ['error.suggestion.relogin']
  },
  'insufficient credits': {
    messageKey: 'error.insufficientCredits',
    suggestionKeys: ['error.suggestion.topUp', 'error.suggestion.checkPricing']
  },
  // 股票相关错误
  'invalid symbol': {
    messageKey: 'error.invalidSymbol',
    suggestionKeys: ['error.suggestion.checkSymbol']
  }
};

/**
 * 根据错误字符串查找匹配的错误信息
 */
function findMatchingError(error: string): { messageKey: string; suggestionKeys: string[] } | null {
  const lowerError = error.toLowerCase();

  for (const [key, value] of Object.entries(errorMessages)) {
    if (lowerError.includes(key)) {
      return value;
    }
  }

  return null;
}

interface ErrorAlertProps {
  error: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  suggestions?: string[];
  showHelp?: boolean;
  className?: string;
  variant?: 'default' | 'compact' | 'inline';
}

/**
 * 错误提示组件
 * 显示用户友好的错误信息和可操作的建议
 */
export function ErrorAlert({
  error,
  onRetry,
  onDismiss,
  suggestions,
  showHelp = true,
  className,
  variant = 'default'
}: ErrorAlertProps) {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language.startsWith('zh');

  // 查找匹配的错误信息
  const matchedError = findMatchingError(error);

  // 获取显示的消息
  const displayMessage = matchedError
    ? t(matchedError.messageKey, { defaultValue: error })
    : error;

  // 获取建议列表
  const displaySuggestions = suggestions ||
    matchedError?.suggestionKeys.map(key => t(key)) ||
    [];

  if (variant === 'inline') {
    return (
      <div className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-md bg-destructive/10 border border-destructive/30 text-sm",
        className
      )}>
        <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
        <span className="text-destructive flex-1">{displayMessage}</span>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry} className="h-7 px-2">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        )}
        {onDismiss && (
          <Button variant="ghost" size="sm" onClick={onDismiss} className="h-7 px-2">
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={cn(
        "rounded-lg border border-destructive/50 bg-destructive/10 p-3",
        className
      )}>
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-destructive">{displayMessage}</p>
            {onRetry && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetry}
                className="mt-2 h-7 text-xs"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                {t('error.retry', { defaultValue: isZh ? '重试' : 'Retry' })}
              </Button>
            )}
          </div>
          {onDismiss && (
            <Button variant="ghost" size="sm" onClick={onDismiss} className="h-6 w-6 p-0">
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div className={cn(
      "rounded-lg border border-destructive/50 bg-destructive/10 p-4",
      className
    )}>
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-destructive/20 shrink-0">
          <AlertTriangle className="h-4 w-4 text-destructive" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-destructive">{displayMessage}</p>

          {displaySuggestions.length > 0 && (
            <div className="mt-3">
              <p className="text-sm text-muted-foreground mb-2">
                {t('error.trySuggestions', { defaultValue: isZh ? '请尝试以下操作：' : 'Try the following:' })}
              </p>
              <ul className="text-sm text-muted-foreground space-y-1">
                {displaySuggestions.map((suggestion, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="border-destructive/30 hover:bg-destructive/10 text-destructive hover:text-destructive"
              >
                <RefreshCw className="h-4 w-4 mr-1.5" />
                {t('error.retry', { defaultValue: isZh ? '重试' : 'Retry' })}
              </Button>
            )}
            {showHelp && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => window.open('/help', '_blank')}
                className="text-muted-foreground"
              >
                <HelpCircle className="h-4 w-4 mr-1.5" />
                {t('error.getHelp', { defaultValue: isZh ? '获取帮助' : 'Get Help' })}
              </Button>
            )}
          </div>
        </div>

        {onDismiss && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="h-8 w-8 p-0 shrink-0"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * 简化的错误提示（用于表单字段等）
 */
interface FieldErrorProps {
  error: string;
  className?: string;
}

export function FieldError({ error, className }: FieldErrorProps) {
  return (
    <p className={cn("text-sm text-destructive mt-1", className)}>
      {error}
    </p>
  );
}

/**
 * 错误边界回退组件
 */
interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary?: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  const { i18n } = useTranslation();
  const isZh = i18n.language.startsWith('zh');

  return (
    <div className="flex flex-col items-center justify-center min-h-[200px] p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/20 mb-4">
        <AlertTriangle className="h-6 w-6 text-destructive" />
      </div>
      <h3 className="text-lg font-semibold mb-2">
        {isZh ? '出现错误' : 'Something went wrong'}
      </h3>
      <p className="text-muted-foreground text-sm mb-4 max-w-md">
        {error.message || (isZh ? '发生了意外错误，请刷新页面重试' : 'An unexpected error occurred. Please refresh the page.')}
      </p>
      {resetErrorBoundary && (
        <Button onClick={resetErrorBoundary} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          {isZh ? '重试' : 'Try Again'}
        </Button>
      )}
    </div>
  );
}

export default ErrorAlert;
