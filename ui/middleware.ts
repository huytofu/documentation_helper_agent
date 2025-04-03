import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  // Check cookies for auth state
  const authSessionCookie = request.cookies.get('auth_session')?.value;
  const loggedInCookie = request.cookies.get('logged_in')?.value;
  const firebaseAuthCookie = request.cookies.get('firebase:authUser')?.value;
  
  // Check for CopilotKit cookies (any cookie containing "copilotkit" in its name)
  const hasCopilotKitCookies = Array.from(request.cookies.getAll()).some(
    cookie => cookie.name.toLowerCase().includes('copilotkit')
  );
  
  // Determine authentication status
  const isAuthenticated = !!(authSessionCookie || loggedInCookie || firebaseAuthCookie);
  
  // Public paths that don't require authentication
  const publicPaths = ['/login', '/register', '/verify-email'];
  const isPublicPath = publicPaths.some(path => request.nextUrl.pathname.startsWith(path));
  
  // API paths that should be excluded from redirection
  const apiPaths = ['/api/copilotkit'];
  const isApiPath = apiPaths.some(path => request.nextUrl.pathname.startsWith(path));
  
  // Get the URL and query parameters
  const url = new URL(request.url);
  const redirectSource = url.searchParams.get('redirectSource') || '';
  
  // Prevent redirect loops
  const preventRedirectLoop = redirectSource === 'middleware';
  
  // Skip redirection for CopilotKit-related requests
  // 1. If it's a CopilotKit API endpoint
  // 2. If the request contains CopilotKit cookies
  if (isApiPath || hasCopilotKitCookies) {
    console.log('Middleware: Skipping redirection for CopilotKit request');
    return NextResponse.next();
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
      // Add original URL as a parameter for potential redirect after login
      loginUrl.searchParams.set('returnUrl', request.nextUrl.pathname);
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