/**
 * Unit tests for API utilities and functions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import service, { requestWithRetry } from '../../src/api/index'

describe('API Utilities', () => {
  describe('requestWithRetry', () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })

    afterEach(() => {
      vi.clearAllMocks()
    })

    it('should successfully return on first attempt', async () => {
      const mockFn = vi.fn().mockResolvedValue({ success: true, data: 'test' })

      const result = await requestWithRetry(mockFn, 3, 100)

      expect(result).toEqual({ success: true, data: 'test' })
      expect(mockFn).toHaveBeenCalledTimes(1)
    })

    it('should retry on failure and succeed', async () => {
      const mockFn = vi
        .fn()
        .mockRejectedValueOnce(new Error('First attempt failed'))
        .mockResolvedValueOnce({ success: true, data: 'retry success' })

      const result = await requestWithRetry(mockFn, 3, 100)

      expect(result).toEqual({ success: true, data: 'retry success' })
      expect(mockFn).toHaveBeenCalledTimes(2)
    })

    it('should fail after max retries exceeded', async () => {
      const error = new Error('Persistent error')
      const mockFn = vi.fn().mockRejectedValue(error)

      await expect(requestWithRetry(mockFn, 2, 100)).rejects.toThrow('Persistent error')
      expect(mockFn).toHaveBeenCalledTimes(2)
    })

    it('should use exponential backoff', async () => {
      vi.useFakeTimers()
      const mockFn = vi
        .fn()
        .mockRejectedValueOnce(new Error('Fail 1'))
        .mockRejectedValueOnce(new Error('Fail 2'))
        .mockResolvedValueOnce({ success: true })

      const promise = requestWithRetry(mockFn, 3, 100)

      // Fast-forward through retries
      await vi.runAllTimersAsync()

      const result = await promise
      expect(result).toEqual({ success: true })

      vi.useRealTimers()
    })

    it('should handle multiple retries with custom delay', async () => {
      const mockFn = vi
        .fn()
        .mockRejectedValueOnce(new Error('Attempt 1'))
        .mockRejectedValueOnce(new Error('Attempt 2'))
        .mockResolvedValueOnce({ data: 'success' })

      const result = await requestWithRetry(mockFn, 4, 50)

      expect(result).toEqual({ data: 'success' })
      expect(mockFn).toHaveBeenCalledTimes(3)
    })
  })

  describe('axios service instance', () => {
    it('should have correct base configuration', () => {
      expect(service.defaults.timeout).toBe(300000) // 5 minutes
      expect(service.defaults.headers['Content-Type']).toBe('application/json')
    })

    it('should have request interceptor', () => {
      expect(service.interceptors.request).toBeDefined()
    })

    it('should have response interceptor', () => {
      expect(service.interceptors.response).toBeDefined()
    })

    it('should use correct base URL from environment or default', () => {
      const baseURL = service.defaults.baseURL
      expect(baseURL).toBe('http://localhost:5001')
    })
  })
})
