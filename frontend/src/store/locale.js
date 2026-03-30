import { ref } from 'vue'

const locale = ref(localStorage.getItem('mirofish-lang') || 'en')

export function useLocale() {
  return locale
}

export function setLocale(lang) {
  locale.value = lang
  localStorage.setItem('mirofish-lang', lang)
}
