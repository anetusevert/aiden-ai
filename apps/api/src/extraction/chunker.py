"""Deterministic text chunking for document processing.

Creates stable chunks with character offsets for citation support.
Chunks are designed to be ~800-1200 characters, splitting on paragraph
boundaries when possible.
"""

import re
from dataclasses import dataclass

# Configurable chunk size parameters
MIN_CHUNK_SIZE = 800
MAX_CHUNK_SIZE = 1200
TARGET_CHUNK_SIZE = 1000


@dataclass
class ChunkResult:
    """Result of chunking operation."""

    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_start: int | None = None
    page_end: int | None = None


def create_chunks(
    text: str,
    min_size: int = MIN_CHUNK_SIZE,
    max_size: int = MAX_CHUNK_SIZE,
    target_size: int = TARGET_CHUNK_SIZE,
) -> list[ChunkResult]:
    """Create deterministic chunks from extracted text.

    Chunks are created by:
    1. Splitting on paragraph boundaries (double newlines) when possible
    2. Falling back to single newlines
    3. Falling back to sentence boundaries
    4. Hard splitting at max_size if no natural boundary found

    This is fully deterministic: same input text always produces identical chunks.

    Args:
        text: The text to chunk
        min_size: Minimum chunk size in characters
        max_size: Maximum chunk size in characters
        target_size: Target chunk size (we try to get close to this)

    Returns:
        List of ChunkResult with text and offsets
    """
    if not text or not text.strip():
        return []

    chunks: list[ChunkResult] = []
    current_start = 0
    chunk_index = 0

    while current_start < len(text):
        # Determine chunk end
        remaining = len(text) - current_start

        if remaining <= max_size:
            # Last chunk - take everything
            chunk_end = len(text)
        else:
            # Find a good split point
            chunk_end = _find_split_point(
                text, current_start, min_size, max_size, target_size
            )

        # Extract chunk text
        chunk_text = text[current_start:chunk_end]

        # Skip empty chunks (shouldn't happen but be safe)
        if chunk_text.strip():
            chunks.append(
                ChunkResult(
                    chunk_index=chunk_index,
                    text=chunk_text,
                    char_start=current_start,
                    char_end=chunk_end,
                    page_start=None,  # Could be computed if page offsets known
                    page_end=None,
                )
            )
            chunk_index += 1

        current_start = chunk_end

    return chunks


def _find_split_point(
    text: str,
    start: int,
    min_size: int,
    max_size: int,
    target_size: int,
) -> int:
    """Find the best split point for a chunk.

    Looks for natural boundaries in this priority:
    1. Paragraph break (double newline)
    2. Single newline
    3. Sentence end (. ! ?)
    4. Hard split at max_size

    Args:
        text: Full text
        start: Start position of current chunk
        min_size: Minimum chunk size
        max_size: Maximum chunk size
        target_size: Target chunk size

    Returns:
        End position for the chunk
    """
    end_limit = min(start + max_size, len(text))
    search_start = start + min_size

    # If we're too close to the end, just take what's left
    if search_start >= len(text):
        return len(text)

    # Search window: from min_size to max_size
    search_text = text[search_start:end_limit]

    # Priority 1: Look for paragraph break (double newline)
    # Search backwards from target_size for a paragraph break
    target_end = start + target_size
    if target_end < len(text):
        # Look around target size
        para_match = _find_best_break(
            search_text, r"\n\s*\n", target_size - min_size
        )
        if para_match is not None:
            return search_start + para_match

    # Priority 2: Look for single newline
    newline_match = _find_best_break(
        search_text, r"\n", target_size - min_size
    )
    if newline_match is not None:
        return search_start + newline_match

    # Priority 3: Look for sentence end
    sentence_match = _find_best_break(
        search_text, r"[.!?]\s+", target_size - min_size
    )
    if sentence_match is not None:
        # Include the punctuation and space
        return search_start + sentence_match

    # Priority 4: Look for any whitespace
    space_match = _find_best_break(
        search_text, r"\s+", target_size - min_size
    )
    if space_match is not None:
        return search_start + space_match

    # Fallback: hard split at max_size
    return end_limit


def _find_best_break(
    search_text: str,
    pattern: str,
    target_offset: int,
) -> int | None:
    """Find the break point closest to target offset.

    Args:
        search_text: Text to search in
        pattern: Regex pattern for break points
        target_offset: Target position within search_text

    Returns:
        Best break position or None if no match
    """
    matches = list(re.finditer(pattern, search_text))
    if not matches:
        return None

    # Find match closest to target
    best_match = None
    best_distance = float("inf")

    for match in matches:
        # Use end of match as break point
        match_end = match.end()
        distance = abs(match_end - target_offset)

        if distance < best_distance:
            best_distance = distance
            best_match = match_end

    return best_match
