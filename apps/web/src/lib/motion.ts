import type { Variants, Transition } from 'framer-motion';

/* ── Timing Tokens ── */
export const motionTokens = {
  duration: {
    instant: 0.08,
    fast: 0.14,
    base: 0.22,
    slow: 0.34,
    slower: 0.48,
    cinematic: 0.72,
  },
  ease: [0.2, 0.8, 0.2, 1] as [number, number, number, number],
  easeOut: [0.0, 0.0, 0.2, 1] as [number, number, number, number],
  easeIn: [0.4, 0.0, 1, 1] as [number, number, number, number],
  spring: {
    type: 'spring' as const,
    stiffness: 300,
    damping: 24,
    mass: 0.8,
  },
  springGentle: {
    type: 'spring' as const,
    stiffness: 200,
    damping: 20,
    mass: 1,
  },
  springBouncy: {
    type: 'spring' as const,
    stiffness: 400,
    damping: 22,
    mass: 0.6,
  },
};

/* ── Base Presets ── */
export const fadeUp = {
  initial: { opacity: 0, y: 12 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: motionTokens.ease,
      delay: 0.05,
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

export const fadeIn = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

export const scaleIn = {
  initial: { opacity: 0, scale: 0.92 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: motionTokens.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

/* ── Drawer / Panel ── for Amin side panel */
export const drawerMotion = {
  initial: { x: '100%', opacity: 0.6 },
  animate: { x: 0, opacity: 1, transition: motionTokens.spring },
  exit: {
    x: '100%',
    opacity: 0.5,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

/* ── Glass Reveal ── modals, panels, floating surfaces */
export const glassReveal = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: motionTokens.spring,
  },
  exit: {
    opacity: 0,
    scale: 0.97,
    y: 4,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

export const glassBackdrop = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

/* ── Tiles ── for card grids */
export const tileMotion = {
  initial: { opacity: 0, y: 12 },
  animate: (index = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: index * 0.04,
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  }),
  hover: { y: -3, scale: 1.012 },
  tap: { scale: 0.985 },
};

/* ── Staggered Reveal ── for lists, grids, navigation items */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.04, delayChildren: 0.08 },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
};

/* ── Route Transition ── page-level enter/exit */
export const routeTransition = {
  initial: { opacity: 0, y: 6, scale: 0.995 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: motionTokens.duration.slow,
      ease: motionTokens.ease,
    },
  },
  exit: {
    opacity: 0,
    y: -4,
    scale: 0.998,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

/* ── Ambient Pulse ── for floating button, indicators */
export const ambientPulse: Variants = {
  idle: {
    scale: [1, 1.04, 1],
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

export const aminBreathing: Variants = {
  idle: {
    scale: [1, 1.02, 1],
    transition: {
      duration: 4,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/* ── Avatar State Transitions ── */
export const avatarIdle: Transition = {
  duration: 4,
  repeat: Infinity,
  ease: 'easeInOut',
};

export const avatarSpeaking: Transition = {
  duration: 0.3,
  repeat: Infinity,
  repeatType: 'reverse',
  ease: 'easeInOut',
};

export const avatarThinking: Transition = {
  duration: 2,
  repeat: Infinity,
  ease: 'easeInOut',
};

/* ── Entry Sequence ── cinematic app boot */
export const entrySequence = {
  logo: {
    initial: { opacity: 0, scale: 0.7 },
    animate: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.8, ease: motionTokens.ease, delay: 0.2 },
    },
  },
  title: {
    initial: { opacity: 0, y: 12 },
    animate: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: motionTokens.ease, delay: 0.6 },
    },
  },
  subtitle: {
    initial: { opacity: 0 },
    animate: {
      opacity: 1,
      transition: { duration: 0.4, ease: motionTokens.ease, delay: 0.9 },
    },
  },
  progress: {
    initial: { scaleX: 0 },
    animate: {
      scaleX: 1,
      transition: {
        duration: 1.8,
        ease: [0.4, 0, 0.2, 1] as number[],
        delay: 0.4,
      },
    },
  },
  exit: {
    opacity: 0,
    scale: 1.02,
    transition: { duration: 0.4, ease: motionTokens.ease },
  },
};

/* ── Letter Reveal ── per-character stagger for brand text */
export const letterReveal: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: 0.3 + i * 0.06,
      duration: 0.4,
      ease: motionTokens.ease,
    },
  }),
};

/* ── Cinematic Sweep In ── for capability pills */
export const cinematicSweepIn: Variants = {
  hidden: { opacity: 0, x: -30 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: {
      delay: i * 0.12,
      duration: motionTokens.duration.slow,
      ease: motionTokens.ease,
    },
  }),
};

/* ── Dock Expand ── expand from floating button */
export const dockExpand = {
  initial: { opacity: 0, scale: 0.4, y: 40, x: 40 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    x: 0,
    transition: motionTokens.springBouncy,
  },
  exit: {
    opacity: 0,
    scale: 0.5,
    y: 30,
    x: 30,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
};

/* ── Message Enter ── chat message appearance */
export const messageEnter: Variants = {
  hidden: { opacity: 0, y: 12, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
};

/* ── Sidebar Nav Rail ── */
export const navRailContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.035, delayChildren: 0.15 },
  },
};

export const navRailItem: Variants = {
  hidden: { opacity: 0, x: -12 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: motionTokens.duration.base,
      ease: motionTokens.ease,
    },
  },
};

/* ── Voice Toggle ── */
export const voiceRingPulse: Variants = {
  off: { scale: 1, opacity: 0 },
  active: {
    scale: [1, 1.3, 1],
    opacity: [0.6, 0, 0.6],
    transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' },
  },
  passive: {
    scale: [1, 1.15, 1],
    opacity: [0.3, 0, 0.3],
    transition: { duration: 2.5, repeat: Infinity, ease: 'easeInOut' },
  },
};

/* ── Marketing Entry ── cinematic marketing splash */
export const goldLineExpand = {
  initial: { scaleX: 0, opacity: 0 },
  animate: {
    scaleX: 1,
    opacity: 1,
    transition: {
      duration: 0.8,
      ease: [0.22, 1, 0.36, 1] as number[],
      delay: 0.2,
    },
  },
};

export const marketingEntryExit = {
  opacity: 0,
  scale: 1.04,
  filter: 'blur(8px)',
  transition: { duration: 0.6, ease: motionTokens.ease },
};

export const heroFloatParticle: Variants = {
  animate: (i: number) => ({
    y: [0, -20 - i * 5, 0],
    x: [0, 8 + i * 3, 0],
    opacity: [0.15, 0.4, 0.15],
    transition: {
      duration: 6 + i * 2,
      repeat: Infinity,
      ease: 'easeInOut',
      delay: i * 0.8,
    },
  }),
};

export const scrollReveal: Variants = {
  hidden: { y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: motionTokens.duration.cinematic,
      ease: motionTokens.ease,
    },
  },
};

export const scrollStagger: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.15 },
  },
};

export const stepReveal: Variants = {
  hidden: { y: 30, scale: 0.97 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.15,
      duration: motionTokens.duration.slower,
      ease: motionTokens.ease,
    },
  }),
};

export const pillFade: Variants = {
  hidden: { scale: 0.9, y: 10 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      delay: 0.1 + i * 0.08,
      duration: motionTokens.duration.slow,
      ease: motionTokens.ease,
    },
  }),
};

/* ── Navigation Loader ── contextual page transition */
export const navigationLoader = {
  overlay: {
    initial: { opacity: 0 },
    animate: {
      opacity: 1,
      transition: { duration: 0.3, ease: motionTokens.ease },
    },
    exit: {
      opacity: 0,
      scale: 1.02,
      transition: { duration: 0.4, ease: motionTokens.ease },
    },
  },
  message: {
    initial: { opacity: 0, y: 8 },
    animate: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.4,
        ease: motionTokens.ease,
        delay: 0.2,
      },
    },
  },
  progress: {
    initial: { scaleX: 0 },
    animate: {
      scaleX: 1,
      transition: {
        duration: 2,
        ease: [0.4, 0, 0.2, 1] as number[],
        delay: 0.3,
      },
    },
  },
};

/* ── Marketing Page Transition ── scene change within marketing routes */
export const marketingPageTransition = {
  enter: {
    initial: {
      opacity: 0,
      y: 20,
      filter: 'blur(4px)',
    },
    animate: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: { duration: 0.6, ease: motionTokens.ease },
    },
  },
  exit: {
    opacity: 0,
    scale: 1.04,
    filter: 'blur(6px)',
    transition: { duration: 0.5, ease: motionTokens.ease },
  },
};
