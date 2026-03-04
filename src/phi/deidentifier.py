"""PHI de-identification using Microsoft Presidio with deterministic placeholders.

Analyzes text for all HIPAA Safe Harbor entity types and replaces each
with a typed, numbered placeholder like [PATIENT_001], [DATE_003].
Same original value within a document always maps to the same placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine

from src.phi.mapping import PHIMapping
from src.phi.recognizers import get_all_custom_recognizers


# Map Presidio entity types to human-readable placeholder prefixes
ENTITY_PREFIX_MAP = {
    "PERSON": "PATIENT",
    "DATE_TIME": "DATE",
    "LOCATION": "LOCATION",
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "US_SSN": "SSN",
    "MEDICAL_RECORD_NUMBER": "MRN",
    "URL": "URL",
    "IP_ADDRESS": "IP",
    "HEALTH_PLAN_ID": "PLAN_ID",
    "ACCOUNT_NUMBER": "ACCOUNT",
    "US_DRIVER_LICENSE": "LICENSE",
    "FAX_NUMBER": "FAX",
    "FACILITY": "FACILITY",
    "DEVICE_IDENTIFIER": "DEVICE",
    "VIN": "VIN",
    "US_BANK_NUMBER": "BANK_ACCT",
    "US_PASSPORT": "PASSPORT",
    "US_ITIN": "ITIN",
    "CRYPTO": "CRYPTO",
    "NRP": "NRP",
    "IBAN_CODE": "IBAN",
    "CREDIT_CARD": "CREDIT_CARD",
}

# All entity types we want Presidio to detect
ENTITIES_TO_DETECT = [
    "PERSON",
    "DATE_TIME",
    "LOCATION",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "MEDICAL_RECORD_NUMBER",
    "URL",
    "IP_ADDRESS",
    "HEALTH_PLAN_ID",
    "ACCOUNT_NUMBER",
    "US_DRIVER_LICENSE",
    "FAX_NUMBER",
    "FACILITY",
    "DEVICE_IDENTIFIER",
    "VIN",
    "US_BANK_NUMBER",
    "CREDIT_CARD",
]


@dataclass
class DeIdentificationResult:
    """Result of de-identifying a text document."""

    deidentified_text: str
    mappings: list[PHIMapping]


class PlaceholderTracker:
    """Tracks placeholder assignments for deterministic mapping.

    Same original value always gets the same placeholder within a document.
    """

    def __init__(self):
        # {entity_type: {original_value: placeholder_string}}
        self._assignments: dict[str, dict[str, str]] = {}
        # {entity_type: next_counter}
        self._counters: dict[str, int] = {}

    def get_placeholder(self, entity_type: str, original_value: str) -> str:
        """Get or create a deterministic placeholder for a value."""
        if entity_type not in self._assignments:
            self._assignments[entity_type] = {}
            self._counters[entity_type] = 1

        normalized = original_value.strip()
        if normalized in self._assignments[entity_type]:
            return self._assignments[entity_type][normalized]

        prefix = ENTITY_PREFIX_MAP.get(entity_type, entity_type)
        counter = self._counters[entity_type]
        placeholder = f"[{prefix}_{counter:03d}]"
        self._assignments[entity_type][normalized] = placeholder
        self._counters[entity_type] = counter + 1
        return placeholder


class DeIdentifier:
    """Presidio-based PHI de-identifier with deterministic placeholders.

    Usage:
        deid = DeIdentifier()
        result = deid.deidentify("Patient John Smith, DOB 01/15/1980, MRN: 12345678")
        print(result.deidentified_text)
        # "Patient [PATIENT_001], DOB [DATE_001], MRN: [MRN_001]"
    """

    def __init__(self, score_threshold: float = 0.35):
        """Initialize with Presidio engines and custom recognizers.

        Args:
            score_threshold: Minimum confidence score for entity detection.
                Lower = more aggressive detection (fewer missed PHI, more false positives).
                Default 0.35 is tuned for clinical text where missing PHI is worse
                than over-redacting.
        """
        self.score_threshold = score_threshold

        # Build registry with custom recognizers
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        for recognizer in get_all_custom_recognizers():
            registry.add_recognizer(recognizer)

        self.analyzer = AnalyzerEngine(registry=registry)
        self.anonymizer = AnonymizerEngine()

    def deidentify(self, text: str, language: str = "en") -> DeIdentificationResult:
        """De-identify text, replacing all PHI with deterministic placeholders.

        Args:
            text: Raw text potentially containing PHI.
            language: Language code for NLP analysis.

        Returns:
            DeIdentificationResult with de-identified text and PHI mappings.
        """
        if not text or not text.strip():
            return DeIdentificationResult(deidentified_text=text, mappings=[])

        # Analyze: detect all PHI entities
        results = self.analyzer.analyze(
            text=text,
            entities=ENTITIES_TO_DETECT,
            language=language,
            score_threshold=self.score_threshold,
        )

        if not results:
            return DeIdentificationResult(deidentified_text=text, mappings=[])

        # Sort results by start position (descending) so we can replace
        # from end to start without shifting indices
        results.sort(key=lambda r: r.start, reverse=True)

        # Remove overlapping detections — keep highest confidence
        filtered = []
        for result in results:
            overlaps = False
            for kept in filtered:
                if result.start < kept.end and result.end > kept.start:
                    overlaps = True
                    break
            if not overlaps:
                filtered.append(result)

        # Build placeholders and mappings
        tracker = PlaceholderTracker()
        mappings: list[PHIMapping] = []
        deidentified = text

        for result in filtered:
            original_value = text[result.start:result.end]
            placeholder = tracker.get_placeholder(result.entity_type, original_value)

            mappings.append(PHIMapping(
                placeholder=placeholder,
                original_value=original_value,
                entity_type=result.entity_type,
                start=result.start,
                end=result.end,
            ))

            deidentified = deidentified[:result.start] + placeholder + deidentified[result.end:]

        return DeIdentificationResult(
            deidentified_text=deidentified,
            mappings=mappings,
        )
