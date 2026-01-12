
import { useState, useEffect } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
// Removed unused imports: Label, Select, ScrollArea
import type { ExpirationDate, OptionChainResponse, OptionData } from '@/types/options';
import { useNavigate } from 'react-router-dom';

export default function Options() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    const [ticker, setTicker] = useState('AAPL');
    const [expirations, setExpirations] = useState<ExpirationDate[]>([]);
    const [selectedExpiry, setSelectedExpiry] = useState('');
    const [chain, setChain] = useState<OptionChainResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    // selectedOption removed
    const [enhancedAnalysis, setEnhancedAnalysis] = useState<any>(null);
    const [analysisLoading, setAnalysisLoading] = useState(false);

    // Fetch Expirations
    const fetchExpirations = async () => {
        if (!ticker) return;
        setLoading(true);
        setError('');
        try {
            const response = await api.get(`/options/expirations/${ticker}`);
            setExpirations(response.data.expirations);
            if (response.data.expirations.length > 0) {
                setSelectedExpiry(response.data.expirations[0].date);
            }
        } catch (err: any) {
            console.error(err);
            setError('Failed to fetch expirations');
        } finally {
            setLoading(false);
        }
    };

    // Fetch Chain
    const fetchChain = async () => {
        if (!ticker || !selectedExpiry) return;
        setLoading(true);
        try {
            const response = await api.get(`/options/chain/${ticker}/${selectedExpiry}`);
            setChain(response.data);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.error || 'Failed to fetch option chain');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user && ticker) {
            fetchExpirations();
        }
    }, [user]); // Initial load or user login

    useEffect(() => {
        if (selectedExpiry) {
            fetchChain();
        }
    }, [selectedExpiry]);

    const handleEnhancedAnalysis = async (option: OptionData) => {
        setAnalysisLoading(true);
        setEnhancedAnalysis(null);
        // setSelectedOption removed
        try {
            // Encode identifier if needed, usually safe in path
            const response = await api.get(`/options/enhanced-analysis/${ticker}/${option.identifier}`);
            setEnhancedAnalysis(response.data);
        } catch (err: any) {
            console.error(err);
            // Handle error without clearing option selection
        } finally {
            setAnalysisLoading(false);
        }
    };

    if (authLoading) return <div>Loading...</div>;
    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
                <h2 className="text-2xl font-bold">Please Log In</h2>
                <Button onClick={() => navigate('/login')}>Login to Access Options</Button>
            </div>
        );
    }

    const renderOptionTable = (options: OptionData[], type: 'CALL' | 'PUT') => {
        return (
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Strike</TableHead>
                            <TableHead>Price</TableHead>
                            <TableHead>IV</TableHead>
                            <TableHead>Delta</TableHead>
                            <TableHead>Score ({type === 'PUT' ? 'SPRV' : 'BCRV'})</TableHead>
                            <TableHead>Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {options.map((opt) => {
                            const score = type === 'PUT' ? opt.scores?.sprv : opt.scores?.bcrv;
                            const scoreColor = score && score > 1.0 ? 'text-green-600 font-bold' : '';

                            return (
                                <TableRow key={opt.identifier}>
                                    <TableCell>{opt.strike}</TableCell>
                                    <TableCell>{opt.latest_price?.toFixed(2)}</TableCell>
                                    <TableCell>{(opt.implied_vol! * 100).toFixed(1)}%</TableCell>
                                    <TableCell>{opt.delta?.toFixed(2)}</TableCell>
                                    <TableCell className={scoreColor}>{score?.toFixed(2)}</TableCell>
                                    <TableCell>
                                        <Dialog>
                                            <DialogTrigger asChild>
                                                <Button variant="outline" size="sm" onClick={() => handleEnhancedAnalysis(opt)}>
                                                    Analyze
                                                </Button>
                                            </DialogTrigger>
                                            <DialogContent className="max-w-2xl">
                                                <DialogHeader>
                                                    <DialogTitle>{opt.identifier}</DialogTitle>
                                                    <DialogDescription>
                                                        Details and Enhanced Analysis
                                                    </DialogDescription>
                                                </DialogHeader>
                                                <div className="space-y-4">
                                                    <div className="grid grid-cols-2 gap-4 border p-4 rounded bg-muted/50">
                                                        <div>
                                                            <div className="text-sm font-medium">IV Rank</div>
                                                            <div>{opt.scores?.iv_rank?.toFixed(1)}</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium">Liquidity</div>
                                                            <div>{(opt.scores?.liquidity_factor! * 100).toFixed(0)}%</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium">Prob. Assignment</div>
                                                            <div>{opt.scores?.assignment_probability?.toFixed(1)}%</div>
                                                        </div>
                                                        <div>
                                                            <div className="text-sm font-medium">Annualized Return</div>
                                                            <div className="text-green-600 font-bold">{opt.scores?.annualized_return?.toFixed(1)}%</div>
                                                        </div>
                                                    </div>

                                                    {analysisLoading ? (
                                                        <div>Loading deep analysis...</div>
                                                    ) : enhancedAnalysis ? (
                                                        <div className="space-y-2">
                                                            <h3 className="font-semibold">VRP Analysis</h3>
                                                            {enhancedAnalysis.vrp_result ? (
                                                                <div className="grid grid-cols-2 gap-4">
                                                                    <div>VRP: {enhancedAnalysis.vrp_result.vrp.toFixed(4)}</div>
                                                                    <div>Recommendation: <Badge>{enhancedAnalysis.vrp_result.recommendation.toUpperCase()}</Badge></div>
                                                                </div>
                                                            ) : (
                                                                <div>VRP data not available</div>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <div>Click Analyze to see details</div>
                                                    )}
                                                </div>
                                            </DialogContent>
                                        </Dialog>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </div>
        );
    };

    return (
        <div className="space-y-6 animate-in fade-in">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold tracking-tight">Options Chain</h1>
                <div className="flex gap-2 items-center">
                    <Input
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        className="w-32"
                        placeholder="Symbol"
                    />
                    <Button onClick={fetchExpirations} disabled={loading}>Go</Button>
                </div>
            </div>

            {error && <div className="text-red-500">{error}</div>}

            <div className="flex gap-4 items-center overflow-x-auto pb-2">
                {expirations.map(exp => (
                    <Button
                        key={exp.date}
                        variant={selectedExpiry === exp.date ? 'default' : 'outline'}
                        onClick={() => setSelectedExpiry(exp.date)}
                        className="whitespace-nowrap"
                    >
                        {exp.date} {exp.period_tag === 'm' ? '(M)' : ''}
                    </Button>
                ))}
            </div>

            {chain ? (
                <Tabs defaultValue="puts" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="calls">Calls</TabsTrigger>
                        <TabsTrigger value="puts">Puts</TabsTrigger>
                    </TabsList>
                    <TabsContent value="calls">
                        <Card>
                            <CardHeader>
                                <CardTitle>Call Options</CardTitle>
                                <CardDescription>Strategies: Covered Call, Long Call</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {renderOptionTable(chain.calls, 'CALL')}
                            </CardContent>
                        </Card>
                    </TabsContent>
                    <TabsContent value="puts">
                        <Card>
                            <CardHeader>
                                <CardTitle>Put Options</CardTitle>
                                <CardDescription>Strategies: Cash-Secured Put, Long Put</CardDescription>
                            </CardHeader>
                            <CardContent>
                                {renderOptionTable(chain.puts, 'PUT')}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            ) : (
                <div className="text-center p-12 text-muted-foreground">Select a symbol and expiration to view chain</div>
            )}
        </div>
    );
}
