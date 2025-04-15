'use client';

import React, { useState, useEffect } from 'react';
import { AuthService } from '@/lib/auth';
import { useRouter, useSearchParams } from 'next/navigation';
import { getUserId } from '@/lib/userUtils';
import { AGENT_NAME } from '@/constants';
import { useCoAgent } from '@copilotkit/react-core';
import { AgentState } from '@/types/agent';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get('returnUrl') || '/dashboard';
  const authError = searchParams.get('error');
  const authService = AuthService.getInstance();
  const { state, setState } = useCoAgent<AgentState>({
    name: AGENT_NAME
  });

  useEffect(() => {
    // Set error message if redirected with error parameter
    if (authError) {
      setError(decodeURIComponent(authError));
    }
  }, [authError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await authService.login(email, password);
      
      // Set session cookie via API
      const response = await fetch('/api/auth/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          uid: user.uid,
          email: user.email
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to set session cookie');
      } else {
        console.log('Session cookie set successfully');
        const firebase_uid = getUserId();
        console.log('Firebase UID:', firebase_uid);
        setState({
          ...state,
          user_id: firebase_uid
          
        });
      }
      
      // Navigate to the return URL or dashboard
      router.push(returnUrl);
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || 'Failed to login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center">Login</h2>
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            required
          />
        </div>
        <div className="mb-6">
          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
      <div className="mt-4 text-center">
        <a href="/register" className="text-blue-500 hover:text-blue-600">
          Don't have an account? Register
        </a>
      </div>
    </div>
  );
} 