import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  // Check cookies for auth state
  const authSessionCookie = request.cookies.get('auth_session')?.value;
  const loggedInCookie = request.cookies.get('logged_in')?.value;
  const firebaseAuthCookie = request.cookies.get('firebase:authUser')?.value;
  
  // Determine authentication status
  const isAuthenticated = !!(authSessionCookie || loggedInCookie || firebaseAuthCookie);
  
  // Public paths that don't require authentication
  const publicPaths = ['/login', '/register', '/verify-email'];
  const isPublicPath = publicPaths.some(path => request.nextUrl.pathname.startsWith(path));
  
  // Get the URL and query parameters
  const url = new URL(request.url);
  const redirectSource = url.searchParams.get('redirectSource') || '';
  
  // Prevent redirect loops
  const preventRedirectLoop = redirectSource === 'middleware';
  
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
    // Match all paths except static assets and images
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:jpg|jpeg|gif|png|svg)).*)',
  ],
}; 