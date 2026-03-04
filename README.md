# Clinical Document OCR + PHI De-Identification Pipeline

Local pipeline for processing scanned clinical documents (faxes, referrals, intake packets) through OCR and HIPAA-compliant PHI de-identification.

## What It Does

1. **OCR** — Extracts text from scanned PDFs, faxed images, photos of paper documents using Tesseract with OpenCV pre-processing (deskew, denoise, binarize)
2. **PHI De-Identification** — Strips all 18 HIPAA Safe Harbor identifiers using Microsoft Presidio with custom clinical recognizers, replacing each with deterministic placeholders like `[PATIENT_001]`, `[DATE_003]`
3. **Encrypted Mapping** — Stores PHI mappings in Fernet-encrypted files for later re-identification
4. **Re-Identification** — Restores original PHI from encrypted mappings when needed

## Quick Start (Docker)

```bash
# Build the container (includes Tesseract, poppler, spaCy model)
docker compose build

# Process a document
docker compose run phi-pipeline process /app/data/my_document.pdf

# Re-identify
docker compose run phi-pipeline reidentify <document_id> /app/output/<document_id>.txt
```

## Quick Start (Local)

Requires: Python 3.11+, `tesseract-ocr`, `poppler-utils`

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr poppler-utils

# Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# Process a document
python -m src.cli process path/to/document.pdf --output-dir ./output

# Re-identify a previously processed document
python -m src.cli reidentify <document_id> ./output/<document_id>.txt
```

## Python API

```python
from src.phi.deidentifier import DeIdentifier
from src.phi.mapping import MappingStore

# De-identify text directly (no OCR)
deid = DeIdentifier()
result = deid.deidentify("Patient John Smith, DOB 01/15/1980, MRN: 12345678")
print(result.deidentified_text)
# "Patient [PATIENT_001], DOB [DATE_001], MRN: [MRN_001]"

# Full pipeline: OCR + de-identify
from src.pipeline import process_document
result = process_document("scan.pdf")
print(result.deidentified_text)
print(f"Found {result.phi_count} PHI entities")
```

## PHI Entity Types Detected

| Category | Entity Type | Example |
|----------|------------|---------|
| Names | PERSON | John Smith → `[PATIENT_001]` |
| Dates | DATE_TIME | 03/15/1958 → `[DATE_001]` |
| Locations | LOCATION | Springfield → `[LOCATION_001]` |
| Phone | PHONE_NUMBER | (217) 555-0142 → `[PHONE_001]` |
| Email | EMAIL_ADDRESS | john@example.com → `[EMAIL_001]` |
| SSN | US_SSN | 412-68-7935 → `[SSN_001]` |
| MRN | MEDICAL_RECORD_NUMBER | MRN: 78456123 → `[MRN_001]` |
| Fax | FAX_NUMBER | Fax: (217) 555-0199 → `[FAX_001]` |
| Insurance | HEALTH_PLAN_ID | Member ID: BCB987 → `[PLAN_ID_001]` |
| Accounts | ACCOUNT_NUMBER | Account #: 845612 → `[ACCOUNT_001]` |
| Facilities | FACILITY | Sunrise Rehab Hospital → `[FACILITY_001]` |
| URLs | URL | example.com → `[URL_001]` |
| IPs | IP_ADDRESS | 192.168.1.1 → `[IP_001]` |
| License | US_DRIVER_LICENSE | DL numbers → `[LICENSE_001]` |
| Devices | DEVICE_IDENTIFIER | Serial #: ABC123 → `[DEVICE_001]` |
| VIN | VIN | Vehicle IDs → `[VIN_001]` |

## Encryption

PHI mappings are encrypted with Fernet (AES-128-CBC + HMAC). Set `PHI_ENCRYPTION_KEY` env var for persistent keys:

```bash
# Generate a key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Use it
export PHI_ENCRYPTION_KEY="your-generated-key"
```

## Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
src/
├── cli.py                 # CLI entry point
├── pipeline.py            # End-to-end: file → OCR → de-identify → output
├── ocr/
│   ├── preprocessor.py    # OpenCV image preprocessing
│   └── engine.py          # Tesseract OCR wrapper
└── phi/
    ├── recognizers.py     # Custom Presidio recognizers for clinical PHI
    ├── deidentifier.py    # Presidio analyzer + deterministic placeholders
    └── mapping.py         # Encrypted PHI mapping store
```
