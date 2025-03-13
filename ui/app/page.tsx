"use client";

import React from 'react';
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MessageSquare } from "lucide-react";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { ProgrammingLanguage } from "@/types";
import { AgentStatePanel } from "@/components/AgentStatePanel";

export default function Home() {
  const { selectedLanguage, setSelectedLanguage } = useContext(LanguageContext);

  // Add the CoAgent state management
  const { state, setState } = useCoAgent<{
    language: ProgrammingLanguage | "";
    current_node: string;
    final_generation: string;
  }>({
    name: "coding_agent",
    initialState: {
      language: "python",
      current_node: "",
      final_generation: ""
    },
  });

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
            selectedLanguage={state.language}
            onLanguageChange={(lang) => {
              setSelectedLanguage(lang);
              setState({ 
                ...state, 
                language: lang as ProgrammingLanguage | ""
              });
            }}
          />
        </div>

        {/* Main Content with Side Panel Layout */}
        <div className="flex gap-4">
          {/* Chat Interface */}
          <div className="flex-1 rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg">
            <div className="flex items-center gap-2 p-4 border-b bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-t-xl">
              <MessageSquare className="h-5 w-5 text-blue-500" />
              <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                Chat Interface
              </h2>
            </div>
            <div className="h-[600px]">
              <CopilotChat
                className="h-full"
                makeSystemMessage={() => 
                  `You are a helpful assistant focusing on helping users with their questions, 
                  You must always route user queries to available backend agents first for processing. 
                  Do not attempt to answer questions directly without consulting the backend agents.}`
                }
              />
            </div>
          </div>

          {/* Agent State Side Panel */}
          <AgentStatePanel />
        </div>
      </div>
    </div>
  );
} 