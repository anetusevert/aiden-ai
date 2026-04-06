'use client';

import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

export type AvatarState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'error'
  | 'sleeping';

export type AvatarSize = 'micro' | 'small' | 'medium' | 'full' | 'hero' | 'fab';

interface AminAvatarV2Props {
  size?: AvatarSize;
  state?: AvatarState;
  className?: string;
  showRing?: boolean;
}

const sizeMap: Record<AvatarSize, number> = {
  micro: 28,
  small: 40,
  medium: 64,
  full: 110,
  hero: 160,
  fab: 52,
};

const ringMap: Record<AvatarSize, number> = {
  micro: 36,
  small: 50,
  medium: 80,
  full: 132,
  hero: 196,
  fab: 64,
};

const EXTRAS_SIZES = new Set<AvatarSize>(['medium', 'full', 'hero']);

function isActive(s: AvatarState) {
  return s === 'speaking' || s === 'thinking' || s === 'listening';
}

function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

/* ── Glow palette (white spectrum) ── */
const GLOW: Record<
  AvatarState,
  { primary: string; ring: string; mid: string }
> = {
  sleeping: {
    primary: 'rgba(255,255,255,0.12)',
    ring: 'rgba(255,255,255,0.08)',
    mid: 'rgba(255,255,255,0.04)',
  },
  idle: {
    primary: 'rgba(255,255,255,0.22)',
    ring: 'rgba(255,255,255,0.25)',
    mid: 'rgba(255,255,255,0.06)',
  },
  speaking: {
    primary: 'rgba(255,255,255,0.55)',
    ring: 'rgba(255,255,255,0.45)',
    mid: 'rgba(255,255,255,0.14)',
  },
  listening: {
    primary: 'rgba(255,255,255,0.42)',
    ring: 'rgba(255,255,255,0.35)',
    mid: 'rgba(255,255,255,0.12)',
  },
  thinking: {
    primary: 'rgba(255,255,255,0.45)',
    ring: 'rgba(255,255,255,0.35)',
    mid: 'rgba(255,255,255,0.10)',
  },
  error: {
    primary: 'rgba(248,113,113,0.45)',
    ring: 'rgba(248,113,113,0.35)',
    mid: 'rgba(248,113,113,0.12)',
  },
};

/* ── Particle system ── */
function AvatarParticles({
  state,
  ringPx,
}: {
  state: AvatarState;
  ringPx: number;
}) {
  const r = ringPx / 2;
  const g = GLOW[state] ?? GLOW.idle;

  if (state === 'sleeping') {
    return (
      <>
        {[0, 1, 2].map(i => (
          <motion.span
            key={`z${i}`}
            style={{
              position: 'absolute',
              top: r * 0.15 - i * r * 0.14,
              right: r * 0.05 + i * r * 0.12,
              fontSize: Math.max(8, r * 0.13 + i * 2),
              color: 'rgba(180,170,230,0.6)',
              fontWeight: 800,
              fontFamily: 'system-ui',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{
              y: [0, -r * 0.18, -r * 0.36],
              opacity: [0.7, 0.35, 0],
              scale: [0.8, 1, 0.7],
              rotate: [-5, 5, 12],
            }}
            transition={{
              duration: 2.5,
              repeat: Infinity,
              delay: i * 0.7,
              ease: 'easeOut',
            }}
          >
            Z
          </motion.span>
        ))}
      </>
    );
  }

  const count =
    state === 'speaking'
      ? 7
      : state === 'listening'
        ? 5
        : state === 'thinking'
          ? 6
          : 4;

  return (
    <>
      {Array.from({ length: count }).map((_, i) => {
        const angle = (i / count) * Math.PI * 2;
        const dist = r + r * 0.22;
        const x = Math.cos(angle) * dist;
        const y = Math.sin(angle) * dist;
        const sz = Math.max(2, r * 0.04);

        const anim =
          state === 'speaking'
            ? {
                x: [x, x * 1.18, x],
                y: [y, y * 1.18, y],
                opacity: [0.25, 0.75, 0.25],
                scale: [0.8, 1.4, 0.8],
              }
            : state === 'listening'
              ? {
                  x: [x * 1.2, x * 0.75, x * 1.2],
                  y: [y * 1.2, y * 0.75, y * 1.2],
                  opacity: [0.2, 0.6, 0.2],
                }
              : state === 'thinking'
                ? {
                    x: [
                      Math.cos(angle) * dist,
                      Math.cos(angle + 0.8) * dist,
                      Math.cos(angle + 1.6) * dist,
                      Math.cos(angle) * dist,
                    ],
                    y: [
                      Math.sin(angle) * dist,
                      Math.sin(angle + 0.8) * dist,
                      Math.sin(angle + 1.6) * dist,
                      Math.sin(angle) * dist,
                    ],
                    opacity: [0.25, 0.5, 0.25],
                  }
                : {
                    x: [x, x + r * 0.06, x],
                    y: [y, y + r * 0.06, y],
                    opacity: [0.12, 0.35, 0.12],
                  };

        const dur =
          state === 'speaking'
            ? 0.5
            : state === 'thinking'
              ? 5
              : state === 'listening'
                ? 2.2
                : 4;

        return (
          <motion.div
            key={`p${i}`}
            style={{
              position: 'absolute',
              width: sz,
              height: sz,
              borderRadius: '50%',
              background: g.primary,
              top: '50%',
              left: '50%',
              marginTop: -sz / 2,
              marginLeft: -sz / 2,
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={anim}
            transition={{
              duration: dur,
              repeat: Infinity,
              delay: i * 0.12,
              ease: 'easeInOut',
            }}
          />
        );
      })}
    </>
  );
}

export function AminAvatarV2({
  size = 'medium',
  state = 'idle',
  className,
  showRing = true,
}: AminAvatarV2Props) {
  const px = sizeMap[size];
  const ringPx = ringMap[size];
  const active = isActive(state);
  const prevState = usePrevious(state);
  const showExtras = EXTRAS_SIZES.has(size);

  const blinkCtrl = useAnimation();
  const blinkTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saccadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const glintTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wakeTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const mountedRef = useRef(true);
  useEffect(
    () => () => {
      mountedRef.current = false;
    },
    []
  );

  const [wakePhase, setWakePhase] = useState<0 | 1 | 2 | 3>(0);
  const [saccadeOff, setSaccadeOff] = useState({ dx: 0, dy: 0 });
  const [showGlint, setShowGlint] = useState(false);

  const glow = GLOW[state] ?? GLOW.idle;
  const glowScale = ringPx / 80;
  const midInset = Math.round(-8 * glowScale);
  const outerInset = Math.round(-14 * glowScale);
  const uid = `amin-${size}`;

  /* ── Wake-up detection ── */
  useEffect(() => {
    if (prevState === 'sleeping' && state !== 'sleeping') {
      wakeTimers.current.forEach(clearTimeout);
      setWakePhase(1);
      wakeTimers.current = [
        setTimeout(() => setWakePhase(2), 300),
        setTimeout(() => setWakePhase(3), 600),
        setTimeout(() => setWakePhase(0), 950),
      ];
    }
  }, [state, prevState]);

  useEffect(() => {
    if (state === 'sleeping') {
      wakeTimers.current.forEach(clearTimeout);
      wakeTimers.current = [];
      setWakePhase(0);
    }
  }, [state]);

  useEffect(
    () => () => {
      wakeTimers.current.forEach(clearTimeout);
    },
    []
  );

  /* ── Wake-up eyelid phases ── */
  useEffect(() => {
    if (!mountedRef.current) return;
    if (wakePhase === 1)
      blinkCtrl
        .start({
          scaleY: 0.45,
          transition: { duration: 0.25, ease: [0.2, 0.8, 0.2, 1] },
        })
        .catch(() => {});
    else if (wakePhase >= 2)
      blinkCtrl
        .start({
          scaleY: 0,
          transition: { duration: 0.22, ease: [0, 0, 0.2, 1] },
        })
        .catch(() => {});
  }, [wakePhase, blinkCtrl]);

  /* ── Normal eyelid control ── */
  useEffect(() => {
    if (wakePhase > 0) return;
    if (blinkTimer.current) {
      clearTimeout(blinkTimer.current);
      blinkTimer.current = null;
    }
    if (!mountedRef.current) return;

    if (state === 'sleeping') {
      blinkCtrl.set({ scaleY: 1 });
      return;
    }
    if (state !== 'idle') {
      blinkCtrl
        .start({ scaleY: 0, transition: { duration: 0.1 } })
        .catch(() => {});
      return;
    }

    blinkCtrl
      .start({ scaleY: 0, transition: { duration: 0.15 } })
      .catch(() => {});
    const doBlink = async () => {
      if (!mountedRef.current) return;
      try {
        const dbl = Math.random() < 0.1;
        await blinkCtrl.start({ scaleY: 1, transition: { duration: 0.07 } });
        if (!mountedRef.current) return;
        await blinkCtrl.start({ scaleY: 0, transition: { duration: 0.1 } });
        if (!mountedRef.current) return;
        if (dbl) {
          await new Promise(resolve => setTimeout(resolve, 80));
          if (!mountedRef.current) return;
          await blinkCtrl.start({ scaleY: 1, transition: { duration: 0.06 } });
          if (!mountedRef.current) return;
          await blinkCtrl.start({ scaleY: 0, transition: { duration: 0.09 } });
        }
        if (mountedRef.current) {
          blinkTimer.current = setTimeout(doBlink, 2500 + Math.random() * 3500);
        }
      } catch {
        /* unmounted */
      }
    };
    blinkTimer.current = setTimeout(doBlink, 1500 + Math.random() * 2000);
    return () => {
      if (blinkTimer.current) clearTimeout(blinkTimer.current);
    };
  }, [state, blinkCtrl, wakePhase]);

  /* ── Micro-saccade (idle only) ── */
  const saccadeResetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (state !== 'idle' || wakePhase > 0) {
      setSaccadeOff({ dx: 0, dy: 0 });
      return;
    }
    const doSaccade = () => {
      setSaccadeOff({
        dx: (Math.random() - 0.5) * 1.5,
        dy: (Math.random() - 0.5) * 1,
      });
      saccadeResetTimer.current = setTimeout(
        () => setSaccadeOff({ dx: 0, dy: 0 }),
        200
      );
      saccadeTimer.current = setTimeout(doSaccade, 3000 + Math.random() * 3000);
    };
    saccadeTimer.current = setTimeout(doSaccade, 2000 + Math.random() * 2000);
    return () => {
      if (saccadeTimer.current) clearTimeout(saccadeTimer.current);
      if (saccadeResetTimer.current) clearTimeout(saccadeResetTimer.current);
    };
  }, [state, wakePhase]);

  /* ── Glasses glint (idle only) ── */
  const glintResetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (state !== 'idle') {
      setShowGlint(false);
      return;
    }
    const doGlint = () => {
      setShowGlint(true);
      glintResetTimer.current = setTimeout(() => setShowGlint(false), 600);
      glintTimer.current = setTimeout(doGlint, 8000 + Math.random() * 6000);
    };
    glintTimer.current = setTimeout(doGlint, 5000 + Math.random() * 5000);
    return () => {
      if (glintTimer.current) clearTimeout(glintTimer.current);
      if (glintResetTimer.current) clearTimeout(glintResetTimer.current);
    };
  }, [state]);

  /* ── Computed animation configs ── */
  const containerAnim =
    state === 'sleeping'
      ? {
          scale: [1, 1.005, 1],
          y: [0, 0.5, 0],
          transition: {
            duration: 6,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        }
      : state === 'idle'
        ? {
            scale: [1, 1.02, 1],
            y: [0, -1, 0],
            transition: {
              duration: 4,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : state === 'speaking'
          ? {
              scale: [1, 1.035, 0.98, 1.028, 1],
              transition: {
                duration: 0.55,
                repeat: Infinity,
                ease: 'easeInOut' as const,
              },
            }
          : state === 'thinking'
            ? {
                rotate: [0, -1.5, 1.5, -0.6, 0],
                transition: {
                  duration: 3.5,
                  repeat: Infinity,
                  ease: 'easeInOut' as const,
                },
              }
            : state === 'listening'
              ? {
                  scale: [1, 1.025, 1],
                  scaleX: [1, 1.012, 1],
                  transition: {
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut' as const,
                  },
                }
              : state === 'error'
                ? { x: [0, -3, 3, -2, 1, 0], transition: { duration: 0.5 } }
                : undefined;

  const headAnim =
    state === 'sleeping'
      ? {
          rotate: -4,
          y: 3,
          x: 0,
          transition: { duration: 0.5, ease: 'easeInOut' as const },
        }
      : wakePhase === 1
        ? {
            rotate: -1.5,
            y: 1,
            x: 0,
            transition: { duration: 0.3, ease: [0.2, 0.8, 0.2, 1] as number[] },
          }
        : wakePhase >= 2
          ? {
              rotate: 0,
              y: 0,
              x: 0,
              transition: {
                type: 'spring' as const,
                stiffness: 180,
                damping: 14,
              },
            }
          : state === 'speaking'
            ? {
                y: [0, -2.5, 1, -1.8, 0.5, -1, 0],
                x: 0,
                rotate: 0,
                transition: {
                  duration: 1.2,
                  repeat: Infinity,
                  ease: 'easeInOut' as const,
                },
              }
            : state === 'thinking'
              ? {
                  x: [0, -1.2, 0],
                  y: [0, -1.8, 0],
                  rotate: 0,
                  transition: {
                    duration: 3.5,
                    repeat: Infinity,
                    ease: 'easeInOut' as const,
                  },
                }
              : state === 'listening'
                ? {
                    rotate: [0, 3.5, -2, 1.5, -1, 0],
                    x: 0,
                    y: 0,
                    transition: {
                      duration: 3.5,
                      repeat: Infinity,
                      ease: 'easeInOut' as const,
                    },
                  }
                : { x: 0, y: 0, rotate: 0 };

  const neckAnim =
    state === 'speaking' ? { y: [0, 1.2, -0.4, 0.8, -0.2, 0.5, 0] } : { y: 0 };
  const neckTransition =
    state === 'speaking'
      ? { duration: 1.2, repeat: Infinity, ease: 'easeInOut' as const }
      : undefined;

  const DEFAULT_MOUTH = 'M86 118 Q100 126, 114 118';
  const mouthAnim =
    state === 'sleeping'
      ? { d: 'M88 119 Q100 123, 112 119', transition: { duration: 0.5 } }
      : state === 'speaking'
        ? {
            d: [
              'M86 118 Q100 127, 114 118',
              'M88 116 Q100 134, 112 116',
              'M87 117 Q100 121, 113 117',
              'M86 118 Q100 136, 114 118',
              'M89 116 Q100 122, 111 116',
              'M87 117 Q100 130, 113 117',
              'M88 117 Q100 120, 112 117',
              'M86 118 Q100 133, 114 118',
              'M86 118 Q100 127, 114 118',
            ],
            transition: { duration: 0.4, repeat: Infinity },
          }
        : state === 'thinking'
          ? { d: 'M90 119 Q100 122, 110 119', transition: { duration: 0.5 } }
          : state === 'error'
            ? { d: 'M88 120 Q100 118, 112 120', transition: { duration: 0.3 } }
            : {
                d: DEFAULT_MOUTH,
                transition: { duration: 0.3, ease: 'easeOut' },
              };

  const leftBrowAnim =
    state === 'sleeping'
      ? { d: 'M72 84 Q82 80, 92 83', transition: { duration: 0.5 } }
      : state === 'speaking'
        ? {
            d: [
              'M70 81 Q80 74, 92 78',
              'M70 79 Q80 71, 92 75',
              'M70 80 Q80 73, 92 77',
              'M70 81 Q80 74, 92 78',
            ],
            transition: {
              duration: 1.8,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : state === 'thinking'
          ? { d: 'M70 77 Q80 70, 92 74', transition: { duration: 0.6 } }
          : state === 'listening'
            ? { d: 'M70 79 Q80 71, 92 75', transition: { duration: 0.5 } }
            : state === 'error'
              ? { d: 'M70 78 Q80 72, 92 80', transition: { duration: 0.3 } }
              : { d: 'M70 81 Q80 74, 92 78' };

  const rightBrowAnim =
    state === 'sleeping'
      ? { d: 'M108 83 Q118 80, 128 84', transition: { duration: 0.5 } }
      : state === 'speaking'
        ? {
            d: [
              'M108 78 Q120 74, 130 81',
              'M108 75 Q120 71, 130 78',
              'M108 77 Q120 73, 130 80',
              'M108 78 Q120 74, 130 81',
            ],
            transition: {
              duration: 1.8,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : state === 'thinking'
          ? { d: 'M108 76 Q120 74, 130 79', transition: { duration: 0.6 } }
          : state === 'listening'
            ? { d: 'M108 75 Q120 71, 130 78', transition: { duration: 0.5 } }
            : state === 'error'
              ? { d: 'M108 80 Q118 72, 130 78', transition: { duration: 0.3 } }
              : { d: 'M108 78 Q120 74, 130 81' };

  const eyeGroupAnim =
    state === 'thinking'
      ? { y: [-0.5, 1, -0.5], transition: { duration: 3, repeat: Infinity } }
      : state === 'listening'
        ? { y: [0, -1, 0], transition: { duration: 2.5, repeat: Infinity } }
        : { y: 0 };

  const leftPupilAnim =
    state === 'thinking'
      ? {
          cx: [83, 79, 78, 80, 83],
          cy: [92, 89, 89, 90, 92],
          transition: { duration: 3, repeat: Infinity },
        }
      : state === 'listening'
        ? {
            cx: [83, 81, 82, 81, 83],
            cy: [92, 90, 91, 90, 92],
            r: [4.5, 4.8, 4.6, 4.8, 4.5],
            transition: {
              duration: 2.5,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : {
            cx: 83 + saccadeOff.dx,
            cy: 92 + saccadeOff.dy,
            transition: {
              type: 'spring' as const,
              stiffness: 300,
              damping: 20,
            },
          };

  const rightPupilAnim =
    state === 'thinking'
      ? {
          cx: [117, 113, 112, 114, 117],
          cy: [92, 89, 89, 90, 92],
          transition: { duration: 3, repeat: Infinity },
        }
      : state === 'listening'
        ? {
            cx: [117, 115, 116, 115, 117],
            cy: [92, 90, 91, 90, 92],
            r: [4.5, 4.8, 4.6, 4.8, 4.5],
            transition: {
              duration: 2.5,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : {
            cx: 117 + saccadeOff.dx,
            cy: 92 + saccadeOff.dy,
            transition: {
              type: 'spring' as const,
              stiffness: 300,
              damping: 20,
            },
          };

  const innerRingAnim =
    state === 'sleeping'
      ? {
          borderColor: [
            'rgba(255,255,255,0.06)',
            'rgba(255,255,255,0.12)',
            'rgba(255,255,255,0.06)',
          ],
          boxShadow: [
            '0 0 4px rgba(255,255,255,0.08)',
            '0 0 10px rgba(255,255,255,0.14)',
            '0 0 4px rgba(255,255,255,0.08)',
          ],
          transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
        }
      : state === 'idle'
        ? {
            borderColor: [
              'rgba(255,255,255,0.15)',
              'rgba(255,255,255,0.35)',
              'rgba(255,255,255,0.15)',
            ],
            boxShadow: [
              '0 0 8px rgba(255,255,255,0.12)',
              '0 0 20px rgba(255,255,255,0.22)',
              '0 0 8px rgba(255,255,255,0.12)',
            ],
            transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' },
          }
        : state === 'speaking'
          ? {
              borderColor: [
                'rgba(255,255,255,0.35)',
                'rgba(255,255,255,0.95)',
                'rgba(255,255,255,0.35)',
              ],
              boxShadow: [
                '0 0 12px rgba(255,255,255,0.25)',
                '0 0 30px rgba(255,255,255,0.45)',
                '0 0 12px rgba(255,255,255,0.25)',
              ],
              transition: {
                duration: 0.4,
                repeat: Infinity,
                ease: 'easeInOut',
              },
            }
          : state === 'listening'
            ? {
                borderColor: [
                  'rgba(255,255,255,0.25)',
                  'rgba(255,255,255,0.55)',
                  'rgba(255,255,255,0.25)',
                ],
                boxShadow: [
                  '0 0 10px rgba(255,255,255,0.18)',
                  '0 0 26px rgba(255,255,255,0.35)',
                  '0 0 10px rgba(255,255,255,0.18)',
                ],
                transition: {
                  duration: 1.2,
                  repeat: Infinity,
                  ease: 'easeInOut',
                },
              }
            : state === 'thinking'
              ? {
                  borderColor: [
                    'rgba(255,255,255,0.35)',
                    'rgba(255,255,255,0.65)',
                    'rgba(255,255,255,0.35)',
                  ],
                  boxShadow: [
                    '0 0 8px rgba(255,255,255,0.2)',
                    '0 0 22px rgba(255,255,255,0.38)',
                    '0 0 8px rgba(255,255,255,0.2)',
                  ],
                  transition: {
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  },
                }
              : {
                  borderColor: [
                    'rgba(248,113,113,0.20)',
                    'rgba(248,113,113,0.50)',
                    'rgba(248,113,113,0.20)',
                  ],
                  boxShadow: [
                    '0 0 10px rgba(248,113,113,0.2)',
                    '0 0 24px rgba(248,113,113,0.4)',
                    '0 0 10px rgba(248,113,113,0.2)',
                  ],
                  transition: {
                    duration: 0.8,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  },
                };

  const midAuraAnim =
    state === 'sleeping'
      ? {
          opacity: [0.3, 0.5, 0.3],
          scale: [1, 1.02, 1],
          transition: {
            duration: 5,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        }
      : state === 'idle'
        ? {
            opacity: [0.4, 0.7, 0.4],
            scale: [1, 1.03, 1],
            transition: {
              duration: 3.5,
              repeat: Infinity,
              ease: 'easeInOut' as const,
            },
          }
        : state === 'speaking'
          ? {
              opacity: [0.5, 0.9, 0.5],
              scale: [1, 1.05, 1],
              transition: {
                duration: 0.45,
                repeat: Infinity,
                ease: 'easeInOut' as const,
              },
            }
          : state === 'listening'
            ? {
                opacity: [0.4, 0.8, 0.4],
                scale: [1, 1.04, 1],
                transition: {
                  duration: 1.5,
                  repeat: Infinity,
                  ease: 'easeInOut' as const,
                },
              }
            : state === 'thinking'
              ? {
                  opacity: [0.3, 0.6, 0.3],
                  scale: [1, 1.03, 1],
                  transition: {
                    duration: 2.5,
                    repeat: Infinity,
                    ease: 'easeInOut' as const,
                  },
                }
              : {
                  opacity: [0.5, 0.8, 0.5],
                  scale: [1, 1.04, 1],
                  transition: {
                    duration: 0.6,
                    repeat: Infinity,
                    ease: 'easeInOut' as const,
                  },
                };

  return (
    <motion.div
      className={className ?? ''}
      style={{
        width: ringPx,
        height: ringPx,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        willChange: 'transform',
        flexShrink: 0,
      }}
      animate={containerAnim}
    >
      {/* ── Layer 1: Inner Ring ── */}
      {showRing && (
        <motion.div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `1.5px solid ${glow.ring}`,
            background: active
              ? 'rgba(255,255,255,0.04)'
              : state === 'sleeping'
                ? 'rgba(255,255,255,0.02)'
                : 'rgba(255,255,255,0.02)',
            willChange: 'border-color, box-shadow',
          }}
          animate={innerRingAnim}
        />
      )}

      {/* ── Layer 2: Mid Aura ── */}
      {showRing && (
        <motion.div
          style={{
            position: 'absolute',
            inset: midInset,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${glow.mid} 0%, transparent 70%)`,
            pointerEvents: 'none',
            willChange: 'opacity, transform',
          }}
          animate={midAuraAnim}
        />
      )}

      {/* ── Layer 3: Outer Halo (active only) ── */}
      <AnimatePresence>
        {showRing && active && (
          <motion.div
            key="outer-halo"
            style={{
              position: 'absolute',
              inset: outerInset,
              borderRadius: '50%',
              border: `1px solid ${glow.primary}`,
              pointerEvents: 'none',
              willChange: 'opacity, transform',
            }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{
              opacity: [0, 0.35, 0],
              scale: [1, 1.1, 1],
              transition: {
                duration:
                  state === 'speaking' ? 0.5 : state === 'listening' ? 1.2 : 2,
                repeat: Infinity,
                ease: 'easeOut',
              },
            }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
          />
        )}
      </AnimatePresence>

      {/* ── Listening sound-wave rings ── */}
      {state === 'listening' && (
        <>
          <motion.div
            style={{
              position: 'absolute',
              inset: -4 * glowScale,
              borderRadius: '50%',
              border: '1.5px solid rgba(255,255,255,0.25)',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ scale: [1, 1.18, 1], opacity: [0.35, 0, 0.35] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
          />
          <motion.div
            style={{
              position: 'absolute',
              inset: -8 * glowScale,
              borderRadius: '50%',
              border: '1px solid rgba(255,255,255,0.18)',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ scale: [1, 1.22, 1], opacity: [0.25, 0, 0.25] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeOut',
              delay: 0.25,
            }}
          />
          <motion.div
            style={{
              position: 'absolute',
              inset: -12 * glowScale,
              borderRadius: '50%',
              border: '0.5px solid rgba(255,255,255,0.10)',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ scale: [1, 1.28, 1], opacity: [0.15, 0, 0.15] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeOut',
              delay: 0.5,
            }}
          />
        </>
      )}

      {/* ── Speaking ripples ── */}
      {state === 'speaking' && showExtras && (
        <>
          <motion.div
            style={{
              position: 'absolute',
              bottom: -3 * glowScale,
              left: '50%',
              transform: 'translateX(-50%)',
              width: px * 0.6,
              height: px * 0.25,
              borderRadius: '50%',
              border: '1px solid rgba(255,255,255,0.25)',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ scale: [1, 1.35, 1], opacity: [0.3, 0, 0.3] }}
            transition={{ duration: 0.5, repeat: Infinity }}
          />
          <motion.div
            style={{
              position: 'absolute',
              bottom: -6 * glowScale,
              left: '50%',
              transform: 'translateX(-50%)',
              width: px * 0.8,
              height: px * 0.35,
              borderRadius: '50%',
              border: '1px solid rgba(255,255,255,0.15)',
              pointerEvents: 'none',
              willChange: 'transform, opacity',
            }}
            animate={{ scale: [1, 1.3, 1], opacity: [0.2, 0, 0.2] }}
            transition={{ duration: 0.5, repeat: Infinity, delay: 0.15 }}
          />
        </>
      )}

      {/* ── Wake-up ring fill ── */}
      <AnimatePresence>
        {showRing && wakePhase > 0 && (
          <motion.svg
            key="wake-ring"
            viewBox={`0 0 ${ringPx} ${ringPx}`}
            style={{
              position: 'absolute',
              inset: 0,
              pointerEvents: 'none',
              transform: 'rotate(-90deg)',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.3 } }}
          >
            <motion.circle
              cx={ringPx / 2}
              cy={ringPx / 2}
              r={ringPx / 2 - 2}
              fill="none"
              stroke="rgba(255,255,255,0.65)"
              strokeWidth="2.5"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{
                pathLength: wakePhase >= 3 ? 1 : wakePhase >= 2 ? 0.7 : 0.3,
              }}
              transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
            />
          </motion.svg>
        )}
      </AnimatePresence>

      {/* ── Wake-up glow burst ── */}
      <AnimatePresence>
        {wakePhase === 2 && (
          <motion.div
            key="glow-burst"
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: '50%',
              background:
                'radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%)',
              pointerEvents: 'none',
            }}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1.8, opacity: [0, 0.5, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: [0, 0, 0.2, 1] }}
          />
        )}
      </AnimatePresence>

      {/* ══════════════════════════════════════════════════
          SVG Illustrated Avatar — Amin
          200x200 viewBox, character styled from photo:
          curly dark hair, rectangular glasses, beard,
          navy suit, warm brown skin
         ══════════════════════════════════════════════════ */}
      <svg
        viewBox="0 0 200 200"
        width={px}
        height={px}
        style={{
          borderRadius: '50%',
          overflow: 'hidden',
          filter: `drop-shadow(0 0 ${active ? 10 : state === 'sleeping' ? 4 : 6}px ${glow.primary})`,
          opacity: state === 'sleeping' ? 0.82 : 1,
          willChange: 'filter',
        }}
      >
        <defs>
          <radialGradient id={`${uid}-bg`} cx="50%" cy="38%" r="58%">
            <stop offset="0%" stopColor="#1e3048" />
            <stop offset="60%" stopColor="#141e30" />
            <stop offset="100%" stopColor="#0e1420" />
          </radialGradient>
          <radialGradient id={`${uid}-skin`} cx="46%" cy="40%" r="54%">
            <stop offset="0%" stopColor="#d4a06a" />
            <stop offset="40%" stopColor="#c68a5a" />
            <stop offset="80%" stopColor="#b07848" />
            <stop offset="100%" stopColor="#a06830" />
          </radialGradient>
          <linearGradient
            id={`${uid}-suit`}
            x1="50%"
            y1="0%"
            x2="50%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#2a3a58" />
            <stop offset="50%" stopColor="#1e2e48" />
            <stop offset="100%" stopColor="#152238" />
          </linearGradient>
          <linearGradient
            id={`${uid}-hair`}
            x1="30%"
            y1="0%"
            x2="70%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#1a1210" />
            <stop offset="50%" stopColor="#120c08" />
            <stop offset="100%" stopColor="#0a0604" />
          </linearGradient>
          <linearGradient
            id={`${uid}-glasses`}
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#1a2840" />
            <stop offset="100%" stopColor="#0e1a2e" />
          </linearGradient>
          <linearGradient
            id={`${uid}-shirt`}
            x1="50%"
            y1="0%"
            x2="50%"
            y2="100%"
          >
            <stop offset="0%" stopColor="#f0ece8" />
            <stop offset="100%" stopColor="#ddd8d2" />
          </linearGradient>
          <clipPath id={`${uid}-clip`}>
            <circle cx="100" cy="100" r="100" />
          </clipPath>
        </defs>

        <g clipPath={`url(#${uid}-clip)`}>
          {/* Background */}
          <circle cx="100" cy="100" r="100" fill={`url(#${uid}-bg)`} />
          <circle cx="75" cy="60" r="55" fill="rgba(30,48,72,0.3)" />

          {/* Neck & suit jacket */}
          <motion.g animate={neckAnim} transition={neckTransition}>
            {/* Suit body */}
            <path
              d="M52 168 Q58 148, 100 138 Q142 148, 148 168 L155 210 L45 210 Z"
              fill={`url(#${uid}-suit)`}
            />
            {/* Lapel lines */}
            <path
              d="M100 142 L78 170"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="0.8"
            />
            <path
              d="M100 142 L122 170"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="0.8"
            />
            {/* Suit check pattern */}
            <path
              d="M65 160 L75 165"
              fill="none"
              stroke="rgba(100,130,180,0.06)"
              strokeWidth="0.4"
            />
            <path
              d="M125 160 L135 165"
              fill="none"
              stroke="rgba(100,130,180,0.06)"
              strokeWidth="0.4"
            />
            <path
              d="M70 170 L80 175"
              fill="none"
              stroke="rgba(100,130,180,0.06)"
              strokeWidth="0.4"
            />
            <path
              d="M120 170 L130 175"
              fill="none"
              stroke="rgba(100,130,180,0.06)"
              strokeWidth="0.4"
            />
            {/* White shirt collar V */}
            <path
              d="M82 148 L100 160 L118 148"
              fill="none"
              stroke={`url(#${uid}-shirt)`}
              strokeWidth="3.5"
              strokeLinejoin="round"
            />
            <path
              d="M84 146 L100 156 L116 146"
              fill={`url(#${uid}-shirt)`}
              opacity="0.9"
            />
            {/* Collar shadow */}
            <path
              d="M86 148 Q100 158, 114 148"
              fill="none"
              stroke="rgba(0,0,0,0.08)"
              strokeWidth="0.5"
            />
            {/* Neck */}
            <path
              d="M88 144 Q100 138, 112 144 Q114 134, 100 130 Q86 134, 88 144"
              fill="#b07848"
            />
          </motion.g>

          {/* Head group */}
          <motion.g
            initial={
              state === 'sleeping'
                ? { rotate: -4, y: 3, x: 0 }
                : { rotate: 0, y: 0, x: 0 }
            }
            animate={headAnim}
            style={{ originX: '100px', originY: '95px' }}
          >
            {/* Face shadow + face */}
            <ellipse cx="100" cy="96" rx="54" ry="58" fill="rgba(0,0,0,0.15)" />
            <ellipse
              cx="100"
              cy="94"
              rx="53"
              ry="57"
              fill={`url(#${uid}-skin)`}
            />
            <ellipse
              cx="100"
              cy="118"
              rx="38"
              ry="18"
              fill="rgba(140,100,60,0.06)"
            />

            {/* Ears */}
            <ellipse cx="48" cy="98" rx="7" ry="10" fill="#b87a48" />
            <ellipse cx="49" cy="98" rx="4.5" ry="6.5" fill="#a06830" />
            <ellipse cx="152" cy="98" rx="7" ry="10" fill="#b87a48" />
            <ellipse cx="151" cy="98" rx="4.5" ry="6.5" fill="#a06830" />

            {/* Ear glow — listening */}
            {state === 'listening' &&
              [0, 1, 2].map(i => (
                <g key={`ear${i}`}>
                  <motion.circle
                    cx="48"
                    cy="98"
                    r={9}
                    fill="none"
                    stroke={`rgba(255,255,255,${0.35 - i * 0.1})`}
                    strokeWidth={1.2 - i * 0.3}
                    initial={false}
                    animate={{
                      r: [9 + i * 3, 15 + i * 4, 9 + i * 3],
                      opacity: [0.35 - i * 0.1, 0, 0.35 - i * 0.1],
                    }}
                    transition={{
                      duration: 1.2,
                      repeat: Infinity,
                      delay: i * 0.15,
                    }}
                  />
                  <motion.circle
                    cx="152"
                    cy="98"
                    r={9}
                    fill="none"
                    stroke={`rgba(255,255,255,${0.35 - i * 0.1})`}
                    strokeWidth={1.2 - i * 0.3}
                    initial={false}
                    animate={{
                      r: [9 + i * 3, 15 + i * 4, 9 + i * 3],
                      opacity: [0.35 - i * 0.1, 0, 0.35 - i * 0.1],
                    }}
                    transition={{
                      duration: 1.2,
                      repeat: Infinity,
                      delay: 0.2 + i * 0.15,
                    }}
                  />
                </g>
              ))}

            {/* Beard / stubble */}
            <ellipse
              cx="100"
              cy="126"
              rx="36"
              ry="24"
              fill="rgba(18,12,8,0.12)"
            />
            <ellipse
              cx="100"
              cy="130"
              rx="30"
              ry="18"
              fill="rgba(18,12,8,0.10)"
            />
            <path
              d="M66 110 Q68 132, 80 140 Q90 144, 100 145 Q110 144, 120 140 Q132 132, 134 110"
              fill="none"
              stroke="rgba(18,12,8,0.06)"
              strokeWidth="1"
            />
            {/* Jawline stubble texture */}
            <path
              d="M72 118 Q74 130, 84 136"
              fill="none"
              stroke="rgba(18,12,8,0.04)"
              strokeWidth="0.6"
            />
            <path
              d="M128 118 Q126 130, 116 136"
              fill="none"
              stroke="rgba(18,12,8,0.04)"
              strokeWidth="0.6"
            />
            <path
              d="M88 138 Q100 142, 112 138"
              fill="none"
              stroke="rgba(18,12,8,0.05)"
              strokeWidth="0.5"
            />

            {/* Hair — dark, curly, voluminous */}
            <path
              d="M44 84 Q44 38, 72 26 Q88 20, 104 21 Q122 20, 142 30 Q160 42, 158 84"
              fill={`url(#${uid}-hair)`}
            />
            <path
              d="M46 86 Q48 42, 76 30 Q90 24, 106 25 Q124 24, 144 34 Q158 48, 156 86"
              fill="#120c08"
            />
            {/* Curly texture strands */}
            <path
              d="M52 68 Q48 50, 58 38 Q64 32, 72 28"
              fill="none"
              stroke="rgba(26,18,16,0.7)"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path
              d="M148 68 Q152 50, 142 38 Q136 32, 128 28"
              fill="none"
              stroke="rgba(26,18,16,0.7)"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path
              d="M60 55 Q70 26, 100 22 Q130 26, 148 48"
              fill="none"
              stroke="rgba(26,18,16,0.5)"
              strokeWidth="3"
            />
            {/* Volume wave highlights */}
            <path
              d="M56 62 Q60 44, 72 34"
              fill="none"
              stroke="rgba(40,28,20,0.6)"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d="M144 62 Q140 44, 128 34"
              fill="none"
              stroke="rgba(40,28,20,0.6)"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d="M66 48 Q80 30, 100 26 Q120 30, 134 48"
              fill="none"
              stroke="rgba(50,35,25,0.3)"
              strokeWidth="2.5"
            />
            {/* Curl definition */}
            <path
              d="M54 72 Q50 58, 56 46"
              fill="none"
              stroke="rgba(26,18,16,0.5)"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M146 72 Q150 58, 144 46"
              fill="none"
              stroke="rgba(26,18,16,0.5)"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M68 40 Q76 28, 92 24"
              fill="none"
              stroke="rgba(60,42,30,0.15)"
              strokeWidth="1.8"
            />
            <path
              d="M132 40 Q124 28, 108 24"
              fill="none"
              stroke="rgba(60,42,30,0.15)"
              strokeWidth="1.8"
            />
            {/* Top curl wave */}
            <path
              d="M74 32 Q82 22, 96 21 Q104 20, 112 22 Q120 24, 126 30"
              fill="none"
              stroke="rgba(60,42,30,0.2)"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Subtle shine */}
            <path
              d="M76 36 Q88 28, 106 28"
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1.5"
            />
            {/* Sideburns */}
            <path
              d="M48 84 Q44 72, 48 56"
              fill="none"
              stroke="#120c08"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path
              d="M156 84 Q160 72, 156 56"
              fill="none"
              stroke="#120c08"
              strokeWidth="3.5"
              strokeLinecap="round"
            />
            <rect
              x="44"
              y="82"
              width="8"
              height="18"
              rx="3"
              fill="#120c08"
              opacity="0.7"
            />
            <rect
              x="148"
              y="82"
              width="8"
              height="18"
              rx="3"
              fill="#120c08"
              opacity="0.7"
            />

            {/* Eyebrows — thicker for Amin */}
            <motion.path
              key={`lb-${state}`}
              d="M70 81 Q80 74, 92 78"
              fill="none"
              stroke="#1a1210"
              strokeWidth="3"
              strokeLinecap="round"
              initial={false}
              animate={leftBrowAnim}
            />
            <motion.path
              key={`rb-${state}`}
              d="M108 78 Q120 74, 130 81"
              fill="none"
              stroke="#1a1210"
              strokeWidth="3"
              strokeLinecap="round"
              initial={false}
              animate={rightBrowAnim}
            />

            {/* Eyes */}
            <motion.g animate={eyeGroupAnim}>
              {/* Left eye */}
              <ellipse cx="82" cy="92" rx="9" ry="7.5" fill="white" />
              <ellipse
                cx="82"
                cy="92"
                rx="9"
                ry="7.5"
                fill="rgba(220,230,255,0.15)"
              />
              <motion.circle
                key={`lp-${state}`}
                cx="83"
                cy="92"
                r="4.5"
                fill="#2a1a0e"
                initial={false}
                animate={leftPupilAnim}
              />
              <circle cx="85" cy="90" r="1.5" fill="white" opacity="0.85" />
              <circle cx="80" cy="93.5" r="0.7" fill="white" opacity="0.4" />

              {/* Right eye */}
              <ellipse cx="118" cy="92" rx="9" ry="7.5" fill="white" />
              <ellipse
                cx="118"
                cy="92"
                rx="9"
                ry="7.5"
                fill="rgba(220,230,255,0.15)"
              />
              <motion.circle
                key={`rp-${state}`}
                cx="117"
                cy="92"
                r="4.5"
                fill="#2a1a0e"
                initial={false}
                animate={rightPupilAnim}
              />
              <circle cx="119" cy="90" r="1.5" fill="white" opacity="0.85" />
              <circle cx="115" cy="93.5" r="0.7" fill="white" opacity="0.4" />

              {/* Eyelids */}
              <motion.rect
                x="72"
                y="84"
                width="20"
                height="16"
                rx="8"
                fill={`url(#${uid}-skin)`}
                initial={{ scaleY: state === 'sleeping' ? 1 : 0 }}
                animate={blinkCtrl}
                style={{ originX: '82px', originY: '84px' }}
              />
              <motion.rect
                x="108"
                y="84"
                width="20"
                height="16"
                rx="8"
                fill={`url(#${uid}-skin)`}
                initial={{ scaleY: state === 'sleeping' ? 1 : 0 }}
                animate={blinkCtrl}
                style={{ originX: '118px', originY: '84px' }}
              />
            </motion.g>

            {/* Glasses — rectangular frames */}
            <motion.g
              animate={
                state === 'thinking'
                  ? {
                      y: [0, 0.3, 0],
                      transition: { duration: 3, repeat: Infinity },
                    }
                  : { y: 0 }
              }
            >
              <rect
                x="66"
                y="82"
                width="30"
                height="20"
                rx="3"
                fill="none"
                stroke={`url(#${uid}-glasses)`}
                strokeWidth="3"
              />
              <rect
                x="104"
                y="82"
                width="30"
                height="20"
                rx="3"
                fill="none"
                stroke={`url(#${uid}-glasses)`}
                strokeWidth="3"
              />
              {/* Bridge */}
              <path
                d="M96 91 Q100 86, 104 91"
                fill="none"
                stroke="#1a2840"
                strokeWidth="2.5"
              />
              {/* Arms */}
              <line
                x1="66"
                y1="89"
                x2="50"
                y2="86"
                stroke="#1a2840"
                strokeWidth="2.2"
              />
              <line
                x1="134"
                y1="89"
                x2="150"
                y2="86"
                stroke="#1a2840"
                strokeWidth="2.2"
              />
              {/* Lens reflection */}
              <path
                d="M72 86 L77 84"
                stroke="rgba(180,210,255,0.20)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <path
                d="M110 86 L115 84"
                stroke="rgba(180,210,255,0.20)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              {/* Thinking reflection */}
              {state === 'thinking' && (
                <motion.path
                  d="M74 88 L76 86"
                  stroke="rgba(200,230,255,0.5)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  animate={{ opacity: [0, 0.6, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
              {/* Glint flash */}
              {showGlint && (
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 0.7, 0] }}
                  transition={{ duration: 0.6 }}
                >
                  <path
                    d="M73 87 L78 84.5"
                    stroke="rgba(200,230,255,0.6)"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                  <path
                    d="M111 87 L116 84.5"
                    stroke="rgba(200,230,255,0.5)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </motion.g>
              )}
            </motion.g>

            {/* Nose */}
            <path
              d="M96 100 Q100 112, 104 100"
              fill="none"
              stroke="rgba(140,95,55,0.25)"
              strokeWidth="1.5"
            />
            <circle cx="96" cy="107" r="1.5" fill="rgba(140,95,55,0.08)" />

            {/* Mouth */}
            <motion.path
              key={`mouth-${state}`}
              d={DEFAULT_MOUTH}
              fill="none"
              stroke="rgba(120,65,40,0.50)"
              strokeWidth="2.2"
              strokeLinecap="round"
              initial={false}
              animate={mouthAnim}
            />

            {/* Tongue hint (speaking) */}
            {state === 'speaking' && (
              <motion.ellipse
                cx="100"
                cy="126"
                rx="4"
                ry="2.5"
                fill="rgba(160,70,60,0.3)"
                initial={false}
                animate={{
                  cy: [126, 129, 125, 130, 125, 128, 125, 129, 126],
                  opacity: [0.15, 0.4, 0, 0.45, 0, 0.3, 0, 0.4, 0.15],
                  ry: [2, 3.2, 1, 3.5, 1, 2.8, 1, 3.2, 2],
                }}
                transition={{ duration: 0.4, repeat: Infinity }}
              />
            )}

            {/* Lower lip (speaking) */}
            {state === 'speaking' && (
              <motion.path
                d="M90 122 Q100 125, 110 122"
                fill="none"
                stroke="rgba(110,55,35,0.22)"
                strokeWidth="1.2"
                initial={false}
                animate={{
                  d: [
                    'M90 122 Q100 125, 110 122',
                    'M90 122 Q100 131, 110 122',
                    'M90 122 Q100 123, 110 122',
                    'M90 122 Q100 133, 110 122',
                    'M90 122 Q100 123, 110 122',
                    'M90 122 Q100 128, 110 122',
                    'M90 122 Q100 123, 110 122',
                    'M90 122 Q100 131, 110 122',
                    'M90 122 Q100 125, 110 122',
                  ],
                }}
                transition={{ duration: 0.4, repeat: Infinity }}
              />
            )}

            {/* Cheeks */}
            <motion.circle
              key={`cl-${state}`}
              cx="70"
              cy="108"
              r="9"
              fill="rgba(180,110,70,0.06)"
              initial={false}
              animate={
                state === 'speaking'
                  ? {
                      r: [9, 10.5, 9],
                      fill: [
                        'rgba(180,110,70,0.06)',
                        'rgba(180,110,70,0.12)',
                        'rgba(180,110,70,0.06)',
                      ],
                      transition: { duration: 0.5, repeat: Infinity },
                    }
                  : { r: 9 }
              }
            />
            <motion.circle
              key={`cr-${state}`}
              cx="130"
              cy="108"
              r="9"
              fill="rgba(180,110,70,0.06)"
              initial={false}
              animate={
                state === 'speaking'
                  ? {
                      r: [9, 10.5, 9],
                      fill: [
                        'rgba(180,110,70,0.06)',
                        'rgba(180,110,70,0.12)',
                        'rgba(180,110,70,0.06)',
                      ],
                      transition: { duration: 0.5, repeat: Infinity },
                    }
                  : { r: 9 }
              }
            />

            {/* Thinking dots */}
            {state === 'thinking' && (
              <motion.g>
                <motion.circle
                  cx="140"
                  cy="68"
                  r="2"
                  fill="rgba(255,255,255,0.45)"
                  initial={false}
                  animate={{ opacity: [0, 1, 0], y: [0, -2, 0] }}
                  transition={{ duration: 1.2, repeat: Infinity }}
                />
                <motion.circle
                  cx="148"
                  cy="62"
                  r="2.5"
                  fill="rgba(255,255,255,0.38)"
                  initial={false}
                  animate={{ opacity: [0, 1, 0], y: [0, -2, 0] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.25 }}
                />
                <motion.circle
                  cx="156"
                  cy="56"
                  r="3"
                  fill="rgba(255,255,255,0.32)"
                  initial={false}
                  animate={{ opacity: [0, 1, 0], y: [0, -3, 0] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: 0.5 }}
                />
              </motion.g>
            )}
          </motion.g>

          {/* Sparkle star */}
          <motion.g
            animate={
              state === 'speaking'
                ? {
                    opacity: [0.4, 1, 0.4],
                    scale: [0.85, 1.15, 0.85],
                    transition: { duration: 0.5, repeat: Infinity },
                  }
                : state === 'sleeping'
                  ? {
                      opacity: [0.1, 0.2, 0.1],
                      scale: 0.8,
                      transition: {
                        duration: 4,
                        repeat: Infinity,
                        ease: 'easeInOut',
                      },
                    }
                  : {
                      opacity: [0.25, 0.6, 0.25],
                      scale: 1,
                      transition: {
                        duration: 3,
                        repeat: Infinity,
                        ease: 'easeInOut',
                      },
                    }
            }
            style={{ originX: '172px', originY: '172px' }}
          >
            <path
              d="M172 164 L174 170 L180 172 L174 174 L172 180 L170 174 L164 172 L170 170 Z"
              fill="rgba(255,255,255,0.75)"
            />
            <path
              d="M172 167 L173 170 L176 172 L173 174 L172 177 L171 174 L168 172 L171 170 Z"
              fill="rgba(255,255,255,0.9)"
            />
          </motion.g>
        </g>
      </svg>

      {/* ── Particles ── */}
      {showExtras && <AvatarParticles state={state} ringPx={ringPx} />}

      {/* ── Sleeping: crescent moon ── */}
      <AnimatePresence>
        {state === 'sleeping' && showExtras && (
          <motion.div
            key="moon"
            style={{
              position: 'absolute',
              top: -2 * glowScale,
              right: -2 * glowScale,
              pointerEvents: 'none',
            }}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: [0.5, 0.8, 0.5], y: [0, -2, 0], scale: 1 }}
            exit={{ opacity: 0, scale: 0.3, transition: { duration: 0.3 } }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <svg
              viewBox="0 0 16 16"
              width={Math.max(10, 14 * glowScale)}
              height={Math.max(10, 14 * glowScale)}
            >
              <path
                d="M9 2 A5 5 0 1 0 9 14 A3.8 3.8 0 1 1 9 2"
                fill="rgba(200,190,255,0.75)"
              />
            </svg>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Wake-up: sun flash ── */}
      <AnimatePresence>
        {wakePhase === 2 && showExtras && (
          <motion.div
            key="sun"
            style={{
              position: 'absolute',
              top: -2 * glowScale,
              right: -2 * glowScale,
              pointerEvents: 'none',
            }}
            initial={{ opacity: 0, scale: 0.3, rotate: -30 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            exit={{ opacity: 0, scale: 1.5, transition: { duration: 0.4 } }}
            transition={{ type: 'spring', stiffness: 300, damping: 15 }}
          >
            <svg
              viewBox="0 0 16 16"
              width={Math.max(10, 14 * glowScale)}
              height={Math.max(10, 14 * glowScale)}
            >
              <circle cx="8" cy="8" r="3" fill="rgba(255,255,255,0.9)" />
              {[0, 1, 2, 3, 4, 5, 6, 7].map(j => {
                const a = (j / 8) * Math.PI * 2;
                return (
                  <line
                    key={j}
                    x1={8 + Math.cos(a) * 4.5}
                    y1={8 + Math.sin(a) * 4.5}
                    x2={8 + Math.cos(a) * 6.5}
                    y2={8 + Math.sin(a) * 6.5}
                    stroke="rgba(255,255,255,0.65)"
                    strokeWidth="1"
                    strokeLinecap="round"
                  />
                );
              })}
            </svg>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
