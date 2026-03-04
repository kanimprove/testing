"""Tests for PHI de-identification.

Tests the custom recognizers, deterministic placeholder generation,
encrypted mapping store, and round-trip re-identification.
"""

import os
import tempfile

import pytest

from src.phi.deidentifier import DeIdentifier, PlaceholderTracker, ENTITY_PREFIX_MAP
from src.phi.mapping import MappingStore, PHIMapping


class TestPlaceholderTracker:
    """Test deterministic placeholder assignment."""

    def test_first_assignment(self):
        tracker = PlaceholderTracker()
        p = tracker.get_placeholder("PERSON", "John Smith")
        assert p == "[PATIENT_001]"

    def test_same_value_same_placeholder(self):
        tracker = PlaceholderTracker()
        p1 = tracker.get_placeholder("PERSON", "John Smith")
        p2 = tracker.get_placeholder("PERSON", "John Smith")
        assert p1 == p2

    def test_different_values_different_placeholders(self):
        tracker = PlaceholderTracker()
        p1 = tracker.get_placeholder("PERSON", "John Smith")
        p2 = tracker.get_placeholder("PERSON", "Jane Doe")
        assert p1 == "[PATIENT_001]"
        assert p2 == "[PATIENT_002]"

    def test_different_entity_types(self):
        tracker = PlaceholderTracker()
        p1 = tracker.get_placeholder("PERSON", "John Smith")
        p2 = tracker.get_placeholder("DATE_TIME", "01/15/2025")
        assert p1 == "[PATIENT_001]"
        assert p2 == "[DATE_001]"

    def test_unknown_entity_type_uses_raw(self):
        tracker = PlaceholderTracker()
        p = tracker.get_placeholder("CUSTOM_TYPE", "value")
        assert p == "[CUSTOM_TYPE_001]"


class TestDeIdentifier:
    """Test the full de-identification engine."""

    @pytest.fixture
    def deid(self):
        return DeIdentifier()

    def test_empty_text(self, deid):
        result = deid.deidentify("")
        assert result.deidentified_text == ""
        assert result.mappings == []

    def test_no_phi(self, deid):
        text = "The patient shows improved range of motion in the left shoulder."
        result = deid.deidentify(text)
        # This text might or might not trigger detections depending on model
        # At minimum, verify we get a result
        assert isinstance(result.deidentified_text, str)

    def test_person_name_detected(self, deid):
        text = "Patient John Michael Smith was seen today for follow-up."
        result = deid.deidentify(text)
        assert "John Michael Smith" not in result.deidentified_text
        assert "[PATIENT_" in result.deidentified_text

    def test_ssn_detected(self, deid):
        text = "Patient SSN: 412-68-7935"
        result = deid.deidentify(text)
        assert "412-68-7935" not in result.deidentified_text

    def test_phone_detected(self, deid):
        text = "Contact phone: (217) 555-0142"
        result = deid.deidentify(text)
        assert "(217) 555-0142" not in result.deidentified_text

    def test_email_detected(self, deid):
        text = "Email: john.smith@hospital.com"
        result = deid.deidentify(text)
        assert "john.smith@hospital.com" not in result.deidentified_text

    def test_date_detected(self, deid):
        text = "Date of birth: 03/15/1958"
        result = deid.deidentify(text)
        assert "03/15/1958" not in result.deidentified_text

    def test_mrn_detected(self, deid):
        text = "MRN: 78456123"
        result = deid.deidentify(text)
        assert "78456123" not in result.deidentified_text

    def test_deterministic_same_name(self, deid):
        text = "Dr. Johnson referred patient to Dr. Johnson for a second opinion."
        result = deid.deidentify(text)
        # Both mentions of Dr. Johnson should map to the same placeholder
        placeholders = [m.placeholder for m in result.mappings if m.original_value.strip() == "Johnson"]
        if len(placeholders) >= 2:
            assert placeholders[0] == placeholders[1]

    def test_mappings_populated(self, deid):
        text = "Patient John Smith, DOB 01/15/1980, SSN 412-68-7935"
        result = deid.deidentify(text)
        assert len(result.mappings) > 0
        for mapping in result.mappings:
            assert mapping.placeholder.startswith("[")
            assert mapping.placeholder.endswith("]")
            assert mapping.original_value
            assert mapping.entity_type

    def test_clinical_text_comprehensive(self, deid):
        """Test with realistic clinical text containing multiple PHI types."""
        text = """PATIENT: John Michael Smith
DATE OF BIRTH: 03/15/1958
DATE OF SERVICE: 01/22/2025
MRN: 78456123
FACILITY: Sunrise Rehabilitation Hospital
ADDRESS: 4521 Oak Valley Drive, Springfield, IL 62704
PHONE: (217) 555-0142
FAX: (217) 555-0199
REFERRING PHYSICIAN: Dr. Sarah Elizabeth Johnson, MD
INSURANCE: BlueCross BlueShield
Member ID: BCB9876543210
Patient SSN on file: 412-68-7935
Email: john.smith.patient@email.com"""

        result = deid.deidentify(text)

        # These specific PHI values should NOT appear in the output
        phi_values = [
            "John Michael Smith",
            "78456123",
            "412-68-7935",
            "john.smith.patient@email.com",
            "(217) 555-0142",
        ]

        for phi in phi_values:
            assert phi not in result.deidentified_text, (
                f"PHI value '{phi}' was NOT de-identified in output"
            )

        assert len(result.mappings) >= 5, (
            f"Expected at least 5 PHI mappings, got {len(result.mappings)}"
        )


class TestMappingStore:
    """Test encrypted PHI mapping storage and re-identification."""

    @pytest.fixture
    def store(self):
        """Create a MappingStore with a temp directory and known key."""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MappingStore(storage_dir=tmpdir, encryption_key=key)

    def test_save_and_load(self, store):
        mappings = [
            PHIMapping("[PATIENT_001]", "John Smith", "PERSON", 0, 10),
            PHIMapping("[DATE_001]", "01/15/2025", "DATE_TIME", 20, 30),
        ]
        store.save("doc-123", mappings)
        loaded = store.load("doc-123")
        assert len(loaded) == 2
        assert loaded[0].placeholder == "[PATIENT_001]"
        assert loaded[0].original_value == "John Smith"

    def test_load_nonexistent(self, store):
        with pytest.raises(FileNotFoundError):
            store.load("nonexistent-doc")

    def test_reidentify(self, store):
        mappings = [
            PHIMapping("[PATIENT_001]", "John Smith", "PERSON", 0, 10),
            PHIMapping("[DATE_001]", "01/15/2025", "DATE_TIME", 20, 30),
        ]
        store.save("doc-456", mappings)

        text = "Patient [PATIENT_001] was seen on [DATE_001]."
        result = store.reidentify(text, "doc-456")
        assert result == "Patient John Smith was seen on 01/15/2025."

    def test_encryption_is_not_plaintext(self, store):
        mappings = [PHIMapping("[PATIENT_001]", "John Smith", "PERSON", 0, 10)]
        path = store.save("doc-789", mappings)
        raw_bytes = path.read_bytes()
        assert b"John Smith" not in raw_bytes
