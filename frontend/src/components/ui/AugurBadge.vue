<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, default: 'draft' } })
const map = {
  completed: { label: 'Concluído', color: '#00e5c3', bg: 'rgba(0,229,195,.14)' },
  running: { label: 'Em execução', color: '#7c6ff7', bg: 'rgba(124,111,247,.18)' },
  draft: { label: 'Rascunho', color: '#9898b0', bg: 'rgba(152,152,176,.15)' },
  failed: { label: 'Falhou', color: '#ff5a5a', bg: 'rgba(255,90,90,.16)' },
  preparing: { label: 'Preparando', color: '#f5a623', bg: 'rgba(245,166,35,.18)' }
}
const conf = computed(() => map[props.status] || map.draft)
</script>

<template>
  <span class="badge" :style="{ color: conf.color, background: conf.bg }">{{ conf.label }}</span>
</template>

<style scoped>
.badge { padding:4px 8px; border-radius:999px; font-size:12px; font-weight:600; }
</style>
