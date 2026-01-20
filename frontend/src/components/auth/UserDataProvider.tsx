import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './AuthProvider';
import api from '@/lib/api';

// Types
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

type CreditsData = {
    total_credits: number;
    subscription: {
        has_subscription: boolean;
        plan_tier: string;
        status: string;
    };
    daily_free: {
        remaining: number;
        quota: number;
    };
};

type PricingData = {
    plans: {
        free: { name: string; features: string[]; credits?: string; price?: number };
        plus: { 
            name: string; 
            features: string[]; 
            monthly: { price: number; credits?: number; currency?: string; period?: string };
            yearly?: { price: number; credits?: number; currency?: string; period?: string; savings?: string };
        };
        pro: { 
            name: string; 
            features: string[]; 
            monthly: { price: number; credits?: number; currency?: string; period?: string };
            yearly?: { price: number; credits?: number; currency?: string; period?: string; savings?: string };
        };
        enterprise?: { name: string; features: string[]; price?: number | null; credits?: string };
    };
    topups: {
        '100': { name: string; price: number; validity: string; currency?: string };
    };
};

type UserDataContextType = {
    // Data
    credits: CreditsData | null;
    pricing: PricingData | null;
    transactions: Transaction[];
    usageLogs: UsageLog[];

    // Pagination info for transactions & usage logs
    transactionPagination: {
        current_page: number;
        total_pages: number;
        has_next: boolean;
        has_prev: boolean;
    };
    usagePagination: {
        current_page: number;
        total_pages: number;
        total_records: number;
        has_next: boolean;
        has_prev: boolean;
    };

    // Loading states
    isInitialLoading: boolean;
    creditsLoading: boolean;
    pricingLoading: boolean;
    transactionsLoading: boolean;
    usageLoading: boolean;

    // Manual refresh functions
    refreshCredits: () => Promise<void>;
    refreshPricing: () => Promise<void>;
    refreshTransactions: (page?: number) => Promise<void>;
    refreshUsageHistory: (page?: number) => Promise<void>;
    refreshAll: () => Promise<void>;

    // Navigation functions
    fetchTransactionsPage: (page: number) => Promise<void>;
    fetchUsagePage: (page: number) => Promise<void>;
};

const UserDataContext = createContext<UserDataContextType | undefined>(undefined);

export function UserDataProvider({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();

    // Data state
    const [credits, setCredits] = useState<CreditsData | null>(null);
    const [pricing, setPricing] = useState<PricingData | null>(null);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [usageLogs, setUsageLogs] = useState<UsageLog[]>([]);

    // Pagination state
    const [transactionPagination, setTransactionPagination] = useState({
        current_page: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
    });
    const [usagePagination, setUsagePagination] = useState({
        current_page: 1,
        total_pages: 1,
        total_records: 0,
        has_next: false,
        has_prev: false,
    });

    // Loading states
    const [isInitialLoading, setIsInitialLoading] = useState(false);
    const [creditsLoading, setCreditsLoading] = useState(false);
    const [pricingLoading, setPricingLoading] = useState(false);
    const [transactionsLoading, setTransactionsLoading] = useState(false);
    const [usageLoading, setUsageLoading] = useState(false);

    // Cache flags to prevent duplicate API calls
    const dataCache = useRef({
        credits: false,
        pricing: false,
        transactions_page_1: false,
        usage_page_1: false,
    });

    // Fetch credits data
    const refreshCredits = useCallback(async () => {
        if (!user || creditsLoading) return;

        setCreditsLoading(true);
        try {
            const response = await api.get('/payment/credits');
            setCredits(response.data);
            dataCache.current.credits = true;
        } catch (error) {
            console.error('Failed to fetch credits:', error);
        } finally {
            setCreditsLoading(false);
        }
    }, [user, creditsLoading]);

    // Fetch pricing data
    const refreshPricing = useCallback(async () => {
        if (pricingLoading) return;

        setPricingLoading(true);
        try {
            const response = await api.get('/payment/pricing');
            setPricing(response.data);
            dataCache.current.pricing = true;
        } catch (error) {
            console.error('Failed to fetch pricing:', error);
        } finally {
            setPricingLoading(false);
        }
    }, [pricingLoading]);

    // Fetch transactions
    const refreshTransactions = useCallback(async (page = 1) => {
        if (!user || transactionsLoading) return;

        setTransactionsLoading(true);
        try {
            const response = await api.get(`/payment/transactions?page=${page}&per_page=10`);
            setTransactions(response.data.transactions || []);
            setTransactionPagination({
                current_page: page,
                total_pages: response.data.pages || 1,
                has_next: page < (response.data.pages || 1),
                has_prev: page > 1,
            });

            if (page === 1) {
                dataCache.current.transactions_page_1 = true;
            }
        } catch (error) {
            console.error('Failed to fetch transactions:', error);
        } finally {
            setTransactionsLoading(false);
        }
    }, [user, transactionsLoading]);

    // Fetch usage history
    const refreshUsageHistory = useCallback(async (page = 1) => {
        if (!user || usageLoading) return;

        setUsageLoading(true);
        try {
            const response = await api.get(`/payment/usage-history?page=${page}&per_page=10`);
            setUsageLogs(response.data.usage_logs || []);
            setUsagePagination({
                current_page: page,
                total_pages: response.data.pages || 1,
                total_records: response.data.total || 0,
                has_next: page < (response.data.pages || 1),
                has_prev: page > 1,
            });

            if (page === 1) {
                dataCache.current.usage_page_1 = true;
            }
        } catch (error) {
            console.error('Failed to fetch usage history:', error);
        } finally {
            setUsageLoading(false);
        }
    }, [user, usageLoading]);

    // Navigation functions for pagination
    const fetchTransactionsPage = useCallback(async (page: number) => {
        await refreshTransactions(page);
    }, [refreshTransactions]);

    const fetchUsagePage = useCallback(async (page: number) => {
        await refreshUsageHistory(page);
    }, [refreshUsageHistory]);

    // Refresh all data
    const refreshAll = useCallback(async () => {
        const promises = [
            refreshPricing(), // Always fetch pricing as it's not user-specific
        ];

        if (user) {
            promises.push(
                refreshCredits(),
                refreshTransactions(1),
                refreshUsageHistory(1)
            );
        }

        await Promise.allSettled(promises);
    }, [user, refreshCredits, refreshPricing, refreshTransactions, refreshUsageHistory]);

    // Auto-fetch data when user changes
    useEffect(() => {
        if (user) {
            // Check if we need to do initial loading (any critical data is missing)
            const needsInitialLoading = !dataCache.current.credits || !dataCache.current.pricing;

            if (needsInitialLoading) {
                setIsInitialLoading(true);
            }

            // Only fetch credits if not already cached
            if (!dataCache.current.credits && !creditsLoading) {
                refreshCredits();
            }

            // Only fetch transactions if not already cached
            if (!dataCache.current.transactions_page_1 && !transactionsLoading) {
                refreshTransactions(1);
            }

            // Only fetch usage history if not already cached
            if (!dataCache.current.usage_page_1 && !usageLoading) {
                refreshUsageHistory(1);
            }
        } else {
            // Clear user-specific data when user logs out
            setIsInitialLoading(false);
            setCredits(null);
            setTransactions([]);
            setUsageLogs([]);
            setTransactionPagination({ current_page: 1, total_pages: 1, has_next: false, has_prev: false });
            setUsagePagination({ current_page: 1, total_pages: 1, total_records: 0, has_next: false, has_prev: false });

            // Clear cache flags for user-specific data
            dataCache.current.credits = false;
            dataCache.current.transactions_page_1 = false;
            dataCache.current.usage_page_1 = false;
        }
    }, [user]); // Remove function dependencies to avoid infinite loops

    // Auto-fetch pricing on mount (not user-dependent)
    useEffect(() => {
        if (!dataCache.current.pricing && !pricingLoading) {
            refreshPricing();
        }
    }, []); // Only run once on mount

    // Monitor when initial loading should end
    useEffect(() => {
        if (isInitialLoading && user) {
            // Check if all critical data is loaded
            const hasCredits = credits !== null;
            const hasPricing = pricing !== null;
            const notLoading = !creditsLoading && !pricingLoading;

            if (hasCredits && hasPricing && notLoading) {
                setIsInitialLoading(false);
            }
        }
    }, [isInitialLoading, user, credits, pricing, creditsLoading, pricingLoading]);

    const value: UserDataContextType = {
        // Data
        credits,
        pricing,
        transactions,
        usageLogs,

        // Pagination
        transactionPagination,
        usagePagination,

        // Loading states
        isInitialLoading,
        creditsLoading,
        pricingLoading,
        transactionsLoading,
        usageLoading,

        // Refresh functions
        refreshCredits,
        refreshPricing,
        refreshTransactions,
        refreshUsageHistory,
        refreshAll,

        // Navigation
        fetchTransactionsPage,
        fetchUsagePage,
    };

    return (
        <UserDataContext.Provider value={value}>
            {children}
        </UserDataContext.Provider>
    );
}

export function useUserData() {
    const context = useContext(UserDataContext);
    if (context === undefined) {
        throw new Error('useUserData must be used within a UserDataProvider');
    }
    return context;
}