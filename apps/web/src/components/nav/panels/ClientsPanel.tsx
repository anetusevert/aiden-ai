'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';

interface ClientItem {
  id: string;
  display_name: string;
  client_type: string;
  case_count: number;
}

const TYPE_COLORS: Record<string, string> = {
  individual: 'rgba(255, 255, 255, 0.7)',
  company: 'rgba(255, 255, 255, 0.8)',
  organisation: 'rgba(255, 255, 255, 0.6)',
};

function TypeIcon({ type }: { type: string }) {
  const color = TYPE_COLORS[type] ?? '#94a3b8';
  if (type === 'company') {
    return (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
      >
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      </svg>
    );
  }
  if (type === 'organisation') {
    return (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="1.5"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    );
  }
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="1.5"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export function ClientsPanel() {
  const { navigateTo } = useNavigation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.get('search') ?? '';
  const typeFilter = searchParams.get('client_type') ?? '';
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [loading, setLoading] = useState(true);

  const setClientType = useCallback(
    (t: string) => {
      const sp = new URLSearchParams(searchParams.toString());
      if (t) sp.set('client_type', t);
      else sp.delete('client_type');
      const q = sp.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (typeFilter) params.set('client_type', typeFilter);
      params.set('limit', '20');
      const res = await fetch(`/api/v1/clients?${params}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setClients(data.items ?? []);
      }
    } catch {
      /* */
    }
    setLoading(false);
  }, [search, typeFilter]);

  useEffect(() => {
    const timer = setTimeout(fetchClients, 300);
    return () => clearTimeout(timer);
  }, [fetchClients]);

  const types = ['', 'individual', 'company', 'organisation'];
  const typeLabels: Record<string, string> = {
    '': 'All',
    individual: 'Individual',
    company: 'Company',
    organisation: 'Organisation',
  };

  return (
    <div className="r2-panel-stack">
      <div className="r2-header">CLIENTS</div>

      <div className="r2-filter-chips r2-filter-chips-grid">
        {types.map(t => (
          <button
            key={t || 'all'}
            type="button"
            className={`r2-chip${typeFilter === t ? ' r2-chip-active' : ''}`}
            onClick={() => setClientType(t)}
          >
            {typeLabels[t]}
          </button>
        ))}
      </div>

      <div className="r2-link-list r2-scrollable">
        {loading &&
          [...Array(4)].map((_, i) => (
            <div
              key={i}
              className="skeleton-row"
              style={{ padding: '8px 16px', animationDelay: `${i * 60}ms` }}
            >
              <div className="skeleton-group">
                <div
                  className="skeleton-line"
                  style={{ width: `${65 - i * 10}%` }}
                />
                <div
                  className="skeleton-line skeleton-line-sm"
                  style={{ width: '25%' }}
                />
              </div>
            </div>
          ))}
        {!loading && clients.length === 0 && (
          <div className="r2-empty">No clients found</div>
        )}
        {clients.map(client => (
          <Link
            key={client.id}
            href={`/clients/${client.id}`}
            className="r2-link r2-link-stacked"
            onClick={e => {
              e.preventDefault();
              navigateTo(`/clients/${client.id}`);
            }}
          >
            <span className="r2-link-icon">
              <TypeIcon type={client.client_type} />
            </span>
            <span className="r2-link-text">{client.display_name}</span>
            {client.case_count > 0 && (
              <span className="r2-count-badge">{client.case_count} cases</span>
            )}
          </Link>
        ))}
      </div>

      <div className="r2-panel-footer">
        <button
          type="button"
          className="r2-action-btn"
          onClick={() => navigateTo('/clients?new=true')}
        >
          + New Client
        </button>
      </div>
    </div>
  );
}
