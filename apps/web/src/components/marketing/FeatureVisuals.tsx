'use client';

import { motion } from 'framer-motion';

const LINE_EASE = [0.16, 1, 0.3, 1] as const;

/* ─────────────────────────────────────────────
   Case Management — animated case card
   ───────────────────────────────────────────── */

const statusBadges = [
  { label: 'Active', color: '#22c55e' },
  { label: 'Priority', color: '#f59e0b' },
  { label: 'Review', color: '#3b82f6' },
];

const timelineDots = [0, 1, 2, 3, 4];

export function CaseCardVisual() {
  return (
    <motion.div
      className="fv-case-card"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.4 }}
    >
      {/* Card chrome */}
      <div className="fv-card-chrome">
        <motion.div
          className="fv-card-header"
          variants={{
            hidden: { opacity: 0, y: 8 },
            visible: {
              opacity: 1,
              y: 0,
              transition: { duration: 0.5, ease: LINE_EASE },
            },
          }}
        >
          <div className="fv-card-icon" />
          <div>
            <div className="fv-card-title-line" />
            <div className="fv-card-subtitle-line" />
          </div>
        </motion.div>

        {/* Status badges */}
        <div className="fv-badges">
          {statusBadges.map((b, i) => (
            <motion.span
              key={b.label}
              className="fv-badge"
              style={
                {
                  '--badge-color': b.color,
                } as React.CSSProperties
              }
              variants={{
                hidden: { opacity: 0, scale: 0.7 },
                visible: {
                  opacity: 1,
                  scale: 1,
                  transition: {
                    duration: 0.4,
                    ease: LINE_EASE,
                    delay: 0.3 + i * 0.1,
                  },
                },
              }}
            >
              {b.label}
            </motion.span>
          ))}
        </div>

        {/* Info rows */}
        {[0, 1, 2].map(i => (
          <motion.div
            key={i}
            className="fv-info-row"
            variants={{
              hidden: { opacity: 0, x: -10 },
              visible: {
                opacity: 1,
                x: 0,
                transition: {
                  duration: 0.4,
                  ease: LINE_EASE,
                  delay: 0.5 + i * 0.08,
                },
              },
            }}
          >
            <div className="fv-info-label" />
            <div
              className="fv-info-value"
              style={{ width: `${60 + i * 12}%` }}
            />
          </motion.div>
        ))}

        {/* Timeline */}
        <motion.div
          className="fv-timeline"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { duration: 0.3, delay: 0.7 },
            },
          }}
        >
          <div className="fv-timeline-track" />
          {timelineDots.map(i => (
            <motion.div
              key={i}
              className="fv-timeline-dot"
              style={{ left: `${i * 25}%` }}
              variants={{
                hidden: { scale: 0 },
                visible: {
                  scale: 1,
                  transition: {
                    duration: 0.3,
                    ease: LINE_EASE,
                    delay: 0.8 + i * 0.08,
                  },
                },
              }}
            />
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Legal Research — animated knowledge graph
   ───────────────────────────────────────────── */

const graphNodes = [
  { x: 50, y: 20, r: 18, label: 'Law' },
  { x: 20, y: 50, r: 14, label: 'Art. 5' },
  { x: 80, y: 45, r: 14, label: 'Reg.' },
  { x: 35, y: 80, r: 12, label: 'Case' },
  { x: 65, y: 78, r: 12, label: 'Ref.' },
  { x: 10, y: 25, r: 10, label: '' },
  { x: 90, y: 22, r: 10, label: '' },
];

const graphEdges = [
  [0, 1],
  [0, 2],
  [1, 3],
  [2, 4],
  [3, 4],
  [0, 5],
  [0, 6],
  [1, 2],
];

export function KnowledgeGraphVisual() {
  return (
    <motion.div
      className="fv-graph"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.4 }}
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
        className="fv-graph-svg"
      >
        {/* Edges */}
        {graphEdges.map(([a, b], i) => (
          <motion.line
            key={`e-${i}`}
            x1={graphNodes[a].x}
            y1={graphNodes[a].y}
            x2={graphNodes[b].x}
            y2={graphNodes[b].y}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={0.4}
            variants={{
              hidden: { pathLength: 0, opacity: 0 },
              visible: {
                pathLength: 1,
                opacity: 1,
                transition: {
                  duration: 0.8,
                  ease: LINE_EASE,
                  delay: 0.2 + i * 0.06,
                },
              },
            }}
          />
        ))}

        {/* Nodes */}
        {graphNodes.map((n, i) => (
          <motion.g key={`n-${i}`}>
            <motion.circle
              cx={n.x}
              cy={n.y}
              r={n.r}
              fill="rgba(255,255,255,0.04)"
              stroke="rgba(255,255,255,0.15)"
              strokeWidth={0.5}
              variants={{
                hidden: { scale: 0, opacity: 0 },
                visible: {
                  scale: 1,
                  opacity: 1,
                  transition: {
                    duration: 0.5,
                    ease: LINE_EASE,
                    delay: 0.4 + i * 0.08,
                  },
                },
              }}
            />
            {n.label && (
              <motion.text
                x={n.x}
                y={n.y + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="rgba(255,255,255,0.5)"
                fontSize={3.5}
                fontWeight={500}
                variants={{
                  hidden: { opacity: 0 },
                  visible: {
                    opacity: 1,
                    transition: { duration: 0.3, delay: 0.6 + i * 0.08 },
                  },
                }}
              >
                {n.label}
              </motion.text>
            )}
          </motion.g>
        ))}
      </svg>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Document Wizard — animated editor mockup
   ───────────────────────────────────────────── */

const toolbarIcons = ['B', 'I', 'U', 'H1', '¶', '⊞'];
const docLines = [
  { width: '85%', delay: 0.5 },
  { width: '72%', delay: 0.6 },
  { width: '90%', delay: 0.7 },
  { width: '55%', delay: 0.8 },
  { width: '78%', delay: 0.9 },
  { width: '65%', delay: 1.0 },
];

export function DocumentEditorVisual() {
  return (
    <motion.div
      className="fv-editor"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.4 }}
    >
      {/* Toolbar */}
      <motion.div
        className="fv-editor-toolbar"
        variants={{
          hidden: { opacity: 0, y: -6 },
          visible: {
            opacity: 1,
            y: 0,
            transition: { duration: 0.4, ease: LINE_EASE },
          },
        }}
      >
        {toolbarIcons.map((icon, i) => (
          <motion.span
            key={icon}
            className="fv-toolbar-btn"
            variants={{
              hidden: { opacity: 0, scale: 0.6 },
              visible: {
                opacity: 1,
                scale: 1,
                transition: {
                  duration: 0.3,
                  ease: LINE_EASE,
                  delay: 0.15 + i * 0.05,
                },
              },
            }}
          >
            {icon}
          </motion.span>
        ))}
      </motion.div>

      {/* Doc body */}
      <div className="fv-editor-body">
        {docLines.map((line, i) => (
          <motion.div
            key={i}
            className="fv-doc-line"
            style={{ width: line.width }}
            variants={{
              hidden: { opacity: 0, scaleX: 0 },
              visible: {
                opacity: 1,
                scaleX: 1,
                transition: {
                  duration: 0.5,
                  ease: LINE_EASE,
                  delay: line.delay,
                },
              },
            }}
          />
        ))}

        {/* Typing cursor */}
        <motion.div
          className="fv-cursor"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: [0, 1, 0],
              transition: {
                duration: 1,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: 1.2,
              },
            },
          }}
        />
      </div>
    </motion.div>
  );
}
