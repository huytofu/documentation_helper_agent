"use client";

import React from 'react';
import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { useLangGraphInterrupt, useCoAgentStateRender, useCoAgent } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MessageSquare, Sparkles } from "lucide-react";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProgrammingLanguage } from "@/types";

// Define the agent state type
type AgentState = {
  language: ProgrammingLanguage | "";
  current_node: string;
  final_generation: string;
}

// Custom AgentStatePanel component
const AgentStatePanel: React.FC<{
  status?: string;
  state?: AgentState;
}> = ({ status, state }) => {
  // Add more detailed logging to debug state updates
  console.log("Agent State Update - Full Details:", {
    status,
    state,
    hasState: !!state,
    currentNode: state?.current_node,
    stateKeys: state ? Object.keys(state) : []
  });
  
  return (
    <div className="space-y-4">
      {/* Status Indicator */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          status === "inProgress" ? "bg-blue-500 animate-pulse" : 
          status === "complete" ? "bg-green-500" : 
          "bg-gray-500"
        }`} />
        <span className="text-sm font-medium capitalize">{status}</span>
      </div>
      
      {/* Current Node */}
      {state?.current_node && (
        <div className="text-sm bg-blue-50 rounded px-3 py-2">
          <span className="font-medium">Current Node:</span>
          <div className="mt-1">{state.current_node}</div>
        </div>
      )}

      {/* Debug Information */}
      <div className="text-xs bg-gray-100 rounded px-3 py-2">
        <span className="font-medium">Debug Info:</span>
        <pre className="mt-1 overflow-auto">
          {JSON.stringify({ 
            status, 
            hasState: !!state, 
            node: state?.current_node 
          }, null, 2)}
        </pre>
      </div>
    </div>
  );
};

// Wrapper component for the state renderer
const AgentStateRenderer: React.FC = () => {
  useCoAgentStateRender<AgentState>({
    name: "coding_agent",
    render: ({ status, state }) => (
      <AgentStatePanel status={status} state={state} />
    ),
  });
  return null;
};

export default function Home() {
  const { selectedLanguage, setSelectedLanguage } = useContext(LanguageContext);

  // Add the CoAgent state management
  const { state, setState } = useCoAgent<AgentState>({
    name: "coding_agent",
    initialState: {
      language: "python",
      current_node: "",
      final_generation: ""
    },
  });

  // Add the LangGraph interrupt handler
  useLangGraphInterrupt<string>({
    render: ({ event, resolve }) => (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 space-y-4">
          <h3 className="text-lg font-semibold">Human Input Required</h3>
          <p className="text-sm text-gray-600">{event.value}</p>
          <form 
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement;
              resolve(form.response.value);
              form.reset();
            }}
          >
            <Input 
              type="text" 
              name="response" 
              placeholder="Enter your response" 
              className="w-full"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button type="submit">
                Submit
              </Button>
            </div>
          </form>
        </div>
      </div>
    )
  });

  return (
    <div className="container mx-auto px-4 py-8 max-w-[1400px] min-h-[calc(100vh-3.5rem)]">
      <div className="space-y-8">
        {/* Header Section */}
        <div className="space-y-4 text-center">
          <div className="flex items-center justify-center gap-2">
            <Sparkles className="h-6 w-6 text-blue-500" />
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
                language: lang as AgentState["language"]
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
          <div className="w-80 shrink-0 rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg">
            <div className="flex items-center gap-2 p-4 border-b bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-t-xl">
              <Sparkles className="h-5 w-5 text-blue-500" />
              <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                Agent Status
              </h2>
            </div>
            <AgentStateRenderer />
          </div>
        </div>
      </div>
    </div>
  );
} 