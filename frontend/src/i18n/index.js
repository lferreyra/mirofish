import { createI18n } from 'vue-i18n'
import languages from '../../../locales/languages.json'

const localeFiles = import.meta.glob('../../../locales/!(languages).json', { eager: true })

const messages = {}
const availableLocales = []
const DEFAULT_LOCALE = 'en'
const LEGACY_DEFAULT_LOCALE = 'zh'
const LOCALE_STORAGE_KEY = 'locale'
const LOCALE_MIGRATION_KEY = 'locale_default_migrated_v1'

for (const path in localeFiles) {
  const key = path.match(/\/([^/]+)\.json$/)[1]
  if (languages[key]) {
    messages[key] = localeFiles[path].default
    availableLocales.push({ key, label: languages[key].label })
  }
}

const normalizeLocale = (value) => {
  if (!value || !languages[value]) {
    return null
  }
  return value
}

const resolveInitialLocale = () => {
  const savedLocale = normalizeLocale(localStorage.getItem(LOCALE_STORAGE_KEY))
  const hasMigratedLegacyDefault = localStorage.getItem(LOCALE_MIGRATION_KEY) === '1'

  if (savedLocale === LEGACY_DEFAULT_LOCALE && !hasMigratedLegacyDefault) {
    localStorage.setItem(LOCALE_STORAGE_KEY, DEFAULT_LOCALE)
    localStorage.setItem(LOCALE_MIGRATION_KEY, '1')
    return DEFAULT_LOCALE
  }

  if (savedLocale) {
    if (!hasMigratedLegacyDefault) {
      localStorage.setItem(LOCALE_MIGRATION_KEY, '1')
    }
    return savedLocale
  }

  localStorage.setItem(LOCALE_STORAGE_KEY, DEFAULT_LOCALE)
  localStorage.setItem(LOCALE_MIGRATION_KEY, '1')
  return DEFAULT_LOCALE
}

const savedLocale = resolveInitialLocale()

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: DEFAULT_LOCALE,
  messages
})

export { availableLocales }
export default i18n
