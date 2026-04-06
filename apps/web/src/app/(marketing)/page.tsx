'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import {
  motionTokens,
  cinematicSweepIn,
  scrollReveal,
  scrollStagger,
  stepReveal,
  pillFade,
  heroFloatParticle,
} from '@/lib/motion';

const features = [
  {
    icon: 'M9.663 17h4.674M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    title: 'Research with receipts',
    body: 'Every response ties back to sources you can inspect, verify, and cite with confidence.',
  },
  {
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
    title: 'Document intelligence',
    body: 'Upload contracts and policies. Amin reads, indexes, and surfaces what matters.',
  },
  {
    icon: 'M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z',
    title: 'Voice-ready',
    body: 'Speak naturally. Amin listens, understands context, and responds in real time.',
  },
  {
    icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z',
    title: 'Enterprise-grade security',
    body: 'Role-based access, audit trails, and data residency controls built for regulated industries.',
  },
];

const capabilities = [
  {
    label: 'Legal Research',
    icon: 'M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z',
  },
  {
    label: 'Document Analysis',
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  },
  {
    label: 'Voice-Ready',
    icon: 'M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z',
  },
];

const steps = [
  {
    num: '01',
    title: 'Ask',
    body: 'Type or speak your question. Amin understands legal context natively.',
  },
  {
    num: '02',
    title: 'Amin researches',
    body: 'Cross-references statutes, precedent, and your uploaded documents in seconds.',
  },
  {
    num: '03',
    title: 'Verified answers',
    body: 'Every response cites its sources. Inspect, verify, and export with confidence.',
  },
];

const trustBadges = [
  'End-to-end encryption',
  'Audit trails',
  'Role-based access',
  'Data residency controls',
  'SOC 2 aligned',
];

export default function MarketingHomePage() {
  return (
    <>
      {/* ── Hero ── split layout with floating particles */}
      <section className="ha-hero ha-hero-split">
        {/* Background particles */}
        <div className="ha-hero-particles" aria-hidden>
          {[0, 1, 2, 3, 4].map(i => (
            <motion.div
              key={i}
              className="ha-hero-particle"
              variants={heroFloatParticle}
              animate="animate"
              custom={i}
              style={{
                left: `${15 + i * 17}%`,
                top: `${20 + (i % 3) * 25}%`,
                width: 3 + i * 0.5,
                height: 3 + i * 0.5,
              }}
            />
          ))}
        </div>

        <div className="ha-glow" aria-hidden />

        <div className="ha-hero-inner ha-hero-row">
          {/* Left: Copy */}
          <div className="ha-hero-text">
            <motion.p
              className="ha-eyebrow"
              initial={{ y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.05 }}
            >
              HeyAmin
            </motion.p>

            <motion.h1
              initial={{ y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.6,
                delay: 0.15,
                ease: motionTokens.ease,
              }}
            >
              Legal intelligence,{' '}
              <span className="ha-accent">built for how you work.</span>
            </motion.h1>

            <motion.p
              className="ha-hero-sub"
              initial={{ y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              Grounded answers, clear citations, and workspace controls — in one
              seamless experience powered by Amin, your AI legal assistant.
            </motion.p>

            <motion.div
              className="ha-cta-row"
              initial={{ y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.42 }}
            >
              <Link href="/login" className="ha-btn-primary">
                Get started
              </Link>
              <a href="#meet-amin" className="ha-btn-ghost">
                Meet Amin &darr;
              </a>
            </motion.div>
          </div>

          {/* Right: Avatar */}
          <motion.div
            className="ha-hero-avatar"
            initial={{ scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: 0.9,
              ease: [0.22, 1, 0.36, 1],
              delay: 0.25,
            }}
          >
            <div className="ha-hero-avatar-glow" aria-hidden />
            <AminAvatar size={200} state="idle" showWaveform={false} />
          </motion.div>
        </div>
      </section>

      {/* ── Meet Amin ── */}
      <section className="ha-section ha-meet-section" id="meet-amin">
        <div className="ha-section-inner ha-meet-inner">
          <motion.div
            className="ha-meet-avatar"
            initial={{ scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <AminAvatar size={96} state="idle" showWaveform={false} />
          </motion.div>

          <motion.h2
            className="ha-meet-heading"
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.5 }}
          >
            Meet <span className="ha-accent">Amin</span>
          </motion.h2>

          <motion.p
            className="ha-meet-body"
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.5 }}
          >
            Your AI legal assistant, purpose-built for professional workflows.
            Amin researches statutes, analyses documents, and delivers answers
            grounded in verifiable sources — so you can focus on what matters.
          </motion.p>

          <motion.div
            className="ha-meet-caps"
            variants={scrollStagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
          >
            {capabilities.map((cap, i) => (
              <motion.div
                key={cap.label}
                className="ha-meet-pill"
                variants={cinematicSweepIn}
                custom={i}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={cap.icon} />
                </svg>
                <span>{cap.label}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section className="ha-section" id="capabilities">
        <div className="ha-section-inner">
          <motion.h2
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.4 }}
          >
            Everything you need, nothing you don&rsquo;t
          </motion.h2>

          <div className="ha-grid">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                className="ha-tile"
                initial={{ y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.5,
                  delay: i * 0.1,
                  ease: motionTokens.ease,
                }}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
              >
                <div className="ha-tile-icon">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d={f.icon} />
                  </svg>
                </div>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="ha-section ha-steps-section">
        <div className="ha-section-inner">
          <motion.h2
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.4 }}
          >
            How it works
          </motion.h2>

          <div className="ha-steps">
            {/* Connecting line */}
            <div className="ha-steps-line" aria-hidden />

            {steps.map((step, i) => (
              <motion.div
                key={step.num}
                className="ha-step"
                variants={stepReveal}
                custom={i}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.3 }}
              >
                <span className="ha-step-num">{step.num}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Trust / Social Proof ── */}
      <section className="ha-section ha-trust-section">
        <div className="ha-section-inner">
          <motion.h2
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.4 }}
          >
            Built for teams that cannot afford guesswork
          </motion.h2>

          <motion.p
            className="ha-trust-sub"
            variants={scrollReveal}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.4 }}
          >
            Enterprise-ready from day one. Security and compliance are not
            afterthoughts — they&rsquo;re foundational.
          </motion.p>

          <motion.div
            className="ha-trust-pills"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
          >
            {trustBadges.map((badge, i) => (
              <motion.span
                key={badge}
                className="ha-trust-pill"
                variants={pillFade}
                custom={i}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 13l4 4L19 7" />
                </svg>
                {badge}
              </motion.span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="ha-footer ha-footer-full">
        <div className="ha-footer-inner">
          <div className="ha-footer-brand">
            <HeyAminLogo variant="mark" size={48} />
            <p className="ha-footer-tagline">
              Professional legal intelligence.
            </p>
          </div>
          <Link href="/login" className="ha-btn-primary ha-btn-sm">
            Sign in
          </Link>
        </div>
        <div className="ha-footer-rule" />
        <p className="ha-footer-copy">
          &copy; {new Date().getFullYear()} HeyAmin. All rights reserved.
        </p>
      </footer>
    </>
  );
}
