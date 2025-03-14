import React, { useState, useEffect, useRef } from 'react';
import { useCoAgentStateRender, useCoAgent } from "@copilotkit/react-core";
import { Input } from "@/components/ui/input";
import { ProgrammingLanguage } from "@/types";
import { AGENT_NAME } from "@/constants";

// Define the agent state interface
export interface AgentState {
  language: ProgrammingLanguage | "";
  comments: string;
  current_node: string;
  test_counter?: number;
}

// Helper function to check if two states are equivalent
const areStatesEqual = (state1: AgentState | null, state2: AgentState | null): boolean => {
  if (!state1 && !state2) return true;
  if (!state1 || !state2) return false;
  
  return (
    state1.language === state2.language &&
    state1.comments === state2.comments &&
    state1.current_node === state2.current_node &&
    state1.test_counter === state2.test_counter
  );
};

// Component to display the content of the agent state
const StatusContent = ({ state, isLoading }: { 
  state: AgentState;
  isLoading: boolean;
}) => {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-1">Current Node:</h3>
        <div className="bg-secondary/50 p-2 rounded text-sm">
          {isLoading ? "Processing..." : (state.current_node || "Waiting for agent to start...")}
        </div>
      </div>
      
      <div>
        <h3 className="text-sm font-medium mb-1">Language:</h3>
        <div className="bg-secondary/50 p-2 rounded text-sm">
          {state.language || "Not set"}
        </div>
      </div>
      
      {state.comments && (
        <div>
          <h3 className="text-sm font-medium mb-1">Comments:</h3>
          <div className="bg-secondary/50 p-2 rounded text-sm whitespace-pre-wrap">
            {state.comments}
          </div>
        </div>
      )}
      
      {state.test_counter !== undefined && (
        <div>
          <h3 className="text-sm font-medium mb-1">Test Counter:</h3>
          <div className="bg-secondary/50 p-2 rounded text-sm">
            {state.test_counter}
          </div>
        </div>
      )}
    </div>
  );
};

export function AgentStatePanel() {
  // Get state directly from useCoAgent
  const { state: directState } = useCoAgent<AgentState>({
    name: AGENT_NAME
  });
  
  // State for tracking loading and updates
  const [isLoading, setIsLoading] = useState(false);
  const [updateCount, setUpdateCount] = useState(0);
  
  // Reference to track render count for debugging
  const renderCountRef = useRef(0);
  
  // Reference to store the last node we saw
  const lastNodeRef = useRef<string>("");
  
  // Timer reference for loading state
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Handle node changes and loading state
  useEffect(() => {
    if (directState?.current_node && directState.current_node !== lastNodeRef.current) {
      console.log(`AgentStatePanel: New node detected: ${directState.current_node}, setting loading state`);
      lastNodeRef.current = directState.current_node;
      setIsLoading(true);
      
      // Clear any existing timer
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      
      // Set a timer to clear the loading state after a delay
      loadingTimerRef.current = setTimeout(() => {
        console.log("AgentStatePanel: Clearing loading state after timeout");
        setIsLoading(false);
      }, 1500);
      
      // Increment update count
      setUpdateCount(prev => prev + 1);
    }
  }, [directState?.current_node]);
  
  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, []);
  
  // Log state changes
  useEffect(() => {
    console.log("AgentStatePanel: directState changed:", directState);
  }, [directState]);
  
  // Render component with state from useCoAgent
  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground mb-2">
        State Updates: {updateCount}
      </div>
      
      {directState ? (
        <StatusContent state={directState} isLoading={isLoading} />
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          Waiting for agent to start... (No state available)
        </div>
      )}
      
      {/* Debug information */}
      <div className="mt-4 p-2 border border-gray-200 rounded bg-gray-50 text-xs">
        <div>Debug Info:</div>
        <div>Has Direct State: {directState ? 'Yes' : 'No'}</div>
        <div>Current Node: {directState?.current_node || 'None'}</div>
        <div>Language: {directState?.language || 'None'}</div>
        <div>Has Comments: {directState?.comments ? 'Yes' : 'No'}</div>
        <div>Is Loading: {isLoading ? 'Yes' : 'No'}</div>
      </div>
    </div>
  );
} 