import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'

const API = ''  // same origin — Vite proxy forwards /api/* to :8000

const EXAMPLES = [
  'Breathable gym socks for women under ₹600',
  'A crisp formal shirt for office wear, men, size L',
  'Casual cotton t-shirt under 700 rupees',
]

const THEME_KEY = 'shopsage-theme'

async function postJSON(url, body) {
  const res = await fetch(API + url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || res.statusText)
  return data
}

async function getJSON(url) {
  const res = await fetch(API + url)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || res.statusText)
  return data
}

// ── theme ─────────────────────────────────────────────────────────────────────

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || 'dark')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))]
}

// ── small shared components ───────────────────────────────────────────────────

function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-stone-300 bg-white/70 text-base transition hover:scale-110 hover:shadow-md dark:border-rose-100/15 dark:bg-rose-50/[0.06]"
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
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
        className="rounded-lg border border-stone-300 bg-white/70 px-3 py-1.5 text-stone-800 placeholder:text-stone-400 focus:outline-none focus:border-amber-500 dark:border-rose-100/20 dark:bg-black/30 dark:text-rose-50 dark:placeholder:text-rose-100/40 dark:focus:border-amber-300/60"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-gradient-to-r from-rose-700 to-amber-600 px-3 py-1.5 font-medium text-white shadow-sm transition hover:scale-105 hover:shadow-lg hover:shadow-rose-500/30 disabled:opacity-50 disabled:hover:scale-100"
      >
        {loading ? 'Loading…' : 'Log in'}
      </button>
      {status && <span className="text-stone-500 dark:text-rose-100/70">{status}</span>}
    </form>
  )
}

function Avatar({ isUser }) {
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base shadow-sm ${
        isUser
          ? 'bg-gradient-to-br from-rose-700 to-amber-600 text-white'
          : 'border border-stone-200 bg-stone-100 dark:border-rose-100/15 dark:bg-rose-50/10'
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
  strong: ({ children }) => <strong className="font-semibold text-amber-600 dark:text-amber-200">{children}</strong>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="underline decoration-amber-500/60 hover:text-amber-600 dark:decoration-amber-400/60 dark:hover:text-amber-200"
    >
      {children}
    </a>
  ),
}

function TypingBubble() {
  return (
    <div className="flex animate-message-in items-end gap-2">
      <Avatar isUser={false} />
      <div className="flex items-center gap-1 rounded-2xl border border-stone-200 bg-stone-100 px-4 py-3 dark:border-rose-100/10 dark:bg-rose-50/[0.06]">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.3s] dark:bg-rose-100/50" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-stone-400 [animation-delay:-0.15s] dark:bg-rose-100/50" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-stone-400 dark:bg-rose-100/50" />
      </div>
    </div>
  )
}

function ProductCard({ product, onSelect }) {
  const [imgOk, setImgOk] = useState(true)
  const imageSrc = product.image || (product.sku ? `images/${product.sku}.png` : '')
  const hasImage = imageSrc && imgOk
  const fullSrc = imageSrc.startsWith('/') ? imageSrc : `/${imageSrc}`

  return (
    <div className="w-32 shrink-0 overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg dark:border-rose-100/10 dark:bg-rose-50/[0.05]">
      <button
        type="button"
        onClick={() => onSelect(product)}
        className="flex h-32 w-32 cursor-pointer items-center justify-center bg-stone-100 dark:bg-black/20"
      >
        {hasImage ? (
          <img
            src={fullSrc}
            alt={product.title}
            className="h-full w-full object-cover"
            onError={() => setImgOk(false)}
          />
        ) : (
          <span className="text-2xl">🛍️</span>
        )}
      </button>
      <div className="p-2">
        <p className="truncate text-xs font-medium text-stone-800 dark:text-rose-50">{product.title}</p>
        <p className="truncate text-[11px] text-stone-500 dark:text-rose-100/60">{product.brand}</p>
        {product.price_inr != null && (
          <p className="mt-0.5 text-xs font-semibold text-amber-600 dark:text-amber-200">INR {product.price_inr}</p>
        )}
      </div>
    </div>
  )
}

function ProductRow({ products, onSelectProduct }) {
  if (!products?.length) return null
  return (
    <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
      {products.map((p) => (
        <ProductCard key={p.sku} product={p} onSelect={onSelectProduct} />
      ))}
    </div>
  )
}

function Bubble({ role, content, products, onSelectProduct }) {
  const isUser = role === 'user'
  return (
    <div className={`flex animate-message-in items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <Avatar isUser={isUser} />
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm ${
          isUser
            ? 'whitespace-pre-wrap bg-gradient-to-r from-rose-700 to-amber-600 text-white'
            : 'border border-stone-200 bg-white text-stone-800 dark:border-rose-100/10 dark:bg-rose-50/[0.06] dark:text-rose-50/90'
        }`}
      >
        {isUser ? content : <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>}
        {!isUser && <ProductRow products={products} onSelectProduct={onSelectProduct} />}
      </div>
    </div>
  )
}

function ProductDetailModal({ product, onClose }) {
  const [modalImgOk, setModalImgOk] = useState(true)

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!product) return null
  const attributes = Object.entries(product.attributes || {})
  const imageSrc = product.image || (product.sku ? `images/${product.sku}.png` : '')
  const hasImage = imageSrc && modalImgOk
  const fullSrc = imageSrc.startsWith('/') ? imageSrc : `/${imageSrc}`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-2xl sm:flex-row dark:border-rose-100/15 dark:bg-[#2a1418]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-center bg-stone-100 dark:bg-black/30 sm:w-1/2 min-h-[160px]">
          {hasImage ? (
            <img
              src={fullSrc}
              alt={product.title}
              className="max-h-[40vh] w-full object-contain sm:max-h-[85vh]"
              onError={() => setModalImgOk(false)}
            />
          ) : (
            <span className="text-5xl">🛍️</span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <button
            type="button"
            onClick={onClose}
            className="float-right rounded-full border border-stone-300 px-2.5 py-1 text-xs text-stone-500 transition hover:scale-110 hover:bg-stone-100 dark:border-rose-100/15 dark:text-rose-100/70 dark:hover:bg-rose-50/[0.08]"
          >
            ✕
          </button>
          <h2 className="text-lg font-bold text-stone-900 dark:text-rose-50">{product.title}</h2>
          <p className="text-sm text-stone-500 dark:text-rose-100/60">
            {product.brand}
            {product.item_type ? ` · ${product.item_type}` : ''}
          </p>
          {product.price_inr != null && (
            <p className="mt-2 text-xl font-semibold text-amber-600 dark:text-amber-200">INR {product.price_inr}</p>
          )}
          {product.description && (
            <p className="mt-3 text-sm leading-relaxed text-stone-700 dark:text-rose-100/90">{product.description}</p>
          )}
          {product.sizes_available && (
            <p className="mt-3 text-sm">
              <span className="text-stone-400 dark:text-rose-100/50">Sizes: </span>
              {product.sizes_available}
            </p>
          )}
          {product.colors_available && (
            <p className="mt-1 text-sm">
              <span className="text-stone-400 dark:text-rose-100/50">Colors: </span>
              {product.colors_available}
            </p>
          )}
          {attributes.length > 0 && (
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              {attributes.map(([key, value]) => (
                <div key={key} className="contents">
                  <dt className="capitalize text-stone-400 dark:text-rose-100/50">{key}</dt>
                  <dd className="text-stone-800 dark:text-rose-50/90">{String(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Observability Dashboard ───────────────────────────────────────────────────

function Badge({ label, value, variant = 'blue' }) {
  const colors = {
    blue:   'bg-blue-600/80 text-white',
    green:  'bg-emerald-600/80 text-white',
    red:    'bg-red-600/80 text-white',
    amber:  'bg-amber-500/80 text-white',
    purple: 'bg-purple-600/80 text-white',
    slate:  'bg-stone-500/70 text-white dark:bg-rose-100/10 dark:text-rose-100/80',
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[variant]}`}>
      {label}: <strong>{value}</strong>
    </span>
  )
}

function DashSection({ icon, title, children }) {
  return (
    <div className="rounded-xl border border-rose-100/10 bg-black/20 p-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-rose-100/40">
        {icon} {title}
      </p>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  )
}

function ObservabilityDashboard({ data, loading, lastUpdated, onReset }) {
  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-6 text-sm text-rose-100/50">
        Loading dashboard…
      </div>
    )
  }

  if (!data || data.num_turns === 0) {
    return (
      <div className="flex items-center justify-center py-6 text-sm text-rose-100/40">
        No turns yet — send a message to start collecting metrics.
      </div>
    )
  }

  const tc  = data.tool_calls  || {}
  const gr  = data.guardrails  || {}
  const ca  = data.cache       || {}
  const la  = data.latency     || {}
  const ec  = data.edge_cases  || {}
  const ev  = data.eval        || {}

  const failRate  = tc.failure_rate_pct ?? 0
  const hitRate   = ca.hit_rate_pct     ?? 0
  const passRate  = ev.pass_rate_pct    ?? 0

  return (
    <div className="space-y-2.5">
      {/* header row */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-rose-100/50">
          Turns: <strong className="text-rose-50">{data.num_turns}</strong>
          {lastUpdated && (
            <span className="ml-2 text-[10px] text-rose-100/30">
              updated {lastUpdated}
            </span>
          )}
        </span>
        <button
          onClick={onReset}
          className="rounded-md border border-rose-100/10 px-2 py-0.5 text-[11px] text-rose-100/50 transition hover:border-rose-100/30 hover:text-rose-100/80"
        >
          Reset
        </button>
      </div>

      {/* Tool Calls */}
      <DashSection icon="🔧" title="Tool Calls">
        <Badge label="Total"    value={tc.total    ?? 0} variant="blue" />
        <Badge label="Failures" value={tc.failures  ?? 0} variant={failRate > 10 ? 'red' : 'green'} />
        <Badge label="Fail rate" value={`${failRate.toFixed(1)}%`} variant={failRate > 10 ? 'red' : 'green'} />
      </DashSection>

      {/* Guardrails */}
      <DashSection icon="🛡️" title="Guardrails">
        <Badge label="Triggered" value={gr.total_triggers ?? 0} variant="purple" />
        {Object.entries(gr.by_rule || {}).map(([rule, cnt]) => (
          <Badge key={rule} label={rule} value={`${cnt}×`} variant="purple" />
        ))}
        {(gr.total_triggers ?? 0) === 0 && (
          <span className="text-xs text-rose-100/30">No triggers this session</span>
        )}
      </DashSection>

      {/* Cache */}
      <DashSection icon="⚡" title="Retrieval Cache">
        <Badge label="Hits"     value={ca.hits   ?? 0} variant={hitRate > 50 ? 'green' : 'amber'} />
        <Badge label="Misses"   value={ca.misses ?? 0} variant="amber" />
        <Badge label="Hit rate" value={`${hitRate.toFixed(1)}%`} variant={hitRate > 50 ? 'green' : 'amber'} />
      </DashSection>

      {/* Latency */}
      <DashSection icon="⏱️" title="Latency">
        <Badge label="Avg turn" value={`${la.avg_turn_ms ?? 0} ms`} variant="blue" />
        {Object.entries(la.avg_generate_ms_by_path || {}).map(([path, ms]) => (
          <Badge key={path} label={path} value={`${ms} ms`} variant="slate" />
        ))}
      </DashSection>

      {/* Edge Cases */}
      {ec && (
        <DashSection icon="⚠️" title="Edge Cases">
          <Badge label="API timeouts"  value={ec.inventory_timeouts?.count   ?? 0} variant={ec.inventory_timeouts?.count   > 0 ? 'red'    : 'slate'} />
          <Badge label="No-match"      value={ec.no_catalog_match?.count     ?? 0} variant={ec.no_catalog_match?.count     > 0 ? 'amber'  : 'slate'} />
          <Badge label="Ambiguous ref" value={ec.ambiguous_references?.count ?? 0} variant={ec.ambiguous_references?.count > 0 ? 'purple' : 'slate'} />
        </DashSection>
      )}

      {/* Eval */}
      {ev.available ? (
        <DashSection icon="📊" title="Eval Scores">
          <Badge label="Baseline" value={ev.baseline_score ?? '—'} variant="slate" />
          <Badge label="Improved" value={ev.improved_score ?? '—'} variant="green" />
          {ev.delta != null && (
            <Badge label="Δ" value={ev.delta > 0 ? `+${ev.delta}` : ev.delta} variant={ev.delta > 0 ? 'green' : 'red'} />
          )}
          <Badge label="Pass rate" value={`${passRate.toFixed(1)}%`} variant={passRate >= 70 ? 'green' : 'red'} />
          {Object.entries(ev.failure_by_category || {}).map(([cat, cnt]) => (
            <Badge key={cat} label={cat} value={`${cnt} fails`} variant="slate" />
          ))}
        </DashSection>
      ) : (
        <p className="text-[11px] text-rose-100/30 px-1">{ev.note}</p>
      )}
    </div>
  )
}

// ── main app ──────────────────────────────────────────────────────────────────

export default function App() {
  const [theme, toggleTheme] = useTheme()
  const [messages, setMessages]         = useState([])
  const [input, setInput]               = useState('')
  const [sending, setSending]           = useState(false)
  const [loginStatus, setLoginStatus]   = useState('')
  const [loggingIn, setLoggingIn]       = useState(false)
  const [error, setError]               = useState('')
  const [previewProduct, setPreviewProduct] = useState(null)

  // Dashboard state
  const [dashOpen, setDashOpen]         = useState(false)
  const [dashData, setDashData]         = useState(null)
  const [dashLoading, setDashLoading]   = useState(false)
  const [dashUpdated, setDashUpdated]   = useState('')
  const dashTimerRef                    = useRef(null)

  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  // ── Dashboard polling ────────────────────────────────────────────────────
  const fetchDashboard = useCallback(async () => {
    setDashLoading(true)
    try {
      const data = await getJSON('/api/dashboard')
      setDashData(data)
      setDashUpdated(new Date().toLocaleTimeString())
    } catch {
      // silently ignore — dashboard is non-critical
    } finally {
      setDashLoading(false)
    }
  }, [])

  useEffect(() => {
    if (dashOpen) {
      fetchDashboard()
      dashTimerRef.current = setInterval(fetchDashboard, 10_000)
    } else {
      clearInterval(dashTimerRef.current)
    }
    return () => clearInterval(dashTimerRef.current)
  }, [dashOpen, fetchDashboard])

  // Also refresh dashboard after every agent turn
  const refreshDashAfterTurn = useCallback(() => {
    if (dashOpen) fetchDashboard()
  }, [dashOpen, fetchDashboard])

  const handleDashReset = async () => {
    await postJSON('/api/dashboard/reset', {})
    setDashData(null)
    setDashUpdated('')
  }

  // ── Auth ─────────────────────────────────────────────────────────────────
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

  // ── Chat ─────────────────────────────────────────────────────────────────
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
      setMessages([
        ...nextMessages,
        { role: 'assistant', content: data.reply, products: data.products },
      ])
      refreshDashAfterTurn()
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

  const handleNewChat = async () => {
    setMessages([])
    await postJSON('/api/dashboard/reset', {}).catch(() => {})
    setDashData(null)
    setDashUpdated('')
  }

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-[linear-gradient(160deg,#fff7f2_0%,#fef6e8_100%)] text-stone-800 transition-colors duration-300 dark:bg-[linear-gradient(160deg,#2a1418_0%,#2b2012_100%)] dark:text-rose-50">
      {/* background blobs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="animate-blob absolute -top-24 -left-24 h-72 w-72 rounded-full bg-rose-400/20 blur-3xl dark:bg-rose-700/20" />
        <div className="animate-blob animation-delay-4000 absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-amber-400/20 blur-3xl dark:bg-amber-600/20" />
      </div>

      {/* header */}
      <header className="relative z-10 shrink-0 border-b border-stone-200 bg-white/70 px-6 py-4 backdrop-blur-sm dark:border-rose-100/10 dark:bg-rose-50/[0.04]">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="bg-gradient-to-r from-rose-700 via-amber-600 to-rose-700 bg-clip-text text-2xl font-extrabold text-transparent dark:from-rose-300 dark:via-amber-200 dark:to-rose-300">
              🛍️ ShopSage
            </h1>
            <p className="mt-1 text-sm text-stone-500 dark:text-rose-100/70">
              Tell me what you're looking for and I'll find pieces you'll love.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LoginBar onLogin={handleLogin} status={loginStatus} loading={loggingIn} />
            {messages.length > 0 && (
              <button
                onClick={handleNewChat}
                className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-600 transition hover:bg-stone-100 dark:border-rose-100/15 dark:text-rose-100/70 dark:hover:bg-rose-50/[0.06]"
              >
                New chat
              </button>
            )}
            {/* Dashboard toggle */}
            <button
              id="dashboard-toggle"
              onClick={() => setDashOpen((o) => !o)}
              title="Observability Dashboard"
              className={`flex h-9 w-9 items-center justify-center rounded-full border text-base transition hover:scale-110 hover:shadow-md ${
                dashOpen
                  ? 'border-amber-500 bg-amber-500/20 text-amber-600 dark:border-amber-300/60 dark:bg-amber-400/10 dark:text-amber-200'
                  : 'border-stone-300 bg-white/70 dark:border-rose-100/15 dark:bg-rose-50/[0.06]'
              }`}
            >
              📊
            </button>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </div>
      </header>

      {/* main layout — side-by-side when dashboard is open */}
      <div className="relative z-10 mx-auto flex w-full min-h-0 max-w-5xl flex-1 overflow-hidden">

        {/* chat column */}
        <main className={`flex min-h-0 flex-1 flex-col px-4 transition-all duration-300 ${dashOpen ? 'mr-[320px]' : ''}`}>
          <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto py-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center gap-4 pt-6 text-center">
                <p className="text-sm text-stone-500 dark:text-rose-100/40">
                  👋 Ask me about shirts, socks, occasion wear…
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((ex) => (
                    <button
                      key={ex}
                      onClick={() => sendMessage(ex)}
                      className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs text-stone-600 shadow-sm transition hover:scale-105 hover:shadow-md dark:border-rose-100/15 dark:bg-rose-50/[0.04] dark:text-rose-100/70 dark:hover:bg-rose-50/[0.08]"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <Bubble
                key={i}
                role={m.role}
                content={m.content}
                products={m.products}
                onSelectProduct={setPreviewProduct}
              />
            ))}
            {sending && <TypingBubble />}
          </div>

          {error && (
            <p className="mb-2 shrink-0 rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-400/30 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </p>
          )}

          <form
            onSubmit={submit}
            className="mb-4 flex shrink-0 gap-2 rounded-2xl border border-stone-200 bg-white/80 p-3 shadow-sm backdrop-blur-sm dark:border-rose-100/10 dark:bg-rose-50/[0.03]"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="What are you shopping for today?"
              className="flex-1 rounded-xl bg-stone-100 px-4 py-2 text-sm text-stone-800 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-500/40 dark:bg-black/30 dark:text-rose-50 dark:placeholder:text-rose-100/40 dark:focus:ring-amber-300/30"
            />
            <button
              type="submit"
              disabled={sending}
              className="rounded-xl bg-gradient-to-r from-rose-700 to-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:scale-105 hover:shadow-lg hover:shadow-rose-500/30 disabled:opacity-50 disabled:hover:scale-100"
            >
              Send
            </button>
          </form>
        </main>

        {/* Dashboard slide-in panel */}
        <aside
          className={`fixed right-0 top-[73px] bottom-0 w-[320px] overflow-y-auto border-l border-rose-100/10 bg-[#1e1218]/95 px-4 py-4 backdrop-blur-sm transition-transform duration-300 ${
            dashOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-rose-50">
              📊 Observability Dashboard
            </h2>
            <button
              onClick={() => setDashOpen(false)}
              className="text-rose-100/40 transition hover:text-rose-100/80"
            >
              ✕
            </button>
          </div>

          <ObservabilityDashboard
            data={dashData}
            loading={dashLoading}
            lastUpdated={dashUpdated}
            onReset={handleDashReset}
          />
        </aside>
      </div>

      <ProductDetailModal product={previewProduct} onClose={() => setPreviewProduct(null)} />
    </div>
  )
}
