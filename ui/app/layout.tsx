import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { CopilotKit } from "@copilotkit/react-core";
import { ReactNode } from "react";
import { Header } from "@/components/Header";

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
    <html lang="en" className="h-full">
      <body className={`${inter.className} min-h-full bg-background`}>
        <CopilotKit url={process.env.NEXT_PUBLIC_COPILOT_URL || "/api/copilotkit"}>
          <div className="relative flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
          </div>
        </CopilotKit>
      </body>
    </html>
  );
} 