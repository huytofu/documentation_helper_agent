'use client';

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, Code2, Code } from "lucide-react";
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
    <div className="mb-4 rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg overflow-hidden">
      <div className="flex items-center gap-2 p-4 border-b bg-gradient-to-r from-blue-500/10 to-purple-500/10">
        <Code2 className="h-5 w-5 text-blue-500" />
        <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          Programming Language
        </h2>
      </div>
      
      <div className="p-4">
        <p className="text-sm text-muted-foreground mb-3">
          Select the programming language for documentation assistance:
        </p>
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-between bg-white/50 backdrop-blur-sm hover:bg-white/80 border border-gray-300 shadow-sm"
            >
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 text-blue-500" />
                {selectedLanguage ? (
                  <span className="capitalize">{selectedLanguage}</span>
                ) : (
                  "Select Language"
                )}
              </div>
              <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-full max-h-[300px] overflow-y-auto bg-white/90 backdrop-blur-sm border border-gray-200 shadow-md">
            <DropdownMenuItem
              onClick={() => {
                onLanguageChange("");
              }}
              className="hover:bg-blue-50 cursor-pointer flex items-center gap-2"
            >
              <span className="text-muted-foreground">Clear Selection</span>
            </DropdownMenuItem>
            
            <div className="py-1 px-2 text-xs font-medium text-muted-foreground bg-gray-50">Popular Languages</div>
            {languages.slice(0, 10).map((lang) => (
              <DropdownMenuItem
                key={lang}
                onClick={() => {
                  onLanguageChange(lang);
                }}
                className={`hover:bg-blue-50 cursor-pointer flex items-center gap-2 ${selectedLanguage === lang ? 'bg-blue-100 text-blue-700' : ''}`}
              >
                <Code className="h-3.5 w-3.5 text-blue-500" />
                <span className="capitalize">{lang}</span>
              </DropdownMenuItem>
            ))}
            
            <div className="py-1 px-2 text-xs font-medium text-muted-foreground bg-gray-50">Other Languages</div>
            {languages.slice(10).map((lang) => (
              <DropdownMenuItem
                key={lang}
                onClick={() => {
                  onLanguageChange(lang);
                }}
                className={`hover:bg-blue-50 cursor-pointer flex items-center gap-2 ${selectedLanguage === lang ? 'bg-blue-100 text-blue-700' : ''}`}
              >
                <Code className="h-3.5 w-3.5 text-blue-500" />
                <span className="capitalize">{lang}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
} 