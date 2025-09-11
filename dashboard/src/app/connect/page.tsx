'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function ConnectPage() {
  const [activeTab, setActiveTab] = useState<'yahoo' | 'sleeper' | 'espn'>('yahoo')
  const [sleeperData, setSleeperData] = useState({
    league_id: '',
    username: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [step, setStep] = useState(1)

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
        setSleeperData({ league_id: '', username: '' })
        setStep(2)
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                1
              </div>
              <span className="text-sm font-medium text-gray-900">Connect League</span>
            </div>
            
            <div className="flex-1 h-1 bg-gray-200 rounded">
              <div className={`h-1 rounded transition-all duration-300 ${
                step >= 2 ? 'bg-blue-600 w-1/3' : 'bg-gray-200 w-0'
              }`}></div>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                2
              </div>
              <span className="text-sm font-medium text-gray-600">Verify & Setup</span>
            </div>
            
            <div className="flex-1 h-1 bg-gray-200 rounded">
              <div className={`h-1 rounded transition-all duration-300 ${
                step >= 3 ? 'bg-blue-600 w-2/3' : 'bg-gray-200 w-0'
              }`}></div>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                3
              </div>
              <span className="text-sm font-medium text-gray-600">Go Live</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Connect Your Fantasy League
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Link your league to start automating power rankings, waiver reports, and weekly recaps
            </p>
          </div>

          {step === 1 && (
            <div className="max-w-2xl mx-auto">
              {/* Platform Tabs */}
              <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-8">
                <button
                  onClick={() => setActiveTab('yahoo')}
                  className={`flex-1 py-3 px-4 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'yahoo'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Yahoo Fantasy
                </button>
                <button
                  onClick={() => setActiveTab('sleeper')}
                  className={`flex-1 py-3 px-4 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'sleeper'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Sleeper
                </button>
                <button
                  onClick={() => setActiveTab('espn')}
                  className={`flex-1 py-3 px-4 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'espn'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  ESPN (Soon)
                </button>
              </div>

              {/* Yahoo Content */}
              {activeTab === 'yahoo' && (
                <div className="bg-white rounded-xl shadow-lg p-8">
                  <div className="flex items-center mb-6">
                    <div className="bg-purple-100 w-12 h-12 rounded-full flex items-center justify-center mr-4">
                      <svg className="w-6 h-6 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900">Yahoo Fantasy Sports</h3>
                      <p className="text-gray-600">Most popular option • OAuth secure connection</p>
                    </div>
                  </div>
                  
                  <div className="mb-6">
                    <h4 className="font-medium text-gray-900 mb-3">What you'll get:</h4>
                    <ul className="space-y-2 text-gray-600">
                      <li className="flex items-center">
                        <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Automatic access to all your leagues
                      </li>
                      <li className="flex items-center">
                        <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Real-time roster and transaction data
                      </li>
                      <li className="flex items-center">
                        <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Weekly matchup and scoring information
                      </li>
                    </ul>
                  </div>

                  <button
                    onClick={handleYahooConnect}
                    className="w-full bg-purple-600 text-white py-4 px-6 rounded-lg hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200 text-lg font-medium"
                  >
                    Connect with Yahoo
                  </button>
                  
                  <p className="text-xs text-gray-500 text-center mt-4">
                    We'll redirect you to Yahoo to securely authorize access to your leagues
                  </p>
                </div>
              )}

              {/* Sleeper Content */}
              {activeTab === 'sleeper' && (
                <div className="bg-white rounded-xl shadow-lg p-8">
                  <div className="flex items-center mb-6">
                    <div className="bg-orange-100 w-12 h-12 rounded-full flex items-center justify-center mr-4">
                      <svg className="w-6 h-6 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900">Sleeper Fantasy</h3>
                      <p className="text-gray-600">Popular dynasty platform • League ID required</p>
                    </div>
                  </div>

                  <form onSubmit={handleSleeperConnect} className="space-y-6">
                    <div>
                      <label htmlFor="league_id" className="block text-sm font-medium text-gray-700 mb-2">
                        League ID *
                      </label>
                      <input
                        type="text"
                        id="league_id"
                        value={sleeperData.league_id}
                        onChange={(e) => setSleeperData(prev => ({ ...prev, league_id: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="e.g. 123456789012345678"
                        required
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Find this in your Sleeper app: League → Settings → League ID
                      </p>
                    </div>

                    <div>
                      <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                        Your Sleeper Username (optional)
                      </label>
                      <input
                        type="text"
                        id="username"
                        value={sleeperData.username}
                        onChange={(e) => setSleeperData(prev => ({ ...prev, username: e.target.value }))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Your Sleeper username"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Helps us identify your team for verification
                      </p>
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className={`w-full py-4 px-6 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 text-lg font-medium ${
                        loading 
                          ? 'bg-gray-400 cursor-not-allowed' 
                          : 'bg-blue-600 hover:bg-blue-700'
                      }`}
                    >
                      {loading ? (
                        <div className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Connecting...
                        </div>
                      ) : (
                        'Connect Sleeper League'
                      )}
                    </button>
                  </form>
                </div>
              )}

              {/* ESPN Content */}
              {activeTab === 'espn' && (
                <div className="bg-white rounded-xl shadow-lg p-8">
                  <div className="flex items-center mb-6">
                    <div className="bg-red-100 w-12 h-12 rounded-full flex items-center justify-center mr-4">
                      <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900">ESPN Fantasy</h3>
                      <p className="text-gray-600">Coming soon • Traditional fantasy platform</p>
                    </div>
                  </div>
                  
                  <div className="text-center py-8">
                    <p className="text-gray-600 mb-6">
                      ESPN integration is currently in development. Join our waitlist to be notified when it's ready!
                    </p>
                    <button
                      disabled
                      className="bg-gray-300 text-gray-500 py-4 px-6 rounded-lg cursor-not-allowed text-lg font-medium"
                    >
                      Coming Soon
                    </button>
                  </div>
                </div>
              )}

              {message && (
                <div className={`mt-6 p-4 rounded-lg ${
                  message.includes('successfully') 
                    ? 'bg-green-50 text-green-700 border border-green-200' 
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {message}
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="max-w-2xl mx-auto text-center">
              <div className="bg-white rounded-xl shadow-lg p-8">
                <div className="mb-6">
                  <div className="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                    <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">League Connected!</h2>
                  <p className="text-gray-600">
                    Your league has been successfully connected. Next, let's verify your team and set up your preferences.
                  </p>
                </div>
                
                <div className="space-y-4">
                  <Link 
                    href="/settings/onboarding"
                    className="w-full bg-blue-600 text-white py-4 px-6 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 text-lg font-medium inline-block"
                  >
                    Continue Setup
                  </Link>
                  
                  <Link 
                    href="/demo"
                    className="w-full bg-gray-100 text-gray-700 py-4 px-6 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition duration-200 text-lg font-medium inline-block"
                  >
                    See Demo First
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
