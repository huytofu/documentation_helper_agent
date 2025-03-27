import { auth, db } from '../lib/firebase';
import { doc, setDoc, Timestamp } from 'firebase/firestore';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { encrypt } from '../lib/encryption';

// Create a test user
async function createTestUser() {
  try {
    const email = 'test@example.com';
    const password = 'testPassword123!';
    
    // Create user in Firebase Auth
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    // Generate and encrypt sensitive data
    const apiKey = crypto.randomUUID();
    const encryptedApiKey = encrypt(apiKey);
    const encryptedEmail = encrypt(email);

    // Create user document
    await setDoc(doc(db, 'users', user.uid), {
      uid: user.uid,
      email: encryptedEmail,
      emailVerified: false,
      createdAt: Timestamp.now(),
      lastLoginAt: null,
      apiKey: encryptedApiKey,
      usageLimit: 100,
      currentUsage: 0,
      isActive: false,
      role: 'user',
      chatUsage: {
        count: 0,
        lastReset: Timestamp.now()
      }
    });

    console.log('Test user created successfully');
  } catch (error) {
    console.error('Error creating test user:', error);
  }
}

// Initialize database
async function initializeDatabase() {
  try {
    // Create test user
    await createTestUser();
    
    console.log('Database initialized successfully');
  } catch (error) {
    console.error('Error initializing database:', error);
  }
}

// Run initialization
initializeDatabase(); 