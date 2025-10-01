import pytest

from app.services.parser import parse_patient_report


def test_parse_basic_labeled():
    text = "Patient Age: 42; Patient Sex: Female; Diagnosis Status: Confirmed"
    parsed = parse_patient_report(text)
    assert parsed["patient_age"] == 42
    assert parsed["patient_sex"].lower() == "female"
    assert parsed["diagnosis_status"].lower() == "confirmed"


def test_parse_varied_labels():
    text = "Age: 29\nGender: M\nDiagnosis: likely remission"
    parsed = parse_patient_report(text)
    assert parsed["patient_age"] == 29
    assert parsed["patient_sex"].lower() == "male"
    assert parsed["diagnosis_status"].lower() == "likely remission"


essay = """
This is a free text clinical note.
Age is 67. The patient is a woman presenting with X.
Diagnosis status: Under evaluation.
"""

def test_parse_informal_text():
    parsed = parse_patient_report(essay)
    assert parsed["patient_age"] == 67
    assert parsed["patient_sex"].lower() in ("female", "woman")
    assert "under evaluation" in parsed["diagnosis_status"].lower()
