'use client';

import React, { useEffect, useRef, useState } from 'react';
import "@copilotkit/react-ui/styles.css";
import { CopilotChat } from '@copilotkit/react-ui';
import { MessageSquare } from 'lucide-react';
import { useCopilotChat } from '@copilotkit/react-core';
import { AgentState } from '@/types/agent';
import { AuthService } from '@/lib/auth';
import { User } from '@/types/user';
import { getUserId } from '@/lib/userUtils';

interface ChatInterfaceProps {
  state: AgentState;
  setState: (state: AgentState) => void;
}

export default function ChatInterface({ state, setState }: ChatInterfaceProps) {
  const [shouldReload, setShouldReload] = useState(false);
  const [chatInProgress, setChatInProgress] = useState(false);
  const isInitialMount = useRef(true);
  const [isMounted, setIsMounted] = useState(false);
  const [canChat, setCanChat] = useState(true);
  const [remainingChats, setRemainingChats] = useState(0);
  const [user, setUser] = useState<User | null>(null);
  const authService = AuthService.getInstance();
  const { visibleMessages } = useCopilotChat();
  
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
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
        const canUserChat = await authService.checkChatLimit();
        const remaining = await authService.getRemainingChats();
        setCanChat(canUserChat);
        setRemainingChats(remaining);
      } catch (error) {
        console.error('Error checking chat availability:', error);
        // Only set canChat to false if it's a usage limit error
        // For other errors (like Firestore connection), keep canChat as true
        if (error instanceof Error && error.message.includes('usage limit')) {
          setCanChat(false);
        }
      }
    };

    // Initial check
    checkChatAvailability();

    // Set up periodic checks (every 15 seconds)
    const intervalId = setInterval(checkChatAvailability, 15000);
    
    // Clean up interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  // Add effect to log chat progress changes
  useEffect(() => {
    console.log('Chat in progress:', chatInProgress);
  }, [chatInProgress]);

  const handleChatProgress = async (inProgress: boolean) => {
    if (!inProgress && chatInProgress) {
      setChatInProgress(false);
      try {
        // Save the assistant's response to the database when chat completes
        if (visibleMessages.length > 0) {
          // Get the last message (which should be the assistant's response)
          const lastMessage = visibleMessages[visibleMessages.length - 1];
          
          // Type guard to check if it's an assistant message
          if ('role' in lastMessage && 
              lastMessage.role === 'assistant' && 
              'content' in lastMessage) {
            console.log('Saving assistant response to database');
            
            // Get message content with type safety
            const messageContent = typeof lastMessage.content === 'string' 
              ? lastMessage.content 
              : JSON.stringify(lastMessage.content);
            
            if (messageContent) {
              // Check if this is a successful response (no error_type)
              const additionalKwargs = (lastMessage as any).additional_kwargs || {};
              const isError = 'error_type' in additionalKwargs;
              
              // Only track chat usage for successful responses
              if (!isError) {
                try {
                  await authService.incrementChatUsage();
                  const remaining = await authService.getRemainingChats();
                  setRemainingChats(remaining);
                  console.log('Chat usage incremented. Remaining chats:', remaining);
                } catch (error) {
                  console.error('Error tracking chat usage:', error);
                }
              }

              // Send to the API endpoint regardless of success/error
              await fetch('/api/conversation', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                  content: messageContent,
                  user_id: getUserId(),
                  type: isError ? 'error' : 'answer'
                })
              });
              
              console.log('Assistant response saved successfully');
            }
          } else {
            console.log('Skipping chat usage tracking - last message was not from assistant');
          }
        }
      } catch (error) {
        console.error('Error saving chat response:', error);
      }
    } else if (inProgress && !chatInProgress) {
      setChatInProgress(true);
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
                  Do not attempt to answer questions directly without consulting the backend agents.
                  Do not display any intermediate responses. Only display the final response.`
                }
                key={shouldReload ? 1 : 0}
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