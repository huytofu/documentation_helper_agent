"use client";

import { CopilotChat } from "@copilotkit/react-ui";

export default function Home() {  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-4xl">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="space-y-4">
            <CopilotChat
              className="h-full"
              makeSystemMessage={() => 
                `You are a helpful assistant focusing on helping users with their questions, 
                You must always route user queries to available backend agents first for processing. 
                Do not attempt to answer questions directly without consulting the backend agents}`
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
} 