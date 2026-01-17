import { useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, CreditCard, User, Activity, History, RefreshCcw, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import api from '@/lib/api';
import i18n from '@/lib/i18n';

export default function Profile() {
    const { user } = useAuth();
    const { t } = useTranslation();

    // Helper function to translate service type
    const translateServiceType = (serviceType: string): string => {
        const serviceTypeMap: Record<string, string> = {
            'stock_analysis': t('profile.service.stockAnalysis'),
            'option_analysis': t('profile.service.optionAnalysis'),
            'deep_report': t('profile.service.deepReport'),
        };
        return serviceTypeMap[serviceType] || serviceType;
    };

    // Helper function to translate transaction description
    const translateDescription = (description: string): string => {
        // Map common backend descriptions to translation keys
        const descriptionMap: Record<string, string> = {
            '购买': t('profile.purchase'),
            '购买额度': t('profile.purchase'),
        };
        return descriptionMap[description] || description;
    };
    const {
        credits,
        transactions,
        usageLogs,
        transactionPagination,
        usagePagination,
        creditsLoading,
        transactionsLoading,
        usageLoading,
        fetchTransactionsPage,
        fetchUsagePage,
        refreshCredits,
        refreshTransactions,
        refreshUsageHistory,
    } = useUserData();

    const [manageSubscriptionLoading, setManageSubscriptionLoading] = useState(false);

    const handleManageSubscription = async () => {
        setManageSubscriptionLoading(true);
        try {
            const response = await api.post('/payment/customer-portal', {
                return_url: window.location.origin + '/profile'
            });

            if (response.data.portal_url) {
                // 在新窗口中打开Stripe客户门户
                window.open(response.data.portal_url, '_blank');
            }
        } catch (error: any) {
            console.error('打开客户门户失败:', error);
            const errorMessage = error.response?.data?.error || '打开客户门户失败，请稍后再试';
            alert(errorMessage);
        } finally {
            setManageSubscriptionLoading(false);
        }
    };

    if (!user) return (
        <div className="flex items-center justify-center min-h-[50vh] text-slate-400">
            {t('common.pleaseLogin')}
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{t('profile.title')}</h1>

            <div className="grid gap-4 sm:gap-6 grid-cols-1 lg:grid-cols-2">
                {/* User Details Card */}
                <Card className="bg-[#0f0f11] border-white/10">
                    <CardHeader className="flex flex-row items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-[#0D9B97]/20 flex items-center justify-center">
                            <User className="w-5 h-5 text-[#0D9B97]" />
                        </div>
                        <CardTitle>{t('profile.userInfo')}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="flex justify-between items-center py-2 border-b border-white/5">
                            <span className="text-slate-500">{t('common.email')}</span>
                            <span className="font-medium">{user.email}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-slate-500">ID</span>
                            <span className="font-mono text-sm text-slate-400">{user.id?.substring(0, 8)}...</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Subscription & Credits Card */}
                <Card className="bg-[#0f0f11] border-white/10">
                    <CardHeader className="flex flex-row items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-[#0D9B97]/20 flex items-center justify-center">
                            <CreditCard className="w-5 h-5 text-[#0D9B97]" />
                        </div>
                        <CardTitle>{t('profile.subscriptionAndCredits')}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {creditsLoading ? (
                            <div className="text-slate-500 flex items-center gap-2">
                                <RefreshCcw className="w-4 h-4 animate-spin" />
                                {t('profile.loading')}
                            </div>
                        ) : credits ? (
                            <>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-slate-500">{t('profile.currentPlan')}</span>
                                    <Badge
                                        variant={credits.subscription.has_subscription ? 'default' : 'secondary'}
                                        className={credits.subscription.has_subscription ? 'bg-[#0D9B97]' : ''}
                                    >
                                        {credits.subscription.plan_tier.toUpperCase()}
                                    </Badge>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-slate-500">{t('profile.remainingCredits')}</span>
                                    <span className="font-bold text-2xl text-[#0D9B97]">{credits.total_credits}</span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-slate-500">{t('profile.dailyFreeCredits')}</span>
                                    <span className="text-slate-300">
                                        {credits.daily_free.remaining} / {credits.daily_free.quota}
                                    </span>
                                </div>
                                <div className="pt-2 space-y-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={refreshCredits}
                                        disabled={creditsLoading}
                                        className="w-full"
                                    >
                                        <RefreshCcw className={`w-4 h-4 mr-2 ${creditsLoading ? 'animate-spin' : ''}`} />
                                        {t('profile.refreshCredits')}
                                    </Button>

                                    {/* 订阅管理按钮 - 只对已订阅用户显示 */}
                                    {credits.subscription.has_subscription && (
                                        <Button
                                            variant="default"
                                            size="sm"
                                            onClick={handleManageSubscription}
                                            disabled={manageSubscriptionLoading}
                                            className="w-full bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white"
                                        >
                                            <Settings className={`w-4 h-4 mr-2 ${manageSubscriptionLoading ? 'animate-spin' : ''}`} />
                                            {manageSubscriptionLoading ? t('profile.opening') : t('profile.manageSubscription')}
                                        </Button>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="text-slate-500">{t('common.error')}</div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Usage History */}
            <Card className="bg-[#0f0f11] border-white/10">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                            <Activity className="w-5 h-5 text-amber-500" />
                        </div>
                        <div>
                            <CardTitle>{t('profile.usageHistory')}</CardTitle>
                            <p className="text-sm text-slate-500">{t('profile.totalRecords', { count: usagePagination.total_records })}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchUsagePage(usagePagination.current_page - 1)}
                            disabled={!usagePagination.has_prev || usageLoading}
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-slate-500">
                            {usagePagination.current_page} / {usagePagination.total_pages}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchUsagePage(usagePagination.current_page + 1)}
                            disabled={!usagePagination.has_next || usageLoading}
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => refreshUsageHistory()}
                            disabled={usageLoading}
                        >
                            <RefreshCcw className={`w-4 h-4 ${usageLoading ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <Table>
                        <TableHeader>
                            <TableRow className="border-white/5">
                                <TableHead>{t('profile.time')}</TableHead>
                                <TableHead>{t('profile.serviceType')}</TableHead>
                                <TableHead className="text-right">{t('profile.creditsUsed')}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {usageLoading ? (
                                <TableRow>
                                    <TableCell colSpan={3} className="text-center text-slate-500 py-8">
                                        <div className="flex items-center justify-center gap-2">
                                            <RefreshCcw className="w-4 h-4 animate-spin" />
                                            {t('profile.loading')}
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : usageLogs.length > 0 ? (
                                usageLogs.map((log) => (
                                    <TableRow key={log.id} className="border-white/5">
                                        <TableCell className="text-slate-400">
                                            {new Date(log.created_at).toLocaleString(i18n.language === 'zh' ? 'zh-CN' : 'en-US', {
                                                month: 'short',
                                                day: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="border-white/20">
                                                {translateServiceType(log.service_type)}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right font-medium text-amber-500">
                                            -{log.amount_used}
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={3} className="text-center text-slate-500 py-8">
                                        {t('profile.noUsageRecords')}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                    </div>
                </CardContent>
            </Card>

            {/* Payment History */}
            <Card className="bg-[#0f0f11] border-white/10">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                            <History className="w-5 h-5 text-green-500" />
                        </div>
                        <CardTitle>{t('profile.transactionHistory')}</CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchTransactionsPage(transactionPagination.current_page - 1)}
                            disabled={!transactionPagination.has_prev || transactionsLoading}
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-slate-500">
                            {transactionPagination.current_page} / {transactionPagination.total_pages}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchTransactionsPage(transactionPagination.current_page + 1)}
                            disabled={!transactionPagination.has_next || transactionsLoading}
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => refreshTransactions()}
                            disabled={transactionsLoading}
                        >
                            <RefreshCcw className={`w-4 h-4 ${transactionsLoading ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <Table>
                        <TableHeader>
                            <TableRow className="border-white/5">
                                <TableHead>{t('profile.date')}</TableHead>
                                <TableHead>{t('profile.description')}</TableHead>
                                <TableHead>{t('profile.amount')}</TableHead>
                                <TableHead>{t('profile.status')}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {transactionsLoading ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center text-slate-500 py-8">
                                        <div className="flex items-center justify-center gap-2">
                                            <RefreshCcw className="w-4 h-4 animate-spin" />
                                            {t('profile.loading')}
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : transactions.length > 0 ? (
                                transactions.map((transaction, i) => (
                                    <TableRow key={i} className="border-white/5">
                                        <TableCell className="text-slate-400">
                                            {new Date(transaction.date).toLocaleDateString(i18n.language === 'zh' ? 'zh-CN' : 'en-US')}
                                        </TableCell>
                                        <TableCell>{translateDescription(transaction.description)}</TableCell>
                                        <TableCell className="font-medium">
                                            {transaction.currency.toUpperCase()} {transaction.amount}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={transaction.status === 'succeeded' ? 'default' : 'destructive'}
                                                className={transaction.status === 'succeeded' ? 'bg-green-600' : ''}>
                                                {transaction.status === 'succeeded' ? t('profile.successful') : transaction.status}
                                            </Badge>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center text-slate-500 py-8">
                                        {t('profile.noTransactionRecords')}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
