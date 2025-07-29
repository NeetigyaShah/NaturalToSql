import axios from 'axios';

// Configuration
const API_BASE = 'https://0f07e28b401c.ngrok-free.app/api'; // Update with your backend API base URL
const TIMEOUT = 15000; // 15 seconds

// Create axios instance with enhanced configuration
const api = axios.create({
  baseURL: API_BASE,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  }
});


api.interceptors.request.use(
  config => {
    console.log(`🚀 Making ${config.method.toUpperCase()} request to: ${config.url}`);
    return config;
  },
  error => {
    console.error('❌ Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for debugging and handling
api.interceptors.response.use(
  response => {
    console.log(`✅ Response from ${response.config.url}:`, response.status);
    return response;
  },
  error => {
    console.error('❌ Response error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      detail: error.response?.data?.detail
    });
    return Promise.reject(error);
  }
);

// Enhanced error handler
const handleApiError = (error, context) => {
  if (error.code === 'ECONNREFUSED' || error.code === 'ECONNABORTED') {
    throw new Error(`Cannot connect to server (${context}). Check if backend is running.`);
  }
  if (error.response?.status === 504 || error.response?.status === 522) {
    throw new Error(`Cloudflare timeout (${context}). Server might be overloaded.`);
  }
  throw new Error(error.response?.data?.detail || `Failed to ${context}`);
};

// API Methods
export const sqlApi = {
  generateSql: async (naturalQuery) => {
    try {
      const response = await api.post('/generate-sql', {
        natural_query: naturalQuery
      });
      return response.data;
    } catch (error) {
      handleApiError(error, 'generate SQL');
    }
  },

  executeSql: async (sql) => {
    try {
      const response = await api.post('/execute-sql', { sql });
      return response.data;
    } catch (error) {
      handleApiError(error, 'execute SQL');
    }
  },

  getSchema: async () => {
    try {
      const response = await api.get('/schema');
      return response.data;
    } catch (error) {
      handleApiError(error, 'load schema');
    }
  },

  reloadSchema: async () => {
    try {
      console.log('🔄 Reloading schema...');
      const response = await api.get('/schema/reload');
      console.log('✅ Schema reloaded successfully');
      return response.data;
    } catch (error) {
      console.error('❌ Schema reload failed');
      handleApiError(error, 'reload schema');
    }
  },

  executeCustomSql: async (sql) => {
    try {
      console.log('⚡ Executing custom SQL...');
      const response = await api.post('/execute-custom-sql', { sql });
      console.log('✅ Custom SQL executed successfully');
      return response.data;
    } catch (error) {
      console.error('❌ Custom SQL execution failed');
      handleApiError(error, 'execute custom SQL');
    }
  },

  // Health check method
  checkConnection: async () => {
    try {
      await api.get('/schema');
      console.log('✅ Backend connection successful');
      return true;
    } catch (error) {
      console.error('❌ Backend connection failed');
      return false;
    }
  }
};

// Auto-check connection on import
sqlApi.checkConnection().catch(console.error);

export default sqlApi;