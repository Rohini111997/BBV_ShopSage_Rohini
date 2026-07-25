import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const EXAMPLES = [
  'Breathable gym socks for women under ₹600',
  'A crisp formal shirt for office wear, men, size L',
  'Casual cotton t-shirt under 700 rupees',
]

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || res.statusText)
  return data
}

function LoginBar({ onLogin, status, loading }) {
  const [customerId, setCustomerId] = useState('')

  const submit = (e) => {
    e.preventDefault()
    if (!customerId.trim()) return
    onLogin(customerId.trim())
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2 text-sm">
      <input
        value={customerId}
        onChange={(e) => setCustomerId(e.target.value)}
        placeholder="Customer ID (e.g. CUST-0028)"
        className="rounded-lg bg-black/30 border border-rose-100/20 px-3 py-1.5 text-rose-50 placeholder:text-rose-100/40 focus:outline-none focus:border-amber-300/60"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-gradient-to-r from-rose-800 to-amber-700 px-3 py-1.5 font-medium text-rose-50 disabled:opacity-50"
      >
        {loading ? 'Loading…' : 'Log in'}
      </button>
      {status && <span className="text-rose-100/70">{status}</span>}
    </form>
  )
}

function Avatar({ isUser }) {
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base ${
        isUser ? 'bg-gradient-to-br from-rose-800 to-amber-700' : 'bg-rose-50/10 border border-rose-100/15'
      }`}
    >
      {isUser ? '🧑' : '🛍️'}
    </div>
  )
}

const markdownComponents = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-4 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-4 last:mb-0">{children}</ol>,
  strong: ({ children }) => <strong className="font-semibold text-amber-200">{children}</strong>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline decoration-amber-400/60 hover:text-amber-200">
      {children}
    </a>
  ),
}

function TypingBubble() {
  return (
    <div className="flex items-end gap-2">
      <Avatar isUser={false} />
      <div className="flex items-center gap-1 rounded-2xl border border-rose-100/10 bg-rose-50/[0.06] px-4 py-3">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-rose-100/50 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-rose-100/50 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-rose-100/50" />
      </div>
    </div>
  )
}

function Bubble({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <Avatar isUser={isUser} />
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? 'whitespace-pre-wrap bg-gradient-to-r from-rose-800 to-amber-700 text-rose-50'
            : 'bg-rose-50/[0.06] border border-rose-100/10 text-rose-50/90'
        }`}
      >
        {isUser ? content : <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>}
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loginStatus, setLoginStatus] = useState('')
  const [loggingIn, setLoggingIn] = useState(false)
  const [error, setError] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleLogin = async (customerId) => {
    setLoggingIn(true)
    setError('')
    try {
      const data = await postJSON('/api/login', { customer_id: customerId })
      setLoginStatus(data.status)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoggingIn(false)
    }
  }

  const sendMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    const history = messages
    const nextMessages = [...history, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setInput('')
    setSending(true)
    setError('')
    try {
      const data = await postJSON('/api/chat', { message: trimmed, history })
      setMessages([...nextMessages, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(err.message)
      setMessages(history)
    } finally {
      setSending(false)
    }
  }

  const submit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(160deg,#2a1418_0%,#2b2012_100%)] text-rose-50">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-8">
        <header className="rounded-2xl border border-rose-100/10 bg-rose-50/[0.04] p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold">🛍️ ShopSage</h1>
            <div className="flex flex-wrap items-center gap-2">
              <LoginBar onLogin={handleLogin} status={loginStatus} loading={loggingIn} />
              {messages.length > 0 && (
                <button
                  onClick={() => setMessages([])}
                  className="rounded-lg border border-rose-100/15 px-3 py-1.5 text-sm text-rose-100/70 hover:bg-rose-50/[0.06]"
                >
                  New chat
                </button>
              )}
            </div>
          </div>
          <p className="mt-2 text-sm text-rose-100/70">
            Tell me what you're looking for and I'll find pieces you'll love.
          </p>
        </header>

        <main className="flex h-[520px] flex-col rounded-2xl border border-rose-100/10 bg-rose-50/[0.03]">
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <p className="text-center text-sm text-rose-100/40">
                👋 Ask me about shirts, socks, occasion wear…
              </p>
            )}
            {messages.map((m, i) => (
              <Bubble key={i} role={m.role} content={m.content} />
            ))}
            {sending && <TypingBubble />}
          </div>

          <form onSubmit={submit} className="flex gap-2 border-t border-rose-100/10 p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="What are you shopping for today?"
              className="flex-1 rounded-xl bg-black/30 px-4 py-2 text-sm text-rose-50 placeholder:text-rose-100/40 focus:outline-none"
            />
            <button
              type="submit"
              disabled={sending}
              className="rounded-xl bg-gradient-to-r from-rose-800 to-amber-700 px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </main>

        {error && (
          <p className="rounded-xl border border-red-400/30 bg-red-950/40 px-4 py-2 text-sm text-red-200">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => sendMessage(ex)}
              className="rounded-full border border-rose-100/15 bg-rose-50/[0.04] px-3 py-1 text-xs text-rose-100/70 hover:bg-rose-50/[0.08]"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
