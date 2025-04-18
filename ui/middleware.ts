import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  // Check cookies for auth state
  const authSessionCookie = request.cookies.get('auth_session')?.value;
  const loggedInCookie = request.cookies.get('logged_in')?.value;
  const firebaseAuthCookie = request.cookies.get('firebase:authUser')?.value;
  
  // Get all cookies for debugging
  const allCookies = Array.from(request.cookies.getAll());
  
  // Check for CopilotKit cookies (any cookie containing "copilotkit" in its name)
  const copilotKitCookies = allCookies.filter(
    cookie => cookie.name.toLowerCase().includes('copilotkit') || 
              cookie.name.toLowerCase().includes('coagent') ||
              cookie.name.toLowerCase().includes('copilot_')
  );
  
  const hasCopilotKitCookies = copilotKitCookies.length > 0;
  
  // Log cookies for debugging, if CopilotKit cookies are present
  if (hasCopilotKitCookies) {
    console.log('Middleware: CopilotKit cookies found:', 
      copilotKitCookies.map(c => `${c.name}=${c.value.substring(0, 10)}...`)
    );
  }
  
  // Determine authentication status
  const isAuthenticated = !!(authSessionCookie || loggedInCookie || firebaseAuthCookie);
  
  // Public paths that don't require authentication
  const publicPaths = ['/login', '/register', '/verify-email', '/'];
  const isPublicPath = publicPaths.some(path => request.nextUrl.pathname.startsWith(path));
  
  // API paths that should be excluded from redirection
  const apiPaths = ['/api/copilotkit'];
  const isApiPath = apiPaths.some(path => request.nextUrl.pathname.startsWith(path));

  // Get the URL and query parameters
  const url = new URL(request.url);
  const redirectSource = url.searchParams.get('redirectSource') || '';
  
  // Prevent redirect loops
  const preventRedirectLoop = redirectSource === 'middleware';
  
  // Special handling for requests with CopilotKit context
  if (hasCopilotKitCookies) {
    console.log(`Middleware: Path ${request.nextUrl.pathname} has CopilotKit cookies, preserving context`);
    
    // Create a new response that preserves the request
    const response = NextResponse.next();
    
    // Make sure we preserve all CopilotKit cookies in the response
    copilotKitCookies.forEach(cookie => {
      response.cookies.set(cookie.name, cookie.value);
    });
    
    return response;
  }
  
  // Skip redirection for CopilotKit API endpoints
  if (isApiPath) {
    console.log('Middleware: Skipping redirection for CopilotKit API path');
    const response = NextResponse.next();
    
    // Preserve all authentication cookies for API routes
    const authCookies = allCookies.filter(
      cookie => cookie.name === 'auth_session' || 
                cookie.name === 'logged_in' || 
                cookie.name.includes('firebase:authUser')
    );
    
    // Pass auth cookies to the API route
    if (authCookies.length > 0) {
      console.log('Middleware: Preserving auth cookies for CopilotKit API path');
      authCookies.forEach(cookie => {
        response.cookies.set(cookie.name, cookie.value);
      });
    }
    
    return response;
  }
  
  // Redirect authenticated users away from public paths (login, register)
  if (isAuthenticated && isPublicPath && !preventRedirectLoop) {
    console.log('Middleware: Redirecting authenticated user to dashboard');
    const dashboardUrl = new URL('/dashboard', request.url);
    dashboardUrl.searchParams.set('redirectSource', 'middleware');
    return NextResponse.redirect(dashboardUrl);
  }

  // Redirect unauthenticated users to login
  if (!isAuthenticated && !isPublicPath) {
    // Skip API routes and static assets
    if (!request.nextUrl.pathname.startsWith('/api/') && 
        !request.nextUrl.pathname.includes('/_next/')) {
      console.log('Middleware: Redirecting unauthenticated user to login');
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirectSource', 'middleware');
      // Set returnUrl to dashboard if coming from home page, otherwise use original path
      loginUrl.searchParams.set('returnUrl', 
        request.nextUrl.pathname === '/' ? '/dashboard' : request.nextUrl.pathname
      );
      return NextResponse.redirect(loginUrl);
    }
  }

  // Allow the request to proceed
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all paths except static assets, images, and CopilotKit API endpoints
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:jpg|jpeg|gif|png|svg)).*)',
  ],
}; 