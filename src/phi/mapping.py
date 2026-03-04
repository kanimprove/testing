"""Encrypted PHI mapping store for de-identification and re-identification.

Mappings are stored as Fernet-encrypted JSON files, one per document.
The encryption key is loaded from the PHI_ENCRYPTION_KEY environment variable.
"""

import json
import os
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path

from cryptography.fernet import Fernet


DEFAULT_MAPPING_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "phi_mappings")


@dataclass
class PHIMapping:
    """A single PHI entity mapping: placeholder ↔ original value."""

    placeholder: str
    original_value: str
    entity_type: str
    start: int
    end: int


class MappingStore:
    """Encrypted storage for PHI mappings.

    Each document's mappings are stored in a separate Fernet-encrypted JSON file.
    """

    def __init__(self, storage_dir: str | None = None, encryption_key: str | None = None):
        self.storage_dir = Path(storage_dir or DEFAULT_MAPPING_DIR)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        key = encryption_key or os.environ.get("PHI_ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            warnings.warn(
                "PHI_ENCRYPTION_KEY not set. Generated an ephemeral, non-persistent "
                "encryption key for this process. Set PHI_ENCRYPTION_KEY env var for "
                "persistent storage and re-identification across processes.",
                stacklevel=2,
            )
        if isinstance(key, str):
            key = key.encode()
        self.fernet = Fernet(key)

    def _path_for(self, document_id: str) -> Path:
        return self.storage_dir / f"{document_id}.enc"

    def save(self, document_id: str, mappings: list[PHIMapping]) -> Path:
        """Encrypt and save mappings for a document.

        Returns the path to the encrypted file.
        """
        data = json.dumps([asdict(m) for m in mappings]).encode()
        encrypted = self.fernet.encrypt(data)
        path = self._path_for(document_id)
        path.write_bytes(encrypted)
        return path

    def load(self, document_id: str) -> list[PHIMapping]:
        """Load and decrypt mappings for a document."""
        path = self._path_for(document_id)
        if not path.exists():
            raise FileNotFoundError(f"No mappings found for document: {document_id}")
        encrypted = path.read_bytes()
        data = json.loads(self.fernet.decrypt(encrypted))
        return [PHIMapping(**item) for item in data]

    def reidentify(self, text: str, document_id: str) -> str:
        """Replace all placeholders in text with original PHI values.

        Replaces longer placeholders first to avoid partial replacement issues.
        """
        mappings = self.load(document_id)
        # Sort by placeholder length descending to avoid partial matches
        mappings.sort(key=lambda m: len(m.placeholder), reverse=True)
        for mapping in mappings:
            text = text.replace(mapping.placeholder, mapping.original_value)
        return text
