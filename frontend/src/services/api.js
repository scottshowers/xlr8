import axios from 'axios'

const api = axios.create({
  baseURL: 'https://hcmpact-xlr8-production.up.railway.app/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export default api
