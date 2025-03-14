"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import { ProgrammingLanguage } from "@/types";

interface LanguageSelectorProps {
  selectedLanguage: ProgrammingLanguage | "";
  onLanguageChange: (language: ProgrammingLanguage | "") => void;
}

export function LanguageSelector({ selectedLanguage, onLanguageChange }: LanguageSelectorProps) {
  const languages: ProgrammingLanguage[] = [
    "python",
    "javascript",
    "typescript",
    "java",
    "cpp",
    "csharp",
    "go",
    "rust",
    "swift",
    "kotlin",
    "php",
    "ruby",
    "scala",
    "r",
    "matlab",
    "sql",
    "html",
    "css",
    "shell",
    "powershell",
    "bash",
    "markdown",
    "yaml",
    "json",
    "xml",
    "ini",
    "toml",
    "dockerfile",
    "plaintext"
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="w-[200px] justify-between bg-white/50 backdrop-blur-sm hover:bg-white/80"
        >
          {selectedLanguage ? (
            <span className="capitalize">{selectedLanguage}</span>
          ) : (
            "Select Language"
          )}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[200px] bg-white/80 backdrop-blur-sm">
        <DropdownMenuItem
          onClick={() => {
            onLanguageChange("");
          }}
        >
          <span className="text-muted-foreground">Clear Selection</span>
        </DropdownMenuItem>
        {languages.map((lang) => (
          <DropdownMenuItem
            key={lang}
            onClick={() => {
              onLanguageChange(lang);
            }}
          >
            <span className="capitalize">{lang}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
} 