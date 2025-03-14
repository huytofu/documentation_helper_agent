"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useCoAgent } from "@copilotkit/react-core";
import { AgentState } from './AgentStatePanel';
import { Button } from "@/components/ui/button";
import { ProgrammingLanguage } from '@/types';
import { AGENT_NAME } from '@/constants';
import { MessageRole, TextMessage } from "@copilotkit/runtime-client-gql";

export const TestStateUpdates: React.FC = () => {
  // Local state for testing
  const [localCounter, setLocalCounter] = useState(0);
  const [renderCount, setRenderCount] = useState(0);
  const isInitialMount = useRef(true);
  
  // CoAgent state
  const { state, setState, run } = useCoAgent<AgentState>({
    name: AGENT_NAME,
    initialState: {
      language: "python" as ProgrammingLanguage,
      current_node: "",
      comments: "",
    },
  });
  
  // Track renders
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    setRenderCount(prev => prev + 1);
    console.log('TestStateUpdates rendered', { localCounter, agentCounter: state?.test_counter });
  }, [localCounter, state]);
  
  // Test local state update and agent state update
  const testStateUpdate = () => {
    // Update local counter
    setLocalCounter(prev => prev + 1);
    
    // Update agent state - ensure we include all required fields
    setState((prevState: AgentState | undefined) => {
      const newCounter = (prevState?.test_counter || 0) + 1;
      
      // Make sure we return a complete AgentState object
      return {
        // Use a valid language from ProgrammingLanguage type
        language: prevState?.language || "python" as ProgrammingLanguage,
        comments: prevState?.comments || "",
        current_node: prevState?.current_node || "",
        test_counter: newCounter
      };
    });
  };
  
  // Test agent trigger
  const testAgentTrigger = () => {
    // Use the run function from useCoAgent
    run(() => new TextMessage({ 
      role: MessageRole.User, 
      content: `Test message ${Date.now()}` 
    }));
  };
  
  return (
    <div className="w-full p-4 border rounded-lg bg-white/50 backdrop-blur-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">State Update Test</h2>
      </div>
      <div className="space-y-4">
        <div>
          <p>Render count: {renderCount}</p>
          <p>Local counter: {localCounter}</p>
          <p>Agent counter: {state?.test_counter || 0}</p>
        </div>
        
        <div className="space-x-2">
          <Button onClick={testStateUpdate}>
            Test State Update
          </Button>
          <Button onClick={testAgentTrigger} variant="outline">
            Test Agent Trigger
          </Button>
        </div>
      </div>
    </div>
  );
}; 