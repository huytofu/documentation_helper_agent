"use client";

import React, { useEffect } from 'react';
import { useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { ProgrammingLanguage } from "@/types";
import { AgentStatePanel } from "@/components/AgentStatePanel";
import { ChatInterface } from "@/components/ChatInterface";
import { AGENT_NAME } from "@/constants";

// Define shared agent state interface
export interface AgentState {
  language: ProgrammingLanguage | "";
  comments: string;
  current_node: string;
  test_counter?: number;
}

export default function Home() {
  const { selectedLanguage, setSelectedLanguage } = useContext(LanguageContext);

  // Use coAgent state management with proper initialization
  const { state, setState } = useCoAgent<AgentState>({
    name: AGENT_NAME,
    initialState: {
      language: selectedLanguage || "python",
      current_node: "",
      comments: "",
    },
  });

  // Update agent state when language changes
  useEffect(() => {
    // Only update if the language has actually changed and is different from the current state
    if (selectedLanguage !== state.language) {
      console.log("Language changed, updating agent state:", selectedLanguage);
      setState((prevState) => ({
        ...prevState,
        language: selectedLanguage,
        // Ensure required fields are always present
        comments: prevState?.comments || "",
        current_node: prevState?.current_node || "",
      }));
    }
  }, [selectedLanguage, setState, state.language]);

  // Log state changes for debugging
  useEffect(() => {
    console.log("useCoAgent state changed in page.tsx:", {
      language: state.language,
      current_node: state.current_node,
      comments: state.comments,
      test_counter: state.test_counter,
      timestamp: new Date().toISOString()
    });
  }, [state]);

  // Handler for language changes - only update context, don't directly update agent state
  const handleLanguageChange = (lang: ProgrammingLanguage | "") => {
    console.log("Language selector changed to:", lang);
    // Only update if the language has actually changed
    if (lang !== selectedLanguage) {
      setSelectedLanguage(lang);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-8">
      <div className="w-full max-w-7xl">
        <h1 className="text-2xl font-bold mb-6 text-center bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Documentation Helper Agent
        </h1>
        
        <div className="w-full flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-1/2 space-y-4">
            <div className="bg-white/30 backdrop-blur-sm p-4 rounded-lg border border-gray-200 shadow-sm">
              <LanguageSelector 
                selectedLanguage={selectedLanguage} 
                onLanguageChange={handleLanguageChange} 
              />
            </div>
            
            <ChatInterface />
          </div>
          
          <div className="w-full md:w-1/2">
            <div className="bg-white/30 backdrop-blur-sm p-4 rounded-lg border border-gray-200 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">Agent Status</h2>
              <AgentStatePanel />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
} 