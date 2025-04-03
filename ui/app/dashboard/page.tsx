'use client';

import { AuthLayout } from '@/components/layout/AuthLayout';
import { AuthService } from '@/lib/auth';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { auth } from '@/lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import type { User } from '@/types/user';

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const authService = AuthService.getInstance();

  useEffect(() => {
    // Use a simple function to check cookies directly
    const checkAuthentication = () => {
      const isLoggedIn = document.cookie.includes('logged_in=true') || 
                          document.cookie.includes('firebase:authUser');
      
      if (!isLoggedIn) {
        console.log('No session cookie found, redirecting to login');
        window.location.href = '/login';
        return;
      }
    };
    
    // Check cookies first (synchronous)
    checkAuthentication();
    
    // Then check Firebase auth state (asynchronous)
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
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
        console.log('Firebase auth check: No user found, redirecting to login');
        window.location.href = '/login';
      }
    });

    return () => unsubscribe();
  }, [router, authService]);

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
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Welcome, {user?.email}</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Account Status</h2>
            <p className="text-sm text-gray-600">
              {user?.emailVerified ? 'Email Verified' : 'Email Not Verified'}
            </p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <h2 className="text-lg font-semibold mb-2">Usage</h2>
            <p className="text-sm text-gray-600">
              {user?.currentUsage || 0} / {user?.usageLimit || 100} requests
            </p>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
} 