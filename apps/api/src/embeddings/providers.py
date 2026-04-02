"""Embedding provider implementations.

Provides embedding generation without external API calls.
"""

import hashlib
import math
import struct
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Embedding providers generate vector representations of text
    for semantic similarity search.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced by this provider."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier for this provider."""
        ...

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding for document text.

        Args:
            text: The text to embed (typically chunk content)

        Returns:
            List of floats representing the embedding vector
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a search query.

        This may differ from embed_text for some models that use
        asymmetric embeddings for queries vs documents.

        Args:
            text: The query text to embed

        Returns:
            List of floats representing the embedding vector
        """
        ...

    def format_for_pgvector(self, embedding: list[float]) -> str:
        """Format an embedding as a pgvector string.

        Args:
            embedding: List of floats representing the embedding

        Returns:
            String in format '[v1,v2,v3,...]' for pgvector
        """
        return "[" + ",".join(str(v) for v in embedding) + "]"

    # Deprecated: Use native pgvector storage instead
    def serialize_embedding(self, embedding: list[float]) -> bytes:
        """DEPRECATED: Serialize an embedding to bytes.

        Note: Binary serialization is deprecated. Embeddings are now stored
        as native pgvector vector(384) type. This method is kept for
        backward compatibility only.

        Args:
            embedding: List of floats representing the embedding

        Returns:
            Bytes representation of the embedding
        """
        import warnings
        warnings.warn(
            "serialize_embedding is deprecated. Use native pgvector storage.",
            DeprecationWarning,
            stacklevel=2,
        )
        return struct.pack(f"{len(embedding)}f", *embedding)

    def deserialize_embedding(self, data: bytes) -> list[float]:
        """DEPRECATED: Deserialize an embedding from bytes.

        Note: Binary deserialization is deprecated. Embeddings are now stored
        as native pgvector vector(384) type. This method is kept for
        backward compatibility only.

        Args:
            data: Bytes representation of the embedding

        Returns:
            List of floats representing the embedding
        """
        import warnings
        warnings.warn(
            "deserialize_embedding is deprecated. Use native pgvector storage.",
            DeprecationWarning,
            stacklevel=2,
        )
        num_floats = len(data) // 4  # 4 bytes per float32
        return list(struct.unpack(f"{num_floats}f", data))


class DeterministicHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding provider.

    This provider generates embeddings by hashing text using a combination
    of character n-grams and word tokens, then mapping to fixed buckets.
    The result is normalized to unit length.

    Properties:
    - Deterministic: Same text always produces the same embedding
    - Fast: No network calls, pure computation
    - No dependencies: Uses only standard library
    - Dimension: 384 (standard for many embedding models)

    This is suitable for:
    - Testing and development
    - Early prototyping before integrating real embedding models
    - Scenarios where semantic quality is less important than speed

    Note: This does NOT provide real semantic understanding.
    Similar-meaning texts may have very different embeddings.
    For production semantic search, use a real embedding model.
    """

    DIMENSION = 384
    MODEL_NAME = "deterministic_hash_v1"

    # N-gram sizes for character-level features
    NGRAM_SIZES = [2, 3, 4]

    @property
    def dimension(self) -> int:
        """Return embedding dimension (384)."""
        return self.DIMENSION

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        return self.MODEL_NAME

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase, split on whitespace/punctuation.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Normalize: lowercase and replace punctuation with spaces
        normalized = text.lower()
        for char in ".,;:!?()[]{}\"'`~@#$%^&*-_=+|\\/<>":
            normalized = normalized.replace(char, " ")

        # Split and filter empty
        return [t for t in normalized.split() if t]

    def _get_ngrams(self, text: str) -> list[str]:
        """Extract character n-grams from text.

        Args:
            text: Input text

        Returns:
            List of n-gram strings
        """
        text = text.lower()
        ngrams = []

        for n in self.NGRAM_SIZES:
            for i in range(len(text) - n + 1):
                ngrams.append(text[i : i + n])

        return ngrams

    def _hash_to_bucket(self, token: str, salt: str = "") -> int:
        """Hash a token to a bucket index.

        Args:
            token: The token to hash
            salt: Optional salt for different hash functions

        Returns:
            Bucket index in range [0, DIMENSION)
        """
        h = hashlib.sha256((salt + token).encode("utf-8")).digest()
        # Use first 4 bytes as unsigned int
        value = int.from_bytes(h[:4], byteorder="big", signed=False)
        return value % self.DIMENSION

    def _hash_to_sign(self, token: str) -> int:
        """Determine sign (+1 or -1) for a token's contribution.

        Args:
            token: The token

        Returns:
            +1 or -1
        """
        h = hashlib.sha256(("sign_" + token).encode("utf-8")).digest()
        return 1 if h[0] % 2 == 0 else -1

    def _normalize(self, vector: list[float]) -> list[float]:
        """Normalize vector to unit length (L2 normalization).

        Args:
            vector: Input vector

        Returns:
            Normalized vector with L2 norm of 1
        """
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude < 1e-10:
            # Avoid division by zero; return zero vector
            return vector
        return [v / magnitude for v in vector]

    def embed_text(self, text: str) -> list[float]:
        """Generate a deterministic embedding for text.

        The algorithm:
        1. Extract word tokens and character n-grams
        2. Hash each feature to a bucket and accumulate with sign
        3. Normalize the result to unit length

        Args:
            text: The text to embed

        Returns:
            List of 384 floats representing the embedding
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.DIMENSION

        # Initialize bucket counts
        buckets = [0.0] * self.DIMENSION

        # Add word token contributions
        tokens = self._tokenize(text)
        for token in tokens:
            bucket = self._hash_to_bucket(token, salt="word_")
            sign = self._hash_to_sign(token)
            buckets[bucket] += sign * 1.0

        # Add n-gram contributions (with lower weight)
        ngrams = self._get_ngrams(text)
        for ngram in ngrams:
            bucket = self._hash_to_bucket(ngram, salt="ngram_")
            sign = self._hash_to_sign(ngram)
            buckets[bucket] += sign * 0.3  # Lower weight for n-grams

        # Normalize to unit length
        return self._normalize(buckets)

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a search query.

        For this deterministic provider, query embedding is the same
        as document embedding.

        Args:
            text: The query text

        Returns:
            List of 384 floats representing the embedding
        """
        return self.embed_text(text)


# Global provider instance (singleton pattern)
_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get the global embedding provider instance.

    Returns:
        The configured embedding provider (DeterministicHashEmbeddingProvider by default)
    """
    global _provider
    if _provider is None:
        _provider = DeterministicHashEmbeddingProvider()
    return _provider
