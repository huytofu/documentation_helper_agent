"use client";

import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MessageSquare, Sparkles } from "lucide-react";
import { LanguageContext } from "./layout";
import { useContext } from "react";

export default function Home() {
  const { selectedLanguage } = useContext(LanguageContext);

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