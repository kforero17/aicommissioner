import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const normalizedBackendUrl = backendUrl.replace(/\/$/, '')
    
    return [
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

export default nextConfig
