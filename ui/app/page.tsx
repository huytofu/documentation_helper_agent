"use client";

import React, { useEffect } from 'react';
import { useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { ProgrammingLanguage } from "@/types";
import { AgentStatePanel } from "@/components/AgentStatePanel";
import { ChatInterface } from "@/components/ChatInterface";
import { Button } from "@/components/ui/button";

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
    name: "coding_agent",
    initialState: {
      language: selectedLanguage || "python",
      current_node: "",
      comments: "",
      test_counter: 0
    }
  });

  // Effect to update agent state when selected language changes
  useEffect(() => {
    if (selectedLanguage && selectedLanguage !== state?.language) {
      console.log("Language context changed, updating agent state:", selectedLanguage);
      setState({
        language: selectedLanguage,
        comments: state?.comments || "",
        current_node: state?.current_node || "",
        test_counter: state?.test_counter || 0
      });
    }
  }, [selectedLanguage, setState, state]);

  // Effect to log state changes for testing bidirectional communication
  useEffect(() => {
    console.log("useCoAgent state changed in page.tsx:", {
      state,
      timestamp: new Date().toISOString()
    });
  }, [state]);

  // Handler for language changes
  const handleLanguageChange = (lang: ProgrammingLanguage | "") => {
    console.log("Language changed to:", lang);
    setSelectedLanguage(lang);
    
    // Update state to ensure the agent receives the language
    setState({
      language: lang,
      comments: state?.comments || "",
      current_node: state?.current_node || "",
      test_counter: state?.test_counter || 0
    });
    
    // Log the update for debugging
    console.log("Updated agent state with language:", lang);
  };

  // Test function to increment counter and verify bidirectional communication
  const testBidirectionalCommunication = () => {
    const newCounter = (state?.test_counter || 0) + 1;
    console.log("Testing bidirectional communication, incrementing counter to:", newCounter);
    
    setState({
      language: state?.language || "python",
      comments: state?.comments || "",
      current_node: state?.current_node || "",
      test_counter: newCounter
    });
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

        <div className="flex justify-center items-center gap-4">
          <LanguageSelector
            selectedLanguage={selectedLanguage}
            onLanguageChange={handleLanguageChange}
          />
          
          {/* Test button for bidirectional communication */}
          <Button 
            variant="outline" 
            onClick={testBidirectionalCommunication}
            className="flex items-center gap-2"
          >
            Test Bidirectional Comm
            {state?.test_counter !== undefined && (
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                {state.test_counter}
              </span>
            )}
          </Button>
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