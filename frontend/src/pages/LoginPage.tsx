import { useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

type View = "signin" | "signup" | "confirm"

export function LoginPage() {
  const [view, setView] = useState<View>("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSignIn() {
    setError(null)
    setLoading(true)
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setError(error.message)
    setLoading(false)
  }

  async function handleSignUp() {
    setError(null)
    if (password !== confirm) {
      setError("Passwords do not match.")
      return
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.")
      return
    }
    setLoading(true)
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) setError(error.message)
    else setView("confirm")
    setLoading(false)
  }

  if (view === "confirm") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="w-full max-w-sm text-center space-y-4 p-8">
          <div className="flex justify-center">
            <div className="w-14 h-14 rounded-full bg-gray-900 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
            </div>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Check your email</h1>
          <p className="text-sm text-gray-500">
            We sent a confirmation link to <span className="font-medium text-gray-700">{email}</span>. Click the link to activate your account.
          </p>
          <button
            className="text-sm text-gray-500 hover:text-gray-700 underline"
            onClick={() => { setView("signin"); setPassword(""); setConfirm("") }}
          >
            Back to sign in
          </button>
        </div>
      </div>
    )
  }

  if (view === "signup") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="w-full max-w-sm space-y-3 p-8">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900">Create account</h1>
            <p className="text-sm text-gray-500 mt-1">Join RAG Chat</p>
          </div>
          {error && <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded">{error}</p>}
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-600">Email</label>
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-600">Password</label>
            <Input
              type="password"
              placeholder="Min. 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-gray-600">Confirm password</label>
            <Input
              type="password"
              placeholder="Re-enter your password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSignUp()}
            />
          </div>
          <Button
            className="w-full bg-gray-900 hover:bg-gray-800 text-white mt-2"
            onClick={handleSignUp}
            disabled={loading || !email || !password || !confirm}
          >
            {loading ? "Creating account..." : "Create account"}
          </Button>
          <p className="text-center text-xs text-gray-500 pt-2">
            Already have an account?{" "}
            <button
              className="text-gray-900 font-medium hover:underline"
              onClick={() => { setView("signin"); setError(null) }}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="w-full max-w-sm space-y-3 p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">Welcome back</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to RAG Chat</p>
        </div>
        {error && <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded">{error}</p>}
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-600">Email</label>
          <Input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-600">Password</label>
          <Input
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSignIn()}
          />
        </div>
        <Button
          className="w-full bg-gray-900 hover:bg-gray-800 text-white mt-2"
          onClick={handleSignIn}
          disabled={loading || !email || !password}
        >
          {loading ? "Signing in..." : "Sign in"}
        </Button>
        <p className="text-center text-xs text-gray-500 pt-2">
          Don't have an account?{" "}
          <button
            className="text-gray-900 font-medium hover:underline"
            onClick={() => { setView("signup"); setError(null) }}
          >
            Sign up
          </button>
        </p>
      </div>
    </div>
  )
}
