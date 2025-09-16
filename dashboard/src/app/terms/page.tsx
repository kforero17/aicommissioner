import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms of Service - Hall of Fame LM',
  description: 'Terms of Service for Hall of Fame LM fantasy league management platform',
}

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="mb-8">
            <Link 
              href="/auth/signup" 
              className="text-blue-600 hover:text-blue-700 text-sm font-medium mb-4 inline-block"
            >
              ← Back to Sign Up
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
            <p className="text-gray-600">Last updated: {new Date().toLocaleDateString()}</p>
          </div>

          <div className="prose prose-gray max-w-none">
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-700 mb-4">
                By accessing and using Hall of Fame LM ("the Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Description of Service</h2>
              <p className="text-gray-700 mb-4">
                Hall of Fame LM is a fantasy sports league management platform that provides automated content generation, power rankings, waiver reports, and weekly recaps for fantasy football leagues. The Service connects to third-party fantasy platforms including Yahoo Fantasy Sports, Sleeper, and ESPN (when available).
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">3. User Accounts and Data</h2>
              <p className="text-gray-700 mb-4">
                To use our Service, you must create an account and provide accurate information. You are responsible for maintaining the confidentiality of your account credentials. We access your fantasy league data only as necessary to provide our services, and we do not store sensitive personal information beyond what is required for functionality.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Third-Party Integrations</h2>
              <p className="text-gray-700 mb-4">
                Our Service integrates with third-party fantasy sports platforms. Your use of these platforms is governed by their respective terms of service. We are not responsible for the availability, accuracy, or reliability of third-party services.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Content and AI Generation</h2>
              <p className="text-gray-700 mb-4">
                The Service uses artificial intelligence to generate fantasy sports content including recaps, power rankings, and commentary. While we strive for accuracy, AI-generated content may contain errors or inaccuracies. Users should verify important information independently.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Prohibited Uses</h2>
              <p className="text-gray-700 mb-4">
                You may not use the Service for any illegal purpose or to violate any laws. You may not attempt to gain unauthorized access to our systems, interfere with the Service's operation, or use the Service to harass or harm others.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Service Availability</h2>
              <p className="text-gray-700 mb-4">
                We strive to maintain high availability but do not guarantee uninterrupted service. We may temporarily suspend the Service for maintenance, updates, or other operational reasons.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Limitation of Liability</h2>
              <p className="text-gray-700 mb-4">
                Hall of Fame LM shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of the Service. Our total liability shall not exceed the amount paid by you for the Service in the preceding 12 months.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Changes to Terms</h2>
              <p className="text-gray-700 mb-4">
                We reserve the right to modify these terms at any time. We will notify users of significant changes via email or through the Service. Continued use of the Service after changes constitutes acceptance of the new terms.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Contact Information</h2>
              <p className="text-gray-700 mb-4">
                If you have any questions about these Terms of Service, please contact us through our support channels or via email.
              </p>
            </section>
          </div>

          <div className="mt-8 pt-8 border-t border-gray-200">
            <Link 
              href="/auth/signup" 
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors duration-200"
            >
              Back to Sign Up
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
