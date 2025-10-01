from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Any
import os
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from pathlib import Path
import json
import sys

# Import Google Sheets service
from app.services.google_sheets import GoogleSheetsService
from app.services.triage_transform import build_patient_report

# Load environment variables (ensure we load backend/.env regardless of where the app is started)
_found_env = find_dotenv(filename=".env")
if not _found_env:
    # Fallback to backend/.env relative to this file
    _found_env = str(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(_found_env)

# Read required env
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
if not SPREADSHEET_ID:
    raise ValueError("GOOGLE_SHEETS_ID environment variable not set in backend/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set in backend/.env")

app = FastAPI(
    title="KindRoot API",
    description="API for KindRoot application",
    version="0.1.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class SheetRangeRequest(BaseModel):
    range: str

class SheetDataRequest(SheetRangeRequest):
    values: List[List[Any]]

# Initialize Google Sheets service (simple, fail fast if misconfigured)
sheets_service = GoogleSheetsService(SPREADSHEET_ID)

# Allow importing the agents package from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.autogen.autogen_agent import triage_safety, parse_patient_info

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to KindRoot API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": {"google_sheets": "connected"}}

# Google Sheets endpoints
@app.get("/api/sheets/read")
async def read_sheet(range: str):
    """
    Read data from a Google Sheet.
    
    Args:
        range: The A1 notation of the range to read (e.g., 'Sheet1!A1:D10')
    """
    try:
        data = sheets_service.read_sheet(range)
        return {"status": "success", "data": data}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read from Google Sheet: {str(e)}"
        )


@app.post("/api/clinical/dashboard/triage/write")
async def clinical_dashboard_write_triage(
    sheet_name: str = "Processed Data",
    patient_id_col: str = "A",
    summary_col: str = "J",
    triage_col: str = "AH",
):
    """
    Compute a new triage response for the latest row (based on summary_col) and
    write the JSON into the triage_col of the same row.
    Returns the row index, patient_id, summary, and the triage JSON.
    """
    try:
        # Locate the row using the summary column as the source of truth
        last_row = sheets_service.get_last_filled_row_index(sheet_name, summary_col)

        # Read patient ID and summary
        patient_id_cell = f"{patient_id_col}{last_row}"
        summary_cell = f"{summary_col}{last_row}"
        triage_cell = f"{triage_col}{last_row}"

        patient_id = sheets_service.get_cell_value(sheet_name, patient_id_cell)
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)

        if summary_text in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found at the latest row")

        # Compute triage via SafetyAgent helper
        triage = triage_safety(summary_text=summary_text, api_key=OPENAI_API_KEY, model="gpt-4.1-mini")

        # Write compact JSON into the triage column cell
        triage_str = json.dumps(triage, separators=(",", ":"))
        range_name = f"{sheet_name}!{triage_cell}"
        sheets_service.write_to_sheet(range_name, [[triage_str]])

        return {
            "status": "success",
            "data": {
                "row": last_row,
                "patient_id": patient_id,
                "summary": summary_text,
                "triage_cell": triage_cell,
                "triage_response": triage,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Writing triage to sheet failed: {str(e)}"
        )


@app.get("/api/clinical/dashboard/latest")
async def clinical_dashboard_latest(
    sheet_name: str = "Processed Data",
    patient_id_col: str = "A",
    summary_col: str = "I",
):
    """
    Return the latest record for the clinical dashboard:
    - patient_id: from the specified patient_id_col at the last filled row of summary_col
    - summary: from the specified summary_col at that row
    - triage_response: JSON returned by SafetyAgent (triage_safety)
    """
    try:
        # Find the last filled row based on the summary column
        last_row = sheets_service.get_last_filled_row_index(sheet_name, summary_col)

        # Read patient ID and summary for that row
        patient_id_cell = f"{patient_id_col}{last_row}"
        summary_cell = f"{summary_col}{last_row}"
        patient_id = sheets_service.get_cell_value(sheet_name, patient_id_cell)
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)

        if summary_text in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found at the latest row")

        triage = triage_safety(summary_text=summary_text, api_key=OPENAI_API_KEY, model="gpt-4.1-mini")

        return {
            "status": "success",
            "data": {
                "row": last_row,
                "patient_id": patient_id,
                "summary": summary_text,
                "triage_response": triage,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clinical dashboard retrieval failed: {str(e)}"
        )

@app.get("/api/pipeline/triage/latest")
@app.post("/api/pipeline/triage/latest")
async def triage_latest_processed_data_summary():
    """
    Pipeline Step 1: Resolve the 'Patient Summary' column on the 'Processed Data' sheet,
    fetch the latest summary from that column, and run the Base Agent triage using
    model gpt-4.1-mini. Returns JSON.
    """
    try:
        # Resolve the summary column by header name
        col_letter = sheets_service.get_column_letter_by_header("Processed Data", "Patient Summary", header_row=1)
        latest_summary = sheets_service.get_last_non_empty_in_column("Processed Data", col_letter)
        if latest_summary in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found in 'Processed Data' for header 'Patient Summary'")

        # Call Base Agent triage task
        result_json = triage_safety(latest_summary, api_key=OPENAI_API_KEY, model="gpt-4.1-mini")

        return {"status": "success", "triage": result_json}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage pipeline failed: {str(e)}"
        )


@app.get("/api/pipeline/triage/latest_for_report")
@app.post("/api/pipeline/triage/latest_for_report")
async def triage_latest_for_report():
    """
    Resolve the 'Patient Summary' column on the 'Processed Data' sheet, fetch the latest summary,
    run the Base Agent triage, and return both:
    - result_json: clinician-oriented triage JSON (per TRIAGE_JSON_SCHEMA_EXAMPLE)
    - triage_result_report_json: patient-friendly simplified report JSON
    """
    try:
        # Resolve the summary column by header name
        col_letter = sheets_service.get_column_letter_by_header("Processed Data", "Patient Summary", header_row=1)
        latest_summary = sheets_service.get_last_non_empty_in_column("Processed Data", col_letter)
        if latest_summary in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found in 'Processed Data' for header 'Patient Summary'")

        # Clinician triage JSON
        result_json = triage_safety(latest_summary, api_key=OPENAI_API_KEY, model="gpt-4.1-mini")

        # Patient-friendly report JSON
        triage_result_report_json = build_patient_report(result_json, source_version="1.0.0")

        return {
            "status": "success",
            "triage": result_json,
            "triage_result_report_json": triage_result_report_json,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage report pipeline failed: {str(e)}"
        )


@app.get("/api/patient/latest")
async def patient_latest(
    sheet_name: str = "Processed Data",
    column_letter: str | None = None,
    column_header: str = "Patient Summary",
    model: str = "gpt-4.1-mini",
):
    """
    Fetch the latest non-empty value from the given column and return LLM-parsed patient info JSON.

    - If `column_letter` is provided, it is used directly (e.g., "J").
    - Otherwise, the column letter is resolved by matching `column_header` in the header row (default: "Patient Summary").
    """
    try:
        # Resolve column letter if not provided
        col_letter = column_letter or sheets_service.get_column_letter_by_header(sheet_name, column_header, header_row=1)

        latest_summary = sheets_service.get_last_non_empty_in_column(sheet_name, col_letter)
        if latest_summary in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found in specified column")

        parsed = parse_patient_info(str(latest_summary), api_key=OPENAI_API_KEY, model=model)
        return {
            "status": "success",
            "data": {
                "row_source": {"sheet": sheet_name, "column": col_letter, "header": column_header},
                "summary": latest_summary,
                "parsed": parsed,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Patient parsing failed: {str(e)}"
        )


@app.post("/api/sheets/write")
async def write_to_sheet(request: SheetDataRequest):
    """
    Write data to a Google Sheet.
    
    Request body should be:
    {
        "range": "Sheet1!A1",
        "values": [["Header1", "Header2"], ["Value1", "Value2"]]
    }
    """
    try:
        result = sheets_service.write_to_sheet(request.range, request.values)
        return {"status": "success", "result": result}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write to Google Sheet: {str(e)}"
        )

@app.post("/api/sheets/append")
async def append_to_sheet(request: SheetDataRequest):
    """
    Append data to a Google Sheet.
    
    Request body should be:
    {
        "range": "Sheet1!A1",
        "values": [["NewRow1", "NewRow2"]]
    }
    """
    try:
        result = sheets_service.append_to_sheet(request.range, request.values)
        return {"status": "success", "result": result}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to append to Google Sheet: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
