/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Get backend URL from environment with fallback to localhost
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    
    // Ensure protocol is included and strip trailing slash
    const normalizedBackendUrl = backendUrl.replace(/\/$/, '')
    
    return [
      // Proxy API calls to the backend
      {
        source: '/api/:path*',
        destination: `${normalizedBackendUrl}/api/:path*`,
      },
      {
        source: '/auth/:path*',
        destination: `${normalizedBackendUrl}/auth/:path*`,
      },
      {
        source: '/connect/:path*',
        destination: `${normalizedBackendUrl}/connect/:path*`,
      },
      {
        source: '/admin/:path*',
        destination: `${normalizedBackendUrl}/admin/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
