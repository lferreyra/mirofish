import { computed, ref } from 'vue'
import service from '../api'

export function useSimulation(simulationId) {
  const simulation = ref(null)
  const runStatus = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  const id = computed(() => (typeof simulationId === 'object' ? simulationId.value : simulationId))

  async function fetchSimulation() {
    if (!id.value) return null
    isLoading.value = true
    error.value = null
    try {
      const response = await service.get(`/api/simulation/${id.value}`)
      simulation.value = response.data || response
      return simulation.value
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchRunStatus() {
    if (!id.value) return null
    try {
      const response = await service.get(`/api/simulation/${id.value}/run-status`)
      runStatus.value = response.data || response
      return runStatus.value
    } catch (err) {
      error.value = err
      throw err
    }
  }

  async function startSimulation(params) {
    isLoading.value = true
    error.value = null
    try {
      return await service.post('/api/simulation/start', params)
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function stopSimulation() {
    if (!id.value) return null
    try {
      return await service.post('/api/simulation/stop', { simulation_id: id.value })
    } catch (err) {
      error.value = err
      throw err
    }
  }

  return { simulation, runStatus, isLoading, error, fetchSimulation, fetchRunStatus, startSimulation, stopSimulation }
}
