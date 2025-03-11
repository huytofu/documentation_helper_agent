"use client";

// import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { useLangGraphInterrupt, useCoAgentStateRender } from "@copilotkit/react-core";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MessageSquare, Sparkles } from "lucide-react";
import { LanguageContext } from "./layout";
import { useContext } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Define the agent state type
type AgentState = {
  final_generation: string;
}

export default function Home() {
  const { selectedLanguage } = useContext(LanguageContext);

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

  // Add the agent state renderer
  useCoAgentStateRender<AgentState>({
    name: "coding_agent",
    render: ({ status, state }) => {
      if (!state.final_generation || state.final_generation === "") return null;
      
      return (
        <div className="fixed bottom-4 right-4 max-w-md bg-white rounded-lg shadow-lg p-4 border border-gray-200">
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-2 h-2 rounded-full ${
              status === "inProgress" ? "bg-blue-500 animate-pulse" : 
              status === "complete" ? "bg-green-500" : 
              "bg-gray-500"
            }`} />
            <span className="text-sm font-medium capitalize">{status}</span>
          </div>
          <p className="text-sm text-gray-600">{state.final_generation}</p>
        </div>
      );
    },
  });

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl min-h-[calc(100vh-3.5rem)] flex flex-col justify-center">
      <div className="space-y-12">
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

        <div className="space-y-8">
          <div className="flex justify-center">
            <LanguageSelector
              selectedLanguage={selectedLanguage}
              onLanguageChange={(lang) => {
                // This will be handled by the context
                console.log("Language changed:", lang);
              }}
            />
          </div>

          <div className="relative rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg">
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
        </div>
      </div>
    </div>
  );
} 