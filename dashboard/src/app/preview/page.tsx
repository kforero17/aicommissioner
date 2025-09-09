'use client'

import { useState } from 'react'

interface PreviewRequest {
  league_id: string
  week?: number
  style: string
  persona?: string
  recap_type: string
}

const STYLE_OPTIONS = [
  { value: 'balanced', label: 'Balanced' },
  { value: 'snark', label: 'Snark' },
  { value: 'hype', label: 'Hype' },
  { value: 'nerd', label: 'Nerd' }
]

const RECAP_TYPES = [
  { value: 'power_rankings', label: 'Power Rankings' },
  { value: 'waiver_recap', label: 'Waiver Recap' },
  { value: 'custom', label: 'Custom Recap' }
]

export default function PreviewPage() {
  const [request, setRequest] = useState<PreviewRequest>({
    league_id: '',
    week: undefined,
    style: 'balanced',
    persona: '',
    recap_type: 'power_rankings'
  })
  const [generatedText, setGeneratedText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const generatePreview = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!request.league_id) {
      setError('League ID is required')
      return
    }

    setLoading(true)
    setError('')
    setGeneratedText('')

    try {
      const body: Record<string, string | number | boolean> = {
        league_id: request.league_id,
        style: request.style,
        recap_type: request.recap_type,
        publish: false // Important: don't publish, just generate
      }

      if (request.week) {
        body.week = parseInt(request.week.toString())
      }

      if (request.persona) {
        body.persona = request.persona
      }

      const response = await fetch('/api/preview/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (response.ok) {
        const data = await response.json()
        setGeneratedText(data.recap_text || data.text || 'Generated successfully but no text returned')
      } else {
        const errorText = await response.text()
        setError(`Failed to generate preview: ${errorText}`)
      }
    } catch {
      setError('Network error occurred')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generatedText)
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy text:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Preview Generator
          </h1>
          <p className="text-gray-600 mt-2">
            Generate recap text without publishing to test your settings
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Form */}
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Settings</h2>
            
            <form onSubmit={generatePreview} className="space-y-4">
              <div>
                <label htmlFor="league_id" className="block text-sm font-medium text-gray-700 mb-2">
                  League ID *
                </label>
                <input
                  type="text"
                  id="league_id"
                  value={request.league_id}
                  onChange={(e) => setRequest(prev => ({ ...prev, league_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter league ID"
                  required
                />
              </div>

              <div>
                <label htmlFor="recap_type" className="block text-sm font-medium text-gray-700 mb-2">
                  Recap Type
                </label>
                <select
                  id="recap_type"
                  value={request.recap_type}
                  onChange={(e) => setRequest(prev => ({ ...prev, recap_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {RECAP_TYPES.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="week" className="block text-sm font-medium text-gray-700 mb-2">
                  Week (optional)
                </label>
                <input
                  type="number"
                  id="week"
                  value={request.week || ''}
                  onChange={(e) => setRequest(prev => ({ 
                    ...prev, 
                    week: e.target.value ? parseInt(e.target.value) : undefined 
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Current week if empty"
                  min="1"
                  max="18"
                />
              </div>

              <div>
                <label htmlFor="style" className="block text-sm font-medium text-gray-700 mb-2">
                  Style
                </label>
                <select
                  id="style"
                  value={request.style}
                  onChange={(e) => setRequest(prev => ({ ...prev, style: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {STYLE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="persona" className="block text-sm font-medium text-gray-700 mb-2">
                  Custom Persona (optional)
                </label>
                <input
                  type="text"
                  id="persona"
                  value={request.persona || ''}
                  onChange={(e) => setRequest(prev => ({ ...prev, persona: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., 'witty sports commentator'"
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
                {loading ? 'Generating...' : 'Generate Preview'}
              </button>
            </form>

            {error && (
              <div className="mt-4 p-4 rounded-md bg-red-100 text-red-700">
                {error}
              </div>
            )}
          </div>

          {/* Preview Output */}
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">Preview</h2>
              {generatedText && (
                <button
                  onClick={copyToClipboard}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                >
                  Copy
                </button>
              )}
            </div>

            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Generating preview...</div>
              </div>
            ) : generatedText ? (
              <div className="bg-gray-50 rounded-lg p-4 h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                  {generatedText}
                </pre>
              </div>
            ) : (
              <div className="flex items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
                <div className="text-center">
                  <div className="text-gray-400 text-sm">
                    Generated preview will appear here
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
