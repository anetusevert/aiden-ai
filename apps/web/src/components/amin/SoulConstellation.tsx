'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SoulDimension } from '@/lib/apiClient';

interface SoulConstellationProps {
  dimensions: SoulDimension[];
  maturity: string;
  interactionCount: number;
  size?: number;
  showLabels?: boolean;
  interactive?: boolean;
}

const CATEGORY_RINGS: Record<string, number> = {
  identity: 0.3,
  style: 0.55,
  expertise: 0.8,
};

const CATEGORY_COLORS: Record<string, string> = {
  identity: 'rgba(255,255,255,0.92)',
  style: 'rgba(255,255,255,0.75)',
  expertise: 'rgba(255,255,255,0.6)',
};

const MATURITY_PARTICLES: Record<string, number> = {
  nascent: 3,
  forming: 5,
  developing: 7,
  established: 10,
  deep: 12,
};

function seededRandom(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

export function SoulConstellation({
  dimensions,
  maturity,
  interactionCount,
  size = 280,
  showLabels = true,
  interactive = true,
}: SoulConstellationProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size / 2 - 20;

  const nodes = useMemo(() => {
    const grouped: Record<string, SoulDimension[]> = {};
    for (const d of dimensions) {
      const cat = d.category || 'style';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(d);
    }

    return dimensions.map((d, i) => {
      const cat = d.category || 'style';
      const ring = CATEGORY_RINGS[cat] ?? 0.55;
      const siblings = grouped[cat] || [];
      const idx = siblings.indexOf(d);
      const spread = (2 * Math.PI) / Math.max(siblings.length, 1);
      const jitter = (seededRandom(i + 7) - 0.5) * 0.3;
      const angle = spread * idx + jitter + i * 0.1;
      const r = ring * maxR + (seededRandom(i + 3) - 0.5) * maxR * 0.08;

      return {
        ...d,
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        radius: 3 + d.confidence * 5,
        color: CATEGORY_COLORS[cat] ?? 'rgba(255,255,255,0.75)',
      };
    });
  }, [dimensions, cx, cy, maxR]);

  const edges = useMemo(() => {
    const result: {
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      opacity: number;
    }[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < maxR * 0.7) {
          const sameCategory = nodes[i].category === nodes[j].category;
          result.push({
            x1: nodes[i].x,
            y1: nodes[i].y,
            x2: nodes[j].x,
            y2: nodes[j].y,
            opacity: sameCategory ? 0.15 : 0.06,
          });
        }
      }
    }
    return result;
  }, [nodes, maxR]);

  const particleCount = MATURITY_PARTICLES[maturity] ?? 5;
  const selected = nodes.find(n => n.id === selectedId);

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <radialGradient id="soul-center-glow">
            <stop offset="0%" stopColor="rgba(255,255,255,0.25)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Concentric rings */}
        {Object.values(CATEGORY_RINGS).map((ring, i) => (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={ring * maxR}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}

        {/* Edges */}
        {edges.map((e, i) => (
          <line
            key={i}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="0.5"
            opacity={e.opacity}
          />
        ))}

        {/* Center hub */}
        <circle cx={cx} cy={cy} r={14} fill="url(#soul-center-glow)" />
        <circle
          cx={cx}
          cy={cy}
          r={8}
          fill="rgba(255,255,255,0.12)"
          stroke="rgba(255,255,255,0.35)"
          strokeWidth="1"
        />
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fontSize="9"
          fontWeight="700"
          fill="rgba(255,255,255,0.9)"
        >
          A
        </text>

        {/* Dimension nodes */}
        {nodes.map(n => (
          <g key={n.id}>
            <motion.circle
              cx={n.x}
              cy={n.y}
              r={n.radius}
              fill={n.color}
              opacity={n.confidence * 0.7 + 0.3}
              style={{ cursor: interactive ? 'pointer' : 'default' }}
              onClick={() =>
                interactive && setSelectedId(selectedId === n.id ? null : n.id)
              }
              animate={{
                cx: n.x + (seededRandom(n.id.length) - 0.5) * 2,
                cy: n.y + (seededRandom(n.id.length + 1) - 0.5) * 2,
              }}
              transition={{
                duration: 4 + seededRandom(n.id.length) * 2,
                repeat: Infinity,
                repeatType: 'reverse',
                ease: 'easeInOut',
              }}
            />
            {showLabels && n.radius > 4 && (
              <text
                x={n.x}
                y={n.y + n.radius + 10}
                textAnchor="middle"
                fontSize="7"
                fill="rgba(255,255,255,0.4)"
              >
                {n.label}
              </text>
            )}
          </g>
        ))}

        {/* Ambient particles */}
        {Array.from({ length: particleCount }).map((_, i) => {
          const angle = (i / particleCount) * Math.PI * 2;
          const r = maxR * (0.3 + seededRandom(i * 7) * 0.6);
          return (
            <motion.circle
              key={`p${i}`}
              cx={cx + Math.cos(angle) * r}
              cy={cy + Math.sin(angle) * r}
              r={1}
              fill="rgba(255,255,255,0.28)"
              animate={{
                cx: cx + Math.cos(angle + 0.2) * r,
                cy: cy + Math.sin(angle + 0.2) * r,
                opacity: [0.15, 0.4, 0.15],
              }}
              transition={{
                duration: 5 + i * 0.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          );
        })}
      </svg>

      {/* Selected node popover */}
      <AnimatePresence>
        {interactive && selected && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9 }}
            style={{
              position: 'absolute',
              left: Math.min(Math.max(selected.x - 80, 0), size - 170),
              top: Math.min(selected.y + selected.radius + 14, size - 70),
              background: 'rgba(20,24,36,0.95)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              padding: '8px 12px',
              width: 170,
              backdropFilter: 'blur(12px)',
              zIndex: 10,
            }}
          >
            <div
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: selected.color,
                marginBottom: 4,
              }}
            >
              {selected.label}
            </div>
            <div
              style={{
                fontSize: 10,
                color: 'rgba(255,255,255,0.5)',
                marginBottom: 6,
              }}
            >
              {selected.category}
            </div>
            <div
              style={{
                height: 4,
                borderRadius: 2,
                background: 'rgba(255,255,255,0.08)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${selected.value * 100}%`,
                  background: selected.color,
                  borderRadius: 2,
                }}
              />
            </div>
            <div
              style={{
                fontSize: 9,
                color: 'rgba(255,255,255,0.4)',
                marginTop: 3,
              }}
            >
              {selected.value < 0.33
                ? 'Low'
                : selected.value < 0.66
                  ? 'Moderate'
                  : 'High'}
              {' · '}
              Confidence: {Math.round(selected.confidence * 100)}%
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <div
        style={{
          position: 'absolute',
          bottom: -28,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 12,
          fontSize: 10,
          color: 'rgba(255,255,255,0.4)',
        }}
      >
        <span
          style={{
            padding: '2px 8px',
            borderRadius: 10,
            background: 'rgba(255,255,255,0.08)',
            border: '1px solid rgba(255,255,255,0.18)',
            color: 'rgba(255,255,255,0.85)',
            textTransform: 'capitalize',
          }}
        >
          {maturity}
        </span>
        <span>{interactionCount} interactions</span>
      </div>
    </div>
  );
}
