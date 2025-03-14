import React, { useState, useEffect, useCallback } from 'react';
import { useCoAgentStateRender, useLangGraphInterrupt } from "@copilotkit/react-core";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProgrammingLanguage } from "@/types";

// Define the agent state type
type AgentState = {
  language: ProgrammingLanguage | "";
  comments?: string;
  current_node?: string;
}

// Status content component
function StatusContent({ state }: { state?: AgentState }) {
  // Determine status based on current_node
  let statusDisplay = "idle";
  let statusColor = "bg-gray-500";
  
  if (state?.current_node) {
    statusDisplay = "inProgress";
    statusColor = "bg-blue-500 animate-pulse";
    
    // Check for specific node states
    if (state.current_node.includes("STARTED")) {
      statusDisplay = "started";
      statusColor = "bg-yellow-500 animate-pulse";
    } else if (state.current_node.includes("GENERATING")) {
      statusDisplay = "generating";
      statusColor = "bg-blue-500 animate-pulse";
    } else if (state.current_node.includes("COMPLETE")) {
      statusDisplay = "complete";
      statusColor = "bg-green-500";
    }
  }
  
  // Check if we're at a final node
  if (state?.current_node === "END") {
    statusDisplay = "complete";
    statusColor = "bg-green-500";
  }
  
  return (
    <div className="space-y-4 p-4">
      {/* Status Indicator */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${statusColor}`} />
        <span className="text-sm font-medium capitalize">{statusDisplay}</span>
      </div>
      
      {/* Current Node */}
      {state?.current_node && (
        <div className="text-sm bg-blue-50 rounded px-3 py-2">
          <span className="font-medium">Current Node:</span>
          <div className="mt-1">{state.current_node}</div>
        </div>
      )}

      {/* Language */}
      {state?.language && (
        <div className="text-sm bg-purple-50 rounded px-3 py-2">
          <span className="font-medium">Language:</span>
          <div className="mt-1">{state.language}</div>
        </div>
      )}

      {/* Comments */}
      {state?.comments && (
        <div className="text-sm bg-amber-50 rounded px-3 py-2">
          <span className="font-medium">Comments:</span>
          <div className="mt-1">{state.comments}</div>
        </div>
      )}

      {/* Debug Information */}
      <div className="text-xs bg-gray-100 rounded px-3 py-2">
        <span className="font-medium">Debug Info:</span>
        <pre className="mt-1 overflow-auto">
          {JSON.stringify({ 
            status: statusDisplay, 
            hasState: !!state, 
            stateKeys: state ? Object.keys(state) : [],
            timestamp: new Date().toISOString()
          }, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export function AgentStatePanel() {
  // Local state to track updates
  const [currentState, setCurrentState] = useState<AgentState | undefined>(undefined);
  const [stateUpdateCount, setStateUpdateCount] = useState(0);
  
  // Create a stable callback for state updates
  const handleStateUpdate = useCallback((newState: AgentState) => {
    // Use Promise.resolve().then to schedule the state update for the next tick
    // This prevents the "Cannot update during render" error
    Promise.resolve().then(() => {
      setCurrentState(prevState => {
        if (!prevState) return newState;
        return {
          ...prevState,
          ...newState
        };
      });
      setStateUpdateCount(prev => prev + 1);
    });
  }, []);
  
  // Use the useCoAgentStateRender hook for real-time updates
  useCoAgentStateRender<AgentState>({
    name: "coding_agent",
    render: ({ state: renderedState }) => {
      console.log("Rendering state update:", renderedState);
      
      // Only process if we have state
      if (renderedState) {
        // Schedule the state update for after rendering is complete
        handleStateUpdate(renderedState);
      }
      
      // Return an invisible div instead of null
      return <div style={{ display: 'none' }} />;
    }
  });

  // Log state updates for debugging
  useEffect(() => {
    console.log("Current state:", currentState);
    console.log("State update count:", stateUpdateCount);
  }, [currentState, stateUpdateCount]);

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
        {stateUpdateCount > 0 && (
          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
            Updates: {stateUpdateCount}
          </span>
        )}
      </div>
      {!currentState ? (
        <div className="text-sm text-gray-500 p-4">
          Waiting for agent state...
        </div>
      ) : (
        <StatusContent state={currentState} />
      )}
    </div>
  );
} 