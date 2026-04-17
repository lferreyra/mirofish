import service, { requestWithRetry } from './index'

export const preparePrivateSimulation = (data) =>
  requestWithRetry(() => service.post('/api/private-impact/prepare', data), 3, 2000)

export const startPrivateSimulation = (data) =>
  requestWithRetry(() => service.post('/api/private-impact/start', data), 3, 1000)

export const getPrivateStatus = (simId) =>
  service.get(`/api/private-impact/status/${simId}`)

export const stopPrivateSimulation = (simId) =>
  service.post(`/api/private-impact/stop/${simId}`)

export const getPrivateActions = (simId, params = {}) =>
  service.get(`/api/private-impact/actions/${simId}`, { params })

export const generatePrivateReport = (simId, data = {}) =>
  requestWithRetry(() => service.post(`/api/private-impact/report/${simId}`, data), 3, 1000)

export const cleanupPrivateSimulation = (simId) =>
  service.delete(`/api/private-impact/cleanup/${simId}`)

export const getPrivateReportStatus = (taskId) =>
  service.post('/api/report/generate/status', { task_id: taskId })
