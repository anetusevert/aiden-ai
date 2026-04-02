"""S3/MinIO storage client for document vault.

This module provides a simple interface for storing and retrieving
files from S3-compatible storage (MinIO).
"""

import hashlib
import logging
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.config import settings

logger = logging.getLogger(__name__)


class S3StorageError(Exception):
    """Base exception for S3 storage errors."""

    pass


class S3ObjectNotFoundError(S3StorageError):
    """Raised when an object is not found in S3."""

    pass


class S3UploadError(S3StorageError):
    """Raised when an upload fails."""

    pass


class S3StorageClient:
    """Client for S3/MinIO storage operations.

    This client is configured to work with MinIO using path-style addressing.
    All configuration is read from settings (config.py) which uses canonical
    S3_* environment variables with fallback to legacy AWS_* vars.
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        region: str | None = None,
        use_ssl: bool | None = None,
        force_path_style: bool | None = None,
    ):
        """Initialize S3 storage client.

        All parameters default to values from config.py (which reads S3_* env vars).

        Args:
            endpoint_url: S3/MinIO endpoint URL (e.g., http://localhost:9000)
            access_key_id: S3/MinIO access key ID
            secret_access_key: S3/MinIO secret access key
            bucket_name: Default bucket name
            region: AWS region (default from S3_REGION or "us-east-1")
            use_ssl: Whether to use SSL (default from S3_USE_SSL)
            force_path_style: Force path-style addressing (default from S3_FORCE_PATH_STYLE)
        """
        # Use config values as defaults (canonical S3_* env vars)
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.access_key_id = access_key_id or settings.s3_access_key_id
        self.secret_access_key = secret_access_key or settings.s3_secret_access_key
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.region = region or settings.s3_region
        self.use_ssl = use_ssl if use_ssl is not None else settings.s3_use_ssl
        self.force_path_style = (
            force_path_style
            if force_path_style is not None
            else settings.s3_force_path_style
        )

        # Configure boto3 addressing style based on settings
        addressing_style = "path" if self.force_path_style else "auto"
        self._config = Config(
            signature_version="s3v4",
            s3={"addressing_style": addressing_style},
            retries={"max_attempts": 3, "mode": "standard"},
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
            config=self._config,
            use_ssl=self.use_ssl,
        )

    def put_object(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
        bucket: str | None = None,
    ) -> None:
        """Upload an object to S3.

        Args:
            key: Object key (path) in the bucket
            data: File data as bytes or file-like object
            content_type: MIME type of the file
            bucket: Bucket name (uses default if not specified)

        Raises:
            S3UploadError: If the upload fails
        """
        bucket = bucket or self.bucket_name

        try:
            # Convert bytes to BytesIO if needed
            if isinstance(data, bytes):
                body = BytesIO(data)
            else:
                body = data

            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
            logger.info(f"Uploaded object to s3://{bucket}/{key}")

        except ClientError as e:
            logger.error(f"Failed to upload to s3://{bucket}/{key}: {e}")
            raise S3UploadError(f"Failed to upload object: {e}") from e

    def get_object(
        self,
        key: str,
        bucket: str | None = None,
    ) -> tuple[bytes, str]:
        """Download an object from S3.

        Args:
            key: Object key (path) in the bucket
            bucket: Bucket name (uses default if not specified)

        Returns:
            Tuple of (file bytes, content type)

        Raises:
            S3ObjectNotFoundError: If the object is not found
            S3StorageError: If the download fails for another reason
        """
        bucket = bucket or self.bucket_name

        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            data = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            logger.info(f"Downloaded object from s3://{bucket}/{key}")
            return data, content_type

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise S3ObjectNotFoundError(
                    f"Object not found: s3://{bucket}/{key}"
                ) from e
            logger.error(f"Failed to download from s3://{bucket}/{key}: {e}")
            raise S3StorageError(f"Failed to download object: {e}") from e

    def get_object_stream(
        self,
        key: str,
        bucket: str | None = None,
    ) -> tuple[BinaryIO, str, int]:
        """Get a streaming response for an object from S3.

        Args:
            key: Object key (path) in the bucket
            bucket: Bucket name (uses default if not specified)

        Returns:
            Tuple of (streaming body, content type, content length)

        Raises:
            S3ObjectNotFoundError: If the object is not found
            S3StorageError: If the download fails for another reason
        """
        bucket = bucket or self.bucket_name

        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            content_type = response.get("ContentType", "application/octet-stream")
            content_length = response.get("ContentLength", 0)
            logger.info(f"Streaming object from s3://{bucket}/{key}")
            return response["Body"], content_type, content_length

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise S3ObjectNotFoundError(
                    f"Object not found: s3://{bucket}/{key}"
                ) from e
            logger.error(f"Failed to stream from s3://{bucket}/{key}: {e}")
            raise S3StorageError(f"Failed to stream object: {e}") from e

    def delete_object(
        self,
        key: str,
        bucket: str | None = None,
    ) -> None:
        """Delete an object from S3.

        Args:
            key: Object key (path) in the bucket
            bucket: Bucket name (uses default if not specified)

        Raises:
            S3StorageError: If the deletion fails
        """
        bucket = bucket or self.bucket_name

        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted object from s3://{bucket}/{key}")

        except ClientError as e:
            logger.error(f"Failed to delete s3://{bucket}/{key}: {e}")
            raise S3StorageError(f"Failed to delete object: {e}") from e

    def object_exists(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Check if an object exists in S3.

        Args:
            key: Object key (path) in the bucket
            bucket: Bucket name (uses default if not specified)

        Returns:
            True if object exists, False otherwise
        """
        bucket = bucket or self.bucket_name

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def bucket_exists(
        self,
        bucket: str | None = None,
    ) -> bool:
        """Check if a bucket exists in S3/MinIO.

        Useful for fail-fast validation in tests.

        Args:
            bucket: Bucket name (uses default if not specified)

        Returns:
            True if bucket exists, False otherwise
        """
        bucket = bucket or self.bucket_name

        try:
            self._client.head_bucket(Bucket=bucket)
            return True
        except ClientError:
            return False


def generate_storage_key(
    tenant_id: str,
    workspace_id: str,
    document_id: str,
    version_id: str,
    filename: str,
) -> str:
    """Generate a unique storage key for a document version.

    The key structure is:
    tenants/{tenant_id}/workspaces/{workspace_id}/documents/{document_id}/versions/{version_id}/{filename}

    Args:
        tenant_id: Tenant UUID
        workspace_id: Workspace UUID
        document_id: Document UUID
        version_id: Version UUID
        filename: Original filename

    Returns:
        Storage key string
    """
    # Sanitize filename to prevent path traversal
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"tenants/{tenant_id}/workspaces/{workspace_id}/documents/{document_id}/versions/{version_id}/{safe_filename}"


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of data.

    Args:
        data: File data as bytes

    Returns:
        Lowercase hex string of the SHA256 hash
    """
    return hashlib.sha256(data).hexdigest()


# Singleton instance for convenience
_storage_client: S3StorageClient | None = None


def get_storage_client() -> S3StorageClient:
    """Get the singleton S3 storage client instance.

    Returns:
        S3StorageClient instance
    """
    global _storage_client
    if _storage_client is None:
        _storage_client = S3StorageClient()
    return _storage_client


def get_s3_client() -> S3StorageClient:
    """Alias for get_storage_client() for dependency injection.

    Returns:
        S3StorageClient instance
    """
    return get_storage_client()
