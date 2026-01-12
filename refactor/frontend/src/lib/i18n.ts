
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Translations
const resources = {
    en: {
        translation: {
            // Navigation
            "nav.stock": "Stock Analysis",
            "nav.options": "Options Research",
            "nav.pricing": "Pricing",
            "nav.profile": "Profile",
            "nav.logout": "Logout",
            "nav.login": "Login",

            // Footer
            "footer.copyright": "© 2025 Alpha GBM. Data provided for educational purposes.",

            // Home/Landing
            "home.welcome": "Welcome to AlphaG",
            "home.desc": "Advanced AI-powered stock analysis and options research platform.",

            // Login & Auth
            "auth.login": "Login",
            "auth.signup": "Sign Up",
            "auth.email": "Email",
            "auth.password": "Password",
            "auth.confirmPassword": "Confirm Password",
            "auth.forgotPassword": "Forgot password?",
            "auth.resetPassword": "Reset Password",
            "auth.sendResetEmail": "Send Reset Email",
            "auth.backToLogin": "Back to Login",
            "auth.signInWithGoogle": "Sign in with Google",
            "auth.dontHaveAccount": "Don't have an account? Sign Up",
            "auth.alreadyHaveAccount": "Already have an account? Login",
            "auth.processing": "Processing...",

            // Profile Page
            "profile.title": "Account Center",
            "profile.userInfo": "User Information",
            "profile.subscriptionAndCredits": "Subscription & Credits",
            "profile.currentPlan": "Current Plan",
            "profile.remainingCredits": "Remaining Credits",
            "profile.dailyFreeCredits": "Daily Free Credits",
            "profile.usageHistory": "Usage History",
            "profile.transactionHistory": "Transaction History",
            "profile.loading": "Loading...",
            "profile.refreshCredits": "Refresh Credits",
            "profile.time": "Time",
            "profile.serviceType": "Service Type",
            "profile.creditsUsed": "Credits Used",
            "profile.date": "Date",
            "profile.description": "Description",
            "profile.amount": "Amount",
            "profile.status": "Status",
            "profile.successful": "Successful",
            "profile.noUsageRecords": "No usage records",
            "profile.noTransactionRecords": "No transaction records",
            "profile.totalRecords": "Total {{count}} records",

            // Pricing Page
            "pricing.title": "Choose Your Plan",
            "pricing.subtitle": "Whether you're just starting out or a professional investor, we have the right intelligent analysis tools for you",
            "pricing.subscriptionSuccess": "Subscription Successful!",
            "pricing.subscriptionSuccessDesc": "Your membership has been activated, thank you for your support",
            "pricing.currentPlan": "Current Plan",
            "pricing.subscribe": "Subscribe",
            "pricing.topUpTitle": "Pay-per-use Top-up",
            "pricing.topUp": "Top Up",
            "pricing.free.name": "Free",
            "pricing.free.desc": "Free trial",
            "pricing.plus.name": "Plus",
            "pricing.plus.desc": "For serious investors",
            "pricing.pro.name": "Pro",
            "pricing.pro.desc": "Professional experience",
            "pricing.mostPopular": "🔥 Most Popular",
            "pricing.perMonth": "/month",

            // Common
            "common.pleaseLogin": "Please login first",
            "common.email": "Email",
            "common.password": "Password",
            "common.confirm": "Confirm",
            "common.cancel": "Cancel",
            "common.save": "Save",
            "common.loading": "Loading...",
            "common.error": "Error",
            "common.success": "Success",
            "common.warning": "Warning"
        }
    },
    zh: {
        translation: {
            // 导航
            "nav.stock": "股票分析",
            "nav.options": "期权研究",
            "nav.pricing": "定价方案",
            "nav.profile": "个人中心",
            "nav.logout": "退出登录",
            "nav.login": "登录",

            // 页脚
            "footer.copyright": "© 2025 Alpha GBM. 数据仅供教育用途。",

            // 主页/着陆页
            "home.welcome": "欢迎来到 AlphaG",
            "home.desc": "先进的 AI 驱动股票分析与期权研究平台。",

            // 登录与认证
            "auth.login": "登录",
            "auth.signup": "注册",
            "auth.email": "邮箱",
            "auth.password": "密码",
            "auth.confirmPassword": "确认密码",
            "auth.forgotPassword": "忘记密码？",
            "auth.resetPassword": "重置密码",
            "auth.sendResetEmail": "发送重置邮件",
            "auth.backToLogin": "返回登录",
            "auth.signInWithGoogle": "使用 Google 登录",
            "auth.dontHaveAccount": "没有账户？立即注册",
            "auth.alreadyHaveAccount": "已有账户？立即登录",
            "auth.processing": "处理中...",

            // 个人资料页面
            "profile.title": "账户中心",
            "profile.userInfo": "用户信息",
            "profile.subscriptionAndCredits": "订阅与额度",
            "profile.currentPlan": "当前方案",
            "profile.remainingCredits": "剩余额度",
            "profile.dailyFreeCredits": "每日免费额度",
            "profile.usageHistory": "使用记录",
            "profile.transactionHistory": "交易记录",
            "profile.loading": "加载中...",
            "profile.refreshCredits": "刷新额度",
            "profile.time": "时间",
            "profile.serviceType": "服务类型",
            "profile.creditsUsed": "消耗额度",
            "profile.date": "日期",
            "profile.description": "描述",
            "profile.amount": "金额",
            "profile.status": "状态",
            "profile.successful": "成功",
            "profile.noUsageRecords": "暂无使用记录",
            "profile.noTransactionRecords": "暂无交易记录",
            "profile.totalRecords": "共 {{count}} 条记录",

            // 定价页面
            "pricing.title": "选择适合您的方案",
            "pricing.subtitle": "无论您是刚入门还是专业投资者，我们都有适合您的智能分析工具",
            "pricing.subscriptionSuccess": "订阅成功！",
            "pricing.subscriptionSuccessDesc": "您的会员已激活，感谢您的支持",
            "pricing.currentPlan": "当前方案",
            "pricing.subscribe": "立即订阅",
            "pricing.topUpTitle": "按量充值",
            "pricing.topUp": "充值",
            "pricing.free.name": "免费版",
            "pricing.free.desc": "免费体验",
            "pricing.plus.name": "进阶版",
            "pricing.plus.desc": "适合认真投资者",
            "pricing.pro.name": "专业版",
            "pricing.pro.desc": "专业级体验",
            "pricing.mostPopular": "🔥 最受欢迎",
            "pricing.perMonth": "/月",

            // 通用
            "common.pleaseLogin": "请先登录",
            "common.email": "邮箱",
            "common.password": "密码",
            "common.confirm": "确认",
            "common.cancel": "取消",
            "common.save": "保存",
            "common.loading": "加载中...",
            "common.error": "错误",
            "common.success": "成功",
            "common.warning": "警告"
        }
    }
};

i18n
    .use(initReactI18next)
    .init({
        resources,
        lng: "zh", // 默认使用中文
        fallbackLng: "zh", // 备用语言也设为中文
        interpolation: {
            escapeValue: false
        }
    });

export default i18n;
