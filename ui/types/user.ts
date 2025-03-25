import { Timestamp } from 'firebase/firestore';

export interface User {
  uid: string;
  email: string;  // Will be encrypted
  emailVerified: boolean;
  createdAt: Date;
  lastLoginAt: Date | null;
  apiKey: string;  // Already encrypted
  usageLimit: number;
  currentUsage: number;
  isActive: boolean;
  role: 'user' | 'admin';
  chatUsage: {
    count: number;
    lastReset: Date;
  };
}

export interface UserSession {
  id: string;
  userId: string;
  createdAt: Date;
  expiresAt: Timestamp;
  ipAddress: string;
  userAgent: string;
  isValid: boolean;
}

export interface RateLimit {
  userId: string;
  endpoint: string;
  count: number;
  windowStart: Timestamp;
  windowEnd: Timestamp;
} 