import * as functions from 'firebase-functions';
import * as admin from 'firebase-admin';
import { UserRecord } from 'firebase-admin/auth';

// Initialize Firebase Admin
admin.initializeApp();

// Listen for email verification
export const onEmailVerified = functions.auth
  .user()
  .onEmailVerified(async (user: UserRecord) => {
    try {
      console.log('Email verification trigger received for user:', user.uid);
      console.log('User email verified status:', user.emailVerified);

      // Get the user document first to check current state
      const userDoc = await admin.firestore()
        .collection('users')
        .doc(user.uid)
        .get();

      console.log('Current Firestore document state:', userDoc.data());

      // Force update the user document in Firestore
      await admin.firestore()
        .collection('users')
        .doc(user.uid)
        .set({
          emailVerified: true,
          isActive: true,
          updatedAt: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true }); // Use merge to preserve other fields

      console.log(`Successfully updated Firestore document for user ${user.uid}`);
      return null;
    } catch (error) {
      console.error('Error updating user document:', error);
      throw error;
    }
  }); 