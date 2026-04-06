import type { Metadata } from 'next';
import { IBM_Plex_Sans, Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/lib/AuthContext';
import { HtmlDirProvider } from '@/components/HtmlDirProvider';

// Premium typography: IBM Plex Sans for headings, Inter for body
const ibmPlexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-heading',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'HeyAmin — Legal intelligence',
  description:
    'HeyAmin — grounded legal workflows, workspace controls, and evidence-backed outputs.',
  icons: {
    icon: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${ibmPlexSans.variable} ${inter.variable}`}>
      <body>
        <AuthProvider>
          <HtmlDirProvider />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
