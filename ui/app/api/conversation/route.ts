import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_ENDPOINT } from '@/constants';
import { getUserId } from '@/lib/userUtils';

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
    
    // Get the endpoint for conversation history
    const backendUrl = `${BACKEND_ENDPOINT}/conversation`;
    
    console.log('Sending conversation data to backend:', payload);
    console.log('Backend URL:', backendUrl);
    
    // Send request to backend
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    // If backend request failed
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      console.error('Backend conversation API error:', errorData);
      return NextResponse.json(
        { success: false, error: errorData?.error || 'Backend service error' },
        { status: response.status }
      );
    }
    
    // Return the backend response
    const responseData = await response.json();
    return NextResponse.json(responseData);
    
  } catch (error) {
    console.error('Conversation API error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to save conversation' },
      { status: 500 }
    );
  }
} 