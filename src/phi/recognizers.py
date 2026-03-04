"""Custom Presidio recognizers for clinical-specific PHI.

These augment Presidio's built-in recognizers (PERSON, PHONE_NUMBER,
EMAIL_ADDRESS, US_SSN, LOCATION, URL, IP_ADDRESS, US_DRIVER_LICENSE,
DATE_TIME) with patterns common in clinical documents.
"""

from presidio_analyzer import PatternRecognizer, Pattern, EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts


def create_mrn_recognizer() -> PatternRecognizer:
    """Medical Record Number recognizer.

    Catches patterns like: MRN: 123456, MR# 1234567890, Medical Record 12345678
    """
    return PatternRecognizer(
        supported_entity="MEDICAL_RECORD_NUMBER",
        name="MRN Recognizer",
        patterns=[
            Pattern("MRN_PREFIX", r"\bMRN\s*[:#]?\s*\d{6,10}\b", 0.9),
            Pattern("MR_HASH", r"\bMR#\s*\d{6,10}\b", 0.9),
            Pattern("MED_RECORD", r"\bMedical\s+Record\s*(?:#|No\.?|Number)?\s*:?\s*\d{6,10}\b", 0.85),
            Pattern("PATIENT_ID", r"\bPatient\s*ID\s*[:#]?\s*\d{6,10}\b", 0.8),
        ],
        context=["medical record", "mrn", "patient id", "record number", "chart"],
    )


def create_fax_number_recognizer() -> PatternRecognizer:
    """Fax number recognizer — phone numbers near fax-related context."""
    return PatternRecognizer(
        supported_entity="FAX_NUMBER",
        name="Fax Number Recognizer",
        patterns=[
            Pattern(
                "FAX_PREFIXED",
                r"\b(?:Fax|FAX|F)\s*[:#]?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                0.9,
            ),
        ],
        context=["fax", "facsimile"],
    )


def create_health_plan_recognizer() -> PatternRecognizer:
    """Health plan / insurance ID recognizer."""
    return PatternRecognizer(
        supported_entity="HEALTH_PLAN_ID",
        name="Health Plan ID Recognizer",
        patterns=[
            Pattern(
                "PLAN_ID",
                r"\b(?:Member|Policy|Group|Insurance|Plan)\s*(?:ID|#|No\.?|Number)\s*[:#]?\s*[A-Z0-9]{6,20}\b",
                0.8,
            ),
        ],
        context=[
            "health plan", "insurance", "member id", "policy", "group number",
            "subscriber", "coverage", "plan id",
        ],
    )


def create_account_number_recognizer() -> PatternRecognizer:
    """Account/billing number recognizer."""
    return PatternRecognizer(
        supported_entity="ACCOUNT_NUMBER",
        name="Account Number Recognizer",
        patterns=[
            Pattern(
                "ACCT_NUM",
                r"\b(?:Account|Acct)\s*(?:#|No\.?|Number)?\s*[:#]?\s*\d{6,12}\b",
                0.8,
            ),
        ],
        context=["account", "acct", "billing", "invoice"],
    )


def create_device_identifier_recognizer() -> PatternRecognizer:
    """Device/serial number recognizer for medical devices."""
    return PatternRecognizer(
        supported_entity="DEVICE_IDENTIFIER",
        name="Device Identifier Recognizer",
        patterns=[
            Pattern(
                "DEVICE_SERIAL",
                r"\b(?:Serial|Device|UDI)\s*(?:#|No\.?|Number)?\s*[:#]?\s*[A-Z0-9-]{8,20}\b",
                0.7,
            ),
        ],
        context=["device", "serial", "implant", "equipment", "UDI"],
    )


def create_vin_recognizer() -> PatternRecognizer:
    """Vehicle Identification Number recognizer."""
    return PatternRecognizer(
        supported_entity="VIN",
        name="VIN Recognizer",
        patterns=[
            Pattern("VIN_PATTERN", r"\b[A-HJ-NPR-Z0-9]{17}\b", 0.6),
        ],
        context=["vin", "vehicle", "identification number"],
    )


class FacilityRecognizer(EntityRecognizer):
    """Recognizes facility/hospital names using context patterns.

    Detects text following keywords like Hospital, Clinic, Medical Center, etc.
    """

    FACILITY_KEYWORDS = [
        "hospital", "clinic", "medical center", "rehabilitation",
        "health center", "surgery center", "nursing facility",
        "rehab center", "treatment center",
    ]

    def __init__(self):
        super().__init__(
            supported_entities=["FACILITY"],
            supported_language="en",
            name="Facility Recognizer",
        )

    def load(self):
        pass

    def analyze(self, text: str, entities, nlp_artifacts: NlpArtifacts = None, **kwargs):
        results = []
        text_lower = text.lower()
        for keyword in self.FACILITY_KEYWORDS:
            idx = 0
            while True:
                pos = text_lower.find(keyword, idx)
                if pos == -1:
                    break
                # Find the start of this name — look backwards for newline, colon, or start
                line_start = text.rfind("\n", 0, pos)
                colon = text.rfind(":", 0, pos)
                start = max(line_start, colon) + 1
                # Strip leading whitespace
                while start < pos and text[start] in " \t":
                    start += 1
                # End is after the keyword
                end = pos + len(keyword)
                # Only report if there's a name before or including the keyword
                if end - start > len(keyword):
                    results.append(
                        RecognizerResult(
                            entity_type="FACILITY",
                            start=start,
                            end=end,
                            score=0.6,
                        )
                    )
                idx = end
        return results


def get_all_custom_recognizers() -> list:
    """Return all custom clinical recognizers for registration."""
    return [
        create_mrn_recognizer(),
        create_fax_number_recognizer(),
        create_health_plan_recognizer(),
        create_account_number_recognizer(),
        create_device_identifier_recognizer(),
        create_vin_recognizer(),
        FacilityRecognizer(),
    ]
