'use client'

import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api'

interface Upload {
  id: string
  filename: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  processed_at?: string
  error_message?: string
}

interface ParsedData {
  personal_info?: any
  profile?: any
  education?: any[]
  experience?: any[]
  skills?: any[]
  raw_text?: string
}

export default function UploadPage() {
  const { user, session, loading: authLoading } = useAuth()
  const [uploads, setUploads] = useState<Upload[]>([])
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [parsedData, setParsedData] = useState<ParsedData | null>(null)
  const [selectedUpload, setSelectedUpload] = useState<string | null>(null)

  // Set auth token when session is available
  useEffect(() => {
    if (session?.access_token && !apiClient.token) {
      apiClient.setToken(session.access_token)
    }
  }, [session])

  const loadUploads = async () => {
    try {
      const response = await apiClient.get('/uploads')
      if (response.data) {
        setUploads(response.data as Upload[])
      }
    } catch (error) {
      console.error('Failed to load uploads:', error)
    }
  }

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/pdf') {
      alert('Please select a PDF file')
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      alert('File size must be less than 50MB')
      return
    }
    setSelectedFile(file)
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }, [])

  const uploadFile = async () => {
    if (!selectedFile) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/uploads/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: formData,
      })

      if (response.ok) {
        const upload = await response.json()
        setUploads(prev => [upload, ...prev])
        setSelectedFile(null)
        alert('File uploaded successfully! Parsing in progress...')
      } else {
        const error = await response.json()
        alert(`Upload failed: ${error.detail}`)
      }
    } catch (error) {
      alert('Upload failed: Network error')
      console.error('Upload error:', error)
    } finally {
      setUploading(false)
    }
  }

  const viewParsedData = async (uploadId: string) => {
    try {
      const response = await apiClient.get(`/uploads/${uploadId}/parsed-data`)
      if (response.data) {
        setParsedData(response.data)
        setSelectedUpload(uploadId)
      } else {
        alert('Parsed data not available yet. Please wait for processing to complete.')
      }
    } catch (error) {
      alert('Failed to load parsed data')
      console.error('Parse data error:', error)
    }
  }

  const deleteUpload = async (uploadId: string) => {
    if (!confirm('Are you sure you want to delete this upload?')) return

    try {
      const response = await apiClient.delete(`/uploads/${uploadId}`)
      if (response.error) {
        alert(`Delete failed: ${response.error}`)
      } else {
        setUploads(prev => prev.filter(u => u.id !== uploadId))
        if (selectedUpload === uploadId) {
          setParsedData(null)
          setSelectedUpload(null)
        }
      }
    } catch (error) {
      alert('Delete failed')
      console.error('Delete error:', error)
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
        <div className="text-lg">Please log in to upload files.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h1 className="text-2xl font-bold text-gray-900">CV Upload & Parsing</h1>
            <p className="text-gray-600">Upload your CV to extract structured data automatically</p>
          </div>

          <div className="p-6">
            {/* Upload Section */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload New CV</h2>
              
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                {selectedFile ? (
                  <div className="space-y-4">
                    <div className="text-sm text-gray-600">
                      Selected: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                    </div>
                    <div className="space-x-4">
                      <button
                        onClick={uploadFile}
                        disabled={uploading}
                        className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        {uploading ? 'Uploading...' : 'Upload & Parse'}
                      </button>
                      <button
                        onClick={() => setSelectedFile(null)}
                        className="bg-gray-300 text-gray-700 px-6 py-2 rounded-md hover:bg-gray-400"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <div>
                      <p className="text-lg text-gray-600">Drop your CV here or</p>
                      <label className="cursor-pointer">
                        <span className="text-blue-600 hover:text-blue-500 font-medium">browse files</span>
                        <input
                          type="file"
                          className="hidden"
                          accept=".pdf"
                          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                        />
                      </label>
                    </div>
                    <p className="text-sm text-gray-500">PDF files only, max 50MB</p>
                  </div>
                )}
              </div>
            </div>

            {/* Uploads List */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Your Uploads</h2>
                  <button
                    onClick={loadUploads}
                    className="text-blue-600 hover:text-blue-500 text-sm"
                  >
                    Refresh
                  </button>
                </div>

                <div className="space-y-3">
                  {uploads.map((upload) => (
                    <div key={upload.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">{upload.filename}</h3>
                          <p className="text-sm text-gray-500">
                            {(upload.file_size / 1024 / 1024).toFixed(2)} MB • {new Date(upload.created_at).toLocaleDateString()}
                          </p>
                          <div className="mt-2">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              upload.status === 'completed' ? 'bg-green-100 text-green-800' :
                              upload.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                              upload.status === 'failed' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {upload.status}
                            </span>
                          </div>
                          {upload.error_message && (
                            <p className="text-sm text-red-600 mt-1">{upload.error_message}</p>
                          )}
                        </div>
                        <div className="flex space-x-2">
                          {upload.status === 'completed' && (
                            <button
                              onClick={() => viewParsedData(upload.id)}
                              className="text-blue-600 hover:text-blue-500 text-sm"
                            >
                              View Data
                            </button>
                          )}
                          <button
                            onClick={() => deleteUpload(upload.id)}
                            className="text-red-600 hover:text-red-500 text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {uploads.length === 0 && (
                    <p className="text-gray-500 text-center py-8">No uploads yet</p>
                  )}
                </div>
              </div>

              {/* Parsed Data Display */}
              <div>
                {parsedData && (
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Parsed Data</h2>
                    <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(parsedData, null, 2)}
                      </pre>
                    </div>
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          setParsedData(null)
                          setSelectedUpload(null)
                        }}
                        className="text-gray-600 hover:text-gray-500 text-sm"
                      >
                        Close
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}