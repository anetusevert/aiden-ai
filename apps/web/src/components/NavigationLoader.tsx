'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import { getRouteContext, type RouteContext } from '@/lib/routeContext';
import { navigationLoader } from '@/lib/motion';

interface NavigationState {
  isNavigating: boolean;
  routeContext: RouteContext | null;
  targetPath: string | null;
  startedAt: number;
}

interface NavigationContextValue {
  navigateTo: (href: string) => void;
  isNavigating: boolean;
}

const NavigationContext = createContext<NavigationContextValue>({
  navigateTo: () => {},
  isNavigating: false,
});

/** Next.js pathname and router href can differ by trailing slash — compare normalized. */
function normalizePath(p: string | null): string {
  if (!p) return '';
  const noQuery = p.split('?')[0];
  if (noQuery.length > 1 && noQuery.endsWith('/')) {
    return noQuery.slice(0, -1);
  }
  return noQuery;
}

const NAV_OVERLAY_MAX_MS = 12_000;

export function useNavigation() {
  return useContext(NavigationContext);
}

export function NavigationLoaderProvider({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<NavigationState>({
    isNavigating: false,
    routeContext: null,
    targetPath: null,
    startedAt: 0,
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const exitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelInflight = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (exitTimerRef.current) {
      clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }
  }, []);

  const navigateTo = useCallback(
    (href: string) => {
      cancelInflight();

      const targetPath = href.split('?')[0];
      const routeContext = getRouteContext(href);
      const startedAt = Date.now();
      setState({ isNavigating: true, routeContext, targetPath, startedAt });

      timerRef.current = setTimeout(() => {
        router.push(href);
      }, 120);
    },
    [router, cancelInflight]
  );

  useEffect(() => {
    if (!state.isNavigating || !state.targetPath) return;
    if (normalizePath(pathname) !== normalizePath(state.targetPath)) return;

    const elapsed = Date.now() - state.startedAt;
    const remaining = Math.max(0, 650 - elapsed);

    exitTimerRef.current = setTimeout(() => {
      setState({
        isNavigating: false,
        routeContext: null,
        targetPath: null,
        startedAt: 0,
      });
    }, remaining);

    return () => {
      if (exitTimerRef.current) {
        clearTimeout(exitTimerRef.current);
        exitTimerRef.current = null;
      }
    };
  }, [pathname, state.isNavigating, state.targetPath, state.startedAt]);

  // If navigation never completes (path mismatch, router stall), clear overlay.
  useEffect(() => {
    if (!state.isNavigating || !state.targetPath) return;
    const t = setTimeout(() => {
      setState({
        isNavigating: false,
        routeContext: null,
        targetPath: null,
        startedAt: 0,
      });
    }, NAV_OVERLAY_MAX_MS);
    return () => clearTimeout(t);
  }, [state.isNavigating, state.targetPath, state.startedAt]);

  return (
    <NavigationContext.Provider
      value={{ navigateTo, isNavigating: state.isNavigating }}
    >
      {children}
      <NavigationOverlay
        isNavigating={state.isNavigating}
        routeContext={state.routeContext}
      />
    </NavigationContext.Provider>
  );
}

function NavigationOverlay({
  isNavigating,
  routeContext,
}: {
  isNavigating: boolean;
  routeContext: RouteContext | null;
}) {
  return (
    <AnimatePresence>
      {isNavigating && (
        <motion.div
          className="nav-loader-overlay"
          key="nav-loader"
          {...navigationLoader.overlay}
        >
          <div className="nav-loader-content">
            <motion.div
              className="nav-loader-mark"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
              style={{ marginBottom: 12 }}
            >
              <HeyAminLogo variant="mark" size={40} />
            </motion.div>
            <div className="nav-loader-avatar">
              <AminAvatar size={72} state="thinking" showWaveform={false} />
            </div>
            <span className="nav-loader-label">
              {routeContext?.label || 'Loading'}
            </span>
            <motion.p
              className="nav-loader-message"
              {...navigationLoader.message}
            >
              {routeContext?.headline || 'Preparing workspace'}
            </motion.p>
            <p className="nav-loader-detail">
              {routeContext?.detail ||
                'Amin is restoring the next view and your active context.'}
            </p>
            <div className="nav-loader-progress-track">
              <motion.div
                className="nav-loader-progress-bar"
                {...navigationLoader.progress}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
