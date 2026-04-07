'use client';

import { useState, useEffect, useCallback } from 'react';
import { MarketingHeader } from '@/components/MarketingHeader';
import MarketingEntrySequence from '@/components/marketing/MarketingEntrySequence';
import { I18nProvider } from '@/components/I18nProvider';
import './heyamin-marketing.css';

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [showEntry, setShowEntry] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem('mkt-entry-seen')) {
      setShowEntry(true);
    }
  }, []);

  const handleEntryComplete = useCallback(() => {
    sessionStorage.setItem('mkt-entry-seen', '1');
    setShowEntry(false);
  }, []);

  return (
    <I18nProvider>
      <MarketingEntrySequence
        visible={showEntry}
        onComplete={handleEntryComplete}
      />
      <div
        className="ha-mkt"
        style={showEntry ? { opacity: 0, pointerEvents: 'none' } : undefined}
      >
        <MarketingHeader />
        <main>{children}</main>
      </div>
    </I18nProvider>
  );
}
