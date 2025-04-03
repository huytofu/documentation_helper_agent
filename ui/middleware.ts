import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { AuthService } from '@/lib/auth';

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

  // Redirect authenticated users away from public paths (login, register)
  if (isAuthenticated && isPublicPath) {
    console.log('Redirecting authenticated user from public path to dashboard');
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Redirect unauthenticated users to login
  if (!isAuthenticated && !isPublicPath) {
    console.log('Redirecting unauthenticated user to login');
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Allow the request to proceed
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}; 