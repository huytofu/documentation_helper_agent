import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_ENDPOINT } from '@/constants';
import { getUserId } from '@/lib/userUtils';
const DOCUMENTATION_HELPER_API_KEY = process.env.DOCUMENTATION_HELPER_API_KEY;

/**
 * API endpoint for saving conversation history (singular version)
 * This route forwards requests to the Python backend
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();
    
    // Extract data from request
    let { message, user_id, type } = body;
    
    // Get message content from the message object if provided
    let content = message?.content || body.content || '';
    
    // If no content was found directly, check for nested content
    if (!content && message?.additional_kwargs?.content) {
      content = message.additional_kwargs.content;
    }
    
    // Validate content
    if (!content) {
      return NextResponse.json(
        { success: false, error: 'Message content is required' },
        { status: 400 }
      );
    }
    
    // Validate message type
    if (!type || (type !== 'question' && type !== 'answer')) {
      return NextResponse.json(
        { success: false, error: 'Valid message type (question/answer) is required' },
        { status: 400 }
      );
    }
    
    // If user_id is not provided, try to get it from userUtils
    if (!user_id) {
      user_id = getUserId();
      console.log('Using user ID from userUtils:', user_id);
    }
    
    // Prepare payload for the backend
    const payload = {
      user_id,
      type,
      content
    };
    
    // Set up the possible backend URLs to try in sequence
    let backendUrls = [
        `${BACKEND_ENDPOINT.split('copilotkitagent')[0]}conversation`,
    ]
    
    console.log('Sending conversation data to backend:', payload);
    
    // Try each URL in sequence until one succeeds
    for (let i = 0; i < backendUrls.length; i++) {
      try {
        console.log(`Trying backend URL #${i + 1}:`, backendUrls[i]);
        const result = await sendRequest(backendUrls[i], payload);
        console.log(`Backend URL #${i + 1} succeeded!`);
        return result; // Return successful result and stop trying other URLs
      } catch (error) {
        console.error(`Backend URL #${i + 1} failed:`, error);
        // If this is the last URL, throw the error to be caught by the outer catch block
        if (i === backendUrls.length - 1) {
          throw error;
        }
        // Otherwise, continue to the next URL
        console.log(`Trying next URL...`);
      }
    }
    
    // This code should never be reached because either a URL succeeds or the last one throws
    throw new Error('All backend URLs failed');
    
  } catch (error) {
    console.error('All backend URLs failed:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to save conversation to any endpoint' },
      { status: 500 }
    );
  }
} 

async function sendRequest(url: string, payload: any) {
  // Send request to backend
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': DOCUMENTATION_HELPER_API_KEY || ''
    },
    body: JSON.stringify(payload)
  });
  
  // If backend request failed
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    console.error('Backend conversation API error:', errorData);
    console.error('Response status:', response.status);
    
    // Throw error to be caught by the calling function
    throw new Error(`API error: ${response.status} ${errorData?.error || ''}`);
  }
  
  // Return the backend response
  const responseData = await response.json();
  console.log('Successful response from backend:', responseData);
  return NextResponse.json(responseData);
}
