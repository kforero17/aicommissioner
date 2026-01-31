'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface InviteValidation {
  valid: boolean
  league_name?: string
  league_id?: number
  invited_by?: string
  error?: string
}

export default function InvitePage() {
  const params = useParams()
  const router = useRouter()
  const { isAuthenticated, user } = useAuth()
  const token = params.token as string

  const [validation, setValidation] = useState<InviteValidation | null>(null)
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    validateToken()
  }, [token])

  const validateToken = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`${API_BASE}/members/invite/${token}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data: InviteValidation = await response.json()
        setValidation(data)
      } else {
        const errorData = await response.json().catch(() => ({}))
        setError(errorData.detail || 'Failed to validate invite link')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const acceptInvite = async () => {
    if (!isAuthenticated) {
      const returnUrl = `/invite/${token}`
      router.push(`/auth/login?returnUrl=${encodeURIComponent(returnUrl)}`)
      return
    }

    try {
      setAccepting(true)
      setError(null)

      const response = await fetch(`${API_BASE}/members/invite/${token}/accept`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        router.push(`/league/${data.league_id}`)
      } else {
        const errorData = await response.json().catch(() => ({}))
        setError(errorData.detail || 'Failed to accept invite')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setAccepting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Validating invite...</p>
        </div>
      </div>
    )
  }

  if (error || !validation || !validation.valid) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-4">
              <svg className="h-10 w-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Invalid Invite Link</h2>
            <p className="text-gray-600 mb-6">
              {error || validation?.error || 'This invite link is invalid or has expired.'}
            </p>
            <Link
              href="/"
              className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              Go to Home
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="text-center mb-6">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 mb-4">
              <svg className="h-10 w-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              You&apos;re Invited!
            </h1>
            <p className="text-gray-600">
              Join your league on All Pro Commish
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
            <div className="text-center">
              <p className="text-sm font-medium text-blue-900 mb-2">League</p>
              <p className="text-2xl font-bold text-gray-900 mb-3">{validation.league_name}</p>
              {validation.invited_by && (
                <p className="text-sm text-gray-600">
                  Invited by <span className="font-medium">{validation.invited_by}</span>
                </p>
              )}
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {isAuthenticated ? (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-green-800">
                      Signed in as {user?.email}
                    </p>
                  </div>
                </div>
              </div>

              <button
                onClick={acceptInvite}
                disabled={accepting}
                className={`w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors ${
                  accepting
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {accepting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Accepting...
                  </>
                ) : (
                  'Accept Invite'
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm text-amber-800 text-center">
                  Please sign in to accept this invite
                </p>
              </div>

              <button
                onClick={acceptInvite}
                className="w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Sign In to Accept
              </button>

              <p className="text-xs text-center text-gray-600">
                Don&apos;t have an account? You&apos;ll be able to create one after clicking above.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
