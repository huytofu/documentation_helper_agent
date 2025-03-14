"use client";

import React, { useEffect } from 'react';
import { useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { ProgrammingLanguage } from "@/types";
import { AgentStatePanel } from "@/components/AgentStatePanel";
import { ChatInterface } from "@/components/ChatInterface";

// Define shared agent state type
export type AgentState = {
  language: ProgrammingLanguage | "";
}

export default function Home() {
  const { selectedLanguage, setSelectedLanguage } = useContext(LanguageContext);

  // Use coAgent state management with proper initialization
  const { state, setState } = useCoAgent<AgentState>({
    name: "coding_agent",
    initialState: {
      language: selectedLanguage || "python",
      current_node: "",
      comments: ""
    }
  });

  // Effect to update agent state when selected language changes
  useEffect(() => {
    if (selectedLanguage && selectedLanguage !== state?.language) {
      console.log("Language context changed, updating agent state:", selectedLanguage);
      setState({
        language: selectedLanguage
      });
    }
  }, [selectedLanguage, setState, state]);

  // Handler for language changes
  const handleLanguageChange = (lang: ProgrammingLanguage | "") => {
    console.log("Language changed to:", lang);
    setSelectedLanguage(lang);
    
    // Update agent state directly when language selector changes
    setState({
      language: lang
    });
    
    // Log the update for debugging
    console.log("Updated agent state with language:", lang);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-[1400px] min-h-[calc(100vh-3.5rem)]">
      <div className="space-y-8">
        {/* Header Section */}
        <div className="space-y-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
              Documentation Helper Agent
            </h1>
          </div>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Your AI-powered assistant for programming documentation and implementation
          </p>
        </div>

        <div className="flex justify-center">
          <LanguageSelector
            selectedLanguage={selectedLanguage}
            onLanguageChange={handleLanguageChange}
          />
        </div>

        {/* Main Content with Side Panel Layout */}
        <div className="flex gap-4">
          {/* Chat Interface */}
          <ChatInterface />

          {/* Agent State Side Panel */}
          <AgentStatePanel />
        </div>
      </div>
    </div>
  );
} 