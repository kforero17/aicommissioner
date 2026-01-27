'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const OAUTH_URL = process.env.NEXT_PUBLIC_OAUTH_URL || API_BASE_URL

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
  const [activeTab, setActiveTab] = useState<'yahoo' | 'sleeper' | 'espn'>('yahoo')
  const [sleeperData, setSleeperData] = useState({
    league_id: '',
    username: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [step, setStep] = useState(1)
  const [yahooStatus, setYahooStatus] = useState<any>(null)
  const [checkingStatus, setCheckingStatus] = useState(false)
  const [debugInfo, setDebugInfo] = useState<any>(null)
  const [showDebug, setShowDebug] = useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()

  // Check Yahoo connection status on load
  useEffect(() => {
    checkYahooStatus()
  }, [])

  // Handle Yahoo OAuth callback
  useEffect(() => {
    const yahooConnected = searchParams.get('yahoo_connected')

    if (yahooConnected === 'true') {
      // Token is now stored in HTTP-only secure cookie by backend
      setMessage('Yahoo account connected successfully!')
      setStep(2)
      // Recheck status after connection
      setTimeout(() => checkYahooStatus(), 1000)

      // Clean up URL
      router.replace('/connect', undefined)
    }
  }, [searchParams, router])

  const checkYahooStatus = async () => {
    setCheckingStatus(true)
    try {
      const response = await fetch(`${API_BASE_URL}/auth/yahoo/status`, {
        credentials: 'include'
      })

      if (response.ok) {
        const status = await response.json()
        setYahooStatus(status)
        if (status.connected && status.leagues.length > 0) {
          setStep(2)
        }
      }
    } catch (error) {
      console.error('Error checking Yahoo status:', error)
    } finally {
      setCheckingStatus(false)
    }
  }

  const triggerYahooImport = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/auth/yahoo/import-leagues`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        setMessage('Yahoo league import started...')
        setTimeout(() => checkYahooStatus(), 3000)
      } else {
        setMessage('Failed to import Yahoo leagues')
      }
    } catch (error) {
      setMessage('Error importing Yahoo leagues')
    } finally {
      setLoading(false)
    }
  }

  const runYahooDebug = async () => {
    setCheckingStatus(true)
    try {
      const response = await fetch(`${API_BASE_URL}/auth/yahoo/debug`, {
        credentials: 'include'
      })

      if (response.ok) {
        const debug = await response.json()
        setDebugInfo(debug)
        setShowDebug(true)
      } else {
        setMessage('Failed to run debug check')
      }
    } catch (error) {
      setMessage('Error running debug check')
    } finally {
      setCheckingStatus(false)
    }
  }

  const handleYahooConnect = () => {
    // Redirect to Yahoo OAuth start via tunnel URL to preserve session
    window.location.href = `${OAUTH_URL}/auth/yahoo/start`
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

                  {yahooStatus?.connected ? (
                    <div className="space-y-4">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center">
                          <svg className="w-5 h-5 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <span className="text-green-700 font-medium">Yahoo Connected</span>
                        </div>
                        <p className="text-green-600 text-sm mt-1">
                          {yahooStatus.leagues.length} league(s) imported
                        </p>
                      </div>
                      
                      {yahooStatus.leagues.length === 0 && (
                        <div className="space-y-3">
                          <button
                            onClick={triggerYahooImport}
                            disabled={loading}
                            className={`w-full py-3 px-4 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200 ${
                              loading 
                                ? 'bg-gray-400 cursor-not-allowed' 
                                : 'bg-purple-600 hover:bg-purple-700'
                            }`}
                          >
                            {loading ? 'Importing Leagues...' : 'Import Yahoo Leagues'}
                          </button>
                          
                          <button
                            onClick={runYahooDebug}
                            disabled={checkingStatus}
                            className="w-full py-2 px-4 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition duration-200 text-sm"
                          >
                            {checkingStatus ? 'Running Debug...' : 'Debug Connection'}
                          </button>
                        </div>
                      )}
                      
                      {yahooStatus.leagues.length > 0 && (
                        <button
                          onClick={() => setStep(2)}
                          className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-200"
                        >
                          Continue to Team Selection
                        </button>
                      )}
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={handleYahooConnect}
                        disabled={checkingStatus}
                        className={`w-full py-4 px-6 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200 text-lg font-medium ${
                          checkingStatus 
                            ? 'bg-gray-400 cursor-not-allowed' 
                            : 'bg-purple-600 hover:bg-purple-700'
                        }`}
                      >
                        {checkingStatus ? 'Checking Status...' : 'Connect with Yahoo'}
                      </button>
                      
                      <p className="text-xs text-gray-500 text-center mt-4">
                        We'll redirect you to Yahoo to securely authorize access to your leagues
                      </p>
                    </>
                  )}
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

              {/* Debug Information */}
              {showDebug && debugInfo && (
                <div className="mt-6 bg-gray-50 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-medium text-gray-900">Debug Information</h4>
                    <button 
                      onClick={() => setShowDebug(false)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ×
                    </button>
                  </div>
                  <div className="text-xs font-mono bg-white p-3 rounded border overflow-auto max-h-64">
                    <pre>{JSON.stringify(debugInfo, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="max-w-2xl mx-auto">
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Verify Your Team</h2>
                <p className="text-gray-600">
                  Select your team from the list below
                </p>
              </div>

              {yahooStatus?.leagues && yahooStatus.leagues.length > 0 ? (
                <div className="space-y-6">
                  {yahooStatus.leagues.map((league: any, leagueIndex: number) => (
                    <div key={league.id} className="bg-white rounded-xl shadow-lg p-6">
                      <h3 className="text-xl font-semibold text-gray-900 mb-4">
                        League: {league.name} - {league.provider_league_id}
                      </h3>
                      
                      <div className="text-sm text-gray-500 mb-4">
                        Season: {league.season} • Last sync: {league.last_sync_at ? new Date(league.last_sync_at).toLocaleDateString() : 'Never'}
                      </div>

                      {/* TODO: Show actual teams from the league */}
                      <div className="space-y-3">
                        <p className="text-gray-600">
                          Teams will be loaded after league sync is complete. 
                        </p>
                        <button
                          onClick={triggerYahooImport}
                          disabled={loading}
                          className={`w-full py-2 px-4 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 ${
                            loading 
                              ? 'bg-gray-400 cursor-not-allowed' 
                              : 'bg-blue-600 hover:bg-blue-700'
                          }`}
                        >
                          {loading ? 'Syncing League Data...' : 'Sync League Data'}
                        </button>
                      </div>
                    </div>
                  ))}

                  <div className="space-y-4 pt-4">
                    <Link 
                      href="/dashboard"
                      className="w-full bg-green-600 text-white py-4 px-6 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-200 text-lg font-medium inline-block text-center"
                    >
                      Continue to Dashboard
                    </Link>
                    
                    <Link 
                      href="/demo"
                      className="w-full bg-gray-100 text-gray-700 py-4 px-6 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition duration-200 text-lg font-medium inline-block text-center"
                    >
                      See Demo First
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-xl shadow-lg p-8 text-center">
                  <div className="mb-6">
                    <div className="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                      <svg className="h-8 w-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">No Leagues Found</h3>
                    <p className="text-gray-600 mb-6">
                      We couldn't find any leagues in your Yahoo account. Make sure you're in at least one active fantasy league.
                    </p>
                    
                    <div className="space-y-3">
                      <button
                        onClick={triggerYahooImport}
                        disabled={loading}
                        className={`w-full py-3 px-4 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200 ${
                          loading 
                            ? 'bg-gray-400 cursor-not-allowed' 
                            : 'bg-purple-600 hover:bg-purple-700'
                        }`}
                      >
                        {loading ? 'Checking Again...' : 'Refresh League List'}
                      </button>
                      
                      <button
                        onClick={() => setStep(1)}
                        className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition duration-200"
                      >
                        Back to Connection
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
