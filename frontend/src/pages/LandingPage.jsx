import { useState } from 'react'
import {
  ArrowRight, AudioLines, BookOpenCheck, CheckCircle2,
  CircleDot, MessageCircle, SearchCheck, ShieldCheck, Sparkles,
} from 'lucide-react'
import '../styles/landing.css'

const intelligenceSteps = [
  {
    id: 'understand', number: '01', title: 'Understand',
    heading: 'First, understand the problem.',
    description: 'TraceDesk identifies the employee request and determines which information is needed.',
    icon: MessageCircle, detail: 'Intent recognition & intelligent routing',
  },
  {
    id: 'verify', number: '02', title: 'Verify',
    heading: 'Then, verify the evidence.',
    description: 'Official knowledge and relevant helpdesk information help ground the response.',
    icon: SearchCheck, detail: 'RAG knowledge + MCP service information',
  },
  {
    id: 'decide', number: '03', title: 'Decide',
    heading: 'Make a policy-aware decision.',
    description: 'TraceDesk uses available evidence and company policies to choose an appropriate response.',
    icon: BookOpenCheck, detail: 'Evidence & Trust Trace',
  },
  {
    id: 'act', number: '04', title: 'Act',
    heading: 'The employee stays in control.',
    description: 'When ticket creation is needed, TraceDesk requests human approval before proceeding.',
    icon: ShieldCheck, detail: 'Human approval gate',
  },
]

export default function LandingPage({ onGetStarted }) {
  const [activeStep, setActiveStep] = useState(0)
  const currentStep = intelligenceSteps[activeStep]
  const ActiveIcon = currentStep.icon

  return (
    <div className="landing-page landing-wow">
      <header className="landing-navbar">
        <a className="landing-brand" href="#home" aria-label="TraceDesk AI, back to top">
          <span className="landing-brand-icon"><ShieldCheck size={24} /></span>
          <span>TraceDesk AI</span>
        </a>
        <nav className="landing-nav" aria-label="Main navigation">
          <a href="#intelligence">Intelligence</a>
          <a href="#voice">Voice Experience</a>
        </nav>
        <span className="landing-nav-caption">Nakhla IT · Demo Environment</span>
      </header>

      <main>
        <section className="wow-hero" id="home" aria-labelledby="hero-heading">
          <div className="wow-hero-content">
            <span className="landing-eyebrow">
              <Sparkles size={16} /> Intelligent support. Transparent decisions.
            </span>
            <h1 id="hero-heading">IT Support.<br /><span>Reimagined.</span></h1>
            <p>
              An intelligent IT assistant that connects trusted knowledge,
              live service information, and human-approved actions.
            </p>
            <button className="landing-primary-button" type="button" onClick={onGetStarted}>
              Launch TraceDesk <ArrowRight size={19} />
            </button>
          </div>

          <div className="wow-hero-preview" aria-label="Illustrative Nakhla IT support workflow">
            <div className="wow-preview-topbar">
              <div className="wow-preview-identity">
                <span className="wow-preview-logo"><ShieldCheck size={19} /></span>
                <div><strong>Nakhla IT Desk</strong><small>Simulated support environment</small></div>
              </div>
              <span className="wow-preview-badge">DEMO</span>
            </div>
            <div className="wow-preview-body">
              <div className="wow-preview-question">
                <span className="wow-preview-label">EMPLOYEE REQUEST</span>
                <p>My VPN shows NX-503. What should I do?</p>
              </div>
              <div className="wow-preview-connection" aria-hidden="true">
                <span className="wow-preview-connection-line" />
                <span className="wow-preview-connection-icon"><Sparkles size={17} /></span>
                <span className="wow-preview-connection-line" />
              </div>
              <div className="wow-preview-evidence">
                <div className="wow-preview-evidence-header">
                  <ShieldCheck size={17} /><strong>TraceDesk AI</strong><span>Support workflow</span>
                </div>
                <div className="wow-preview-evidence-row">
                  <BookOpenCheck size={18} /><span>Official knowledge</span><CheckCircle2 size={16} />
                </div>
                <div className="wow-preview-evidence-row">
                  <SearchCheck size={18} /><span>Service status verification</span><CheckCircle2 size={16} />
                </div>
                <div className="wow-preview-evidence-row">
                  <ShieldCheck size={18} /><span>Human-approved actions</span><CheckCircle2 size={16} />
                </div>
              </div>
            </div>
            <div className="wow-preview-bottom">
              <span className="wow-preview-live-dot" aria-hidden="true" />
              Illustrative support workflow — not a live result
            </div>
          </div>
        </section>

        <section className="wow-intelligence" id="intelligence" aria-labelledby="intelligence-heading">
          <div className="wow-section-heading">
            <span>THE INTELLIGENCE BEHIND THE ANSWER</span>
            <h2 id="intelligence-heading">Not just an answer. A trusted process.</h2>
            <p>Explore how TraceDesk turns an IT request into an evidence-driven response.</p>
          </div>
          <div className="wow-showcase">
            <div className="wow-showcase-header">
              <div className="wow-showcase-brand"><span className="wow-status-dot" />TraceDesk Intelligence</div>
              <span className="wow-demo-label">Illustrative workflow</span>
            </div>
            <div className="wow-scenario">
              <span className="wow-scenario-icon"><MessageCircle size={19} /></span>
              <div><span>EMPLOYEE REQUEST</span><p>My VPN shows NX-503. What should I do?</p></div>
            </div>
            <div className="wow-step-navigation" role="group" aria-label="Explore workflow stages">
              {intelligenceSteps.map((step, index) => {
                const Icon = step.icon
                return (
                  <button
                    key={step.id} type="button"
                    className={`wow-step-button${activeStep === index ? ' active' : ''}`}
                    onClick={() => setActiveStep(index)}
                    aria-pressed={activeStep === index}
                  >
                    <span className="wow-step-number">{step.number}</span>
                    <Icon size={20} /><span>{step.title}</span>
                  </button>
                )
              })}
            </div>
            <div className="wow-step-detail" key={currentStep.id} aria-live="polite">
              <div className="wow-step-detail-icon"><ActiveIcon size={29} /></div>
              <div className="wow-step-detail-content">
                <span className="wow-step-eyebrow">STEP {currentStep.number}</span>
                <h3>{currentStep.heading}</h3>
                <p>{currentStep.description}</p>
                <div className="wow-step-detail-tag"><CheckCircle2 size={16} />{currentStep.detail}</div>
              </div>
            </div>
            <div className="wow-showcase-footer">
              <span><CircleDot size={15} />Explore each stage</span>
              <span>No hidden reasoning exposed</span>
            </div>
          </div>
        </section>

        <section className="wow-voice" id="voice" aria-labelledby="voice-heading">
          <div className="wow-voice-content">
            <span className="wow-voice-eyebrow"><AudioLines size={17} />VOICE INTELLIGENCE</span>
            <h2 id="voice-heading">Just say, “Hey TraceDesk.”</h2>
            <p>Move naturally between voice and chat with a hands-free assistant designed for IT support.</p>
            <div className="wow-voice-states" aria-label="Voice assistant states">
              <span>Standby</span><span>Listening</span><span>Speaking</span>
            </div>
          </div>
          <div className="wow-voice-visual" role="img" aria-label="Illustration of the TraceDesk voice assistant">
            <div className="wow-voice-halo" />
            <div className="wow-voice-orb"><AudioLines size={50} /></div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>TraceDesk AI</span><span>Agentic IT Support · Demo Experience</span>
      </footer>
    </div>
  )
}
