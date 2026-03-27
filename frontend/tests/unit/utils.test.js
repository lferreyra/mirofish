/**
 * Unit tests for utility functions
 */

import { describe, it, expect } from 'vitest'

describe('Common Utilities', () => {
  describe('String utilities', () => {
    it('should capitalize string', () => {
      const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1)
      expect(capitalize('hello')).toBe('Hello')
    })

    it('should handle empty string', () => {
      const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1)
      expect(capitalize('')).toBe('')
    })

    it('should handle single character', () => {
      const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1)
      expect(capitalize('a')).toBe('A')
    })
  })

  describe('Array utilities', () => {
    it('should filter array', () => {
      const arr = [1, 2, 3, 4, 5]
      const result = arr.filter(x => x > 2)
      expect(result).toEqual([3, 4, 5])
    })

    it('should map array', () => {
      const arr = [1, 2, 3]
      const result = arr.map(x => x * 2)
      expect(result).toEqual([2, 4, 6])
    })

    it('should find element in array', () => {
      const arr = [{ id: 1 }, { id: 2 }, { id: 3 }]
      const result = arr.find(item => item.id === 2)
      expect(result).toEqual({ id: 2 })
    })
  })

  describe('Object utilities', () => {
    it('should merge objects', () => {
      const obj1 = { a: 1, b: 2 }
      const obj2 = { b: 3, c: 4 }
      const result = { ...obj1, ...obj2 }
      expect(result).toEqual({ a: 1, b: 3, c: 4 })
    })

    it('should clone object', () => {
      const original = { a: 1, b: { c: 2 } }
      const cloned = JSON.parse(JSON.stringify(original))
      expect(cloned).toEqual(original)
      expect(cloned).not.toBe(original)
    })

    it('should check if object has property', () => {
      const obj = { a: 1, b: 2 }
      expect(Object.prototype.hasOwnProperty.call(obj, 'a')).toBe(true)
      expect(Object.prototype.hasOwnProperty.call(obj, 'c')).toBe(false)
    })
  })

  describe('Number utilities', () => {
    it('should format number with decimals', () => {
      const formatDecimals = (num, decimals) => Number(num.toFixed(decimals))
      expect(formatDecimals(3.14159, 2)).toBe(3.14)
      expect(formatDecimals(10, 2)).toBe(10)
    })

    it('should check if number is integer', () => {
      expect(Number.isInteger(5)).toBe(true)
      expect(Number.isInteger(5.5)).toBe(false)
    })

    it('should calculate percentage', () => {
      const percentage = (current, total) => (current / total) * 100
      expect(percentage(25, 100)).toBe(25)
      expect(percentage(50, 100)).toBe(50)
    })
  })

  describe('Date utilities', () => {
    it('should format date as ISO string', () => {
      const date = new Date('2024-03-26')
      const isoString = date.toISOString()
      expect(isoString).toContain('2024-03-26')
    })

    it('should get current timestamp', () => {
      const now = Date.now()
      expect(typeof now).toBe('number')
      expect(now).toBeGreaterThan(0)
    })

    it('should parse date string', () => {
      const dateString = '2024-03-26T10:30:00Z'
      const date = new Date(dateString)
      // toISOString() adds milliseconds, so check it contains the date
      expect(date.toISOString()).toContain('2024-03-26T10:30:00')
    })
  })
})
