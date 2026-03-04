# Clinical Document OCR + PHI De-Identification Pipeline

Local pipeline for processing scanned clinical documents (faxes, referrals, intake packets) through OCR and HIPAA-compliant PHI de-identification.

## What It Does

1. **OCR** — Extracts text from scanned PDFs, faxed images, photos of paper documents using Tesseract with OpenCV pre-processing (deskew, denoise, binarize)
2. **PHI De-Identification** — Strips all 18 HIPAA Safe Harbor identifiers using Microsoft Presidio with custom clinical recognizers, replacing each with deterministic placeholders like `[PATIENT_001]`, `[DATE_003]`
3. **Encrypted Mapping** — Stores PHI mappings in Fernet-encrypted files for later re-identification
4. **Re-Identification** — Restores original PHI from encrypted mappings when needed

## Windows Quick Start (No coding required)

### One-time setup

**Step 1 — Install Docker Desktop**

1. Go to https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Run the installer — click Next through everything
4. **Restart your computer** when it asks
5. After restart, Docker Desktop opens automatically — wait for the green **"Engine running"** icon in the bottom-left

> If it says "WSL 2 not installed": Open PowerShell as Administrator (right-click Start button → "Terminal (Admin)"), type `wsl --install`, press Enter, then restart.

**Step 2 — Install Git**

1. Go to https://git-scm.com/download/win
2. Run the installer — click Next through everything (defaults are fine)

**Step 3 — Download this project**

1. Open **Git Bash** (search for it in the Start menu)
2. Type this and press Enter:
   ```
   git clone https://github.com/kanimprove/testing.git
   ```
3. To find the folder: open **File Explorer** → click the address bar → type `%USERPROFILE%\testing` → press Enter

**Step 4 — Run setup**

1. Open the `testing` folder (see Step 3 for how to find it)
2. **Double-click `setup.bat`**
3. A black window appears — wait about 5 minutes while it downloads everything
4. When you see "Setup complete!", press any key to close

### Processing documents

**Step 5 — Add your documents**

1. Open the `testing` folder
2. Open the `data` folder inside it
3. Copy your scanned documents here (PDF, PNG, JPG, or TIFF files)

**Step 6 — Run the pipeline**

1. Go back to the `testing` folder
2. **Double-click `process.bat`**
3. Wait while it processes each document
4. When done, the `output` folder opens automatically with your results

**Step 7 — View results**

Each `.txt` file in `output` contains the extracted text with all patient information replaced:
- `John Smith` → `[PATIENT_001]`
- `03/15/1958` → `[DATE_001]`
- `412-68-7935` → `[SSN_001]`
- etc.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| "Docker Desktop is not running" | Open Docker Desktop from Start menu, wait for green icon, try again |
| Setup takes forever | The first build downloads ~1.5GB — needs good internet. Be patient. |
| "No supported documents found" | Make sure your files are in the `data` folder (not a subfolder) |
| Black window closes immediately | Right-click the `.bat` file → "Run as administrator" |

---

## Docker (command line)

```bash
# Build the container (includes Tesseract, poppler, spaCy model)
docker compose build

# Process a single document
docker compose run --rm phi-pipeline process /app/data/my_document.pdf

# Process all documents in data/ folder
docker compose run --rm phi-pipeline process-all /app/data

# Re-identify
docker compose run --rm phi-pipeline reidentify <document_id> /app/output/<document_id>.txt
```

## Local Install (Linux/macOS)

Requires: Python 3.11+, `tesseract-ocr`, `poppler-utils`

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr poppler-utils
# macOS: brew install tesseract poppler

# Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg

# Process a document
python -m src.cli process path/to/document.pdf --output-dir ./output

# Process all documents in a folder
python -m src.cli process-all ./data --output-dir ./output

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
