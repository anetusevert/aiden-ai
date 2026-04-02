'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';

const features = [
  {
    title: 'Research with receipts',
    body: 'Every response ties back to sources you can inspect and verify.',
  },
  {
    title: 'Your workspace, your rules',
    body: 'Organisations, roles, and audit trails designed for professional use.',
  },
  {
    title: 'Fast, focused UI',
    body: 'A calm, high-contrast surface that stays out of your way.',
  },
];

export default function MarketingHomePage() {
  return (
    <>
      {/* ── Hero ── */}
      <section className="ha-hero">
        <div className="ha-hero-inner">
          <motion.p
            className="ha-eyebrow"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.05 }}
          >
            HeyAmin
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.15 }}
          >
            Legal intelligence,{' '}
            <span className="ha-accent">built for how you work.</span>
          </motion.h1>

          <motion.p
            className="ha-hero-sub"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
          >
            Grounded answers, clear citations, and workspace controls — in one
            HeyAmin Cloud experience.
          </motion.p>

          <motion.div
            className="ha-cta-row"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.38 }}
          >
            <Link href="/login" className="ha-btn-primary">
              Sign in
            </Link>
            <a href="#capabilities" className="ha-btn-ghost">
              Explore capabilities &darr;
            </a>
          </motion.div>
        </div>

        <div className="ha-glow" aria-hidden />
      </section>

      {/* ── Feature tiles ── */}
      <section className="ha-section" id="capabilities">
        <div className="ha-section-inner">
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.5 }}
          >
            Built for teams that cannot afford guesswork
          </motion.h2>

          <div className="ha-grid">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                className="ha-tile"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.45, delay: i * 0.08 }}
              >
                <h3>{f.title}</h3>
                <p>{f.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="ha-footer">
        <p>
          Hey<span className="ha-accent">Amin</span> — professional legal
          workflows.
        </p>
      </footer>
    </>
  );
}
