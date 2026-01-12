import { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, CreditCard, User, Activity, History } from 'lucide-react';

type UsageLog = {
    id: number;
    service_type: string;
    amount_used: number;
    created_at: string;
};

type Transaction = {
    date: string;
    description: string;
    amount: number;
    currency: string;
    status: string;
};

const serviceTypeLabels: Record<string, string> = {
    'stock_analysis': '股票分析',
    'option_analysis': '期权分析',
    'deep_report': '深度研报',
};

export default function Profile() {
    const { user } = useAuth();
    const [credits, setCredits] = useState<any>(null);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [usageLogs, setUsageLogs] = useState<UsageLog[]>([]);
    const [usagePage, setUsagePage] = useState(1);
    const [usagePages, setUsagePages] = useState(1);
    const [usageTotal, setUsageTotal] = useState(0);
    const [transactionPage, setTransactionPage] = useState(1);
    const [transactionPages, setTransactionPages] = useState(1);

    useEffect(() => {
        if (user) {
            api.get('/payment/credits').then(res => setCredits(res.data));
            fetchTransactions(1);
            fetchUsageHistory(1);
        }
    }, [user]);

    const fetchTransactions = async (page: number) => {
        try {
            const res = await api.get(`/payment/transactions?page=${page}&per_page=10`);
            setTransactions(res.data.transactions);
            setTransactionPages(res.data.pages);
            setTransactionPage(page);
        } catch (err) {
            console.error(err);
        }
    };

    const fetchUsageHistory = async (page: number) => {
        try {
            const res = await api.get(`/payment/usage-history?page=${page}&per_page=10`);
            setUsageLogs(res.data.usage_logs);
            setUsagePages(res.data.pages);
            setUsageTotal(res.data.total);
            setUsagePage(page);
        } catch (err) {
            console.error(err);
        }
    };

    if (!user) return (
        <div className="flex items-center justify-center min-h-[50vh] text-slate-400">
            请先登录
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in">
            <h1 className="text-3xl font-bold tracking-tight">账户中心</h1>

            <div className="grid gap-6 md:grid-cols-2">
                {/* User Details Card */}
                <Card className="bg-[#0f0f11] border-white/10">
                    <CardHeader className="flex flex-row items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-[#0D9B97]/20 flex items-center justify-center">
                            <User className="w-5 h-5 text-[#0D9B97]" />
                        </div>
                        <CardTitle>用户信息</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="flex justify-between items-center py-2 border-b border-white/5">
                            <span className="text-slate-500">邮箱</span>
                            <span className="font-medium">{user.email}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-slate-500">用户ID</span>
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
                        <CardTitle>订阅与额度</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {credits ? (
                            <>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-slate-500">当前方案</span>
                                    <Badge
                                        variant={credits.subscription.has_subscription ? 'default' : 'secondary'}
                                        className={credits.subscription.has_subscription ? 'bg-[#0D9B97]' : ''}
                                    >
                                        {credits.subscription.plan_tier.toUpperCase()}
                                    </Badge>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b border-white/5">
                                    <span className="text-slate-500">剩余额度</span>
                                    <span className="font-bold text-2xl text-[#0D9B97]">{credits.total_credits}</span>
                                </div>
                                <div className="flex justify-between items-center py-2">
                                    <span className="text-slate-500">每日免费额度</span>
                                    <span className="text-slate-300">
                                        {credits.daily_free.remaining} / {credits.daily_free.quota}
                                    </span>
                                </div>
                            </>
                        ) : (
                            <div className="text-slate-500">加载中...</div>
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
                            <CardTitle>使用记录</CardTitle>
                            <p className="text-sm text-slate-500">共 {usageTotal} 条记录</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchUsageHistory(usagePage - 1)}
                            disabled={usagePage <= 1}
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-slate-500">
                            {usagePage} / {usagePages || 1}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchUsageHistory(usagePage + 1)}
                            disabled={usagePage >= usagePages}
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow className="border-white/5">
                                <TableHead>时间</TableHead>
                                <TableHead>服务类型</TableHead>
                                <TableHead className="text-right">消耗额度</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {usageLogs.length > 0 ? (
                                usageLogs.map((log) => (
                                    <TableRow key={log.id} className="border-white/5">
                                        <TableCell className="text-slate-400">
                                            {new Date(log.created_at).toLocaleString('zh-CN', {
                                                month: 'short',
                                                day: 'numeric',
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="border-white/20">
                                                {serviceTypeLabels[log.service_type] || log.service_type}
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
                                        暂无使用记录
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Payment History */}
            <Card className="bg-[#0f0f11] border-white/10">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                            <History className="w-5 h-5 text-green-500" />
                        </div>
                        <CardTitle>交易记录</CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchTransactions(transactionPage - 1)}
                            disabled={transactionPage <= 1}
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-sm text-slate-500">
                            {transactionPage} / {transactionPages || 1}
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchTransactions(transactionPage + 1)}
                            disabled={transactionPage >= transactionPages}
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow className="border-white/5">
                                <TableHead>日期</TableHead>
                                <TableHead>描述</TableHead>
                                <TableHead>金额</TableHead>
                                <TableHead>状态</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {transactions.length > 0 ? (
                                transactions.map((t, i) => (
                                    <TableRow key={i} className="border-white/5">
                                        <TableCell className="text-slate-400">
                                            {new Date(t.date).toLocaleDateString('zh-CN')}
                                        </TableCell>
                                        <TableCell>{t.description}</TableCell>
                                        <TableCell className="font-medium">
                                            {t.currency.toUpperCase()} {t.amount}
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={t.status === 'succeeded' ? 'default' : 'destructive'}
                                                className={t.status === 'succeeded' ? 'bg-green-600' : ''}>
                                                {t.status === 'succeeded' ? '成功' : t.status}
                                            </Badge>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center text-slate-500 py-8">
                                        暂无交易记录
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
