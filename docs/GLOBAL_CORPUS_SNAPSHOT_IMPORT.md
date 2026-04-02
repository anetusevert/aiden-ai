# Global Corpus Snapshot Import

This document defines the contract for importing GCC Harvester snapshots into Aiden.ai's global legal corpus.

## Overview

The snapshot import endpoint allows platform administrators to bulk-import legal instrument data from gcc-harvester ZIP snapshots into the Aiden global corpus. This is a one-way data pipeline:

```
gcc-harvester → ZIP snapshot → Aiden.ai POST /global/legal-import/snapshot → Global Corpus
```

## Expected ZIP Structure

The gcc-harvester produces ZIP archives with the following structure:

```
snapshot_YYYY-MM-DD.zip
├── manifest.json                    # Metadata about the snapshot
├── records/
│   └── <connector>.jsonl            # One JSONL file per connector/source
└── raw/
    └── <sha256>.<ext>               # Raw artifact files (PDF, DOCX, HTML, etc.)
```

### manifest.json

```json
{
  "harvester_version": "1.0.0",
  "created_at": "2025-01-27T10:00:00Z",
  "connector_count": 3,
  "record_count": 150,
  "jurisdictions": ["UAE", "KSA", "DIFC"]
}
```

### JSONL Record Format

Each line in a `records/<connector>.jsonl` file is a JSON object with the following keys:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `jurisdiction` | string | Yes | GCC jurisdiction code (UAE, KSA, DIFC, ADGM, OMAN, BAHRAIN, QATAR, KUWAIT) |
| `source_name` | string | Yes | Connector/source identifier (e.g., "moj_uae") |
| `source_url` | string | Yes | Full URL to the official source |
| `retrieved_at` | string | Yes | ISO 8601 timestamp of retrieval |
| `title_ar` | string | Yes | Arabic title of the instrument |
| `instrument_type_guess` | string | Yes | Best guess of instrument type |
| `published_at_guess` | string | No | Best guess of publication date (YYYY-MM-DD) |
| `raw_artifact_path` | string | Yes | Path to raw file within ZIP (e.g., "raw/abc123.pdf") |
| `raw_sha256` | string | Yes | SHA256 hash of the raw artifact file |

Example record:

```json
{
  "jurisdiction": "UAE",
  "source_name": "moj_uae",
  "source_url": "https://elaws.moj.gov.ae/mojLawDetails.aspx?lawNo=5&year=1985",
  "retrieved_at": "2025-01-27T09:00:00Z",
  "title_ar": "قانون المعاملات المدنية",
  "instrument_type_guess": "federal_law",
  "published_at_guess": "1985-01-01",
  "raw_artifact_path": "raw/abc123def456.pdf",
  "raw_sha256": "abc123def456789..."
}
```

## Key Derivation (Dedupe Strategy)

### Instrument Key

Uniquely identifies a legal instrument across imports. Derived deterministically:

```
instrument_key = "{jurisdiction}:{source_name}:{sha256(source_url)}"
```

Where `sha256(source_url)` is the **FULL 64-character lowercase hex** SHA256 hash (no truncation).

Example:
```
UAE:moj_uae:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

**Rationale**: The source URL is the canonical identifier from the harvester. We hash it to normalize and avoid special characters. Using the full 64-char hash ensures collision-free uniqueness across imports.

### Version Key

Uniquely identifies a specific version/snapshot of an instrument. Derived from the file content:

```
version_key = "{raw_sha256}"
```

**Rationale**: The SHA256 of the raw artifact uniquely identifies the exact file content. If the same file is imported twice, it won't create duplicate versions.

## Database Mapping

### LegalInstrument

| JSONL Field | DB Column | Notes |
|-------------|-----------|-------|
| `jurisdiction` | `jurisdiction` | Direct mapping, validated against known jurisdictions |
| `source_url` | `official_source_url` | Full source URL stored |
| `title_ar` | `title` | Arabic title used as primary title (translation deferred) |
| `title_ar` | `title_ar` | Arabic title stored in dedicated field |
| `instrument_type_guess` | `instrument_type` | Mapped to valid enum, fallback to "other" |
| `published_at_guess` | `published_at` | Parsed as date, nullable if invalid |
| - | `instrument_key` | Derived dedupe key |
| - | `import_batch_id` | UUID of the import batch |
| - | `status` | Default: "active" |

### LegalInstrumentVersion

| JSONL Field | DB Column | Notes |
|-------------|-----------|-------|
| `raw_sha256` | `sha256` | File content hash |
| `raw_sha256` | `version_key` | Dedupe key (same as sha256) |
| `raw_artifact_path` | `file_name` | **Derived**: `{raw_sha256}.{ext}` (NOT the raw path) |
| - | `content_type` | Inferred from extension (pdf, docx, html, txt; else octet-stream) |
| - | `version_label` | Set to "imported" |
| - | `storage_key` | S3 key: `global-legal/{instrument_id}/versions/{version_id}/{file_name}` |
| - | `is_indexed` | Default: `false` (indexing deferred) |
| - | `import_batch_id` | UUID of the import batch |
| - | `imported_at` | Timestamp of import |
| - | `language` | "ar" if `title_ar` exists and non-empty, else "mixed" |

#### File Name Derivation

The `file_name` is constructed from the record, NOT stored as the raw artifact path:

```
raw_artifact_path: "raw/abc123def456.pdf"
→ parse extension: "pdf"
→ file_name: "{raw_sha256}.pdf"
```

This ensures:
1. Consistent naming based on content hash
2. No path components stored in file_name
3. Extension preserved for content-type inference

## Unique Constraints

| Table | Constraint Name | Columns | Notes |
|-------|-----------------|---------|-------|
| `legal_instruments` | `uq_legal_instruments_jurisdiction_instrument_key` | `(jurisdiction, instrument_key)` | Partial index, WHERE instrument_key IS NOT NULL |
| `legal_instrument_versions` | `uq_legal_instrument_versions_instrument_version_key` | `(legal_instrument_id, version_key)` | Partial index, WHERE version_key IS NOT NULL |

## Storage Layout

Raw files are stored in S3/MinIO following the pattern:

```
global-legal/{instrument_id}/versions/{version_id}/{filename}
```

Example:
```
global-legal/550e8400-e29b-41d4-a716-446655440000/versions/6ba7b810-9dad-11d1-80b4-00c04fd430c8/abc123def456.pdf
```

## What is Created

On each import:

1. **LegalInstrument** - Upserted by `(jurisdiction, instrument_key)`
   - Created if new
   - Updated (`updated_at` timestamp, `import_batch_id`) if existing

2. **LegalInstrumentVersion** - Created if `version_key` not present for instrument
   - File uploaded to S3
   - Version row created with `is_indexed=false`
   - Skipped if version_key already exists

## What is Deferred

The following are **NOT** performed during snapshot import:

| Feature | Status | How to Enable |
|---------|--------|---------------|
| Text Extraction | Deferred | Use `/global/legal-instruments/{id}/versions/{version_id}/reindex` |
| Chunking | Deferred | Triggered by reindex |
| Embedding Generation | Deferred | Triggered by reindex |
| Indexing | `is_indexed=false` | Triggered by reindex |

## Idempotency Rules

The import is fully idempotent:

1. **Same snapshot twice** → 0 new instruments, 0 new versions
2. **Same instrument, new version** → 0 new instruments, 1 new version
3. **New instrument** → 1 new instrument, 1 new version

The response clearly indicates what was created vs. what already existed:
- `instruments_created`: New instruments added
- `instruments_existing`: Instruments that matched by key
- `versions_created`: New versions added
- `versions_existing`: Versions skipped (already exist by version_key)

## Import Limits (Enforced in Code)

All limits are enforced at runtime with clear errors:

| Limit | Value | Enforcement | Error |
|-------|-------|-------------|-------|
| Max records per request | 5,000 | After parsing JSONL | `RecordLimitExceededError` → 400 Bad Request |
| Max ZIP size | 500 MB | On upload read | `ZipSizeLimitExceededError` → 400 Bad Request |
| Max individual file size | 50 MB | On artifact extraction | Per-record failure (error: `raw_file_too_large`) |

### Limit Constants

```python
MAX_RECORDS_PER_IMPORT = 5000
MAX_ZIP_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
```

### Per-Record File Size Failures

When an individual artifact exceeds `MAX_FILE_SIZE_BYTES`:
- The record is added to `failures[]` with error `"raw_file_too_large: <size> bytes (max 50 MB)"`
- `failure_count` is incremented
- `versions_created` is NOT incremented for that record
- Other records continue processing normally

Example failure in response:
```json
{
  "failures": [
    {
      "record_index": 5,
      "source_url": "https://example.com/large-law.pdf",
      "error": "File too large: 75,000,000 bytes (max 52,428,800 bytes / 50 MB)"
    }
  ],
  "failure_count": 1
}
```

## Error Handling

| Error Type | HTTP Status | Response |
|------------|-------------|----------|
| Invalid/missing manifest.json | 400 | `{"detail": "manifest.json not found in ZIP"}` |
| Zip-slip attack detected | 400 | `{"detail": "Security error: Unsafe path detected"}` |
| Record limit exceeded | 400 | `{"detail": "Too many records: X (max 5000)"}` |
| Per-record failures | 200 | Included in `failures` array (max 20 shown) |

## API Endpoint

### POST /global/legal-import/snapshot

**Authorization**: Platform Admin only (`is_platform_admin=true`)

**Content-Type**: `multipart/form-data`

**Request**:
```
POST /global/legal-import/snapshot
Content-Type: multipart/form-data

file: <snapshot.zip>
```

**Response** (200 OK):
```json
{
  "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "instruments_created": 45,
  "instruments_existing": 5,
  "versions_created": 48,
  "versions_existing": 2,
  "failures": [
    {
      "record_index": 12,
      "source_url": "https://example.com/law/123",
      "error": "Missing raw artifact file"
    }
  ],
  "failure_count": 3,
  "processing_time_ms": 12500
}
```

## Security Considerations

1. **Platform Admin Only**: Endpoint requires `is_platform_admin=true`
2. **Zip-Slip Prevention**: All paths validated before extraction
   - Absolute paths rejected
   - Parent directory traversal (`..`) rejected
3. **Content-Type Mapping**: Known document types mapped to MIME types
4. **SHA256 Verification**: File hashes validated against declared values

## Title Handling

Since gcc-harvester primarily provides Arabic titles (`title_ar`), and the schema requires a non-null `title` field:

1. If `title_ar` is present, use it for both `title` and `title_ar`
2. This is a temporary measure until translation is available
3. Future enhancement: Machine translation for English titles

**Important**: The `title` field may contain Arabic text. UI should handle RTL rendering appropriately.

## Audit Trail

All imports are logged to the audit system:

```json
{
  "action": "global_legal.import",
  "status": "success",
  "resource_type": "snapshot_import",
  "resource_id": "<import_batch_id>",
  "meta": {
    "import_batch_id": "550e8400-...",
    "instruments_created": 45,
    "instruments_existing": 5,
    "versions_created": 48,
    "versions_existing": 2,
    "failure_count": 3,
    "processing_time_ms": 12500,
    "source_file": "snapshot_2025-01-27.zip"
  }
}
```

Security events (zip-slip attempts) are logged separately with `action: "global_legal.import.security"`.

## Migration Summary

**Migration ID**: `20250127_000001_add_snapshot_import_keys`

**Changes**:
- Added `instrument_key` (TEXT, nullable) to `legal_instruments`
- Added `import_batch_id` (UUID, nullable) to `legal_instruments`
- Added unique partial index on `(jurisdiction, instrument_key)` WHERE `instrument_key IS NOT NULL`
- Added `version_key` (TEXT, nullable) to `legal_instrument_versions`
- Added `import_batch_id` (UUID, nullable) to `legal_instrument_versions`
- Added `imported_at` (TIMESTAMPTZ, nullable) to `legal_instrument_versions`
- Added unique partial index on `(legal_instrument_id, version_key)` WHERE `version_key IS NOT NULL`

All columns are nullable to maintain backward compatibility with manually created instruments/versions.
