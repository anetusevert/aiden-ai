# Railway Deployment Guide

Deploy the Aiden.ai monorepo on Railway as a multi-service project.

## Services Overview

| Service            | Type                     | Source                        |
| ------------------ | ------------------------ | ----------------------------- |
| **aiden-api**      | GitHub repo (Dockerfile) | `Dockerfile.api` at repo root |
| **aiden-web**      | GitHub repo (Dockerfile) | `apps/web/Dockerfile`         |
| **PostgreSQL**     | Railway managed plugin   | Auto-provisioned              |
| **Redis**          | Railway managed plugin   | Auto-provisioned              |
| **Collabora**      | Docker image             | `collabora/code:latest`       |
| **Object Storage** | External (Cloudflare R2) | Manual setup                  |

## Step 1: Create Railway Project

1. Go to https://railway.app and create a new **empty project**.
2. Connect your GitHub repository.

## Step 2: Add Managed Services

### PostgreSQL

- Click **+ New** > **Database** > **PostgreSQL**.
- Railway auto-provisions the database and provides `DATABASE_URL`.
- The pgvector extension is enabled automatically by the Alembic migration
  (`CREATE EXTENSION IF NOT EXISTS vector`).

### Redis

- Click **+ New** > **Database** > **Redis**.
- Railway auto-provisions Redis and provides `REDIS_URL`.

## Step 3: Add the API Service

1. Click **+ New** > **GitHub Repo** > select your repo.
2. In the service **Settings**:
   - **Root Directory**: `/` (repo root — required so the build can access `amin-soul/`).
   - **Builder**: Dockerfile
   - **Dockerfile Path**: `Dockerfile.api`
3. Set environment variables (see table below).
4. Enable **Public Networking** and note the assigned domain (e.g. `aiden-api-production-XXXX.up.railway.app`).

### API Environment Variables

| Variable               | Value                                                                     |
| ---------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`         | `${{Postgres.DATABASE_URL}}`                                              |
| `REDIS_URL`            | `${{Redis.REDIS_URL}}`                                                    |
| `ENVIRONMENT`          | `prod`                                                                    |
| `AUTH_ALLOW_DEV_LOGIN` | `false`                                                                   |
| `JWT_SECRET`           | Generate: `openssl rand -hex 32`                                          |
| `COOKIE_SECURE`        | `true`                                                                    |
| `CORS_ORIGINS_STR`     | `https://<web-domain>.railway.app,https://<collabora-domain>.railway.app` |
| `COLLABORA_URL`        | `https://<collabora-domain>.railway.app`                                  |
| `WOPI_INTERNAL_URL`    | `http://aiden-api.railway.internal:8000/api/v1/wopi`                      |
| `WOPI_PUBLIC_URL`      | `https://<api-domain>.railway.app/api/v1/wopi`                            |
| `WOPI_BASE_URL`        | `https://<api-domain>.railway.app/api/v1/wopi`                            |
| `S3_ENDPOINT_URL`      | Your R2 / S3 endpoint URL                                                 |
| `S3_ACCESS_KEY_ID`     | Your R2 / S3 access key                                                   |
| `S3_SECRET_ACCESS_KEY` | Your R2 / S3 secret key                                                   |
| `S3_BUCKET_NAME`       | `aiden-storage`                                                           |
| `S3_REGION`            | `auto` (R2) or your AWS region                                            |
| `S3_USE_SSL`           | `true`                                                                    |
| `S3_FORCE_PATH_STYLE`  | `true`                                                                    |
| `LLM_PROVIDER`         | `openai` (or `stub` for initial testing)                                  |
| `LLM_MODEL`            | `gpt-4o`                                                                  |
| `LLM_API_KEY`          | Your OpenAI API key                                                       |

> Railway injects `PORT` automatically. The startup script (`start.sh`) uses
> `${PORT:-8000}` so this is handled without configuration.
>
> `CORS_ORIGINS_STR` must contain the exact browser origin for the deployed web
> app, with scheme and host only. Do not add a trailing slash, and do not
> replace the web origin with the API origin.

## Step 4: Add the Web Service

1. Click **+ New** > **GitHub Repo** > select your repo.
2. In the service **Settings**:
   - **Root Directory**: `apps/web`
   - **Builder**: Dockerfile
   - **Dockerfile Path**: `Dockerfile`
3. Set environment variables (see table below).
4. Enable **Public Networking** and note the assigned domain.

### Web Environment Variables

| Variable                        | Value                                    |
| ------------------------------- | ---------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`      | `https://<api-domain>.railway.app`       |
| `API_INTERNAL_BASE_URL`         | `http://aiden-api.railway.internal:8000` |
| `NEXT_PUBLIC_COLLABORA_URL`     | `https://<collabora-domain>.railway.app` |
| `NEXT_PUBLIC_COLLABORA_ENABLED` | `true`                                   |

> `NEXT_PUBLIC_API_BASE_URL` must be the API origin only, for example
> `https://aiden-api-production-xxxx.up.railway.app`. Do not append `/api` or a
> trailing slash because the web app already appends `/api/v1/...` routes at
> runtime.
>
> This is especially important for Office/Collabora routes. The editor requests
> `POST /api/v1/office/documents/{id}/wopi-token` from the browser, so a value
> like `https://<api-domain>.railway.app/api` will produce broken URLs and
> misleading `Failed to fetch` errors in the UI.

## Step 5: Add the Collabora Service

1. Click **+ New** > **Docker Image**.
2. Set image to `collabora/code:latest`.
3. Set environment variables (see table below).
4. Enable **Public Networking** and note the assigned domain.

### Collabora Environment Variables

| Variable       | Value                                           |
| -------------- | ----------------------------------------------- |
| `aliasgroup1`  | `https://<api-domain>.railway.app`              |
| `extra_params` | `--o:ssl.enable=false --o:ssl.termination=true` |
| `username`     | `admin`                                         |
| `password`     | Set a strong password                           |
| `server_name`  | `<collabora-domain>.railway.app`                |

### Office / Collabora Wiring Checklist

The Office editor only works when all four URL roles stay distinct and aligned:

| Variable                    | Example                                              | Used by                           |
| --------------------------- | ---------------------------------------------------- | --------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`  | `https://<api-domain>.railway.app`                   | Browser -> API                    |
| `NEXT_PUBLIC_COLLABORA_URL` | `https://<collabora-domain>.railway.app`             | Browser -> Collabora iframe       |
| `WOPI_INTERNAL_URL`         | `http://aiden-api.railway.internal:8000/api/v1/wopi` | Collabora -> API                  |
| `aliasgroup1`               | `https://<api-domain>.railway.app`                   | Collabora allowlist for WOPI host |

Rules:

1. `NEXT_PUBLIC_API_BASE_URL` must be the API origin only. Do not append `/api`.
2. `CORS_ORIGINS_STR` must include the exact web origin, including the correct `https://` scheme and no trailing slash.
3. `NEXT_PUBLIC_COLLABORA_URL` and `COLLABORA_URL` must point to the public Collabora domain the browser can load in an iframe.
4. `WOPI_INTERNAL_URL` must stay on Railway private networking so the Collabora service can reach the API directly.
5. `aliasgroup1` must match the API host that Collabora is expected to trust for WOPI requests.

## Step 6: Object Storage (Cloudflare R2)

Self-hosted MinIO on Railway is not recommended for production because
Railway service restarts can cause data loss.

**Recommended: Cloudflare R2** (S3-compatible, no egress fees).

1. Create a Cloudflare account and enable R2.
2. Create a bucket named `aiden-storage`.
3. Generate an R2 API token with read/write access.
4. Set the `S3_*` variables on the API service (see table in Step 3).

Alternatives: AWS S3, Backblaze B2, DigitalOcean Spaces.

## Step 7: Update Cross-Service URLs

After all services are deployed and have their public domains, go back and
update the placeholder `<...-domain>` values in all environment variables:

1. **API service**: update `CORS_ORIGINS_STR`, `COLLABORA_URL`, `WOPI_PUBLIC_URL`, `WOPI_BASE_URL`.
2. **Web service**: update `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_COLLABORA_URL`.
3. **Collabora service**: update `aliasgroup1`, `server_name`.

For internal (service-to-service) communication, use Railway's private
networking: `http://<service-name>.railway.internal:<port>`.

### Cross-Origin Contract

For the default Railway setup, the web app and API run on different public
origins. Keep that contract consistent:

1. The web service must set `NEXT_PUBLIC_API_BASE_URL=https://<api-domain>.railway.app`.
2. The API service must set `CORS_ORIGINS_STR=https://<web-domain>.railway.app,...`.
3. `NEXT_PUBLIC_API_BASE_URL` must not include `/api` because the frontend
   already requests `/api/v1/...`.
4. `CORS_ORIGINS_STR` must include the web origin exactly, with no trailing
   slash, or the browser will block credentialed requests before the UI can read
   the real response.
5. After changing either variable, redeploy both services so the API CORS policy
   and the web bundle pick up the same origin pair.

### Office Verification

After deploying the web, API, and Collabora services together:

1. Open the deployed web app and create an Office document.
2. Confirm the browser request to `POST /api/v1/office/documents/{id}/wopi-token` succeeds.
3. Inspect the returned `collabora_editor_url`:
   - the base must be the public Collabora origin
   - the encoded `WOPISrc` must point at `WOPI_INTERNAL_URL`
4. Confirm Collabora loads the iframe and then calls:
   - `GET /api/v1/wopi/files/{id}`
   - `GET /api/v1/wopi/files/{id}/contents`
   - `POST /api/v1/wopi/files/{id}/contents` after a save
5. If step 2 fails in the browser, fix `NEXT_PUBLIC_API_BASE_URL`, cookies, or `CORS_ORIGINS_STR` first.
6. If step 2 succeeds but the iframe stalls, check `NEXT_PUBLIC_COLLABORA_URL`, `WOPI_INTERNAL_URL`, and `aliasgroup1`.

## Verification

After deployment, verify the API health endpoint:

```bash
curl https://<api-domain>.railway.app/health
```

Expected response:

```json
{
  "status": "healthy",
  "environment": "prod",
  "llm_provider": "openai",
  "llm_model": "gpt-4o"
}
```

Then verify browser-origin access from the deployed web domain:

```bash
curl -i "https://<api-domain>.railway.app/api/v1/clients" \
  -H "Origin: https://<web-domain>.railway.app"
```

Expected result:

- The response includes `access-control-allow-origin: https://<web-domain>.railway.app`
- The response includes `access-control-allow-credentials: true`
- A `404` for a specific client id should come from the API body, not from the
  browser blocking the response

## Security Checklist

- [ ] `ENVIRONMENT=prod` (disables dev-only features)
- [ ] `AUTH_ALLOW_DEV_LOGIN=false` (disables passwordless dev login)
- [ ] `JWT_SECRET` is a strong random value (not the dev default)
- [ ] `COOKIE_SECURE=true` (enforces HTTPS-only cookies)
- [ ] PostgreSQL and Redis have **public networking disabled** (internal only)
- [ ] Collabora `password` is not the default `changeme`

## Startup Sequence

The API container runs `start.sh` which:

1. Executes `alembic upgrade head` to apply any pending database migrations.
2. Starts `uvicorn` on `$PORT` (injected by Railway).

If migrations fail, the container will exit and Railway will show the error
in the deploy logs.

## Troubleshooting

| Symptom                                                                   | Cause                                                                                                                 | Fix                                                                                                                                     |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Build fails with "Railpack could not determine how to build"              | Root directory or Dockerfile path misconfigured                                                                       | Set root to `/`, Dockerfile to `Dockerfile.api`                                                                                         |
| `CREATE EXTENSION vector` fails                                           | Railway Postgres version too old                                                                                      | Check Postgres version in Railway dashboard; pgvector requires PG 13+                                                                   |
| API returns 500 on startup                                                | Database not reachable                                                                                                | Verify `DATABASE_URL` uses `${{Postgres.DATABASE_URL}}` reference                                                                       |
| Collabora iframe fails to load                                            | CORS or aliasgroup1 mismatch                                                                                          | Ensure `aliasgroup1` matches the API public URL                                                                                         |
| Cookies not attaching                                                     | Mixed HTTP/HTTPS or domain mismatch                                                                                   | Ensure `COOKIE_SECURE=true` and all URLs use HTTPS                                                                                      |
| WOPI callbacks fail                                                       | Collabora can't reach API                                                                                             | Use Railway internal URL for `WOPI_INTERNAL_URL`                                                                                        |
| Client detail page shows a blocked fetch or fake "Client not found" state | `NEXT_PUBLIC_API_BASE_URL` points at the wrong host, includes `/api`, or `CORS_ORIGINS_STR` is missing the web origin | Set `NEXT_PUBLIC_API_BASE_URL` to the API origin only and include the exact web origin in `CORS_ORIGINS_STR`, then redeploy API and web |
