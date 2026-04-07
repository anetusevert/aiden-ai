'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import {
  CaseCardVisual,
  KnowledgeGraphVisual,
  DocumentEditorVisual,
} from '@/components/marketing/FeatureVisuals';

const EASE = [0.16, 1, 0.3, 1] as const;

const features = [
  {
    eyebrow: 'CASE MANAGEMENT',
    headline: 'Every case. Every client. Every detail.',
    body: 'Manage your entire practice from one place. Amin knows every document, every deadline, and every step of every matter — so nothing falls through the cracks.',
    Visual: CaseCardVisual,
  },
  {
    eyebrow: 'LEGAL RESEARCH',
    headline: 'Research that compounds.',
    body: 'Unlike generic AI, Amin builds a persistent legal wiki from every source it reads. Royal Decrees, court circulars, regulatory updates — synthesised and cross-referenced automatically.',
    Visual: KnowledgeGraphVisual,
    reverse: true,
  },
  {
    eyebrow: 'DOCUMENT WIZARD',
    headline: 'Draft. Edit. File. All in Amin.',
    body: 'From Statement of Claim to NDA, Amin drafts, refines and edits live documents in Word, Excel and PowerPoint. Collabora-powered editing, AI-guided content.',
    Visual: DocumentEditorVisual,
  },
];

const securityFeatures = [
  {
    icon: '🔒',
    title: 'Workspace Isolation',
    desc: 'Every firm gets a fully isolated workspace. Zero data co-mingling, ever.',
  },
  {
    icon: '📋',
    title: 'Audit Logs',
    desc: 'Comprehensive audit trail for every action — searchable, exportable, immutable.',
  },
  {
    icon: '🛡️',
    title: 'End-to-End Encryption',
    desc: 'AES-256 at rest, TLS 1.3 in transit. Your data never leaves unencrypted.',
  },
  {
    icon: '✓',
    title: 'Compliance-Ready',
    desc: 'Built for DIFC, ADGM, and GCC regulatory frameworks from day one.',
  },
  {
    icon: '🔑',
    title: 'Role-Based Access',
    desc: 'Granular permissions per user, per matter, per document. Full control.',
  },
  {
    icon: '☁️',
    title: 'Private Cloud',
    desc: 'Hosted in MENA-region data centres. Your data stays in jurisdiction.',
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
                transition={{ duration: 0.7, ease: EASE }}
              >
                The AI platform
              </motion.div>
            </div>
            <div style={{ overflow: 'hidden' }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, ease: EASE, delay: 0.15 }}
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
            <Link href="/login" className="ha-btn-primary">
              Get Started
            </Link>
            <a href="#platform" className="ha-btn-secondary">
              See how it works
            </a>
          </motion.div>
        </div>

        <div className="ha-scroll-indicator" />
      </section>

      {/* ── Platform / Features ── */}
      <section className="ha-section" id="platform">
        <div className="ha-section-inner">
          <motion.h2
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{ duration: 0.5, ease: EASE }}
          >
            One platform. Every legal workflow.
          </motion.h2>

          {features.map((feat, i) => (
            <motion.div
              key={feat.eyebrow}
              className={`ha-feature-block${feat.reverse ? ' reverse' : ''}`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.6, ease: EASE, delay: i * 0.1 }}
            >
              <div className="ha-feature-text">
                <p className="ha-feature-eyebrow">{feat.eyebrow}</p>
                <h3 className="ha-feature-headline">{feat.headline}</h3>
                <p className="ha-feature-body">{feat.body}</p>
              </div>
              <div className="ha-feature-visual">
                <feat.Visual />
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Research ── */}
      <section className="ha-section ha-section-alt" id="research">
        <div className="ha-section-inner">
          <motion.div
            className="ha-research-header"
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.6, ease: EASE }}
          >
            <p className="ha-feature-eyebrow" style={{ textAlign: 'center' }}>
              RESEARCH ENGINE
            </p>
            <h2>Legal knowledge that never sleeps.</h2>
            <p
              className="ha-hero-sub"
              style={{ maxWidth: 560, margin: '0 auto' }}
            >
              Amin continuously ingests primary sources from every GCC
              jurisdiction — royal decrees, court circulars, gazette
              publications, and regulatory updates — so your research is always
              current.
            </p>
          </motion.div>

          <div className="ha-stats-row">
            {[
              { value: '6', label: 'GCC Jurisdictions' },
              { value: '50k+', label: 'Legal Sources' },
              { value: '24/7', label: 'Continuous Updates' },
              { value: '<2s', label: 'Query Response' },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                className="ha-stat-card"
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 0.5, ease: EASE, delay: 0.2 + i * 0.1 }}
              >
                <span className="ha-stat-value">{stat.value}</span>
                <span className="ha-stat-label">{stat.label}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ── */}
      <section className="ha-section" id="security">
        <div className="ha-section-inner">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.6, ease: EASE }}
          >
            <p className="ha-feature-eyebrow" style={{ textAlign: 'center' }}>
              ENTERPRISE SECURITY
            </p>
            <h2>Built for the most demanding firms.</h2>
          </motion.div>

          <div className="ha-security-grid">
            {securityFeatures.map((feat, i) => (
              <motion.div
                key={feat.title}
                className="ha-security-card"
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.5,
                  ease: EASE,
                  delay: 0.15 + i * 0.07,
                }}
              >
                <span className="ha-security-icon">{feat.icon}</span>
                <h4 className="ha-security-title">{feat.title}</h4>
                <p className="ha-security-desc">{feat.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── About ── */}
      <section className="ha-section ha-section-about" id="about">
        <div className="ha-section-inner">
          <motion.div
            className="ha-about-content"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.7, ease: EASE }}
          >
            <p className="ha-feature-eyebrow" style={{ textAlign: 'center' }}>
              OUR MISSION
            </p>
            <h2 className="ha-about-headline">
              Built in the Gulf.
              <br />
              Built for the Gulf.
            </h2>
            <p className="ha-about-body">
              HeyAmin was created by lawyers and engineers who understand the
              unique complexity of GCC legal practice — multi-jurisdictional
              matters, Arabic-first documentation, Sharia-informed commercial
              law, and the speed at which the region evolves.
            </p>
            <p className="ha-about-body">
              We believe legal technology should not be an afterthought bolted
              onto Western platforms. It should be purpose-built, deeply
              contextual, and respectful of the traditions and languages of the
              region it serves.
            </p>
            <motion.div
              className="ha-about-divider"
              initial={{ scaleX: 0 }}
              whileInView={{ scaleX: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, ease: EASE, delay: 0.3 }}
            />
            <p className="ha-about-philosophy">
              &ldquo;Technology should amplify expertise, not replace it.&rdquo;
            </p>
          </motion.div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="ha-final-cta">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          <h2>Ready to transform your practice?</h2>
          <p className="ha-final-cta-sub">
            Join GCC lawyers who run their entire practice with HeyAmin.
          </p>
          <Link
            href="/login"
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
          <a href="#security" className="ha-footer-link">
            Security
          </a>
        </div>
      </footer>
    </>
  );
}
