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
import { MessageRole, TextMessage } from "@copilotkit/runtime-client-gql";
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
  const { state, setState, run } = useCoAgent<AgentState>({
    name: AGENT_NAME,
    initialState: {
      language: selectedLanguage || "python",
      current_node: "",
      comments: "",
    },
  });

  // Function to trigger the agent with a message
  const triggerAgent = (message: string) => {
    console.log("Triggering agent with message:", message);
    
    // Update the comments in the state
    setState(prevState => ({
      ...prevState,
      comments: message,
      // Ensure required fields are always present
      language: prevState?.language || selectedLanguage || "python",
      current_node: prevState?.current_node || "",
    }));
    
    // Trigger the agent with the message
    run(() => new TextMessage({ 
      role: MessageRole.User, 
      content: message 
    }));
  };

  // Update agent state when language changes
  useEffect(() => {
    if (selectedLanguage) {
      setState((prevState) => ({
        ...prevState,
        language: selectedLanguage,
        // Ensure required fields are always present
        comments: prevState?.comments || "",
        current_node: prevState?.current_node || "",
      }));
      
      // Optionally trigger the agent when language changes
      // triggerAgent(`I want to work with ${selectedLanguage} code.`);
    }
  }, [selectedLanguage, setState]);

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

  // Handler for language changes
  const handleLanguageChange = (lang: ProgrammingLanguage | "") => {
    setSelectedLanguage(lang);
  };

  return (
    <div className="container mx-auto px-4 py-8 flex flex-col md:flex-row gap-6 h-[calc(100vh-80px)]">
      <div className="flex-1 flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Documentation Helper</h1>
          <LanguageSelector 
            selectedLanguage={selectedLanguage} 
            onLanguageChange={handleLanguageChange} 
          />
        </div>
        
        {/* Add a test button to trigger the agent */}
        <Button 
          className="mb-4"
          onClick={() => triggerAgent("Help me understand this codebase.")}
        >
          Trigger Agent
        </Button>
        
        <div className="flex-1 overflow-hidden">
          <ChatInterface />
        </div>
      </div>
      
      <div className="w-full md:w-96 flex flex-col">
        <h2 className="text-xl font-semibold mb-2">Agent Status</h2>
        <div className="flex-1 border rounded-lg p-4 overflow-auto bg-secondary/30">
          <AgentStatePanel />
        </div>
      </div>
    </div>
  );
} 