<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route  = useRoute()
const router = useRouter()
const simId  = computed(() => route.params.simulationId)

const carregando = ref(true)
const erro       = ref('')
const profiles   = ref([])
const busca      = ref('')

const cores = ['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50','#ff9800','#9c27b0','#00bcd4','#795548','#607d8b']

const filtrados = computed(() => {
  if (!busca.value.trim()) return profiles.value
  const q = busca.value.toLowerCase()
  return profiles.value.filter(p =>
    (p.name || '').toLowerCase().includes(q) ||
    (p.role || p.bio || '').toLowerCase().includes(q)
  )
})

function iniciais(name) {
  return (name || '??').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}
function corAvatar(i) { return cores[i % cores.length] }

onMounted(async () => {
  carregando.value = true
  try {
    // Tentar buscar profiles do endpoint de perfis
    const res = await service.get(`/api/simulation/${simId.value}/profiles`)
    const raw = res?.data?.data || res?.data || res
    profiles.value = raw?.profiles || raw || []
    
    // Se vazio, tentar analytics top_agents
    if (!profiles.value.length) {
      const aRes = await service.get(`/api/analytics/${simId.value}`)
      const analytics = aRes?.data?.data || aRes?.data || {}
      const tw = analytics?.twitter?.top_agents || []
      const rd = analytics?.reddit?.top_agents || []
      const merged = {}
      ;[...tw, ...rd].forEach(a => {
        if (!merged[a.user_id || a.name]) merged[a.user_id || a.name] = a
      })
      profiles.value = Object.values(merged)
    }
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar agentes.'
  } finally {
    carregando.value = false
  }
})

function conversar(agent) {
  // Futuro: navegar para chat individual com o agente
  router.push(`/agentes/${simId.value}`)
}
</script>

<template>
  <AppShell title="Agentes da Simulação">
    <template #actions>
      <AugurButton variant="ghost" @click="router.back()">← Voltar</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="state-box">
      <div class="spin"></div>
      <div>Carregando perfis dos agentes...</div>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="state-box state-err">
      <div style="font-size:42px">⚠️</div>
      <div>{{ erro }}</div>
    </div>

    <div v-else>
      <!-- Header -->
      <div class="header-bar">
        <div class="header-info">
          <div class="header-icon">🧠</div>
          <div>
            <div class="header-title">{{ profiles.length }} agentes no mundo simulado</div>
            <div class="header-sub">Cada agente tem personalidade, crenças e objetivos próprios. Clique para explorar ou converse diretamente.</div>
          </div>
        </div>
        <div class="header-actions">
          <AugurButton variant="ghost" @click="conversar(null)">💬 Conversar</AugurButton>
        </div>
      </div>

      <!-- Search -->
      <div class="search-bar">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="busca" placeholder="Buscar agente por nome ou papel..." />
      </div>

      <!-- Grid -->
      <div class="agents-grid">
        <div v-for="(agent, i) in filtrados" :key="agent.user_id || agent.name || i" class="agent-card">
          <div class="agent-top">
            <div class="avatar" :style="{background: corAvatar(i)}">{{ iniciais(agent.name) }}</div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name || agent.user_name || 'Agente ' + (i+1) }}</div>
              <div class="agent-role">{{ agent.role || agent.bio?.slice(0, 60) || 'Agente simulado' }}</div>
            </div>
          </div>
          <div class="agent-bio" v-if="agent.bio || agent.personality || agent.description">
            {{ (agent.personality || agent.bio || agent.description || '').slice(0, 160) }}
          </div>
          <div class="agent-stats" v-if="agent.posts_count || agent.num_followers">
            <span v-if="agent.posts_count">📝 {{ agent.posts_count }} posts</span>
            <span v-if="agent.total_likes_received">❤️ {{ agent.total_likes_received }}</span>
            <span v-if="agent.num_followers">👥 {{ agent.num_followers }}</span>
          </div>
        </div>
      </div>

      <div v-if="filtrados.length === 0 && busca" class="empty">
        Nenhum agente encontrado para "{{ busca }}"
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.state-box { display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;text-align:center;color:var(--text-muted); }
.state-err { color:var(--danger); }
.spin { width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to { transform:rotate(360deg) } }

.header-bar { display:flex;align-items:center;justify-content:space-between;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:18px 22px;margin-bottom:16px; }
.header-info { display:flex;align-items:center;gap:14px; }
.header-icon { font-size:28px; }
.header-title { font-size:15px;font-weight:700;color:var(--text-primary); }
.header-sub { font-size:12px;color:var(--text-muted);margin-top:2px; }

.search-bar { display:flex;align-items:center;gap:8px;background:var(--bg-surface);border:1px solid var(--border);border-radius:10px;padding:10px 16px;margin-bottom:16px; }
.search-bar svg { color:var(--text-muted);flex-shrink:0; }
.search-bar input { flex:1;background:none;border:none;color:var(--text-primary);font-size:13px;outline:none; }

.agents-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:12px; }
.agent-card { background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:10px;transition:border-color .15s;cursor:default; }
.agent-card:hover { border-color:var(--accent2); }
.agent-top { display:flex;align-items:center;gap:12px; }
.avatar { width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#fff;flex-shrink:0; }
.agent-name { font-size:14px;font-weight:700;color:var(--text-primary); }
.agent-role { font-size:11px;color:var(--text-muted);margin-top:1px; }
.agent-bio { font-size:12px;color:var(--text-muted);line-height:1.6;font-style:italic; }
.agent-stats { display:flex;gap:10px;font-size:11px;color:var(--text-muted); }
.empty { text-align:center;padding:40px;color:var(--text-muted); }

@media (max-width:1080px) { .agents-grid { grid-template-columns:repeat(2,1fr); } }
@media (max-width:680px) { .agents-grid { grid-template-columns:1fr; } }
</style>
