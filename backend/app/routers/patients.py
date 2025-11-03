"""
Patient-related API endpoints.
"""
import logging
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv, find_dotenv

# Load environment variables
_found_env = find_dotenv(filename=".env")
if not _found_env:
    _found_env = str(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(_found_env, override=True)

# Import shared services
from app.services.google_sheets import GoogleSheetsService

logger = logging.getLogger(__name__)

# Initialize services
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
if not SPREADSHEET_ID:
    raise ValueError("GOOGLE_SHEETS_ID environment variable not set")
sheets_service = GoogleSheetsService(spreadsheet_id=SPREADSHEET_ID)

router = APIRouter(tags=["patients"])


@router.get("/patients")
def list_patients(
    sheet_name: str = "Processed Data",
    patient_id_col: str = "A",
    summary_col: str = "J",
    report_url_col: str = "AK",
    report_generated_col: str = "AL",
    report_emailed_col: str = "AM"
):
    """
    Get list of patients from the Google Sheet.
    
    Returns:
        List of patient records with basic information
    """
    try:
        # Read patient IDs, summaries, and report URLs (extend range to include AM for timestamps)
        range_name = f"{sheet_name}!{patient_id_col}2:{report_emailed_col}"
        logger.info(f"Reading patient data from range: {range_name}")
        data = sheets_service.read_sheet(range_name)
        
        patients = []
        for i, row in enumerate(data, start=2):  # Start at row 2 (skip header)
            if len(row) > 0 and row[0]:  # Has patient ID
                # Calculate the summary column index (J is the 10th column, index 9)
                summary_index = ord(summary_col) - ord('A')
                has_summary = len(row) > summary_index and bool(row[summary_index])
                
                # Get direct fields from sheet columns
                # B = date_submitted, C = parent_name, D = email, E = zipcode
                date_submitted = row[1] if len(row) > 1 else None  # Column B
                parent_name = row[2] if len(row) > 2 else None     # Column C
                email = row[3] if len(row) > 3 else None           # Column D
                
                # Calculate report URL column index (AK = 36)
                report_url_index = ord(report_url_col[0]) - ord('A')
                if len(report_url_col) > 1:
                    # Handle multi-letter columns like AK (A=0, K=10, so AK = 26 + 10 = 36)
                    report_url_index = (ord(report_url_col[0]) - ord('A') + 1) * 26 + (ord(report_url_col[1]) - ord('A'))
                
                report_url = row[report_url_index] if len(row) > report_url_index else None
                logger.debug(f"Row {i}: has {len(row)} columns, report_url_index={report_url_index}, report_url={report_url}")
                
                # Get timestamp columns (AL = 37, AM = 38)
                report_generated_index = (ord(report_generated_col[0]) - ord('A') + 1) * 26 + (ord(report_generated_col[1]) - ord('A'))
                report_emailed_index = (ord(report_emailed_col[0]) - ord('A') + 1) * 26 + (ord(report_emailed_col[1]) - ord('A'))
                
                report_generated_at = row[report_generated_index] if len(row) > report_generated_index else None
                report_emailed_at = row[report_emailed_index] if len(row) > report_emailed_index else None
                
                patient_entry = {
                    "row": i,
                    "patient_id": row[0],
                    "parent_name": parent_name if parent_name else None,
                    "date_submitted": date_submitted if date_submitted else None,
                    "email": email if email else None,
                    "has_summary": has_summary,
                    "report_url": report_url if report_url else None,
                    "report_generated_at": report_generated_at if report_generated_at else None,
                    "report_emailed_at": report_emailed_at if report_emailed_at else None,
                }
                
                # Try to extract basic info from summary if available
                if has_summary:
                    try:
                        summary_text = row[summary_index]
                        # Quick extraction of name from summary
                        if "Child's Name:" in summary_text or "Child Name:" in summary_text:
                            for prefix in ["Child's Name:", "Child Name:"]:
                                if prefix in summary_text:
                                    name_part = summary_text.split(prefix)[1].split("\n")[0].strip()
                                    patient_entry["child_name"] = name_part
                                    break
                        
                        # Extract age if present
                        if "Age:" in summary_text:
                            age_part = summary_text.split("Age:")[1].split("\n")[0].strip()
                            patient_entry["age"] = age_part
                    except Exception as e:
                        logger.warning(f"Failed to parse patient info from summary: {e}")
                        pass
                
                patients.append(patient_entry)
        
        return {
            "status": "success",
            "count": len(patients),
            "patients": patients
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in list_patients: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list patients: {str(e)}"
        )


@router.get("/patients/{row}/summary")
def get_patient_summary(
    row: int,
    sheet_name: str = "Processed Data",
    summary_col: str = "J"
):
    """
    Get patient summary text from column J for a specific row.
    Parses pipe-delimited responses into structured Q&A format.
    
    Returns:
        Parsed patient summary with questions and answers
    """
    try:
        # Get summary from sheet
        summary_cell = f"{summary_col}{row}"
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)
        
        if not summary_text:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found at row {row}"
            )
        
        # Parse pipe-delimited responses
        sections = []
        parts = summary_text.split("|")
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Try to split on first colon to separate question from answer
            if ":" in part:
                first_colon = part.index(":")
                question = part[:first_colon].strip()
                answer = part[first_colon + 1:].strip()
                sections.append({
                    "question": question,
                    "answer": answer
                })
            else:
                # If no colon, treat entire part as answer
                sections.append({
                    "question": None,
                    "answer": part
                })
        
        return {
            "status": "success",
            "row": row,
            "raw_summary": summary_text,
            "sections": sections
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting patient summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get patient summary: {str(e)}"
        )
