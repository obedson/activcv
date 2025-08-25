'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';

interface JobStep {
    id: string;
    step_name: string;
    step_order: number;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
    progress_percentage: number;
    step_data: {
        description?: string;
    };
    error_message?: string;
    started_at?: string;
    completed_at?: string;
}

interface JobLog {
    id: string;
    log_level: 'debug' | 'info' | 'warning' | 'error';
    message: string;
    metadata: Record<string, any>;
    created_at: string;
}

interface JobWithSteps {
    id: string;
    job_type: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    priority: number;
    progress_percentage: number;
    current_step?: string;
    total_steps: number;
    error_message?: string;
    retry_count: number;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    steps: JobStep[];
    logs: JobLog[];
}

interface JobProgressUpdate {
    job_id: string;
    status: string;
    progress_percentage: number;
    current_step?: string;
    step_progress?: number;
    message?: string;
    error?: string;
    updated_at: string;
}

export default function JobProcessingPage() {
    const { user, loading: authLoading } = useAuth();
    const [jobs, setJobs] = useState<JobWithSteps[]>([]);
    const [selectedJob, setSelectedJob] = useState<JobWithSteps | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (user && !authLoading) {
            fetchJobs();
        }
    }, [user, authLoading]);

    const fetchJobs = async () => {
        try {
            const response = await apiClient.get<JobWithSteps[]>('/job-processing/');
            if (response.error) {
                setError('Failed to fetch jobs');
            } else {
                setJobs(response.data || []);
            }
        } catch (err) {
            setError('Failed to fetch jobs');
            console.error('Error fetching jobs:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchJobDetails = async (jobId: string) => {
        try {
            const response = await apiClient.get<JobWithSteps>(`/job-processing/${jobId}`);
            if (response.error) {
                console.error('Failed to fetch job details:', response.error);
            } else {
                setSelectedJob(response.data || null);
            }
        } catch (err) {
            console.error('Error fetching job details:', err);
        }
    };

    const retryJob = async (jobId: string) => {
        try {
            const response = await apiClient.post(`/job-processing/${jobId}/retry`, {
                job_id: jobId,
                reset_retry_count: true
            });
            
            if (response.error) {
                setError('Failed to retry job');
            } else {
                fetchJobs();
                if (selectedJob?.id === jobId) {
                    fetchJobDetails(jobId);
                }
            }
        } catch (err) {
            setError('Failed to retry job');
            console.error('Error retrying job:', err);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending': return 'text-yellow-600 bg-yellow-100';
            case 'processing': return 'text-blue-600 bg-blue-100';
            case 'completed': return 'text-green-600 bg-green-100';
            case 'failed': return 'text-red-600 bg-red-100';
            case 'cancelled': return 'text-gray-600 bg-gray-100';
            default: return 'text-gray-600 bg-gray-100';
        }
    };

    const getStepStatusIcon = (status: string) => {
        switch (status) {
            case 'completed': return '✅';
            case 'processing': return '🔄';
            case 'failed': return '❌';
            case 'skipped': return '⏭️';
            default: return '⏳';
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
                    <p className="text-gray-600">You need to be signed in to view job processing.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Job Processing</h1>
                    <p className="mt-2 text-gray-600">
                        Monitor real-time progress of your CV and cover letter generation jobs.
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

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Jobs List */}
                    <div className="lg:col-span-1">
                        <div className="bg-white shadow rounded-lg">
                            <div className="px-4 py-5 sm:p-6">
                                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                                    Recent Jobs
                                </h3>
                                
                                {jobs.length === 0 ? (
                                    <div className="text-center py-8">
                                        <p className="text-gray-500">No jobs found</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {jobs.map((job) => (
                                            <div
                                                key={job.id}
                                                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                                                    selectedJob?.id === job.id 
                                                        ? 'border-blue-500 bg-blue-50' 
                                                        : 'border-gray-200 hover:border-gray-300'
                                                }`}
                                                onClick={() => fetchJobDetails(job.id)}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div>
                                                        <p className="text-sm font-medium text-gray-900 capitalize">
                                                            {job.job_type.replace('_', ' ')}
                                                        </p>
                                                        <p className="text-xs text-gray-500">
                                                            {new Date(job.created_at).toLocaleString()}
                                                        </p>
                                                    </div>
                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                                                        {job.status}
                                                    </span>
                                                </div>
                                                
                                                <div className="mt-2">
                                                    <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                                                        <span>Progress</span>
                                                        <span>{job.progress_percentage}%</span>
                                                    </div>
                                                    <div className="w-full bg-gray-200 rounded-full h-2">
                                                        <div 
                                                            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                                            style={{ width: `${job.progress_percentage}%` }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Job Details */}
                    <div className="lg:col-span-2">
                        {selectedJob ? (
                            <div className="bg-white shadow rounded-lg">
                                <div className="px-4 py-5 sm:p-6">
                                    <div className="flex items-center justify-between mb-6">
                                        <div>
                                            <h3 className="text-lg leading-6 font-medium text-gray-900 capitalize">
                                                {selectedJob.job_type.replace('_', ' ')}
                                            </h3>
                                            <p className="mt-1 text-sm text-gray-500">
                                                Created {new Date(selectedJob.created_at).toLocaleString()}
                                            </p>
                                        </div>
                                        <div className="flex items-center space-x-3">
                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedJob.status)}`}>
                                                {selectedJob.status}
                                            </span>
                                            {selectedJob.status === 'failed' && (
                                                <button
                                                    onClick={() => retryJob(selectedJob.id)}
                                                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-blue-600 hover:bg-blue-700"
                                                >
                                                    Retry
                                                </button>
                                            )}
                                        </div>
                                    </div>

                                    <div className="mb-6">
                                        <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                                            <span>Overall Progress</span>
                                            <span>{selectedJob.progress_percentage}%</span>
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-3">
                                            <div 
                                                className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                                                style={{ width: `${selectedJob.progress_percentage}%` }}
                                            ></div>
                                        </div>
                                        {selectedJob.current_step && (
                                            <p className="mt-2 text-sm text-gray-600">
                                                Current: {selectedJob.current_step}
                                            </p>
                                        )}
                                    </div>

                                    <div className="mb-6">
                                        <h4 className="text-md font-medium text-gray-900 mb-4">Processing Steps</h4>
                                        <div className="space-y-3">
                                            {selectedJob.steps.map((step) => (
                                                <div key={step.id} className="flex items-center space-x-3">
                                                    <span className="text-lg">
                                                        {getStepStatusIcon(step.status)}
                                                    </span>
                                                    <div className="flex-1">
                                                        <div className="flex items-center justify-between">
                                                            <p className="text-sm font-medium text-gray-900">
                                                                {step.step_data.description || step.step_name}
                                                            </p>
                                                            <span className="text-xs text-gray-500">
                                                                {step.progress_percentage}%
                                                            </span>
                                                        </div>
                                                        {step.status === 'processing' && (
                                                            <div className="mt-1 w-full bg-gray-200 rounded-full h-1">
                                                                <div 
                                                                    className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                                                                    style={{ width: `${step.progress_percentage}%` }}
                                                                ></div>
                                                            </div>
                                                        )}
                                                        {step.error_message && (
                                                            <p className="mt-1 text-xs text-red-600">
                                                                Error: {step.error_message}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {selectedJob.error_message && (
                                        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
                                            <h4 className="text-sm font-medium text-red-800 mb-2">Error Details</h4>
                                            <p className="text-sm text-red-700">{selectedJob.error_message}</p>
                                        </div>
                                    )}

                                    {selectedJob.logs.length > 0 && (
                                        <div>
                                            <h4 className="text-md font-medium text-gray-900 mb-4">Processing Logs</h4>
                                            <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                                                <div className="space-y-2">
                                                    {selectedJob.logs.map((log) => (
                                                        <div key={log.id} className="flex items-start space-x-2 text-sm">
                                                            <span className="text-xs text-gray-500 font-mono">
                                                                {new Date(log.created_at).toLocaleTimeString()}
                                                            </span>
                                                            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                                                                log.log_level === 'error' ? 'bg-red-100 text-red-800' :
                                                                log.log_level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                                                                log.log_level === 'info' ? 'bg-blue-100 text-blue-800' :
                                                                'bg-gray-100 text-gray-800'
                                                            }`}>
                                                                {log.log_level.toUpperCase()}
                                                            </span>
                                                            <span className="text-gray-700 flex-1">{log.message}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="bg-white shadow rounded-lg">
                                <div className="px-4 py-5 sm:p-6 text-center">
                                    <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                        <span className="text-gray-400 text-xl">⚙️</span>
                                    </div>
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                                        Select a Job
                                    </h3>
                                    <p className="text-gray-500">
                                        Choose a job from the list to view detailed processing information.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}