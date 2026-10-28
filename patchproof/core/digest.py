"""Cryptographic digest and hashing utilities."""

import hashlib
from pathlib import Path


def compute_sha256(content: str | bytes) -> str:
    """Compute SHA-256 hex digest for a string or byte sequence."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_patch_digest(base_tree_hash: str, canonical_diff: str) -> str:
    """Compute canonical patch digest: SHA-256(base_tree_hash || canonical_diff)."""
    payload = f"{base_tree_hash}:{canonical_diff}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
