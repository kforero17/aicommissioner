'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { LeagueStatusStrip } from '@/components/LeagueStatusStrip'

interface LeagueData {
  id: number
  name: string
  provider: string
  season: number
  week: number | null
  num_teams: number
}

interface StandingsEntry {
  roster_id: number
  provider_roster_id: string
  team_name: string
  owner_name: string | null
  wins: number
  losses: number
  ties: number
  points_for: number
  points_against: number
  power_rank: number | null
  power_rank_change: number | null
  standing: number
}

interface MatchupResponse {
  matchup_id: number
  week: number
  team1_name: string
  team1_roster_id: string
  team1_points: number | null
  team1_projected: number | null
  team2_name: string | null
  team2_roster_id: string | null
  team2_points: number | null
  team2_projected: number | null
  is_complete: boolean
  winner_name: string | null
  margin: number | null
  is_game_of_week: boolean
}

interface AccessCheck {
  has_access: boolean
  role?: 'commissioner' | 'member'
  is_owner: boolean
  preferences?: {
    mute_waivers?: boolean
    mute_power_rankings?: boolean
    mute_weekly_recaps?: boolean
    email_digest?: string
  }
}

interface RecapData {
  id: number
  recap_type: 'power_rankings' | 'waiver_recap' | 'weekly_recap'
  week: number
  season: number
  title: string
  content: string
  status: string
  rendering_mode: string | null
  ai_persona: string | null
  published_at: string | null
  created_at: string
}

interface RecapListResponse {
  recaps: RecapData[]
  total: number
  has_more: boolean
}

type TabType = 'home' | 'feed' | 'history'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function LeagueHubPage() {
  const params = useParams()
  const router = useRouter()
  const leagueId = params.leagueId as string

  const [league, setLeague] = useState<LeagueData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [access, setAccess] = useState<AccessCheck | null>(null)
  const [checkingAccess, setCheckingAccess] = useState(true)

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('home')

  // Data states
  const [standings, setStandings] = useState<StandingsEntry[]>([])
  const [matchups, setMatchups] = useState<MatchupResponse[]>([])
  const [selectedWeek, setSelectedWeek] = useState<number>(1)

  // Recap states
  const [recaps, setRecaps] = useState<RecapData[]>([])
  const [recapsLoading, setRecapsLoading] = useState(false)
  const [feedFilter, setFeedFilter] = useState<string | null>(null)

  // Loading states
  const [standingsLoading, setStandingsLoading] = useState(false)
  const [matchupsLoading, setMatchupsLoading] = useState(false)
  const [showPreferences, setShowPreferences] = useState(false)
  const [savingPreferences, setSavingPreferences] = useState(false)
  const [preferences, setPreferences] = useState({
    mute_waivers: false,
    mute_power_rankings: false,
    mute_weekly_recaps: false
  })

  useEffect(() => {
    fetchLeague()
    checkAccess()
  }, [leagueId])

  const checkAccess = async () => {
    try {
      setCheckingAccess(true)
      const response = await fetch(`${API_BASE}/members/leagues/${leagueId}/access`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: AccessCheck = await response.json()
        if (!data.has_access) {
          router.push('/dashboard')
          return
        }
        setAccess(data)
        if (data.preferences) {
          setPreferences({
            mute_waivers: data.preferences.mute_waivers || false,
            mute_power_rankings: data.preferences.mute_power_rankings || false,
            mute_weekly_recaps: data.preferences.mute_weekly_recaps || false
          })
        }
      } else if (response.status === 401) {
        router.push('/auth/login')
        return
      }
    } catch (err) {
      console.error('Access check failed:', err)
    } finally {
      setCheckingAccess(false)
    }
  }

  const updatePreferences = async (newPreferences: typeof preferences) => {
    try {
      setSavingPreferences(true)
      const response = await fetch(`${API_BASE}/members/leagues/${leagueId}/preferences`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newPreferences)
      })

      if (response.ok) {
        setPreferences(newPreferences)
      }
    } catch (err) {
      console.error('Failed to update preferences:', err)
    } finally {
      setSavingPreferences(false)
    }
  }

  useEffect(() => {
    if (league && activeTab === 'home') {
      fetchStandings()
      fetchMatchups(league.week || 1)
    }
  }, [league, activeTab])

  useEffect(() => {
    if (league && activeTab === 'history') {
      fetchMatchups(selectedWeek)
    }
  }, [selectedWeek, activeTab, league])

  useEffect(() => {
    if (league && activeTab === 'feed') {
      fetchRecaps()
    }
  }, [activeTab, league, feedFilter])

  const fetchRecaps = async () => {
    try {
      setRecapsLoading(true)
      let url = `${API_BASE}/admin/leagues/${leagueId}/recaps?status_filter=published&limit=50`
      if (feedFilter) {
        url += `&recap_type=${feedFilter}`
      }

      const response = await fetch(url, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: RecapListResponse = await response.json()
        setRecaps(data.recaps)
      }
    } catch (err) {
      console.error('Failed to fetch recaps:', err)
    } finally {
      setRecapsLoading(false)
    }
  }

  const fetchLeague = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`${API_BASE}/admin/leagues`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        if (response.status === 401) {
          router.push('/auth/login')
          return
        }
        throw new Error('Failed to fetch league data')
      }

      const leagues: LeagueData[] = await response.json()
      const foundLeague = leagues.find(l => l.id === parseInt(leagueId))

      if (!foundLeague) {
        setError('League not found')
      } else {
        setLeague(foundLeague)
        setSelectedWeek(foundLeague.week || 1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load league')
    } finally {
      setLoading(false)
    }
  }

  const fetchStandings = async () => {
    try {
      setStandingsLoading(true)
      const response = await fetch(`${API_BASE}/admin/leagues/${leagueId}/standings`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: StandingsEntry[] = await response.json()
        setStandings(data)
      }
    } catch (err) {
      console.error('Failed to fetch standings:', err)
    } finally {
      setStandingsLoading(false)
    }
  }

  const fetchMatchups = async (week: number) => {
    try {
      setMatchupsLoading(true)
      const response = await fetch(`${API_BASE}/admin/leagues/${leagueId}/matchups?week=${week}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: MatchupResponse[] = await response.json()
        setMatchups(data)
      }
    } catch (err) {
      console.error('Failed to fetch matchups:', err)
    } finally {
      setMatchupsLoading(false)
    }
  }

  if (loading || checkingAccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading league...</p>
        </div>
      </div>
    )
  }

  if (error || !league) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <svg className="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">{error || 'League not found'}</h2>
          <p className="text-gray-600 mb-6">Unable to load league data</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const leaderTeam = standings.length > 0 ? standings[0] : null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4 transition-colors"
          >
            <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Dashboard
          </Link>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-1">
                {league.name}
              </h1>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  league.provider === 'sleeper'
                    ? 'bg-blue-100 text-blue-800'
                    : league.provider === 'yahoo'
                    ? 'bg-purple-100 text-purple-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {league.provider.charAt(0).toUpperCase() + league.provider.slice(1)}
                </span>
                <span>Season {league.season}</span>
                {league.week && <span>Week {league.week}</span>}
                <span>{league.num_teams} Teams</span>
              </div>
            </div>

            {access?.is_owner && (
              <Link
                href={`/settings/${leagueId}`}
                className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </Link>
            )}
          </div>
        </div>

        {/* Status Strip */}
        <div className="mb-8">
          <LeagueStatusStrip leagueId={leagueId} />
        </div>

        {/* Member Preferences (for non-owners) */}
        {access && !access.is_owner && (
          <div className="mb-6 bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Your Preferences</h3>
                <p className="text-sm text-gray-600">Control what content you receive</p>
              </div>
              <button
                onClick={() => setShowPreferences(!showPreferences)}
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                {showPreferences ? 'Hide' : 'Show'}
              </button>
            </div>

            {showPreferences && (
              <div className="space-y-3 pt-4 border-t border-gray-200">
                <label className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                  <span className="text-sm font-medium text-gray-700">Mute Power Rankings</span>
                  <input
                    type="checkbox"
                    checked={preferences.mute_power_rankings}
                    onChange={(e) => {
                      const newPrefs = { ...preferences, mute_power_rankings: e.target.checked }
                      updatePreferences(newPrefs)
                    }}
                    disabled={savingPreferences}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                  />
                </label>

                <label className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                  <span className="text-sm font-medium text-gray-700">Mute Waiver Recaps</span>
                  <input
                    type="checkbox"
                    checked={preferences.mute_waivers}
                    onChange={(e) => {
                      const newPrefs = { ...preferences, mute_waivers: e.target.checked }
                      updatePreferences(newPrefs)
                    }}
                    disabled={savingPreferences}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                  />
                </label>

                <label className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                  <span className="text-sm font-medium text-gray-700">Mute Weekly Recaps</span>
                  <input
                    type="checkbox"
                    checked={preferences.mute_weekly_recaps}
                    onChange={(e) => {
                      const newPrefs = { ...preferences, mute_weekly_recaps: e.target.checked }
                      updatePreferences(newPrefs)
                    }}
                    disabled={savingPreferences}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                  />
                </label>

                {savingPreferences && (
                  <div className="flex items-center justify-center py-2">
                    <svg className="animate-spin h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="ml-2 text-sm text-gray-600">Saving...</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              <TabButton
                active={activeTab === 'home'}
                onClick={() => setActiveTab('home')}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                }
              >
                Home
              </TabButton>
              <TabButton
                active={activeTab === 'feed'}
                onClick={() => setActiveTab('feed')}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                  </svg>
                }
              >
                Feed
              </TabButton>
              <TabButton
                active={activeTab === 'history'}
                onClick={() => setActiveTab('history')}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
              >
                History
              </TabButton>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-6">
          {activeTab === 'home' && (
            <HomeTab
              leaderTeam={leaderTeam}
              matchups={matchups}
              standings={standings}
              standingsLoading={standingsLoading}
              matchupsLoading={matchupsLoading}
              currentWeek={league.week || 1}
            />
          )}

          {activeTab === 'feed' && (
            <FeedTab
              recaps={recaps}
              recapsLoading={recapsLoading}
              feedFilter={feedFilter}
              setFeedFilter={setFeedFilter}
              preferences={preferences}
              leagueId={leagueId}
            />
          )}

          {activeTab === 'history' && (
            <HistoryTab
              matchups={matchups}
              matchupsLoading={matchupsLoading}
              selectedWeek={selectedWeek}
              setSelectedWeek={setSelectedWeek}
              maxWeek={league.week || 18}
            />
          )}
        </div>
      </div>
    </div>
  )
}

// Tab Button Component
function TabButton({ active, onClick, icon, children }: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`
        group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors
        ${active
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }
      `}
    >
      <span className={active ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}>
        {icon}
      </span>
      <span className="ml-2">{children}</span>
    </button>
  )
}

// Home Tab Component
function HomeTab({ leaderTeam, matchups, standings, standingsLoading, matchupsLoading, currentWeek }: {
  leaderTeam: StandingsEntry | null
  matchups: MatchupResponse[]
  standings: StandingsEntry[]
  standingsLoading: boolean
  matchupsLoading: boolean
  currentWeek: number
}) {
  return (
    <div className="space-y-6">
      {/* League Leader Card */}
      {leaderTeam && (
        <div className="bg-gradient-to-br from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-yellow-500 text-white rounded-full w-12 h-12 flex items-center justify-center text-2xl font-bold">
                1
              </div>
              <div>
                <p className="text-sm font-medium text-yellow-800">League Leader</p>
                <h3 className="text-2xl font-bold text-gray-900">{leaderTeam.team_name}</h3>
                {leaderTeam.owner_name && (
                  <p className="text-sm text-gray-600">{leaderTeam.owner_name}</p>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-gray-900">
                {leaderTeam.wins}-{leaderTeam.losses}
                {leaderTeam.ties > 0 && `-${leaderTeam.ties}`}
              </div>
              <p className="text-sm text-gray-600 mt-1">
                {leaderTeam.points_for.toFixed(1)} PF
              </p>
            </div>
          </div>
        </div>
      )}

      {/* This Week's Matchups */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Week {currentWeek} Matchups</h2>
          <p className="text-sm text-gray-600 mt-1">Current matchups and scores</p>
        </div>

        <div className="p-6">
          {matchupsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-24 bg-gray-200 rounded-lg"></div>
                </div>
              ))}
            </div>
          ) : matchups.length > 0 ? (
            <div className="space-y-4">
              {matchups.map((matchup) => (
                <MatchupCard key={matchup.matchup_id} matchup={matchup} />
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8">No matchups available for this week</p>
          )}
        </div>
      </div>

      {/* Standings Snapshot */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Current Standings</h2>
          <p className="text-sm text-gray-600 mt-1">Top 5 teams with power rankings</p>
        </div>

        <div className="overflow-hidden">
          {standingsLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="animate-pulse flex items-center space-x-4">
                  <div className="h-4 w-8 bg-gray-200 rounded"></div>
                  <div className="h-4 flex-1 bg-gray-200 rounded"></div>
                  <div className="h-4 w-20 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          ) : standings.length > 0 ? (
            <StandingsTable standings={standings.slice(0, 5)} />
          ) : (
            <p className="text-center text-gray-500 py-8">No standings data available</p>
          )}
        </div>

        {standings.length > 5 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-center">
            <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
              View Full Standings
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Feed Tab Component
function FeedTab({ recaps, recapsLoading, feedFilter, setFeedFilter, preferences, leagueId }: {
  recaps: RecapData[]
  recapsLoading: boolean
  feedFilter: string | null
  setFeedFilter: (filter: string | null) => void
  preferences: { mute_waivers: boolean; mute_power_rankings: boolean; mute_weekly_recaps: boolean }
  leagueId: string
}) {
  const [expandedRecap, setExpandedRecap] = useState<number | null>(null)

  const filteredRecaps = recaps.filter(recap => {
    if (recap.recap_type === 'power_rankings' && preferences.mute_power_rankings) return false
    if (recap.recap_type === 'waiver_recap' && preferences.mute_waivers) return false
    if (recap.recap_type === 'weekly_recap' && preferences.mute_weekly_recaps) return false
    return true
  })

  const getRecapIcon = (type: string) => {
    switch (type) {
      case 'power_rankings':
        return (
          <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        )
      case 'waiver_recap':
        return (
          <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
        )
      case 'weekly_recap':
        return (
          <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
            <svg className="h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        )
      default:
        return null
    }
  }

  const getRecapTypeBadge = (type: string) => {
    switch (type) {
      case 'power_rankings':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">Power Rankings</span>
      case 'waiver_recap':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">Waiver Recap</span>
      case 'weekly_recap':
        return <span className="px-2 py-1 text-xs font-medium rounded-full bg-purple-100 text-purple-800">Weekly Recap</span>
      default:
        return null
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Latest Activity</h2>
              <p className="text-sm text-gray-600 mt-1">AI-generated content for your league</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Filter:</span>
              <select
                value={feedFilter || ''}
                onChange={(e) => setFeedFilter(e.target.value || null)}
                className="block pl-3 pr-10 py-2 text-sm border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md"
              >
                <option value="">All Types</option>
                <option value="power_rankings">Power Rankings</option>
                <option value="waiver_recap">Waiver Recaps</option>
                <option value="weekly_recap">Weekly Recaps</option>
              </select>
            </div>
          </div>
        </div>

        <div className="p-6">
          {recapsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse border border-gray-200 rounded-lg p-6">
                  <div className="flex items-start space-x-4">
                    <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
                    <div className="flex-1">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredRecaps.length > 0 ? (
            <div className="space-y-4">
              {filteredRecaps.map((recap) => (
                <div
                  key={recap.id}
                  className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white"
                >
                  <div className="flex items-start space-x-4">
                    {getRecapIcon(recap.recap_type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold text-gray-900">{recap.title}</h3>
                          {getRecapTypeBadge(recap.recap_type)}
                        </div>
                        <span className="text-sm text-gray-500">
                          {formatDate(recap.published_at || recap.created_at)}
                        </span>
                      </div>

                      <div className="mt-3">
                        <div className={`prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap ${
                          expandedRecap === recap.id ? '' : 'line-clamp-6'
                        }`}>
                          {recap.content}
                        </div>

                        {recap.content.length > 400 && (
                          <button
                            onClick={() => setExpandedRecap(expandedRecap === recap.id ? null : recap.id)}
                            className="mt-2 text-sm font-medium text-blue-600 hover:text-blue-700"
                          >
                            {expandedRecap === recap.id ? 'Show less' : 'Show more'}
                          </button>
                        )}
                      </div>

                      {recap.ai_persona && (
                        <div className="mt-3 flex items-center gap-2">
                          <span className="text-xs text-gray-500">AI Style:</span>
                          <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700 capitalize">
                            {recap.ai_persona}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-blue-50 rounded-lg border border-blue-100">
              <svg className="mx-auto h-12 w-12 text-blue-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No content yet</h3>
              <p className="text-sm text-gray-600 max-w-md mx-auto mb-4">
                {recaps.length > 0
                  ? "All recaps are hidden based on your mute preferences. Adjust your preferences to see content."
                  : "Enable recaps in Settings to start generating weekly content for your league."}
              </p>
              <Link
                href={`/settings/${leagueId}`}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Go to Settings
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// History Tab Component
function HistoryTab({ matchups, matchupsLoading, selectedWeek, setSelectedWeek, maxWeek }: {
  matchups: MatchupResponse[]
  matchupsLoading: boolean
  selectedWeek: number
  setSelectedWeek: (week: number) => void
  maxWeek: number
}) {
  const weeks = Array.from({ length: 18 }, (_, i) => i + 1)

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Historical Archive</h2>
              <p className="text-sm text-gray-600 mt-1">View past matchups and content</p>
            </div>
            <div className="flex items-center space-x-2">
              <label htmlFor="week-select" className="text-sm font-medium text-gray-700">
                Week:
              </label>
              <select
                id="week-select"
                value={selectedWeek}
                onChange={(e) => setSelectedWeek(parseInt(e.target.value))}
                className="block w-20 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              >
                {weeks.map((week) => (
                  <option key={week} value={week}>
                    {week}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="p-6">
          <h3 className="text-md font-semibold text-gray-900 mb-4">Week {selectedWeek} Matchups</h3>

          {matchupsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-24 bg-gray-200 rounded-lg"></div>
                </div>
              ))}
            </div>
          ) : matchups.length > 0 ? (
            <div className="space-y-4">
              {matchups.map((matchup) => (
                <MatchupCard key={matchup.matchup_id} matchup={matchup} />
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8">No matchups available for this week</p>
          )}

          <div className="mt-8 text-center py-6 bg-gray-50 rounded-lg border border-gray-200">
            <svg className="mx-auto h-10 w-10 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <p className="text-sm font-medium text-gray-900 mb-1">Historical Content Archive</p>
            <p className="text-sm text-gray-600 max-w-md mx-auto">
              Past recaps and content will be archived here for easy access
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Matchup Card Component
function MatchupCard({ matchup }: { matchup: MatchupResponse }) {
  const team1Score = matchup.team1_points ?? matchup.team1_projected ?? 0
  const team2Score = matchup.team2_points ?? matchup.team2_projected ?? 0
  const isProjected = !matchup.is_complete

  return (
    <div className={`relative border rounded-lg p-4 hover:shadow-md transition-shadow ${
      matchup.is_game_of_week ? 'border-yellow-400 bg-yellow-50' : 'border-gray-200 bg-white'
    }`}>
      {matchup.is_game_of_week && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-400 text-yellow-900">
            <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
            Game of the Week
          </span>
        </div>
      )}

      <div className="flex items-center justify-between">
        {/* Team 1 */}
        <div className="flex-1">
          <p className={`text-sm font-medium ${
            matchup.winner_name === matchup.team1_name ? 'text-green-700' : 'text-gray-700'
          }`}>
            {matchup.team1_name}
          </p>
          <p className={`text-2xl font-bold mt-1 ${
            matchup.winner_name === matchup.team1_name ? 'text-green-600' : 'text-gray-900'
          }`}>
            {team1Score.toFixed(1)}
            {isProjected && <span className="text-sm text-gray-500 ml-1">(proj)</span>}
          </p>
        </div>

        {/* VS */}
        <div className="px-4 text-center">
          <span className="text-xs font-semibold text-gray-500 uppercase">vs</span>
          {matchup.is_complete && matchup.margin !== null && (
            <p className="text-xs text-gray-600 mt-1">
              {matchup.margin.toFixed(1)}
            </p>
          )}
        </div>

        {/* Team 2 */}
        <div className="flex-1 text-right">
          <p className={`text-sm font-medium ${
            matchup.winner_name === matchup.team2_name ? 'text-green-700' : 'text-gray-700'
          }`}>
            {matchup.team2_name || 'BYE'}
          </p>
          {matchup.team2_name && (
            <p className={`text-2xl font-bold mt-1 ${
              matchup.winner_name === matchup.team2_name ? 'text-green-600' : 'text-gray-900'
            }`}>
              {team2Score.toFixed(1)}
              {isProjected && <span className="text-sm text-gray-500 ml-1">(proj)</span>}
            </p>
          )}
        </div>
      </div>

      {matchup.is_complete && matchup.winner_name && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <p className="text-xs text-center text-gray-600">
            <span className="font-semibold text-green-700">{matchup.winner_name}</span> wins
          </p>
        </div>
      )}
    </div>
  )
}

// Standings Table Component
function StandingsTable({ standings }: { standings: StandingsEntry[] }) {
  const getPowerRankChange = (change: number | null) => {
    if (change === null || change === 0) {
      return <span className="text-gray-400">—</span>
    }
    if (change > 0) {
      return (
        <span className="text-green-600 font-medium">
          ▲ {change}
        </span>
      )
    }
    return (
      <span className="text-red-600 font-medium">
        ▼ {Math.abs(change)}
      </span>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Team
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Record
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              PF
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Power Rank
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Change
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {standings.map((entry) => (
            <tr key={entry.roster_id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-semibold text-sm">
                  {entry.standing}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">{entry.team_name}</div>
                {entry.owner_name && (
                  <div className="text-xs text-gray-500">{entry.owner_name}</div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <span className="text-sm font-medium text-gray-900">
                  {entry.wins}-{entry.losses}
                  {entry.ties > 0 && `-${entry.ties}`}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-700">
                {entry.points_for.toFixed(1)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center">
                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-700 font-semibold text-sm">
                  {entry.power_rank ?? '—'}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                {getPowerRankChange(entry.power_rank_change)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
