'use client'

import { useState } from 'react'

/**
 * Client-side page component that renders UI to connect Yahoo Fantasy and Sleeper leagues.
 *
 * Renders two connection panels: a Yahoo section that redirects the browser to `/auth/yahoo/start`
 * when the "Connect Yahoo" button is clicked, and a Sleeper section with a form that accepts a
 * required `league_id` and optional `groupme_bot_id`. Submitting the Sleeper form validates the
 * league ID, sends a POST to `/connect/sleeper` with the provided data, and displays status
 * feedback. While the request is in flight a loading state disables the submit button and updates
 * its label.
 */
export default function ConnectPage() {
  const [sleeperData, setSleeperData] = useState({
    league_id: '',
    groupme_bot_id: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleYahooConnect = () => {
    // Redirect to Yahoo OAuth start
    window.location.href = '/auth/yahoo/start'
  }

  const handleSleeperConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!sleeperData.league_id) {
      setMessage('League ID is required')
      return
    }

    setLoading(true)
    setMessage('')

    try {
      const response = await fetch('/connect/sleeper', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sleeperData),
      })

      if (response.ok) {
        setMessage('Sleeper league connected successfully!')
        setSleeperData({ league_id: '', groupme_bot_id: '' })
      } else {
        const error = await response.text()
        setMessage(`Failed to connect: ${error}`)
      }
    } catch {
      setMessage('Network error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            Connect Your League
          </h1>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Yahoo Fantasy</h2>
          <p className="text-gray-600 mb-4">
            Connect your Yahoo Fantasy leagues to enable automated recaps and analysis.
          </p>
          <button
            onClick={handleYahooConnect}
            className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200"
          >
            Connect Yahoo
          </button>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Sleeper League</h2>
          <form onSubmit={handleSleeperConnect}>
            <div className="mb-4">
              <label htmlFor="league_id" className="block text-sm font-medium text-gray-700 mb-2">
                League ID *
              </label>
              <input
                type="text"
                id="league_id"
                value={sleeperData.league_id}
                onChange={(e) => setSleeperData(prev => ({ ...prev, league_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter Sleeper league ID"
                required
              />
            </div>

            <div className="mb-4">
              <label htmlFor="groupme_bot_id" className="block text-sm font-medium text-gray-700 mb-2">
                GroupMe Bot ID (optional)
              </label>
              <input
                type="text"
                id="groupme_bot_id"
                value={sleeperData.groupme_bot_id}
                onChange={(e) => setSleeperData(prev => ({ ...prev, groupme_bot_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter GroupMe bot ID (optional)"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-2 px-4 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 ${
                loading 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {loading ? 'Connecting...' : 'Connect Sleeper League'}
            </button>
          </form>
        </div>

        {message && (
          <div className={`mt-4 p-4 rounded-md ${
            message.includes('successfully') 
              ? 'bg-green-100 text-green-700' 
              : 'bg-red-100 text-red-700'
          }`}>
            {message}
          </div>
        )}
      </div>
    </div>
  )
}
