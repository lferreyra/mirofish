import zh from './zh.json'
import en from './en.json'
import de from './de.json'

const locales = { zh, en, de }
let currentLang = 'zh'

export function setLanguage(lang) {
  if (locales[lang]) currentLang = lang
}

export function t(key) {
  return locales[currentLang]?.[key] || locales.zh?.[key] || key
}

export async function initLanguage() {
  try {
    const res = await fetch('/api/config/language')
    const data = await res.json()
    if (data.language) setLanguage(data.language)
  } catch (e) {
    // Default to Chinese
  }
}

export function getLanguage() { return currentLang }
