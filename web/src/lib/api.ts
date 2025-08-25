/**
 * API client for backend services
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface ApiResponse<T> {
  data?: T
  error?: string
}

class ApiClient {
  private baseUrl: string
  public token: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  setToken(token: string | null) {
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        return {
          error: errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        }
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
      }
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async put<T>(endpoint: string, data: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()

// Profile API methods
export const profileApi = {
  // Personal Info
  getPersonalInfo: () => apiClient.get('/profiles/personal-info'),
  createPersonalInfo: (data: any) => apiClient.post('/profiles/personal-info', data),
  updatePersonalInfo: (data: any) => apiClient.put('/profiles/personal-info', data),

  // Profile
  getProfile: () => apiClient.get('/profiles/profile'),
  createProfile: (data: any) => apiClient.post('/profiles/profile', data),
  updateProfile: (data: any) => apiClient.put('/profiles/profile', data),

  // Education
  getEducation: () => apiClient.get('/profiles/education'),
  createEducation: (data: any) => apiClient.post('/profiles/education', data),
  updateEducation: (id: number, data: any) => apiClient.put(`/profiles/education/${id}`, data),
  deleteEducation: (id: number) => apiClient.delete(`/profiles/education/${id}`),

  // Experience
  getExperience: () => apiClient.get('/profiles/experience'),
  createExperience: (data: any) => apiClient.post('/profiles/experience', data),
  updateExperience: (id: number, data: any) => apiClient.put(`/profiles/experience/${id}`, data),
  deleteExperience: (id: number) => apiClient.delete(`/profiles/experience/${id}`),

  // Skills
  getSkills: () => apiClient.get('/profiles/skills'),
  createSkill: (data: any) => apiClient.post('/profiles/skills', data),
  updateSkill: (id: number, data: any) => apiClient.put(`/profiles/skills/${id}`, data),
  deleteSkill: (id: number) => apiClient.delete(`/profiles/skills/${id}`),

  // Certifications
  getCertifications: () => apiClient.get('/profiles/certifications'),
  createCertification: (data: any) => apiClient.post('/profiles/certifications', data),
  updateCertification: (id: number, data: any) => apiClient.put(`/profiles/certifications/${id}`, data),
  deleteCertification: (id: number) => apiClient.delete(`/profiles/certifications/${id}`),

  // Referees
  getReferees: () => apiClient.get('/profiles/referees'),
  createReferee: (data: any) => apiClient.post('/profiles/referees', data),
  updateReferee: (id: number, data: any) => apiClient.put(`/profiles/referees/${id}`, data),
  deleteReferee: (id: number) => apiClient.delete(`/profiles/referees/${id}`),

  // Complete Profile
  getCompleteProfile: () => apiClient.get('/profiles/complete'),
}