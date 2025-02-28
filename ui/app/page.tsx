"use client";

import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

const PROGRAMMING_LANGUAGES = [
  "Python",
  "JavaScript",
  "TypeScript",
  "Java",
  "C++",
  "C#",
  "Go",
  "Rust",
  "Ruby",
  "PHP",
] as const;

type ProgrammingLanguage = typeof PROGRAMMING_LANGUAGES[number];

export default function Home() {
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguage | "">("");

  return (
    <main className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-4xl font-bold mb-8 text-center">Documentation Helper Agent</h1>
      
      <div className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="language">Programming Language</Label>
          <Select
            value={selectedLanguage}
            onChange={(value) => setSelectedLanguage(value as ProgrammingLanguage)}
            options={PROGRAMMING_LANGUAGES.map(lang => ({
              label: lang,
              value: lang,
            }))}
            placeholder="Select a programming language"
          />
        </div>

        <div className="h-[600px] border rounded-lg overflow-hidden bg-background">
          <CopilotChat
            className="h-full"
            makeSystemMessage={() => 
              `You are a helpful assistant focusing on ${selectedLanguage || "programming"} development. Help users with their coding questions and documentation needs. When providing code examples or implementation guidance, use ${selectedLanguage || "programming"} as the primary language.`
            }
          />
        </div>
      </div>
    </main>
  );
} 