import { useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import type { User } from "@/types"

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const u = data.session?.user
      setUser(u ? { id: u.id, email: u.email ?? "" } : null)
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      const u = session?.user
      setUser(u ? { id: u.id, email: u.email ?? "" } : null)
    })

    return () => listener.subscription.unsubscribe()
  }, [])

  return { user, loading }
}
