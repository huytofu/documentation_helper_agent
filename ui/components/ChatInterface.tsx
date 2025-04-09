'use client';

import React, { useEffect, useRef, useState } from 'react';
import "@copilotkit/react-ui/styles.css";
import { CopilotChat } from '@copilotkit/react-ui';
import { MessageSquare } from 'lucide-react';
import { useCoAgent, useCopilotChat } from '@copilotkit/react-core';
import { MessageRole, TextMessage, Role } from '@copilotkit/runtime-client-gql';
import { AGENT_NAME } from '@/constants';
import { AgentState } from '@/types/agent';
import { AuthService } from '@/lib/auth';
import { User } from '@/types/user';


export default function ChatInterface() {
  const isInitialMount = useRef(true);
  const [isMounted, setIsMounted] = useState(false);
  const [canChat, setCanChat] = useState(true);
  const [remainingChats, setRemainingChats] = useState(0);
  const [user, setUser] = useState<User | null>(null);
  const authService = AuthService.getInstance();
  
  const { state, run } = useCoAgent<AgentState>({
    name: AGENT_NAME
  });

  const {appendMessage} = useCopilotChat();

  if (state.last_message_content) {
    console.log(state.last_message_content);
    appendMessage( new TextMessage({
      role: MessageRole.User,
      content: state.last_message_content
      })
    );
  }

  // Ensure component is mounted before rendering CopilotChat
  useEffect(() => {
    // Add small delay to ensure component is fully mounted
    const timer = setTimeout(() => setIsMounted(true), 50);
    return () => {
      clearTimeout(timer);
      setIsMounted(false);
    };
  }, []);

  // Periodically check chat availability and update UI
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

    // Initial check
    checkChatAvailability();

    // Set up periodic checks (every 30 seconds)
    const intervalId = setInterval(checkChatAvailability, 30000);
    
    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  const handleChatProgress = async (inProgress: boolean) => {
    if (!inProgress) {
      try {
        // Remove chat usage tracking as it's now handled in the API route
        console.log('Chat completed');
      } catch (error) {
        console.error('Error in chat completion handler:', error);
      }
    } else {
      console.log('Chat in progress');
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
        {canChat && isMounted ? (
          <div className="flex flex-col h-full">
            <p className="text-sm text-gray-500 p-2">
              Remaining chats today: {remainingChats}
            </p>
            <div className="flex-1 overflow-hidden">
              <CopilotChat
                className="h-full overflow-y-auto"
                makeSystemMessage={() => 
                  `You are a helpful assistant focusing on helping users with their questions, 
                  You must always route user queries to available backend agents first for processing. 
                  Do not attempt to answer questions directly without consulting the backend agents.}`
                }
                onInProgress={handleChatProgress}
              />
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center p-8 text-center">
            <div className="max-w-md">
              {!isMounted ? (
                <p>Loading chat interface...</p>
              ) : (
                <>
                  <p className="text-lg text-gray-700 mb-4">
                    Usage exceeds limit of {user?.usageLimit || 20} chats per day, please return tomorrow or login with a new account. 
                    This app is meant to be a demo only and therefore incurred cost is kept to the minimum! 
                    Please show some understanding towards the developer.
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 