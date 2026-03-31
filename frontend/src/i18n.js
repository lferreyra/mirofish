import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import zh from './locales/zh.json'
import vi from './locales/vi.json'

const i18n = createI18n({
  legacy: false, // use Composition API
  locale: 'zh', // default locale
  fallbackLocale: 'en',
  messages: {
    en,
    zh,
    vi
  }
})

export default i18n
