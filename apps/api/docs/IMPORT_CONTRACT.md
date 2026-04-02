# GCC Harvester Snapshot Import Contract

> **Canonical contract**: [`docs/GLOBAL_CORPUS_SNAPSHOT_IMPORT.md`](../../../docs/GLOBAL_CORPUS_SNAPSHOT_IMPORT.md)
>
> This file contains implementation details for the API layer. The canonical specification is in the root `docs/` folder.

This document defines the contract for importing GCC Harvester snapshots into Aiden.ai's global legal corpus.

## Overview

The snapshot import endpoint allows platform administrators to bulk-import legal instrument data from gcc-harvester ZIP snapshots into the Aiden global corpus. This is a one-way data pipeline:

```
gcc-harvester → ZIP snapshot → Aiden.ai POST /global/legal-import/snapshot → Global Corpus
```

## Input Snapshot Format

The gcc-harvester produces ZIP archives with the following structure:

```
snapshot_2025-01-27.zip
├── manifest.json                    # Metadata about the snapshot
├── records/
│   └── <connector>.jsonl            # One JSONL file per connector/source
└── raw/
    └── <sha256>.<ext>               # Raw artifact files (PDF, DOCX, etc.)
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

### JSONL Records

Each line in a `records/<connector>.jsonl` file is a JSON object:

```json
{
  "jurisdiction": "UAE",
  "source_name": "moj_uae",
  "source_url": "https://elaws.moj.gov.ae/...",
  "retrieved_at": "2025-01-27T09:00:00Z",
  "title_ar": "قانون المعاملات المدنية",
  "instrument_type_guess": "federal_law",
  "published_at_guess": "1985-01-01",
  "raw_artifact_path": "raw/abc123.pdf",
  "raw_sha256": "abc123..."
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
| jurisdiction | jurisdiction | Direct mapping |
| source_name | official_source_url | Stored in URL field |
| source_url | official_source_url | Full source URL |
| title_ar | title | Fallback: English title = Arabic title if no translation |
| title_ar | title_ar | Arabic title stored |
| instrument_type_guess | instrument_type | Mapped to valid types, default "other" |
| published_at_guess | published_at | Parsed as date, nullable |
| - | instrument_key | Derived key for dedupe |
| - | import_batch_id | UUID of the import batch |
| - | status | Default: "active" |

### LegalInstrumentVersion

| JSONL Field | DB Column | Notes |
|-------------|-----------|-------|
| raw_sha256 | sha256 | File content hash |
| raw_sha256 | version_key | Dedupe key (same as sha256) |
| raw_artifact_path | file_name | **Derived**: `{raw_sha256}.{ext}` (NOT the raw path) |
| - | content_type | Inferred from extension (pdf, docx, html, txt; else octet-stream) |
| - | storage_key | S3 key: `global-legal/{instrument_id}/versions/{version_id}/{file_name}` |
| - | is_indexed | Default: false (indexing deferred) |
| - | import_batch_id | UUID of the import batch |
| - | imported_at | Timestamp of import |
| - | language | "ar" if title_ar exists, else "mixed" |

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

| Table | Constraint | Columns |
|-------|------------|---------|
| legal_instruments | uq_legal_instruments_jurisdiction_instrument_key | (jurisdiction, instrument_key) |
| legal_instrument_versions | uq_legal_instrument_versions_instrument_version_key | (legal_instrument_id, version_key) |

## Storage Layout

Raw files are stored in S3 following the existing pattern:

```
global-legal/{instrument_id}/versions/{version_id}/{filename}
```

Example:
```
global-legal/550e8400-e29b-41d4-a716-446655440000/versions/6ba7b810-9dad-11d1-80b4-00c04fd430c8/abc123.pdf
```

## What is Created

On each import:

1. **LegalInstrument** - Upserted by (jurisdiction, instrument_key)
   - Created if new
   - Updated (updated_at timestamp) if existing

2. **LegalInstrumentVersion** - Created if version_key not present
   - File uploaded to S3
   - Version row created with `is_indexed=false`
   - Skipped if version_key already exists for the instrument

## What is Deferred

The following are NOT performed during snapshot import:

1. **Text Extraction** - Not run; `extracted_text_id` remains null
2. **Chunking** - No `LegalChunk` rows created
3. **Embedding Generation** - No `LegalChunkEmbedding` rows created
4. **Indexing** - `is_indexed` remains false

To index imported instruments, use the existing `/global/legal-instruments/{id}/versions/{version_id}/reindex` endpoint.

## Import Limits (Enforced in Code)

All limits are enforced at runtime with clear 400 errors:

| Limit | Value | Enforcement | Error |
|-------|-------|-------------|-------|
| Max records per request | 5,000 | After parsing JSONL | `RecordLimitExceededError` → 400 |
| Max ZIP size | 500 MB | On upload read | `ZipSizeLimitExceededError` → 400 |
| Max individual file size | 50 MB | On artifact extraction | Logged as failure per record |

### Limit Constants

```python
MAX_RECORDS_PER_IMPORT = 5000
MAX_ZIP_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
```

## Error Handling

| Error Type | HTTP Status | Behavior |
|------------|-------------|----------|
| Invalid manifest | 400 Bad Request | Entire import rejected |
| ZIP size limit exceeded | 400 Bad Request | Entire import rejected |
| Record limit exceeded | 400 Bad Request | Entire import rejected |
| Zip-slip attack detected | 400 Bad Request | Entire import rejected (security) |
| Missing required fields in record | N/A | Logged as failure, continue with other records |
| Individual file too large (>50MB) | N/A | Logged as failure, continue with other records |
| SHA256 mismatch | N/A | Logged as failure, continue with other records |
| S3 upload failure | N/A | Logged as failure for that record |

## API Response

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
      "source_url": "https://...",
      "error": "Missing raw artifact file"
    }
  ],
  "failure_count": 3,
  "processing_time_ms": 12500
}
```

## Security Considerations

1. **Platform Admin Only**: Endpoint requires `is_platform_admin=true`
2. **Zip-Slip Prevention**: All paths validated against traversal attacks
3. **Content-Type Validation**: Only known document types accepted
4. **SHA256 Verification**: File hashes validated against declared values

## Title Handling

Since gcc-harvester primarily provides Arabic titles (`title_ar`), and the schema requires a non-null `title` field:

1. If `title_ar` is present, use it for both `title` and `title_ar`
2. This is a temporary measure until translation is available
3. Future: Implement machine translation for English titles

**Important**: This means `title` may contain Arabic text. UI should handle RTL rendering.

## Idempotency

The import is fully idempotent:

1. Re-importing the same snapshot produces zero new instruments/versions
2. The response will show `instruments_existing` and `versions_existing` counts
3. S3 uploads are skipped for existing versions (identified by version_key)

## Audit Trail

All imports are logged:

```json
{
  "action": "global_legal.import",
  "status": "success",
  "resource_type": "snapshot_import",
  "meta": {
    "import_batch_id": "...",
    "instruments_created": 45,
    "versions_created": 48,
    "source_file": "snapshot_2025-01-27.zip"
  }
}
```
