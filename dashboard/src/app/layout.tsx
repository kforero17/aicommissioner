import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Commissioner Dashboard',
  description: 'Manage your fantasy football leagues with AI-powered recaps',
}

/**
 * Root layout for the dashboard app.
 *
 * Renders the top-level HTML scaffold using the Inter font, a fixed navigation bar
 * with the brand ("🏈 AI Commissioner") and links to "/connect" and "/preview",
 * and injects the routed page content via `children`.
 *
 * @param children - Page content to render below the navigation bar.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="text-xl font-bold text-gray-900">
                  🏈 AI Commissioner
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link 
                  href="/connect" 
                  className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Connect
                </Link>
                <Link 
                  href="/preview" 
                  className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                >
                  Preview
                </Link>
              </div>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}