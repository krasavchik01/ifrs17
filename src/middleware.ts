import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token;
    const path = req.nextUrl.pathname;

    // Public paths
    if (path.startsWith('/api/auth') || path === '/') {
      return NextResponse.next();
    }

    // Protect dashboard and app routes
    if (path.startsWith('/dashboard') || path.startsWith('/contracts') || path.startsWith('/reports')) {
      if (!token) {
        return NextResponse.redirect(new URL('/auth/signin', req.url));
      }

      // Check subscription status
      if (token.organization?.subscriptionStatus !== 'active') {
        return NextResponse.redirect(new URL('/subscription/inactive', req.url));
      }
    }

    // Admin only routes
    if (path.startsWith('/admin')) {
      if (token?.role !== 'admin') {
        return NextResponse.redirect(new URL('/dashboard', req.url));
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
  }
);

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/contracts/:path*',
    '/reports/:path*',
    '/settings/:path*',
    '/admin/:path*',
    '/api/contracts/:path*',
    '/api/csm/:path*',
    '/api/reports/:path*',
  ],
};
