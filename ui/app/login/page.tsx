'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { auth } from '@/lib/firebase';
import { LoginForm } from '@/components/auth/LoginForm';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Add polling for email verification
  useEffect(() => {
    console.log('Starting verification check polling from login page');
    
    const checkVerification = async () => {
      try {
        const user = auth.currentUser;
        if (!user) {
          // No user, might be logged out or not registered yet
          return;
        }

        // Only proceed if email is not verified yet
        if (!user.emailVerified) {
          // Reload user to get fresh status
          await user.reload();
          console.log('Checking email verification status:', user.emailVerified);

          if (user.emailVerified) {
            console.log('Email verified, updating Firestore...');
            
            // Call our API to update Firestore
            const response = await fetch('/api/verify-email', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ uid: user.uid }),
            });

            const data = await response.json();
            if (data.success) {
              console.log('Firestore updated successfully');
            } else {
              console.error('Failed to update Firestore:', data.error);
            }
          }
        }
      } catch (error) {
        console.error('Error checking verification:', error);
      }
    };

    // Start polling every 1 second
    const interval = setInterval(checkVerification, 1000);

    // Initial check
    checkVerification();

    // Cleanup on unmount
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // Your existing login logic here
    } catch (error: any) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <LoginForm />
    </div>
  );
} 