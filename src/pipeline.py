"""End-to-end document processing pipeline: file → OCR → de-identify → output."""

import os
import uuid
from dataclasses import dataclass

from src.ocr.engine import ocr_file
from src.phi.deidentifier import DeIdentifier
from src.phi.mapping import MappingStore


@dataclass
class ProcessingResult:
    """Result of processing a document through the pipeline."""

    document_id: str
    original_filename: str
    raw_text: str
    deidentified_text: str
    phi_count: int
    pages_processed: int


def process_document(
    file_path: str,
    mapping_store: MappingStore | None = None,
    deidentifier: DeIdentifier | None = None,
) -> ProcessingResult:
    """Process a document through the full OCR → de-identification pipeline.

    Args:
        file_path: Path to the input file (PDF, PNG, JPG, TIFF, BMP).
        mapping_store: Optional MappingStore instance. Creates default if None.
        deidentifier: Optional DeIdentifier instance. Creates default if None.

    Returns:
        ProcessingResult with document ID, raw text, de-identified text,
        and PHI entity count.
    """
    if mapping_store is None:
        mapping_store = MappingStore()
    if deidentifier is None:
        deidentifier = DeIdentifier()

    document_id = uuid.uuid4().hex[:12]
    filename = os.path.basename(file_path)

    # Step 1: OCR
    raw_text = ocr_file(file_path)

    # Count pages from OCR output
    if not raw_text or not raw_text.strip():
        # No text produced by OCR; treat as zero successfully processed pages.
        pages = 0
    else:
        # Estimate page count from page markers; assume at least one page when text exists.
        pages = raw_text.count("--- Page ") or 1

    # Step 2: De-identify
    deid_result = deidentifier.deidentify(raw_text)

    # Step 3: Save encrypted mappings
    if deid_result.mappings:
        mapping_store.save(document_id, deid_result.mappings)

    return ProcessingResult(
        document_id=document_id,
        original_filename=filename,
        raw_text=raw_text,
        deidentified_text=deid_result.deidentified_text,
        phi_count=len(deid_result.mappings),
        pages_processed=pages,
    )
