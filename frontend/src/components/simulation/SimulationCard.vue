<script setup>
import AugurBadge from '../ui/AugurBadge.vue'
import AugurProgress from '../ui/AugurProgress.vue'
defineProps({ simulation: { type: Object, required: true } })
defineEmits(['click'])
</script>
<template>
  <article class="card" @click="$emit('click', simulation)">
    <div class="head">
      <div>
        <strong>{{ simulation.name || simulation.project_name || 'Simulação sem nome' }}</strong>
        <p>{{ simulation.agent_count || 0 }} agentes · {{ simulation.rounds || simulation.max_rounds || 0 }} rodadas · {{ (simulation.platforms || ['Twitter','Reddit']).join(', ') }}</p>
      </div>
      <AugurBadge :status="simulation.status || 'draft'" />
    </div>
    <AugurProgress v-if="simulation.status === 'running' || simulation.progress" :value="simulation.progress || 0" :height="6" />
  </article>
</template>
<style scoped>
.card{background:var(--bg-raised);border:1px solid var(--border);padding:14px;border-radius:var(--r-md);display:grid;gap:10px;cursor:pointer}
.head{display:flex;justify-content:space-between;gap:12px}
strong{display:block}
p{color:var(--text-muted);margin:6px 0 0;font-size:13px}
</style>
