import axios from 'axios';
const API_BASE_URL = import.meta.env.VITE_BACKEND_URI;
console.log(API_BASE_URL);
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    }
});
// Add interceptors for auth tokens if needed
// api.interceptors.request.use((config) => {
//     const token = localStorage.getItem('token');
//     if (token) {
//         config.headers.Authorization = `Bearer ${token}`;
//     }
//     return config;
// });
export const apiService = {
    // Auth endpoints
    // signup: (userData) => api.post('/user/auth/signup', userData),
    // login: (credentials) => api.post('/api/auth/login', credentials),
    
    // Chat endpoints
    newChat : async (video_id,query)=> api.post('/chats/sessions',{video_id:video_id,query:query}),
};