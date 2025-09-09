import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 sm:text-6xl">
            🏈 AI Commissioner
          </h1>
          <p className="mt-6 text-xl text-gray-600 max-w-3xl mx-auto">
            Automate your fantasy football league with AI-powered recaps, power rankings, 
            and waiver wire analysis. Connect your leagues and let the AI handle the commentary.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center">
              <div className="text-3xl mb-4">🔗</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Connect Leagues</h3>
              <p className="text-gray-600 text-sm mb-4">
                Link your Yahoo Fantasy or Sleeper leagues to get started
              </p>
              <Link 
                href="/connect"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Connect Now
              </Link>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center">
              <div className="text-3xl mb-4">⚙️</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Configure Settings</h3>
              <p className="text-gray-600 text-sm mb-4">
                Set up your recap schedule and AI personality style
              </p>
              <Link 
                href="/settings/1"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
              >
                Settings
              </Link>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center">
              <div className="text-3xl mb-4">👁️</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Preview Content</h3>
              <p className="text-gray-600 text-sm mb-4">
                Test your settings and see generated recaps before publishing
              </p>
              <Link 
                href="/preview"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700"
              >
                Preview
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-16 bg-white rounded-lg shadow p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">🏆 Power Rankings</h3>
              <p className="text-gray-600">
                Automated Tuesday power rankings with matchup analysis and team performance insights.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">💰 Waiver Reports</h3>
              <p className="text-gray-600">
                Wednesday waiver wire recaps tracking FAAB spending and transaction activity.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">🤖 AI Personalities</h3>
              <p className="text-gray-600">
                Choose from balanced, snark, hype, or nerd writing styles for personalized content.
              </p>
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">📱 Multi-Platform</h3>
              <p className="text-gray-600">
                Publish to GroupMe and email automatically. Never miss a league update.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}