"use client";

import React from 'react';
// import { useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { ProgrammingLanguage } from "@/types";
import { AgentStatePanel } from "@/components/AgentStatePanel";
import { ChatInterface } from "@/components/ChatInterface";

// Define shared agent state type
// export type AgentState = {
//   language: ProgrammingLanguage | "";
//   comments: string;
//   current_node: string;
// }

export default function Home() {
  const { selectedLanguage, setSelectedLanguage } = useContext(LanguageContext);

  // Temporarily disabled coAgent state management
  // const { state, setState } = useCoAgent<AgentState>({
  //   name: "coding_agent",
  //   initialState: {
  //     language: "python",
  //     current_node: "",
  //     comments: ""
  //   }
  // });

  // Handler for language changes
  const handleLanguageChange = (lang: ProgrammingLanguage | "") => {
    console.log("Language changed to:", lang);
    setSelectedLanguage(lang);
    // setState({
    //   ...state,
    //   language: lang
    // });
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
          {/* <AgentStatePanel /> */}
        </div>
      </div>
    </div>
  );
} 