import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useCoAgentStateRender } from "@copilotkit/react-core";
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
const StatusContent = ({ currentStatus, currentState, isLoading }: { 
  currentStatus: string; 
  currentState: AgentState | null;
  isLoading: boolean;
}) => {
  if (!currentState) {
    return <div>No state available</div>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium mb-1">Current Node:</h3>
        <div className="bg-secondary/50 p-2 rounded text-sm">
          {isLoading ? "Processing..." : (currentStatus || "Waiting for agent to start...")}
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
  const [isLoading, setIsLoading] = useState(false);
  
  // Reference to track render count for debugging
  const renderCountRef = useRef(0);
  
  // Reference to track if we're currently updating state
  const isUpdatingRef = useRef(false);
  
  // Reference to store the last state we processed
  const lastStateRef = useRef<AgentState | null>(null);
  
  // Timer reference for loading state
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  // Handle state updates in a stable way using useCallback
  const handleStateUpdate = useCallback((newState: AgentState) => {
    // Skip if we're already updating to prevent loops
    if (isUpdatingRef.current) return;
    
    // Skip if the new state is the same as the last state we processed
    if (areStatesEqual(lastStateRef.current, newState)) {
      console.log("AgentStatePanel: Skipping identical state update");
      return;
    }
    
    // Set the updating flag
    isUpdatingRef.current = true;
    
    // Update the last state reference
    lastStateRef.current = { ...newState };
    
    // Set loading state when a new node is detected
    if (newState.current_node && newState.current_node !== currentStatus) {
      setIsLoading(true);
      
      // Clear any existing timer
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      
      // Set a timer to clear the loading state after a delay
      loadingTimerRef.current = setTimeout(() => {
        setIsLoading(false);
      }, 1500); // Adjust this delay as needed
    }
    
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
      
      // Reset the updating flag
      isUpdatingRef.current = false;
    });
  }, [currentStatus]);
  
  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, []);
  
  // Use the useCoAgentStateRender hook for real-time updates
  useCoAgentStateRender<AgentState>({
    name: AGENT_NAME,
    render: ({ state: renderedState }) => {
      // Track render count for debugging
      renderCountRef.current += 1;
      console.log(`AgentStatePanel: Rendering state update (${renderCountRef.current}):`, renderedState);
      
      // Only process if we have state and we're not already updating
      if (renderedState && !isUpdatingRef.current) {
        // Schedule the state update for after rendering is complete
        handleStateUpdate(renderedState);
      }
      
      // Return an invisible div to avoid rendering in the chat
      return <div style={{ display: 'none' }} />;
    }
  });
  
  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground mb-2">
        State Updates: {stateUpdateCount}
      </div>
      
      {currentState ? (
        <StatusContent currentStatus={currentStatus} currentState={currentState} isLoading={isLoading} />
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          Waiting for agent to start...
        </div>
      )}
    </div>
  );
} 