import React, { useState } from 'react';
import { useCoAgentStateRender, useLangGraphInterrupt } from "@copilotkit/react-core";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProgrammingLanguage } from "@/types";

// Define the agent state type
type AgentState = {
  language: ProgrammingLanguage | "";
  current_node: string;
  final_generation: string;
}

// Status content component
function StatusContent({ status, state }: { status?: string; state?: AgentState }) {
  return (
    <div className="space-y-4 p-4">
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
}

export function AgentStatePanel() {
  const [currentStatus, setCurrentStatus] = useState<string>();
  const [currentState, setCurrentState] = useState<AgentState>();

  // Add the state renderer hook
  useCoAgentStateRender<AgentState>({
    name: "coding_agent",
    render: ({ status, state }) => {
      // Update local state
      setCurrentStatus(status);
      setCurrentState(state);
      // Return null to prevent rendering in chat
      return null;
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
    <div className="w-80 shrink-0 rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg">
      <div className="flex items-center gap-2 p-4 border-b bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-t-xl">
        <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          Agent Status
        </h2>
      </div>
      {(!currentState && !currentStatus) ? (
        <div className="text-sm text-gray-500 p-4">
          Waiting for agent state...
        </div>
      ) : (
        <StatusContent status={currentStatus} state={currentState} />
      )}
    </div>
  );
} 