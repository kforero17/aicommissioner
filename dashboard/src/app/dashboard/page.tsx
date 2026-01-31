'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import Link from 'next/link'
import { formatDistanceToNow } from 'date-fns'
import { LeagueStatusStrip } from '@/components/LeagueStatusStrip'

interface League {
  id: number
  provider: string
  provider_league_id: string
  name: string
  season: number
  week: number | null
  num_teams: number
  groupme_bot_id: string | null
  enable_power_rankings: boolean
  enable_waiver_recaps: boolean
  enable_llm_rendering: boolean
  ai_persona_style: string | null
  is_active: boolean
  last_sync_at: string | null
}

interface SyncState {
  status: 'idle' | 'syncing' | 'success' | 'failure'
  taskId?: string
}

type SyncStates = Map<number, SyncState>

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function DashboardContent() {
  const { user, logout } = useAuth()
  const [leagues, setLeagues] = useState<League[]>([])
  const [leagueWeeks, setLeagueWeeks] = useState<Map<number, number>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncStates, setSyncStates] = useState<SyncStates>(new Map())
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  useEffect(() => {
    fetchLeagues()
  }, [])

  // Initialize weeks from league data
  useEffect(() => {
    if (leagues.length > 0) {
      const initialWeeks = new Map<number, number>()
      leagues.forEach(league => {
        initialWeeks.set(league.id, league.week || 1)
      })
      setLeagueWeeks(initialWeeks)
    }
  }, [leagues])

  // Auto-dismiss toast after 5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  const fetchLeagues = async () => {
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
        throw new Error('Failed to fetch leagues')
      }

      const data = await response.json()
      setLeagues(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leagues')
    } finally {
      setLoading(false)
    }
  }

  const pollTaskStatus = async (leagueId: number, taskId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/admin/tasks/${taskId}`, {
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error('Failed to fetch task status')
        }

        const data = await response.json()

        if (data.status === 'SUCCESS') {
          setSyncStates(prev => new Map(prev).set(leagueId, { status: 'success' }))
          setToast({ message: 'Sync completed successfully!', type: 'success' })

          // Reset to idle after 2 seconds
          setTimeout(() => {
            setSyncStates(prev => new Map(prev).set(leagueId, { status: 'idle' }))
            fetchLeagues() // Refresh leagues to update last_sync_at
          }, 2000)
        } else if (data.status === 'FAILURE') {
          setSyncStates(prev => new Map(prev).set(leagueId, { status: 'failure' }))
          setToast({
            message: `Sync failed: ${data.error || 'Unknown error'}`,
            type: 'error'
          })
        } else {
          // Still pending or started, continue polling
          setTimeout(poll, 2000)
        }
      } catch (err) {
        setSyncStates(prev => new Map(prev).set(leagueId, { status: 'failure' }))
        setToast({
          message: 'Failed to check sync status',
          type: 'error'
        })
      }
    }

    poll()
  }

  const handleSync = async (leagueId: number) => {
    try {
      setSyncStates(prev => new Map(prev).set(leagueId, { status: 'syncing' }))
      const week = leagueWeeks.get(leagueId) || 1

      const response = await fetch(`${API_BASE}/admin/leagues/${leagueId}/sync?week=${week}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error('Failed to start sync')
      }

      const data = await response.json()

      // Start polling for task status
      if (data.task_id) {
        setSyncStates(prev => new Map(prev).set(leagueId, {
          status: 'syncing',
          taskId: data.task_id
        }))
        pollTaskStatus(leagueId, data.task_id)
      }
    } catch (err) {
      setSyncStates(prev => new Map(prev).set(leagueId, { status: 'failure' }))
      setToast({
        message: err instanceof Error ? err.message : 'Failed to start sync',
        type: 'error'
      })
    }
  }

  const formatLastSync = (lastSyncAt: string | null) => {
    if (!lastSyncAt) return 'Never'

    try {
      const date = new Date(lastSyncAt)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return 'Unknown'
    }
  }

  const getSyncButtonContent = (leagueId: number) => {
    const state = syncStates.get(leagueId)

    switch (state?.status) {
      case 'syncing':
        return (
          <>
            <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Syncing...
          </>
        )
      case 'success':
        return '✓ Synced'
      case 'failure':
        return '⚠ Failed - Retry?'
      default:
        return 'Sync'
    }
  }

  const isSyncDisabled = (leagueId: number) => {
    const state = syncStates.get(leagueId)
    return state?.status === 'syncing' || state?.status === 'success'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading leagues...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in">
          <div className={`rounded-lg px-4 py-3 shadow-lg ${
            toast.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            <div className="flex items-center">
              {toast.type === 'success' ? (
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              <span className="font-medium">{toast.message}</span>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
          <div className="mb-4 sm:mb-0">
            <h1 className="text-3xl font-bold text-gray-900 mb-1">
              Operator Console
            </h1>
            <p className="text-gray-600">
              Manage leagues and trigger manual syncs
            </p>
          </div>

          <button
              onClick={logout}
              className="text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md text-sm font-medium transition-colors border border-gray-300 hover:bg-gray-50"
            >
              Sign Out
            </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="ml-3">
                <p className="text-sm font-medium text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* League Status Strip - shows status for first active league */}
        {leagues.length > 0 && (
          <div className="mb-6">
            <LeagueStatusStrip leagueId={leagues[0].id} />
          </div>
        )}

        {/* League Table */}
        {leagues.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No leagues yet</h3>
            <p className="text-gray-600 mb-6">Connect a league to get started</p>
            <Link
              href="/connect"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Connect League
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      League Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Platform
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Sync
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {leagues.map((league) => (
                    <tr key={league.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-gray-900">{league.name}</div>
                        <div className="text-xs text-gray-500">
                          Season {league.season} • Week {league.week || '—'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          league.provider === 'sleeper'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-purple-100 text-purple-800'
                        }`}>
                          {league.provider.charAt(0).toUpperCase() + league.provider.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatLastSync(league.last_sync_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          league.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {league.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end gap-3">
                          <div className="flex items-center gap-1">
                            <span className="text-xs text-gray-500">Week</span>
                            <input
                              type="number"
                              min="1"
                              max="18"
                              value={leagueWeeks.get(league.id) || league.week || 1}
                              onChange={(e) => {
                                const week = parseInt(e.target.value) || 1
                                setLeagueWeeks(prev => new Map(prev).set(league.id, week))
                              }}
                              className="w-14 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                          <Link
                            href={`/league/${league.id}`}
                            className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
                          >
                            View League
                          </Link>
                          <button
                            onClick={() => handleSync(league.id)}
                            disabled={isSyncDisabled(league.id)}
                            className={`inline-flex items-center px-3 py-2 border text-sm font-medium rounded-md transition-colors ${
                              isSyncDisabled(league.id)
                                ? 'border-gray-300 bg-gray-100 text-gray-400 cursor-not-allowed'
                                : syncStates.get(league.id)?.status === 'failure'
                                ? 'border-red-300 bg-red-50 text-red-700 hover:bg-red-100'
                                : 'border-blue-300 bg-blue-50 text-blue-700 hover:bg-blue-100'
                            }`}
                          >
                            {getSyncButtonContent(league.id)}
                          </button>
                          <Link
                            href={`/settings/${league.id}`}
                            className="text-gray-600 hover:text-gray-900 font-medium"
                          >
                            Settings →
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="md:hidden divide-y divide-gray-200">
              {leagues.map((league) => (
                <div key={league.id} className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900">{league.name}</h3>
                      <p className="text-xs text-gray-500">Season {league.season} • Week {league.week || '—'}</p>
                    </div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      league.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {league.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                    <div>
                      <span className="text-gray-500">Platform:</span>
                      <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        league.provider === 'sleeper'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {league.provider.charAt(0).toUpperCase() + league.provider.slice(1)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Last Sync:</span>
                      <span className="ml-2 text-gray-900">{formatLastSync(league.last_sync_at)}</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 whitespace-nowrap">Sync Week:</span>
                      <input
                        type="number"
                        min="1"
                        max="18"
                        value={leagueWeeks.get(league.id) || league.week || 1}
                        onChange={(e) => {
                          const week = parseInt(e.target.value) || 1
                          setLeagueWeeks(prev => new Map(prev).set(league.id, week))
                        }}
                        className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <Link
                      href={`/league/${league.id}`}
                      className="w-full inline-flex items-center justify-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors"
                    >
                      View League
                    </Link>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSync(league.id)}
                        disabled={isSyncDisabled(league.id)}
                        className={`flex-1 inline-flex items-center justify-center px-3 py-2 border text-sm font-medium rounded-md transition-colors ${
                          isSyncDisabled(league.id)
                            ? 'border-gray-300 bg-gray-100 text-gray-400 cursor-not-allowed'
                            : syncStates.get(league.id)?.status === 'failure'
                            ? 'border-red-300 bg-red-50 text-red-700'
                            : 'border-blue-300 bg-blue-50 text-blue-700'
                        }`}
                      >
                        {getSyncButtonContent(league.id)}
                      </button>
                      <Link
                        href={`/settings/${league.id}`}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        Settings →
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  )
}
