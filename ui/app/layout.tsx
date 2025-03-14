"use client";

import { Inter } from "next/font/google";
import "./globals.css";
import { CopilotKit } from "@copilotkit/react-core";
import { ReactNode, useState, createContext, useContext } from "react";
import { Header } from "@/components/Header";
import "@copilotkit/react-ui/styles.css";
import { ProgrammingLanguage } from "@/types";
import { AGENT_NAME, API_ENDPOINT } from "@/constants";

const inter = Inter({ subsets: ["latin"] });

interface RootLayoutProps {
  children: ReactNode;
}

// Create a context for the programming language
export const LanguageContext = createContext<{
  selectedLanguage: ProgrammingLanguage | "";
  setSelectedLanguage: (language: ProgrammingLanguage | "") => void;
}>({
  selectedLanguage: "",
  setSelectedLanguage: () => {},
});

export default function RootLayout({ children }: RootLayoutProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguage | "">("");

  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} min-h-full bg-background relative`}>
        <div className="absolute inset-0 bg-grid-white/[0.02] -z-10" />
        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/10 to-transparent -z-10" />
        <div className="absolute inset-0 border-4 border-blue-500/20 rounded-3xl m-4 -z-10" />
        <LanguageContext.Provider value={{ selectedLanguage, setSelectedLanguage }}>
          <CopilotKit 
            runtimeUrl={API_ENDPOINT}
            agent={AGENT_NAME}
            // properties={{
            //   language: selectedLanguage,
            // }}
          >
            <div className="relative flex min-h-screen flex-col">
              <Header />
              <main className="flex-1">{children}</main>
            </div>
          </CopilotKit>
        </LanguageContext.Provider>
      </body>
    </html>
  );
} 