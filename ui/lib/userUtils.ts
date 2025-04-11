/**
 * User utility functions for managing user information across the application
 */

import { auth } from './firebase';

/**
 * Gets the current user ID from various sources
 * Priority order:
 * 1. Firebase Auth (if authenticated)
 * 2. Local storage
 * 3. Cookie
 * 4. Returns 'anonymous' if no user ID is found
 */
export function getUserId(): string {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') {
    return 'server-side';
  }

  // Check Firebase Auth first
  const firebaseUser = auth.currentUser;
  if (firebaseUser) {
    return firebaseUser.uid;
  }

  // Check localStorage
  const storedUserId = localStorage.getItem('userId');
  if (storedUserId) {
    return storedUserId;
  }

  // Check cookies
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'user_id') {
      return value;
    }
  }

  // Check Firebase auth cookie
  const firebaseAuthCookie = cookies.find(c => c.trim().startsWith('firebase:authUser'));
  if (firebaseAuthCookie) {
    try {
      const cookieValue = firebaseAuthCookie.split('=')[1];
      const parsed = JSON.parse(decodeURIComponent(cookieValue));
      if (parsed.uid) {
        return parsed.uid;
      }
    } catch (error) {
      console.error('Error parsing Firebase auth cookie:', error);
    }
  }

  // Generate a temporary anonymous ID if nothing else is available
  let anonymousId = localStorage.getItem('anonymousId');
  if (!anonymousId) {
    anonymousId = `anon_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    localStorage.setItem('anonymousId', anonymousId);
  }
  
  return anonymousId;
}

/**
 * Sets a user ID cookie
 */
export function setUserIdCookie(userId: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  
  // Set cookie to expire in 30 days
  const expiryDate = new Date();
  expiryDate.setDate(expiryDate.getDate() + 30);
  
  // Set the cookie
  document.cookie = `user_id=${userId};expires=${expiryDate.toUTCString()};path=/;SameSite=Lax`;
  
  // Also store in localStorage for redundancy
  localStorage.setItem('userId', userId);
}

/**
 * Clears user ID from storage
 */
export function clearUserId(): void {
  if (typeof window === 'undefined') {
    return;
  }
  
  // Clear the cookie
  document.cookie = 'user_id=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;';
  
  // Clear localStorage
  localStorage.removeItem('userId');
  localStorage.removeItem('anonymousId');
} 