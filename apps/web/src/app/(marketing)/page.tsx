'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import { prestige } from '@/lib/motion';

const firms = [
  'Al Tamimi & Company',
  'Baker McKenzie',
  'King & Spalding',
  'Latham & Watkins',
  'White & Case',
  'DLA Piper',
];

const features = [
  {
    eyebrow: 'CASE MANAGEMENT',
    headline: 'Every case. Every client. Every detail.',
    body: 'Manage your entire practice from one place. Amin knows every document, every deadline, and every step of every matter — so nothing falls through the cracks.',
    visual: 'Case Detail',
  },
  {
    eyebrow: 'LEGAL RESEARCH',
    headline: 'Research that compounds.',
    body: 'Unlike generic AI, Amin builds a persistent legal wiki from every source it reads. Royal Decrees, court circulars, regulatory updates — synthesised and cross-referenced automatically.',
    visual: 'Legal Wiki',
    reverse: true,
  },
  {
    eyebrow: 'DOCUMENT WIZARD',
    headline: 'Draft. Edit. File. All in Amin.',
    body: 'From Statement of Claim to NDA, Amin drafts, refines and edits live documents in Word, Excel and PowerPoint. Collabora-powered editing, AI-guided content.',
    visual: 'Document Editor',
  },
];

export default function MarketingHomePage() {
  return (
    <>
      {/* ── Hero ── */}
      <section className="ha-hero">
        <div className="ha-hero-inner">
          <motion.div
            className="ha-eyebrow"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <span className="ha-eyebrow-dot" />
            Legal Intelligence for the GCC
          </motion.div>

          <h1>
            <div style={{ overflow: 'hidden' }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              >
                The AI platform
              </motion.div>
            </div>
            <div style={{ overflow: 'hidden' }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.7,
                  ease: [0.16, 1, 0.3, 1],
                  delay: 0.15,
                }}
              >
                built for lawyers.
              </motion.div>
            </div>
          </h1>

          <motion.p
            className="ha-hero-sub"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            Amin understands GCC law. Every workflow, every jurisdiction, every
            matter — guided by AI that thinks like a lawyer.
          </motion.p>

          <motion.div
            className="ha-cta-row"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.55 }}
          >
            <Link href="/auth/register" className="ha-btn-primary">
              Get Started
            </Link>
            <a href="#platform" className="ha-btn-secondary">
              See how it works
            </a>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <div className="ha-scroll-indicator" />
      </section>

      {/* ── Social Proof ── */}
      <section className="ha-social-proof">
        <p className="ha-social-proof-label">
          Trusted by leading law practices across the GCC
        </p>
        <div className="ha-social-proof-row">
          {firms.map(name => (
            <span key={name} className="ha-social-proof-name">
              {name}
            </span>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="ha-section" id="platform">
        <div className="ha-section-inner">
          {features.map((feat, i) => (
            <motion.div
              key={feat.eyebrow}
              className={`ha-feature-block${feat.reverse ? ' reverse' : ''}`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{
                duration: 0.6,
                ease: [0.16, 1, 0.3, 1],
                delay: i * 0.1,
              }}
            >
              <div className="ha-feature-text">
                <p className="ha-feature-eyebrow">{feat.eyebrow}</p>
                <h3 className="ha-feature-headline">{feat.headline}</h3>
                <p className="ha-feature-body">{feat.body}</p>
              </div>
              <div className="ha-feature-visual">
                <div className="ha-feature-visual-placeholder">
                  {feat.visual}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="ha-final-cta">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <h2>Ready to transform your practice?</h2>
          <p className="ha-final-cta-sub">
            Join GCC lawyers who run their entire practice with HeyAmin.
          </p>
          <Link
            href="/auth/register"
            className="ha-btn-primary"
            style={{ height: 48, padding: '0 32px' }}
          >
            Request Access
          </Link>
          <p className="ha-final-cta-languages">
            Available in English, Arabic, French, Urdu and Filipino
          </p>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="ha-footer">
        <div className="ha-footer-brand">
          <HeyAminLogo variant="mark" size={24} />
          <span>HeyAmin</span>
        </div>
        <p>&copy; {new Date().getFullYear()} HeyAmin. All rights reserved.</p>
        <div className="ha-footer-links">
          <a href="/privacy" className="ha-footer-link">
            Privacy
          </a>
          <a href="/terms" className="ha-footer-link">
            Terms
          </a>
          <a href="/security" className="ha-footer-link">
            Security
          </a>
        </div>
      </footer>
    </>
  );
}
