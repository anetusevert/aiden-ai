'use client';

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react';
import {
  apiClient,
  CurrentUserResponse,
  WorkspaceContext,
  clearSession,
  setStoredTenantId,
  setStoredWorkspaceId,
  getStoredWorkspaceContext,
  getDefaultOutputLanguage,
} from './apiClient';
import { getApiBaseUrl } from './api';
import { normalizeLanguage, setVoice, setLanguage } from './aminVoiceClient';

const SUPPORTED_VOICES = new Set(['onyx', 'echo', 'fable']);

function normalizeVoice(voice: string | null | undefined): string {
  return voice && SUPPORTED_VOICES.has(voice) ? voice : 'onyx';
}

interface AuthContextType {
  user: CurrentUserResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /**
   * Complete login after successful /auth/dev-login.
   * Cookies are already set by the server.
   * This just triggers a user refresh.
   */
  login: () => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshUser: () => Promise<void>;
  canEdit: boolean;
  /** Workspace context with language defaults */
  workspaceContext: WorkspaceContext | null;
  /** Default output language derived from workspace context */
  defaultOutputLanguage: 'en' | 'ar';
  /** Auth mode - always 'cookie' now */
  authMode: 'cookie';
  /** Amin voice preference */
  aminVoice: string;
  /** App language preference */
  appLanguage: string;
  /** Update amin preferences in context (called by My Amin page) */
  setAminPreferences: (voice: string, language: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [workspaceContext, setWorkspaceContext] =
    useState<WorkspaceContext | null>(null);
  const [aminVoice, setAminVoice] = useState('onyx');
  const [appLanguage, setAppLanguage] = useState('en');

  const setAminPreferences = useCallback((voice: string, language: string) => {
    const normalizedVoice = normalizeVoice(voice);
    const normalizedLanguage = normalizeLanguage(language);
    setAminVoice(normalizedVoice);
    setAppLanguage(normalizedLanguage);
    setVoice(normalizedVoice);
    setLanguage(normalizedLanguage);
  }, []);

  const loadTwinPreferences = useCallback(async () => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 12_000);
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/twin/me`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      if (res.ok) {
        const data = await res.json();
        const voice = normalizeVoice(data.amin_voice);
        const lang = normalizeLanguage(data.app_language);
        setAminVoice(voice);
        setAppLanguage(lang);
        setVoice(voice);
        setLanguage(lang);
      }
    } catch {
      // Non-critical — keep defaults
    } finally {
      window.clearTimeout(timeoutId);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await apiClient.getMe();
      setUser(userData);
      // Store tenant/workspace for convenience
      setStoredTenantId(userData.tenant_id);
      setStoredWorkspaceId(userData.workspace_id);
      // Load workspace context from storage
      setWorkspaceContext(getStoredWorkspaceContext());
      // Twin prefs must NOT block shell render — if /twin/me hangs, the app would
      // stay on the loading screen forever while isLoading stays true.
      void loadTwinPreferences();
    } catch {
      setUser(null);
      // Don't clear session here - let the apiClient handle redirects
    } finally {
      setIsLoading(false);
    }
  }, [loadTwinPreferences]);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Last resort: if anything in the auth chain never settles, never leave the shell stuck.
  useEffect(() => {
    const safety = window.setTimeout(() => {
      setIsLoading(false);
    }, 28_000);
    return () => window.clearTimeout(safety);
  }, []);

  const login = useCallback(async () => {
    // Cookies are already set by /auth/dev-login
    // Just refresh the user data
    await refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try {
      await apiClient.logout();
    } catch {
      // Ignore errors - we're logging out anyway
    }
    setUser(null);
    clearSession();
    window.location.href = '/login';
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      await apiClient.logoutAll();
    } catch {
      // Ignore errors
    }
    setUser(null);
    clearSession();
    window.location.href = '/login?reason=session_expired';
  }, []);

  const canEdit = user?.role === 'ADMIN' || user?.role === 'EDITOR';
  const defaultOutputLanguage = getDefaultOutputLanguage();

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        logoutAll,
        refreshUser,
        canEdit,
        workspaceContext,
        defaultOutputLanguage,
        authMode: 'cookie',
        aminVoice,
        appLanguage,
        setAminPreferences,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
