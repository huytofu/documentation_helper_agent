import { NextRequest, NextResponse } from 'next/server';
// import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    const { uid, email } = await request.json();
    
    if (!uid || !email) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Get the origin to determine which domain we're on
    const origin = request.headers.get('origin') || '';
    const isLocalhost = origin.includes('localhost');
    const isIP = origin.includes('104.255.9.187');
    
    // Create response
    const response = NextResponse.json({ success: true });
    
    // Only set cookies if we're on a valid domain
    if (isLocalhost || isIP) {
      const domain = isLocalhost ? 'localhost' : '104.255.9.187';
      
      // Set a secure, HTTP-only cookie for session tracking
      response.cookies.set('auth_session', uid, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24, // 1 day
        path: '/',
        domain
      });
      
      // Set a non-HTTP-only cookie to check logged-in state on client
      response.cookies.set('logged_in', 'true', {
        httpOnly: false,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24, // 1 day
        path: '/',
        domain
      });
    }

    return response;
  } catch (error) {
    console.error('Session API error:', error);
    return NextResponse.json(
      { error: 'Failed to set session' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    // Get the origin to determine which domain we're on
    const origin = request.headers.get('origin') || '';
    const isLocalhost = origin.includes('localhost');
    const isIP = origin.includes('104.255.9.187');
    
    // Create response
    const response = NextResponse.json({ success: true });
    
    // Only clear cookies if we're on a valid domain
    if (isLocalhost || isIP) {
      const domain = isLocalhost ? 'localhost' : '104.255.9.187';
      
      // Delete auth_session cookie
      response.cookies.set('auth_session', '', {
        expires: new Date(0),
        path: '/',
        domain
      });
      
      // Delete logged_in cookie
      response.cookies.set('logged_in', '', {
        expires: new Date(0),
        path: '/',
        domain
      });
    }
    
    return response;
  } catch (error) {
    console.error('Session logout error:', error);
    return NextResponse.json(
      { error: 'Failed to clear session' },
      { status: 500 }
    );
  }
} 