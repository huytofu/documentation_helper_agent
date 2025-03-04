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
    <div className="space-y-2">
      <Label htmlFor="language" className="flex items-center gap-2">
        <Code2 className="h-4 w-4" />
        Programming Language
      </Label>
      <Select
        value={selectedLanguage}
        onChange={(value) => onLanguageChange(value as ProgrammingLanguage)}
        options={PROGRAMMING_LANGUAGES.map(lang => ({
          label: lang,
          value: lang,
        }))}
        placeholder="Select a programming language"
      />
    </div>
  );
} 