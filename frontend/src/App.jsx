
import { useEffect, useRef, useState } from 'react'
import {
  ShieldCheck,
  MessageSquareText,
  BookOpen,
  Activity,
  Send,
  Plus,
  LoaderCircle,
  UserRound,
  AudioLines,
  Layers3,
  Sparkles,
  Mic,
  Ticket, History, Settings, LogOut, RefreshCw, AlertCircle,
} from 'lucide-react'
import './App.css'
import { useVoiceAssistant } from './useVoiceAssistant'

function createSessionId() {
  return `ui-${crypto.randomUUID()}`
}

function App({ employee, onSwitchAccount, onLogOut }) {
  const [activePage, setActivePage] = useState('chat')
  const [savedConversations, setSavedConversations] = useState([])
  const [knowledgeDocuments, setKnowledgeDocuments] = useState([])
  const [knowledgeLoading, setKnowledgeLoading] = useState(false)
  const [knowledgeError, setKnowledgeError] = useState('')
  const [selectedKnowledgeDocument, setSelectedKnowledgeDocument] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [selectedConversation, setSelectedConversation] = useState(null)
  const [conversationLoading, setConversationLoading] = useState(false)
  const [tickets, setTickets] = useState([])
  const [ticketsLoading, setTicketsLoading] = useState(false)
  const [ticketsError, setTicketsError] = useState('')
  const [ticketFilter, setTicketFilter] = useState('all')
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [traceTab, setTraceTab] = useState('evidence')
  const [selectedMessageIndex, setSelectedMessageIndex] = useState(null)
  const selectedMessage =
    selectedMessageIndex === null
      ? null
      : messages[selectedMessageIndex]



  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(createSessionId)
  const email = (employee?.email || employee?.employee?.email || '').trim().toLowerCase()

  const [citations, setCitations] = useState([])
  const [toolCalls, setToolCalls] = useState([])
  const [pendingAction, setPendingAction] = useState(null)
  const [actionResult, setActionResult] = useState(null)

  const displayedCitations = selectedMessage?.citations ?? citations
  const displayedToolCalls = selectedMessage?.toolCalls ?? toolCalls

  useEffect(() => {
    if (activePage !== 'tickets' || !email) return
    const controller = new AbortController()
    setTicketsLoading(true)
    setTicketsError('')
    fetch(`/api/my-tickets?requester_email=${encodeURIComponent(email)}&limit=50`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Ticket service returned HTTP ${response.status}`)
        const data = await response.json()
        if (data.ok === false) throw new Error(data.error?.message || 'Ticket lookup failed')
        return data
      })
      .then((data) => setTickets(Array.isArray(data.tickets) ? data.tickets : []))
      .catch((error) => { if (error.name !== 'AbortError') setTicketsError(error.message) })
      .finally(() => { if (!controller.signal.aborted) setTicketsLoading(false) })
    return () => controller.abort()
  }, [activePage, email])

  useEffect(() => {
  if (activePage !== 'knowledge') return

  const controller = new AbortController()

  setKnowledgeLoading(true)
  setKnowledgeError('')
  setSelectedKnowledgeDocument(null)

  fetch('/api/knowledge-base', { signal: controller.signal })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(
          `Knowledge Base service returned HTTP ${response.status}`
        )
      }
      return response.json()
    })
    .then((data) => {
      if (!controller.signal.aborted) {
        setKnowledgeDocuments(
          Array.isArray(data.documents) ? data.documents : []
        )
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        setKnowledgeError(error.message)
      }
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setKnowledgeLoading(false)
      }
    })

  return () => controller.abort()
}, [activePage])
  useEffect(() => {
  if (activePage !== 'history' || !email) return

  const controller = new AbortController()

  setHistoryLoading(true)
  setHistoryError('')
  setSelectedConversation(null)

  fetch(
    `/api/conversations?employee_email=${encodeURIComponent(email)}`,
    { signal: controller.signal }
  )
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`History service returned HTTP ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (!controller.signal.aborted) {
        setSavedConversations(
          Array.isArray(data.conversations) ? data.conversations : []
        )
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        setHistoryError(error.message)
      }
    })
    .finally(() => {
      if (!controller.signal.aborted) {
        setHistoryLoading(false)
      }
    })

  return () => controller.abort()
}, [activePage, email])

  function leaveWorkspace(callback) {
    if (requestInFlight.current || loading) return
    if (pendingAction && !window.confirm('A ticket is awaiting approval. Leave this workspace and discard the current approval view?')) return
    stopVoice()
    setMessages([])
    setPendingAction(null)
    setCitations([])
    setToolCalls([])
    setActionResult(null)
    setTickets([])
    callback?.()
  }

  function openPage(page) {
    if (requestInFlight.current || loading) return
    if (page !== 'chat') stopVoice()
    setActivePage(page)
  }

  const chatEndRef = useRef(null)
  const requestInFlight = useRef(false)
  const [voiceLanguage, setVoiceLanguage] = useState('en-US')

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    })
  }, [messages, loading])

  async function handleSend(event, voiceText = null) {
    event?.preventDefault()

    const text = (voiceText ?? message).trim()
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
        citations: Array.isArray(data.citations) ? data.citations : [],
        toolCalls: Array.isArray(data.tool_calls) ? data.tool_calls : [],
      },
    ])

      setCitations(Array.isArray(data.citations) ? data.citations : [])
      setToolCalls(Array.isArray(data.tool_calls) ? data.tool_calls : [])
      setPendingAction(data.pending_action || null)
      setActionResult(data.result || null)
      return data.reply || 'No response received.'
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'assistant',
          content: `Unable to contact the helpdesk: ${error.message}`,
        },
      ])
      return null
    } finally {
      requestInFlight.current = false
      setLoading(false)
    }
  }

  const {
    voiceStatus,
    voiceError,
    start: startVoice,
    startDirect: startDirectVoice,
    stop: stopVoice,
    speak,
    isVoiceActive,
  } = useVoiceAssistant({
  language: voiceLanguage,
  onTranscript: async (transcript) => {
    const reply = await handleSend(null, transcript)

    if (reply) {
      speak(reply)
    } else {
      stopVoice()
    }
  },
})

useEffect(() => {
  startVoice()
}, [sessionId, startVoice])

  function startNewChat() {
    if (requestInFlight.current) return
    stopVoice()

    setActivePage('chat')
    setSessionId(createSessionId())
    setMessages([])
    setSelectedMessageIndex(null)
    setMessage('')
    setCitations([])
    setToolCalls([])
    setPendingAction(null)
    setActionResult(null)
    setTraceTab('evidence')
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
    <div className="app-shell workspace-v2">
      <nav className="workspace-sidebar" aria-label="Workspace navigation">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark"><ShieldCheck size={27} /></div>
          <strong>TraceDesk AI</strong>
          <span>Intelligent IT Support</span>
        </div>
        <div className="sidebar-navigation">
          {[
            ['chat', MessageSquareText, 'Chat'],
            ['tickets', Ticket, 'My Tickets'],
            ['history', History, 'History'],
            ['knowledge', BookOpen, 'Knowledge Base'],
            ['settings', Settings, 'Settings'],
          ].map(([page, Icon, label]) => (
            <button key={page} type="button" className={`sidebar-link ${activePage === page ? 'active' : ''}`}
              aria-current={activePage === page ? 'page' : undefined} onClick={() => openPage(page)}>
              <Icon size={19} /> <span>{label}</span>
            </button>
          ))}
        </div>
        <div className="sidebar-account-actions">
          <button type="button" className="sidebar-link" onClick={() => leaveWorkspace(onSwitchAccount)} disabled={loading}>
            <RefreshCw size={18} /><span>Switch Account</span>
          </button>
          <button type="button" className="sidebar-link" onClick={() => leaveWorkspace(onLogOut)} disabled={loading}>
            <LogOut size={18} /><span>Log Out</span>
          </button>
        </div>
        <div className="sidebar-bottom">
          <span className="sidebar-environment">Nakhla IT · Demo environment</span>
          <small>Evidence-led support</small>
        </div>
      </nav>
      <div className="workspace-main">
        <header className="topbar">
          <div className="workspace-heading">
            <Sparkles size={25} aria-hidden="true" />
            <div><h1>IT Support Assistant</h1><p>Reliable answers. Transparent actions.</p></div>
          </div>
          <div className="topbar-right">
            <div className="voice-indicator" aria-live="polite">
              <Mic size={19} aria-hidden="true" />
              <div><strong>Voice Assistant</strong><span>{voiceStatus === 'standby' ? 'Waiting for “Hey TraceDesk”' : voiceStatus === 'listening' ? 'Listening' : voiceStatus === 'thinking' ? 'Thinking' : voiceStatus === 'speaking' ? 'Speaking' : 'Voice mode off'}</span></div>
              <i className={isVoiceActive ? 'voice-dot active' : 'voice-dot'} aria-hidden="true" />
            </div>
            <div className="employee-identity" title={email}>
              <span className="employee-avatar"><UserRound size={20} /></span>
              <div><strong>Demo employee</strong><span>{email || 'No employee selected'}</span></div>
            </div>
          </div>
        </header>
      {activePage === 'chat' ? <main className="workspace">
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
                    className={`message-bubble ${item.role}${
                      item.role === 'assistant' && selectedMessageIndex === index
                        ? ' selected-message'
                        : ''
                    }`}
                    onClick={
                      item.role === 'assistant'
                        ? () => setSelectedMessageIndex(index)
                        : undefined
                    }
                    onKeyDown={
                      item.role === 'assistant'
                        ? (event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              setSelectedMessageIndex(index)
                            }
                          }
                        : undefined
                    }
                    role={item.role === 'assistant' ? 'button' : undefined}
                    tabIndex={item.role === 'assistant' ? 0 : undefined}
                    aria-pressed={
                      item.role === 'assistant'
                        ? selectedMessageIndex === index
                        : undefined
                    }
                  >
                    {item.role === 'assistant' && (
                      <div className="assistant-message-heading">
                        <ShieldCheck size={15} aria-hidden="true" />
                        <span>TraceDesk AI</span>
                        <span className="message-evidence-hint">{selectedMessageIndex === index ? 'Viewing evidence' : 'Select to view evidence'}</span>
                      </div>
                    )}
                    <div className="message-text" dir="auto">
                      {item.content}
                    </div>
                    {item.role === 'assistant' && Array.isArray(item.citations) && item.citations.length > 0 && (
                      <div className="message-source-count"><BookOpen size={13} aria-hidden="true" /> {item.citations.length} source{item.citations.length === 1 ? '' : 's'} · View in Trust Trace</div>
                    )}
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

          <div className="composer-dock">
           <div className="voice-controls">
  <select
    className="voice-language"
    value={voiceLanguage}
    onChange={(event) => setVoiceLanguage(event.target.value)}
    disabled={isVoiceActive}
    aria-label="Voice language"
  >
    <option value="en-US">English</option>
    <option value="ar-SA">العربية</option>
    <option value="he-IL">עברית</option>
  </select>

  <button
    type="button"
    className={`voice-button ${isVoiceActive ? 'voice-button-active' : ''}`}
    onClick={() => {
      if (isVoiceActive) {
        stopVoice()
      } else if (!loading && !pendingAction) {
        startVoice()
      }
    }}
    disabled={!isVoiceActive && (loading || Boolean(pendingAction))}
    aria-label={isVoiceActive ? 'Stop voice conversation' : 'Start voice conversation'}
    aria-pressed={isVoiceActive}
  >
    <AudioLines size={24} strokeWidth={2.5} />
  </button>

<button
  type="button"
  onClick={startDirectVoice}
  disabled={
    loading ||
    Boolean(pendingAction) ||
    voiceStatus === 'thinking' ||
    voiceStatus === 'speaking'
  }
  aria-label="Start direct voice conversation"
>
  Talk Now
</button>

  <span className="voice-status" aria-live="polite">
    {voiceStatus === 'standby' && 'Standby · Say "Hey TraceDesk"'}
    {voiceStatus === 'listening' && 'Listening...'}
    {voiceStatus === 'thinking' && 'Thinking...'}
    {voiceStatus === 'speaking' && 'Speaking...'}
    {voiceStatus === 'idle' && 'Voice Mode'}
  </span>

  {voiceError && (
    <span className="voice-error" role="alert">
      {voiceError}
    </span>
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
          </div>
        </section>

        <aside className="side-panel">
          <div className="trace-card">
            <div className="heading-title">
              <ShieldCheck size={21} />
              <h2>Trust Trace</h2>
            </div>

            <p className="card-description">Evidence · Decision · Action</p>
            <p className="trace-context-label">{selectedMessageIndex === null ? 'Latest assistant response' : 'Selected assistant response'}</p>
            <div className="trace-tabs" role="tablist" aria-label="Trust Trace sections">
              <button type="button" role="tab" aria-selected={traceTab === 'evidence'} className={traceTab === 'evidence' ? 'active' : ''} onClick={() => setTraceTab('evidence')}><BookOpen size={15} /> Evidence</button>
              <button type="button" role="tab" aria-selected={traceTab === 'activity'} className={traceTab === 'activity' ? 'active' : ''} onClick={() => setTraceTab('activity')}><Activity size={15} /> Activity</button>
              <button type="button" role="tab" aria-selected={traceTab === 'decision'} className={traceTab === 'decision' ? 'active' : ''} onClick={() => setTraceTab('decision')}><Layers3 size={15} /> Decision</button>
            </div>

            {traceTab === 'evidence' && <div className="trace-tab-content" role="tabpanel">
            <div className="trace-section">
              <div className="trace-section-title">
                <UserRound size={18} />
                <h3>Work Email</h3>
              </div>

              <input
                className="email-input"
                type="email"
                value={email}
                placeholder="employee@company.com"
                aria-label="Work email"
                readOnly
              />
            </div>

            <div className="trace-section">
              <div className="trace-section-title">
                <BookOpen size={18} />
                <h3>Knowledge Sources</h3>
              </div>

              {displayedCitations.length === 0 ? (
                <p>
                  Sources used in an answer will appear here after the assistant responds.
                </p>
              ) : (
                <div className="source-list">
                  {displayedCitations.map((source, index) => {
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

            </div>}
            {traceTab === 'activity' && <div className="trace-tab-content" role="tabpanel">
            <div className="trace-section">
              <div className="trace-section-title"><Activity size={18} /><h3>Agent Activity</h3></div>

              {(
                displayedToolCalls.length === 0 ? (
                  <p>No tool activity available for this response.</p>
                ) : (
                  <div className="source-list">
                    {displayedToolCalls.map((tool, index) => (
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
            </div>}
            {traceTab === 'decision' && <div className="trace-tab-content" role="tabpanel">
              <div className="trace-section decision-section">
                <div className="trace-section-title"><Layers3 size={18} /><h3>Action & approval</h3></div>
                {pendingAction ? <p>An action is awaiting your review. Check the approval card below before proceeding.</p> : actionResult ? <p>An action result is available below.</p> : <p>No pending action. Detailed policy reasoning is not available from the current response.</p>}
              </div>
            </div>}
          </div>

          {pendingAction && (
            <div className="approval-placeholder">
              <div className="approval-heading"><ShieldCheck size={20} /><h3>Ticket Approval Required</h3></div>

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
      </main> : (
        <main className="workspace-secondary">
          <section className="workspace-page-card">
            {activePage === 'tickets' && <>
              <div className="workspace-page-heading"><div><h2>My Tickets</h2><p>Support requests associated with your work email.</p></div>
                <select aria-label="Ticket status" value={ticketFilter} onChange={(e) => setTicketFilter(e.target.value)}>
                  <option value="all">All statuses</option><option value="open">Open</option>
                  <option value="resolved">Resolved</option><option value="closed">Closed</option>
                </select>
              </div>
              {ticketsLoading ? <p>Loading tickets…</p> : ticketsError ? <p role="alert" className="workspace-error"><AlertCircle size={17} /> {ticketsError}</p> :
                tickets.filter(t => ticketFilter === 'all' || t.status === ticketFilter).length === 0 ?
                <p className="workspace-empty">No matching tickets were found for this employee.</p> :
                <div className="workspace-records">{tickets.filter(t => ticketFilter === 'all' || t.status === ticketFilter).map((t) =>
                  <article key={t.ticket_id} className="workspace-record">
                    <div><strong>{t.subject || 'Untitled ticket'}</strong><small>{t.ticket_id} · {t.category || 'IT support'}</small></div>
                    <span className="workspace-status">{t.status || 'Unknown'}</span>
                    {t.description && <p>{t.description}</p>}
                  </article>)}</div>}
            </>}
           {activePage === 'history' && <>
  <div className="workspace-page-heading">
    <div>
      <h2>Conversation History</h2>
      <p>Your saved support conversations.</p>
    </div>
  </div>

  {historyLoading ? (
    <p>Loading conversations…</p>
  ) : historyError ? (
    <p role="alert" className="workspace-error">
      <AlertCircle size={17} /> {historyError}
    </p>
  ) : savedConversations.length === 0 ? (
    <p className="workspace-empty">
      No saved conversations found for this employee.
    </p>
  ) : (
    <div className="workspace-records">
      {savedConversations.map((conversation) => (
        <button
          key={conversation.session_id}
          type="button"
          className="workspace-record"
          style={{
            width: '100%',
            textAlign: 'left',
            cursor: 'pointer',
            font: 'inherit',
          }}
          onClick={async () => {
            setConversationLoading(true)
            setHistoryError('')

            try {
              const response = await fetch(
                `/api/conversations/${encodeURIComponent(conversation.session_id)}?employee_email=${encodeURIComponent(email)}`
              )

              if (!response.ok) {
                throw new Error(
                  `Conversation service returned HTTP ${response.status}`
                )
              }

              const data = await response.json()
              setSelectedConversation(data.conversation)
            } catch (error) {
              setHistoryError(error.message)
            } finally {
              setConversationLoading(false)
            }
          }}
        >
          <strong>{conversation.title}</strong>
          <small>
            {new Date(conversation.updated_at).toLocaleString()}
          </small>
        </button>
      ))}
    </div>
  )}

  {conversationLoading && <p>Loading messages…</p>}

  {selectedConversation && !conversationLoading && (
    <div className="workspace-records">
      <h3>{selectedConversation.title}</h3>

      {selectedConversation.messages.map((m, i) => (
        <article className="workspace-record" key={i}>
          <small>
            {m.role === 'user' ? 'You' : 'TraceDesk AI'}
          </small>
          <p dir="auto">{m.content}</p>
        </article>
      ))}

      <p className="workspace-note">
        Saved conversation — read-only.
      </p>

      <button
        className="workspace-primary"
        type="button"
        onClick={() => setSelectedConversation(null)}
      >
        Close Conversation
      </button>
    </div>
  )}

  <button
    className="workspace-primary"
    type="button"
    onClick={() => openPage('chat')}
  >
    Back to Chat
  </button>
</>}
            {activePage === 'knowledge' && (
  <>
    <div className="workspace-page-heading">
      <div>
        <h2>Knowledge Base</h2>
        <p>Browse current, authoritative IT support documents and policies.</p>
      </div>
    </div>

    {knowledgeLoading ? (
      <p>Loading knowledge documents…</p>
    ) : knowledgeError ? (
      <p role="alert" className="workspace-error">
        <AlertCircle size={17} /> {knowledgeError}
      </p>
    ) : knowledgeDocuments.length === 0 ? (
      <p className="workspace-empty">
        No approved knowledge documents are available.
      </p>
    ) : selectedKnowledgeDocument ? (
      <div className="workspace-records">
        <button
          className="workspace-primary"
          type="button"
          onClick={() => setSelectedKnowledgeDocument(null)}
        >
          Back to Knowledge Base
        </button>

        <article className="workspace-record">
          <div>
            <small>
              {selectedKnowledgeDocument.id}
              {' · '}Version {selectedKnowledgeDocument.version}
            </small>
            <h3>{selectedKnowledgeDocument.title}</h3>
            <small>
              Updated: {selectedKnowledgeDocument.last_updated}
              {' · '}Owner: {selectedKnowledgeDocument.owner}
            </small>
          </div>

          <div
            style={{
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
              lineHeight: 1.7,
              marginTop: 16,
            }}
          >
            {selectedKnowledgeDocument.content}
          </div>
        </article>
      </div>
    ) : (
      <>
        <p className="workspace-note">
          {knowledgeDocuments.length} approved knowledge documents
        </p>

        <div className="workspace-records">
          {knowledgeDocuments.map((doc) => (
            <button
              key={doc.id}
              type="button"
              className="workspace-record"
              style={{
                width: '100%',
                textAlign: 'left',
                cursor: 'pointer',
                font: 'inherit',
              }}
              onClick={() => setSelectedKnowledgeDocument(doc)}
            >
              <div>
                <strong>
                  {doc.id} — {doc.title}
                </strong>
                <small>
                  Version {doc.version}
                  {' · '}Updated {doc.last_updated}
                </small>
                <small>{doc.owner}</small>
              </div>
              <BookOpen size={19} aria-hidden="true" />
            </button>
          ))}
        </div>
      </>
    )}
  </>
)}
            {activePage === 'settings' && <>
              <div className="workspace-page-heading"><div><h2>Settings</h2><p>Personalize your support experience.</p></div></div>
              <div className="workspace-setting"><label>Selected work email</label><strong>{email}</strong></div>
              <div className="workspace-setting"><label htmlFor="settings-voice-language">Voice language</label>
                <select id="settings-voice-language" value={voiceLanguage} onChange={(e) => { stopVoice(); setVoiceLanguage(e.target.value) }}>
                  <option value="en-US">English</option><option value="ar-SA">العربية</option><option value="he-IL">עברית</option>
                </select></div>
              <p className="workspace-note">Demo identity selection is not secure authentication.</p>
              <button className="workspace-primary" type="button" onClick={() => leaveWorkspace(onSwitchAccount)}>Switch Account</button>
            </>}
          </section>
        </main>
      )}
      </div>
    </div>
  )
}

export default App
