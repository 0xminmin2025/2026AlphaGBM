
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
// Tabs import removed

export default function Profile() {
    const { user } = useAuth();
    const [credits, setCredits] = useState<any>(null);
    const [transactions, setTransactions] = useState<any[]>([]);

    useEffect(() => {
        if (user) {
            api.get('/payment/credits').then(res => setCredits(res.data));
            api.get('/payment/transactions').then(res => setTransactions(res.data.transactions));
        }
    }, [user]);

    if (!user) return <div>Please login</div>;

    return (
        <div className="space-y-8 animate-in fade-in">
            <h1 className="text-3xl font-bold tracking-tight">Account Profile</h1>

            <div className="grid gap-8 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>User Details</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div>Email: {user.email}</div>
                        <div>ID: {user.id}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Subscription & Credits</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {credits ? (
                            <>
                                <div className="flex justify-between items-center">
                                    <span>Plan:</span>
                                    <Badge variant={credits.subscription.has_subscription ? 'default' : 'secondary'}>
                                        {credits.subscription.plan_tier.toUpperCase()}
                                    </Badge>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span>Total Credits:</span>
                                    <span className="font-bold text-xl">{credits.total_credits}</span>
                                </div>
                                <div className="flex justify-between items-center text-sm text-muted-foreground">
                                    <span>Daily Free Quota:</span>
                                    <span>{credits.daily_free.remaining} / {credits.daily_free.quota} remaining</span>
                                </div>
                            </>
                        ) : (
                            <div>Loading credits...</div>
                        )}
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Payment History</CardTitle>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead>Amount</TableHead>
                                <TableHead>Status</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {transactions.length > 0 ? (
                                transactions.map((t: any, i: number) => (
                                    <TableRow key={i}>
                                        <TableCell>{new Date(t.date).toLocaleDateString()}</TableCell>
                                        <TableCell>{t.description}</TableCell>
                                        <TableCell>{t.currency.toUpperCase()} {t.amount}</TableCell>
                                        <TableCell>
                                            <Badge variant={t.status === 'succeeded' ? 'default' : 'destructive'}>
                                                {t.status}
                                            </Badge>
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                <TableRow>
                                    <TableCell colSpan={4} className="text-center">No transactions found</TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
