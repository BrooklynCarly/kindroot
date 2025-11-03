"""
Report generation and email API endpoints.
"""
import logging
import json
import datetime
import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from dotenv import load_dotenv, find_dotenv

# Load environment variables
_found_env = find_dotenv(filename=".env")
if not _found_env:
    _found_env = str(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(_found_env, override=True)

# Add project root to path for agents import
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import shared services
from app.services.google_sheets import GoogleSheetsService
from app.services.google_docs import GoogleDocsService
from app.services.triage_transform import build_patient_report
from app.services.knowledge_base import load_all_kb_items
from agents.autogen.agents import (
    OpenAIChat,
    TriageService,
    PatientParseService,
    LeadInvestigatorService,
    ResourceGenerationService,
)

logger = logging.getLogger(__name__)

# Initialize services
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
if not SPREADSHEET_ID:
    raise ValueError("GOOGLE_SHEETS_ID environment variable not set")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

sheets_service = GoogleSheetsService(spreadsheet_id=SPREADSHEET_ID)
docs_service = GoogleDocsService()

router = APIRouter(tags=["reports"])


@router.post("/generate-report/{row}")
def generate_patient_report(
    row: int,
    sheet_name: str = "Processed Data",
    patient_id_col: str = "A",
    date_submitted_col: str = "B",
    parent_name_col: str = "C",
    email_col: str = "D",
    zipcode_col: str = "E",
    summary_col: str = "J",
    triage_col: str = "AH",
    hypotheses_col: str = "AI",
    resources_col: str = "AJ",
    report_url_col: str = "AK",
    report_generated_col: str = "AL"
):
    """
    Generate a comprehensive patient report as a Google Doc.
    Always generates fresh triage, hypotheses, and resources data.
    Writes all generated data back to the Google Sheet.
    
    Args:
        row: The row number of the patient in the sheet
        
    Returns:
        URL of the generated Google Doc report
    """
    try:
        logger.info(f"Generating report for row {row}")
        
        # Get patient summary
        summary_cell = f"{summary_col}{row}"
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)
        
        if not summary_text:
            raise HTTPException(
                status_code=404,
                detail=f"No summary found at row {row}"
            )
        
        logger.info(f"Found summary for row {row}")
        
        # Initialize LLM
        llm = OpenAIChat(api_key=OPENAI_API_KEY)
        
        # Parse patient info from summary
        logger.info("Parsing patient info...")
        patient_parse_svc = PatientParseService(llm=llm, model="gpt-4.1-mini")
        patient_info_obj = patient_parse_svc.run(summary_text=summary_text)
        
        # Get additional patient fields directly from sheet
        patient_id_cell = f"{patient_id_col}{row}"
        date_submitted_cell = f"{date_submitted_col}{row}"
        parent_name_cell = f"{parent_name_col}{row}"
        email_cell = f"{email_col}{row}"
        zipcode_cell = f"{zipcode_col}{row}"
        
        patient_id = sheets_service.get_cell_value(sheet_name, patient_id_cell)
        date_submitted = sheets_service.get_cell_value(sheet_name, date_submitted_cell)
        parent_name = sheets_service.get_cell_value(sheet_name, parent_name_cell)
        email = sheets_service.get_cell_value(sheet_name, email_cell)
        zipcode = sheets_service.get_cell_value(sheet_name, zipcode_cell)
        
        logger.info(f"Patient info parsed: {patient_id}, Parent: {parent_name}, Date: {date_submitted}")
        
        # Generate triage (always fresh)
        logger.info("Generating triage...")
        triage_svc = TriageService(llm=llm, model="gpt-4.1-mini")
        triage_obj = triage_svc.run(summary_text=summary_text)
        
        # Write triage to sheet
        triage_cell = f"{triage_col}{row}"
        triage_str = json.dumps(triage_obj.model_dump(), separators=(",", ":"))
        sheets_service.write_to_sheet(f"{sheet_name}!{triage_cell}", [[triage_str]])
        logger.info(f"Triage written to {triage_cell}")
        
        # Generate hypotheses (always fresh) - pass Pydantic objects
        logger.info("Generating hypotheses...")
        kb_items = load_all_kb_items()
        investigator_svc = LeadInvestigatorService(llm=llm, model="gpt-4.1-mini")
        hypotheses_obj = investigator_svc.run(
            patient_info=patient_info_obj,
            triage_result=triage_obj,
            kb_items=kb_items
        )
        hypotheses = hypotheses_obj.model_dump()
        
        # Write hypotheses to sheet
        hypotheses_cell = f"{hypotheses_col}{row}"
        hypotheses_str = json.dumps(hypotheses, separators=(",", ":"))
        sheets_service.write_to_sheet(f"{sheet_name}!{hypotheses_cell}", [[hypotheses_str]])
        logger.info(f"Hypotheses written to {hypotheses_cell}")
        
        # Generate resources
        logger.info("Generating resources...")
        resource_svc = ResourceGenerationService(llm=llm)
        zipcode = resource_svc.extract_zipcode(summary_text)
        
        if zipcode:
            resources = resource_svc.generate_resources(summary_text)
            logger.info(f"Resources generated for zipcode {zipcode}")
        else:
            resources = {
                "status": "skipped",
                "reason": "No zipcode found",
                "data": {}
            }
            logger.info("No zipcode found, skipping resources")

        # Write resources to sheet
        resources_cell = f"{resources_col}{row}"
        resources_str = json.dumps(resources, separators=(",", ":"))
        sheets_service.write_to_sheet(f"{sheet_name}!{resources_cell}", [[resources_str]])
        logger.info(f"Resources written to {resources_cell}")
        
        # Create Google Doc report - merge parsed info with sheet fields
        logger.info("Creating Google Doc...")
        patient_info_dict = patient_info_obj.model_dump()
        patient_info_dict["patient_id"] = patient_id  # Keep for internal use, just not displayed in doc
        patient_info_dict["date_submitted"] = date_submitted if date_submitted else None
        patient_info_dict["parent_name"] = parent_name if parent_name else None
        patient_info_dict["email"] = email if email else None
        patient_info_dict["zipcode"] = zipcode if zipcode else None
        
        # Build patient-friendly triage report for the Doc
        triage_report = build_patient_report(triage_obj)
        
        try:
            doc_url = docs_service.create_patient_report(
                patient_info=patient_info_dict,
                triage_result=triage_report,
                hypotheses=hypotheses,
                resources=resources,
                folder_id=GOOGLE_DRIVE_FOLDER_ID
            )
            logger.info(f"Report generated successfully: {doc_url}")
        except Exception as e:
            logger.warning(f"Failed to create Google Doc: {e}")
            # Fallback: return link to the Google Sheet instead
            doc_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=0&range={row}:{row}"
            logger.info(f"Using Google Sheet link as fallback: {doc_url}")
        
        # Ensure sheet has enough columns (AL = 38, AM = 39, so we need at least 40 columns)
        try:
            sheets_service.expand_sheet_columns(sheet_name, 40)
        except Exception as e:
            logger.warning(f"Could not expand sheet columns: {e}")
        
        # Write report URL and timestamp to sheet
        report_url_cell = f"{report_url_col}{row}"
        report_generated_cell = f"{report_generated_col}{row}"
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sheets_service.write_to_sheet(f"{sheet_name}!{report_url_cell}", [[doc_url]])
        sheets_service.write_to_sheet(f"{sheet_name}!{report_generated_cell}", [[current_timestamp]])
        logger.info(f"Report URL written to {report_url_cell}, timestamp to {report_generated_cell}")
        
        return {
            "status": "success",
            "report_url": doc_url,
            "patient_id": patient_id,
            "row": row,
            "data_written_to_sheet": {
                "triage_cell": triage_cell,
                "hypotheses_cell": hypotheses_cell
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.post("/email-report/{row}")
def email_report(
    row: int,
    sheet_name: str = "Processed Data",
    email_col: str = "D",
    parent_name_col: str = "C",
    report_url_col: str = "AK",
    report_emailed_col: str = "AM"
):
    """
    Share the report with the email and send an email notification.
    
    Args:
        row: Row number in the sheet
        sheet_name: Name of the sheet
        email_col: Column containing email address
        parent_name_col: Column containing parent name
        report_url_col: Column containing report URL
        
    Returns:
        Status of email operation
    """
    try:
        # Get email and report URL from sheet
        email_cell = f"{email_col}{row}"
        parent_name_cell = f"{parent_name_col}{row}"
        report_url_cell = f"{report_url_col}{row}"
        
        email = sheets_service.get_cell_value(sheet_name, email_cell)
        parent_name = sheets_service.get_cell_value(sheet_name, parent_name_cell)
        report_url = sheets_service.get_cell_value(sheet_name, report_url_cell)
        
        if not email:
            raise HTTPException(
                status_code=404,
                detail=f"No email found at row {row}"
            )
        
        if not report_url:
            raise HTTPException(
                status_code=404,
                detail=f"No report URL found at row {row}. Please generate a report first."
            )
        
        # Extract document ID from URL
        doc_id = None
        if "docs.google.com/document/d/" in report_url:
            doc_id = report_url.split("/d/")[1].split("/")[0]
        
        if not doc_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid report URL format"
            )
        
        # Share the document with the email
        logger.info(f"Sharing document {doc_id} with {email}")
        docs_service.drive_service.permissions().create(
            fileId=doc_id,
            body={
                'type': 'user',
                'role': 'reader',
                'emailAddress': email
            },
            sendNotificationEmail=True,
            emailMessage=f"Hello {parent_name or 'there'},\n\nYour informational report is ready. You can access it using the link below:\n\n{report_url}\n\nBest regards,\nKindroot Team"
        ).execute()
        
        logger.info(f"Report shared with {email}")
        
        # Write email timestamp to sheet
        report_emailed_cell = f"{report_emailed_col}{row}"
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheets_service.write_to_sheet(f"{sheet_name}!{report_emailed_cell}", [[current_timestamp]])
        logger.info(f"Email timestamp written to {report_emailed_cell}")
        
        return {
            "status": "success",
            "email": email,
            "report_url": report_url,
            "emailed_at": current_timestamp,
            "message": f"Report shared with {email}"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error emailing report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to email report: {str(e)}"
        )
