# KindRoot Patient Report Web Application

## Overview

A full-stack web application for viewing patient records and generating comprehensive Google Docs reports.

## Architecture

### Backend (FastAPI)
- **Location**: `/backend`
- **Port**: 8000
- **Key Endpoints**:
  - `GET /api/patients` - List all patient records
  - `POST /api/generate-report/{row}` - Generate comprehensive report
  - `GET /api/clinical/dashboard/triage/write` - Generate and write triage data
  - `GET /api/resources/generate/latest` - Generate resources for latest patient

### Frontend (React + TypeScript + Vite)
- **Location**: `/frontend`
- **Port**: 3000
- **Features**:
  - Patient list view with real-time data
  - One-click report generation
  - Loading states and error handling
  - Direct links to generated Google Docs

## Data Flow

1. **Patient List**: Frontend fetches from `/api/patients` → displays all patients from Google Sheet
2. **Generate Report**: User clicks "Generate Report" → POST to `/api/generate-report/{row}` → Backend:
   - Parses patient info from summary
   - Generates triage analysis (writes to column AH)
   - Generates clinical hypotheses (writes to column AI)
   - Generates local resources (if zipcode available)
   - Creates formatted Google Doc
   - Returns Google Doc URL
3. **View Report**: User clicks "Open Report" → Opens Google Doc in new tab

## Google Sheets Integration

### Columns Used:
- **Column A**: Patient ID
- **Column J**: Patient Summary (source data)
- **Column AH**: Triage Results (JSON, written by backend)
- **Column AI**: Clinical Hypotheses (JSON, written by backend)
- **Column AJ**: Local Resources (JSON, written by backend)

### Required Permissions:
The service account (from `backend/credentials.json`) must have **Editor** access to the Google Sheet.

## Running the Application

### 1. Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Backend runs on http://localhost:8000

### 2. Start Frontend
```bash
cd frontend
npm run dev
```
Frontend runs on http://localhost:3000

### 3. Access the Application
Open http://localhost:3000 in your browser

## Report Generation Process

When a report is generated:

1. **Patient Info Parsing**: Extracts structured data from patient summary
2. **Triage Analysis**: Identifies urgent safety concerns
3. **Clinical Hypotheses**: Generates potential underlying causes
4. **Resource Generation**: Finds local autism resources by zipcode
5. **Google Doc Creation**: Formats all data into a professional report
6. **Sheet Update**: Writes all generated data back to Google Sheets

## API Response Format

### List Patients
```json
{
  "status": "success",
  "count": 5,
  "patients": [
    {
      "row": 2,
      "patient_id": "P001",
      "has_summary": true,
      "child_name": "John Doe",
      "age": "5"
    }
  ]
}
```

### Generate Report
```json
{
  "status": "success",
  "report_url": "https://docs.google.com/document/d/...",
  "patient_id": "P001",
  "row": 2,
  "data_written_to_sheet": {
    "triage_cell": "AH2",
    "hypotheses_cell": "AI2"
  }
}
```

## Troubleshooting

### Backend Issues
- **"Writing triage to sheet failed"**: Check service account has Editor permissions
- **"No summary found"**: Verify data exists in the Patient Summary column
- **API Key errors**: Check `.env` file has valid `OPENAI_API_KEY` and `GOOGLE_SHEETS_ID`

### Frontend Issues
- **"Failed to fetch patients"**: Ensure backend is running on port 8000
- **CORS errors**: Vite proxy should handle this automatically
- **Report generation hangs**: Check backend logs for errors

## Next Steps

- Add filtering and search to patient list
- Show progress indicators during report generation
- Add ability to regenerate reports
- Display report metadata (when generated, by whom)
- Add patient detail view
