'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ProtectedRoute from '@/components/ProtectedRoute'

// League Connection Component
function LeagueConnection({ onComplete }: { onComplete: (data: any) => void }) {
  const [activeTab, setActiveTab] = useState<'yahoo' | 'sleeper' | 'espn'>('yahoo')
  const [sleeperData, setSleeperData] = useState({
    league_id: '',
    username: ''
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const handleYahooConnect = () => {
    // Simulate Yahoo OAuth redirect
    setLoading(true)
    setTimeout(() => {
      onComplete({ platform: 'yahoo', leagueId: 'yahoo-league-123' })
    }, 1500)
  }

  const handleSleeperConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!sleeperData.league_id) {
      setMessage('League ID is required')
      return
    }

    setLoading(true)
    setMessage('')

    // Simulate API call
    setTimeout(() => {
      onComplete({ 
        platform: 'sleeper', 
        leagueId: sleeperData.league_id,
        username: sleeperData.username 
      })
    }, 1500)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Connect Your League</h2>
        <p className="text-gray-600">Choose your fantasy platform to get started</p>
      </div>

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
              <p className="text-gray-600">Secure OAuth connection</p>
            </div>
          </div>

          <button
            onClick={handleYahooConnect}
            disabled={loading}
            className="w-full bg-purple-600 text-white py-4 px-6 rounded-lg hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition duration-200 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Connecting...' : 'Connect with Yahoo'}
          </button>
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
              <p className="text-gray-600">League ID required</p>
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
              {loading ? 'Connecting...' : 'Connect Sleeper League'}
            </button>
          </form>
        </div>
      )}

      {/* ESPN Content */}
      {activeTab === 'espn' && (
        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="text-center py-8">
            <p className="text-gray-600 mb-6">
              ESPN integration is coming soon!
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
        <div className="mt-6 p-4 rounded-lg bg-red-50 text-red-700 border border-red-200">
          {message}
        </div>
      )}
    </div>
  )
}

// Preferences Component
function PreferencesSelection({ onComplete }: { onComplete: (data: any) => void }) {
  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    weeklyRecap: true,
    recapDay: 'tuesday',
    recapTime: '09:00',
    powerRankings: true,
    waiverReport: true,
    injuryAlerts: false,
    tradeAlerts: true,
    groupmeIntegration: false,
    groupmeGroupId: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onComplete(preferences)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Set Your Preferences</h2>
        <p className="text-gray-600">Customize how you want to receive updates</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 space-y-6">
        {/* Email Notifications */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Notification Settings</h3>
          
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Email Notifications</span>
              <input
                type="checkbox"
                checked={preferences.emailNotifications}
                onChange={(e) => setPreferences(prev => ({ ...prev, emailNotifications: e.target.checked }))}
                className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
              />
            </label>

            <div className={`pl-6 space-y-4 ${!preferences.emailNotifications ? 'opacity-50' : ''}`}>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-gray-700">Weekly Recap</span>
                <input
                  type="checkbox"
                  checked={preferences.weeklyRecap}
                  onChange={(e) => setPreferences(prev => ({ ...prev, weeklyRecap: e.target.checked }))}
                  disabled={!preferences.emailNotifications}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>

              {preferences.weeklyRecap && preferences.emailNotifications && (
                <div className="grid grid-cols-2 gap-4 pl-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Recap Day
                    </label>
                    <select
                      value={preferences.recapDay}
                      onChange={(e) => setPreferences(prev => ({ ...prev, recapDay: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="monday">Monday</option>
                      <option value="tuesday">Tuesday</option>
                      <option value="wednesday">Wednesday</option>
                      <option value="thursday">Thursday</option>
                      <option value="friday">Friday</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Time
                    </label>
                    <input
                      type="time"
                      value={preferences.recapTime}
                      onChange={(e) => setPreferences(prev => ({ ...prev, recapTime: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-gray-700">Power Rankings</span>
                <input
                  type="checkbox"
                  checked={preferences.powerRankings}
                  onChange={(e) => setPreferences(prev => ({ ...prev, powerRankings: e.target.checked }))}
                  disabled={!preferences.emailNotifications}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-gray-700">Waiver Report</span>
                <input
                  type="checkbox"
                  checked={preferences.waiverReport}
                  onChange={(e) => setPreferences(prev => ({ ...prev, waiverReport: e.target.checked }))}
                  disabled={!preferences.emailNotifications}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-gray-700">Trade Alerts</span>
                <input
                  type="checkbox"
                  checked={preferences.tradeAlerts}
                  onChange={(e) => setPreferences(prev => ({ ...prev, tradeAlerts: e.target.checked }))}
                  disabled={!preferences.emailNotifications}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                />
              </label>
            </div>
          </div>
        </div>

        {/* GroupMe Integration */}
        <div className="border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">GroupMe Integration</h3>
          
          <label className="flex items-center justify-between cursor-pointer mb-4">
            <span className="text-gray-700">Enable GroupMe Bot</span>
            <input
              type="checkbox"
              checked={preferences.groupmeIntegration}
              onChange={(e) => setPreferences(prev => ({ ...prev, groupmeIntegration: e.target.checked }))}
              className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
            />
          </label>

          {preferences.groupmeIntegration && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                GroupMe Group ID
              </label>
              <input
                type="text"
                value={preferences.groupmeGroupId}
                onChange={(e) => setPreferences(prev => ({ ...prev, groupmeGroupId: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your GroupMe group ID"
              />
              <p className="text-xs text-gray-500 mt-1">
                We'll send you instructions on how to add our bot to your group
              </p>
            </div>
          )}
        </div>

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-4 px-6 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 text-lg font-medium"
        >
          Continue
        </button>
      </form>
    </div>
  )
}

// Team Verification Component
function TeamVerification({ leagueData, onComplete }: { leagueData: any; onComplete: (data: any) => void }) {
  const [selectedTeam, setSelectedTeam] = useState('')
  const [loading, setLoading] = useState(false)

  // Mock teams for demonstration
  const mockTeams = [
    { id: '1', name: 'The Touchdown Makers', owner: 'John Smith' },
    { id: '2', name: 'Gridiron Gladiators', owner: 'Sarah Johnson' },
    { id: '3', name: 'Fantasy Legends', owner: 'Mike Williams' },
    { id: '4', name: 'The Blitz Brigade', owner: 'Emily Davis' },
    { id: '5', name: 'Red Zone Runners', owner: 'Chris Brown' },
    { id: '6', name: 'Victory Formation', owner: 'Alex Taylor' }
  ]

  const handleVerify = () => {
    if (!selectedTeam) return
    
    setLoading(true)
    setTimeout(() => {
      onComplete({ teamId: selectedTeam })
    }, 1000)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">Verify Your Team</h2>
        <p className="text-gray-600">Select your team from the list below</p>
      </div>

      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="mb-6">
          <p className="text-sm text-gray-600 mb-4">
            League: <span className="font-semibold">{leagueData.platform} - {leagueData.leagueId}</span>
          </p>
        </div>

        <div className="space-y-3 mb-6">
          {mockTeams.map((team) => (
            <label
              key={team.id}
              className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedTeam === team.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input
                type="radio"
                name="team"
                value={team.id}
                checked={selectedTeam === team.id}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="w-4 h-4 text-blue-600 focus:ring-blue-500"
              />
              <div className="ml-3">
                <p className="font-semibold text-gray-900">{team.name}</p>
                <p className="text-sm text-gray-600">{team.owner}</p>
              </div>
            </label>
          ))}
        </div>

        <button
          onClick={handleVerify}
          disabled={!selectedTeam || loading}
          className={`w-full py-4 px-6 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 text-lg font-medium ${
            !selectedTeam || loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Verifying...' : 'Verify Team'}
        </button>

        <p className="text-xs text-gray-500 text-center mt-4">
          Don't see your team? Make sure you're connected to the right league.
        </p>
      </div>
    </div>
  )
}

// Completion Component
function SetupComplete({ leagueId }: { leagueId?: string }) {
  const router = useRouter()

  const handleGoToSettings = () => {
    if (leagueId) {
      router.push(`/settings/${leagueId}`)
    } else {
      // Fallback to dashboard if no leagueId available
      router.push('/dashboard')
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto text-center">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="mb-6">
          <div className="mx-auto h-20 w-20 bg-green-100 rounded-full flex items-center justify-center mb-4">
            <svg className="h-10 w-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">You're All Set!</h2>
          <p className="text-gray-600">
            Your league is connected and preferences are saved. You're ready to experience automated fantasy management.
          </p>
        </div>

        <div className="space-y-4">
          <button
            onClick={() => router.push('/demo')}
            className="w-full bg-blue-600 text-white py-4 px-6 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 text-lg font-medium"
          >
            See Demo Content
          </button>
          
          <button
            onClick={handleGoToSettings}
            className="w-full bg-gray-100 text-gray-700 py-4 px-6 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition duration-200 text-lg font-medium"
          >
            {leagueId ? 'Go to League Settings' : 'Go to Dashboard'}
          </button>
        </div>

        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Next Steps:</strong> Your first weekly recap will be sent on {new Date().toLocaleDateString('en-US', { weekday: 'long' })} at 9:00 AM. You can change this anytime in {leagueId ? 'league settings' : 'your dashboard'}.
          </p>
        </div>
      </div>
    </div>
  )
}

// Main Onboarding Component
function OnboardingContent() {
  const [currentStep, setCurrentStep] = useState(1)
  const [onboardingData, setOnboardingData] = useState({
    league: null,
    preferences: null,
    team: null
  })

  const steps = [
    { id: 1, name: 'Connect League', icon: '🔗' },
    { id: 2, name: 'Set Preferences', icon: '⚙️' },
    { id: 3, name: 'Verify Team', icon: '✓' },
    { id: 4, name: 'Complete', icon: '🎉' }
  ]

  const handleLeagueConnect = (data: any) => {
    setOnboardingData(prev => ({ ...prev, league: data }))
    setCurrentStep(2)
  }

  const handlePreferences = (data: any) => {
    setOnboardingData(prev => ({ ...prev, preferences: data }))
    setCurrentStep(3)
  }

  const handleTeamVerification = (data: any) => {
    setOnboardingData(prev => ({ ...prev, team: data }))
    setCurrentStep(4)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className="flex items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep >= step.id 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {currentStep > step.id ? '✓' : step.icon}
                  </div>
                  <span className={`ml-2 text-sm font-medium ${
                    currentStep >= step.id ? 'text-gray-900' : 'text-gray-500'
                  }`}>
                    {step.name}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div className="w-16 sm:w-24 mx-4">
                    <div className="h-1 bg-gray-200 rounded">
                      <div className={`h-1 rounded transition-all duration-300 ${
                        currentStep > step.id ? 'bg-blue-600 w-full' : 'bg-gray-200 w-0'
                      }`}></div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          {currentStep === 1 && <LeagueConnection onComplete={handleLeagueConnect} />}
          {currentStep === 2 && <PreferencesSelection onComplete={handlePreferences} />}
          {currentStep === 3 && onboardingData.league && (
            <TeamVerification 
              leagueData={onboardingData.league} 
              onComplete={handleTeamVerification} 
            />
          )}
          {currentStep === 4 && <SetupComplete leagueId={onboardingData.league?.leagueId} />}
        </div>
      </div>
    </div>
  )
}

export default function Onboarding() {
  return (
    <ProtectedRoute>
      <OnboardingContent />
    </ProtectedRoute>
  )
}
