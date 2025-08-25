'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';

interface Document {
    id: string;
    document_type: string;
    title: string;
    description?: string;
    file_name: string;
    file_size: number;
    template_used?: string;
    download_count: number;
    is_shared: boolean;
    share_count: number;
    folder_name?: string;
    folder_color?: string;
    job_title?: string;
    job_company?: string;
    created_at: string;
    updated_at: string;
}

interface Folder {
    id: string;
    name: string;
    description?: string;
    color: string;
    icon: string;
    is_system_folder: boolean;
}

interface StorageStats {
    total_documents: number;
    total_size_bytes: number;
    storage_used_mb: number;
    documents_by_type: Record<string, number>;
    storage_limit_mb: number;
    storage_used_percentage: number;
}

export default function DocumentsPage() {
    const { user, loading: authLoading } = useAuth();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [folders, setFolders] = useState<Folder[]>([]);
    const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
    const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
    const [selectedDocumentType, setSelectedDocumentType] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

    useEffect(() => {
        if (user && !authLoading) {
            fetchDocuments();
            fetchFolders();
            fetchStorageStats();
        }
    }, [user, authLoading, selectedFolder, selectedDocumentType, searchQuery]);

    const fetchDocuments = async () => {
        try {
            const params = new URLSearchParams();
            if (selectedFolder) params.append('folder_id', selectedFolder);
            if (selectedDocumentType !== 'all') params.append('document_type', selectedDocumentType);
            if (searchQuery) params.append('search_query', searchQuery);

            const response = await apiClient.get<{
                success: boolean;
                documents: Document[];
                total_count: number;
            }>(`/document-vault/?${params}`);
            
            if (response.error) {
                setError('Failed to fetch documents');
            } else {
                setDocuments(response.data?.documents || []);
            }
        } catch (err) {
            setError('Failed to fetch documents');
            console.error('Error fetching documents:', err);
        }
    };

    const fetchFolders = async () => {
        try {
            const response = await apiClient.get<{
                success: boolean;
                folders: Folder[];
            }>('/document-vault/folders/');
            
            if (response.error) {
                console.error('Failed to fetch folders:', response.error);
            } else {
                setFolders(response.data?.folders || []);
            }
        } catch (err) {
            console.error('Error fetching folders:', err);
        }
    };

    const fetchStorageStats = async () => {
        try {
            const response = await apiClient.get<{
                success: boolean;
                stats: StorageStats;
            }>('/document-vault/stats/storage');
            
            if (response.error) {
                console.error('Failed to fetch storage stats:', response.error);
            } else {
                setStorageStats(response.data?.stats || null);
            }
        } catch (err) {
            console.error('Error fetching storage stats:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteDocument = async (documentId: string) => {
        if (!confirm('Are you sure you want to delete this document?')) {
            return;
        }

        try {
            const response = await apiClient.delete<{
                success: boolean;
                message?: string;
            }>(`/document-vault/${documentId}`);
            
            if (response.error) {
                setError('Failed to delete document');
            } else if (response.data?.success) {
                setDocuments(prev => prev.filter(doc => doc.id !== documentId));
                fetchStorageStats(); // Refresh storage stats
            } else {
                setError('Failed to delete document');
            }
        } catch (err) {
            setError('Failed to delete document');
            console.error('Error deleting document:', err);
        }
    };

    const handleShareDocument = async (documentId: string) => {
        try {
            const response = await apiClient.post<{
                success: boolean;
                share_url?: string;
                share_token?: string;
                share_info?: any;
            }>(`/document-vault/${documentId}/share`, {
                permissions: ['view', 'download'],
                expires_in_days: 30
            });
            
            if (response.error) {
                setError('Failed to create share link');
            } else if (response.data?.success && response.data.share_url) {
                navigator.clipboard.writeText(response.data.share_url);
                alert('Share link copied to clipboard!');
            } else {
                setError('Failed to get share link');
            }
        } catch (err) {
            setError('Failed to create share link');
            console.error('Error sharing document:', err);
        }
    };

    const getDocumentIcon = (documentType: string) => {
        switch (documentType) {
            case 'cv': return '📄';
            case 'cover_letter': return '📝';
            case 'certificate': return '🏆';
            case 'portfolio': return '💼';
            default: return '📁';
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getDocumentTypeColor = (type: string) => {
        switch (type) {
            case 'cv': return 'bg-blue-100 text-blue-800';
            case 'cover_letter': return 'bg-green-100 text-green-800';
            case 'certificate': return 'bg-yellow-100 text-yellow-800';
            case 'portfolio': return 'bg-purple-100 text-purple-800';
            default: return 'bg-gray-100 text-gray-800';
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
                    <p className="text-gray-600">You need to be signed in to view your documents.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Document Vault</h1>
                    <p className="mt-2 text-gray-600">
                        Manage your generated CVs, cover letters, and other documents.
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

                {/* Storage Stats */}
                {storageStats && (
                    <div className="mb-8 bg-white rounded-lg shadow p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Storage Usage</h3>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">{storageStats.total_documents}</div>
                                <div className="text-sm text-gray-500">Total Documents</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">{storageStats.storage_used_mb.toFixed(1)} MB</div>
                                <div className="text-sm text-gray-500">Storage Used</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-purple-600">{storageStats.storage_limit_mb} MB</div>
                                <div className="text-sm text-gray-500">Storage Limit</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-orange-600">{storageStats.storage_used_percentage.toFixed(1)}%</div>
                                <div className="text-sm text-gray-500">Usage</div>
                            </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(storageStats.storage_used_percentage, 100)}%` }}
                            ></div>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                    {/* Sidebar */}
                    <div className="lg:col-span-1">
                        <div className="bg-white shadow rounded-lg p-6">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">Folders</h3>
                            
                            <div className="space-y-2">
                                <button
                                    onClick={() => setSelectedFolder(null)}
                                    className={`w-full text-left px-3 py-2 rounded-md text-sm ${
                                        selectedFolder === null 
                                            ? 'bg-blue-100 text-blue-700' 
                                            : 'text-gray-700 hover:bg-gray-100'
                                    }`}
                                >
                                    📁 All Documents
                                </button>
                                
                                {folders.map((folder) => (
                                    <button
                                        key={folder.id}
                                        onClick={() => setSelectedFolder(folder.id)}
                                        className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center ${
                                            selectedFolder === folder.id 
                                                ? 'bg-blue-100 text-blue-700' 
                                                : 'text-gray-700 hover:bg-gray-100'
                                        }`}
                                    >
                                        <span 
                                            className="w-3 h-3 rounded-full mr-2"
                                            style={{ backgroundColor: folder.color }}
                                        ></span>
                                        {folder.name}
                                    </button>
                                ))}
                            </div>

                            <h3 className="text-lg font-medium text-gray-900 mt-6 mb-4">Document Types</h3>
                            <div className="space-y-2">
                                {['all', 'cv', 'cover_letter', 'certificate', 'portfolio'].map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => setSelectedDocumentType(type)}
                                        className={`w-full text-left px-3 py-2 rounded-md text-sm capitalize ${
                                            selectedDocumentType === type 
                                                ? 'bg-blue-100 text-blue-700' 
                                                : 'text-gray-700 hover:bg-gray-100'
                                        }`}
                                    >
                                        {getDocumentIcon(type)} {type === 'all' ? 'All Types' : type.replace('_', ' ')}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="lg:col-span-3">
                        {/* Search and Controls */}
                        <div className="bg-white shadow rounded-lg p-6 mb-6">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                                <div className="flex-1">
                                    <input
                                        type="text"
                                        placeholder="Search documents..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setViewMode('grid')}
                                        className={`p-2 rounded-md ${
                                            viewMode === 'grid' 
                                                ? 'bg-blue-100 text-blue-700' 
                                                : 'text-gray-400 hover:text-gray-600'
                                        }`}
                                    >
                                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                            <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                                        </svg>
                                    </button>
                                    <button
                                        onClick={() => setViewMode('list')}
                                        className={`p-2 rounded-md ${
                                            viewMode === 'list' 
                                                ? 'bg-blue-100 text-blue-700' 
                                                : 'text-gray-400 hover:text-gray-600'
                                        }`}
                                    >
                                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Documents */}
                        <div className="bg-white shadow rounded-lg">
                            {documents.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-4">
                                        <span className="text-gray-400 text-xl">📄</span>
                                    </div>
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                                        No documents found
                                    </h3>
                                    <p className="text-gray-500 mb-6">
                                        {selectedFolder || selectedDocumentType !== 'all' || searchQuery
                                            ? 'Try adjusting your filters or search query.'
                                            : 'Generate your first CV or cover letter to get started.'}
                                    </p>
                                    {!selectedFolder && selectedDocumentType === 'all' && !searchQuery && (
                                        <a
                                            href="/jobs"
                                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                                        >
                                            Browse Jobs
                                        </a>
                                    )}
                                </div>
                            ) : viewMode === 'grid' ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                                    {documents.map((document) => (
                                        <div key={document.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                            <div className="flex items-start justify-between mb-3">
                                                <div className="flex items-center">
                                                    <span className="text-2xl mr-2">
                                                        {getDocumentIcon(document.document_type)}
                                                    </span>
                                                    <div>
                                                        <h4 className="text-sm font-medium text-gray-900 truncate">
                                                            {document.title}
                                                        </h4>
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getDocumentTypeColor(document.document_type)}`}>
                                                            {document.document_type.replace('_', ' ')}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <div className="text-xs text-gray-500 mb-3">
                                                <p>{formatFileSize(document.file_size)}</p>
                                                <p>{new Date(document.created_at).toLocaleDateString()}</p>
                                                {document.job_title && (
                                                    <p className="truncate">For: {document.job_title}</p>
                                                )}
                                            </div>

                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center space-x-2 text-xs text-gray-500">
                                                    <span>↓ {document.download_count}</span>
                                                    {document.is_shared && <span>🔗 Shared</span>}
                                                </div>
                                                <div className="flex items-center space-x-1">
                                                    <button
                                                        onClick={() => window.open(`/api/v1/document-vault/${document.id}/download`, '_blank')}
                                                        className="p-1 text-gray-400 hover:text-blue-600"
                                                        title="Download"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleShareDocument(document.id)}
                                                        className="p-1 text-gray-400 hover:text-green-600"
                                                        title="Share"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteDocument(document.id)}
                                                        className="p-1 text-gray-400 hover:text-red-600"
                                                        title="Delete"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="divide-y divide-gray-200">
                                    {documents.map((document) => (
                                        <div key={document.id} className="p-6 hover:bg-gray-50">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center space-x-4">
                                                    <span className="text-2xl">
                                                        {getDocumentIcon(document.document_type)}
                                                    </span>
                                                    <div>
                                                        <h4 className="text-sm font-medium text-gray-900">
                                                            {document.title}
                                                        </h4>
                                                        <div className="flex items-center space-x-2 mt-1">
                                                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getDocumentTypeColor(document.document_type)}`}>
                                                                {document.document_type.replace('_', ' ')}
                                                            </span>
                                                            <span className="text-xs text-gray-500">
                                                                {formatFileSize(document.file_size)}
                                                            </span>
                                                            <span className="text-xs text-gray-500">
                                                                {new Date(document.created_at).toLocaleDateString()}
                                                            </span>
                                                        </div>
                                                        {document.job_title && (
                                                            <p className="text-xs text-gray-500 mt-1">
                                                                For: {document.job_title} at {document.job_company}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <div className="flex items-center space-x-4 text-xs text-gray-500 mr-4">
                                                        <span>↓ {document.download_count}</span>
                                                        {document.is_shared && <span>🔗 {document.share_count} shares</span>}
                                                    </div>
                                                    <button
                                                        onClick={() => window.open(`/api/v1/document-vault/${document.id}/download`, '_blank')}
                                                        className="p-2 text-gray-400 hover:text-blue-600"
                                                        title="Download"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleShareDocument(document.id)}
                                                        className="p-2 text-gray-400 hover:text-green-600"
                                                        title="Share"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteDocument(document.id)}
                                                        className="p-2 text-gray-400 hover:text-red-600"
                                                        title="Delete"
                                                    >
                                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}