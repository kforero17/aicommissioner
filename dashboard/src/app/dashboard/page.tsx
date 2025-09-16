'use client'

import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import Link from 'next/link'

function DashboardContent() {
  const { user, logout } = useAuth()
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Welcome back, {user?.name || user?.email}!
            </h1>
            <p className="text-gray-600">
              Manage your leagues and view your automated content
            </p>
          </div>
          <button
            onClick={logout}
            className="text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md text-sm font-medium transition-colors border border-gray-300 hover:bg-gray-50"
          >
            Sign Out
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* League Overview Card */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Your Leagues</h3>
              <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm font-medium">
                1 Active
              </span>
            </div>
            <p className="text-gray-600 mb-4">
              You have 1 connected league with automated updates enabled.
            </p>
            <Link 
              href="/settings"
              className="text-blue-600 hover:text-blue-700 font-medium text-sm"
            >
              Manage Leagues →
            </Link>
          </div>

          {/* Recent Recaps Card */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Recaps</h3>
            <div className="space-y-3">
              <div className="border-l-4 border-green-500 pl-4">
                <p className="font-medium text-gray-900">Week 12 Recap</p>
                <p className="text-sm text-gray-600">Sent 2 days ago</p>
              </div>
              <div className="border-l-4 border-blue-500 pl-4">
                <p className="font-medium text-gray-900">Power Rankings</p>
                <p className="text-sm text-gray-600">Sent 5 days ago</p>
              </div>
            </div>
            <Link 
              href="/preview"
              className="text-blue-600 hover:text-blue-700 font-medium text-sm mt-4 inline-block"
            >
              View All →
            </Link>
          </div>

          {/* Quick Actions Card */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-3">
              <Link
                href="/demo"
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-3 rounded-lg transition-colors duration-200 text-sm font-medium block text-center"
              >
                View Demo Content
              </Link>
              <Link
                href="/settings"
                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-3 rounded-lg transition-colors duration-200 text-sm font-medium block text-center"
              >
                Update Preferences
              </Link>
              <button
                onClick={() => router.push('/connect')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg transition-colors duration-200 text-sm font-medium"
              >
                Add Another League
              </button>
            </div>
          </div>
        </div>

        {/* Status Banner */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-green-800">
                All systems operational
              </p>
              <p className="text-sm text-green-700">
                Your next weekly recap will be sent on Tuesday at 9:00 AM
              </p>
            </div>
          </div>
        </div>
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
