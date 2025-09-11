'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'

interface LeagueSettings {
  enable_power_rankings: boolean
  enable_waiver_recaps: boolean
  ai_persona_style: string
  enable_llm_rendering: boolean
}

const STYLE_OPTIONS = [
  { value: 'balanced', label: 'Balanced' },
  { value: 'snark', label: 'Snark' },
  { value: 'hype', label: 'Hype' },
  { value: 'nerd', label: 'Nerd' }
]

export default function SettingsPage() {
  const params = useParams()
  const leagueId = params.leagueId as string

  const [settings, setSettings] = useState<LeagueSettings>({
    enable_power_rankings: true,
    enable_waiver_recaps: true,
    ai_persona_style: 'balanced',
    enable_llm_rendering: false
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testSending, setTestSending] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadSettings()
  }, [leagueId]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadSettings = async () => {
    try {
      const response = await fetch(`/api/leagues/${leagueId}/settings`)
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch {
      console.error('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    setMessage('')

    try {
      const response = await fetch(`/api/leagues/${leagueId}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        setMessage('Settings saved successfully!')
      } else {
        setMessage('Failed to save settings')
      }
    } catch {
      setMessage('Network error occurred')
    } finally {
      setSaving(false)
    }
  }

  const sendTestPost = async () => {
    setTestSending(true)
    setMessage('')

    try {
      const response = await fetch(`/admin/run/tuesday/${leagueId}`, {
        method: 'POST',
      })

      if (response.ok) {
        setMessage('Test post sent successfully!')
      } else {
        setMessage('Failed to send test post')
      }
    } catch {
      setMessage('Network error occurred')
    } finally {
      setTestSending(false)
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
          <p className="text-gray-600 mt-2">League ID: {leagueId}</p>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Recap Schedule</h2>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-base font-medium text-gray-900">
                  Tuesday Review
                </label>
                <p className="text-sm text-gray-600">
                  Weekly power rankings and matchup analysis
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSettings(prev => ({ 
                  ...prev, 
                  enable_power_rankings: !prev.enable_power_rankings 
                }))}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  settings.enable_power_rankings ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    settings.enable_power_rankings ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-base font-medium text-gray-900">
                  Wednesday Waivers
                </label>
                <p className="text-sm text-gray-600">
                  Waiver wire activity and FAAB spending recap
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSettings(prev => ({ 
                  ...prev, 
                  enable_waiver_recaps: !prev.enable_waiver_recaps 
                }))}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  settings.enable_waiver_recaps ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    settings.enable_waiver_recaps ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">AI Settings</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Writing Style
              </label>
              <select
                value={settings.ai_persona_style}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  ai_persona_style: e.target.value 
                }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {STYLE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-base font-medium text-gray-900">
                  Use LLM
                </label>
                <p className="text-sm text-gray-600">
                  Use AI to generate more creative and personalized content
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.enable_llm_rendering}
                onChange={(e) => setSettings(prev => ({ 
                  ...prev, 
                  enable_llm_rendering: e.target.checked 
                }))}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Test & Preview</h2>
          <button
            onClick={sendTestPost}
            disabled={testSending}
            className={`w-full py-2 px-4 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition duration-200 ${
              testSending 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {testSending ? 'Sending Test...' : 'Send Test Post'}
          </button>
        </div>

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
