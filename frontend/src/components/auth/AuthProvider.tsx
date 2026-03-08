import { createContext, useContext, useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

const MOCK_AUTH = import.meta.env.VITE_MOCK_AUTH === 'true'

const MOCK_USER = {
    id: 'dev-test-user-001',
    email: 'dev@alphagbm.test',
    role: 'authenticated',
    aud: 'authenticated',
    app_metadata: { provider: 'email' },
    user_metadata: { name: 'Dev Tester' },
    created_at: '2025-01-01T00:00:00.000Z',
} as unknown as User

const MOCK_SESSION = {
    access_token: 'mock-dev-token',
    refresh_token: 'mock-refresh-token',
    expires_in: 86400,
    expires_at: Math.floor(Date.now() / 1000) + 86400,
    token_type: 'bearer',
    user: MOCK_USER,
} as unknown as Session

type AuthContextType = {
    session: Session | null
    user: User | null
    loading: boolean
    signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [session, setSession] = useState<Session | null>(null)
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (MOCK_AUTH) {
            console.warn('[DEV] Mock auth enabled — auto-login as dev@alphagbm.test')
            setSession(MOCK_SESSION)
            setUser(MOCK_USER)
            setLoading(false)
            return
        }

        // Set a timeout to prevent infinite loading
        const timeoutId = setTimeout(() => {
            if (loading) {
                console.warn("Auth loading timeout, setting loading to false");
                setLoading(false);
            }
        }, 5000); // 5 second timeout

        supabase.auth.getSession().then(({ data: { session } }) => {
            console.log("Supabase Session:", session);
            setSession(session)
            setUser(session?.user ?? null)
            setLoading(false)
            clearTimeout(timeoutId);
        }).catch((error) => {
            console.error("Error getting session:", error);
            setLoading(false);
            clearTimeout(timeoutId);
        })

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            console.log("Auth State Change:", _event, session);
            setSession(session)
            setUser(session?.user ?? null)
            setLoading(false)
            clearTimeout(timeoutId);
        })

        return () => {
            clearTimeout(timeoutId);
            subscription.unsubscribe()
        }
    }, [])

    const signOut = async () => {
        if (MOCK_AUTH) {
            setSession(null)
            setUser(null)
            return
        }
        await supabase.auth.signOut()
    }

    return (
        <AuthContext.Provider value={{ session, user, loading, signOut }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
