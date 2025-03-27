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

// The actual endpoint can be simpler now
export async function POST(request: Request) {
  try {
    const { uid } = await request.json();

    if (!uid) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      );
    }

    // Get the user from Admin SDK
    const userRecord = await auth.getUser(uid);

    return NextResponse.json({
      success: true,
      emailVerified: userRecord.emailVerified,
      message: 'User status checked successfully'
    });

  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Error checking user status:', error);
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
} 