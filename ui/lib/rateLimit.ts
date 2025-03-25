import { doc, getDoc, setDoc, updateDoc, increment, Timestamp } from 'firebase/firestore';
import { db } from './firebase';

interface RateLimit {
  userId: string;
  endpoint: string;
  count: number;
  windowStart: Timestamp;
  windowEnd: Timestamp;
}

export class RateLimitService {
  private static instance: RateLimitService;
  private readonly WINDOW_SIZE = 60 * 60 * 1000; // 1 hour in milliseconds
  private readonly MAX_REQUESTS = 100; // requests per hour

  private constructor() {}

  public static getInstance(): RateLimitService {
    if (!RateLimitService.instance) {
      RateLimitService.instance = new RateLimitService();
    }
    return RateLimitService.instance;
  }

  public async checkRateLimit(userId: string, endpoint: string): Promise<boolean> {
    const now = new Date();
    const rateLimitRef = doc(db, 'rateLimits', `${userId}_${endpoint}`);
    const rateLimitDoc = await getDoc(rateLimitRef);

    if (!rateLimitDoc.exists()) {
      // Create new rate limit document
      const rateLimit: RateLimit = {
        userId,
        endpoint,
        count: 1,
        windowStart: Timestamp.fromDate(now),
        windowEnd: Timestamp.fromDate(new Date(now.getTime() + this.WINDOW_SIZE))
      };
      await setDoc(rateLimitRef, rateLimit);
      return true;
    }

    const rateLimit = rateLimitDoc.data() as RateLimit;
    const windowEnd = rateLimit.windowEnd.toDate();

    if (now > windowEnd) {
      // Reset window
      await setDoc(rateLimitRef, {
        ...rateLimit,
        count: 1,
        windowStart: Timestamp.fromDate(now),
        windowEnd: Timestamp.fromDate(new Date(now.getTime() + this.WINDOW_SIZE))
      });
      return true;
    }

    if (rateLimit.count >= this.MAX_REQUESTS) {
      return false;
    }

    // Increment count
    await updateDoc(rateLimitRef, {
      count: increment(1)
    });

    return true;
  }

  public async getRateLimitInfo(userId: string, endpoint: string): Promise<{
    remaining: number;
    resetTime: Date;
  }> {
    const rateLimitRef = doc(db, 'rateLimits', `${userId}_${endpoint}`);
    const rateLimitDoc = await getDoc(rateLimitRef);

    if (!rateLimitDoc.exists()) {
      return {
        remaining: this.MAX_REQUESTS,
        resetTime: new Date(Date.now() + this.WINDOW_SIZE)
      };
    }

    const rateLimit = rateLimitDoc.data() as RateLimit;
    const now = new Date();
    const windowEnd = rateLimit.windowEnd.toDate();

    if (now > windowEnd) {
      return {
        remaining: this.MAX_REQUESTS,
        resetTime: new Date(now.getTime() + this.WINDOW_SIZE)
      };
    }

    return {
      remaining: this.MAX_REQUESTS - rateLimit.count,
      resetTime: windowEnd
    };
  }
} 