import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { CopilotProvider } from '@/providers/CopilotProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Documentation Helper',
  description: 'AI-powered documentation & coding assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotProvider>
          {children}
        </CopilotProvider>
      </body>
    </html>
  );
} 