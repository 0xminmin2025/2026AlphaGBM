import { useState, useEffect, useRef, useCallback } from 'react';
import { searchStocks } from '@/lib/stockData';
import type { StockInfo } from '@/lib/stockData';
import api from '@/lib/api';

interface UseStockSearchOptions {
    limit?: number;
    excludeTickers?: string[];
}

interface UseStockSearchReturn {
    query: string;
    setQuery: (q: string) => void;
    results: StockInfo[];
    isSearching: boolean;
}

export function useStockSearch({
    limit = 8,
    excludeTickers = [],
}: UseStockSearchOptions = {}): UseStockSearchReturn {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<StockInfo[]>([]);
    const [isSearching, setIsSearching] = useState(false);

    const abortRef = useRef<AbortController | null>(null);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    // Keep a ref so the debounced callback always sees the latest excludeTickers
    const excludeRef = useRef<string[]>(excludeTickers);
    excludeRef.current = excludeTickers;

    const mergeResults = useCallback(
        (local: StockInfo[], remote: StockInfo[], exclude: string[]): StockInfo[] => {
            const seen = new Set(exclude.map(t => t.toUpperCase()));
            const merged: StockInfo[] = [];

            for (const s of local) {
                const key = s.ticker.toUpperCase();
                if (!seen.has(key)) {
                    seen.add(key);
                    merged.push(s);
                }
            }
            for (const s of remote) {
                const key = s.ticker.toUpperCase();
                if (!seen.has(key)) {
                    seen.add(key);
                    merged.push(s);
                }
            }
            return merged.slice(0, limit);
        },
        [limit],
    );

    useEffect(() => {
        // Cancel any pending API call
        if (timerRef.current) clearTimeout(timerRef.current);
        if (abortRef.current) abortRef.current.abort();

        const trimmed = query.trim();
        if (!trimmed) {
            setResults([]);
            setIsSearching(false);
            return;
        }

        // Instant local results
        const local = searchStocks(trimmed, limit);
        const filtered = local.filter(
            s => !excludeRef.current.some(t => t.toUpperCase() === s.ticker.toUpperCase()),
        );
        setResults(filtered);

        // Debounced API call (300ms)
        setIsSearching(true);
        timerRef.current = setTimeout(() => {
            const controller = new AbortController();
            abortRef.current = controller;

            api
                .get('/stock/search', {
                    params: { q: trimmed, limit },
                    signal: controller.signal,
                })
                .then(res => {
                    const remote: StockInfo[] = (res.data?.results ?? []).map(
                        (r: Record<string, string>) => ({
                            ticker: r.ticker ?? '',
                            nameCn: r.nameCn ?? '',
                            nameEn: r.nameEn ?? '',
                            pinyin: r.pinyin ?? '',
                            market: (r.market ?? 'US') as StockInfo['market'],
                        }),
                    );
                    // Re-compute local inside callback to have freshest exclude list
                    const freshLocal = searchStocks(trimmed, limit).filter(
                        s =>
                            !excludeRef.current.some(
                                t => t.toUpperCase() === s.ticker.toUpperCase(),
                            ),
                    );
                    setResults(mergeResults(freshLocal, remote, excludeRef.current));
                })
                .catch(err => {
                    if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
                    // Graceful degradation: keep local results
                })
                .finally(() => {
                    setIsSearching(false);
                });
        }, 300);

        return () => {
            if (timerRef.current) clearTimeout(timerRef.current);
            if (abortRef.current) abortRef.current.abort();
        };
    }, [query, limit, mergeResults]);

    return { query, setQuery, results, isSearching };
}
