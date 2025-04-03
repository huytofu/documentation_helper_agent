'use client';

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { CopilotKit } from '@copilotkit/react-core';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Documentation Helper',
  description: 'AI-powered documentation assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
} 