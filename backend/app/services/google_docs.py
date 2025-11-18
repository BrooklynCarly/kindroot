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
import base64

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
        
        Gracefully handles OAuth token expiration by falling back to service account.
        """
        auth_mode = os.getenv("DOCS_AUTH_MODE", "service").lower()
        if auth_mode == "oauth":
            # OAuth user flow - try to use it, but fall back if it fails
            try:
                creds: Credentials | None = None
                if OAUTH_TOKEN_FILE.exists():
                    try:
                        creds = Credentials.from_authorized_user_file(str(OAUTH_TOKEN_FILE), SCOPES)
                    except Exception as e:
                        print(f"Warning: Could not load OAuth token file: {e}")
                        creds = None
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            # Save refreshed token
                            with open(OAUTH_TOKEN_FILE, 'w') as token:
                                token.write(creds.to_json())
                        except Exception as e:
                            print(f"⚠️  OAuth token expired or revoked: {e}")
                            print(f"💡 Falling back to service account mode.")
                            print(f"💡 To re-authenticate OAuth, delete {OAUTH_TOKEN_FILE} and set DOCS_AUTH_MODE=oauth")
                            # Fall through to service account mode below
                            creds = None
                    else:
                        if not OAUTH_CLIENT_SECRETS.exists():
                            print(f"Warning: OAuth client secrets not found at {OAUTH_CLIENT_SECRETS}")
                            print(f"Falling back to service account mode.")
                            creds = None
                        else:
                            flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_SECRETS), SCOPES)
                            creds = flow.run_local_server(port=0)
                            # Save the credentials for the next run
                            try:
                                with open(OAUTH_TOKEN_FILE, 'w') as token:
                                    token.write(creds.to_json())
                            except Exception:
                                pass
                
                # If we successfully got OAuth creds, return them
                if creds and creds.valid:
                    return creds
                
                # Otherwise fall through to service account
                print("ℹ️  Using service account for Google Docs API")
                
            except Exception as e:
                print(f"⚠️  OAuth authentication failed: {e}")
                print(f"💡 Falling back to service account mode.")
        # Default: service account
        # Try to get credentials from environment variable first (production)
        credentials_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
        if credentials_base64:
            try:
                # Decode base64 and parse JSON
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                credentials_dict = json.loads(credentials_json)
                creds = service_account.Credentials.from_service_account_info(
                    credentials_dict, scopes=SCOPES
                )
                return creds
            except Exception as e:
                raise ValueError(f"Failed to load credentials from GOOGLE_CREDENTIALS_BASE64: {str(e)}")
        
        # Fall back to local file (development)
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Credentials file not found at {CREDENTIALS_FILE}. "
                "Set GOOGLE_CREDENTIALS_BASE64 environment variable for production."
            )
        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE), scopes=SCOPES
        )
        return creds

    def move_to_folder(self, file_id: str, destination_folder_id: str) -> None:
        """
        Move a Google Drive file to a specified folder.
        
        Args:
            file_id: The ID of the file to move
            destination_folder_id: The ID of the destination folder
        """
        try:
            # Get the file's current parents
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents',
                supportsAllDrives=True
            ).execute()
            
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file to the new folder
            self.drive_service.files().update(
                fileId=file_id,
                addParents=destination_folder_id,
                removeParents=previous_parents,
                fields='id, parents',
                supportsAllDrives=True
            ).execute()
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error moving file to folder: {str(e)}"
            )

    def create_patient_report(
        self,
        patient_info: Dict[str, Any],
        triage_result: Dict[str, Any],
        hypotheses: Dict[str, Any],
        actionable_steps: Dict[str, Any],
        resources: Dict[str, Any],
        folder_id: str = None
    ) -> str:
        """
        Create a formatted Google Doc with patient report.
        
        Args:
            patient_info: Patient information dictionary
            triage_result: Triage analysis results
            hypotheses: Lead investigator hypotheses
            actionable_steps: Actionable intervention approaches
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
            
            # Phase 1: Build and execute requests for the main document structure, including empty tables
            structure_requests, table_locations = self._build_structure_requests(
                patient_info, triage_result, hypotheses, actionable_steps, resources
            )
            if structure_requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id, body={'requests': structure_requests}
                ).execute()

            # Phase 2: Build and execute requests to populate the tables
            if table_locations:
                # Get the latest state of the document to find table cell indices
                doc_content = self.docs_service.documents().get(documentId=doc_id, fields='body').execute()
                
                # --- TEMPORARY DIAGNOSTIC LOGGING ---
                import json
                print("--- DOCUMENT BODY STRUCTURE ---")
                print(json.dumps(doc_content, indent=2))
                print("-----------------------------")
                # --- END DIAGNOSTIC LOGGING ---
                
                populate_requests = self._build_table_population_requests(table_locations, doc_content)
                if populate_requests:
                    self.docs_service.documents().batchUpdate(
                        documentId=doc_id, body={'requests': populate_requests}
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

    
    def _build_table_population_requests(self, table_locations: List[Dict], doc_content: Dict) -> List[Dict]:
        """
        Builds requests to populate table cells using the document content to find exact indices.
        This is the robust way to handle table population, avoiding fragile index arithmetic.
        """
        requests = []
        field_labels = ["Why This May Help", "What Others Did", "What Families Tracked", "Decision Points", "Considerations", "Notes"]
        
        intervention_map = {loc['start_index']: loc['intervention'] for loc in table_locations}
        
        doc_body_content = doc_content.get('body', {}).get('content', [])
        for element in doc_body_content:
            if 'table' in element and element['startIndex'] in intervention_map:
                table_start_index = element['startIndex']
                intervention = intervention_map[table_start_index]
                table = element['table']
                
                contents = [
                    intervention.get('why_this_may_help', 'N/A'),
                    '\n'.join(f"• {item}" for item in (intervention.get('what_others_have_done') or [])) or 'N/A',
                    '\n'.join(f"• {item}" for item in (intervention.get('what_families_tracked') or [])) or 'N/A',
                    '\n'.join(f"• {item}" for item in (intervention.get('common_decision_points') or [])) or 'N/A',
                    '\n'.join(f"• {item}" for item in (intervention.get('considerations') or [])) or 'N/A',
                    "Review with your healthcare provider"
                ]

                for row_idx, row in enumerate(table.get('tableRows', [])):
                    if row_idx >= len(contents): break

                    # Left cell (label)
                    left_cell = row['tableCells'][0]
                    # The correct insertion point in an empty cell is its endIndex - 1.
                    left_cell_insertion_index = left_cell['endIndex'] - 1
                    requests.append({'insertText': {'location': {'index': left_cell_insertion_index}, 'text': field_labels[row_idx]}})
                    requests.append({'updateTextStyle': {'range': {'startIndex': left_cell_insertion_index, 'endIndex': left_cell_insertion_index + len(field_labels[row_idx])}, 'textStyle': {'bold': True}, 'fields': 'bold'}})

                    # Right cell (content)
                    right_cell = row['tableCells'][1]
                    right_cell_insertion_index = right_cell['endIndex'] - 1
                    requests.append({'insertText': {'location': {'index': right_cell_insertion_index}, 'text': contents[row_idx]}})
        return requests

    def _build_structure_requests(
            self,
            patient_info: Dict[str, Any],
            triage_result: Dict[str, Any],
            hypotheses: Dict[str, Any],
            actionable_steps: Dict[str, Any],
            resources: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Build requests for the main document structure, including empty tables.
        Returns the requests and the locations of the tables for the second phase.
        """
        requests = []
        index = 1
        table_locations = []

        def add_paragraph(text: str, style: str = "NORMAL_TEXT", page_break_before: bool = False):
            nonlocal index
            if page_break_before:
                requests.append({'insertPageBreak': {'location': {'index': index}}})
                index += 1
            requests.append({'insertText': {'location': {'index': index}, 'text': text + '\n'}})
            if style != "NORMAL_TEXT":
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': index, 'endIndex': index + len(text) + 1},
                        'paragraphStyle': {'namedStyleType': style},
                        'fields': 'namedStyleType'
                    }
                })
            index += len(text) + 1

        def add_link(label: str, url: str):
            nonlocal index
            full_text = f"{label}: {url}\n"
            requests.append({'insertText': {'location': {'index': index}, 'text': full_text}})
            url_start = index + len(label) + 2
            url_end = url_start + len(url)
            requests.append({
                'updateTextStyle': {
                    'range': {'startIndex': url_start, 'endIndex': url_end},
                    'textStyle': {
                        'link': {'url': url},
                        'foregroundColor': {'color': {'rgbColor': {'blue': 1.0}}},
                        'underline': True
                    },
                    'fields': 'link,foregroundColor,underline'
                }
            })
            index += len(full_text)

        # --- Main Content ---
        add_paragraph("Parent Report", "HEADING_1")
        add_paragraph("We are parents helping parents have productive conversations with their pediatricians.")
        add_paragraph("What this is—and isn't: This report shares information and resources to discuss with your healthcare provider. It is not medical advice, a diagnosis, or a treatment plan.")
        add_paragraph("What to know: Your kiddo is unique. What helps one child may not fit another, but we aim to find information from families with kids similar to yours. You'll see ideas from reputable clinical sources and from families who've been there. Use these insights to prepare for conversations with your child's clinician.")

        # --- Your Information ---
        add_paragraph("Your Information", "HEADING_2", page_break_before=True)
        if patient_info.get('date_submitted'): add_paragraph(f"Date Submitted: {patient_info['date_submitted']}")
        if patient_info.get('parent_name'): add_paragraph(f"Parent Name: {patient_info['parent_name']}")
        add_paragraph(f"Child's Age: {patient_info.get('patient_age', 'N/A')}")
        top_priorities = patient_info.get('top_family_priorities') or []
        if top_priorities:
            add_paragraph("Top Family Priorities:")
            for p in top_priorities: add_paragraph(f"• {p}")

        # --- Top 3 Potential Root Causes ---
        add_paragraph("Top 3 Potential Root Causes", "HEADING_2", page_break_before=True)
        hypotheses_list = hypotheses.get('hypotheses', [])
        if hypotheses_list:
            for i, hyp in enumerate(hypotheses_list[:3], 1):
                add_paragraph(f"{i}. {hyp.get('name', 'Unknown')}", "HEADING_3")
                add_paragraph(f"Why this might fit (evidence): {hyp.get('rationale', 'N/A')}")
                talking_points = hyp.get('talking_points') or []
                if talking_points:
                    add_paragraph("Talking points for your pediatrician", "HEADING_4")
                    for tp in talking_points: add_paragraph(f"• {tp}")
        else:
            add_paragraph("No root causes available.")

        # --- What Others Have Tried (Actionable Steps) ---
        add_paragraph("What Others Have Tried", "HEADING_2", page_break_before=True)
        add_paragraph("Based on the patterns identified above, here are approaches other families with similar situations have explored. This information is for discussion with your pediatrician—not medical advice. Always consult your care team before making changes.")
        
        # --- Intervention Approaches ---
        approaches = actionable_steps.get('recommended_approaches', [])
        if approaches:
            for i, intervention in enumerate(approaches, 1):
                add_paragraph(f"{i}. {intervention.get('intervention_name', 'Unknown')}", "HEADING_4")
                
                # Why This May Help
                if intervention.get('why_this_may_help'):
                    add_paragraph(f"Why This May Help: {intervention['why_this_may_help']}")
                
                # What Others Have Done
                what_others = intervention.get('what_others_have_done') or []
                if what_others:
                    add_paragraph("What Others Did:")
                    for item in what_others:
                        add_paragraph(f"• {item}")
                
                # What Families Tracked
                what_tracked = intervention.get('what_families_tracked') or []
                if what_tracked:
                    add_paragraph("What Families Tracked:")
                    for item in what_tracked:
                        add_paragraph(f"• {item}")
                
                # Decision Points
                decision_points = intervention.get('common_decision_points') or []
                if decision_points:
                    add_paragraph("Decision Points:")
                    for item in decision_points:
                        add_paragraph(f"• {item}")
                
                # Considerations
                considerations = intervention.get('considerations') or []
                if considerations:
                    add_paragraph("Considerations:")
                    for item in considerations:
                        add_paragraph(f"• {item}")
                
                # Notes
                add_paragraph("Notes: Review with your healthcare provider")
                add_paragraph("")  # Blank line between interventions

        # --- General Notes ---
        general_notes = actionable_steps.get('general_notes') or []
        if general_notes:
            add_paragraph("Important Reminders", "HEADING_3")
            for note in general_notes: add_paragraph(f"• {note}")

        # --- Local Resources ---
        add_paragraph("Local Resources", "HEADING_2", page_break_before=True)
        if resources.get('status') == 'skipped':
            add_paragraph(f"Resource lookup skipped: {resources.get('reason', 'No reason provided')}")
        elif resources.get('status') == 'error':
            add_paragraph(f"Error generating resources: {resources.get('message', 'Unknown error')}")
        else:
            summary_report = resources.get('summary_report', {})
            if summary_report:
                location = summary_report.get('patient_location', {})
                if location:
                    add_paragraph(f"Location: {location.get('city', 'N/A')}, {location.get('state', 'N/A')} {location.get('zip_code', 'N/A')}")
                peds = summary_report.get('pediatricians', [])
                if peds:
                    add_paragraph("Pediatricians / Developmental Pediatrics", "HEADING_4")
                    for i, provider in enumerate(peds, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown')}", "HEADING_5")
                        if provider.get('website'): add_link("Website", provider['website'])
            else:
                add_paragraph("No resources available for this location.")

        return requests, table_locations

