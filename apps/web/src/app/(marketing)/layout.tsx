import { MarketingHeader } from '@/components/MarketingHeader';
import './heyamin-marketing.css';

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="ha-mkt">
      <MarketingHeader />
      <main>{children}</main>
    </div>
  );
}
