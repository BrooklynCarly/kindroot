import os
import sys
import json
import datetime
import logging
from pathlib import Path
from typing import List, Any, Dict, Optional

# Load environment variables (ensure we load backend/.env regardless of where the app is started)
from dotenv import load_dotenv, find_dotenv

_found_env = find_dotenv(filename=".env")
if not _found_env:
    # Fallback to backend/.env relative to this file
    _found_env = str(Path(__file__).resolve().parents[1] / ".env")
load_dotenv(_found_env, override=True)  # Ensure latest values are loaded

# Now import FastAPI and other modules after environment is loaded
from fastapi import FastAPI, HTTPException, Query, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Google Sheets service
from app.services.google_sheets import GoogleSheetsService
from app.services.google_docs import GoogleDocsService
from app.services.triage_transform import build_patient_report
from app.services.knowledge_base import load_all_kb_items

# Environment variables are now loaded at the top of the file

# Read required env
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
if not SPREADSHEET_ID:
    raise ValueError("GOOGLE_SHEETS_ID environment variable not set in backend/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set in backend/.env")

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # Optional
logger.info(f"Google Drive Folder ID loaded: {GOOGLE_DRIVE_FOLDER_ID if GOOGLE_DRIVE_FOLDER_ID else 'NOT SET'}")

app = FastAPI(
    title="KindRoot API",
    description="API for KindRoot application",
    version="0.1.0"
)

# Session middleware for OAuth (must be added before other middleware)
import secrets
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_urlsafe(32))
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# CORS middleware configuration
# Allow both local development and production frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CONSUMER_FRONTEND_URL = os.getenv("CONSUMER_FRONTEND_URL", "http://localhost:3001")

allowed_origins = [
    "http://localhost:3000",  # Local admin frontend
    "http://localhost:3001",  # Local consumer frontend
]

# Add production URLs if configured
if FRONTEND_URL and FRONTEND_URL != "http://localhost:3000":
    allowed_origins.append(FRONTEND_URL)
if CONSUMER_FRONTEND_URL and CONSUMER_FRONTEND_URL != "http://localhost:3001":
    allowed_origins.append(CONSUMER_FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.routers import patients, reports, auth, resources

# Register auth router (no /api prefix as it's already in the router)
app.include_router(auth.router)

# Register other routers
app.include_router(patients.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(resources.router, prefix="/api")

# Pydantic models for request/response validation
class SheetRangeRequest(BaseModel):
    range: str

class SheetDataRequest(SheetRangeRequest):
    values: List[List[Any]]


class InvestigatorRequest(BaseModel):
    """Optional payload to enrich Lead Investigator with KB items and override model."""
    patient_info: Dict[str, Any]
    triage_result: Dict[str, Any]
    kb_items: List[Dict[str, Any]] | None = None
    model: str | None = None

# Initialize Google Sheets service (simple, fail fast if misconfigured)
sheets_service = GoogleSheetsService(SPREADSHEET_ID)
docs_service = GoogleDocsService()

# Allow importing the agents package from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.autogen.agents import (
    OpenAIChat,
    TriageService,
    PatientParseService,
    LeadInvestigatorService,
    ResourceGenerationService,
)

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


@app.get("/api/clinical/dashboard/triage/write")
async def clinical_dashboard_write_triage(
    sheet_name: str = "Processed Data",
    patient_id_col: str = "A",
    summary_header: str = "Patient Summary",
    triage_col: str = "AH",
):
    """
    Compute a new triage response for the latest row (based on Patient Summary column) and
    write the JSON into the triage_col of the same row.
    Returns the row index, patient_id, summary, and the triage JSON.
    """
    try:
        # Resolve the summary column by header name (same approach as working endpoint)
        summary_col = sheets_service.get_column_letter_by_header(sheet_name, summary_header, header_row=1)
        logger.info(f"Resolved '{summary_header}' to column {summary_col}")
        
        # Locate the row using the summary column as the source of truth
        last_row = sheets_service.get_last_filled_row_index(sheet_name, summary_col)
        logger.info(f"Last filled row in column {summary_col}: {last_row}")

        # Read patient ID and summary
        patient_id_cell = f"{patient_id_col}{last_row}"
        summary_cell = f"{summary_col}{last_row}"
        triage_cell = f"{triage_col}{last_row}"

        patient_id = sheets_service.get_cell_value(sheet_name, patient_id_cell)
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)

        if summary_text in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found at the latest row")

        logger.info(f"Processing triage for patient {patient_id} at row {last_row}")

        # Compute triage via TriageService
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        triage = triage_svc.run(summary_text=summary_text)

        logger.info(f"Triage computed, writing to {triage_cell}")

        # Write compact JSON into the triage column cell
        triage_str = json.dumps(triage.model_dump(), separators=(",", ":"))
        range_name = f"{sheet_name}!{triage_cell}"
        write_result = sheets_service.write_to_sheet(range_name, [[triage_str]])
        
        logger.info(f"Write result: {write_result.get('updatedCells', 0)} cells updated")

        return {
            "status": "success",
            "data": {
                "row": last_row,
                "patient_id": patient_id,
                "summary": summary_text[:100] + "..." if len(summary_text) > 100 else summary_text,
                "triage_cell": triage_cell,
                "triage_response": triage,
                "write_confirmation": {
                    "updated_cells": write_result.get('updatedCells', 0),
                    "updated_range": write_result.get('updatedRange', 'N/A')
                }
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in clinical_dashboard_write_triage: {str(e)}", exc_info=True)
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

        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        triage = triage_svc.run(summary_text=summary_text)

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

        # Call TriageService
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        result_json = triage_svc.run(summary_text=latest_summary)

        return {"status": "success", "triage": result_json}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Triage pipeline failed: {str(e)}"
        )


@app.get("/api/pipeline/triage/latest_for_report")
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
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        result_json = triage_svc.run(summary_text=latest_summary)

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

        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        parser_svc = PatientParseService(llm=llm, model=model)
        parsed = parser_svc.run(summary_text=str(latest_summary))
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


@app.get("/api/investigator/latest")
async def get_investigator_latest(
    sheet_name: str = "Processed Data",
    column_header: str = "Patient Summary",
    hypotheses_col: str = "AI",
):
    """
    Retrieve the most recent investigation results without reprocessing.
    
    Args:
        sheet_name: Name of the sheet to read from (default: "Processed Data")
        column_header: Header of the column containing patient summaries (default: "Patient Summary")
        hypotheses_col: Column letter where hypotheses are stored (default: "AI")
        
    Returns:
        The most recent investigation results including patient info, triage, and hypotheses
    """
    try:
        # Resolve the column and get the last row with data
        col_letter = sheets_service.get_column_letter_by_header(sheet_name, column_header, header_row=1)
        last_row = sheets_service.get_last_filled_row_index(sheet_name, col_letter)
        
        if last_row is None:
            raise HTTPException(status_code=404, detail="No data found in the specified sheet")
            
        # Get the latest summary
        latest_summary = sheets_service.get_cell_value(sheet_name, f"{col_letter}{last_row}")
        
        # Try to get existing hypotheses if available
        hypotheses_cell = f"{hypotheses_col}{last_row}"
        hypotheses_json = sheets_service.get_cell_value(sheet_name, hypotheses_cell)
        
        # If no hypotheses found, return a message indicating they need to be generated
        if not hypotheses_json:
            return {
                "status": "success",
                "message": "No existing investigation found. Use POST /api/investigator/latest to generate new results.",
                "data": {
                    "row_source": {
                        "sheet": sheet_name,
                        "column": col_letter,
                        "header": column_header,
                        "row": last_row
                    },
                    "summary": latest_summary
                }
            }
        
        # Parse the hypotheses JSON
        try:
            hypotheses = json.loads(hypotheses_json)
        except json.JSONDecodeError:
            hypotheses = {"error": "Failed to parse existing hypotheses JSON"}
        
        return {
            "status": "success",
            "data": {
                "row_source": {
                    "sheet": sheet_name,
                    "column": col_letter,
                    "header": column_header,
                    "row": last_row,
                },
                "summary": latest_summary,
                "hypotheses": hypotheses,
                "hypotheses_cell": hypotheses_cell,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest investigation: {str(e)}"
        )


@app.post("/api/investigator/latest")
async def investigator_latest(
    request: InvestigatorRequest,
    sheet_name: str = "Processed Data",
    column_header: str = "Patient Summary",
    write_to_sheet: bool = True,
    hypotheses_col: str = "AI",
):
    """
    Orchestrate Lead Investigator hypotheses using the latest 'Patient Summary' cell value:
    - Parse patient info
    - Compute triage
    - Combine with optional KB items to generate hypotheses
    - Optionally write results back to Google Sheets
    
    Args:
        write_to_sheet: If True, write hypotheses JSON to the sheet (default: True)
        hypotheses_col: Column letter to write hypotheses to (default: "AI")
    """
    try:
        # Resolve latest summary and get row index
        col_letter = sheets_service.get_column_letter_by_header(sheet_name, column_header, header_row=1)
        latest_summary = sheets_service.get_last_non_empty_in_column(sheet_name, col_letter)
        if latest_summary in (None, ""):
            raise HTTPException(status_code=404, detail="No summary found in specified column")
        
        # Get the row index for writing back
        last_row = sheets_service.get_last_filled_row_index(sheet_name, col_letter)

        # LLM sub-steps
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        model = request.model or "gpt-4.1-mini"
        
        parser_svc = PatientParseService(llm=llm, model=model)
        patient_info = parser_svc.run(summary_text=str(latest_summary))
        
        triage_svc = TriageService(llm=llm, model=model)
        triage = triage_svc.run(summary_text=str(latest_summary))

        # Load KB items and merge with any provided in request
        kb_items = load_all_kb_items()
        if request.kb_items:
            kb_items.extend(request.kb_items)

        # Orchestration
        investigator_svc = LeadInvestigatorService(llm=llm, model=model)
        hypotheses = investigator_svc.run(
            patient_info=patient_info,
            triage_result=triage,
            kb_items=kb_items
        )

        # Write back to Google Sheets if requested
        hypotheses_cell = None
        if write_to_sheet:
            hypotheses_cell = f"{hypotheses_col}{last_row}"
            hypotheses_json = json.dumps(hypotheses.model_dump(), separators=(",", ":"))
            range_name = f"{sheet_name}!{hypotheses_cell}"
            sheets_service.write_to_sheet(range_name, [[hypotheses_json]])

        return {
            "status": "success",
            "data": {
                "row_source": {"sheet": sheet_name, "column": col_letter, "header": column_header, "row": last_row},
                "summary": latest_summary,
                "patient_info": patient_info,
                "triage": triage,
                "hypotheses": hypotheses,
                "written_to_sheet": write_to_sheet,
                "hypotheses_cell": hypotheses_cell,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lead Investigator orchestration failed: {str(e)}"
        )

@app.get("/api/resources/generate/latest")
async def generate_resources_latest(
    sheet_name: str = "Processed Data",
    summary_header: str = "Patient Summary",
    resources_col: str = "AJ",
    debug: bool = Query(False, description="Enable debug mode for more detailed error information"),
):
    """
    Generate local autism resources for the latest patient and write to column AJ.
    Extracts zipcode from the patient summary and generates resources.
    """
    try:
        # Resolve the summary column by header name
        summary_col = sheets_service.get_column_letter_by_header(sheet_name, summary_header, header_row=1)
        logger.info(f"Resolved '{summary_header}' to column {summary_col}")
        
        # Get the last row with summary
        last_row = sheets_service.get_last_filled_row_index(sheet_name, summary_col)
        logger.info(f"Last filled row in column {summary_col}: {last_row}")
        
        # Read the summary
        summary_cell = f"{summary_col}{last_row}"
        summary = sheets_service.get_cell_value(sheet_name, summary_cell)
        
        if not summary:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found at row {last_row}"
            )
        
        logger.info(f"Generating resources for row {last_row}")
        
        # Use OpenAI for resource generation
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        service = ResourceGenerationService(llm=llm)
        
        # Extract zipcode from summary
        zipcode = service.extract_zipcode(summary)
        
        if not zipcode:
            result = {
                "status": "skipped",
                "reason": "No zipcode found in provided data",
                "suggestion": "Please provide a valid 5-digit zipcode"
            }
        else:
            # Generate resources
            result = service.generate_resources(summary)
            
            # Check for error or skipped status
            if result.get("status") in ("error", "skipped"):
                logger.warning(f"Resource generation returned status: {result.get('status')}")
        
        # Write to column AJ
        resources_cell = f"{resources_col}{last_row}"
        resources_str = json.dumps(result, separators=(",", ":"))
        range_name = f"{sheet_name}!{resources_cell}"
        write_result = sheets_service.write_to_sheet(range_name, [[resources_str]])
        
        logger.info(f"Resources written to {resources_cell}: {write_result.get('updatedCells', 0)} cells updated")
        
        return {
            "status": "success",
            "row": last_row,
            "zipcode": zipcode,
            "resources_cell": resources_cell,
            "data": result,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "write_confirmation": {
                "updated_cells": write_result.get('updatedCells', 0),
                "updated_range": write_result.get('updatedRange', 'N/A')
            }
        }
            
    except HTTPException as he:
        if debug:
            he.detail = f"{he.detail}\n\nDebug Info: {str(he.__dict__)}"
        raise
    except Exception as e:
        error_detail = f"Unexpected error: {str(e)}"
        if debug:
            import traceback
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        logger.error(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
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

@app.get("/api/kb/list")
async def list_kb_items():
    """
    List all knowledge base items currently loaded.
    
    Returns:
        All KB items from the knowledge base directory
    """
    try:
        kb_items = load_all_kb_items()
        return {
            "status": "success",
            "count": len(kb_items),
            "items": kb_items
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load KB items: {str(e)}"
        )


@app.get("/api/kb/observable-symptoms")
async def get_observable_symptoms_kb():
    """
    Get the full Observable Symptoms and Links knowledge base.
    
    Returns:
        Complete KB structure with symptom mappings and cross-cutting patterns
    """
    try:
        from app.services.knowledge_base import load_observable_symptoms_and_links
        kb = load_observable_symptoms_and_links()
        if not kb:
            raise HTTPException(status_code=404, detail="Observable Symptoms KB not found")
        return {"status": "success", "kb": kb}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load Observable Symptoms KB: {str(e)}"
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

# ============================================================================
# PATIENT AND REPORT ENDPOINTS
# ============================================================================
# These endpoints have been moved to:
# - routers/patients.py: /api/patients, /api/patients/{row}/summary
# - routers/reports.py: /api/generate-report/{row}, /api/email-report/{row}
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)