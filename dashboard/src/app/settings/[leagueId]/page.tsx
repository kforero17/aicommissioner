'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { LeagueStatusStrip } from '@/components/LeagueStatusStrip'

interface LeagueData {
  id: number
  name: string
  season: number
  week: number | null
  enable_power_rankings: boolean
  enable_waiver_recaps: boolean
  ai_persona_style: string | null
  enable_llm_rendering: boolean
  power_rankings_day: string
  power_rankings_time: string
  waiver_recap_day: string
  waiver_recap_time: string
  enable_email_recaps: boolean
  has_email_recipients: boolean
  groupme_bot_id: string | null
  commissioner_notes: string | null
}

interface LeagueSettings {
  enable_power_rankings: boolean
  enable_waiver_recaps: boolean
  ai_persona_style: string
  enable_llm_rendering: boolean
  power_rankings_day: string
  power_rankings_time: string
  waiver_recap_day: string
  waiver_recap_time: string
  commissioner_notes: string
}

interface LeagueMember {
  id: number
  email: string
  username?: string
  role: 'commissioner' | 'member'
  status: 'active' | 'pending'
  joined_at?: string
}

interface TaskStatus {
  task_id: string
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY'
  result?: Record<string, unknown>
  error?: string
  progress?: Record<string, unknown>
}

const STYLE_OPTIONS = [
  { value: 'witty', label: 'Witty — Clever humor, puns, and playful roasting' },
  { value: 'professional', label: 'Professional — ESPN-style sports journalism' },
  { value: 'roastmaster', label: 'Roastmaster — Savage trash talk and brutal honesty' },
  { value: 'hype', label: 'Hype — Maximum energy and excitement' },
  { value: 'analyst', label: 'Analyst — Deep strategy and statistical insights' },
  { value: 'casual', label: 'Casual — Friendly group chat vibes' },
]

const DAYS = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday'
]

const TIMES = [
  '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
  '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
  '18:00', '19:00', '20:00', '21:00', '22:00'
]

interface ScheduleRowProps {
  title: string
  description: string
  enabled: boolean
  onToggle: () => void
  day: string
  time: string
  onDayChange: (day: string) => void
  onTimeChange: (time: string) => void
  destinations: string[]
}

function ScheduleRow({
  title,
  description,
  enabled,
  onToggle,
  day,
  time,
  onDayChange,
  onTimeChange,
  destinations
}: ScheduleRowProps) {
  const formatTime = (time24: string) => {
    const [hours, minutes] = time24.split(':')
    const hour = parseInt(hours)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const hour12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour
    return `${hour12}:${minutes} ${ampm}`
  }

  const formatDay = (day: string) => {
    return day.charAt(0).toUpperCase() + day.slice(1)
  }

  return (
    <div className={`flex items-center gap-4 p-4 rounded-lg border ${
      enabled ? 'border-gray-200 bg-white' : 'border-gray-100 bg-gray-50'
    }`}>
      <button
        type="button"
        onClick={onToggle}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
          enabled ? 'bg-blue-600' : 'bg-gray-200'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            enabled ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>

      <div className="flex-1">
        <div className="flex items-center gap-3 mb-1">
          <span className={`font-medium ${enabled ? 'text-gray-900' : 'text-gray-500'}`}>
            {title}
          </span>
          {enabled && (
            <>
              <select
                value={day}
                onChange={(e) => onDayChange(e.target.value)}
                className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {DAYS.map(d => (
                  <option key={d} value={d}>
                    {formatDay(d)}
                  </option>
                ))}
              </select>
              <select
                value={time}
                onChange={(e) => onTimeChange(e.target.value)}
                className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {TIMES.map(t => (
                  <option key={t} value={t}>
                    {formatTime(t)}
                  </option>
                ))}
              </select>
              <span className="text-sm text-gray-500">CT</span>
            </>
          )}
        </div>
        <p className={`text-sm ${enabled ? 'text-gray-600' : 'text-gray-400'}`}>
          {description}
        </p>
      </div>

      {enabled && (
        <div className="flex items-center gap-2">
          {destinations.length > 0 ? (
            destinations.map(dest => (
              <span
                key={dest}
                className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-md"
              >
                {dest}
              </span>
            ))
          ) : (
            <span className="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-700 rounded-md">
              No destinations
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const params = useParams()
  const leagueId = params.leagueId as string

  const [leagueName, setLeagueName] = useState<string>('')
  const [currentWeek, setCurrentWeek] = useState<number | null>(null)
  const [settings, setSettings] = useState<LeagueSettings>({
    enable_power_rankings: true,
    enable_waiver_recaps: true,
    ai_persona_style: 'witty',
    enable_llm_rendering: false,
    power_rankings_day: 'tuesday',
    power_rankings_time: '09:00',
    waiver_recap_day: 'wednesday',
    waiver_recap_time: '09:00',
    commissioner_notes: ''
  })
  const [groupmeBotId, setGroupmeBotId] = useState<string | null>(null)
  const [enableEmailRecaps, setEnableEmailRecaps] = useState(false)
  const [hasEmailRecipients, setHasEmailRecipients] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testSending, setTestSending] = useState(false)
  const [testProgress, setTestProgress] = useState<string>('')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [previewContent, setPreviewContent] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [testModeEnabled, setTestModeEnabled] = useState(true)
  const [publishing, setPublishing] = useState(false)
  const [members, setMembers] = useState<LeagueMember[]>([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [inviteUrl, setInviteUrl] = useState<string | null>(null)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [generatingInvite, setGeneratingInvite] = useState(false)
  const [copiedInvite, setCopiedInvite] = useState(false)

  const showMessage = useCallback((type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }, [])

  const loadSettings = useCallback(async () => {
    try {
      const response = await fetch('/admin/leagues', { credentials: 'include' })
      if (response.ok) {
        const leagues: LeagueData[] = await response.json()
        const league = leagues.find(l => l.id === parseInt(leagueId))
        if (league) {
          setLeagueName(league.name)
          setCurrentWeek(league.week)
          setSettings({
            enable_power_rankings: league.enable_power_rankings,
            enable_waiver_recaps: league.enable_waiver_recaps,
            ai_persona_style: league.ai_persona_style || 'witty',
            enable_llm_rendering: league.enable_llm_rendering,
            power_rankings_day: league.power_rankings_day || 'tuesday',
            power_rankings_time: league.power_rankings_time || '09:00',
            waiver_recap_day: league.waiver_recap_day || 'wednesday',
            waiver_recap_time: league.waiver_recap_time || '09:00',
            commissioner_notes: league.commissioner_notes || ''
          })
          setGroupmeBotId(league.groupme_bot_id)
          setEnableEmailRecaps(league.enable_email_recaps)
          setHasEmailRecipients(league.has_email_recipients)
        } else {
          showMessage('error', 'League not found')
        }
      } else if (response.status === 401) {
        showMessage('error', 'Please log in to access settings')
      } else {
        showMessage('error', 'Failed to load league settings')
      }
    } catch {
      showMessage('error', 'Network error loading settings')
    } finally {
      setLoading(false)
    }
  }, [leagueId, showMessage])

  useEffect(() => {
    loadSettings()
    loadMembers()
  }, [loadSettings])

  const loadMembers = async () => {
    try {
      setMembersLoading(true)
      const response = await fetch(`/admin/leagues/${leagueId}/members`, {
        credentials: 'include'
      })
      if (response.ok) {
        const data: LeagueMember[] = await response.json()
        setMembers(data)
      }
    } catch {
      // Silent fail - members section will show empty
    } finally {
      setMembersLoading(false)
    }
  }

  const generateInviteLink = async () => {
    try {
      setGeneratingInvite(true)
      const response = await fetch(`/admin/leagues/${leagueId}/invite`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        const data = await response.json()
        setInviteUrl(data.invite_url)
        setShowInviteModal(true)
        setCopiedInvite(false)
      } else {
        showMessage('error', 'Failed to generate invite link')
      }
    } catch {
      showMessage('error', 'Network error generating invite')
    } finally {
      setGeneratingInvite(false)
    }
  }

  const copyInviteLink = () => {
    if (inviteUrl) {
      navigator.clipboard.writeText(inviteUrl)
      setCopiedInvite(true)
      setTimeout(() => setCopiedInvite(false), 2000)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    setMessage(null)

    try {
      const response = await fetch(`/admin/leagues/${leagueId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        showMessage('success', 'Settings saved successfully!')
        await loadSettings()
      } else if (response.status === 401) {
        showMessage('error', 'Your session has expired. Please log in again.')
      } else if (response.status === 404) {
        const error = await response.json().catch(() => ({}))
        console.error('Save failed with 404:', error)
        showMessage('error', error.detail || 'League not found. You may not have permission to edit this league.')
      } else {
        const error = await response.json().catch(() => ({}))
        console.error(`Save failed with status ${response.status}:`, error)
        showMessage('error', error.detail || 'Failed to save settings')
      }
    } catch (err) {
      console.error('Network error saving settings:', err)
      showMessage('error', 'Network error saving settings. Please check your connection.')
    } finally {
      setSaving(false)
    }
  }

  const pollTaskStatus = async (taskId: string): Promise<TaskStatus> => {
    const response = await fetch(`/admin/tasks/${taskId}`, { credentials: 'include' })
    if (!response.ok) throw new Error('Failed to check task status')
    return response.json()
  }

  const generatePreview = async () => {
    setTestSending(true)
    setMessage(null)
    setTestProgress('Starting content generation...')

    try {
      const response = await fetch('/admin/recaps/power-rankings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          league_id: parseInt(leagueId),
          week: currentWeek,
          preview_only: true
        }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          showMessage('error', 'Please log in to generate content')
          return
        }
        if (response.status === 400) {
          const error = await response.json().catch(() => ({}))
          showMessage('error', error.detail || 'Power rankings are disabled for this league')
          return
        }
        showMessage('error', 'Failed to start content generation')
        return
      }

      const data = await response.json()
      const { task_id, status: taskStatus, result: inlineResult } = data

      // Direct result (no Celery) — use inline content
      if (taskStatus === 'SUCCESS' && inlineResult) {
        const content = inlineResult.content as string
        if (content) {
          setPreviewContent(content)
          setShowPreview(true)
        } else {
          showMessage('error', 'No content returned from preview')
        }
        setTestProgress('')
        return
      }

      if (!task_id) {
        showMessage('error', 'Failed to start content generation')
        setTestProgress('')
        return
      }

      setTestProgress('Generating power rankings preview...')

      const maxAttempts = 60
      for (let i = 0; i < maxAttempts; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        const status = await pollTaskStatus(task_id)

        if (status.status === 'SUCCESS') {
          const content = status.result?.content as string
          if (content) {
            setPreviewContent(content)
            setShowPreview(true)
            setTestProgress('')
          } else {
            showMessage('error', 'No content returned from preview')
            setTestProgress('')
          }
          return
        }

        if (status.status === 'FAILURE') {
          showMessage('error', status.error || 'Content generation failed')
          setTestProgress('')
          return
        }

        if (status.status === 'STARTED' && status.progress) {
          setTestProgress(`Generating: ${JSON.stringify(status.progress)}`)
        }
      }

      showMessage('error', 'Content generation timed out')
    } catch (err) {
      showMessage('error', err instanceof Error ? err.message : 'Network error occurred')
    } finally {
      setTestSending(false)
      setTestProgress('')
    }
  }

  const publishContent = async () => {
    if (!previewContent) return

    setPublishing(true)
    setMessage(null)

    try {
      const response = await fetch('/admin/recaps/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          league_id: parseInt(leagueId),
          content: previewContent,
          test_mode: testModeEnabled
        }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          showMessage('error', 'Please log in to publish content')
          return
        }
        const error = await response.json().catch(() => ({}))
        showMessage('error', error.detail || 'Failed to publish content')
        return
      }

      showMessage('success', testModeEnabled ? 'Test post sent successfully!' : 'Post sent to group!')
      setShowPreview(false)
      setPreviewContent(null)
    } catch (err) {
      showMessage('error', err instanceof Error ? err.message : 'Network error occurred')
    } finally {
      setPublishing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            League Settings
          </h1>
          <p className="text-gray-600 mt-2">
            {leagueName || `League ${leagueId}`}
            {currentWeek && <span className="ml-2 text-sm">(Week {currentWeek})</span>}
          </p>
        </div>

        <div className="mb-6">
          <LeagueStatusStrip leagueId={leagueId} />
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Recap Schedule</h2>
          <p className="text-sm text-gray-500 mb-6">Configure when and where your recaps are delivered</p>

          <div className="space-y-4">
            <ScheduleRow
              title="Power Rankings"
              description="Weekly standings and matchup analysis"
              enabled={settings.enable_power_rankings}
              onToggle={() => setSettings(prev => ({ ...prev, enable_power_rankings: !prev.enable_power_rankings }))}
              day={settings.power_rankings_day}
              time={settings.power_rankings_time}
              onDayChange={(day) => setSettings(prev => ({ ...prev, power_rankings_day: day }))}
              onTimeChange={(time) => setSettings(prev => ({ ...prev, power_rankings_time: time }))}
              destinations={(() => {
                const dests = []
                if (groupmeBotId) dests.push('GroupMe')
                if (enableEmailRecaps && hasEmailRecipients) dests.push('Email')
                return dests
              })()}
            />

            <div className="border-t border-gray-100" />

            <ScheduleRow
              title="Waiver Report"
              description="FAAB spending and pickup activity"
              enabled={settings.enable_waiver_recaps}
              onToggle={() => setSettings(prev => ({ ...prev, enable_waiver_recaps: !prev.enable_waiver_recaps }))}
              day={settings.waiver_recap_day}
              time={settings.waiver_recap_time}
              onDayChange={(day) => setSettings(prev => ({ ...prev, waiver_recap_day: day }))}
              onTimeChange={(time) => setSettings(prev => ({ ...prev, waiver_recap_time: time }))}
              destinations={(() => {
                const dests = []
                if (groupmeBotId) dests.push('GroupMe')
                if (enableEmailRecaps && hasEmailRecipients) dests.push('Email')
                return dests
              })()}
            />
          </div>

          {!groupmeBotId && !enableEmailRecaps && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-700">
                No publishing destinations configured. Add GroupMe or Email in the Destinations section below.
              </p>
            </div>
          )}
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">League Members</h2>
          <p className="text-sm text-gray-500 mb-6">
            Share your league with members so they can view content and access recaps
          </p>

          <div className="mb-6">
            <button
              onClick={generateInviteLink}
              disabled={generatingInvite}
              className={`w-full sm:w-auto px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors ${
                generatingInvite
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {generatingInvite ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Generating...
                </span>
              ) : (
                <span className="flex items-center">
                  <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Generate Invite Link
                </span>
              )}
            </button>
          </div>

          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-900">
                Current Members ({members.length})
              </h3>
            </div>

            {membersLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse flex items-center p-3 border border-gray-200 rounded-lg">
                    <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                  </div>
                ))}
              </div>
            ) : members.length > 0 ? (
              <div className="space-y-2">
                {members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                        member.role === 'commissioner'
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {member.role === 'commissioner' ? (
                          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M9.504 1.132a1 1 0 01.992 0l1.75 1a1 1 0 11-.992 1.736L10 3.152l-1.254.716a1 1 0 11-.992-1.736l1.75-1zM5.618 4.504a1 1 0 01-.372 1.364L5.016 6l.23.132a1 1 0 11-.992 1.736L4 7.723V8a1 1 0 01-2 0V6a.996.996 0 01.52-.878l1.734-.99a1 1 0 011.364.372zm8.764 0a1 1 0 011.364-.372l1.733.99A1.002 1.002 0 0118 6v2a1 1 0 11-2 0v-.277l-.254.145a1 1 0 11-.992-1.736l.23-.132-.23-.132a1 1 0 01-.372-1.364zm-7 4a1 1 0 011.364-.372L10 8.848l1.254-.716a1 1 0 11.992 1.736L11 10.58V12a1 1 0 11-2 0v-1.42l-1.246-.712a1 1 0 01-.372-1.364zM3 11a1 1 0 011 1v1.42l1.246.712a1 1 0 11-.992 1.736l-1.75-1A1 1 0 012 14v-2a1 1 0 011-1zm14 0a1 1 0 011 1v2a1 1 0 01-.504.868l-1.75 1a1 1 0 11-.992-1.736L16 13.42V12a1 1 0 011-1zm-9.618 5.504a1 1 0 011.364-.372l.254.145V16a1 1 0 112 0v.277l.254-.145a1 1 0 11.992 1.736l-1.735.992a.995.995 0 01-.992 0l-1.735-.992a1 1 0 01-.372-1.364z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {member.username || member.email}
                          {member.role === 'commissioner' && (
                            <span className="ml-2 text-xs font-medium text-blue-600">(Commissioner)</span>
                          )}
                        </p>
                        {member.username && (
                          <p className="text-xs text-gray-500">{member.email}</p>
                        )}
                      </div>
                    </div>
                    <div>
                      {member.status === 'pending' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                          Pending
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 border-2 border-dashed border-gray-300 rounded-lg">
                <svg className="mx-auto h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <p className="text-sm text-gray-600">No members yet</p>
                <p className="text-xs text-gray-500 mt-1">Generate an invite link to add members</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Destinations</h2>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div>
                <span className="font-medium text-gray-900">GroupMe</span>
                <p className="text-sm text-gray-500">
                  {groupmeBotId ? 'Connected' : 'Not configured'}
                </p>
              </div>
              <a
                href={`/settings/${leagueId}/groupme`}
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                {groupmeBotId ? 'Edit' : 'Setup'}
              </a>
            </div>

            <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
              <div>
                <span className="font-medium text-gray-900">Email</span>
                <p className="text-sm text-gray-500">
                  {hasEmailRecipients ? 'Recipients configured' : 'No recipients'}
                </p>
              </div>
              <a
                href={`/settings/${leagueId}/email`}
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                {hasEmailRecipients ? 'Edit' : 'Setup'}
              </a>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Writing Engine</h2>
          <p className="text-sm text-gray-500 mb-6">Choose how your recaps are generated</p>

          <div className="space-y-3 mb-6">
            <label className={`flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
              !settings.enable_llm_rendering
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input
                type="radio"
                name="writing_engine"
                checked={!settings.enable_llm_rendering}
                onChange={() => setSettings(prev => ({ ...prev, enable_llm_rendering: false }))}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <div className="ml-3">
                <span className="font-medium text-gray-900">Template Mode</span>
                <span className="ml-2 text-xs font-medium text-green-600 bg-green-100 px-2 py-0.5 rounded">Fast</span>
                <p className="text-sm text-gray-500 mt-1">
                  Reliable and consistent. Uses structured templates for predictable output every time.
                </p>
              </div>
            </label>

            <label className={`flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
              settings.enable_llm_rendering
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}>
              <input
                type="radio"
                name="writing_engine"
                checked={settings.enable_llm_rendering}
                onChange={() => setSettings(prev => ({ ...prev, enable_llm_rendering: true }))}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
              />
              <div className="ml-3">
                <span className="font-medium text-gray-900">AI Enhanced</span>
                <span className="ml-2 text-xs font-medium text-purple-600 bg-purple-100 px-2 py-0.5 rounded">More Personality</span>
                <p className="text-sm text-gray-500 mt-1">
                  Creative and dynamic. AI writes unique content with personality and flair.
                </p>
              </div>
            </label>
          </div>

          {settings.enable_llm_rendering && (
            <div className="text-xs text-gray-500 mb-6 p-3 bg-gray-50 rounded-lg">
              💡 AI Enhanced may take 10–20 seconds longer and can occasionally be more opinionated.
            </div>
          )}

          {settings.enable_llm_rendering && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                AI Personality
              </label>
              <select
                value={settings.ai_persona_style}
                onChange={(e) => setSettings(prev => ({ ...prev, ai_persona_style: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {STYLE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-2">
                This sets the tone for how your AI writes recaps
              </p>
            </div>
          )}

          {settings.enable_llm_rendering && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Commissioner Notes
              </label>
              <textarea
                value={settings.commissioner_notes}
                onChange={(e) => setSettings(prev => ({ ...prev, commissioner_notes: e.target.value }))}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Add league lore, rivalries, nicknames, running jokes... The AI will weave these into recaps."
              />
              <p className="text-xs text-gray-500 mt-2">
                Give the AI context about your league — rivalries, inside jokes, team nicknames. This makes recaps feel personal.
              </p>
            </div>
          )}
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Test & Preview</h2>
          <p className="text-sm text-gray-600 mb-4">
            Preview how your power rankings will look before sending to your group. This is safe - nothing gets published until you click &quot;Send to Group&quot;.
          </p>
          <button
            onClick={generatePreview}
            disabled={testSending || !settings.enable_power_rankings}
            className={`w-full py-2 px-4 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 ${
              testSending || !settings.enable_power_rankings
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {testSending ? 'Generating Preview...' : 'Preview Power Rankings'}
          </button>
          {!settings.enable_power_rankings && (
            <p className="text-sm text-amber-600 mt-2">
              Enable power rankings above to preview content.
            </p>
          )}
          {testProgress && (
            <div className="mt-3 flex items-center text-sm text-blue-600">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {testProgress}
            </div>
          )}
        </div>

        {showPreview && previewContent && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
              <div className="p-6 border-b border-gray-200">
                <h3 className="text-xl font-semibold text-gray-900">Preview Power Rankings</h3>
                <p className="text-sm text-gray-600 mt-1">Review the content before sending to your group</p>
              </div>

              <div className="p-6 overflow-y-auto flex-1">
                <div className="bg-gray-50 rounded-md p-4 font-mono text-sm whitespace-pre-wrap">
                  {previewContent}
                </div>
              </div>

              <div className="p-6 border-t border-gray-200 space-y-4">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="test-mode"
                    checked={testModeEnabled}
                    onChange={(e) => setTestModeEnabled(e.target.checked)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="test-mode" className="text-sm text-gray-700">
                    Send as TEST (prefix with [TEST] tag)
                  </label>
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={() => {
                      setShowPreview(false)
                      setPreviewContent(null)
                    }}
                    disabled={publishing}
                    className="flex-1 py-2 px-4 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Close
                  </button>
                  <button
                    onClick={publishContent}
                    disabled={publishing}
                    className={`flex-1 py-2 px-4 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-200 ${
                      publishing
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-green-600 hover:bg-green-700'
                    }`}
                  >
                    {publishing ? 'Sending...' : 'Send to Group'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="flex space-x-4">
          <button
            onClick={saveSettings}
            disabled={saving}
            className={`flex-1 py-2 px-4 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition duration-200 ${
              saving 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>

        {message && (
          <div className={`mt-4 p-4 rounded-md ${
            message.type === 'success'
              ? 'bg-green-100 text-green-700'
              : 'bg-red-100 text-red-700'
          }`}>
            {message.text}
          </div>
        )}

        {showInviteModal && inviteUrl && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Invite Link Generated</h3>
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <p className="text-sm text-gray-600 mb-4">
                Share this link with league members. They&apos;ll be able to view your league content and recaps.
              </p>

              <div className="bg-gray-50 rounded-lg p-3 mb-4">
                <p className="text-xs text-gray-700 break-all font-mono">{inviteUrl}</p>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={copyInviteLink}
                  className={`flex-1 px-4 py-2 rounded-md text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors ${
                    copiedInvite
                      ? 'bg-green-600 hover:bg-green-700'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {copiedInvite ? (
                    <span className="flex items-center justify-center">
                      <svg className="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Copied!
                    </span>
                  ) : (
                    <span className="flex items-center justify-center">
                      <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy Link
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
