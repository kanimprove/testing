"""Tests for the end-to-end processing pipeline.

Note: Full pipeline tests require Tesseract to be installed.
These tests are marked with @pytest.mark.integration and can be
skipped in environments without Tesseract.
"""

import os
import shutil
import tempfile

import pytest

from src.phi.deidentifier import DeIdentifier
from src.phi.mapping import MappingStore


def has_tesseract():
    """Check if tesseract is available."""
    return shutil.which("tesseract") is not None


@pytest.mark.skipif(not has_tesseract(), reason="Tesseract not installed")
class TestPipelineIntegration:
    """Integration tests requiring Tesseract OCR."""

    @pytest.fixture
    def setup(self):
        """Generate test fixture and set up temp dirs."""
        from scripts.generate_test_fixture import generate_fixture

        tmpdir = tempfile.mkdtemp()
        fixtures_dir = os.path.join(tmpdir, "fixtures")
        mapping_dir = os.path.join(tmpdir, "mappings")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(fixtures_dir)
        os.makedirs(mapping_dir)
        os.makedirs(output_dir)

        fixture_path = generate_fixture(output_dir=fixtures_dir)

        yield {
            "fixture_path": fixture_path,
            "mapping_dir": mapping_dir,
            "output_dir": output_dir,
            "tmpdir": tmpdir,
        }

        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_full_pipeline(self, setup):
        """End-to-end: image → OCR → de-identify → re-identify."""
        from cryptography.fernet import Fernet
        from src.pipeline import process_document

        key = Fernet.generate_key().decode()
        store = MappingStore(storage_dir=setup["mapping_dir"], encryption_key=key)

        result = process_document(
            file_path=setup["fixture_path"],
            mapping_store=store,
        )

        # Basic result checks
        assert result.document_id
        assert result.raw_text.strip()
        assert result.deidentified_text.strip()
        assert result.phi_count > 0

        # Verify PHI is removed from de-identified text
        phi_values = ["412-68-7935", "john.smith.patient@email.com"]
        for phi in phi_values:
            assert phi not in result.deidentified_text

        # Verify re-identification works
        reidentified = store.reidentify(result.deidentified_text, result.document_id)
        assert reidentified != result.deidentified_text


class TestPipelineUnit:
    """Unit tests that don't require Tesseract (test de-ID directly)."""

    def test_deidentify_and_reidentify_roundtrip(self):
        """De-identify text and verify re-identification restores it."""
        from cryptography.fernet import Fernet

        text = """PATIENT: John Michael Smith
DATE OF BIRTH: 03/15/1958
MRN: 78456123
PHONE: (217) 555-0142
SSN: 412-68-7935
Email: john.smith@example.com"""

        deid = DeIdentifier()
        result = deid.deidentify(text)

        # PHI should be replaced
        assert "412-68-7935" not in result.deidentified_text

        # Round-trip via mapping store
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MappingStore(storage_dir=tmpdir, encryption_key=key)
            store.save("test-doc", result.mappings)

            reidentified = store.reidentify(result.deidentified_text, "test-doc")

            # Re-identified text should contain original PHI
            assert "412-68-7935" in reidentified
