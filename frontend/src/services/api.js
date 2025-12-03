import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URI;
const AUTH_BASE_URL = import.meta.env.VITE_AUTH_BACKEND_URI;

// Validate required environment variables
if (!API_BASE_URL || !AUTH_BASE_URL) {
    console.error('❌ Error: Missing required environment variables:');
    if (!API_BASE_URL) console.error('   - VITE_BACKEND_URI');
    if (!AUTH_BASE_URL) console.error('   - VITE_AUTH_BACKEND_URI');
    console.error('\nPlease check your .env file and ensure all required variables are set.');
    console.error('Refer to .env.example for the required configuration.');
    throw new Error('Missing required environment variables. Check console for details.');
}

console.log('✅ API configuration validated');
console.log('📡 Chatbot API:', API_BASE_URL);
console.log('🔐 Auth API:', AUTH_BASE_URL);

// Chatbot API instance (FastAPI) - proxied through Node.js backend
const api = axios.create({
    baseURL: AUTH_BASE_URL, // Use Node.js backend as proxy
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true
});

// Add auth token to chat requests via Node.js backend
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auth API instance (Node.js)
const authApi = axios.create({
    baseURL: AUTH_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true
});

// Add auth token to requests
authApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
export const apiService = {
    // Auth endpoints (Node.js backend on port 4000)
    signup: (userData) => authApi.post('/user/register', userData),
    login: (credentials) => authApi.post('/user/login', credentials),
    getProfile: (userId) => authApi.get(`/user/${userId}`),

    // Chat endpoints (proxied through Node.js backend to FastAPI)
    newChat: (video_id, query) => api.post('/chats/sessions', { video_id, query }),
    resumeChat: (session_id, video_id, query) => api.post(`/chats/sessions/${session_id}`, { video_id, query }),
    getChatSessions: () => api.get('/chats/sessions'),
    getSession: (session_id) => api.get(`/chats/sessions/${session_id}`),
    deleteSession: (session_id) => api.delete(`/chats/sessions/${session_id}`),
};