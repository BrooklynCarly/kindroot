import { useState } from 'react'
import { FileText, ExternalLink, Loader2, RefreshCw, User, ChevronDown, ChevronRight, Mail } from 'lucide-react'
import { Patient, ReportGenerationResponse } from '../types'
import { useAuth } from '../contexts/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface PatientListProps {
  patients: Patient[]
  onRefresh: () => void
}

export default function PatientList({ patients, onRefresh }: PatientListProps) {
  const { token } = useAuth()
  const [generatingReports, setGeneratingReports] = useState<Set<number>>(new Set())
  const [generatedReports, setGeneratedReports] = useState<Map<number, string>>(new Map())
  const [errors, setErrors] = useState<Map<number, string>>(new Map())
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [loadingSummaries, setLoadingSummaries] = useState<Set<number>>(new Set())
  const [parsedSummaries, setParsedSummaries] = useState<Map<number, any>>(new Map())
  const [emailingReports, setEmailingReports] = useState<Set<number>>(new Set())
  const [emailedReports, setEmailedReports] = useState<Set<number>>(new Set())

  const toggleExpand = async (row: number) => {
    const isExpanded = expandedRows.has(row)
    
    if (isExpanded) {
      // Collapse
      setExpandedRows(prev => {
        const newSet = new Set(prev)
        newSet.delete(row)
        return newSet
      })
    } else {
      // Expand and fetch summary if not already loaded
      setExpandedRows(prev => new Set(prev).add(row))
      
      if (!parsedSummaries.has(row)) {
        setLoadingSummaries(prev => new Set(prev).add(row))
        
        try {
          const response = await fetch(`${API_URL}/api/patients/${row}/summary`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          if (response.ok) {
            const data = await response.json()
            setParsedSummaries(prev => new Map(prev).set(row, data))
          }
        } catch (err) {
          console.error('Error fetching summary:', err)
        } finally {
          setLoadingSummaries(prev => {
            const newSet = new Set(prev)
            newSet.delete(row)
            return newSet
          })
        }
      }
    }
  }

  const emailReport = async (patient: Patient) => {
    const row = patient.row
    
    // Add to emailing set
    setEmailingReports(prev => new Set(prev).add(row))
    
    // Clear any previous error
    setErrors(prev => {
      const newErrors = new Map(prev)
      newErrors.delete(row)
      return newErrors
    })

    try {
      const response = await fetch(`${API_URL}/api/email-report/${row}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to email report: ${response.statusText}`)
      }

      await response.json()
      
      // Mark as emailed
      setEmailedReports(prev => new Set(prev).add(row))
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to email report'
      setErrors(prev => new Map(prev).set(row, errorMessage))
      console.error('Error emailing report:', err)
    } finally {
      // Remove from emailing set
      setEmailingReports(prev => {
        const newSet = new Set(prev)
        newSet.delete(row)
        return newSet
      })
    }
  }

  const generateReport = async (patient: Patient) => {
    const row = patient.row
    
    // Add to generating set
    setGeneratingReports(prev => new Set(prev).add(row))
    
    // Clear any previous error
    setErrors(prev => {
      const newErrors = new Map(prev)
      newErrors.delete(row)
      return newErrors
    })

    try {
      const response = await fetch(`${API_URL}/api/generate-report/${row}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to generate report: ${response.statusText}`)
      }

      const data: ReportGenerationResponse = await response.json()
      
      // Store the report URL
      setGeneratedReports(prev => new Map(prev).set(row, data.report_url))
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate report'
      setErrors(prev => new Map(prev).set(row, errorMessage))
      console.error('Error generating report:', err)
    } finally {
      // Remove from generating set
      setGeneratingReports(prev => {
        const newSet = new Set(prev)
        newSet.delete(row)
        return newSet
      })
    }
  }

  if (patients.length === 0) {
    return (
      <div className="text-center py-12">
        <User className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">No records found</h3>
        <p className="mt-1 text-sm text-gray-500">
          No records are available in the system.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Records
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            {patients.length} record{patients.length !== 1 ? 's' : ''} found
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
      </div>

      <div className="bg-white shadow-sm rounded-lg border border-gray-200 overflow-hidden">
        <ul className="divide-y divide-gray-200">
          {patients.map((patient) => {
            const isGenerating = generatingReports.has(patient.row)
            const reportUrl = generatedReports.get(patient.row) || patient.report_url
            const error = errors.get(patient.row)
            const hasExistingReport = Boolean(patient.report_url)
            const isExpanded = expandedRows.has(patient.row)
            const isLoadingSummary = loadingSummaries.has(patient.row)
            const parsedSummary = parsedSummaries.get(patient.row)
            const isEmailing = emailingReports.has(patient.row)
            const wasEmailed = emailedReports.has(patient.row)

            return (
              <li key={patient.row} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3">
                      {/* Expand/Collapse button */}
                      <button
                        onClick={() => toggleExpand(patient.row)}
                        className="flex-shrink-0 p-1 hover:bg-gray-200 rounded transition-colors"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-5 w-5 text-gray-500" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-gray-500" />
                        )}
                      </button>
                      <div className="flex-shrink-0">
                        <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <User className="h-5 w-5 text-blue-600" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {patient.parent_name && patient.date_submitted
                            ? `${patient.parent_name} - ${patient.date_submitted}`
                            : patient.parent_name || patient.child_name || 'Unknown Name'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {patient.report_generated_at && (
                            <span>Report Generated: {patient.report_generated_at}</span>
                          )}
                          {patient.report_emailed_at && (
                            <span>
                              {patient.report_generated_at && ' • '}
                              Emailed: {patient.report_emailed_at}
                            </span>
                          )}
                          {!patient.report_generated_at && !patient.report_emailed_at && (
                            <span>No report generated yet</span>
                          )}
                          {' • Row: '}{patient.row}
                        </p>
                      </div>
                    </div>

                    {error && (
                      <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
                        {error}
                      </div>
                    )}

                    {/* Expanded summary section */}
                    {isExpanded && (
                      <div className="mt-4 px-4">
                        {isLoadingSummary ? (
                          <div className="flex items-center space-x-2 text-gray-500">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Loading summary...</span>
                          </div>
                        ) : parsedSummary?.sections ? (
                          <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                            <h4 className="text-sm font-semibold text-gray-900 mb-3">Summary</h4>
                            <div className="space-y-3">
                              {parsedSummary.sections.map((section: any, idx: number) => (
                                <div key={idx} className="border-l-2 border-blue-400 pl-3">
                                  {section.question && (
                                    <div className="text-xs font-semibold text-gray-600 uppercase mb-1">
                                      {section.question}
                                    </div>
                                  )}
                                  <div className="text-sm text-gray-900">
                                    {section.answer}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="text-sm text-gray-500">No summary available</div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="ml-6 flex-shrink-0 flex items-center space-x-3">
                    {/* Email Report button - fixed width column */}
                    <div className="w-36">
                      {reportUrl && patient.email && (
                        <button
                          onClick={() => emailReport(patient)}
                          disabled={isEmailing}
                          className={`inline-flex items-center justify-center w-full px-4 py-2 border rounded-md shadow-sm text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                            isEmailing
                              ? 'border-gray-300 text-gray-400 bg-gray-100 cursor-not-allowed'
                              : wasEmailed
                              ? 'border-green-600 text-green-700 bg-green-50 hover:bg-green-100 focus:ring-green-500'
                              : 'border-purple-600 text-purple-700 bg-white hover:bg-purple-50 focus:ring-purple-500'
                          }`}
                        >
                          {isEmailing ? (
                            <>
                              <Loader2 className="animate-spin h-4 w-4 mr-2" />
                              Sending...
                            </>
                          ) : (
                            <>
                              <Mail className="h-4 w-4 mr-2" />
                              {wasEmailed ? 'Email Sent' : 'Email Report'}
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    
                    {/* View Report button - fixed width column */}
                    <div className="w-36">
                      {reportUrl && (
                        <a
                          href={reportUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center w-full px-4 py-2 border border-green-600 rounded-md shadow-sm text-sm font-medium text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          View Report
                        </a>
                      )}
                    </div>
                    
                    {/* Generate Report button - fixed width column */}
                    <div className="w-52">
                      <button
                        onClick={() => generateReport(patient)}
                        disabled={isGenerating || !patient.has_summary}
                        className={`inline-flex items-center justify-center w-full px-4 py-2 border rounded-md shadow-sm text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                          isGenerating
                            ? 'border-gray-300 text-gray-400 bg-gray-100 cursor-not-allowed'
                            : !patient.has_summary
                            ? 'border-gray-300 text-gray-400 bg-gray-100 cursor-not-allowed'
                            : 'border-transparent text-white bg-blue-600 hover:bg-blue-700'
                        }`}
                      >
                        {isGenerating ? (
                          <>
                            <Loader2 className="animate-spin h-4 w-4 mr-2" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <FileText className="h-4 w-4 mr-2" />
                            {hasExistingReport ? 'Generate New Report' : 'Generate Report'}
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
