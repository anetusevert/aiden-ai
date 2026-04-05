'use client';

import { MarketingHeader } from '@/components/MarketingHeader';
import { I18nProvider } from '@/components/I18nProvider';
import './heyamin-marketing.css';

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <I18nProvider>
      <div className="ha-mkt">
        <MarketingHeader />
        <main>{children}</main>
      </div>
    </I18nProvider>
  );
}
