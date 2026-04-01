/**
 * Unit tests for Simulation API functions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock the service module
vi.mock('../../src/api/index', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    defaults: {
      timeout: 300000,
      headers: { 'Content-Type': 'application/json' },
      baseURL: 'http://localhost:5001'
    }
  },
  requestWithRetry: vi.fn((fn) => fn())
}))

describe('Simulation API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('createSimulation', () => {
    it('should call the correct endpoint', async () => {
      const { default: service } = await import('../../src/api/index')
      const mockData = { project_id: 'proj_123', enable_twitter: true }
      vi.mocked(service.post).mockResolvedValue({ success: true, simulation_id: 'sim_123' })

      const { createSimulation } = await import('../../src/api/simulation')
      await createSimulation(mockData)

      expect(vi.mocked(service.post)).toHaveBeenCalled()
    })
  })

  describe('Simulation API functions defined', () => {
    it('should export createSimulation function', async () => {
      const { createSimulation } = await import('../../src/api/simulation')
      expect(typeof createSimulation).toBe('function')
    })

    it('should export getSimulation function', async () => {
      const { getSimulation } = await import('../../src/api/simulation')
      expect(typeof getSimulation).toBe('function')
    })

    it('should export getSimulationProfiles function', async () => {
      const { getSimulationProfiles } = await import('../../src/api/simulation')
      expect(typeof getSimulationProfiles).toBe('function')
    })

    it('should export startSimulation function', async () => {
      const { startSimulation } = await import('../../src/api/simulation')
      expect(typeof startSimulation).toBe('function')
    })

    it('should export getRunStatus function', async () => {
      const { getRunStatus } = await import('../../src/api/simulation')
      expect(typeof getRunStatus).toBe('function')
    })

    it('should export getSimulationPosts function', async () => {
      const { getSimulationPosts } = await import('../../src/api/simulation')
      expect(typeof getSimulationPosts).toBe('function')
    })

    it('should export getSimulationTimeline function', async () => {
      const { getSimulationTimeline } = await import('../../src/api/simulation')
      expect(typeof getSimulationTimeline).toBe('function')
    })

    it('should export listSimulations function', async () => {
      const { listSimulations } = await import('../../src/api/simulation')
      expect(typeof listSimulations).toBe('function')
    })

    it('should export interviewAgents function', async () => {
      const { interviewAgents } = await import('../../src/api/simulation')
      expect(typeof interviewAgents).toBe('function')
    })

    it('should export stopSimulation function', async () => {
      const { stopSimulation } = await import('../../src/api/simulation')
      expect(typeof stopSimulation).toBe('function')
    })

    it('should export getSimulationHistory function', async () => {
      const { getSimulationHistory } = await import('../../src/api/simulation')
      expect(typeof getSimulationHistory).toBe('function')
    })
  })
})
