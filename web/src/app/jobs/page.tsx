'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api'

interface JobSiteFilters {
    location?: string
    country?: string
    state?: string
    city?: string
    work_mode?: 'remote' | 'hybrid' | 'onsite'
    job_type?: 'full-time' | 'part-time' | 'contract' | 'internship'
    keywords?: string[]
    skills?: string[]
    min_salary?: number
    max_salary?: number
    experience_level?: string
}

interface JobSiteWatchlist {
    id: string
    site_url: string
    site_name?: string
    filters: JobSiteFilters
    is_active: boolean
    last_crawled_at?: string
    created_at: string
    updated_at: string
}

interface Job {
    id: string
    title: string
    company?: string
    location?: string
    work_mode?: 'remote' | 'hybrid' | 'onsite'
    job_type?: 'full-time' | 'part-time' | 'contract' | 'internship'
    description?: string
    compensation?: string
    job_url?: string
    posted_date?: string
    created_at: string
}

interface SuggestedJob {
    id: string
    job_id: string
    match_score: number
    is_viewed: boolean
    is_dismissed: boolean
    created_at: string
    job?: Job
}

interface JobStats {
    total_watchlist_sites: number
    active_sites: number
    total_jobs_found: number
    new_jobs_today: number
    suggested_jobs: number
    unviewed_suggestions: number
    generated_cvs: number
    last_crawl?: string
}

type ActiveTab = 'dashboard' | 'watchlist' | 'suggestions' | 'search'

export default function JobsPage() {
    const { user, session, loading: authLoading } = useAuth()
    const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard')
    const [watchlist, setWatchlist] = useState<JobSiteWatchlist[]>([])
    const [suggestedJobs, setSuggestedJobs] = useState<SuggestedJob[]>([])
    const [searchResults, setSearchResults] = useState<Job[]>([])
    const [stats, setStats] = useState<JobStats | null>(null)
    const [loading, setLoading] = useState(false)
    const [showAddSiteForm, setShowAddSiteForm] = useState(false)

    // Form states
    const [newSiteUrl, setNewSiteUrl] = useState('')
    const [newSiteName, setNewSiteName] = useState('')
    const [newSiteFilters, setNewSiteFilters] = useState<JobSiteFilters>({})

    // Search states
    const [searchKeywords, setSearchKeywords] = useState('')
    const [searchLocation, setSearchLocation] = useState('')
    const [searchWorkMode, setSearchWorkMode] = useState('')
    const [searchJobType, setSearchJobType] = useState('')

    // Set auth token when session is available
    useEffect(() => {
        if (session?.access_token && !apiClient.token) {
            apiClient.setToken(session.access_token)
        }
    }, [session])

    useEffect(() => {
        if (user) {
            loadData()
        }
    }, [user, activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

    const loadData = async () => {
        setLoading(true)
        try {
            // Load stats for dashboard
            if (activeTab === 'dashboard') {
                const statsResponse = await apiClient.get<JobStats>('/jobs/stats')
                if (statsResponse.data) {
                    setStats(statsResponse.data)
                }
            }

            // Load watchlist
            if (activeTab === 'watchlist' || activeTab === 'dashboard') {
                const watchlistResponse = await apiClient.get<JobSiteWatchlist[]>('/jobs/watchlist')
                if (watchlistResponse.data) {
                    setWatchlist(watchlistResponse.data)
                }
            }

            // Load suggested jobs
            if (activeTab === 'suggestions' || activeTab === 'dashboard') {
                const suggestionsResponse = await apiClient.get<SuggestedJob[]>('/jobs/suggestions?limit=20')
                if (suggestionsResponse.data) {
                    setSuggestedJobs(suggestionsResponse.data)
                }
            }
        } catch (error) {
            console.error('Failed to load data:', error)
        } finally {
            setLoading(false)
        }
    }

    const addWatchlistSite = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newSiteUrl) return

        try {
            const response = await apiClient.post<JobSiteWatchlist>('/jobs/watchlist', {
                site_url: newSiteUrl,
                site_name: newSiteName || undefined,
                filters: newSiteFilters,
                is_active: true
            })

            if (response.data) {
                setWatchlist(prev => [response.data!, ...prev])
                setNewSiteUrl('')
                setNewSiteName('')
                setNewSiteFilters({})
                setShowAddSiteForm(false)
                alert('Job site added to watchlist!')
            } else if (response.error) {
                alert(`Error: ${response.error}`)
            }
        } catch (error) {
            alert('Failed to add job site')
            console.error('Add site error:', error)
        }
    }

    const toggleSiteActive = async (siteId: string, isActive: boolean) => {
        try {
            const response = await apiClient.put<JobSiteWatchlist>(`/jobs/watchlist/${siteId}`, {
                is_active: !isActive
            })

            if (response.data) {
                setWatchlist(prev => prev.map(site =>
                    site.id === siteId ? { ...site, is_active: !isActive } : site
                ))
            }
        } catch (error) {
            alert('Failed to update site')
            console.error('Update site error:', error)
        }
    }

    const deleteSite = async (siteId: string) => {
        if (!confirm('Are you sure you want to delete this job site?')) return

        try {
            const response = await apiClient.delete(`/jobs/watchlist/${siteId}`)
            if (response.error) {
                alert(`Error: ${response.error}`)
            } else {
                setWatchlist(prev => prev.filter(site => site.id !== siteId))
            }
        } catch (error) {
            alert('Failed to delete site')
            console.error('Delete site error:', error)
        }
    }

    const markSuggestionViewed = async (suggestionId: string) => {
        try {
            await apiClient.put(`/jobs/suggestions/${suggestionId}`, {
                is_viewed: true
            })
            setSuggestedJobs(prev => prev.map(suggestion =>
                suggestion.id === suggestionId ? { ...suggestion, is_viewed: true } : suggestion
            ))
        } catch (error) {
            console.error('Failed to mark suggestion as viewed:', error)
        }
    }

    const dismissSuggestion = async (suggestionId: string) => {
        try {
            await apiClient.put(`/jobs/suggestions/${suggestionId}`, {
                is_dismissed: true
            })
            setSuggestedJobs(prev => prev.filter(suggestion => suggestion.id !== suggestionId))
        } catch (error) {
            console.error('Failed to dismiss suggestion:', error)
        }
    }

    const generateCV = async (jobId: string) => {
        try {
            const response = await apiClient.post(`/jobs/generate-cv/${jobId}`, {})
            if (response.data) {
                alert((response.data as any).message)
            } else if (response.error) {
                alert(`Error: ${response.error}`)
            }
        } catch (error) {
            alert('Failed to generate CV')
            console.error('Generate CV error:', error)
        }
    }

    const triggerCrawling = async (siteId: string) => {
        try {
            const response = await apiClient.post(`/jobs/crawl/${siteId}`, {})
            if (response.data) {
                alert((response.data as any).message)
            }
        } catch (error) {
            alert('Failed to trigger crawling')
            console.error('Crawl error:', error)
        }
    }

    const searchJobs = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)

        try {
            const params = new URLSearchParams()
            if (searchKeywords) params.append('keywords', searchKeywords)
            if (searchLocation) params.append('location', searchLocation)
            if (searchWorkMode) params.append('work_mode', searchWorkMode)
            if (searchJobType) params.append('job_type', searchJobType)
            params.append('limit', '50')

            const response = await apiClient.get<Job[]>(`/jobs/search?${params.toString()}`)
            if (response.data) {
                setSearchResults(response.data)
            }
        } catch (error) {
            console.error('Search failed:', error)
        } finally {
            setLoading(false)
        }
    }

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-lg">Loading...</div>
            </div>
        )
    }

    if (!user) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-lg">Please log in to access job features.</div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white shadow rounded-lg">
                    <div className="px-6 py-4 border-b border-gray-200">
                        <h1 className="text-2xl font-bold text-gray-900">Job Sites Watchlist & AI CV Generator</h1>
                        <p className="text-gray-600">Monitor job sites and get AI-powered job suggestions</p>
                    </div>

                    {/* Tab Navigation */}
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex space-x-8 px-6">
                            {[
                                { key: 'dashboard' as const, label: 'Dashboard' },
                                { key: 'watchlist' as const, label: 'Watchlist' },
                                { key: 'suggestions' as const, label: 'Suggested Jobs' },
                                { key: 'search' as const, label: 'Search Jobs' }
                            ].map((tab) => (
                                <button
                                    key={tab.key}
                                    onClick={() => setActiveTab(tab.key)}
                                    className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === tab.key
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                        }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </nav>
                    </div>

                    <div className="p-6">
                        {/* Dashboard Tab */}
                        {activeTab === 'dashboard' && (
                            <div className="space-y-6">
                                <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>

                                {stats && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        <div className="bg-blue-50 p-4 rounded-lg">
                                            <div className="text-2xl font-bold text-blue-600">{stats.total_watchlist_sites}</div>
                                            <div className="text-sm text-blue-800">Watchlist Sites</div>
                                        </div>
                                        <div className="bg-green-50 p-4 rounded-lg">
                                            <div className="text-2xl font-bold text-green-600">{stats.total_jobs_found}</div>
                                            <div className="text-sm text-green-800">Jobs Found</div>
                                        </div>
                                        <div className="bg-yellow-50 p-4 rounded-lg">
                                            <div className="text-2xl font-bold text-yellow-600">{stats.suggested_jobs}</div>
                                            <div className="text-sm text-yellow-800">Suggested Jobs</div>
                                        </div>
                                        <div className="bg-purple-50 p-4 rounded-lg">
                                            <div className="text-2xl font-bold text-purple-600">{stats.generated_cvs}</div>
                                            <div className="text-sm text-purple-800">Generated CVs</div>
                                        </div>
                                    </div>
                                )}

                                {/* Recent Suggestions Preview */}
                                <div>
                                    <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Job Suggestions</h3>
                                    <div className="space-y-3">
                                        {suggestedJobs.slice(0, 3).map((suggestion) => (
                                            <div key={suggestion.id} className="border rounded-lg p-4">
                                                <div className="flex justify-between items-start">
                                                    <div className="flex-1">
                                                        <h4 className="font-medium text-gray-900">{suggestion.job?.title}</h4>
                                                        <p className="text-sm text-gray-600">
                                                            {suggestion.job?.company} • {suggestion.job?.location}
                                                        </p>
                                                        <div className="mt-2">
                                                            <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                                                {Math.round(suggestion.match_score * 100)}% match
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={() => generateCV(suggestion.job_id)}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        Generate CV
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Watchlist Tab */}
                        {activeTab === 'watchlist' && (
                            <div className="space-y-6">
                                <div className="flex justify-between items-center">
                                    <h2 className="text-xl font-semibold text-gray-900">Job Sites Watchlist</h2>
                                    <button
                                        onClick={() => setShowAddSiteForm(true)}
                                        className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                                    >
                                        Add Job Site
                                    </button>
                                </div>

                                {/* Add Site Form */}
                                {showAddSiteForm && (
                                    <div className="border rounded-lg p-4 bg-gray-50">
                                        <h3 className="text-lg font-medium text-gray-900 mb-4">Add New Job Site</h3>
                                        <form onSubmit={addWatchlistSite} className="space-y-4">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700">Site URL *</label>
                                                    <input
                                                        type="url"
                                                        required
                                                        value={newSiteUrl}
                                                        onChange={(e) => setNewSiteUrl(e.target.value)}
                                                        placeholder="https://example.com/jobs"
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700">Site Name</label>
                                                    <input
                                                        type="text"
                                                        value={newSiteName}
                                                        onChange={(e) => setNewSiteName(e.target.value)}
                                                        placeholder="e.g., Indeed, LinkedIn Jobs"
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                    />
                                                </div>
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700">Location</label>
                                                    <input
                                                        type="text"
                                                        value={newSiteFilters.location || ''}
                                                        onChange={(e) => setNewSiteFilters(prev => ({ ...prev, location: e.target.value }))}
                                                        placeholder="e.g., Remote, New York, CA"
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700">Work Mode</label>
                                                    <select
                                                        value={newSiteFilters.work_mode || ''}
                                                        onChange={(e) => setNewSiteFilters(prev => ({ ...prev, work_mode: e.target.value as JobSiteFilters['work_mode'] }))}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                    >
                                                        <option value="">Any</option>
                                                        <option value="remote">Remote</option>
                                                        <option value="hybrid">Hybrid</option>
                                                        <option value="onsite">Onsite</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700">Job Type</label>
                                                    <select
                                                        value={newSiteFilters.job_type || ''}
                                                        onChange={(e) => setNewSiteFilters(prev => ({ ...prev, job_type: e.target.value as JobSiteFilters['job_type'] }))}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                    >
                                                        <option value="">Any</option>
                                                        <option value="full-time">Full-time</option>
                                                        <option value="part-time">Part-time</option>
                                                        <option value="contract">Contract</option>
                                                        <option value="internship">Internship</option>
                                                    </select>
                                                </div>
                                            </div>

                                            <div>
                                                <label className="block text-sm font-medium text-gray-700">Keywords (comma-separated)</label>
                                                <input
                                                    type="text"
                                                    value={newSiteFilters.keywords?.join(', ') || ''}
                                                    onChange={(e) => setNewSiteFilters(prev => ({
                                                        ...prev,
                                                        keywords: e.target.value.split(',').map(k => k.trim()).filter(k => k)
                                                    }))}
                                                    placeholder="e.g., React, Node.js, Python"
                                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                                />
                                            </div>

                                            <div className="flex space-x-4">
                                                <button
                                                    type="submit"
                                                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                                                >
                                                    Add Site
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setShowAddSiteForm(false)}
                                                    className="bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400"
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        </form>
                                    </div>
                                )}

                                {/* Watchlist Sites */}
                                <div className="space-y-4">
                                    {watchlist.map((site) => (
                                        <div key={site.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-900">
                                                        {site.site_name || new URL(site.site_url).hostname}
                                                    </h3>
                                                    <p className="text-sm text-gray-600">{site.site_url}</p>
                                                    <div className="mt-2 flex flex-wrap gap-2">
                                                        {site.filters.location && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                                                📍 {site.filters.location}
                                                            </span>
                                                        )}
                                                        {site.filters.work_mode && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                                                                🏢 {site.filters.work_mode}
                                                            </span>
                                                        )}
                                                        {site.filters.job_type && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                                                                💼 {site.filters.job_type}
                                                            </span>
                                                        )}
                                                        {site.filters.keywords && site.filters.keywords.length > 0 && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                                                                🔍 {site.filters.keywords.slice(0, 3).join(', ')}
                                                                {site.filters.keywords.length > 3 && '...'}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="mt-2">
                                                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${site.is_active
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-red-100 text-red-800'
                                                            }`}>
                                                            {site.is_active ? 'Active' : 'Inactive'}
                                                        </span>
                                                        {site.last_crawled_at && (
                                                            <span className="ml-2 text-xs text-gray-500">
                                                                Last crawled: {new Date(site.last_crawled_at).toLocaleDateString()}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex space-x-2">
                                                    <button
                                                        onClick={() => triggerCrawling(site.id)}
                                                        className="text-blue-600 hover:text-blue-500 text-sm"
                                                    >
                                                        Crawl Now
                                                    </button>
                                                    <button
                                                        onClick={() => toggleSiteActive(site.id, site.is_active)}
                                                        className="text-yellow-600 hover:text-yellow-500 text-sm"
                                                    >
                                                        {site.is_active ? 'Deactivate' : 'Activate'}
                                                    </button>
                                                    <button
                                                        onClick={() => deleteSite(site.id)}
                                                        className="text-red-600 hover:text-red-500 text-sm"
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}

                                    {watchlist.length === 0 && (
                                        <p className="text-gray-500 text-center py-8">No job sites in your watchlist yet</p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Suggestions Tab */}
                        {activeTab === 'suggestions' && (
                            <div className="space-y-6">
                                <h2 className="text-xl font-semibold text-gray-900">Suggested Jobs</h2>

                                <div className="space-y-4">
                                    {suggestedJobs.map((suggestion) => (
                                        <div key={suggestion.id} className={`border rounded-lg p-4 ${!suggestion.is_viewed ? 'bg-blue-50 border-blue-200' : ''
                                            }`}>
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-900">{suggestion.job?.title}</h3>
                                                    <p className="text-sm text-gray-600">
                                                        {suggestion.job?.company} • {suggestion.job?.location}
                                                    </p>
                                                    {suggestion.job?.description && (
                                                        <p className="text-sm text-gray-700 mt-2">
                                                            {suggestion.job.description.substring(0, 200)}...
                                                        </p>
                                                    )}
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                                            {Math.round(suggestion.match_score * 100)}% match
                                                        </span>
                                                        {suggestion.job?.work_mode && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                                                {suggestion.job.work_mode}
                                                            </span>
                                                        )}
                                                        {suggestion.job?.job_type && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                                                                {suggestion.job.job_type}
                                                            </span>
                                                        )}
                                                        {!suggestion.is_viewed && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                                                                New
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex flex-col space-y-2">
                                                    <button
                                                        onClick={() => generateCV(suggestion.job_id)}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        Generate CV
                                                    </button>
                                                    {suggestion.job?.job_url && (
                                                        <a
                                                            href={suggestion.job.job_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700 text-center"
                                                        >
                                                            View Job
                                                        </a>
                                                    )}
                                                    {!suggestion.is_viewed && (
                                                        <button
                                                            onClick={() => markSuggestionViewed(suggestion.id)}
                                                            className="text-blue-600 hover:text-blue-500 text-sm"
                                                        >
                                                            Mark Read
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => dismissSuggestion(suggestion.id)}
                                                        className="text-red-600 hover:text-red-500 text-sm"
                                                    >
                                                        Dismiss
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}

                                    {suggestedJobs.length === 0 && (
                                        <p className="text-gray-500 text-center py-8">No job suggestions yet</p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Search Tab */}
                        {activeTab === 'search' && (
                            <div className="space-y-6">
                                <h2 className="text-xl font-semibold text-gray-900">Search Jobs</h2>

                                {/* Search Form */}
                                <form onSubmit={searchJobs} className="bg-gray-50 p-4 rounded-lg">
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Keywords</label>
                                            <input
                                                type="text"
                                                value={searchKeywords}
                                                onChange={(e) => setSearchKeywords(e.target.value)}
                                                placeholder="e.g., React, Python, Manager"
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Location</label>
                                            <input
                                                type="text"
                                                value={searchLocation}
                                                onChange={(e) => setSearchLocation(e.target.value)}
                                                placeholder="e.g., Remote, New York"
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Work Mode</label>
                                            <select
                                                value={searchWorkMode}
                                                onChange={(e) => setSearchWorkMode(e.target.value)}
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                            >
                                                <option value="">Any</option>
                                                <option value="remote">Remote</option>
                                                <option value="hybrid">Hybrid</option>
                                                <option value="onsite">Onsite</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700">Job Type</label>
                                            <select
                                                value={searchJobType}
                                                onChange={(e) => setSearchJobType(e.target.value)}
                                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                            >
                                                <option value="">Any</option>
                                                <option value="full-time">Full-time</option>
                                                <option value="part-time">Part-time</option>
                                                <option value="contract">Contract</option>
                                                <option value="internship">Internship</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div className="mt-4">
                                        <button
                                            type="submit"
                                            disabled={loading}
                                            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {loading ? 'Searching...' : 'Search Jobs'}
                                        </button>
                                    </div>
                                </form>

                                {/* Search Results */}
                                <div className="space-y-4">
                                    {searchResults.map((job) => (
                                        <div key={job.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <h3 className="font-medium text-gray-900">{job.title}</h3>
                                                    <p className="text-sm text-gray-600">
                                                        {job.company} • {job.location}
                                                    </p>
                                                    {job.description && (
                                                        <p className="text-sm text-gray-700 mt-2">
                                                            {job.description.substring(0, 300)}...
                                                        </p>
                                                    )}
                                                    <div className="mt-3 flex flex-wrap gap-2">
                                                        {job.work_mode && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                                                                {job.work_mode}
                                                            </span>
                                                        )}
                                                        {job.job_type && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                                                                {job.job_type}
                                                            </span>
                                                        )}
                                                        {job.compensation && (
                                                            <span className="inline-flex px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                                                                {job.compensation}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex flex-col space-y-2">
                                                    <button
                                                        onClick={() => generateCV(job.id)}
                                                        className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    >
                                                        Generate CV
                                                    </button>
                                                    {job.job_url && (
                                                        <a
                                                            href={job.job_url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700 text-center"
                                                        >
                                                            View Job
                                                        </a>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}

                                    {searchResults.length === 0 && activeTab === 'search' && (
                                        <p className="text-gray-500 text-center py-8">No search results. Try adjusting your filters.</p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}