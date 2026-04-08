<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logoPath from '../../assets/logo/augur-logo.svg'
import service from '../../api'

const route = useRoute()
const router = useRouter()
const projetos = ref([])
const simulacoes = ref([])
const carregando = ref(false)

async function carregarDados() {
  carregando.value = true
  try {
    const [projRes, simRes] = await Promise.allSettled([
      service.get('/api/graph/project/list'),
      service.get('/api/simulation/history', { params: { limit: 100 } })
    ])
    if (projRes.status === 'fulfilled') {
      const raw = projRes.value?.data || projRes.value
      projetos.value = (Array.isArray(raw) ? raw : (raw?.data || raw?.items || []))
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    }
    if (simRes.status === 'fulfilled') {
      const raw = simRes.value?.data || simRes.value
      simulacoes.value = Array.isArray(raw) ? raw : (raw?.data || raw?.history || [])
    }
  } catch (e) {
    projetos.value = []
  } finally {
    carregando.value = false
  }
}

function ultimaSim(projectId) {
  return simulacoes.value
    .filter(s => s.project_id === projectId)
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))[0] || null
}

function dotClass(p) {
  const sim = ultimaSim(p.project_id || p.id)
  const s = sim ? (sim.runner_status || sim.status) : null
  if (s === 'running') return 'dot-pulse'
  if (s === 'completed') return 'dot-green'
  if (p.status === 'graph_building') return 'dot-yellow'
  if (p.status === 'graph_completed') return 'dot-green'
  return 'dot-gray'
}

function subLabel(p) {
  const sim = ultimaSim(p.project_id || p.id)
  if (!sim) return 'Sem simulações'
  const s = sim.runner_status || sim.status
  if (s === 'running') return `⏳ Rodada ${sim.current_round || 0}/${sim.total_rounds || '?'}`
  if (s === 'completed') return '✅ Concluída'
  if (s === 'stopped' || s === 'paused') return '⏸ Pausada'
  if (s === 'failed') return '❌ Erro'
  if (s === 'preparing' || s === 'ready') return '⚙️ Preparando'
  return '📋 Iniciada'
}

function isAtivo(id) {
  return route.path === `/projeto/${id}`
}

onMounted(carregarDados)
watch(() => route.path, () => { carregarDados() })
</script>

<template>
  <aside class="sidebar">

    <div class="brand" @click="router.push('/')">
      <img :src="logoPath" alt="AUGUR" />
      <div class="brand-text">
        <strong>AUGUR</strong>
        <small>by itcast</small>
      </div>
    </div>

    <div class="novo-wrap">
      <button class="btn-novo" @click="router.push('/projeto/novo')">
        <span class="plus">+</span>
        <span class="label">Novo Projeto</span>
      </button>
    </div>

    <div class="nav-section">
      <div class="nav-label">PROJETOS</div>

      <div v-if="carregando" class="nav-loading">
        <div class="mini-spinner"></div>
      </div>

      <div v-else-if="projetos.length === 0" class="nav-empty">
        Nenhum projeto ainda
      </div>

      <div
        v-for="p in projetos"
        :key="p.project_id || p.id"
        class="nav-item"
        :class="{ active: isAtivo(p.project_id || p.id) }"
        @click="router.push(`/projeto/${p.project_id || p.id}`)"
      >
        <div class="item-row">
          <span :class="['dot', dotClass(p)]"></span>
          <span class="item-nome">{{ p.name || 'Sem nome' }}</span>
        </div>
        <div class="item-sub">{{ subLabel(p) }}</div>
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="footer-sep"></div>
      <div class="footer-link" @click="router.push('/')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="13" height="13">
          <rect x="1" y="1" width="6" height="6" rx="1"/>
          <rect x="9" y="1" width="6" height="6" rx="1"/>
          <rect x="1" y="9" width="6" height="6" rx="1"/>
          <rect x="9" y="9" width="6" height="6" rx="1"/>
        </svg>
        <span>Dashboard</span>
      </div>
      <div class="footer-link" @click="router.push('/comparar')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="13" height="13">
          <line x1="1" y1="12" x2="5" y2="4"/><line x1="5" y1="4" x2="9" y2="8"/><line x1="9" y1="8" x2="15" y2="2"/>
          <line x1="1" y1="14" x2="15" y2="14"/>
        </svg>
        <span>Comparar</span>
      </div>
      <div class="footer-workspace">Workspace</div>
    </div>

  </aside>
</template>

<style scoped>
.sidebar {
  width: 230px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  cursor: pointer;
  transition: background 0.15s;
}
.brand:hover { background: var(--bg-raised); }
.brand img { width: 32px; height: 32px; border-radius: 8px; }
.brand-text strong { display: block; font-size: 14px; color: var(--text-primary); }
.brand-text small { color: var(--text-muted); font-size: 10px; letter-spacing: 0.5px; }

.novo-wrap { padding: 12px 10px 6px; flex-shrink: 0; }
.btn-novo {
  width: 100%;
  background: var(--accent);
  color: #000;
  border: none;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.15s;
}
.btn-novo:hover { opacity: 0.85; }
.plus { font-size: 18px; font-weight: 300; line-height: 1; }

.nav-section {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 8px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-md) transparent;
}

.nav-label {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1.2px;
  padding: 10px 6px 6px;
  font-weight: 500;
}

.nav-loading { padding: 10px 6px; }
.mini-spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--border-md);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.nav-empty {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 6px;
  font-style: italic;
}

.nav-item {
  padding: 8px 8px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  border-left: 2px solid transparent;
  margin-bottom: 1px;
}
.nav-item:hover { background: var(--bg-raised); }
.nav-item.active {
  background: var(--accent-dim);
  border-left-color: var(--accent);
}

.item-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 3px;
}
.item-nome {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.nav-item.active .item-nome { color: var(--accent); }
.item-sub {
  font-size: 10px;
  color: var(--text-muted);
  padding-left: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-green { background: var(--accent); }
.dot-yellow { background: #f5a623; }
.dot-gray { background: var(--text-muted); opacity: 0.35; }
.dot-pulse {
  background: #f5a623;
  animation: pulse 1.4s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(245,166,35,0.5); }
  50% { opacity: 0.7; box-shadow: 0 0 0 4px rgba(245,166,35,0); }
}

.sidebar-footer { flex-shrink: 0; padding: 8px 10px 12px; }
.footer-sep { height: 1px; background: var(--border); margin-bottom: 8px; }
.footer-link {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-muted);
  padding: 6px; border-radius: 6px; cursor: pointer; transition: all 0.15s;
}
.footer-link:hover { background: var(--bg-raised); color: var(--text-primary); }
.footer-workspace { font-size: 11px; color: var(--text-muted); padding: 3px 6px; opacity: 0.5; }

@media (max-width: 768px) {
  .sidebar { width: 56px; }
  .brand-text, .label, .nav-label, .item-nome, .item-sub,
  .nav-empty, .footer-link span, .footer-workspace { display: none; }
  .btn-novo { justify-content: center; padding: 9px; }
  .nav-item { display: flex; justify-content: center; padding: 10px 4px; }
  .item-row { justify-content: center; }
}
</style>
