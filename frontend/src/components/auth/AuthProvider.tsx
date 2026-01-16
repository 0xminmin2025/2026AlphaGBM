import { createContext, useContext, useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase'

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
