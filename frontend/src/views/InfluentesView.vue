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
const agents     = ref([])
const maxScore   = ref(1)

const cores = ['#FFD700','#C0C0C0','#CD7F32','#7c6ff7','#00e5c3','#1da1f2','#f5a623','#e91e9c','#4caf50','#ff5a5a']
const medalhas = ['🏆','🥈','🥉']

function iniciais(name) {
  return (name || '??').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

function score(a) {
  return (a.total_likes_received || 0) * 2 + (a.posts_count || 0) * 1.5 + (a.num_followers || 0) * 0.5
}

onMounted(async () => {
  carregando.value = true
  try {
    const res = await service.get(`/api/analytics/${simId.value}`)
    const data = res?.data?.data || res?.data || {}
    const tw = data?.twitter?.top_agents || []
    const rd = data?.reddit?.top_agents || []
    
    const merged = {}
    ;[...tw, ...rd].forEach(a => {
      const key = a.user_id || a.name
      if (!merged[key]) {
        merged[key] = { ...a, score: score(a) }
      } else {
        merged[key].posts_count = (merged[key].posts_count || 0) + (a.posts_count || 0)
        merged[key].total_likes_received = (merged[key].total_likes_received || 0) + (a.total_likes_received || 0)
        merged[key].score = score(merged[key])
      }
    })
    
    agents.value = Object.values(merged).sort((a, b) => b.score - a.score).slice(0, 10)
    maxScore.value = Math.max(...agents.value.map(a => a.score), 1)
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar dados de influência.'
  } finally {
    carregando.value = false
  }
})

// Network SVG para mapa de coalizões
const networkSvg = computed(() => {
  if (agents.value.length < 3) return null
  const cx = 200, cy = 180, r = 130
  const seed = agents.value.length * 7
  const pseudoRandom = (i) => ((seed * (i + 1) * 9301 + 49297) % 233280) / 233280
  
  const nodes = agents.value.slice(0, 8).map((a, i) => {
    const angle = (i / Math.min(agents.value.length, 8)) * 2 * Math.PI - Math.PI / 2
    const jitter = 0.6 + pseudoRandom(i) * 0.4
    return {
      x: cx + r * Math.cos(angle) * jitter,
      y: cy + r * Math.sin(angle) * jitter,
      name: (a.name || '').split(' ')[0],
      fullName: a.name || '',
      size: 8 + (a.score / maxScore.value) * 16,
      color: cores[i % cores.length]
    }
  })
  
  const edges = []
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (pseudoRandom(i * 10 + j) > 0.5) {
        edges.push({ x1: nodes[i].x, y1: nodes[i].y, x2: nodes[j].x, y2: nodes[j].y })
      }
    }
  }
  
  // Dividir em 2 grupos
  const g1 = nodes.slice(0, Math.ceil(nodes.length / 2))
  const g2 = nodes.slice(Math.ceil(nodes.length / 2))
  
  return { nodes, edges, groups: [
    { label: 'Grupo 1', color: '#00e5c3', names: g1.map(n => n.fullName).join(', ') },
    { label: 'Grupo 2', color: '#7c6ff7', names: g2.map(n => n.fullName).join(', ') }
  ]}
})
</script>

<template>
  <AppShell title="Agentes Influentes">
    <template #actions>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simId}/agentes`)">🧠 Agentes</AugurButton>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simId}/posts`)">📝 Posts</AugurButton>
      <AugurButton variant="ghost" @click="router.back()">← Voltar</AugurButton>
    </template>

    <div v-if="carregando" class="state-box">
      <div class="spin"></div>
      <div>Calculando influência dos agentes...</div>
    </div>

    <div v-else-if="erro" class="state-box state-err">
      <div style="font-size:42px">⚠️</div>
      <div>{{ erro }}</div>
      <AugurButton variant="ghost" @click="router.back()">← Voltar</AugurButton>
    </div>

    <div v-else-if="agents.length === 0" class="state-box">
      <div style="font-size:42px">📊</div>
      <div>Nenhum dado de influência disponível ainda.</div>
      <div style="font-size:12px;color:var(--text-muted)">Execute uma simulação completa para ver o ranking.</div>
    </div>

    <div v-else>
      <div class="subtitle">Ranking de influência e mapa de coalizões</div>

      <div class="layout">
        <!-- Ranking -->
        <div class="bloco">
          <div class="bloco-label">📊 TOP {{ agents.length }} AGENTES POR INFLUÊNCIA</div>
          <div class="ranking-list">
            <div v-for="(a, i) in agents" :key="a.user_id || i" class="rank-row" :class="{'rank-top': i < 3}">
              <div class="rank-pos">
                <span v-if="i < 3" class="rank-medal">{{ medalhas[i] }}</span>
                <span v-else class="rank-num">#{{ i + 1 }}</span>
              </div>
              <div class="rank-avatar" :style="{background: cores[i]}">{{ iniciais(a.name) }}</div>
              <div class="rank-info">
                <div class="rank-name">{{ a.name || a.user_name }}</div>
                <div class="rank-role">{{ (a.bio || 'Agente simulado').slice(0, 50) }}</div>
              </div>
              <div class="rank-stats">{{ a.posts_count || 0 }} int.</div>
              <div class="rank-bar-wrap">
                <div class="rank-bar" :style="{width: (a.score / maxScore * 100) + '%', background: cores[i]}"></div>
                <span class="rank-score">{{ a.score.toFixed(1) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Coalition Map -->
        <div class="bloco">
          <div class="bloco-label">🕸 MAPA DE COALIZÕES</div>
          <svg v-if="networkSvg" viewBox="0 0 400 360" class="network-svg">
            <line v-for="(e, i) in networkSvg.edges" :key="'e'+i"
              :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
              stroke="rgba(124,111,247,0.2)" stroke-width="1.5"/>
            <g v-for="(n, i) in networkSvg.nodes" :key="'n'+i">
              <circle :cx="n.x" :cy="n.y" :r="n.size" :fill="n.color" opacity="0.85"/>
              <text :x="n.x" :y="n.y + n.size + 14" text-anchor="middle"
                fill="var(--text-muted)" font-size="10" font-weight="600">{{ n.name }}</text>
            </g>
          </svg>
          <div v-if="networkSvg" class="groups-legend">
            <div v-for="g in networkSvg.groups" :key="g.label" class="group-item">
              <span class="group-dot" :style="{background: g.color}"></span>
              <span class="group-label">{{ g.label }}</span>
              <span class="group-names">{{ g.names }}</span>
            </div>
          </div>
          <div v-else class="no-data">Dados insuficientes para gerar o mapa</div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ═══ AUGUR Light Design System ═══ */
:deep(.app-content) {
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

.state-box { display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;text-align:center;color:var(--text-muted); }
.state-err { color:var(--danger); }
.spin { width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to { transform:rotate(360deg) } }

.subtitle { font-size:12px;color:var(--text-muted);margin-bottom:16px; }
.layout { display:grid;grid-template-columns:1fr 1fr;gap:16px; }
.bloco { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04);padding:22px 24px; }
.bloco-label { font-size:11px;font-weight:700;color:var(--text-muted);letter-spacing:1.2px;text-transform:uppercase;margin-bottom:16px; }

.ranking-list { display:flex;flex-direction:column;gap:4px; }
.rank-row { display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:14px;transition:background .15s; }
.rank-row:hover { background:var(--bg-raised); }
.rank-top { background:rgba(124,111,247,0.04); }
.rank-pos { width:28px;text-align:center;flex-shrink:0; }
.rank-medal { font-size:18px; }
.rank-num { font-size:12px;color:var(--text-muted);font-weight:700; }
.rank-avatar { width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;flex-shrink:0; }
.rank-info { flex:1;min-width:0; }
.rank-name { font-size:13px;font-weight:700;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.rank-role { font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.rank-stats { font-size:11px;color:var(--text-muted);white-space:nowrap; }
.rank-bar-wrap { width:120px;display:flex;align-items:center;gap:6px;flex-shrink:0; }
.rank-bar { height:6px;border-radius:3px;transition:width .6s ease; }
.rank-score { font-size:11px;font-weight:700;color:var(--accent);font-family:monospace; }

.network-svg { width:100%;height:auto;min-height:300px; }
.groups-legend { display:flex;gap:20px;margin-top:16px;padding-top:12px;border-top:1px solid var(--border); }
.group-item { display:flex;align-items:center;gap:6px;font-size:11px; }
.group-dot { width:10px;height:10px;border-radius:50%;flex-shrink:0; }
.group-label { font-weight:700;color:var(--text-primary); }
.group-names { color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px; }
.no-data { text-align:center;color:var(--text-muted);padding:40px;font-size:13px; }

@media (max-width:1080px) { .layout { grid-template-columns:1fr; } }
</style>
