import { useState, useEffect } from 'react'
import { AuthService, AuthUser } from '@/lib/auth'
import { Session } from '@supabase/supabase-js'

export interface UseAuthReturn {
    user: AuthUser | null
    session: Session | null
    loading: boolean
    signIn: (email: string, password: string) => Promise<void>
    signUp: (email: string, password: string) => Promise<void>
    signInWithMagicLink: (email: string) => Promise<void>
    signOut: () => Promise<void>
    resetPassword: (email: string) => Promise<void>
    updatePassword: (password: string) => Promise<void>
}

export function useAuth(): UseAuthReturn {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [session, setSession] = useState<Session | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Get initial session
        const initializeAuth = async () => {
            try {
                const currentSession = await AuthService.getCurrentSession()
                setSession(currentSession)
                setUser(currentSession?.user as AuthUser | null)
            } catch (error) {
                console.error('Auth initialization error:', error)
            } finally {
                setLoading(false)
            }
        }

        initializeAuth()

        // Listen for auth changes
        const { data: { subscription } } = AuthService.onAuthStateChange((user, session) => {
            setUser(user)
            setSession(session)
            setLoading(false)
        })

        return () => subscription.unsubscribe()
    }, [])

    const signIn = async (email: string, password: string) => {
        setLoading(true)
        try {
            await AuthService.signIn(email, password)
        } finally {
            setLoading(false)
        }
    }

    const signUp = async (email: string, password: string) => {
        setLoading(true)
        try {
            await AuthService.signUp(email, password)
        } finally {
            setLoading(false)
        }
    }

    const signInWithMagicLink = async (email: string) => {
        setLoading(true)
        try {
            await AuthService.signInWithMagicLink(email)
        } finally {
            setLoading(false)
        }
    }

    const signOut = async () => {
        setLoading(true)
        try {
            await AuthService.signOut()
        } finally {
            setLoading(false)
        }
    }

    const resetPassword = async (email: string) => {
        await AuthService.resetPassword(email)
    }

    const updatePassword = async (password: string) => {
        await AuthService.updatePassword(password)
    }

    return {
        user,
        session,
        loading,
        signIn,
        signUp,
        signInWithMagicLink,
        signOut,
        resetPassword,
        updatePassword,
    }
}