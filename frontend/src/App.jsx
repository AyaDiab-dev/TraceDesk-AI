
import { useEffect, useRef, useState } from 'react'
import {
  ShieldCheck,
  MessageSquareText,
  BookOpen,
  Activity,
  Send,
  Plus,
  ChevronDown,
  LoaderCircle,
  UserRound,
} from 'lucide-react'
import './App.css'

function createSessionId() {
  return `ui-${crypto.randomUUID()}`
}

function App() {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [showActivity, setShowActivity] = useState(false)

  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(createSessionId)
  const [email, setEmail] = useState('tariq.hamdan@nakhla.example')

  const [citations, setCitations] = useState([])
  const [toolCalls, setToolCalls] = useState([])
  const [pendingAction, setPendingAction] = useState(null)
  const [actionResult, setActionResult] = useState(null)

  const chatEndRef = useRef(null)
  const requestInFlight = useRef(false)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    })
  }, [messages, loading])

  async function handleSend(event) {
    event.preventDefault()

    const text = message.trim()
    if (!text || requestInFlight.current || pendingAction) return

    requestInFlight.current = true
    setLoading(true)

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: text },
    ])

    setMessage('')
    setActionResult(null)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          ...(email.trim()
            ? { user: { email: email.trim().toLowerCase() } }
            : {}),
        }),
      })

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`)
      }

      const data = await response.json()

      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: data.reply || 'No response received.',
        },
      ])

      setCitations(Array.isArray(data.citations) ? data.citations : [])
      setToolCalls(Array.isArray(data.tool_calls) ? data.tool_calls : [])
      setPendingAction(data.pending_action || null)
      setActionResult(data.result || null)
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: `Unable to contact the helpdesk: ${error.message}`,
        },
      ])
    } finally {
      requestInFlight.current = false
      setLoading(false)
    }
  }

  function startNewChat() {
    if (requestInFlight.current) return

    setSessionId(createSessionId())
    setMessages([])
    setMessage('')
    setCitations([])
    setToolCalls([])
    setPendingAction(null)
    setActionResult(null)
    setShowActivity(false)
  }

  async function handleApproval(approved) {
    if (!pendingAction || requestInFlight.current) return

    requestInFlight.current = true
    setLoading(true)

    const action = pendingAction

    try {
      const response = await fetch('/api/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          action_id: action.action_id,
          approved,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`)
      }

      const data = await response.json()

      setMessages((previous) => [
        ...previous,
        { role: 'user', content: approved ? 'Approve' : 'Reject' },
        {
          role: 'assistant',
          content: data.reply || 'No response received.',
        },
      ])

      setCitations(Array.isArray(data.citations) ? data.citations : [])
      setToolCalls(Array.isArray(data.tool_calls) ? data.tool_calls : [])
      setPendingAction(data.pending_action || null)
      setActionResult(data.result || null)
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: `Unable to process approval: ${error.message}`,
        },
      ])
      // Keep the pending action available for retry.
    } finally {
      requestInFlight.current = false
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={23} />
          </div>
          <div>
            <h1>TraceDesk AI</h1>
            <p>Explainable IT Support</p>
          </div>
        </div>

        <span className="demo-label">Evidence-Driven Support</span>
      </header>

      <main className="workspace">
        <section className="chat-panel">
          <div className="panel-heading">
            <div className="heading-title">
              <MessageSquareText size={20} />
              <h2>Support Assistant</h2>
            </div>

            <button
              className="new-chat-button"
              onClick={startNewChat}
              type="button"
              disabled={loading}
            >
              <Plus size={17} />
              New chat
            </button>
          </div>

          <div className="chat-content">
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-icon">
                  <ShieldCheck size={30} />
                </div>

                <h2>How can I help you today?</h2>
                <p>
                  Describe your IT issue or share an error code.
                  I'll help you find the next step.
                </p>

                <div className="suggestions">
                  <button
                    type="button"
                    onClick={() =>
                      setMessage(
                        'My account is locked after 5 failed login attempts in 15 minutes. What should I do?'
                      )
                    }
                  >
                    Account locked
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setMessage('NakhlaConnect shows error NX-781.')
                    }
                  >
                    VPN issue
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setMessage(
                        'I need help creating an IT support ticket.'
                      )
                    }
                  >
                    Create a ticket
                  </button>
                </div>
              </div>
            ) : (
              <div className="message-list" aria-live="polite">
                {messages.map((item, index) => (
                  <div
                    key={index}
                    className={`message-bubble ${item.role}`}
                  >
                    {item.content}
                  </div>
                ))}

                {loading && (
                  <div className="message-bubble assistant">
                    <LoaderCircle
                      size={15}
                      className="loading-icon"
                    />
                    {' '}TraceDesk AI is working...
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          <form className="composer" onSubmit={handleSend}>
            <input
              type="text"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={
                pendingAction
                  ? 'Review the pending ticket first...'
                  : 'Describe your IT issue...'
              }
              aria-label="Your IT support message"
              disabled={loading || Boolean(pendingAction)}
              maxLength={2000}
            />

            <button
              type="submit"
              disabled={!message.trim() || loading || Boolean(pendingAction)}
              aria-label="Send message"
            >
              {loading ? (
                <LoaderCircle size={19} className="loading-icon" />
              ) : (
                <Send size={19} />
              )}
            </button>
          </form>
        </section>

        <aside className="side-panel">
          <div className="trace-card">
            <div className="heading-title">
              <ShieldCheck size={21} />
              <h2>Trust Trace</h2>
            </div>

            <p className="card-description">
              Evidence and agent activity from the latest response.
            </p>

            <div className="trace-section">
              <div className="trace-section-title">
                <UserRound size={18} />
                <h3>Work Email</h3>
              </div>

              <input
                className="email-input"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="employee@company.com"
                aria-label="Work email"
                disabled={loading || messages.length > 0}
              />
            </div>

            <div className="trace-section">
              <div className="trace-section-title">
                <BookOpen size={18} />
                <h3>Knowledge Sources</h3>
              </div>

              {citations.length === 0 ? (
                <p>
                  No sources yet. Start a conversation to see cited evidence.
                </p>
              ) : (
                <div className="source-list">
                  {citations.map((source, index) => {
                    const label =
                      typeof source === 'string'
                        ? source
                        : `${source.id || 'Source'}${
                            source.title ? ` — ${source.title}` : ''
                          }`

                    return (
                      <div className="source-item" key={index}>
                        <BookOpen size={14} />
                        <span>{label}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="trace-section">
              <button
                className="activity-toggle"
                type="button"
                onClick={() => setShowActivity(!showActivity)}
                aria-expanded={showActivity}
              >
                <span>
                  <Activity size={18} />
                  Agent Activity
                </span>

                <ChevronDown
                  size={17}
                  className={showActivity ? 'rotated' : ''}
                />
              </button>

              {showActivity && (
                toolCalls.length === 0 ? (
                  <p>No tool activity recorded for the latest turn.</p>
                ) : (
                  <div className="source-list">
                    {toolCalls.map((tool, index) => (
                      <div className="source-item" key={index}>
                        <Activity size={14} />
                        <span>
                          {typeof tool === 'string'
                            ? tool
                            : `${tool.tool || 'Tool'}${
                                tool.ok === true
                                  ? ' — OK'
                                  : tool.ok === false
                                    ? ' — Failed'
                                    : ''
                              }${
                                typeof tool.ms === 'number'
                                  ? ` (${tool.ms} ms)`
                                  : ''
                              }`}
                        </span>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          </div>

          {pendingAction && (
            <div className="approval-placeholder">
              <h3>Ticket Approval Required</h3>

              <p>
                {pendingAction.summary || 'Review this action before proceeding.'}
              </p>

              {pendingAction.payload && (
                <div className="ticket-details">
                  {[
                    'subject',
                    'category',
                    'priority',
                    'department',
                    'requester_email',
                  ].map((field) =>
                    pendingAction.payload[field] != null ? (
                      <p key={field}>
                        <strong>{field.replaceAll('_', ' ')}:</strong>{' '}
                        {String(pendingAction.payload[field])}
                      </p>
                    ) : null
                  )}

                  {pendingAction.payload.description && (
                    <p>
                      <strong>Description:</strong>{' '}
                      {pendingAction.payload.description}
                    </p>
                  )}

                  {Array.isArray(pendingAction.payload.attempted_steps) && (
                    <p>
                      <strong>Attempted steps:</strong>{' '}
                      {pendingAction.payload.attempted_steps.join('; ')}
                    </p>
                  )}

                  {Array.isArray(pendingAction.payload.kb_refs) && (
                    <p>
                      <strong>KB references:</strong>{' '}
                      {pendingAction.payload.kb_refs.join(', ') || 'None'}
                    </p>
                  )}
                </div>
              )}

              <div className="approval-actions">
                <button
                  type="button"
                  className="approve-button"
                  disabled={loading}
                  onClick={() => handleApproval(true)}
                >
                  Approve
                </button>

                <button
                  type="button"
                  className="reject-button"
                  disabled={loading}
                  onClick={() => handleApproval(false)}
                >
                  Reject
                </button>
              </div>
            </div>
          )}

          {actionResult && Object.keys(actionResult).length > 0 && (
            <div className="approval-placeholder">
              <h3>Action Result</h3>

              {Object.entries(actionResult).map(([key, value]) => (
                <p key={key}>
                  <strong>{key.replaceAll('_', ' ')}:</strong>{' '}
                  {typeof value === 'object'
                    ? JSON.stringify(value)
                    : String(value)}
                </p>
              ))}
            </div>
          )}
        </aside>
      </main>
    </div>
  )
}

export default App
