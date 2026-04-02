"""Tests for configuration loading.

Test Categories:
- Unit tests: No database required

Run unit tests only:
    uv run pytest tests/test_config.py -v
"""

import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestS3ConfigFallback:
    """Tests for S3 configuration with legacy AWS_* fallback."""

    def test_canonical_s3_vars_preferred(self):
        """Canonical S3_* vars are preferred over AWS_* vars."""
        env = {
            "S3_ENDPOINT_URL": "http://canonical:9000",
            "S3_ACCESS_KEY_ID": "canonical_key",
            "S3_SECRET_ACCESS_KEY": "canonical_secret",
            "S3_BUCKET_NAME": "canonical-bucket",
            "AWS_ENDPOINT_URL": "http://legacy:9000",
            "AWS_ACCESS_KEY_ID": "legacy_key",
            "AWS_SECRET_ACCESS_KEY": "legacy_secret",
        }

        with patch.dict(os.environ, env, clear=True):
            # Reset the module to pick up new env vars
            import importlib

            import src.config

            # Reset the legacy warning flag
            src.config._legacy_warning_emitted = False
            importlib.reload(src.config)

            settings = src.config.Settings()

            assert settings.s3_endpoint_url == "http://canonical:9000"
            assert settings.s3_access_key_id == "canonical_key"
            assert settings.s3_secret_access_key == "canonical_secret"
            assert settings.s3_bucket_name == "canonical-bucket"

    def test_aws_fallback_works_when_s3_not_set(self):
        """AWS_* vars work as fallback when S3_* vars are not set."""
        env = {
            "AWS_ENDPOINT_URL": "http://legacy:9000",
            "AWS_ACCESS_KEY_ID": "legacy_key",
            "AWS_SECRET_ACCESS_KEY": "legacy_secret",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import src.config

            # Reset the legacy warning flag
            src.config._legacy_warning_emitted = False
            importlib.reload(src.config)

            settings = src.config.Settings()

            assert settings.s3_endpoint_url == "http://legacy:9000"
            assert settings.s3_access_key_id == "legacy_key"
            assert settings.s3_secret_access_key == "legacy_secret"

    def test_defaults_used_when_no_env_vars(self):
        """Default values are used when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            # Reset the legacy warning flag
            src.config._legacy_warning_emitted = False
            importlib.reload(src.config)

            settings = src.config.Settings()

            assert settings.s3_endpoint_url == "http://localhost:9000"
            assert settings.s3_access_key_id == "minioadmin"
            assert settings.s3_secret_access_key == "minioadmin"
            assert settings.s3_bucket_name == "aiden-storage"
            assert settings.s3_region == "us-east-1"
            assert settings.s3_use_ssl is False
            assert settings.s3_force_path_style is True

    def test_minio_bucket_fallback(self):
        """MINIO_BUCKET falls back when S3_BUCKET_NAME is not set."""
        env = {
            "MINIO_BUCKET": "legacy-minio-bucket",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import src.config

            src.config._legacy_warning_emitted = False
            importlib.reload(src.config)

            settings = src.config.Settings()

            assert settings.s3_bucket_name == "legacy-minio-bucket"

    def test_s3_bucket_name_preferred_over_minio_bucket(self):
        """S3_BUCKET_NAME is preferred over MINIO_BUCKET."""
        env = {
            "S3_BUCKET_NAME": "canonical-bucket",
            "MINIO_BUCKET": "legacy-bucket",
        }

        with patch.dict(os.environ, env, clear=True):
            import importlib

            import src.config

            src.config._legacy_warning_emitted = False
            importlib.reload(src.config)

            settings = src.config.Settings()

            assert settings.s3_bucket_name == "canonical-bucket"
