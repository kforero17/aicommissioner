'use client'

import { useState, useEffect } from 'react'
import { formatDistanceToNow, format } from 'date-fns'

interface LastGenerated {
  type: 'power_rankings' | 'waiver_recap' | null
  timestamp: string
  week: number
  label: string
}

interface NextScheduled {
  type: 'power_rankings' | 'waiver_recap'
  timestamp: string
  label: string
}

interface Health {
  status: 'connected' | 'warning' | 'error'
  message: string
  last_sync: string
}

interface LeagueStatus {
  last_generated: LastGenerated | null
  next_scheduled: NextScheduled | null
  publishing_to: string[]
  health: Health
}

interface LeagueStatusStripProps {
  leagueId: number | string
}

export function LeagueStatusStrip({ leagueId }: LeagueStatusStripProps) {
  const [status, setStatus] = useState<LeagueStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`/admin/leagues/${leagueId}/status`, {
          credentials: 'include'
        })

        if (response.ok) {
          const data = await response.json()
          setStatus(data)
          setError(false)
        } else {
          setError(true)
        }
      } catch {
        setError(true)
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 60000)
    return () => clearInterval(interval)
  }, [leagueId])

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-48" />
          <div className="h-4 bg-gray-200 rounded w-40" />
          <div className="h-4 bg-gray-200 rounded w-32" />
          <div className="h-4 bg-gray-200 rounded w-36" />
        </div>
      </div>
    )
  }

  if (error || !status) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-amber-800 text-sm">
          <span className="text-lg">⚠️</span>
          <span>Unable to load league status</span>
        </div>
      </div>
    )
  }

  const healthStyles = {
    connected: 'text-green-700',
    warning: 'text-amber-700',
    error: 'text-red-700'
  }

  const healthIcons = {
    connected: '✅',
    warning: '⚠️',
    error: '❌'
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex flex-col md:flex-row md:items-center gap-4 md:divide-x md:divide-blue-200">
        {/* Last Generated */}
        <div className="flex items-start gap-2 md:pr-4">
          <span className="text-lg" aria-label="Last generated">🕐</span>
          <div className="flex flex-col">
            <span className="text-xs text-blue-600 font-medium">Last</span>
            {status.last_generated ? (
              <>
                <span className="text-sm text-gray-900 font-medium">
                  {format(new Date(status.last_generated.timestamp), 'EEE h:mmaaa')}
                </span>
                <span className="text-xs text-gray-600">
                  {status.last_generated.label}
                </span>
              </>
            ) : (
              <span className="text-sm text-gray-500 italic">None yet</span>
            )}
          </div>
        </div>

        {/* Next Scheduled */}
        <div className="flex items-start gap-2 md:px-4">
          <span className="text-lg" aria-label="Next scheduled">📅</span>
          <div className="flex flex-col">
            <span className="text-xs text-blue-600 font-medium">Next</span>
            {status.next_scheduled ? (
              <>
                <span className="text-sm text-gray-900 font-medium">
                  {format(new Date(status.next_scheduled.timestamp), 'EEE h:mmaaa')}
                </span>
                <span className="text-xs text-gray-600">
                  {status.next_scheduled.label}
                </span>
              </>
            ) : (
              <span className="text-sm text-gray-500 italic">Not scheduled</span>
            )}
          </div>
        </div>

        {/* Publishing To */}
        <div className="flex items-start gap-2 md:px-4">
          <span className="text-lg" aria-label="Publishing to">📢</span>
          <div className="flex flex-col">
            <span className="text-xs text-blue-600 font-medium">Publishing</span>
            {status.publishing_to.length > 0 ? (
              <div className="flex flex-wrap gap-1 mt-1">
                {status.publishing_to.map((channel) => (
                  <span
                    key={channel}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {channel}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-sm text-gray-500 italic">No channels</span>
            )}
          </div>
        </div>

        {/* Health Status */}
        <div className="flex items-start gap-2 md:pl-4">
          <span className="text-lg" aria-label={`Health: ${status.health.status}`}>
            {healthIcons[status.health.status]}
          </span>
          <div className="flex flex-col">
            <span className="text-xs text-blue-600 font-medium">Status</span>
            <span className={`text-sm font-medium ${healthStyles[status.health.status]}`}>
              {status.health.message}
            </span>
            <span className="text-xs text-gray-500">
              {formatDistanceToNow(new Date(status.health.last_sync), { addSuffix: true })}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
