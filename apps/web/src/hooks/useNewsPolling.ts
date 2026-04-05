'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, type LegalNewsItem } from '@/lib/apiClient';

const POLL_INTERVAL_MS = 20 * 60 * 1000; // 20 minutes

export interface UseNewsPollingResult {
  items: LegalNewsItem[];
  isLoading: boolean;
  error: string | null;
  fetchedAt: string | null;
  refresh: () => Promise<void>;
}

export function useNewsPolling(): UseNewsPollingResult {
  const [items, setItems] = useState<LegalNewsItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNews = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getLegalNews();
      setItems(response.items);
      setFetchedAt(response.fetched_at);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();

    intervalRef.current = setInterval(fetchNews, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchNews]);

  return { items, isLoading, error, fetchedAt, refresh: fetchNews };
}
