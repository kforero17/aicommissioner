import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'
import Navigation from '@/components/Navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Hall of Fame LM - AI Fantasy League Management',
  description: 'AI that writes recaps, tracks waivers, and keeps your league trash-talk alive.',
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
        <AuthProvider>
          <Navigation />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}