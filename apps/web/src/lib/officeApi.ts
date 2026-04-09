'use client';

import { resolveApiUrl } from '@/lib/api';

export type OfficeDocType = 'docx' | 'xlsx' | 'pptx';

export interface OfficeDocument {
  id: string;
  org_id: string;
  owner_id: string;
  title: string;
  doc_type: OfficeDocType;
  storage_key: string;
  size_bytes: number;
  last_modified_by: string | null;
  created_at: string;
  updated_at: string;
  metadata_: Record<string, unknown>;
  wopi_url: string;
  collabora_url: string;
}

export interface OfficeDocumentListResponse {
  items: OfficeDocument[];
  total: number;
  limit: number;
  offset: number;
}

export interface OfficeDocumentCountResponse {
  count: number;
}

export interface WopiTokenResponse {
  token: string;
  collabora_editor_url: string;
  expires_at: string;
}

export interface OfficeDocumentEditResponse {
  success: boolean;
  ops_applied: Array<Record<string, unknown>>;
  summary: string;
}

function extractErrorMessage(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail;
    if (typeof detail === 'string') return detail;
    if (
      typeof detail === 'object' &&
      detail !== null &&
      typeof detail.message === 'string'
    ) {
      return detail.message;
    }
  } catch {
    // not JSON — use as-is if short, otherwise generic
  }
  if (body && body.length < 200 && !body.startsWith('{')) return body;
  return `Request failed (${status})`;
}

async function officeFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const opts: RequestInit = {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  };

  const url = resolveApiUrl(path, 'client');
  let response = await fetch(url, opts);

  // On 401, try a silent token refresh and retry once
  if (response.status === 401) {
    try {
      const refreshRes = await fetch(resolveApiUrl('/auth/refresh', 'client'), {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshRes.ok) {
        response = await fetch(url, opts);
      }
    } catch {
      // refresh failed — fall through to error handling
    }
  }

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(extractErrorMessage(response.status, text));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const officeApi = {
  listDocuments(params?: {
    doc_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) {
    const query = new URLSearchParams();
    if (params?.doc_type) query.set('doc_type', params.doc_type);
    if (params?.search) query.set('search', params.search);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return officeFetch<OfficeDocumentListResponse>(
      `/api/v1/office/documents${suffix}`
    );
  },

  countDocuments() {
    return officeFetch<OfficeDocumentCountResponse>(
      '/api/v1/office/documents?count_only=true'
    );
  },

  getDocument(docId: string) {
    return officeFetch<OfficeDocument>(`/api/v1/office/documents/${docId}`);
  },

  createDocument(payload: {
    title: string;
    doc_type: OfficeDocType;
    template?: string;
  }) {
    return officeFetch<OfficeDocument>('/api/v1/office/documents', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateDocument(docId: string, payload: { title: string }) {
    return officeFetch<OfficeDocument>(`/api/v1/office/documents/${docId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteDocument(docId: string) {
    return officeFetch<void>(`/api/v1/office/documents/${docId}`, {
      method: 'DELETE',
    });
  },

  generateWopiToken(docId: string) {
    return officeFetch<WopiTokenResponse>(
      `/api/v1/office/documents/${docId}/wopi-token`,
      {
        method: 'POST',
      }
    );
  },

  aminEdit(docId: string, instruction: string) {
    return officeFetch<OfficeDocumentEditResponse>(
      `/api/v1/office/documents/${docId}/amin-edit`,
      {
        method: 'POST',
        body: JSON.stringify({ instruction }),
      }
    );
  },

  getDownloadUrl(docId: string) {
    return resolveApiUrl(
      `/api/v1/office/documents/${docId}/download`,
      'client'
    );
  },
};
