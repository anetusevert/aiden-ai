import Link from 'next/link';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';

export function MarketingFooter() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mkt-footer">
      <div className="mkt-footer-inner">
        <div className="mkt-footer-brand">
          <div
            className="mkt-footer-logo"
            style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            <HeyAminLogo variant="mark" size={28} />
            <span>HeyAmin</span>
          </div>
          <p className="mkt-footer-tagline">
            Professional-grade AI for legal work.
          </p>
        </div>

        <div className="mkt-footer-links">
          <div className="mkt-footer-col">
            <h4 className="mkt-footer-heading">Platform</h4>
            <Link href="/login" className="mkt-footer-link">
              Sign In
            </Link>
            <Link href="/setup" className="mkt-footer-link">
              Create Workspace
            </Link>
          </div>
          <div className="mkt-footer-col">
            <h4 className="mkt-footer-heading">Capabilities</h4>
            <span className="mkt-footer-link">Legal Research</span>
            <span className="mkt-footer-link">Contract Review</span>
            <span className="mkt-footer-link">Clause Redlines</span>
          </div>
          <div className="mkt-footer-col">
            <h4 className="mkt-footer-heading">Security</h4>
            <span className="mkt-footer-link">Audit Logs</span>
            <span className="mkt-footer-link">Workspace Isolation</span>
            <span className="mkt-footer-link">Access Controls</span>
          </div>
        </div>

        <div className="mkt-footer-bottom">
          <p className="mkt-footer-copyright">
            © {currentYear} HeyAmin. All rights reserved.
          </p>
          <p className="mkt-footer-note">
            Enterprise legal intelligence platform.
          </p>
        </div>
      </div>
    </footer>
  );
}
