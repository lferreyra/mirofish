<script setup>
import { computed } from 'vue'
const props = defineProps({ agent: { type: Object, required: true }, selected: Boolean })
const emit = defineEmits(['select'])
const initials = computed(() => (props.agent.name || 'AG').split(' ').slice(0,2).map(s=>s[0]).join('').toUpperCase())
</script>
<template>
  <button class="agent" :class="{ selected }" @click="emit('select', agent)">
    <span class="avatar">{{ initials }}</span>
    <div>
      <strong>{{ agent.name || 'Agente' }}</strong>
      <small>{{ agent.role || 'Especialista' }}</small>
    </div>
  </button>
</template>
<style scoped>
.agent{width:100%;display:flex;gap:10px;align-items:center;padding:10px;border:1px solid var(--border);background:var(--bg-raised);border-radius:var(--r-sm);color:var(--text-primary);cursor:pointer;text-align:left;}
.agent.selected{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent-dim) inset;}
.avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:var(--bg-overlay);font-size:12px;font-weight:700;color:var(--accent);}
small{color:var(--text-muted);display:block}
</style>
