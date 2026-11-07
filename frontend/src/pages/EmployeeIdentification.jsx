import { useState } from 'react'
import { ArrowRight, ShieldCheck, Mail, LoaderCircle } from 'lucide-react'
import './EmployeeIdentification.css'

export default function EmployeeIdentification({ onSuccess }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()

    const normalizedEmail = email.trim().toLowerCase()

    setLoading(true)
    setError('')

    try {
      const response = await fetch(
        `/api/demo/employee?email=${encodeURIComponent(normalizedEmail)}`
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to identify employee.')
      }

      if (!data.employee || !data.employee.email) {
        throw new Error('Employee directory returned incomplete information.')
      }

      onSuccess(data.employee)
    } catch (err) {
      setError(err.message || 'Unable to connect to employee directory.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="employee-identification">
      <div className="employee-identification-card">
        <div className="employee-identification-icon">
          <ShieldCheck size={30} />
        </div>

        <div className="employee-identification-heading">
          <span className="employee-identification-eyebrow">
            TRACEDESK AI
          </span>

          <h1>Your IT workspace starts here.</h1>

          <p>
            Enter your Nakhla work email to access your
            personalized IT support experience.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="employee-email">Work email</label>

          <div className="employee-email-field">
            <Mail size={19} />

            <input
              id="employee-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name.surname@nakhla.example"
              autoComplete="email"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <p className="employee-identification-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={loading}>
            {loading ? (
              <>
                <LoaderCircle size={18} className="employee-spin" />
                Identifying employee...
              </>
            ) : (
              <>
                Continue to Workspace
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="employee-identification-footer">
          <ShieldCheck size={15} />
          Local demo environment · Employee directory lookup
        </div>
      </div>
    </main>
  )
}