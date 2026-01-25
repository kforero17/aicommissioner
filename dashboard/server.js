const { createServer } = require('http')
const { parse } = require('url')
const next = require('next')
const { createProxyMiddleware } = require('http-proxy-middleware')

const dev = process.env.NODE_ENV !== 'production'
const hostname = 'localhost'
const port = 3000

// Disable SSL verification for development
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'

const app = next({ dev, hostname, port })
const handle = app.getRequestHandler()

// Create proxy middleware with SSL bypass
const proxyMiddleware = createProxyMiddleware({
  target: 'https://localhost:8000',
  changeOrigin: true,
  secure: false, // This bypasses SSL certificate verification
  logLevel: 'debug',
  onError: (err, req, res) => {
    console.error('Proxy error:', err.message)
    res.writeHead(500, {
      'Content-Type': 'text/plain',
    })
    res.end('Proxy error: ' + err.message)
  },
  onProxyReq: (proxyReq, req, res) => {
    console.log(`Proxying ${req.method} ${req.url} to https://localhost:8000${req.url}`)
  }
})

app.prepare().then(() => {
  createServer(async (req, res) => {
    try {
      const parsedUrl = parse(req.url, true)
      const { pathname } = parsedUrl

      // Proxy auth routes to HTTPS backend
      if (pathname.startsWith('/auth/') || 
          pathname.startsWith('/api/') || 
          pathname.startsWith('/admin/')) {
        proxyMiddleware(req, res)
        return
      }

      // Handle all other routes with Next.js
      await handle(req, res, parsedUrl)
    } catch (err) {
      console.error('Error occurred handling', req.url, err)
      res.statusCode = 500
      res.end('internal server error')
    }
  })
    .once('error', (err) => {
      console.error(err)
      process.exit(1)
    })
    .listen(port, () => {
      console.log(`> Ready on http://${hostname}:${port}`)
      console.log(`> Proxying auth requests to https://localhost:8000`)
    })
})