<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

defineProps({ title: { type: String, default: '' } })

const route = useRoute()
const router = useRouter()

const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'Dashboard', icon: '🏠', path: '/' }]
  const p = route.path

  if (p.startsWith('/projeto/novo')) {
    crumbs.push({ label: 'Novo Projeto', icon: '✦' })
  } else if (p.startsWith('/projeto/') && p.includes('/grafo')) {
    crumbs.push({ label: 'Projeto', icon: '📂', path: `/projeto/${route.params.projectId}` })
    crumbs.push({ label: 'Grafo', icon: '🕸' })
  } else if (p.startsWith('/projeto/')) {
    crumbs.push({ label: 'Projeto', icon: '📂' })
  } else if (p.startsWith('/simulacao/') && p.includes('/executar')) {
    crumbs.push({ label: 'Simulação', icon: '🧪' })
    crumbs.push({ label: 'Dashboard ao Vivo', icon: '📡' })
  } else if (p.startsWith('/simulacao/') && p.includes('/agentes')) {
    crumbs.push({ label: 'Simulação', icon: '🧪' })
    crumbs.push({ label: 'Agentes', icon: '🧠' })
  } else if (p.startsWith('/simulacao/') && p.includes('/agente/')) {
    crumbs.push({ label: 'Simulação', icon: '🧪' })
    crumbs.push({ label: 'Agentes', icon: '🧠', path: `/simulacao/${route.params.simulationId}/agentes` })
    crumbs.push({ label: 'Perfil', icon: '👤' })
  } else if (p.startsWith('/simulacao/') && p.includes('/influentes')) {
    crumbs.push({ label: 'Simulação', icon: '🧪' })
    crumbs.push({ label: 'Influentes', icon: '👑' })
  } else if (p.startsWith('/simulacao/') && p.includes('/posts')) {
    crumbs.push({ label: 'Simulação', icon: '🧪' })
    crumbs.push({ label: 'Posts', icon: '📝' })
  } else if (p.startsWith('/simulacao/')) {
    crumbs.push({ label: 'Pipeline', icon: '⚙️' })
  } else if (p.startsWith('/relatorio/')) {
    crumbs.push({ label: 'Relatório', icon: '📊' })
  } else if (p.startsWith('/agentes/')) {
    crumbs.push({ label: 'Relatório', icon: '📊', path: `/relatorio/${route.params.reportId}` })
    crumbs.push({ label: 'Entrevistas', icon: '💬' })
  } else if (p === '/comparar') {
    crumbs.push({ label: 'Comparar', icon: '📊' })
  }

  return crumbs
})

function navTo(path) {
  if (path) router.push(path)
}
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopbar :title="title">
        <template #actions><slot name="actions" /></template>
      </AppTopbar>
      <!-- Breadcrumbs -->
      <nav v-if="breadcrumbs.length > 1" class="breadcrumbs">
        <template v-for="(bc, i) in breadcrumbs" :key="i">
          <span v-if="i > 0" class="bc-sep">›</span>
          <span
            :class="['bc-item', { 'bc-link': bc.path && i < breadcrumbs.length - 1, 'bc-current': i === breadcrumbs.length - 1 }]"
            @click="navTo(bc.path)">
            <span class="bc-icon">{{ bc.icon }}</span>
            {{ bc.label }}
          </span>
        </template>
      </nav>
      <main class="app-content"><slot /></main>
    </div>
  </div>
</template>

<style scoped>
/* ═══ AUGUR Light Design System ═══ */
:root {
  --bg-base: #f5f5fa;
  --bg-surface: #ffffff;
  --bg-raised: #fafafe;
  --bg-overlay: #f0f0f5;
  --border: #eeeef2;
  --border-md: #dddde5;
  --text-primary: #1a1a2e;
  --text-secondary: #444466;
  --text-muted: #8888aa;
  --accent: #00e5c3;
  --accent-dim: rgba(0,229,195,0.08);
  --accent2: #7c6ff7;
  --accent2-dim: rgba(124,111,247,0.08);
  --danger: #ff5a5a;
  --font-mono: 'JetBrains Mono', monospace;
}

.app-shell { display:flex; min-height:100vh; background:var(--bg-base); }
.app-main { flex:1; min-width:0; display:flex; flex-direction:column; }
.app-content { padding:24px; overflow:auto; height:calc(100vh - 56px - 32px); }
.breadcrumbs { display:flex;align-items:center;gap:6px;padding:6px 24px;font-size:11px;color:var(--text-muted);background:var(--bg-surface);border-bottom:1px solid var(--border);flex-shrink:0;min-height:32px; }
.bc-item { display:flex;align-items:center;gap:4px; }
.bc-link { cursor:pointer;color:var(--text-muted);transition:color .12s; }
.bc-link:hover { color:var(--accent2); }
.bc-current { color:var(--text-primary);font-weight:600; }
.bc-sep { color:var(--border-md);font-size:13px; }
.bc-icon { font-size:12px; }
</style>
