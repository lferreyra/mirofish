<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import logoPath from '../../assets/logo/augur-logo.svg'
import service from '../../api'

const route = useRoute()
const router = useRouter()
const projetos = ref([])

async function carregarProjetos() {
  try {
    const res = await service.get('/api/graph/project/list')
    const raw = res.data || res
    projetos.value = Array.isArray(raw) ? raw : (raw.data || raw.projects || raw.items || [])
  } catch (e) {
    projetos.value = []
  }
}

function statusDot(projeto) {
  if (projeto.status === 'graph_completed') return 'dot-green'
  if (projeto.status === 'graph_building') return 'dot-yellow'
  return 'dot-gray'
}

function isProjetoAtivo(id) {
  return route.path === `/projeto/${id}`
}

function isAtivo(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

onMounted(carregarProjetos)

// Recarregar projetos ao navegar
watch(() => route.path, () => {
  if (route.path === '/' || route.path.startsWith('/projeto')) {
    carregarProjetos()
  }
})
</script>

<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="brand">
      <img :src="logoPath" alt="AUGUR" />
      <div>
        <strong>AUGUR</strong>
        <small>by itcast</small>
      </div>
    </div>

    <!-- Botão novo projeto -->
    <div class="novo-btn-wrap">
      <button class="novo-btn" @click="router.push('/novo')">
        <span class="novo-icon">+</span>
        Nova Simulação
      </button>
    </div>

    <!-- Lista de projetos -->
    <div class="section">
      <p class="section-title">PROJETOS</p>

      <div v-if="projetos.length === 0" class="sem-projetos">
        Nenhum projeto ainda
      </div>

      <button
        v-for="p in projetos"
        :key="p.project_id || p.id"
        class="projeto-item"
        :class="{ active: isProjetoAtivo(p.project_id || p.id) }"
        @click="router.push(`/projeto/${p.project_id || p.id}`)"
      >
        <span :class="['dot', statusDot(p)]"></span>
        <span class="projeto-nome">{{ p.name || 'Sem nome' }}</span>
      </button>
    </div>

    <!-- Footer fixo -->
    <div class="sidebar-footer">
      <button
        class="footer-item"
        :class="{ active: isAtivo('/configuracoes') }"
        @click="router.push('/')"
      >
        Dashboard
      </button>
      <div class="workspace-label">Workspace</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 16px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.brand img { width: 32px; height: 32px; }
.brand strong { display: block; font-size: 14px; color: var(--text-primary); }
.brand small { color: var(--text-muted); font-size: 11px; }

.novo-btn-wrap { padding: 12px 10px 8px; flex-shrink: 0; }
.novo-btn {
  width: 100%;
  background: var(--accent);
  color: #000;
  border: none;
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.15s;
}
.novo-btn:hover { opacity: 0.85; }
.novo-icon { font-size: 16px; font-weight: 400; }

.section {
  flex: 1;
  overflow-y: auto;
  padding: 4px 10px 0;
}
.section-title {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  padding: 8px 6px 6px;
  margin: 0;
}

.sem-projetos {
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px 6px;
  font-style: italic;
}

.projeto-item {
  width: 100%;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  border-radius: 0 6px 6px 0;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 13px;
  text-align: left;
  transition: all 0.15s;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.projeto-item:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
}
.projeto-item.active {
  border-left-color: var(--accent);
  background: var(--accent-dim);
  color: var(--accent);
}

.projeto-nome {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status dots */
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-green { background: var(--accent); }
.dot-yellow {
  background: #f5a623;
  animation: pulse 1.5s infinite;
}
.dot-gray { background: var(--text-muted); opacity: 0.5; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.sidebar-footer {
  flex-shrink: 0;
  border-top: 1px solid var(--border);
  padding: 10px;
}
.footer-item {
  width: 100%;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}
.footer-item:hover { background: var(--bg-raised); color: var(--text-primary); }
.footer-item.active { color: var(--accent); }
.workspace-label {
  font-size: 11px;
  color: var(--text-muted);
  padding: 6px 8px 2px;
}

@media (max-width: 768px) {
  .sidebar { width: 60px; }
  .brand div, .section-title, .projeto-nome, .sem-projetos,
  .novo-btn span:last-child, .workspace-label, .footer-item { display: none; }
  .novo-btn { justify-content: center; padding: 9px; }
  .projeto-item { justify-content: center; padding: 8px; }
}
</style>
