import { useState, useEffect } from 'react'
import { useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import UserMenu from './components/UserMenu'
import PatientList from './components/PatientList'
import { Patient } from './types'

function App() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { token } = useAuth()

  useEffect(() => {
    if (token) {
      fetchPatients()
    }
  }, [token])

  const fetchPatients = async () => {
    if (!token) return
    
    try {
      setLoading(true)
      setError(null)
      const response = await fetch('/api/patients', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch patients: ${response.statusText}`)
      }
      
      const data = await response.json()
      setPatients(data.patients || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patients')
      console.error('Error fetching patients:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  KindRoot Patient Reports
                </h1>
                <p className="mt-2 text-sm text-gray-600">
                  View patient records and generate comprehensive reports
                </p>
              </div>
              <UserMenu />
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error loading patients</h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && (
            <PatientList patients={patients} onRefresh={fetchPatients} />
          )}
        </main>
      </div>
    </ProtectedRoute>
  )
}

export default App
