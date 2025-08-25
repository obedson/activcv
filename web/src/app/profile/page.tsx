'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { profileApi, apiClient } from '@/lib/api'

interface PersonalInfo {
  first_name: string
  last_name: string
  email: string
  phone?: string
  address?: string
  city?: string
  country?: string
  postal_code?: string
}

interface Profile {
  headline?: string
  summary?: string
  linkedin_url?: string
  website_url?: string
  additional_details?: string
}

export default function ProfilePage() {
  const { user, session, loading: authLoading } = useAuth()
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (session?.access_token) {
      // Set the auth token for API requests
      apiClient.setToken(session.access_token)
    }
  }, [session])

  useEffect(() => {
    if (user && session?.access_token) {
      loadProfileData()
    }
  }, [user, session])

  const loadProfileData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Load personal info
      const personalInfoResponse = await profileApi.getPersonalInfo()
      if (personalInfoResponse.data) {
        setPersonalInfo(personalInfoResponse.data)
      }

      // Load profile
      const profileResponse = await profileApi.getProfile()
      if (profileResponse.data) {
        setProfile(profileResponse.data)
      }
    } catch (err) {
      setError('Failed to load profile data')
      console.error('Profile load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePersonalInfoSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const data = {
      first_name: formData.get('first_name') as string,
      last_name: formData.get('last_name') as string,
      email: formData.get('email') as string,
      phone: formData.get('phone') as string || undefined,
      address: formData.get('address') as string || undefined,
      city: formData.get('city') as string || undefined,
      country: formData.get('country') as string || undefined,
      postal_code: formData.get('postal_code') as string || undefined,
    }

    try {
      let response
      if (personalInfo) {
        response = await profileApi.updatePersonalInfo(data)
      } else {
        response = await profileApi.createPersonalInfo(data)
      }

      if (response.data) {
        setPersonalInfo(response.data)
        alert('Personal information saved successfully!')
      } else if (response.error) {
        alert(`Error: ${response.error}`)
      }
    } catch (err) {
      alert('Failed to save personal information')
      console.error('Save error:', err)
    }
  }

  const handleProfileSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const data = {
      headline: formData.get('headline') as string || undefined,
      summary: formData.get('summary') as string || undefined,
      linkedin_url: formData.get('linkedin_url') as string || undefined,
      website_url: formData.get('website_url') as string || undefined,
      additional_details: formData.get('additional_details') as string || undefined,
    }

    try {
      let response
      if (profile) {
        response = await profileApi.updateProfile(data)
      } else {
        response = await profileApi.createProfile(data)
      }

      if (response.data) {
        setProfile(response.data)
        alert('Profile saved successfully!')
      } else if (response.error) {
        alert(`Error: ${response.error}`)
      }
    } catch (err) {
      alert('Failed to save profile')
      console.error('Save error:', err)
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Please log in to view your profile.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-gray-900">Profile Management</h1>
            <p className="text-gray-600">Manage your personal information and profile details</p>
          </div>

          {error && (
            <div className="px-6 py-4 bg-red-50 border-l-4 border-red-400">
              <p className="text-red-700">{error}</p>
            </div>
          )}

          <div className="p-6 space-y-8">
            {/* Personal Information Section */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Personal Information</h2>
              <form onSubmit={handlePersonalInfoSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
                      First Name *
                    </label>
                    <input
                      type="text"
                      id="first_name"
                      name="first_name"
                      required
                      defaultValue={personalInfo?.first_name || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
                      Last Name *
                    </label>
                    <input
                      type="text"
                      id="last_name"
                      name="last_name"
                      required
                      defaultValue={personalInfo?.last_name || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                      Email *
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      required
                      defaultValue={personalInfo?.email || user.email || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                      Phone
                    </label>
                    <input
                      type="tel"
                      id="phone"
                      name="phone"
                      defaultValue={personalInfo?.phone || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="address" className="block text-sm font-medium text-gray-700">
                    Address
                  </label>
                  <input
                    type="text"
                    id="address"
                    name="address"
                    defaultValue={personalInfo?.address || ''}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="city" className="block text-sm font-medium text-gray-700">
                      City
                    </label>
                    <input
                      type="text"
                      id="city"
                      name="city"
                      defaultValue={personalInfo?.city || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="country" className="block text-sm font-medium text-gray-700">
                      Country
                    </label>
                    <input
                      type="text"
                      id="country"
                      name="country"
                      defaultValue={personalInfo?.country || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700">
                      Postal Code
                    </label>
                    <input
                      type="text"
                      id="postal_code"
                      name="postal_code"
                      defaultValue={personalInfo?.postal_code || ''}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Save Personal Information
                </button>
              </form>
            </div>

            {/* Profile Section */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Professional Profile</h2>
              <form onSubmit={handleProfileSubmit} className="space-y-4">
                <div>
                  <label htmlFor="headline" className="block text-sm font-medium text-gray-700">
                    Professional Headline
                  </label>
                  <input
                    type="text"
                    id="headline"
                    name="headline"
                    defaultValue={profile?.headline || ''}
                    placeholder="e.g., Senior Software Engineer | Full-Stack Developer"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label htmlFor="summary" className="block text-sm font-medium text-gray-700">
                    Professional Summary
                  </label>
                  <textarea
                    id="summary"
                    name="summary"
                    rows={4}
                    defaultValue={profile?.summary || ''}
                    placeholder="Brief overview of your professional background and key achievements..."
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="linkedin_url" className="block text-sm font-medium text-gray-700">
                      LinkedIn URL
                    </label>
                    <input
                      type="url"
                      id="linkedin_url"
                      name="linkedin_url"
                      defaultValue={profile?.linkedin_url || ''}
                      placeholder="https://linkedin.com/in/yourprofile"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="website_url" className="block text-sm font-medium text-gray-700">
                      Website URL
                    </label>
                    <input
                      type="url"
                      id="website_url"
                      name="website_url"
                      defaultValue={profile?.website_url || ''}
                      placeholder="https://yourwebsite.com"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="additional_details" className="block text-sm font-medium text-gray-700">
                    Additional Details
                  </label>
                  <textarea
                    id="additional_details"
                    name="additional_details"
                    rows={3}
                    defaultValue={profile?.additional_details || ''}
                    placeholder="Any additional information you'd like to include..."
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Save Profile
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}