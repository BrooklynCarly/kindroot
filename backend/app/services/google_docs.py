"""
Google Docs service for creating formatted patient reports.
Supports two auth modes:
- Service Account (default): uses backend/credentials.json
- OAuth (set DOCS_AUTH_MODE=oauth): uses client_secret.json and caches token.json
"""
from typing import Any, Dict, List
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
from fastapi import HTTPException
import os
import json

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
]

CREDENTIALS_FILE = Path("/Users/carly/projects/kindroot/backend/credentials.json")
# OAuth files (used only if DOCS_AUTH_MODE=oauth)
OAUTH_CLIENT_SECRETS = Path(os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS", "/Users/carly/projects/kindroot/backend/client_secret.json"))
OAUTH_TOKEN_FILE = Path("/Users/carly/projects/kindroot/backend/token.json")


class GoogleDocsService:
    def __init__(self):
        """Initialize the Google Docs service."""
        self.creds = self._get_credentials()
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def _get_credentials(self):
        """
        Build credentials based on DOCS_AUTH_MODE environment variable.
        - If DOCS_AUTH_MODE=oauth: use InstalledAppFlow (user account)
        - Else: use Service Account credentials
        """
        auth_mode = os.getenv("DOCS_AUTH_MODE", "service").lower()
        if auth_mode == "oauth":
            # OAuth user flow
            creds: Credentials | None = None
            if OAUTH_TOKEN_FILE.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(OAUTH_TOKEN_FILE), SCOPES)
                except Exception:
                    creds = None
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Failed to refresh OAuth token: {e}")
                else:
                    if not OAUTH_CLIENT_SECRETS.exists():
                        raise FileNotFoundError(
                            f"OAuth client secrets not found at {OAUTH_CLIENT_SECRETS}. Set GOOGLE_OAUTH_CLIENT_SECRETS or place client_secret.json in backend/."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_SECRETS), SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                try:
                    with open(OAUTH_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                except Exception:
                    pass
            return creds
        # Default: service account
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_FILE}")
        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE), scopes=SCOPES
        )
        return creds

    def create_patient_report(
        self,
        patient_info: Dict[str, Any],
        triage_result: Dict[str, Any],
        hypotheses: Dict[str, Any],
        resources: Dict[str, Any],
        folder_id: str = None
    ) -> str:
        """
        Create a formatted Google Doc with patient report.
        
        Args:
            patient_info: Patient information dictionary
            triage_result: Triage analysis results
            hypotheses: Lead investigator hypotheses
            resources: Local autism resources
            folder_id: Optional Google Drive folder ID to create the doc in
            
        Returns:
            URL of the created Google Doc
        """
        try:
            # Create a new document
            parent_name = patient_info.get('parent_name', 'Unknown')
            date_submitted = patient_info.get('date_submitted', 'Unknown')
            doc_title = f"Informational Report - {parent_name} - {date_submitted}"
            
            # Create the document using Drive API (works with both OAuth and SA)
            file_metadata = {
                'name': doc_title,
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            # If folder_id is provided, create directly in that folder
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Create empty document via Drive API directly (in folder if provided)
            file = self.drive_service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True  # Support shared drives
            ).execute()
            doc_id = file.get('id')
            
            # Build the content requests
            requests = self._build_report_content(patient_info, triage_result, hypotheses, resources)
            
            # Update the document with content
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            # Make the document accessible (anyone with link can view)
            self.drive_service.permissions().create(
                fileId=doc_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
            # Return the document URL
            return f"https://docs.google.com/document/d/{doc_id}/edit"
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating Google Doc: {str(e)}"
            )

    def _build_report_content(
        self,
        patient_info: Dict[str, Any],
        triage_result: Dict[str, Any],
        hypotheses: Dict[str, Any],
        resources: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build the batch update requests for document content.
        
        Returns:
            List of batch update requests
        """
        requests = []
        index = 1  # Start after the title
        
        # Helper to add text with optional styling
        def add_paragraph(text: str, style: str = "NORMAL_TEXT", index_offset: int = 0):
            nonlocal index
            insert_index = index + index_offset
            requests.append({
                'insertText': {
                    'location': {'index': insert_index},
                    'text': text + '\n'
                }
            })
            if style != "NORMAL_TEXT":
                text_length = len(text)
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': insert_index,
                            'endIndex': insert_index + text_length
                        },
                        'paragraphStyle': {
                            'namedStyleType': style
                        },
                        'fields': 'namedStyleType'
                    }
                })
            index += len(text) + 1
        
        # Helper to add text with a clickable hyperlink
        def add_link(label: str, url: str):
            nonlocal index
            insert_index = index
            full_text = f"{label}: {url}\n"
            
            # Insert the text
            requests.append({
                'insertText': {
                    'location': {'index': insert_index},
                    'text': full_text
                }
            })
            
            # Make the URL portion clickable
            url_start = insert_index + len(label) + 2  # After "label: "
            url_end = url_start + len(url)
            
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': url_start,
                        'endIndex': url_end
                    },
                    'textStyle': {
                        'link': {'url': url},
                        'foregroundColor': {
                            'color': {
                                'rgbColor': {
                                    'blue': 1.0,
                                    'green': 0.0,
                                    'red': 0.0
                                }
                            }
                        },
                        'underline': True
                    },
                    'fields': 'link,foregroundColor,underline'
                }
            })
            
            index += len(full_text)
        
        # Add disclaimer block at the top
        add_paragraph("Welcome to KindRoot, we're glad you found us. We're hoping this is your start to feeling supported along the evolving journey of helping your kiddo experience their best self possible.")
        
        add_paragraph("What this is—and isn't", "HEADING_2")
        add_paragraph("This report shares general information to help parents and caregivers learn about autism spectrum disorder (ASD) and find resources. It is not medical advice, a diagnosis, or a treatment plan.")
        
        add_paragraph("What to know", "HEADING_2")
        add_paragraph("Every child with ASD is unique. What helps one child may not fit another.")
        add_paragraph("")  # Empty line for spacing
        add_paragraph("You'll see ideas from reputable clinical sources and from families who've been there. Use these insights to prepare for conversations with your child's clinician.")
        add_paragraph("")  # Empty line for spacing
        
        # Demographic Information Section
        add_paragraph("Demographic Information", "HEADING_1")
        
        # Parent/contact info from sheet
        date_submitted = patient_info.get('date_submitted')
        if date_submitted:
            add_paragraph(f"Date Submitted: {date_submitted}")
        
        parent_name = patient_info.get('parent_name')
        if parent_name:
            add_paragraph(f"Parent Name: {parent_name}")
        
        email = patient_info.get('email')
        if email:
            add_paragraph(f"Email: {email}")
        
        zipcode = patient_info.get('zipcode')
        if zipcode:
            add_paragraph(f"Zipcode: {zipcode}")
        
        # Use correct field names from PatientParse model
        age = patient_info.get('patient_age') or patient_info.get('age', 'N/A')
        sex = patient_info.get('patient_sex') or patient_info.get('gender', 'N/A')
        diagnosis = patient_info.get('diagnosis_status', 'N/A')
        
        add_paragraph(f"Child's Age: {age}")
        add_paragraph(f"Sex: {sex}")
        add_paragraph(f"Diagnosis Status: {diagnosis}")
        add_paragraph("")
        
        # Triage Results Section (supports both legacy and new schemas)
        triage_title = triage_result.get('summary_title') or "Safety & Triage Summary"
        add_paragraph(triage_title, "HEADING_1")
        triage_message = triage_result.get('message')
        if triage_message:
            add_paragraph(triage_message)
            add_paragraph("")
        
        urgent_items = triage_result.get('urgent_items', []) or []
        if urgent_items:
            add_paragraph("Urgent Items:", "HEADING_2")
            for i, item in enumerate(urgent_items, 1):
                add_paragraph(f"{i}. {item.get('category', item.get('title', 'Unknown Category'))}", "HEADING_3")
                add_paragraph(f"Severity: {item.get('severity', item.get('level', 'N/A'))}")
                add_paragraph(f"Evidence: {item.get('evidence', item.get('details', 'N/A'))}")
                add_paragraph(f"Why It Matters: {item.get('why_it_matters', item.get('why', 'N/A'))}")
                add_paragraph(f"Next Step: {item.get('next_step', item.get('action', 'N/A'))}")
                add_paragraph("")
        
        # Moderate items (new schema)
        moderate_items = triage_result.get('moderate_items', []) or []
        if moderate_items:
            add_paragraph("Moderate Items:", "HEADING_2")
            for i, item in enumerate(moderate_items, 1):
                add_paragraph(f"{i}. {item.get('category', item.get('title', 'Unknown Category'))}", "HEADING_3")
                add_paragraph(f"Severity: {item.get('severity', item.get('level', 'N/A'))}")
                add_paragraph(f"Evidence: {item.get('evidence', item.get('details', 'N/A'))}")
                add_paragraph(f"Why It Matters: {item.get('why_it_matters', item.get('why', 'N/A'))}")
                add_paragraph(f"Next Step: {item.get('next_step', item.get('action', 'N/A'))}")
                add_paragraph("")
        
        # Hypotheses Section
        add_paragraph("Clinical Hypotheses", "HEADING_1")
        hypotheses_list = hypotheses.get('hypotheses', [])
        if hypotheses_list:
            for i, hyp in enumerate(hypotheses_list, 1):
                # Support both schemas: name/rationale and hypothesis/supporting_evidence
                title = hyp.get('name') or hyp.get('hypothesis') or 'Unknown'
                add_paragraph(f"{i}. {title}", "HEADING_3")
                add_paragraph(f"Confidence: {hyp.get('confidence', 'N/A')}")
                rationale = hyp.get('rationale') or hyp.get('supporting_evidence') or 'N/A'
                add_paragraph(f"Rationale / Evidence: {rationale}")
                add_paragraph("")
        else:
            add_paragraph("No hypotheses available")
            add_paragraph("")
        
        # Next steps and uncertainties are at the top level, not per hypothesis
        uncertainties = hypotheses.get('uncertainties', [])
        if uncertainties:
            add_paragraph("Uncertainties", "HEADING_2")
            for i, uncertainty in enumerate(uncertainties, 1):
                add_paragraph(f"{i}. {uncertainty}")
            add_paragraph("")
        
        next_steps = hypotheses.get('next_steps', [])
        if next_steps:
            add_paragraph("Recommended Next Steps", "HEADING_2")
            for i, step in enumerate(next_steps, 1):
                add_paragraph(f"{i}. {step}")
            add_paragraph("")
        
        # Resources Section
        add_paragraph("Local Resources", "HEADING_1")
        
        # Check if resources generation was skipped
        if resources.get('status') == 'skipped':
            add_paragraph(f"Resource lookup skipped: {resources.get('reason', 'No reason provided')}")
        elif resources.get('status') == 'error':
            add_paragraph(f"Error generating resources: {resources.get('message', 'Unknown error')}")
        else:
            # Resources come from ResourceFinderResult: resources['summary_report']
            summary_report = resources.get('summary_report', {})
            
            if summary_report:
                # Patient location
                location = summary_report.get('patient_location', {})
                if location:
                    add_paragraph(f"Location: {location.get('city', 'N/A')}, {location.get('state', 'N/A')} {location.get('zip_code', 'N/A')}")
                    add_paragraph(f"Metropolitan Area: {summary_report.get('metropolitan_status', 'N/A')}")
                    add_paragraph(f"Search Radius: {summary_report.get('search_radius_miles', 'N/A')} miles")
                    add_paragraph("")
                
                # State Early Intervention Program
                ei_program = summary_report.get('state_early_intervention_program', {})
                if ei_program:
                    add_paragraph("State Early Intervention Program", "HEADING_2")
                    website = ei_program.get('website')
                    if website:
                        add_link("Website", website)
                    if ei_program.get('contact_phone'):
                        add_paragraph(f"Phone: {ei_program.get('contact_phone')}")
                    if ei_program.get('contact_email'):
                        add_paragraph(f"Email: {ei_program.get('contact_email')}")
                    add_paragraph("")
                
                # Behavioral Providers
                behavioral_providers = summary_report.get('behavioral_providers', [])
                if behavioral_providers:
                    add_paragraph("Behavioral Providers", "HEADING_2")
                    for i, provider in enumerate(behavioral_providers, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown Provider')}", "HEADING_3")
                        
                        # Rating and reviews
                        rating = provider.get('rating')
                        review_count = provider.get('review_count')
                        if rating is not None:
                            rating_text = f"Rating: {rating:.1f}/5.0"
                            if review_count:
                                rating_text += f" ({review_count} reviews)"
                            add_paragraph(rating_text)
                        
                        # Distance
                        distance = provider.get('distance_miles')
                        if distance is not None:
                            add_paragraph(f"Distance: {distance:.1f} miles")
                        
                        add_paragraph(f"Address: {provider.get('address', 'N/A')}")
                        
                        if provider.get('phone'):
                            add_paragraph(f"Phone: {provider.get('phone')}")
                        
                        website = provider.get('website')
                        if website:
                            add_link("Website", website)
                        
                        if provider.get('specialties'):
                            specialties = ', '.join(provider.get('specialties', []))
                            add_paragraph(f"Specialties: {specialties}")
                        add_paragraph("")
                
                # Speech Providers
                speech_providers = summary_report.get('speech_providers', [])
                if speech_providers:
                    add_paragraph("Speech Providers", "HEADING_2")
                    for i, provider in enumerate(speech_providers, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown Provider')}", "HEADING_3")
                        
                        # Rating and reviews
                        rating = provider.get('rating')
                        review_count = provider.get('review_count')
                        if rating is not None:
                            rating_text = f"Rating: {rating:.1f}/5.0"
                            if review_count:
                                rating_text += f" ({review_count} reviews)"
                            add_paragraph(rating_text)
                        
                        # Distance
                        distance = provider.get('distance_miles')
                        if distance is not None:
                            add_paragraph(f"Distance: {distance:.1f} miles")
                        
                        add_paragraph(f"Address: {provider.get('address', 'N/A')}")
                        
                        if provider.get('phone'):
                            add_paragraph(f"Phone: {provider.get('phone')}")
                        
                        website = provider.get('website')
                        if website:
                            add_link("Website", website)
                        
                        if provider.get('specialties'):
                            specialties = ', '.join(provider.get('specialties', []))
                            add_paragraph(f"Specialties: {specialties}")
                        add_paragraph("")
                
                # Additional Notes
                notes = summary_report.get('additional_notes', [])
                if notes:
                    add_paragraph("Additional Notes", "HEADING_2")
                    for note in notes:
                        add_paragraph(f"• {note}")
                    add_paragraph("")
            else:
                add_paragraph("No resources available for this location")
        
        return requests
