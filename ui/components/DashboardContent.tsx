'use client';

import React, { useState, useEffect } from 'react';
import { CopilotKit } from '@copilotkit/react-core';
import dynamic from 'next/dynamic';
import Header from '@/components/Header';
import LanguageSelector from '@/components/LanguageSelector';
import { AlertTriangle } from 'lucide-react';
import { ProgrammingLanguage } from '@/types';
import { User } from '@/types/user';
import { AGENT_NAME } from '@/constants';

// Dynamically import components that use CopilotKit features
const ChatInterface = dynamic(() => import('@/components/ChatInterface'), { ssr: false });
const AgentStatePanel = dynamic(() => import('@/components/AgentStatePanel'), { ssr: false });

interface DashboardContentProps {
  user: User | null;
  selectedLanguage: ProgrammingLanguage | "";
  onLanguageChange: (language: ProgrammingLanguage | "") => void;
  hasExceededLimit: boolean;
}

export default function DashboardContent({ 
  user, 
  selectedLanguage, 
  onLanguageChange,
  hasExceededLimit 
}: DashboardContentProps) {
  // State to track if we're mounted on the client
  const [mounted, setMounted] = useState(false);

  // Set mounted to true when component mounts on client
  useEffect(() => {
    setMounted(true);
  }, []);

  // Don't render anything with CopilotKit until we're mounted on client
  if (!mounted) {
    return <div>Loading dashboard...</div>;
  }

  return (
    <div className="flex flex-col space-y-6 w-full">
    {/* Header */}
    <Header />
    
    {/* Main content */}
    <div className="container mx-auto px-4">
        {/* Language Selector */}
        <div className="mb-6">
        <LanguageSelector 
            selectedLanguage={selectedLanguage} 
            onLanguageChange={onLanguageChange} 
        />
        </div>

        {/* Chat and Agent State or Warning */}
        {hasExceededLimit ? (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
            <div className="flex justify-center mb-4">
            <AlertTriangle className="h-12 w-12 text-amber-500" />
            </div>
            <h2 className="text-2xl font-bold text-amber-700 mb-3">
            Daily Usage Limit Exceeded
            </h2>
            <p className="text-amber-600 mb-6 max-w-2xl mx-auto">
            You've reached your limit of {user?.usageLimit} chats for today. 
            Please come back tomorrow when your limit resets, or login with another account to continue using the chat feature.
            </p>
            <div className="bg-white rounded-lg p-3 inline-block">
            <p className="text-sm font-medium text-gray-500">
                Current usage: {user?.chatUsage?.count || 0} / {user?.usageLimit || 20} chats
            </p>
            </div>
        </div>
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Chat Interface - Takes 3/4 of the width on large screens */}
            <div className="lg:col-span-3">
            <ChatInterface />
            </div>
            
            {/* Agent State Panel - Takes 1/4 of the width on large screens */}
            <div className="lg:col-span-1">
            <AgentStatePanel />
            </div>
        </div>
        )}
    </div>
    </div>
  );
} 