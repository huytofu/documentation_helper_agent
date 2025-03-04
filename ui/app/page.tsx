"use client";

import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MessageSquare } from "lucide-react";

type ProgrammingLanguage = "Python" | "JavaScript" | "TypeScript" | "Java" | "C++" | "C#" | "Go" | "Rust" | "Ruby" | "PHP";

export default function Home() {
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguage | "">("");

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="space-y-8">
        <div className="space-y-2 text-center">
          <h1 className="text-4xl font-bold tracking-tight">Documentation Helper Agent</h1>
          <p className="text-muted-foreground">
            Your AI-powered assistant for programming documentation and implementation
          </p>
        </div>

        <div className="space-y-6">
          <LanguageSelector
            selectedLanguage={selectedLanguage}
            onLanguageChange={setSelectedLanguage}
          />

          <div className="relative rounded-lg border bg-card text-card-foreground shadow-sm">
            <div className="flex items-center gap-2 p-4 border-b">
              <MessageSquare className="h-4 w-4" />
              <h2 className="text-lg font-semibold">Chat Interface</h2>
            </div>
            <div className="h-[600px]">
              <CopilotChat
                className="h-full"
                makeSystemMessage={() => 
                  `You are a helpful assistant focusing on ${selectedLanguage || "programming"} development. Help users with their coding questions and documentation needs. When providing code examples or implementation guidance, use ${selectedLanguage || "programming"} as the primary language.`
                }
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 