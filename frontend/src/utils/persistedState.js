import { ref, watch } from 'vue'

/**
 * Create a reactive ref that auto-syncs to localStorage.
 * @param {string} key - localStorage key
 * @param {*} defaultValue - default value if nothing stored
 * @returns {import('vue').Ref} reactive ref synced to localStorage
 */
export function usePersistedState(key, defaultValue) {
  const stored = localStorage.getItem(key)
  let initial = defaultValue
  if (stored !== null) {
    try {
      initial = JSON.parse(stored)
    } catch {
      initial = defaultValue
    }
  }

  const state = ref(initial)

  watch(state, (newVal) => {
    if (newVal === null || newVal === undefined) {
      localStorage.removeItem(key)
    } else {
      localStorage.setItem(key, JSON.stringify(newVal))
    }
  }, { deep: true })

  return state
}

/**
 * Save navigation context so page refresh can recover the user's position.
 */
export function saveNavigationContext(context) {
  localStorage.setItem('mirofish_nav_context', JSON.stringify({
    ...context,
    timestamp: Date.now()
  }))
}

/**
 * Load saved navigation context. Expires after 24 hours.
 */
export function loadNavigationContext() {
  try {
    const raw = localStorage.getItem('mirofish_nav_context')
    if (!raw) return null
    const ctx = JSON.parse(raw)
    if (Date.now() - ctx.timestamp > 24 * 60 * 60 * 1000) {
      localStorage.removeItem('mirofish_nav_context')
      return null
    }
    return ctx
  } catch {
    return null
  }
}

/**
 * Clear saved navigation context.
 */
export function clearNavigationContext() {
  localStorage.removeItem('mirofish_nav_context')
}
