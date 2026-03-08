import axios from 'axios';
import { supabase } from '@/lib/supabase';

// Create Axios Instance
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:5002/api', // Default to local Flask
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor: Add Supabase Token
api.interceptors.request.use(async (config) => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Response Interceptor: Handle 401 (Logout?)
api.interceptors.response.use((response) => {
    return response;
}, (error) => {
    if (error.response?.status === 401) {
        // Optional: Trigger global logout or redirect
        console.warn('Unauthorized access. Redirecting to login...');
    }
    return Promise.reject(error);
});

export default api;
