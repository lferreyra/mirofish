<template>
  <div class="lang-switcher">
    <button
      :class="['lang-option', { active: locale === 'en' }]"
      @click="setLocale('en')"
    >
      EN
    </button>
    <span class="lang-divider">|</span>
    <button
      :class="['lang-option', { active: locale === 'zh' }]"
      @click="setLocale('zh')"
    >
      中文
    </button>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

// Restore persisted locale on mount
const saved = localStorage.getItem('mirofish-locale')
if (saved && (saved === 'en' || saved === 'zh')) {
  locale.value = saved
  document.documentElement.lang = saved
}

function setLocale(lang) {
  locale.value = lang
  localStorage.setItem('mirofish-locale', lang)
  document.documentElement.lang = lang
}
</script>

<style scoped>
.lang-switcher {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  user-select: none;
}

.lang-option {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: inherit;
  opacity: 0.5;
  transition: opacity 0.2s, background-color 0.2s;
}

.lang-option:hover {
  opacity: 0.8;
}

.lang-option.active {
  opacity: 1;
  background-color: rgba(128, 128, 128, 0.2);
}

.lang-divider {
  opacity: 0.3;
  font-size: 12px;
}
</style>
