import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { CopilotKit } from "@copilotkit/react-core";
import { ReactNode } from "react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Documentation Helper Agent",
  description: "AI-powered documentation and coding assistant",
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotKit url="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
} 