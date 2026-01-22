import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

/**
 * 基础骨架屏组件
 * 用于内容加载时的占位显示
 */
function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted/50",
        className
      )}
      {...props}
    />
  )
}

/**
 * 期权表格骨架屏
 * 用于期权链数据加载时的占位
 */
function OptionTableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {/* 表头骨架 */}
      <div className="flex gap-2 pb-2 border-b border-border/50">
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-6 flex-1" />
      </div>

      {/* 表格行骨架 */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-2 items-center">
          <Skeleton className="h-10 w-20" />
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-20" />
          <Skeleton className="h-10 w-16" />
          <Skeleton className="h-10 flex-1" />
        </div>
      ))}
    </div>
  )
}

/**
 * 期权推荐卡片骨架屏
 * 用于推荐列表加载时的占位
 */
function OptionCardSkeleton() {
  return (
    <div className="p-4 rounded-lg border border-border/50 bg-card/50 space-y-3">
      {/* 股票代码 */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-6 w-16" />
        <Skeleton className="h-5 w-12" />
      </div>

      {/* 策略和价格 */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-20" />
      </div>

      {/* 评分 */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-6 w-10 rounded-full" />
      </div>
    </div>
  )
}

/**
 * 卡片骨架屏
 * 通用卡片加载占位
 */
function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="p-6 rounded-lg border border-border/50 bg-card/50 space-y-4">
      <Skeleton className="h-6 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          style={{ width: `${100 - i * 15}%` }}
        />
      ))}
    </div>
  )
}

/**
 * 历史记录项骨架屏
 */
function HistoryItemSkeleton() {
  return (
    <div className="p-4 rounded-lg border border-border/50 bg-card/50 flex items-center gap-4">
      {/* 左侧图标 */}
      <Skeleton className="h-10 w-10 rounded-full shrink-0" />

      {/* 中间内容 */}
      <div className="flex-1 space-y-2">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-48" />
      </div>

      {/* 右侧时间 */}
      <Skeleton className="h-4 w-20 shrink-0" />
    </div>
  )
}

/**
 * 加载中指示器（带进度）
 */
interface LoadingIndicatorProps {
  progress?: number;
  step?: string;
  className?: string;
}

function LoadingIndicator({ progress = 0, step, className }: LoadingIndicatorProps) {
  return (
    <div className={cn("text-center py-6", className)}>
      {/* 旋转 spinner */}
      <div className="mx-auto mb-4 w-10 h-10 border-2 border-muted border-t-primary rounded-full animate-spin" />

      {/* 进度条 */}
      {progress > 0 && (
        <div className="max-w-xs mx-auto mb-3">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-muted-foreground">Loading...</span>
            <span className="text-primary font-semibold">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-muted rounded-lg h-2 overflow-hidden">
            <div
              className="h-full bg-primary rounded-lg transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* 当前步骤 */}
      {step && (
        <p className="text-muted-foreground text-sm">{step}</p>
      )}
    </div>
  )
}

/**
 * 全屏加载骨架
 * 用于页面级加载
 */
function PageSkeleton() {
  return (
    <div className="space-y-6 p-4 sm:p-6">
      {/* 标题区域 */}
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>

      {/* 筛选区域 */}
      <div className="flex flex-wrap gap-3">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-10 w-28" />
      </div>

      {/* 内容区域 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}

export {
  Skeleton,
  OptionTableSkeleton,
  OptionCardSkeleton,
  CardSkeleton,
  HistoryItemSkeleton,
  LoadingIndicator,
  PageSkeleton
}
