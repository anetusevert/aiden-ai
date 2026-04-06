import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import './globals.css';
import { AuthProvider } from '@/lib/AuthContext';
import { HtmlDirProvider } from '@/components/HtmlDirProvider';

export const metadata: Metadata = {
  title: 'HeyAmin — Legal intelligence',
  description:
    'HeyAmin — grounded legal workflows, workspace controls, and evidence-backed outputs.',
  icons: {
    icon: '/brand/heyamin-logo-mark.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body>
        <AuthProvider>
          <HtmlDirProvider />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
