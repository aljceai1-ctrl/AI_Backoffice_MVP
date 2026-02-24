/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API requests to the backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // API_BACKEND_URL is server-only (NOT NEXT_PUBLIC_*) so it never leaks
        // into the client JS bundle. Defaults to Docker-internal hostname.
        destination: `${process.env.API_BACKEND_URL || 'http://backend:8000'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
