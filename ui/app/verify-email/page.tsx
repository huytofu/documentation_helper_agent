'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { AuthService } from '@/lib/auth';
import { useRouter } from 'next/navigation';

export default function VerifyEmailPage() {
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(true);
  const searchParams = useSearchParams();
  const router = useRouter();
  const authService = AuthService.getInstance();

  useEffect(() => {
    console.log('VerifyEmailPage loaded');
    console.log('Search params:', Object.fromEntries(searchParams.entries()));

    const verifyEmail = async () => {
      try {
        const actionCode = searchParams.get('oobCode');
        console.log('Action code from URL:', actionCode);
        
        if (!actionCode) {
          throw new Error('Invalid verification link');
        }

        console.log('Starting email verification...');
        await authService.verifyEmail(actionCode);
        console.log('Email verification completed successfully');
        setSuccess('Email verified successfully! You can now log in.');
        setTimeout(() => {
          router.push('/login');
        }, 3000);
      } catch (err: any) {
        console.error('Verification error:', err);
        setError(err.message || 'Failed to verify email');
      } finally {
        setLoading(false);
      }
    };

    verifyEmail();
  }, [searchParams, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
          <div className="flex justify-center items-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-100 text-green-700 rounded">
            {success}
          </div>
        )}
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Email Verification</h2>
          {!error && !success && (
            <p className="text-gray-600">Verifying your email...</p>
          )}
        </div>
      </div>
    </div>
  );
} 