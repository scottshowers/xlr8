import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
