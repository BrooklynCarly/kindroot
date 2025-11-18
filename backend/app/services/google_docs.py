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
            
            # Build the content requests
            main_requests, toc_requests = self._build_report_content(patient_info, triage_result, hypotheses, actionable_steps, resources)
            
            # Update the document with main content first
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': main_requests}
            ).execute()
            
            # Then update with TOC (bookmarks and links) in a second batch
            if toc_requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': toc_requests}
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
        actionable_steps: Dict[str, Any],
        resources: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Build the batch update requests for document content.
        
        Returns:
            Tuple of (main_requests, toc_requests) - TOC requests must be applied after main content
        """
        requests = []
        index = 1  # Start after the title
        heading2_sections = []  # Track HEADING_2 sections for TOC
        
        # Helper to add text with optional styling
        def add_paragraph(text: str, style: str = "NORMAL_TEXT", index_offset: int = 0, page_break_before: bool = False):
            nonlocal index
            insert_index = index + index_offset
            
            # Add page break before if requested
            if page_break_before:
                requests.append({
                    'insertPageBreak': {
                        'location': {'index': insert_index}
                    }
                })
                index += 1
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
                
                # Track HEADING_2 sections for TOC
                if style == "HEADING_2":
                    heading2_sections.append({
                        'text': text,
                        'index': insert_index
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
        
        # Helper to create a table
        def add_table(rows: int, cols: int) -> int:
            """Insert a table and return the starting index of the table."""
            nonlocal index
            table_start = index
            requests.append({
                'insertTable': {
                    'rows': rows,
                    'columns': cols,
                    'location': {'index': table_start}
                }
            })
            # After inserting a table with r rows and c cols, the index advances by:
            # r * c * 2 + 1 (each cell has 2 chars: content + end-of-cell marker, plus 1 for table end)
            index += rows * cols * 2 + 1
            return table_start
        
        # Helper to insert text into a table cell
        def insert_table_cell_text(row: int, col: int, text: str, table_start: int):
            """Insert text into a specific table cell."""
            # Calculate cell position: table_start + 1 + (row * num_cols + col) * 2
            # We'll need to track the number of columns
            nonlocal index
            # For now, we'll add this to a separate list and apply after table creation
            pass
        
        # Add title and disclaimer block at the top
        add_paragraph("Parent Report", "HEADING_1")
        add_paragraph("")
        add_paragraph("We are parents helping parents have productive conversations with their pediatricians.")
        add_paragraph("")
        add_paragraph("What this is—and isn't: This report shares information and resources to discuss with your healthcare provider. It is not medical advice, a diagnosis, or a treatment plan.")
        add_paragraph("")
        add_paragraph("What to know: Your kiddo is unique. What helps one child may not fit another, but we aim to find information from families with kids similar to yours. You'll see ideas from reputable clinical sources and from families who've been there. Use these insights to prepare for conversations with your child's clinician.")
        add_paragraph("")
        
        # Demographic Information Section
        add_paragraph("Your Information", "HEADING_2", page_break_before=True)
        
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
        add_paragraph("")
        # Use correct field names from PatientParse model
        age = patient_info.get('patient_age') or patient_info.get('age', 'N/A')
        sex = patient_info.get('patient_sex') or patient_info.get('gender', 'N/A')
        diagnosis = patient_info.get('diagnosis_status', 'N/A')
        
        add_paragraph(f"Child's Age: {age}")
        add_paragraph(f"Sex: {sex}")
        add_paragraph(f"Diagnosis Status: {diagnosis}")
        
        # Top Family Priorities
        top_priorities = patient_info.get('top_family_priorities')
        if top_priorities and isinstance(top_priorities, list) and len(top_priorities) > 0:
            add_paragraph("")
            add_paragraph("Top Family Priorities:")
            for priority in top_priorities:
                add_paragraph(f"• {priority}")
        
        # # Triage Results Section (supports both legacy and new schemas)
        # triage_title = triage_result.get('summary_title') or "Safety & Triage Summary"
        # add_paragraph(triage_title, "HEADING_1")
        # triage_message = triage_result.get('message')
        # if triage_message:
        #     add_paragraph(triage_message)
        #     add_paragraph("")
        
        # urgent_items = triage_result.get('urgent_items', []) or []
        # if urgent_items:
        #     add_paragraph("Urgent Items:", "HEADING_2")
        #     for i, item in enumerate(urgent_items, 1):
        #         add_paragraph(f"{i}. {item.get('category', item.get('title', 'Unknown Category'))}", "HEADING_3")
        #         add_paragraph(f"Severity: {item.get('severity', item.get('level', 'N/A'))}")
        #         add_paragraph(f"Evidence: {item.get('evidence', item.get('details', 'N/A'))}")
        #         add_paragraph(f"Why It Matters: {item.get('why_it_matters', item.get('why', 'N/A'))}")
        #         add_paragraph(f"Next Step: {item.get('next_step', item.get('action', 'N/A'))}")
        #         add_paragraph("")
        
        # # Moderate items (new schema)
        # moderate_items = triage_result.get('moderate_items', []) or []
        # if moderate_items:
        #     add_paragraph("Moderate Items:", "HEADING_2")
        #     for i, item in enumerate(moderate_items, 1):
        #         add_paragraph(f"{i}. {item.get('category', item.get('title', 'Unknown Category'))}", "HEADING_3")
        #         add_paragraph(f"Severity: {item.get('severity', item.get('level', 'N/A'))}")
        #         add_paragraph(f"Evidence: {item.get('evidence', item.get('details', 'N/A'))}")
        #         add_paragraph(f"Why It Matters: {item.get('why_it_matters', item.get('why', 'N/A'))}")
        #         add_paragraph(f"Next Step: {item.get('next_step', item.get('action', 'N/A'))}")
        #         add_paragraph("")
        
        # Hypotheses Section
        # Top 3 Potential Root Causes (parent-friendly)
        add_paragraph("Top 3 Potential Root Causes", "HEADING_2", page_break_before=True)
        hypotheses_list = hypotheses.get('hypotheses', [])
        if hypotheses_list:
            for i, hyp in enumerate(hypotheses_list[:3], 1):
                # Support both schemas: name/rationale and hypothesis/supporting_evidence
                title = hyp.get('name') or hyp.get('hypothesis') or 'Unknown'
                add_paragraph(f"{i}. {title}", "HEADING_3")
                rationale = hyp.get('rationale') or hyp.get('supporting_evidence') or 'N/A'
                add_paragraph(f"Why this might fit (evidence): {rationale}")
                tp = hyp.get('talking_points', []) or []
                if tp:
                    add_paragraph("Talking points for your pediatrician", "HEADING_4")
                    for b in tp:
                        add_paragraph(f"• {b}")
                tests = hyp.get('recommended_tests', []) or []
                if tests:
                    add_paragraph("Recommended tests to discuss or consider", "HEADING_4")
                    for t in tests:
                        line = f"• {t.get('name','Test')}"
                        if t.get('category'): line += f" — {t['category']}"
                        if t.get('order_type') == 'self_purchase': line += " (at-home or self-purchase)"
                        elif t.get('order_type') == 'either': line += " (order via clinician or self-purchase)"
                        if t.get('notes'): line += f" — {t['notes']}"
                        add_paragraph(line)
                        if t.get('purchase_url'):
                            add_link("Link", t['purchase_url'])
                add_paragraph("")
        else:
            add_paragraph("No root causes available")
            add_paragraph("")
        
        # Next steps and uncertainties are at the top level, not per hypothesis
        uncertainties = hypotheses.get('uncertainties', [])
        if uncertainties:
            add_paragraph("Uncertainties", "HEADING_3")
            for i, uncertainty in enumerate(uncertainties, 1):
                add_paragraph(f"{i}. {uncertainty}")
            add_paragraph("")
        
        next_steps = hypotheses.get('next_steps', [])
        if next_steps:
            add_paragraph("Recommended Next Steps", "HEADING_3")
            for i, step in enumerate(next_steps, 1):
                add_paragraph(f"{i}. {step}")
            add_paragraph("")
        
        # Actionable Steps Section
        add_paragraph("What Others Have Tried", "HEADING_2", page_break_before=True)
        add_paragraph("Based on the patterns identified above, here are approaches other families with similar situations have explored. This information is for discussion with your pediatrician—not medical advice. Always consult your care team before making changes.")
        add_paragraph("")
        
        # Implementation guidance
        impl_guidance = actionable_steps.get('implementation_guidance')
        if impl_guidance:
            add_paragraph("Getting Started", "HEADING_3")
            add_paragraph(impl_guidance)
            add_paragraph("")
        
        # Recommended approaches
        approaches = actionable_steps.get('recommended_approaches', [])
        if approaches:
            add_paragraph("Important: Discuss any new changes with your pediatrician", "NORMAL_TEXT")
            add_paragraph("")
            
            # Create table: 1 header row + N data rows, 7 columns
            num_rows = len(approaches) + 1
            num_cols = 6
            table_start_index = index
            
            # Insert the table
            requests.append({
                'insertTable': {
                    'rows': num_rows,
                    'columns': num_cols,
                    'location': {'index': table_start_index}
                }
            })
            
            # Calculate new index after table insertion
            # Each cell takes 2 characters (content + end-of-cell), plus 1 for table end
            index = table_start_index + (num_rows * num_cols * 2) + 1
            
            # Now populate the table cells using separate requests
            # Header row (row 0)
            headers = [
                "Intervention",
                "Why This May Help",
                "May Help With",
                "What Others Did",
                "What Families Tracked",
                "Decision Points",
                "Considerations"
            ]
            
            for col_idx, header_text in enumerate(headers):
                # Calculate cell position: table_start + 1 + (row * num_cols + col) * 2
                cell_index = table_start_index + 1 + (0 * num_cols + col_idx) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': header_text
                    }
                })
                # Make header bold
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': cell_index,
                            'endIndex': cell_index + len(header_text)
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            # Data rows
            for row_idx, intervention in enumerate(approaches, start=1):
                # Column 0: Intervention name
                name = intervention.get('intervention_name', 'Unknown')
                cell_index = table_start_index + 1 + (row_idx * num_cols + 0) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': name
                    }
                })
                
                # Column 1: Why this may help
                why_help = intervention.get('why_this_may_help', 'N/A')
                cell_index = table_start_index + 1 + (row_idx * num_cols + 1) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': why_help
                    }
                })
                
                # Column 2: Addresses concerns
                concerns = intervention.get('addresses_multiple_concerns', [])
                concerns_text = ', '.join(concerns) if concerns else 'N/A'
                cell_index = table_start_index + 1 + (row_idx * num_cols + 2) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': concerns_text
                    }
                })
                
                # Column 3: What others did
                what_done = intervention.get('what_others_have_done', [])
                what_done_text = '\n'.join(f"• {item}" for item in what_done) if what_done else 'N/A'
                cell_index = table_start_index + 1 + (row_idx * num_cols + 3) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': what_done_text
                    }
                })
                
                # Column 4: What families tracked
                tracked = intervention.get('what_families_tracked', [])
                tracked_text = '\n'.join(f"• {item}" for item in tracked) if tracked else 'N/A'
                cell_index = table_start_index + 1 + (row_idx * num_cols + 4) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': tracked_text
                    }
                })
                
                # Column 5: Decision points
                decision_points = intervention.get('common_decision_points', [])
                decision_text = '\n'.join(f"• {item}" for item in decision_points) if decision_points else 'N/A'
                cell_index = table_start_index + 1 + (row_idx * num_cols + 5) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': decision_text
                    }
                })
                
                # Column 6: Considerations
                considerations = intervention.get('considerations', [])
                considerations_text = '\n'.join(f"• {item}" for item in considerations) if considerations else 'N/A'
                cell_index = table_start_index + 1 + (row_idx * num_cols + 6) * 2
                requests.append({
                    'insertText': {
                        'location': {'index': cell_index},
                        'text': considerations_text
                    }
                })
            
            # Add all cell updates in reverse order to prevent index shifting
            requests.extend(reversed(cell_updates))
            
            # Style the table to fit page width
            # Set table width to match page margins (8.5" page with 1" margins = 6.5" content width)
            table_width_magnitude = 468  # 6.5 inches * 72 points per inch = 468 points
            
            # Set column widths to distribute evenly across page width
            column_width = table_width_magnitude / num_cols
            
            for col_idx in range(num_cols):
                requests.append({
                    'updateTableColumnProperties': {
                        'tableStartLocation': {'index': table_start_index},
                        'columnIndices': [col_idx],
                        'tableColumnProperties': {
                            'widthType': 'FIXED_WIDTH',
                            'width': {
                                'magnitude': column_width,
                                'unit': 'PT'
                            }
                        },
                        'fields': 'widthType,width'
                    }
                })
            
            # Add spacing after table
            add_paragraph("")
        
        # General notes
        general_notes = actionable_steps.get('general_notes', [])
        if general_notes:
            add_paragraph("Important Reminders", "HEADING_3")
            for note in general_notes:
                add_paragraph(f"• {note}")
            add_paragraph("")
        
        # Resources Section
        add_paragraph("Local Resources", "HEADING_2", page_break_before=True)
        
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
                    # add_paragraph(f"Metropolitan Area: {summary_report.get('metropolitan_status', 'N/A')}")
                    add_paragraph(f"Search Radius: {summary_report.get('search_radius_miles', 'N/A')} miles")
                    add_paragraph("")
                
                # State Early Intervention Program
                ei_program = summary_report.get('state_early_intervention_program', {})
                if ei_program:
                    add_paragraph("State Early Intervention Program", "HEADING_4")
                    website = ei_program.get('website')
                    if website:
                        add_link("Website", website)
                    if ei_program.get('contact_phone'):
                        add_paragraph(f"Phone: {ei_program.get('contact_phone')}")
                    if ei_program.get('contact_email'):
                        add_paragraph(f"Email: {ei_program.get('contact_email')}")
                
                # Pediatricians / Developmental Pediatrics
                peds = summary_report.get('pediatricians', [])
                if peds:
                    add_paragraph("Pediatricians / Developmental Pediatrics", "HEADING_4")
                    for i, provider in enumerate(peds, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown Provider')}", "HEADING_5")
                        rating = provider.get('rating'); reviews = provider.get('review_count')
                        if rating is not None:
                            txt = f"Rating: {rating:.1f}/5.0"
                            if reviews: txt += f" ({reviews} reviews)"
                            add_paragraph(txt)
                        if provider.get('distance_miles') is not None:
                            add_paragraph(f"Distance: {provider['distance_miles']:.1f} miles")
                        add_paragraph(f"Address: {provider.get('address','N/A')}")
                        if provider.get('phone'): add_paragraph(f"Phone: {provider['phone']}")
                        if provider.get('website'): add_link("Website", provider['website'])
                        if provider.get('specialties'):
                            add_paragraph("Specialties: " + ', '.join(provider['specialties']))
                        add_paragraph("")

                # Behavioral Providers
                behavioral_providers = summary_report.get('behavioral_providers', [])
                if behavioral_providers:
                    add_paragraph("Behavioral Providers", "HEADING_4")
                    for i, provider in enumerate(behavioral_providers, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown Provider')}", "HEADING_5")
                        
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

                # Speech Providers
                speech_providers = summary_report.get('speech_providers', [])
                if speech_providers:
                    add_paragraph("Speech Providers", "HEADING_4")
                    for i, provider in enumerate(speech_providers, 1):
                        add_paragraph(f"{i}. {provider.get('name', 'Unknown Provider')}", "HEADING_5")
                        
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
                
                # If undiagnosed, add "Where to obtain an evaluation"
                diag_status = (patient_info.get('diagnosis_status') or "").strip().lower()
                if diag_status in ("", "undiagnosed", "unknown", "none"):
                    add_paragraph("Where to Obtain a Diagnostic Evaluation", "HEADING_3")
                    add_paragraph("If you do not yet have an evaluation, here is a place to get started:")
                    add_link("ADG Cares", "https://www.adgcares.com/")

                # Additional Notes
                notes = summary_report.get('additional_notes', [])
                if notes:
                    add_paragraph("Additional Notes", "HEADING_4")
                    for note in notes:
                        add_paragraph(f"• {note}")
                    add_paragraph("")
            else:
                add_paragraph("No resources available for this location")
        
        # Return main requests only (TOC disabled for now due to API limitations)
        return requests, []
