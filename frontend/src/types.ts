export interface Patient {
  row: number
  patient_id: string
  parent_name?: string | null
  date_submitted?: string | null
  email?: string | null
  has_summary: boolean
  child_name?: string
  age?: string
  report_url?: string | null
  report_generated_at?: string | null
  report_emailed_at?: string | null
}

export interface ReportGenerationResponse {
  status: string
  report_url: string
  patient_id: string
  row: number
  data_written_to_sheet?: {
    triage_cell: string
    hypotheses_cell: string
  }
}
