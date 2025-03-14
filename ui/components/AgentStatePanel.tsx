import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useCoAgentStateRender, useLangGraphInterrupt } from "@copilotkit/react-core";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProgrammingLanguage } from "@/types";
import { MessageSquareX } from "lucide-react";
import { AGENT_NAME } from "@/constants";

// Define the agent state interface
export interface AgentState {
  language: ProgrammingLanguage | "";
  comments: string;
  current_node: string;
  test_counter?: number;
}

// Component to display the content of the agent state
const StatusContent = ({ currentStatus, currentState }: { 
  currentStatus: string; 
  currentState: AgentState | null;
}) => {
  if (!currentState) {
    return <div>No state available</div>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-1">Current Node:</h3>
        <div className="bg-secondary/50 p-2 rounded text-sm">
          {currentStatus || "Waiting for agent to start..."}
        </div>
      </div>
      
      <div>
        <h3 className="text-sm font-medium mb-1">Language:</h3>
        <div className="bg-secondary/50 p-2 rounded text-sm">
          {currentState.language || "Not set"}
        </div>
      </div>
      
      {currentState.comments && (
        <div>
          <h3 className="text-sm font-medium mb-1">Comments:</h3>
          <div className="bg-secondary/50 p-2 rounded text-sm whitespace-pre-wrap">
            {currentState.comments}
          </div>
        </div>
      )}
      
      {currentState.test_counter !== undefined && (
        <div>
          <h3 className="text-sm font-medium mb-1">Test Counter:</h3>
          <div className="bg-secondary/50 p-2 rounded text-sm">
            {currentState.test_counter}
          </div>
        </div>
      )}
    </div>
  );
};

export function AgentStatePanel() {
  // State for tracking the current status and state
  const [currentStatus, setCurrentStatus] = useState<string>("");
  const [currentState, setCurrentState] = useState<AgentState | null>(null);
  const [stateUpdateCount, setStateUpdateCount] = useState(0);
  
  // Reference to track render count for debugging
  const renderCountRef = useRef(0);
  
  // Get the interrupt function to allow stopping the agent
  const interrupt = () => {
    console.log("Interrupting agent...");
    // Implement actual interrupt logic if needed
  };
  const isInterrupting = false;
  
  // Handle state updates in a stable way using useCallback
  const handleStateUpdate = useCallback((newState: AgentState) => {
    // Schedule the state update for the next tick to avoid React warnings
    Promise.resolve().then(() => {
      setCurrentState(prevState => {
        if (!prevState) return newState;
        return {
          ...prevState,
          ...newState
        };
      });
      setStateUpdateCount(prev => prev + 1);
      
      // Update current status based on the current_node
      if (newState.current_node) {
        setCurrentStatus(newState.current_node);
      }
    });
  }, []);
  
  // Use the useCoAgentStateRender hook for real-time updates
  useCoAgentStateRender<AgentState>({
    name: AGENT_NAME,
    render: ({ state: renderedState }) => {
      // Track render count for debugging
      renderCountRef.current += 1;
      console.log(`AgentStatePanel: Rendering state update (${renderCountRef.current}):`, renderedState);
      
      // Only process if we have state
      if (renderedState) {
        // Schedule the state update for after rendering is complete
        handleStateUpdate(renderedState);
      }
      
      // Return an invisible div to avoid rendering in the chat
      return <div style={{ display: 'none' }} />;
    }
  });
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="text-sm text-muted-foreground">
          Updates: {stateUpdateCount}
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={interrupt}
          disabled={isInterrupting}
          className="flex items-center gap-1"
        >
          <MessageSquareX className="h-4 w-4" />
          {isInterrupting ? "Stopping..." : "Stop Agent"}
        </Button>
      </div>
      
      {currentState ? (
        <StatusContent currentStatus={currentStatus} currentState={currentState} />
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          Waiting for agent to start...
        </div>
      )}
    </div>
  );
} 