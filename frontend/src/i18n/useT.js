import { computed } from 'vue'
import { useLocale } from '../store/locale'
import { messages } from './index'

export function useT() {
  const locale = useLocale()
  // Returns a function t(keyPath) that resolves nested keys like 'home.tag'
  const t = computed(() => {
    const lang = locale.value
    const dict = messages[lang] || messages.en
    return function (keyPath, ...args) {
      const parts = keyPath.split('.')
      let val = dict
      for (const p of parts) {
        val = val?.[p]
        if (val === undefined) break
      }
      if (val === undefined) {
        // Fallback to English
        let fallback = messages.en
        for (const p of parts) {
          fallback = fallback?.[p]
          if (fallback === undefined) break
        }
        val = fallback
      }
      if (typeof val === 'function') return val(...args)
      return val ?? keyPath
    }
  })
  return t
}
