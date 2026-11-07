import { useState } from 'react'
import App from './App.jsx'
import LandingPage from './pages/LandingPage.jsx'
import EmployeeIdentification from './pages/EmployeeIdentification.jsx'

export default function AppShell() {
  const [currentPage, setCurrentPage] = useState('landing')
  const [employee, setEmployee] = useState(null)

  function handleEmployeeIdentified(identifiedEmployee) {
    setEmployee(identifiedEmployee)
    setCurrentPage('workspace')
  }

  function handleSwitchAccount() {
    setEmployee(null)
    setCurrentPage('identify')
  }

  function handleLogOut() {
    setEmployee(null)
    setCurrentPage('landing')
  }

  if (currentPage === 'workspace' && employee) {
    return (
      <App
        key={employee.email}
        employee={employee}
        onSwitchAccount={handleSwitchAccount}
        onLogOut={handleLogOut}
      />
    )
  }

  if (currentPage === 'identify') {
    return (
      <EmployeeIdentification
        onSuccess={handleEmployeeIdentified}
      />
    )
  }

  return (
    <LandingPage
      onGetStarted={() => setCurrentPage('identify')}
    />
  )
}