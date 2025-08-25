'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';

interface CoverLetter {
    id: string;
    template_used: string;
    pdf_url?: string;
    email_sent: boolean;
    created_at: string;
    job?: {
        title: string;
        company: string;
        location: string;
    };
}

interface CoverLetterStats {
    total_cover_letters: number;
    cover_letters_this_month: number;
    most_used_template?: string;
    emails_sent: number;
    templates_used: Record<string, number>;
}

export default function CoverLettersPage() {
    const { user, loading: authLoading } = useAuth();
    const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
    const [stats, setStats] = useState<CoverLetterStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (user && !authLoading) {
            fetchCoverLetters();
            fetchStats();
        }
    }, [user, authLoading]);

    const fetchCoverLetters = async () => {
        try {
            const response = await apiClient.get<CoverLetter[]>('/cover-letters/');
            if (response.error) {
                setError('Failed to fetch cover letters');
                console.error('Error fetching cover letters:', response.error);
            } else {
                setCoverLetters(response.data ?? []);
            }
        } catch (err) {
            setError('Failed to fetch cover letters');
            console.error('Error fetching cover letters:', err);
        }
    };

    const fetchStats = async () => {
        try {
            const response = await apiClient.get<CoverLetterStats>('/cover-letters/stats');
            if (response.error) {
                console.error('Error fetching stats:', response.error);
            } else {
                setStats(response.data ?? null);
            }
        } catch (err) {
            console.error('Error fetching stats:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this cover letter?')) {
            return;
        }

        try {
            const response = await apiClient.delete(`/cover-letters/${id}`);
            if (response.error) {
                setError('Failed to delete cover letter');
                console.error('Error deleting cover letter:', response.error);
            } else {
                setCoverLetters(prev => prev.filter(cl => cl.id !== id));
            }
        } catch (err) {
            setError('Failed to delete cover letter');
            console.error('Error deleting cover letter:', err);
        }
    };

    if (authLoading || loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 mb-4">Please sign in</h1>
                    <p className="text-gray-600">You need to be signed in to view your cover letters.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Cover Letters</h1>
                    <p className="mt-2 text-gray-600">
                        Manage your AI-generated cover letters and track your applications.
                    </p>
                </div>

                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
                        <div className="flex">
                            <div className="ml-3">
                                <h3 className="text-sm font-medium text-red-800">Error</h3>
                                <div className="mt-2 text-sm text-red-700">{error}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Stats Cards */}
                {stats && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                                            <span className="text-white text-sm font-medium">📄</span>
                                        </div>
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Total Cover Letters
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {stats.total_cover_letters}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                                            <span className="text-white text-sm font-medium">📅</span>
                                        </div>
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                This Month
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {stats.cover_letters_this_month}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                                            <span className="text-white text-sm font-medium">📧</span>
                                        </div>
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Emails Sent
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {stats.emails_sent}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="bg-white overflow-hidden shadow rounded-lg">
                            <div className="p-5">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0">
                                        <div className="w-8 h-8 bg-orange-500 rounded-md flex items-center justify-center">
                                            <span className="text-white text-sm font-medium">🎨</span>
                                        </div>
                                    </div>
                                    <div className="ml-5 w-0 flex-1">
                                        <dl>
                                            <dt className="text-sm font-medium text-gray-500 truncate">
                                                Favorite Template
                                            </dt>
                                            <dd className="text-lg font-medium text-gray-900">
                                                {stats.most_used_template || 'N/A'}
                                            </dd>
                                        </dl>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Cover Letters List */}
                <div className="bg-white shadow overflow-hidden sm:rounded-md">
                    <div className="px-4 py-5 sm:px-6">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">
                            Your Cover Letters
                        </h3>
                        <p className="mt-1 max-w-2xl text-sm text-gray-500">
                            Generated cover letters for your job applications.
                        </p>
                    </div>

                    {coverLetters.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                <span className="text-gray-400 text-xl">📄</span>
                            </div>
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                                No cover letters yet
                            </h3>
                            <p className="text-gray-500 mb-6">
                                Generate your first cover letter from a job posting.
                            </p>
                            <a
                                href="/jobs"
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                            >
                                Browse Jobs
                            </a>
                        </div>
                    ) : (
                        <ul className="divide-y divide-gray-200">
                            {coverLetters.map((coverLetter) => (
                                <li key={coverLetter.id}>
                                    <div className="px-4 py-4 sm:px-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center">
                                                <div className="flex-shrink-0">
                                                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                                        <span className="text-blue-600 font-medium text-sm">📄</span>
                                                    </div>
                                                </div>
                                                <div className="ml-4">
                                                    <div className="flex items-center">
                                                        <p className="text-sm font-medium text-gray-900">
                                                            {coverLetter.job?.title || 'Cover Letter'}
                                                        </p>
                                                        {coverLetter.email_sent && (
                                                            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                                Sent
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="mt-1 flex items-center text-sm text-gray-500">
                                                        <span>{coverLetter.job?.company}</span>
                                                        {coverLetter.job?.location && (
                                                            <>
                                                                <span className="mx-2">•</span>
                                                                <span>{coverLetter.job.location}</span>
                                                            </>
                                                        )}
                                                        <span className="mx-2">•</span>
                                                        <span className="capitalize">{coverLetter.template_used.replace('_', ' ')}</span>
                                                    </div>
                                                    <p className="mt-1 text-xs text-gray-400">
                                                        Created {new Date(coverLetter.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                {coverLetter.pdf_url && (
                                                    <a
                                                        href={coverLetter.pdf_url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
                                                    >
                                                        Download
                                                    </a>
                                                )}
                                                <button
                                                    onClick={() => handleDelete(coverLetter.id)}
                                                    className="inline-flex items-center px-3 py-1.5 border border-red-300 shadow-sm text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}