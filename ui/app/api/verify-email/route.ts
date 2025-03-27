import { NextResponse } from 'next/server';
import admin from 'firebase-admin';
import type { ListUsersResult, UserRecord } from 'firebase-admin/auth';

// Initialize Firebase Admin if not already initialized
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert({
      projectId: process.env.FIREBASE_PROJECT_ID,
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
      privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
    })
  });
}

// Set up auth state listener
const auth = admin.auth();
const db = admin.firestore();

// Listen to user creation and updates
auth.listUsers().then(async (listUsersResult: ListUsersResult) => {
  console.log('Setting up auth state listener');
  
  listUsersResult.users.forEach(async (userRecord: UserRecord) => {
    // Check if user's email is verified
    if (userRecord.emailVerified) {
      try {
        // Update Firestore document
        await db.collection('users').doc(userRecord.uid).update({
          emailVerified: true,
          isActive: true,
          updatedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        console.log(`Updated Firestore for verified user: ${userRecord.uid}`);
      } catch (error: unknown) {
        console.error(`Error updating user ${userRecord.uid}:`, error);
      }
    }
  });
});

// Set up ongoing listener for user changes
auth.onUserChanged((user: UserRecord | null) => {
  if (user && user.emailVerified) {
    db.collection('users').doc(user.uid).update({
      emailVerified: true,
      isActive: true,
      updatedAt: admin.firestore.FieldValue.serverTimestamp()
    }).then(() => {
      console.log(`Updated Firestore for user: ${user.uid}`);
    }).catch((error: unknown) => {
      console.error(`Error updating user ${user.uid}:`, error);
    });
  }
});

// Add user to pending verifications
export async function POST(request: Request) {
  try {
    const { uid } = await request.json();

    if (!uid) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }

    // Add to pending verifications collection
    await db.collection('pendingVerifications').doc(uid).set({
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
      status: 'pending'
    });

    // Start background polling (runs every second for 1 hour max)
    let attempts = 0;
    const maxAttempts = 3600; // 1 hour worth of seconds

    const pollVerification = async () => {
      try {
        // Check if we should stop polling
        const pendingDoc = await db.collection('pendingVerifications').doc(uid).get();
        if (!pendingDoc.exists || pendingDoc.data()?.status === 'completed') {
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          await db.collection('pendingVerifications').doc(uid).delete();
          return;
        }

        // Check user's verification status
        const userRecord = await auth.getUser(uid);
        console.log(`Checking verification for user ${uid}, attempt ${attempts}`);

        if (userRecord.emailVerified) {
          // Update user document
          await db.collection('users').doc(uid).set({
            emailVerified: true,
            isActive: true,
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
          }, { merge: true });

          // Mark verification as completed
          await db.collection('pendingVerifications').doc(uid).delete();
          console.log(`User ${uid} verified and updated successfully`);
          return;
        }

        // Continue polling
        setTimeout(pollVerification, 1000);
      } catch (error) {
        console.error('Error in verification polling:', error);
        // Continue polling despite error
        setTimeout(pollVerification, 1000);
      }
    };

    // Start polling
    pollVerification();

    return NextResponse.json({
      success: true,
      message: 'Started verification polling'
    });

  } catch (error: any) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
} 