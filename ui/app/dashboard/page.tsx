'use client';

import { useEffect, useState } from 'react';
import { auth } from '@/lib/firebase';
import { onAuthStateChanged, User as FirebaseUser } from 'firebase/auth';
import type { User } from '@/types/user';
import { AuthService } from '@/lib/auth';
import AuthLayout from '@/components/layout/AuthLayout';
import { ProgrammingLanguage } from '@/types';
import dynamic from 'next/dynamic';
import { useLangGraphInterrupt } from '@copilotkit/react-core';

// Import CopilotKit component without SSR - fix the path
const DashboardContent = dynamic(
  () => import('../../components/DashboardContent'),
  { ssr: false }
);

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguage | "">("python");
  const authService = AuthService.getInstance();

  useLangGraphInterrupt<string>({
    render: ({ event, resolve }) => (
      <div>
        <p>{event.value}</p>
        <form onSubmit={(e) => {
          e.preventDefault();
          resolve((e.target as HTMLFormElement).response.value);
        }}>
          <input type="text" name="response" placeholder="Enter your response" />
          <button type="submit">Submit</button>
        </form>
      </div>
    )
  });

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
      <DashboardContent 
        user={user}
        selectedLanguage={selectedLanguage}
        onLanguageChange={handleLanguageChange}
        hasExceededLimit={hasExceededLimit}
      />
    </AuthLayout>
  );
} 