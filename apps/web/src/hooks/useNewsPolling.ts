'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  apiClient,
  type LegalNewsItem,
  type LegalNewsQuery,
} from '@/lib/apiClient';

const POLL_INTERVAL_MS = 20 * 60 * 1000; // 20 minutes

export interface UseNewsPollingResult {
  items: LegalNewsItem[];
  total: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  loadMore: () => Promise<void>;
  breakingItems: LegalNewsItem[];
}

export function useNewsPolling(query?: LegalNewsQuery): UseNewsPollingResult {
  const [items, setItems] = useState<LegalNewsItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [breakingItems, setBreakingItems] = useState<LegalNewsItem[]>([]);
  const offsetRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const queryRef = useRef(query);
  queryRef.current = query;

  const fetchNews = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const q = queryRef.current;
      const response = await apiClient.getLegalNews({
        category: q?.category,
        jurisdiction: q?.jurisdiction,
        importance: q?.importance,
        limit: q?.limit ?? 40,
        offset: 0,
      });
      setItems(response.items);
      setTotal(response.total);
      offsetRef.current = response.items.length;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch news');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    const q = queryRef.current;
    try {
      const response = await apiClient.getLegalNews({
        category: q?.category,
        jurisdiction: q?.jurisdiction,
        importance: q?.importance,
        limit: 20,
        offset: offsetRef.current,
      });
      setItems(prev => [...prev, ...response.items]);
      setTotal(response.total);
      offsetRef.current += response.items.length;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load more');
    }
  }, []);

  const fetchBreaking = useCallback(async () => {
    try {
      const resp = await apiClient.getBreakingNews();
      setBreakingItems(resp.items);
    } catch {
      // non-critical
    }
  }, []);

  // Re-fetch when query params change
  useEffect(() => {
    fetchNews();
    fetchBreaking();
  }, [
    query?.category,
    query?.jurisdiction,
    query?.importance,
    fetchNews,
    fetchBreaking,
  ]);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      fetchNews();
      fetchBreaking();
    }, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchNews, fetchBreaking]);

  return {
    items,
    total,
    isLoading,
    error,
    refresh: fetchNews,
    loadMore,
    breakingItems,
  };
}
