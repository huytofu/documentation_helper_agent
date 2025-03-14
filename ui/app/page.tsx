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
import { TestStateUpdates } from "@/components/TestStateUpdates";

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
    <main className="flex min-h-screen flex-col items-center justify-between p-4 md:p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm flex flex-col gap-4">
        <div className="w-full flex flex-col md:flex-row gap-4">
          <div className="w-full md:w-1/2">
            <LanguageSelector 
              selectedLanguage={selectedLanguage} 
              onLanguageChange={handleLanguageChange} 
            />
            <ChatInterface />
          </div>
          <div className="w-full md:w-1/2">
            <AgentStatePanel />
            <div className="mt-4">
              <TestStateUpdates />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
} 