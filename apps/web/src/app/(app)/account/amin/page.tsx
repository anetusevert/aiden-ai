'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { getApiBaseUrl } from '@/lib/api';
import { setVoice } from '@/lib/aminVoiceClient';
import { motion } from 'framer-motion';
import { glassReveal, staggerContainer, staggerItem } from '@/lib/motion';
import { AminAvatar, type AminAvatarState } from '@/components/amin/AminAvatar';
import { connectAminAudioSource, disconnectAminAudio } from '@/lib/aminAudio';

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

type VoiceId = 'onyx' | 'echo' | 'fable';

interface VoiceOption {
  id: VoiceId;
  name: string;
  detail: string;
}

const VOICES: VoiceOption[] = [
  {
    id: 'onyx',
    name: 'Onyx',
    detail:
      'Deep & authoritative \u2014 commanding presence, ideal for formal legal contexts.',
  },
  {
    id: 'echo',
    name: 'Echo',
    detail:
      'Clear & balanced \u2014 professional tone, natural for everyday legal work.',
  },
  {
    id: 'fable',
    name: 'Fable',
    detail:
      'Warm & engaging \u2014 conversational delivery, great for explanations and summaries.',
  },
];

interface LanguageOption {
  code: string;
  flag: string;
  label: string;
}

const LANGUAGES: LanguageOption[] = [
  { code: 'en', flag: '\u{1F1EC}\u{1F1E7}', label: 'English' },
  {
    code: 'ar',
    flag: '\u{1F1F8}\u{1F1E6}',
    label: '\u0627\u0644\u0639\u0631\u0628\u064A\u0629',
  },
  { code: 'fr', flag: '\u{1F1EB}\u{1F1F7}', label: 'Fran\u00E7ais' },
  { code: 'ur', flag: '\u{1F1F5}\u{1F1F0}', label: '\u0627\u0631\u062F\u0648' },
  { code: 'tl', flag: '\u{1F1F5}\u{1F1ED}', label: 'Filipino' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MyAminPage() {
  const router = useRouter();
  const {
    isAuthenticated,
    isLoading: authLoading,
    setAminPreferences,
  } = useAuth();

  const [selectedVoice, setSelectedVoice] = useState<VoiceId>('onyx');
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Voice preview state
  const [previewingVoice, setPreviewingVoice] = useState<VoiceId | null>(null);
  const [previewPlaying, setPreviewPlaying] = useState<VoiceId | null>(null);
  const [previewError, setPreviewError] = useState<VoiceId | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  // ---- Data loading ----

  const loadPreferences = useCallback(async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/twin/me`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedVoice(data.amin_voice || 'onyx');
        setSelectedLanguage(data.app_language || 'en');
      }
    } catch {
      // fall back to defaults
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (isAuthenticated) {
      loadPreferences();
    }
  }, [authLoading, isAuthenticated, router, loadPreferences]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  // ---- Save ----

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/twin/me`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amin_voice: selectedVoice,
          app_language: selectedLanguage,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(
          typeof err?.detail === 'string'
            ? err.detail
            : `Save failed (${res.status})`
        );
      }
      setVoice(selectedVoice);
      setAminPreferences(selectedVoice, selectedLanguage);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  // ---- Voice preview ----

  const stopCurrentPreview = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
    setPreviewPlaying(null);
    setPreviewingVoice(null);
  }, []);

  const handlePreview = useCallback(
    async (voiceId: VoiceId) => {
      stopCurrentPreview();
      setPreviewError(null);
      setPreviewingVoice(voiceId);

      try {
        const baseUrl = getApiBaseUrl();
        const res = await fetch(`${baseUrl}/twin/voice-preview`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            Accept: 'audio/mpeg',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ voice: voiceId }),
        });

        if (!res.ok) throw new Error('Preview request failed');

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        objectUrlRef.current = url;

        const audio = new Audio(url);
        audioRef.current = audio;

        audio.addEventListener('playing', () => {
          setPreviewingVoice(null);
          setPreviewPlaying(voiceId);
          try {
            connectAminAudioSource(audio);
          } catch {
            /* audio context may fail in some browsers */
          }
        });

        audio.addEventListener('ended', () => {
          disconnectAminAudio();
          stopCurrentPreview();
        });

        audio.addEventListener('error', () => {
          disconnectAminAudio();
          stopCurrentPreview();
          setPreviewError(voiceId);
          setTimeout(() => setPreviewError(null), 3000);
        });

        await audio.play();
      } catch {
        setPreviewingVoice(null);
        setPreviewError(voiceId);
        setTimeout(() => setPreviewError(null), 3000);
      }
    },
    [stopCurrentPreview]
  );

  // ---- Render ----

  if (authLoading || loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) return null;

  return (
    <motion.div
      {...glassReveal}
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <div
        className="page-header"
        style={{
          paddingBottom: 'var(--space-3)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-4)',
        }}
      >
        <AminAvatar
          size={96}
          state={previewPlaying ? 'speaking' : 'idle'}
          showWaveform
        />
        <div>
          <h1 className="page-title">My Amin</h1>
          <p className="page-subtitle">
            Personalise how Amin sounds and speaks with you.
          </p>
        </div>
      </div>

      {/* Two-column grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'var(--space-4)',
          flex: 1,
          minHeight: 0,
        }}
      >
        {/* Left column — Voice */}
        <div
          className="card"
          style={{ display: 'flex', flexDirection: 'column' }}
        >
          <div
            className="card-header"
            style={{ paddingBottom: 'var(--space-2)' }}
          >
            <h3 className="card-title">Voice</h3>
            <p
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-muted)',
                margin: 0,
              }}
            >
              Choose Amin&apos;s voice. All voices are professionally selected
              for clarity.
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
              padding: '0 var(--space-5) var(--space-5)',
            }}
          >
            {VOICES.map(voice => {
              const isSelected = selectedVoice === voice.id;
              const isPreviewing = previewingVoice === voice.id;
              const isPlaying = previewPlaying === voice.id;
              const hasError = previewError === voice.id;

              return (
                <motion.button
                  key={voice.id}
                  variants={staggerItem}
                  type="button"
                  onClick={() => setSelectedVoice(voice.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    background: 'var(--bg-elevated)',
                    border: 'none',
                    borderLeft: isSelected
                      ? '3px solid #d4a017'
                      : '3px solid transparent',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px 16px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                    width: '100%',
                    backgroundColor: isSelected
                      ? 'rgba(212,160,23,0.08)'
                      : 'var(--bg-elevated)',
                  }}
                >
                  {/* Radio dot */}
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      border: isSelected
                        ? '5px solid #d4a017'
                        : '2px solid var(--text-muted)',
                      flexShrink: 0,
                      transition: 'border 0.15s ease',
                    }}
                  />

                  {/* Name + description */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span
                      style={{
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        fontSize: 'var(--text-sm)',
                      }}
                    >
                      {voice.name}
                    </span>
                    <span
                      style={{
                        color: 'var(--text-muted)',
                        fontSize: 'var(--text-xs)',
                        marginLeft: 'var(--space-2)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {voice.detail}
                    </span>
                  </div>

                  {/* Preview button */}
                  <button
                    type="button"
                    onClick={e => {
                      e.stopPropagation();
                      if (isPlaying) {
                        stopCurrentPreview();
                      } else {
                        handlePreview(voice.id);
                      }
                    }}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      height: 28,
                      padding: '0 10px',
                      fontSize: 'var(--text-xs)',
                      background: 'transparent',
                      border: '1px solid var(--glass-border)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      color: hasError
                        ? 'var(--error)'
                        : isPlaying
                          ? '#d4a017'
                          : 'var(--text-secondary)',
                      flexShrink: 0,
                      transition: 'border-color 0.15s ease, color 0.15s ease',
                      animation: isPlaying
                        ? 'aminPulse 1.5s ease-in-out infinite'
                        : 'none',
                    }}
                    disabled={isPreviewing}
                  >
                    {isPreviewing && <Spinner />}
                    {isPlaying && '\u25FC Playing'}
                    {hasError && 'Preview unavailable'}
                    {!isPreviewing &&
                      !isPlaying &&
                      !hasError &&
                      '\u25B6 Preview'}
                  </button>
                </motion.button>
              );
            })}
          </motion.div>
        </div>

        {/* Right column — Language */}
        <div
          className="card"
          style={{ display: 'flex', flexDirection: 'column' }}
        >
          <div
            className="card-header"
            style={{ paddingBottom: 'var(--space-2)' }}
          >
            <h3 className="card-title">Language</h3>
            <p
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-muted)',
                margin: 0,
              }}
            >
              Amin and the entire application will switch to your chosen
              language.
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-2)',
              padding: '0 var(--space-5) var(--space-5)',
            }}
          >
            {LANGUAGES.map(lang => {
              const isSelected = selectedLanguage === lang.code;
              return (
                <motion.button
                  key={lang.code}
                  variants={staggerItem}
                  type="button"
                  onClick={() => setSelectedLanguage(lang.code)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    background: isSelected
                      ? 'rgba(212,160,23,0.08)'
                      : 'var(--bg-elevated)',
                    border: 'none',
                    borderLeft: isSelected
                      ? '3px solid #d4a017'
                      : '3px solid transparent',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 16px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease',
                    width: '100%',
                  }}
                >
                  {/* Radio dot */}
                  <div
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      border: isSelected
                        ? '5px solid #d4a017'
                        : '2px solid var(--text-muted)',
                      flexShrink: 0,
                      transition: 'border 0.15s ease',
                    }}
                  />
                  {/* Flag */}
                  <span
                    style={{
                      fontSize: '1.4em',
                      lineHeight: 1,
                      flexShrink: 0,
                    }}
                  >
                    {lang.flag}
                  </span>
                  {/* Label */}
                  <span
                    style={{
                      color: 'var(--text-primary)',
                      fontSize: 'var(--text-sm)',
                      fontWeight: isSelected ? 600 : 400,
                    }}
                  >
                    {lang.label}
                  </span>
                </motion.button>
              );
            })}
          </motion.div>
        </div>
      </div>

      {/* Save bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
          paddingTop: 'var(--space-4)',
        }}
      >
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving\u2026' : 'Save Preferences'}
        </button>
        {success && (
          <span style={{ color: 'var(--success)', fontSize: 'var(--text-sm)' }}>
            Preferences saved
          </span>
        )}
        {error && (
          <span style={{ color: 'var(--error)', fontSize: 'var(--text-sm)' }}>
            {error}
          </span>
        )}
      </div>

      {/* Keyframe for the playing pulse */}
      <style>{`
        @keyframes aminPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @media (max-width: 767px) {
          /* Stack columns on mobile */
          .amin-grid-override { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Tiny inline spinner for preview loading state
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: 12,
        height: 12,
        border: '2px solid var(--text-muted)',
        borderTopColor: 'transparent',
        borderRadius: '50%',
        animation: 'aminSpin 0.6s linear infinite',
      }}
    >
      <style>{`@keyframes aminSpin { to { transform: rotate(360deg); } }`}</style>
    </span>
  );
}
