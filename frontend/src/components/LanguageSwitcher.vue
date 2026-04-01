<template>
  <div class="language-switcher">
    <button
      v-for="lang in languages"
      :key="lang.code"
      class="lang-btn"
      :class="{ active: currentLocale === lang.code }"
      @click="changeLanguage(lang.code)"
      :title="lang.name"
    >
      {{ lang.code.toUpperCase() }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

const currentLocale = computed(() => locale.value)

const languages = [
  { code: 'zh', name: '简体中文' },
  { code: 'en', name: 'English' }
]

const changeLanguage = (langCode) => {
  locale.value = langCode
  localStorage.setItem('mirofish-locale', langCode)
}

// Load saved language preference on mount
const savedLocale = localStorage.getItem('mirofish-locale')
if (savedLocale) {
  locale.value = savedLocale
}
</script>

<style scoped>
.language-switcher {
  display: flex;
  gap: 4px;
  background: #F5F5F5;
  padding: 4px;
  border-radius: 4px;
}

.lang-btn {
  border: none;
  background: transparent;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #666;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'JetBrains Mono', monospace;
}

.lang-btn:hover {
  background: #E0E0E0;
}

.lang-btn.active {
  background: #FFF;
  color: #000;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
</style>
