import { 
  createUserWithEmailAndPassword, 
  signInWithEmailAndPassword,
  sendEmailVerification,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';
import { doc, setDoc, getDoc, updateDoc, serverTimestamp, collection, query, where, getDocs, Timestamp, increment } from 'firebase/firestore';
import { auth, db } from './firebase';
import { User, UserSession } from '@/types/user';
import { encrypt, decrypt } from './encryption';
import { RateLimitService } from './rateLimit';

export class AuthService {
  private static instance: AuthService;
  private currentUser: User | null = null;
  private sessionId: string | null = null;
  private rateLimitService: RateLimitService;

  private constructor() {
    this.rateLimitService = RateLimitService.getInstance();
    // Listen for auth state changes
    onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      if (firebaseUser) {
        await this.loadUserData(firebaseUser);
      } else {
        this.currentUser = null;
        this.sessionId = null;
      }
    });
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  private async loadUserData(firebaseUser: FirebaseUser): Promise<void> {
    const userDoc = await getDoc(doc(db, 'users', firebaseUser.uid));
    if (userDoc.exists()) {
      const userData = userDoc.data() as User;
      // Decrypt sensitive data
      if (userData.apiKey) {
        userData.apiKey = await decrypt(userData.apiKey);
      }
      if (userData.email) {
        userData.email = await decrypt(userData.email);
      }
      this.currentUser = userData;
    }
  }

  public async register(email: string, password: string): Promise<User> {
    try {
      // Check rate limit for registration
      const canRegister = await this.rateLimitService.checkRateLimit('anonymous', 'register');
      if (!canRegister) {
        throw new Error('Too many registration attempts. Please try again later.');
      }

      // Create user in Firebase Auth
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;

      // Configure verification email settings
      const actionCodeSettings = {
        url: `${window.location.origin}/verify-email`,  // This is where user will be redirected after verification
      };

      // Send verification email with settings
      await sendEmailVerification(firebaseUser, actionCodeSettings);

      // Generate and encrypt sensitive data
      const apiKey = Array.from(crypto.getRandomValues(new Uint8Array(16)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
      const encryptedApiKey = await encrypt(apiKey);
      const encryptedEmail = await encrypt(email);

      // Create user document in Firestore
      const user: User = {
        uid: firebaseUser.uid,
        email: encryptedEmail,
        emailVerified: false,
        createdAt: new Date(),
        lastLoginAt: null,
        apiKey: encryptedApiKey,
        usageLimit: 100, // Default limit
        currentUsage: 0,
        isActive: false, // Will be activated after email verification
        role: 'user',
        chatUsage: {
          count: 0,
          lastReset: new Date()
        }
      };

      await setDoc(doc(db, 'users', firebaseUser.uid), user);
      this.currentUser = { ...user, apiKey, email }; // Store decrypted data in memory

      return this.currentUser;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  }

  public async login(email: string, password: string): Promise<User> {
    try {
      // Check rate limit for login attempts
      const canLogin = await this.rateLimitService.checkRateLimit('anonymous', 'login');
      if (!canLogin) {
        throw new Error('Too many login attempts. Please try again later.');
      }

      // Sign in with Firebase Auth
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;
      console.log('Firebase Auth login successful');

      // Get user document from Firestore
      const userDoc = await getDoc(doc(db, 'users', firebaseUser.uid));
      const userData = userDoc.data() as User;
      console.log('Retrieved user data from Firestore');

      // Sync email verification status if there's a mismatch
      if (firebaseUser.emailVerified && !userData.emailVerified) {
        console.log('Syncing email verification status with Firestore');
        await updateDoc(doc(db, 'users', firebaseUser.uid), {
          emailVerified: true,
          isActive: true
        });
        console.log('Email verification status synced');
      }

      // Check if email is verified
      if (!firebaseUser.emailVerified) {
        throw new Error('Please verify your email before logging in.');
      }

      // Validate existing sessions
      await this.validateSessions(firebaseUser.uid);

      // Update last login
      await updateDoc(doc(db, 'users', firebaseUser.uid), {
        lastLoginAt: serverTimestamp()
      });

      // Create new session
      const session = await this.createSession(firebaseUser.uid);

      // Decrypt sensitive data
      if (userData.apiKey) {
        userData.apiKey = await decrypt(userData.apiKey);
      }

      this.currentUser = userData;
      this.sessionId = session.id;
      return userData;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  private async validateSessions(userId: string): Promise<void> {
    // Invalidate expired sessions
    const sessionsQuery = query(
      collection(db, 'sessions'),
      where('userId', '==', userId),
      where('isValid', '==', true)
    );
    
    const sessionsSnapshot = await getDocs(sessionsQuery);
    const now = new Date();
    
    for (const doc of sessionsSnapshot.docs) {
      const session = doc.data() as UserSession;
      if (session.expiresAt.toDate() < now) {
        await updateDoc(doc.ref, { isValid: false });
      }
    }
  }

  private async createSession(userId: string): Promise<UserSession> {
    // Get client IP and User-Agent
    const ipAddress = await this.getClientIP();
    const userAgent = navigator.userAgent;

    const session: UserSession = {
      id: Array.from(crypto.getRandomValues(new Uint8Array(16)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join(''),
      userId: userId,
      createdAt: new Date(),
      expiresAt: Timestamp.fromDate(new Date(Date.now() + 24 * 60 * 60 * 1000)), // 24 hours
      ipAddress: ipAddress,
      userAgent: userAgent,
      isValid: true
    };

    await setDoc(doc(db, 'sessions', session.id), session);
    return session;
  }

  private async getClientIP(): Promise<string> {
    try {
      const response = await fetch('https://api.ipify.org?format=json');
      const data = await response.json();
      return data.ip;
    } catch (error) {
      console.error('Error getting IP:', error);
      return 'unknown';
    }
  }

  public async logout(): Promise<void> {
    try {
      // Invalidate current session
      if (this.sessionId) {
        await updateDoc(doc(db, 'sessions', this.sessionId), {
          isValid: false
        });
      }
      
      await signOut(auth);
      this.currentUser = null;
      this.sessionId = null;
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }

  public async verifyEmail(actionCode: string): Promise<void> {
    try {
      // Check rate limit for email verification
      const canVerify = await this.rateLimitService.checkRateLimit('anonymous', 'verify_email');
      if (!canVerify) {
        throw new Error('Too many verification attempts. Please try again later.');
      }

      console.log('Starting email verification with action code:', actionCode);

      // First verify the email in Firebase Auth
      await auth.applyActionCode(actionCode);
      console.log('Firebase Auth email verification successful');

      // Get the user's email from the action code
      const email = await auth.checkActionCode(actionCode);
      console.log('Retrieved email from action code:', email);
      
      // Find the user document by email
      const usersRef = collection(db, 'users');
      const encryptedEmail = await encrypt(email);
      console.log('Encrypted email for query:', encryptedEmail);
      
      const q = query(usersRef, where('email', '==', encryptedEmail));
      const querySnapshot = await getDocs(q);
      
      if (querySnapshot.empty) {
        console.error('No user found with email:', email);
        throw new Error('User not found');
      }

      const userDoc = querySnapshot.docs[0];
      const userData = userDoc.data() as User;
      console.log('Found user document:', {
        uid: userData.uid,
        emailVerified: userData.emailVerified,
        isActive: userData.isActive
      });

      // Update user document
      console.log('Updating user document with emailVerified=true and isActive=true');
      await updateDoc(doc(db, 'users', userData.uid), {
        emailVerified: true,
        isActive: true
      });
      console.log('User document updated successfully');

      // Reload user data if user is signed in
      if (auth.currentUser) {
        await this.loadUserData(auth.currentUser);
      }
    } catch (error) {
      console.error('Email verification error:', error);
      throw error;
    }
  }

  public getCurrentUser(): User | null {
    return this.currentUser;
  }

  public async isAuthenticated(): Promise<boolean> {
    if (!this.currentUser || !this.sessionId) {
      return false;
    }

    // Validate current session
    const sessionDoc = await getDoc(doc(db, 'sessions', this.sessionId));
    if (!sessionDoc.exists()) {
      return false;
    }

    const session = sessionDoc.data() as UserSession;
    
    // Validate IP and User-Agent
    const currentIP = await this.getClientIP();
    const currentUserAgent = navigator.userAgent;
    
    if (session.ipAddress !== currentIP || session.userAgent !== currentUserAgent) {
      // Invalidate session if IP or User-Agent changed
      await updateDoc(doc(db, 'sessions', this.sessionId), {
        isValid: false
      });
      return false;
    }

    return session.isValid && session.expiresAt.toDate() > new Date();
  }

  public async checkChatLimit(): Promise<boolean> {
    if (!this.currentUser) {
      throw new Error('User not authenticated');
    }

    const userDoc = await getDoc(doc(db, 'users', this.currentUser.uid));
    if (!userDoc.exists()) {
      throw new Error('User document not found');
    }

    const userData = userDoc.data() as User;
    const now = new Date();
    const lastReset = new Date(userData.chatUsage.lastReset);

    // Reset count if it's a new day
    if (now.getDate() !== lastReset.getDate() || 
        now.getMonth() !== lastReset.getMonth() || 
        now.getFullYear() !== lastReset.getFullYear()) {
      await updateDoc(doc(db, 'users', this.currentUser.uid), {
        'chatUsage.count': 0,
        'chatUsage.lastReset': now
      });
      return true;
    }

    // Check if user has reached daily limit
    if (userData.chatUsage.count >= 5) {
      return false;
    }

    return true;
  }

  public async incrementChatUsage(): Promise<void> {
    if (!this.currentUser) {
      throw new Error('User not authenticated');
    }

    const userRef = doc(db, 'users', this.currentUser.uid);
    await updateDoc(userRef, {
      'chatUsage.count': increment(1)
    });

    // Update local state
    if (this.currentUser.chatUsage) {
      this.currentUser.chatUsage.count += 1;
    }
  }

  public async getRemainingChats(): Promise<number> {
    if (!this.currentUser) {
      throw new Error('User not authenticated');
    }

    const userDoc = await getDoc(doc(db, 'users', this.currentUser.uid));
    if (!userDoc.exists()) {
      throw new Error('User document not found');
    }

    const userData = userDoc.data() as User;
    return Math.max(0, 5 - userData.chatUsage.count);
  }
} 