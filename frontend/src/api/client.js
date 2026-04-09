import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const uploadCV = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/upload/cv', form)
}

export const startApplication = (payload) => api.post('/apply', payload)

export const getApplicationStatus = (sessionId) => api.get(`/apply/${sessionId}`)

export const listApplications = () => api.get('/applications')

export const getApplication = (id) => api.get(`/applications/${id}`)

export default api
