import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { AuthService } from '@/lib/auth';
import { cookies } from 'next/headers';

export async function middleware(request: NextRequest) {
  const authService = AuthService.getInstance();
  const isAuthenticated = await authService.isAuthenticated();
  
  // Check for firebase auth cookie as additional authentication verification
  const authCookie = request.cookies.get('firebase:authUser');
  const hasAuthCookie = !!authCookie;
  
  // Public paths that don't require authentication
  const publicPaths = ['/login', '/register', '/verify-email'];
  const isPublicPath = publicPaths.some(path => request.nextUrl.pathname.startsWith(path));

  // Redirect authenticated users away from public paths
  if ((isAuthenticated || hasAuthCookie) && isPublicPath) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Redirect unauthenticated users to login
  if (!isAuthenticated && !hasAuthCookie && !isPublicPath) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

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