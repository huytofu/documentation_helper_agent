'use client';

import React, { useEffect, useRef, useState } from 'react';
import { CopilotChat } from '@copilotkit/react-ui';
import { MessageSquare } from 'lucide-react';
import { useCoAgent } from '@copilotkit/react-core';
import { MessageRole, TextMessage } from '@copilotkit/runtime-client-gql';
import { AGENT_NAME } from '@/constants';
import { AgentState } from '@/types/agent';
import { AuthService } from '@/lib/auth';
import { User } from '@/types/user';

export default function ChatInterface() {
  const isInitialMount = useRef(true);
  const [canChat, setCanChat] = useState(true);
  const [remainingChats, setRemainingChats] = useState(0);
  const [user, setUser] = useState<User | null>(null);
  const authService = AuthService.getInstance();
  
  const { state, run } = useCoAgent<AgentState>({
    name: AGENT_NAME
  });

  useEffect(() => {
    const checkChatAvailability = async () => {
      try {
        const currentUser = authService.getCurrentUser();
        setUser(currentUser);
        const canUserChat = await authService.checkChatLimit();
        const remaining = await authService.getRemainingChats();
        setCanChat(canUserChat);
        setRemainingChats(remaining);
      } catch (error) {
        console.error('Error checking chat availability:', error);
        setCanChat(false);
      }
    };

    checkChatAvailability();
  }, []);

  const handleChatComplete = async () => {
    try {
      await authService.incrementChatUsage();
      const remaining = await authService.getRemainingChats();
      setRemainingChats(remaining);
      if (remaining <= 0) {
        setCanChat(false);
      }
    } catch (error) {
      console.error('Error updating chat usage:', error);
    }
  };

  return (
    <div className="flex-1 rounded-xl border bg-card/50 backdrop-blur-sm text-card-foreground shadow-lg">
      <div className="flex items-center gap-2 p-4 border-b bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-t-xl">
        <MessageSquare className="h-5 w-5 text-blue-500" />
        <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          Chat Interface
        </h2>
      </div>
      <div className="h-[600px]">
        {canChat ? (
          <CopilotChat
            className="h-full"
            makeSystemMessage={() => 
              `You are a helpful assistant focusing on helping users with their questions, 
              You must always route user queries to available backend agents first for processing. 
              Do not attempt to answer questions directly without consulting the backend agents.}`
            }
            onStopGeneration={handleChatComplete}
          />
        ) : (
          <div className="h-full flex items-center justify-center p-8 text-center">
            <div className="max-w-md">
              <p className="text-lg text-gray-700 mb-4">
                Usage exceeds limit of {user?.usageLimit || 20} chats per day, please return tomorrow or login with a new account. 
                This app is meant to be a demo only and therefore incurred cost is kept to the minimum! 
                Please show some understanding towards the developer.
              </p>
              <p className="text-sm text-gray-500">
                Remaining chats today: {remainingChats}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 