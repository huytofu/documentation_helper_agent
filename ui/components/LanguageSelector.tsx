import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Code2 } from "lucide-react";

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

interface LanguageSelectorProps {
  selectedLanguage: ProgrammingLanguage | "";
  onLanguageChange: (language: ProgrammingLanguage) => void;
}

export function LanguageSelector({ selectedLanguage, onLanguageChange }: LanguageSelectorProps) {
  return (
    <div className="space-y-2 w-full max-w-md">
      <Label htmlFor="language" className="flex items-center gap-2 text-lg font-medium">
        <Code2 className="h-5 w-5 text-blue-500" />
        <span className="bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          Programming Language
        </span>
      </Label>
      <Select
        value={selectedLanguage}
        onChange={(value) => onLanguageChange(value as ProgrammingLanguage)}
        options={PROGRAMMING_LANGUAGES.map(lang => ({
          label: lang,
          value: lang,
        }))}
        placeholder="Select a programming language"
        className="bg-card/50 backdrop-blur-sm border-blue-500/20"
      />
    </div>
  );
} 