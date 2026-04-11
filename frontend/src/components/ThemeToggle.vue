<template>
  <button
    class="theme-toggle"
    @click="toggle"
    :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <span class="toggle-icon">{{ isDark ? '☀' : '☾' }}</span>
  </button>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const isDark = ref(false)

const applyTheme = (dark) => {
  document.documentElement.classList.toggle('dark', dark)
}

const toggle = () => {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved) {
    isDark.value = saved === 'dark'
  } else {
    isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }
  applyTheme(isDark.value)
})
</script>

<style scoped>
.theme-toggle {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 4px 10px;
  font-size: 0.85rem;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  transition: border-color 0.2s;
  line-height: 1;
}

.theme-toggle:hover {
  border-color: #ff6b35;
}
</style>
