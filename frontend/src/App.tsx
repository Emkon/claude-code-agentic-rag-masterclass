import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { LoginPage } from "@/pages/LoginPage"
import { ChatPage } from "@/pages/ChatPage"

type Page = "chat" | "documents"

function App() {
  const { user, loading } = useAuth()
  const [activePage, setActivePage] = useState<Page>("chat")

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!user) return <LoginPage />

  return (
    <ChatPage
      activePage={activePage}
      onNavigate={setActivePage}
      userEmail={user.email}
    />
  )
}

export default App
