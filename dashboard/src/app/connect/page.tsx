'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const OAUTH_URL = process.env.NEXT_PUBLIC_OAUTH_URL || API_BASE_URL

interface YahooLeague {
  id: string
  name: string
  provider_league_id: string
  season: string
  last_sync_at: string | null
}

interface YahooStatus {
  connected: boolean
  leagues: YahooLeague[]
}

function ConnectPageContent() {
  const [activeTab, setActiveTab] = useState<'yahoo' | 'sleeper' | 'espn'>('yahoo')
  const [sleeperData, setSleeperData] = useState({
    league_id: '',
    username: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [step, setStep] = useState(1)
  const [yahooStatus, setYahooStatus] = useState<YahooStatus | null>(null)
  const [checkingStatus, setCheckingStatus] = useState(false)
  const [debugInfo, setDebugInfo] = useState<Record<string, unknown> | null>(null)
  const [showDebug, setShowDebug] = useState(false)
  const [importTaskId, setImportTaskId] = useState<string | null>(null)
  const [importProgress, setImportProgress] = useState<string>('')
  const [showAutoSyncInfo, setShowAutoSyncInfo] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()

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

  const pollForLeagues = useCallback(async () => {
    const maxAttempts = 60 // 2 minutes
    let progressStage = 0
    const progressMessages = [
      'Connecting to Yahoo Fantasy...',
      'Fetching your leagues...',
      'Importing league data...',
      'Loading rosters and matchups...',
      'Almost done...'
    ]

    for (let i = 0; i < maxAttempts; i++) {
      // Update progress message every few polls
      if (i % 4 === 0 && progressStage < progressMessages.length - 1) {
        progressStage++
        setImportProgress(progressMessages[progressStage])
      }

      await new Promise(resolve => setTimeout(resolve, 2000))

      try {
        const response = await fetch(`${API_BASE_URL}/auth/yahoo/status`, {
          credentials: 'include'
        })

        if (response.ok) {
          const status = await response.json()
          setYahooStatus(status)

          if (status.connected && status.leagues && status.leagues.length > 0) {
            // Leagues found! Import complete
            setImportProgress('Import complete!')
            setIsImporting(false)
            setShowAutoSyncInfo(true)
            setMessage(`Successfully imported ${status.leagues.length} league(s)!`)

            // Auto-redirect to dashboard after short delay
            setTimeout(() => {
              router.push('/dashboard')
            }, 2000)
            return
          }
        }
      } catch (error) {
        console.error('Error checking status:', error)
      }
    }

    // Timeout - import may have failed
    setIsImporting(false)
    setImportProgress('')
    setMessage('Import is taking longer than expected. Please check the dashboard or try again.')
  }, [router])

  // Check Yahoo connection status on load
  useEffect(() => {
    checkYahooStatus()
  }, [])

  // Handle Yahoo OAuth callback
  useEffect(() => {
    const yahooConnected = searchParams.get('yahoo_connected')

    if (yahooConnected === 'true') {
      setMessage('Yahoo account connected! Importing your leagues...')
      setIsImporting(true)
      setImportProgress('Connecting to Yahoo Fantasy...')
      pollForLeagues()
      router.replace('/connect', undefined)
    }
  }, [searchParams, router, pollForLeagues])

  const pollImportStatus = async (taskId: string) => {
    const maxAttempts = 60 // 2 minutes at 2-second intervals

    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000))

      try {
        const response = await fetch(`${API_BASE_URL}/admin/tasks/${taskId}`, {
          credentials: 'include'
        })

        if (!response.ok) continue

        const status = await response.json()

        if (status.status === 'SUCCESS') {
          setImportProgress('Import complete!')
          setShowAutoSyncInfo(true)
          await checkYahooStatus() // Refresh league list
          setImportTaskId(null)
          setLoading(false)
          // Auto-advance to step 2 after successful import
          setTimeout(() => setStep(2), 1500)
          return true
        }

        if (status.status === 'FAILURE') {
          setMessage(status.error || 'Import failed. Please try again.')
          setImportTaskId(null)
          setLoading(false)
          return false
        }

        if (status.status === 'STARTED') {
          setImportProgress('Importing league data...')
        } else if (status.status === 'PENDING') {
          setImportProgress('Queued for import...')
        }
      } catch (error) {
        console.error('Error polling task status:', error)
      }
    }

    setMessage('Import timed out. Please try again.')
    setImportTaskId(null)
    setLoading(false)
    return false
  }

  const triggerYahooImport = async () => {
    setLoading(true)
    setMessage('')
    setShowAutoSyncInfo(false)
    setImportProgress('Connecting to Yahoo...')

    try {
      const response = await fetch(`${API_BASE_URL}/auth/yahoo/import-leagues`, {
        method: 'POST',
        credentials: 'include'
      })

      if (response.ok) {
        const data = await response.json()
        if (data.task_id) {
          setImportTaskId(data.task_id)
          setImportProgress('Starting import...')
          // Start polling for task status
          pollImportStatus(data.task_id)
        } else {
          // Fallback for old API response
          setMessage('Yahoo league import started...')
          setTimeout(() => checkYahooStatus(), 3000)
          setLoading(false)
        }
      } else {
        setMessage('Failed to import Yahoo leagues')
        setLoading(false)
      }
    } catch (error) {
      setMessage('Error importing Yahoo leagues')
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

          {step === 1 && !isImporting && (
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
                      <p className="text-gray-600">Most popular option · OAuth secure connection</p>
                    </div>
                  </div>
                  
                  <div className="mb-6">
                    <h4 className="font-medium text-gray-900 mb-3">What you&apos;ll get:</h4>
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

                  {/* Import Progress Indicator */}
                  {importTaskId && importProgress && (
                    <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center">
                        <svg className="animate-spin h-5 w-5 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <div className="flex-1">
                          <p className="text-blue-700 font-medium">{importProgress}</p>
                          <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
                            <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{
                              width: importProgress.includes('Connecting') ? '25%' :
                                     importProgress.includes('Starting') ? '40%' :
                                     importProgress.includes('Importing') ? '70%' :
                                     importProgress.includes('complete') ? '100%' : '10%'
                            }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Auto-sync Info Box */}
                  {showAutoSyncInfo && (
                    <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-start">
                        <svg className="w-5 h-5 text-green-500 mr-3 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="flex-1">
                          <p className="text-green-700 font-medium mb-2">Your leagues will automatically sync:</p>
                          <ul className="text-green-600 text-sm space-y-1 ml-1">
                            <li>• Daily at 6 AM and 6 PM</li>
                            <li>• Every 2 hours on Sundays and Mondays (game days)</li>
                          </ul>
                          <p className="text-green-600 text-sm mt-2">
                            You can also manually sync from your dashboard anytime.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

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
                        We&apos;ll redirect you to Yahoo to securely authorize access to your leagues
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
                      ESPN integration is currently in development. Join our waitlist to be notified when it&apos;s ready!
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

          {/* Importing State */}
          {isImporting && (
            <div className="max-w-md mx-auto text-center">
              <div className="bg-white rounded-xl shadow-lg p-8">
                {/* Animated spinner */}
                <div className="mx-auto w-16 h-16 mb-6">
                  <svg className="animate-spin w-full h-full text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>

                <h2 className="text-xl font-semibold text-gray-900 mb-2">Importing Your Leagues</h2>
                <p className="text-gray-600 mb-4">{importProgress}</p>

                {/* Progress bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: importProgress.includes('complete') ? '100%' : '60%' }}
                  />
                </div>

                <p className="text-sm text-gray-500">
                  This usually takes 15-30 seconds. You&apos;ll be redirected to the dashboard automatically.
                </p>
              </div>
            </div>
          )}

          {/* Success State Before Redirect */}
          {!isImporting && importProgress === 'Import complete!' && (
            <div className="max-w-md mx-auto text-center">
              <div className="bg-white rounded-xl shadow-lg p-8">
                <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Leagues Imported!</h2>
                <p className="text-gray-600">Redirecting to dashboard...</p>
              </div>
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

              {/* Auto-sync Info Box at top of Step 2 */}
              {showAutoSyncInfo && (
                <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <svg className="w-5 h-5 text-blue-500 mr-3 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="flex-1">
                      <p className="text-blue-700 font-medium mb-2">Your leagues stay fresh automatically</p>
                      <ul className="text-blue-600 text-sm space-y-1 ml-1">
                        <li>• Daily syncs at 6 AM and 6 PM</li>
                        <li>• Every 2 hours on game days (Sundays and Mondays)</li>
                        <li>• Manual refresh available from your dashboard</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {yahooStatus?.leagues && yahooStatus.leagues.length > 0 ? (
                <div className="space-y-6">
                  {yahooStatus.leagues.map((league: YahooLeague) => {
                    const getRelativeTime = (dateString: string | null) => {
                      if (!dateString) return 'Never'
                      const date = new Date(dateString)
                      const now = new Date()
                      const diffMs = now.getTime() - date.getTime()
                      const diffMins = Math.floor(diffMs / 60000)
                      const diffHours = Math.floor(diffMins / 60)
                      const diffDays = Math.floor(diffHours / 24)

                      if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
                      if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
                      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
                    }

                    const getNextSyncTime = () => {
                      const now = new Date()
                      const currentHour = now.getHours()
                      const dayOfWeek = now.getDay() // 0 = Sunday, 1 = Monday

                      // Game days (Sunday or Monday)
                      if (dayOfWeek === 0 || dayOfWeek === 1) {
                        const nextSync = new Date(now)
                        nextSync.setHours(Math.ceil(currentHour / 2) * 2, 0, 0, 0)
                        if (nextSync <= now) {
                          nextSync.setHours(nextSync.getHours() + 2)
                        }
                        return `~${nextSync.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} today`
                      }

                      // Regular days - 6 AM or 6 PM
                      if (currentHour < 6) return '~6 AM today'
                      if (currentHour < 18) return '~6 PM today'
                      return '~6 AM tomorrow'
                    }

                    return (
                      <div key={league.id} className="bg-white rounded-xl shadow-lg p-6">
                        <h3 className="text-xl font-semibold text-gray-900 mb-4">
                          League: {league.name} - {league.provider_league_id}
                        </h3>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4 text-sm">
                          <div>
                            <span className="text-gray-500">Season:</span>
                            <span className="ml-2 text-gray-900 font-medium">{league.season}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Last sync:</span>
                            <span className="ml-2 text-gray-900 font-medium">{getRelativeTime(league.last_sync_at)}</span>
                          </div>
                          <div>
                            <span className="text-gray-500">Next auto-sync:</span>
                            <span className="ml-2 text-gray-900 font-medium">{getNextSyncTime()}</span>
                          </div>
                        </div>

                        {/* TODO: Show actual teams from the league */}
                        <div className="space-y-3">
                          <p className="text-gray-600">
                            Teams will be loaded after league sync is complete.
                          </p>
                        </div>
                      </div>
                    )
                  })}

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
              ) : !isImporting ? (
                <div className="bg-white rounded-xl shadow-lg p-8 text-center">
                  <div className="mb-6">
                    <div className="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                      <svg className="h-8 w-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">No Leagues Found</h3>
                    <p className="text-gray-600 mb-6">
                      We couldn&apos;t find any leagues in your Yahoo account. Make sure you&apos;re in at least one active fantasy league.
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
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ConnectPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      <ConnectPageContent />
    </Suspense>
  )
}
