import React from 'react';
import { CopilotChat } from "@copilotkit/react-ui";
import { MessageSquare } from "lucide-react";

export function ChatInterface() {
  return (
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
  );
} 