'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useCoAgent } from "@copilotkit/react-core";
import { ProgrammingLanguage } from "@/types";
import { AGENT_NAME } from "@/constants";
import { Activity, Code, MessageSquare, Terminal, Cpu, Loader2, CheckCircle2, Clock } from "lucide-react";

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
    state1.current_node === state1.current_node &&
    state1.test_counter === state2.test_counter
  );
};

// Function to determine if a node is a terminal node
const isTerminalNode = (nodeName: string): boolean => {
  return nodeName === "END" || nodeName === "POST_HUMAN_IN_LOOP";
};

// Component to display the content of the agent state
const StatusContent = ({ state, isLoading, isComplete }: { 
  state: AgentState;
  isLoading: boolean;
  isComplete: boolean;
}) => {
  return (
    <div className="space-y-4 p-4">
      {/* Status Indicator */}
      <div className={`rounded-lg border ${isComplete ? 'border-green-100 bg-green-50/50' : 'border-amber-100 bg-amber-50/50'} overflow-hidden`}>
        <div className={`${isComplete ? 'bg-green-100/50 border-green-100' : 'bg-amber-100/50 border-amber-100'} px-3 py-2 border-b flex items-center gap-2`}>
          {isComplete ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <Clock className="h-4 w-4 text-amber-600" />
          )}
          <h3 className={`text-sm font-medium ${isComplete ? 'text-green-700' : 'text-amber-700'}`}>Status</h3>
        </div>
        <div className="p-3 text-sm">
          <div className="flex items-center gap-2">
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
                <span className="text-amber-700 font-medium">Processing...</span>
              </>
            ) : isComplete ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <span className="text-green-700 font-medium">Complete</span>
              </>
            ) : (
              <>
                <Clock className="h-4 w-4 text-amber-600" />
                <span className="text-amber-700 font-medium">In Progress</span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50/50 overflow-hidden">
        <div className="bg-blue-100/50 px-3 py-2 border-b border-blue-100 flex items-center gap-2">
          <Terminal className="h-4 w-4 text-blue-600" />
          <h3 className="text-sm font-medium text-blue-700">Current Node</h3>
        </div>
        <div className="p-3 text-sm">
          {isLoading ? (
            <div className="flex items-center gap-2 text-blue-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Processing...</span>
            </div>
          ) : (
            state.current_node || "Waiting for agent to start..."
          )}
        </div>
      </div>
      
      <div className="rounded-lg border border-purple-100 bg-purple-50/50 overflow-hidden">
        <div className="bg-purple-100/50 px-3 py-2 border-b border-purple-100 flex items-center gap-2">
          <Code className="h-4 w-4 text-purple-600" />
          <h3 className="text-sm font-medium text-purple-700">Language</h3>
        </div>
        <div className="p-3 text-sm">
          {state.language ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              {state.language}
            </span>
          ) : (
            "Not set"
          )}
        </div>
      </div>
      
      {state.comments && (
        <div className="rounded-lg border border-green-100 bg-green-50/50 overflow-hidden">
          <div className="bg-green-100/50 px-3 py-2 border-b border-green-100 flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-green-600" />
            <h3 className="text-sm font-medium text-green-700">Comments</h3>
          </div>
          <div className="p-3 text-sm whitespace-pre-wrap">
            {state.comments}
          </div>
        </div>
      )}
      
      {state.test_counter !== undefined && (
        <div className="rounded-lg border border-amber-100 bg-amber-50/50 overflow-hidden">
          <div className="bg-amber-100/50 px-3 py-2 border-b border-amber-100 flex items-center gap-2">
            <Activity className="h-4 w-4 text-amber-600" />
            <h3 className="text-sm font-medium text-amber-700">Test Counter</h3>
          </div>
          <div className="p-3 text-sm">
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
  const [isComplete, setIsComplete] = useState(false);
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
      
      // Check if this is a terminal node
      const complete = isTerminalNode(directState.current_node);
      setIsComplete(complete);
      
      // Only show loading if not complete
      if (!complete) {
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
      } else {
        // If complete, don't show loading
        setIsLoading(false);
      }
      
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
    <div className="rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg overflow-hidden">
      <div className={`flex items-center justify-between gap-2 p-4 border-b ${
        isComplete 
          ? 'bg-gradient-to-r from-green-500/10 to-emerald-500/10' 
          : 'bg-gradient-to-r from-blue-500/10 to-purple-500/10'
      }`}>
        <div className="flex items-center gap-2">
          <Cpu className={`h-5 w-5 ${isComplete ? 'text-green-500' : 'text-blue-500'}`} />
          <h2 className={`text-xl font-semibold bg-clip-text text-transparent ${
            isComplete 
              ? 'bg-gradient-to-r from-green-500 to-emerald-500' 
              : 'bg-gradient-to-r from-blue-500 to-purple-500'
          }`}>
            Agent Status
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-xs text-muted-foreground bg-white/50 px-2 py-1 rounded-full">
            Updates: {updateCount}
          </div>
          {isComplete && (
            <div className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              <span>Complete</span>
            </div>
          )}
        </div>
      </div>
      
      {directState ? (
        <StatusContent state={directState} isLoading={isLoading} isComplete={isComplete} />
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-4" />
          <p>Waiting for agent to start...</p>
          <p className="text-xs mt-2">(No state available)</p>
        </div>
      )}
    </div>
  );
} 