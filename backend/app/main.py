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
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Google Sheets service
from app.services.google_sheets import GoogleSheetsService
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


class InvestigatorRequest(BaseModel):
    """Optional payload to enrich Lead Investigator with KB items and override model."""
    patient_info: Dict[str, Any]
    triage_result: Dict[str, Any]
    kb_items: List[Dict[str, Any]] | None = None
    model: str | None = None

# Initialize Google Sheets service (simple, fail fast if misconfigured)
sheets_service = GoogleSheetsService(SPREADSHEET_ID)

# Allow importing the agents package from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from agents.autogen.agents import (
    OpenAIChat,
    TriageService,
    PatientParseService,
    LeadInvestigatorService,
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

        # Compute triage via TriageService
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        triage = triage_svc.run(summary_text=summary_text)

        # Write compact JSON into the triage column cell
        triage_str = json.dumps(triage.model_dump(), separators=(",", ":"))
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

@app.get("/api/resources/generate")
async def generate_resources(
    summary: Optional[str] = Query(None, description="Patient summary to extract zipcode from"),
    zipcode: Optional[str] = Query(None, description="Direct zipcode (alternative to providing full summary)"),
    debug: bool = Query(False, description="Enable debug mode for more detailed error information"),
):
    """
    Generate local autism resources based on zipcode.
    Either provide a full patient summary (to extract zipcode) or a direct zipcode.
    """
    try:
        if not (summary or zipcode):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'summary' or 'zipcode' parameter is required"
            )
        
        # Initialize Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            error_msg = "GEMINI_API_KEY environment variable not found. Please add it to your .env file."
            if debug:
                error_msg += f" Current environment: {dict(os.environ)}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        
        # Ensure we have all required imports at the top level
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[2]  # Go up from backend/app to kindroot
        agents_dir = project_root / 'agents'
        
        # Add to Python path if not already there
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        if str(agents_dir) not in sys.path:
            sys.path.insert(0, str(agents_dir))
        
        # Debug information
        if debug:
            logger.info(f"Project root: {project_root}")
            logger.info(f"Agents dir exists: {agents_dir.exists()}")
            logger.info(f"Agents dir: {agents_dir}")
            logger.info(f"Current sys.path: {sys.path}")
        
        try:
            # Now try the import
            from agents.autogen.agents import GeminiChat, ResourceGenerationService
            
        except ImportError as ie:
            error_msg = f"Failed to import required modules: {str(ie)}\n"
            error_msg += f"Current Python path: {sys.path}\n"
            error_msg += f"Project root: {project_root if 'project_root' in locals() else 'Not set'}"
            if debug:
                error_msg += f"\n\nPython path: {sys.path}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
            
        try:
            llm = GeminiChat(api_key=gemini_api_key)
            service = ResourceGenerationService(llm=llm)
            
            # Use provided zipcode or extract from summary
            if not zipcode and summary:
                zipcode = service.extract_zipcode(summary)
            
            if not zipcode:
                return {
                    "status": "skipped",
                    "reason": "No zipcode found in provided data",
                    "suggestion": "Please provide a valid 5-digit zipcode"
                }
                
            # Generate resources
            result = service.generate_resources(summary or zipcode)  # Pass the full summary or zipcode
            
            # If the result is a string, it might be an error message
            if isinstance(result, str):
                result = {"status": "error", "message": result}
                
            return {
                "status": "success",
                "zipcode": zipcode,
                "resources": result.get("resources", []),
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "debug": {"raw_result": result} if debug else None
            }
            
        except Exception as e:
            error_detail = f"Error during resource generation: {str(e)}"
            if debug:
                import traceback
                error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
            
    except HTTPException as he:
        if debug:
            he.detail = f"{he.detail}\n\nDebug Info: {str(he.__dict__)}"
        raise
    except Exception as e:
        error_detail = f"Unexpected error: {str(e)}"
        if debug:
            import traceback
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
