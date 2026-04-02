"""Unified hashing utilities for enterprise traceability.

This module provides deterministic SHA256 hashing for audit and traceability:
- hash_text: Base hashing function for any text
- hash_prompt: Hash prompts for LLM fingerprinting (includes optional system prompt)
- hash_question: Hash questions for audit logging

Raw content is NOT stored in database (privacy). Only hashes are stored.
"""

import hashlib


def hash_text(text: str) -> str:
    """Generate a SHA256 hash of text.

    This is the base hashing function used by all other hash utilities.

    Args:
        text: The text to hash

    Returns:
        Hex-encoded SHA256 hash (64 characters)
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_prompt(prompt: str, system_prompt: str | None = None) -> str:
    """Generate a SHA256 hash of the prompt for LLM traceability.

    Used for fingerprinting prompts sent to LLM providers without storing
    the raw prompt content (privacy).

    Args:
        prompt: The main prompt text
        system_prompt: Optional system prompt (combined for hashing)

    Returns:
        Hex-encoded SHA256 hash
    """
    combined = prompt
    if system_prompt:
        combined = f"{system_prompt}\n---\n{prompt}"
    return hash_text(combined)


def hash_question(question: str) -> str:
    """Generate a SHA256 hash of a question for audit logging.

    Used to log a fingerprint of user questions without storing the
    raw question content in audit logs.

    Args:
        question: The question to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    return hash_text(question)
