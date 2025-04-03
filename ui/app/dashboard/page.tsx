'use client';

import { useEffect, useState } from 'react';
import { auth } from '@/lib/firebase';
import { onAuthStateChanged, User as FirebaseUser } from 'firebase/auth';
import type { User } from '@/types/user';
import { AuthService } from '@/lib/auth';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { Header } from '@/components/Header';
import { LanguageSelector } from '@/components/LanguageSelector';
import { ChatInterface } from '@/components/ChatInterface';
import { AgentStatePanel } from '@/components/AgentStatePanel';
import { ProgrammingLanguage } from '@/types';
import { AlertTriangle } from 'lucide-react';

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguage | "">("");
  const authService = AuthService.getInstance();

  useEffect(() => {
    // Fetch user data
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      if (firebaseUser) {
        try {
          console.log('User is authenticated:', firebaseUser.uid);
          // Get user data from auth service
          const currentUser = authService.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error('Failed to load user data:', error);
        } finally {
          setLoading(false);
        }
      } else {
        console.log('No Firebase user found - middleware will handle redirection if needed');
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, [authService]);

  const handleLanguageChange = (language: ProgrammingLanguage | "") => {
    setSelectedLanguage(language);
  };

  // Check if user has exceeded usage limit
  const hasExceededLimit = (user?.chatUsage?.count || 0) > (user?.usageLimit || 20);

  if (loading) {
    return (
      <AuthLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className="flex flex-col space-y-6 w-full">
        {/* Header */}
        <Header />
        
        {/* Main content */}
        <div className="container mx-auto px-4">
          {/* Language Selector */}
          <div className="mb-6">
            <LanguageSelector 
              selectedLanguage={selectedLanguage} 
              onLanguageChange={handleLanguageChange} 
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
    </AuthLayout>
  );
} 