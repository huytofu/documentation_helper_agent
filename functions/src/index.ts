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
      console.log(`User ${user.uid} verified their email`);

      // Update the user document in Firestore
      await admin.firestore()
        .collection('users')
        .doc(user.uid)
        .update({
          emailVerified: true,
          isActive: true,
          updatedAt: admin.firestore.FieldValue.serverTimestamp()
        });

      console.log(`Updated Firestore document for user ${user.uid}`);
      return null;
    } catch (error) {
      console.error('Error updating user document:', error);
      throw error;
    }
  }); 