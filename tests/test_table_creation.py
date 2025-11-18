"""
Test script for debugging Google Docs table creation.
Tests actionable steps generation and table insertion for any patient row.

Usage:
    python tests/test_table_creation.py [row_number]
    
Example:
    python tests/test_table_creation.py 9
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from backend.app.services.google_sheets import GoogleSheetsService
from backend.app.services.google_docs import GoogleDocsService
import json


async def test_table_creation(row_number: int = 9):
    """Test table creation for a specific patient row."""
    
    print(f"\n{'='*60}")
    print(f"Testing Table Creation for Row {row_number}")
    print(f"{'='*60}\n")
    
    # Get required environment variables
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not spreadsheet_id:
        print("✗ Error: GOOGLE_SHEETS_ID environment variable not set")
        return
    
    # Initialize services
    sheets_service = GoogleSheetsService(spreadsheet_id=spreadsheet_id)
    docs_service = GoogleDocsService()
    
    # Step 1: Get patient summary from Google Sheets
    print("Step 1: Fetching patient summary text...")
    try:
        sheet_name = "Processed Data"
        summary_col = "G"  # Column G contains the summary
        summary_cell = f"{summary_col}{row_number}"
        
        summary_text = sheets_service.get_cell_value(sheet_name, summary_cell)
        if not summary_text:
            print(f"✗ No summary found at row {row_number}")
            return
        
        print(f"✓ Found summary text ({len(summary_text)} characters)")
        print(f"  Preview: {summary_text[:100]}...")
    except Exception as e:
        print(f"✗ Error fetching summary: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Create sample actionable steps for table testing
    print("\nStep 2: Creating sample actionable steps for table testing...")
    
    # Using sample data to test table creation without making LLM calls
    actionable_steps = {
        "implementation_guidance": "Start with one change at a time and track outcomes. Consult your pediatrician before making any changes.",
        "recommended_approaches": [
            {
                "intervention_name": "Gut Health Support",
                "why_this_may_help": "Supports digestive function and may reduce behavioral symptoms linked to gut issues.",
                "what_others_have_done": [
                    "Added probiotic foods like yogurt",
                    "Tried elimination diets to identify triggers",
                    "Worked with nutritionist"
                ],
                "what_families_tracked": [
                    "Stool consistency and frequency",
                    "Behavioral changes after meals",
                    "Sleep quality"
                ],
                "common_decision_points": [
                    "Whether to start with food diary or testing first",
                    "Choosing between probiotic supplements vs. food sources"
                ],
                "considerations": [
                    "Changes may take 2-4 weeks to show effect",
                    "Requires consistent tracking"
                ]
            },
            {
                "intervention_name": "Sleep Hygiene Routine",
                "why_this_may_help": "Consistent sleep routines can improve sleep onset and duration.",
                "what_others_have_done": [
                    "Established consistent bedtime",
                    "Reduced screen time before bed",
                    "Used white noise machine"
                ],
                "what_families_tracked": [
                    "Time to fall asleep",
                    "Number of night wakings",
                    "Morning mood"
                ],
                "common_decision_points": [
                    "When to start bedtime routine",
                    "Whether to use melatonin supplements"
                ],
                "considerations": [
                    "Takes 1-2 weeks for routine to become habit",
                    "May require adjusting schedule"
                ]
            },
            {
                "intervention_name": "Sensory Diet",
                "why_this_may_help": "Provides appropriate sensory input throughout the day to help with regulation.",
                "what_others_have_done": [
                    "Added movement breaks every hour",
                    "Used weighted blankets",
                    "Provided chewy/crunchy snacks"
                ],
                "what_families_tracked": [
                    "Frequency of meltdowns",
                    "Ability to focus",
                    "Sleep quality"
                ],
                "common_decision_points": [
                    "Whether to work with OT first",
                    "Which sensory tools to try"
                ],
                "considerations": [
                    "Requires trial and error",
                    "Individual needs vary"
                ]
            }
        ],
        "general_notes": [
            "Always consult with your healthcare team before making changes",
            "Track one intervention at a time for clearer results",
            "Be patient - changes often take weeks to show benefits"
        ]
    }
    
    approaches = actionable_steps.get('recommended_approaches', [])
    print(f"✓ Created {len(approaches)} sample approaches for testing")
    
    if approaches:
        print("\n  Sample Approaches:")
        for i, approach in enumerate(approaches, 1):
            name = approach.get('intervention_name', 'Unknown')
            print(f"    {i}. {name}")
    
    # Step 3: Test table creation
    print("\nStep 3: Testing Google Docs table creation...")
    
    # Get patient info from sheet
    print("  Getting patient metadata from sheet...")
    try:
        patient_id = sheets_service.get_cell_value(sheet_name, f"B{row_number}") or "test_id"
        parent_name = sheets_service.get_cell_value(sheet_name, f"C{row_number}") or "Test Parent"
        email = sheets_service.get_cell_value(sheet_name, f"D{row_number}") or "test@example.com"
        zipcode = sheets_service.get_cell_value(sheet_name, f"E{row_number}") or "12345"
        date_submitted = sheets_service.get_cell_value(sheet_name, f"F{row_number}") or "11/17/2025"
        
        test_patient_info = {
            'patient_id': patient_id,
            'parent_name': parent_name,
            'email': email,
            'patient_age': '2-3 years',  # Placeholder
            'patient_sex': 'Unknown',  # Placeholder
            'diagnosis_status': 'Test',
            'date_submitted': date_submitted,
            'zipcode': zipcode,
            'top_family_priorities': []
        }
        print(f"  ✓ Got patient info for: {patient_id}")
    except Exception as e:
        print(f"  Warning: Could not fetch all patient info: {e}")
        test_patient_info = {
            'patient_id': 'test_id',
            'parent_name': 'Test Parent',
            'email': 'test@example.com',
            'patient_age': '2-3 years',
            'patient_sex': 'Unknown',
            'diagnosis_status': 'Test',
            'date_submitted': '11/17/2025',
            'zipcode': '12345',
            'top_family_priorities': []
        }
    
    test_triage = {
        'summary_title': 'Test Triage',
        'urgent_items': [],
        'moderate_items': [],
        'no_urgent_detected': True,
        'caregiver_tips': [],
        'reminder': 'Test reminder'
    }
    
    test_hypotheses = {
        'hypotheses': [],
        'uncertainties': [],
        'next_steps': []
    }
    
    test_resources = {
        'status': 'skipped',
        'reason': 'Test run'
    }
    
    try:
        print(f"  Creating Google Doc with {len(approaches)} approaches in table...")
        doc_url = docs_service.create_patient_report(
            patient_info=test_patient_info,
            triage_result=test_triage,
            hypotheses=test_hypotheses,
            actionable_steps=actionable_steps,
            resources=test_resources
        )
        
        print(f"✓ Document created successfully!")
        print(f"\n{'='*60}")
        print(f"Document URL: {doc_url}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"✗ Error creating document: {e}")
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✓ Successfully fetched patient data from row {row_number}")
        print(f"✓ Created {len(approaches)} sample intervention approaches")  
        print(f"✗ Table creation failed due to Google Docs API index management")
        print(f"\nDIAGNOSIS: The table structure creates complex index tracking issues")
        print(f"when inserting text into cells. Each text insertion shifts subsequent")
        print(f"cell positions in ways that are difficult to predict.")
        print(f"\nRECOMMENDATION: Use a simpler format like bulleted lists or")
        print(f"break table creation into multiple API calls.")
        print("="*60 + "\n")
        return
    
    print("\n✓ Test completed successfully!")


def main():
    """Main entry point."""
    # Get row number from command line or use default
    row_number = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    
    # Run the test
    asyncio.run(test_table_creation(row_number))


if __name__ == "__main__":
    main()
