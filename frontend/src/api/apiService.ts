import axios from 'axios';
import {
  Company,
  CuratedHolding,
  Idea,
  IdeaDetail,
  IdentityCandidate,
  ListParams,
  Performance,
  QuarantineRecord,
  User,
} from '../types/api';

// Base API URL - Use environment variable with fallback
const API_URL = '/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Define custom error interface for better typing
interface ApiError extends Error {
  response?: {
    status: number;
    statusText?: string;
    data?: unknown;
  };
  request?: unknown;
}

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Create a new error object with the enhanced message
    const enhancedError = new Error() as ApiError;
    
    // Enhance error object with more details
    if (error.response) {
      enhancedError.message = `Server error: ${error.response.status} ${error.response.statusText || ''}`;
      enhancedError.response = error.response;
    } else if (error.request) {
      enhancedError.message = 'No response received from server. Please check your connection.';
      enhancedError.request = error.request;
    } else {
      enhancedError.message = error.message || 'An unknown error occurred';
    }
    
    return Promise.reject(enhancedError);
  }
);

// Ideas API
export const ideasApi = {
  getIdeas: async (params: ListParams = {}): Promise<Idea[]> => {
    const response = await apiClient.get('/ideas/', { params });
    return response.data;
  },

  getIdeaById: async (id: string): Promise<IdeaDetail> => {
    const response = await apiClient.get(`/ideas/${id}`);
    return response.data;
  },

  getIdeaPerformance: async (id: string): Promise<Performance> => {
    const response = await apiClient.get(`/ideas/${id}/performance`);
    return response.data;
  },

  getIdeaDescription: async (id: string): Promise<string> => {
    const response = await apiClient.get(`/ideas/${id}/description`);
    return response.data.description;
  },

  getIdeaCatalysts: async (id: string): Promise<string> => {
    const response = await apiClient.get(`/ideas/${id}/catalysts`);
    return response.data.catalysts;
  },
};

// Companies API
export const companiesApi = {
  getCompanies: async (params: ListParams = {}): Promise<Company[]> => {
    const response = await apiClient.get('/companies/', { params });
    return response.data;
  },
};

// Users API
export const usersApi = {
  getUsers: async (params: ListParams = {}): Promise<User[]> => {
    const response = await apiClient.get('/users/', { params });
    return response.data;
  },
};

// Holdings API
export const holdingsApi = {
  getHoldings: async (params: ListParams = {}): Promise<CuratedHolding[]> => {
    const response = await apiClient.get('/holdings/', { params });
    return response.data;
  },
};

const reviewHeaders = () => {
  const token = window.localStorage.getItem('reviewAdminToken');
  return token ? { Authorization: `Bearer ${token}` } : undefined;
};

export const reviewApi = {
  getIdentityQueue: async (): Promise<IdentityCandidate[]> => {
    const response = await apiClient.get('/review/identity', {
      headers: reviewHeaders(),
    });
    return response.data;
  },
  getQuarantineQueue: async (): Promise<QuarantineRecord[]> => {
    const response = await apiClient.get('/review/quarantine', {
      headers: reviewHeaders(),
    });
    return response.data;
  },
  reprocessQuarantine: async (id: string): Promise<QuarantineRecord> => {
    const response = await apiClient.post(`/review/quarantine/${id}/reprocess`, undefined, {
      headers: reviewHeaders(),
    });
    return response.data;
  },
};

// Health check API
export const healthApi = {
  check: async (): Promise<{ status: string }> => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};
