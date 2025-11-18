import unittest
from unittest.mock import MagicMock, patch, call
import os
import sys
from pathlib import Path

# Add project root to path to allow importing app modules
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from app.services.google_docs import GoogleDocsService

class TestGoogleDocsService(unittest.TestCase):

    @patch('app.services.google_docs.build')
    @patch('app.services.google_docs.service_account.Credentials.from_service_account_file')
    def setUp(self, mock_from_service_account, mock_build):
        """Set up a mock GoogleDocsService for testing."""
        # Mock credentials
        self.mock_creds = MagicMock()
        mock_from_service_account.return_value = self.mock_creds

        # Mock the build function to return mock services
        self.mock_docs_service = MagicMock()
        self.mock_drive_service = MagicMock()
        mock_build.side_effect = [
            self.mock_docs_service,  # First call returns docs service
            self.mock_drive_service  # Second call returns drive service
        ]

        # Set a dummy credentials file path to satisfy the constructor
        with patch('app.services.google_docs.CREDENTIALS_FILE', Path('/dummy/credentials.json')):
            with patch('pathlib.Path.exists', return_value=True):
                os.environ['DOCS_AUTH_MODE'] = 'service'
                self.docs_service = GoogleDocsService()

    def test_create_patient_report_with_tables(self):
        """Test that create_patient_report generates a single batchUpdate with correct table requests."""
        # Sample data mimicking the structure from the router
        patient_info = {
            'parent_name': 'Jane Doe',
            'date_submitted': '2024-01-15',
            'patient_age': '5 years',
            'patient_sex': 'Male',
            'diagnosis_status': 'Undiagnosed',
            'top_family_priorities': ['Communication', 'Social Skills']
        }
        triage_result = {}
        hypotheses = {
            'hypotheses': [
                {
                    'name': 'Gut-Brain Axis Imbalance',
                    'rationale': 'GI issues are common.',
                    'talking_points': ['Discuss probiotics.'],
                    'recommended_tests': []
                }
            ]
        }
        actionable_steps = {
            'recommended_approaches': [
                {
                    'intervention_name': 'Dietary Changes',
                    'why_this_may_help': 'Reduces inflammation.',
                    'what_others_have_done': ['Tried GFCF diet.'],
                    'what_families_tracked': ['Behavioral changes.'],
                    'common_decision_points': ['Consult a nutritionist.'],
                    'considerations': ['Can be challenging.'],
                }
            ],
            'general_notes': ['Monitor for 2 weeks.']
        }
        resources = {'status': 'skipped'}

        # Configure the mock for the chained call without calling it
        mock_create_execute = self.mock_drive_service.files().create.return_value.execute
        mock_create_execute.return_value = {'id': 'test_doc_id'}

        # Call the method under test
        report_url = self.docs_service.create_patient_report(
            patient_info=patient_info,
            triage_result=triage_result,
            hypotheses=hypotheses,
            actionable_steps=actionable_steps,
            resources=resources,
            folder_id='test_folder_id'
        )

        # --- Assertions ---
        self.assertEqual(report_url, 'https://docs.google.com/document/d/test_doc_id/edit')

        # 1. Verify Drive file creation was called correctly
        self.mock_drive_service.files().create.assert_called_once_with(
            body={
                'name': 'Informational Report - Jane Doe - 2024-01-15',
                'mimeType': 'application/vnd.google-apps.document',
                'parents': ['test_folder_id']
            },
            fields='id',
            supportsAllDrives=True
        )

        # 2. Verify that a single batchUpdate was called on the Docs service
        self.mock_docs_service.documents().batchUpdate.assert_called_once()
        
        # 3. Check the content of the batchUpdate call
        args, kwargs = self.mock_docs_service.documents().batchUpdate.call_args
        self.assertEqual(kwargs['documentId'], 'test_doc_id')
        requests = kwargs['body']['requests']
        
        # Convert requests to a string for easy searching
        requests_str = str(requests)

        # Verify key parts of the document structure exist by checking for substrings
        self.assertIn("Parent Report", requests_str)
        self.assertIn("1. Dietary Changes", requests_str)
        self.assertIn("'insertTable':", requests_str)
        self.assertIn("Why This May Help", requests_str)
        self.assertIn("Reduces inflammation.", requests_str)
        self.assertIn("Important Reminders", requests_str)

if __name__ == '__main__':
    unittest.main()
