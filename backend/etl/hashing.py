"""Content hashing for incremental ETL."""

import hashlib

# Bump when chunking rules change and existing vectors must be recomputed.
CHUNKER_VERSION = "1"


def content_hash(text: str) -> str:
    """
    Return SHA-256 hex digest of chunk text (including retrieval prefix).
    """

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
