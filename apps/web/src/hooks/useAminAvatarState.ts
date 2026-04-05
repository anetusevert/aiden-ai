import { useEffect, useRef, useState } from 'react';
import { useAminContext } from '@/components/amin/AminProvider';
import type { AminAvatarState } from '@/components/amin/AminAvatar';

const SLEEP_TIMEOUT_MS = 90_000; // 90 seconds

const STATUS_MAP: Record<string, AminAvatarState> = {
  idle: 'idle',
  thinking: 'thinking',
  streaming: 'speaking',
  speaking: 'speaking',
  listening: 'listening',
  success: 'success',
  error: 'idle',
};

export function useAminAvatarState(): AminAvatarState {
  const { aminStatus } = useAminContext();
  const [isSleeping, setIsSleeping] = useState(false);
  const sleepTimer = useRef<ReturnType<typeof setTimeout>>();

  // Manage sleep timer based on Amin's active status
  useEffect(() => {
    // Any non-idle state wakes Amin immediately
    if (aminStatus !== 'idle') {
      setIsSleeping(false);
      clearTimeout(sleepTimer.current);
      return;
    }

    // Idle: start the sleep countdown
    sleepTimer.current = setTimeout(() => {
      setIsSleeping(true);
    }, SLEEP_TIMEOUT_MS);

    return () => clearTimeout(sleepTimer.current);
  }, [aminStatus]);

  // Reset sleep timer whenever the user sends a message
  useEffect(() => {
    const handleUserMessage = () => {
      setIsSleeping(false);
      clearTimeout(sleepTimer.current);
      // Only restart the sleep timer if currently idle
      sleepTimer.current = setTimeout(() => setIsSleeping(true), SLEEP_TIMEOUT_MS);
    };

    window.addEventListener('amin-user-message', handleUserMessage);
    return () => window.removeEventListener('amin-user-message', handleUserMessage);
  }, []);

  if (isSleeping && aminStatus === 'idle') return 'sleeping';

  return STATUS_MAP[aminStatus] ?? 'idle';
}
