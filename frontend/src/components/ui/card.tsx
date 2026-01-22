import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/**
 * 卡片变体样式
 * - default: 标准卡片
 * - glass: 毛玻璃效果（Landing 页面风格）
 * - elevated: 渐变背景提升效果
 * - featured: 品牌色高亮边框
 * - outline: 仅边框无背景
 * - muted: 淡色背景
 */
const cardVariants = cva(
  "rounded-lg border text-card-foreground transition-all duration-300",
  {
    variants: {
      variant: {
        default:
          "bg-card border-border shadow-sm hover:border-primary/30 hover:shadow-md",
        glass:
          "bg-[rgba(24,24,27,0.6)] backdrop-blur-xl border-white/10 hover:border-primary/50 hover:shadow-[0_10px_30px_-10px_rgba(13,155,151,0.3)]",
        elevated:
          "bg-gradient-to-b from-white/5 to-white/[0.02] border-white/10 shadow-lg hover:shadow-xl",
        featured:
          "bg-gradient-to-br from-primary/15 to-primary/5 border-primary/50 shadow-lg",
        outline:
          "bg-transparent border-border hover:border-primary/50",
        muted:
          "bg-muted/50 border-muted hover:bg-muted/70",
        // 无交互效果的静态版本
        "default-static":
          "bg-card border-border shadow-sm",
        "glass-static":
          "bg-[rgba(24,24,27,0.6)] backdrop-blur-xl border-white/10",
      },
      padding: {
        none: "",
        sm: "p-4",
        default: "p-6",
        lg: "p-8",
      },
      interactive: {
        true: "cursor-pointer",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "none", // 保持向后兼容
      interactive: false,
    },
  }
)

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, interactive, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding, interactive, className }))}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent, cardVariants }
