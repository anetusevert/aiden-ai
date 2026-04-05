# Collabora Online Integration — HeyAmin

> Developer skill document for any agent or engineer working on the Collabora integration.
> Read this before touching anything in `routers/wopi.py`, `services/office_service.py`,
> or `components/office/CollaboraEditor.tsx`.

---

## Network Topology

```
Browser
  │
  ├──► Collabora iframe  →  http://localhost:9980  (COLLABORA_URL)
  │         │
  │         │  Collabora server (Docker) calls WOPI internally:
  │         └──► http://api:8000/api/v1/wopi/files/{id}  (WOPI_INTERNAL_URL)
  │
  └──► HeyAmin API  →  http://localhost:8000  (NEXT_PUBLIC_API_BASE_URL)
```

**The golden rule: never mix internal and public URLs.**

| Variable | Value | Who uses it |
|---|---|---|
| `COLLABORA_URL` | `http://localhost:9980` | Browser → Collabora iframe src |
| `WOPI_INTERNAL_URL` | `http://api:8000/api/v1/wopi` | Collabora server → WOPI API |
| `WOPI_PUBLIC_URL` | `http://localhost:8000/api/v1/wopi` | Display/logs only |
| `aliasgroup1` | `http://api:8000` | Collabora whitelist of allowed WOPI hosts |

### Why WOPISrc uses the Docker-internal URL

The `collabora_editor_url` returned to the frontend looks like:

```
http://localhost:9980/browser/dist/cool.html
  ?WOPISrc=http%3A%2F%2Fapi%3A8000%2Fapi%2Fv1%2Fwopi%2Ffiles%2F{id}
  &access_token={token}
```

The browser loads this and opens the Collabora iframe. Collabora's JavaScript then
tells the Collabora **server** (running in Docker) to fetch `WOPISrc`. That server
can reach `http://api:8000` through the Docker network. The browser itself never
needs to reach `api:8000` — it just passes the parameter to Collabora.

---

## WOPI Flow (step by step)

1. **Frontend** calls `POST /api/v1/office/documents/{id}/wopi-token`
2. **Backend** generates a 64-char hex token, stores it in `wopi_tokens` table (TTL 24h)
3. **Backend** returns `{ token, collabora_editor_url, expires_at }`
4. **Frontend** sets `iframe.src = collabora_editor_url`
5. **Collabora** fetches `CheckFileInfo` → validates token, returns metadata
6. **Collabora** fetches `GetFile` → streams bytes from MinIO
7. **User edits** → Collabora calls `PutFile` → uploads new bytes to MinIO
8. **After save** → frontend dispatches `collabora-reload` event → iframe reloads

---

## Authentication

- WOPI endpoints (`/api/v1/wopi/**`) use `?access_token=<token>` query param.
- They do **NOT** use JWT cookies. They validate against the `wopi_tokens` DB table.
- Never add `Depends(get_current_user)` or `Depends(require_viewer())` to WOPI routes.
- CORS must include `http://localhost:9980` for Collabora's iframe to communicate.

---

## Debugging

### Container not starting
```bash
docker compose ps collabora
docker compose logs collabora --tail 50
```

### Blank iframe / WebSocket errors
- Open Browser DevTools → Network tab → filter `cool.html`
- The URL must use `localhost:9980`, NOT `api:9980` or `collabora:9980`
- Check `WOPISrc` in the URL — must use `api:8000` (Docker-internal)
- CORS errors → ensure `http://localhost:9980` is in `CORS_ORIGINS_STR`

### 401 on WOPI endpoints
- Check `wopi_tokens` table: `SELECT * FROM wopi_tokens ORDER BY created_at DESC LIMIT 5;`
- Token may be expired (24h TTL) — request a new one via the frontend
- Ensure `aliasgroup1=http://api:8000` (not `https://`)

### "Collabora is not running" fallback shows (but it IS running)
- `NEXT_PUBLIC_COLLABORA_ENABLED` might be `false` in `.env.local`
- Health check hits `/hosting/capabilities` — Collabora may still be booting (30–60s)
- Click "Retry" in the fallback UI after Collabora finishes starting

### File not loading in Collabora
- Check MinIO: does the object exist at `office/{org_id}/{doc_id}.{ext}`?
- Check `office_documents` table: `storage_key` must match the MinIO key
- Run `docker compose logs api --tail 30` during a WOPI GetFile request

---

## Document Operations via Amin

Amin does NOT edit documents via WOPI. Amin uses:

```
POST /api/v1/office/documents/{id}/amin-edit
Body: { "instruction": "Add a conclusion section" }
```

This downloads bytes from MinIO → GPT-4o plans ops → python-docx/pptx/openpyxl applies → re-uploads.

After Amin finishes, the backend sends a `collabora_reload` WebSocket event:
- Frontend listens on `ws.onmessage` for `type: "collabora_reload"`
- Dispatches `window.dispatchEvent(new CustomEvent('collabora-reload', { detail: { docId } }))`
- `CollaboraEditor` listens for this event and calls `loadEditor()` to refresh the iframe

---

## Local Development Without Collabora

Set in `apps/web/.env.local`:
```env
NEXT_PUBLIC_COLLABORA_ENABLED=false
```

`CollaboraEditor` immediately shows the fallback UI:
- "Document Editor Unavailable" card
- **Download Template** button → calls `GET /api/v1/office/documents/{id}/download`
- **Ask Amin** shortcut → pre-fills Amin panel with draft request

All Amin document operations (create, edit, read, navigate) still work without Collabora.

---

## Environment Variables Reference

### Backend (`docker-compose.yml` → `api` service)

| Variable | Default (Docker) | Description |
|---|---|---|
| `COLLABORA_URL` | `http://localhost:9980` | Browser-accessible Collabora URL |
| `WOPI_INTERNAL_URL` | `http://api:8000/api/v1/wopi` | Collabora→API internal URL |
| `WOPI_PUBLIC_URL` | `http://localhost:8000/api/v1/wopi` | Public API URL (display) |

### Collabora service

| Variable | Value | Description |
|---|---|---|
| `aliasgroup1` | `http://api:8000` | Allowed WOPI host whitelist |
| `extra_params` | `--o:ssl.enable=false ...` | Disable SSL (local dev) |

### Frontend (`apps/web/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_COLLABORA_URL` | `http://localhost:9980` | Browser→Collabora URL |
| `NEXT_PUBLIC_COLLABORA_ENABLED` | `true` | Set `false` to skip Collabora |
