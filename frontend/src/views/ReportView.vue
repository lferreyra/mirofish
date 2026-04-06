<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route  = useRoute()
const router = useRouter()

const report    = ref(null)
const analytics = ref(null)
const carregando = ref(true)
const erro      = ref('')
const abaAtiva  = ref('relatorio')

// ─── Carregar dados ───────────────────────────────────────────
onMounted(async () => {
  carregando.value = true
  try {
    // 1. Carregar relatório
    const rRes = await service.get(`/api/report/${route.params.reportId}`).catch(e => ({ error: e }))
    if (rRes.error) throw rRes.error

    const raw = rRes?.data?.data || rRes?.data || rRes
    report.value = raw

    // 2. Carregar analytics com simulation_id (endpoint correto: /api/analytics/<sim_id>)
    if (raw?.simulation_id) {
      try {
        const aRes = await service.get(`/api/analytics/${raw.simulation_id}`)
        analytics.value = aRes?.data?.data || aRes?.data || null
      } catch { /* analytics é opcional — não bloqueia o relatório */ }
    }
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar relatório.'
  } finally {
    carregando.value = false
  }
})

// ─── Dados do relatório ───────────────────────────────────────
const titulo   = computed(() => report.value?.outline?.title || report.value?.title || 'Relatório de Previsão')
const resumo   = computed(() => report.value?.outline?.summary || report.value?.simulation_requirement || '')
const secoes   = computed(() => report.value?.outline?.sections || [])
const markdown = computed(() => report.value?.markdown_content || '')
const simReq   = computed(() => report.value?.simulation_requirement || '')
const geradoEm = computed(() => {
  const d = report.value?.completed_at || report.value?.created_at
  if (!d) return ''
  return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
})

// ─── Dados de analytics ───────────────────────────────────────
const combinedRounds = computed(() => analytics.value?.combined?.rounds || [])
const totalInteracoes = computed(() => analytics.value?.combined?.total_interactions || 0)
const peakRound      = computed(() => analytics.value?.combined?.peak_round || {})
const twTotals       = computed(() => analytics.value?.twitter?.totals || {})
const rdTotals       = computed(() => analytics.value?.reddit?.totals || {})
const twTopPosts     = computed(() => (analytics.value?.twitter?.top_posts || []).slice(0, 5))
const rdTopPosts     = computed(() => (analytics.value?.reddit?.top_posts || []).slice(0, 5))
const twEngagement   = computed(() => analytics.value?.twitter?.engagement || [])

// ─── Gráfico SVG de atividade por rodada ──────────────────────
const chartWidth  = 560
const chartHeight = 180
const chartPad    = { top: 20, right: 20, bottom: 30, left: 40 }

const chartPoints = computed(() => {
  const rounds = combinedRounds.value
  if (!rounds.length) return { twitter: '', reddit: '', total: '', xLabels: [] }

  const maxVal = Math.max(...rounds.map(r => r.total), 1)
  const w = chartWidth - chartPad.left - chartPad.right
  const h = chartHeight - chartPad.top - chartPad.bottom
  const n = rounds.length

  const x = (i) => chartPad.left + (i / Math.max(n - 1, 1)) * w
  const y = (v) => chartPad.top + h - (v / maxVal) * h

  const toPath = (getter) =>
    rounds.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(getter(r)).toFixed(1)}`).join(' ')

  const xLabels = rounds
    .filter((_, i) => i % Math.max(Math.floor(n / 8), 1) === 0)
    .map((r, _, arr) => ({
      round: r.round,
      xPos: x(rounds.indexOf(r))
    }))

  return {
    twitter: toPath(r => r.twitter),
    reddit:  toPath(r => r.reddit),
    total:   toPath(r => r.total),
    xLabels,
    maxVal,
    yLines: [0, 0.25, 0.5, 0.75, 1].map(f => ({
      val: Math.round(maxVal * f),
      y: y(maxVal * f)
    }))
  }
})

// ─── Renderizar markdown simples ──────────────────────────────
function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^([^<].+)$/gm, (m) => m.startsWith('<') ? m : `<p>${m}</p>`)
}

// ─── Helpers ─────────────────────────────────────────────────
function truncar(text, n = 120) {
  if (!text) return ''
  return text.length > n ? text.slice(0, n) + '...' : text
}

async function voltar() {
  // project_id pode vir direto do relatório (backend enriquecido)
  // ou precisamos buscar via simulation_id
  let pid = report.value?.project_id
  if (!pid && report.value?.simulation_id) {
    try {
      const res = await service.get('/api/simulation/list', { params: { limit: 200 } })
      const lista = res?.data?.data || res?.data || []
      const sim = lista.find(s => s.simulation_id === report.value.simulation_id)
      pid = sim?.project_id
    } catch { /* ignorar */ }
  }
  router.push(pid ? `/projeto/${pid}` : '/')
}

function corEngajamento(idx) {
  const cores = ['#00e5c3', '#7c6ff7', '#f5a623', '#ff5a5a', '#1da1f2']
  return cores[idx % cores.length]
}
</script>

<template>
  <AppShell :title="titulo">
    <template #actions>
      <AugurButton variant="ghost" @click="voltar">← Projeto</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <div class="loading-text">
        <div class="loading-titulo">Carregando relatório...</div>
        <div class="loading-sub">Processando análises e dados da simulação</div>
      </div>
    </div>

    <!-- Erro -->
    <div v-else-if="erro" class="erro-state">
      <div class="erro-icon">⚠️</div>
      <div class="erro-msg">{{ erro }}</div>
      <button class="btn-ghost" @click="voltar">← Voltar</button>
    </div>

    <div v-else-if="report" class="page">

      <!-- ─── HEADER ─── -->
      <div class="header-card">
        <div class="header-badge">📊 Relatório de Previsão — AUGUR by itcast</div>
        <h1 class="header-titulo">{{ titulo }}</h1>
        <div class="header-hipotese" v-if="simReq">
          <span class="hip-label">Hipótese testada:</span> {{ simReq }}
        </div>
        <div class="header-meta">
          <span v-if="geradoEm">🕐 Gerado em {{ geradoEm }}</span>
          <span v-if="totalInteracoes">🔬 {{ totalInteracoes }} interações simuladas</span>
          <span v-if="combinedRounds.length">🔄 {{ combinedRounds.length }} rodadas</span>
        </div>
        <div class="header-resumo" v-if="resumo">{{ resumo }}</div>
      </div>

      <!-- ─── ABAS ─── -->
      <div class="abas">
        <button :class="['aba', { active: abaAtiva === 'relatorio' }]" @click="abaAtiva = 'relatorio'">
          📋 Relatório
        </button>
        <button :class="['aba', { active: abaAtiva === 'analytics' }]" @click="abaAtiva = 'analytics'"
          v-if="analytics">
          📈 Analytics
        </button>
        <button :class="['aba', { active: abaAtiva === 'posts' }]" @click="abaAtiva = 'posts'"
          v-if="twTopPosts.length || rdTopPosts.length">
          💬 Posts
        </button>
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ABA: RELATÓRIO                                         -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-if="abaAtiva === 'relatorio'">

        <!-- Seções do relatório -->
        <div v-if="secoes.length" class="secoes">
          <div v-for="(s, idx) in secoes" :key="idx" class="secao-card">
            <div class="secao-header">
              <span class="secao-num">{{ String(idx + 1).padStart(2, '0') }}</span>
              <h2 class="secao-titulo">{{ s.title }}</h2>
            </div>
            <div class="secao-content" v-if="s.content" v-html="renderMarkdown(s.content)"></div>
            <div class="secao-desc" v-else-if="s.description">{{ s.description }}</div>
          </div>
        </div>

        <!-- Markdown completo (fallback) -->
        <div v-else-if="markdown" class="markdown-card">
          <div class="markdown-body" v-html="renderMarkdown(markdown)"></div>
        </div>

        <div v-else class="vazio">
          <div>Relatório ainda sendo processado...</div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ABA: ANALYTICS                                         -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-if="abaAtiva === 'analytics' && analytics" class="analytics">

        <!-- Métricas gerais -->
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">Total de interações</div>
            <div class="metric-val">{{ totalInteracoes.toLocaleString('pt-BR') }}</div>
            <div class="metric-sub">Twitter + Reddit</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Posts Twitter</div>
            <div class="metric-val tw">{{ twTotals.posts || 0 }}</div>
            <div class="metric-sub">{{ twTotals.likes || 0 }} curtidas · {{ twTotals.comments || 0 }} comentários</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Posts Reddit</div>
            <div class="metric-val rd">{{ rdTotals.posts || 0 }}</div>
            <div class="metric-sub">{{ rdTotals.likes || 0 }} curtidas · {{ rdTotals.comments || 0 }} comentários</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">Pico de atividade</div>
            <div class="metric-val pk">Rodada {{ peakRound.round }}</div>
            <div class="metric-sub">{{ peakRound.total }} ações nessa rodada</div>
          </div>
        </div>

        <!-- Gráfico de atividade por rodada -->
        <div class="chart-card" v-if="combinedRounds.length > 1">
          <div class="chart-header">
            <h3 class="chart-titulo">Atividade por Rodada</h3>
            <div class="chart-legend">
              <span class="legend-tw">■ Twitter</span>
              <span class="legend-rd">■ Reddit</span>
            </div>
          </div>
          <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="chart-svg" preserveAspectRatio="xMidYMid meet">
            <!-- Grid lines -->
            <g v-for="line in chartPoints.yLines" :key="line.val">
              <line :x1="chartPad.left" :y1="line.y" :x2="chartWidth - chartPad.right" :y2="line.y"
                stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
              <text :x="chartPad.left - 6" :y="line.y + 4" text-anchor="end"
                fill="rgba(255,255,255,0.3)" font-size="10">{{ line.val }}</text>
            </g>
            <!-- X labels -->
            <g v-for="label in chartPoints.xLabels" :key="label.round">
              <text :x="label.xPos" :y="chartHeight - 5" text-anchor="middle"
                fill="rgba(255,255,255,0.3)" font-size="10">R{{ label.round }}</text>
            </g>
            <!-- Twitter line -->
            <path v-if="chartPoints.twitter" :d="chartPoints.twitter"
              fill="none" stroke="#1da1f2" stroke-width="2" stroke-linejoin="round"/>
            <!-- Reddit line -->
            <path v-if="chartPoints.reddit" :d="chartPoints.reddit"
              fill="none" stroke="#ff4500" stroke-width="2" stroke-linejoin="round"/>
            <!-- Area under total -->
            <path v-if="chartPoints.total"
              :d="`${chartPoints.total} L${chartWidth - chartPad.right},${chartHeight - chartPad.bottom} L${chartPad.left},${chartHeight - chartPad.bottom} Z`"
              fill="rgba(0,229,195,0.05)" stroke="none"/>
            <path v-if="chartPoints.total" :d="chartPoints.total"
              fill="none" stroke="rgba(0,229,195,0.4)" stroke-width="1.5" stroke-dasharray="4,3"/>
          </svg>
        </div>

        <!-- Engajamento por agente (barras horizontais) -->
        <div class="chart-card" v-if="twEngagement.length">
          <h3 class="chart-titulo">Top Agentes — Posts publicados (Twitter)</h3>
          <div class="bar-list">
            <div v-for="(ag, idx) in twEngagement.slice(0, 10)" :key="ag.name" class="bar-row">
              <div class="bar-name">{{ ag.name || ag.user_name || `Agente ${idx+1}` }}</div>
              <div class="bar-track">
                <div class="bar-fill"
                  :style="{
                    width: ((ag.posts / (twEngagement[0]?.posts || 1)) * 100) + '%',
                    background: corEngajamento(idx)
                  }">
                </div>
              </div>
              <div class="bar-val">{{ ag.posts }}</div>
              <div class="bar-likes">❤️ {{ ag.likes_received }}</div>
            </div>
          </div>
        </div>

        <!-- Top agentes Twitter -->
        <div class="chart-card" v-if="analytics.twitter?.top_agents?.length">
          <h3 class="chart-titulo">Top Agentes por Curtidas Recebidas (Twitter)</h3>
          <div class="agents-grid">
            <div v-for="(ag, idx) in analytics.twitter.top_agents.slice(0, 6)" :key="ag.user_id" class="agent-card">
              <div class="agent-rank">#{{ idx + 1 }}</div>
              <div class="agent-name">{{ ag.name || ag.user_name }}</div>
              <div class="agent-bio">{{ truncar(ag.bio, 80) }}</div>
              <div class="agent-stats">
                <span>📝 {{ ag.posts_count }} posts</span>
                <span>❤️ {{ ag.total_likes_received }}</span>
                <span>👥 {{ ag.num_followers }} seguidores</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ABA: POSTS                                             -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-if="abaAtiva === 'posts'" class="posts-section">

        <div class="posts-col" v-if="twTopPosts.length">
          <div class="posts-header">
            <span class="tw-badge">Twitter / X</span>
            <span class="posts-subtitle">Top posts por curtidas</span>
          </div>
          <div v-for="post in twTopPosts" :key="post.post_id" class="post-card tw-card">
            <div class="post-author">{{ post.name || post.user_name || 'Agente' }}</div>
            <div class="post-content">{{ truncar(post.content, 200) }}</div>
            <div class="post-stats">
              <span class="stat-like">❤️ {{ post.num_likes }}</span>
              <span class="stat-dis" v-if="post.num_dislikes">👎 {{ post.num_dislikes }}</span>
              <span class="stat-rep" v-if="post.num_reports">🚩 {{ post.num_reports }}</span>
            </div>
          </div>
        </div>

        <div class="posts-col" v-if="rdTopPosts.length">
          <div class="posts-header">
            <span class="rd-badge">Reddit</span>
            <span class="posts-subtitle">Top posts por curtidas</span>
          </div>
          <div v-for="post in rdTopPosts" :key="post.post_id" class="post-card rd-card">
            <div class="post-author">{{ post.name || post.user_name || 'Agente' }}</div>
            <div class="post-content">{{ truncar(post.content, 200) }}</div>
            <div class="post-stats">
              <span class="stat-like">❤️ {{ post.num_likes }}</span>
              <span class="stat-dis" v-if="post.num_dislikes">👎 {{ post.num_dislikes }}</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  </AppShell>
</template>

<style scoped>
/* Layout */
.loading { display:flex; align-items:center; gap:16px; padding:60px; }
.spinner { width:28px; height:28px; border:3px solid var(--border-md); border-top-color:var(--accent); border-radius:50%; animation:spin .8s linear infinite; flex-shrink:0; }
@keyframes spin { to { transform:rotate(360deg); } }
.loading-titulo { font-size:16px; font-weight:600; color:var(--text-primary); }
.loading-sub { font-size:13px; color:var(--text-muted); margin-top:4px; }
.erro-state { text-align:center; padding:60px; display:flex; flex-direction:column; align-items:center; gap:12px; }
.erro-icon { font-size:48px; }
.erro-msg { font-size:14px; color:var(--danger); max-width:400px; }
.btn-ghost { background:none; border:1px solid var(--border); color:var(--text-secondary); border-radius:8px; padding:8px 16px; font-size:13px; cursor:pointer; }

.page { display:flex; flex-direction:column; gap:16px; }

/* Header */
.header-card { background:linear-gradient(135deg, var(--bg-surface) 0%, rgba(124,111,247,0.05) 100%); border:1px solid rgba(124,111,247,0.2); border-radius:16px; padding:28px 32px; display:flex; flex-direction:column; gap:12px; }
.header-badge { font-size:11px; font-weight:600; color:var(--accent2); text-transform:uppercase; letter-spacing:1px; }
.header-titulo { font-size:24px; font-weight:800; color:var(--text-primary); margin:0; letter-spacing:-.4px; line-height:1.3; }
.header-hipotese { font-size:13px; color:var(--text-secondary); background:var(--bg-raised); border-left:3px solid var(--accent2); padding:10px 14px; border-radius:0 8px 8px 0; line-height:1.6; }
.hip-label { font-weight:600; color:var(--accent2); margin-right:6px; }
.header-meta { display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:var(--text-muted); }
.header-resumo { font-size:14px; color:var(--text-secondary); line-height:1.7; font-style:italic; }

/* Abas */
.abas { display:flex; gap:4px; border-bottom:1px solid var(--border); padding-bottom:0; }
.aba { background:none; border:none; border-bottom:2px solid transparent; color:var(--text-muted); padding:8px 18px; font-size:13px; font-weight:500; cursor:pointer; transition:all .2s; margin-bottom:-1px; border-radius:8px 8px 0 0; }
.aba:hover { color:var(--text-secondary); background:var(--bg-raised); }
.aba.active { color:var(--accent2); border-bottom-color:var(--accent2); background:var(--bg-surface); }

/* Relatório - seções */
.secoes { display:flex; flex-direction:column; gap:12px; }
.secao-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; overflow:hidden; }
.secao-header { display:flex; align-items:center; gap:12px; padding:16px 20px; border-bottom:1px solid var(--border); background:var(--bg-raised); }
.secao-num { font-size:11px; font-weight:700; color:var(--accent2); font-family:var(--font-mono); background:rgba(124,111,247,0.1); padding:3px 8px; border-radius:4px; }
.secao-titulo { font-size:15px; font-weight:700; color:var(--text-primary); margin:0; }
.secao-content { padding:20px; color:var(--text-secondary); font-size:14px; line-height:1.8; }
.secao-content :deep(h1), .secao-content :deep(h2) { font-size:17px; font-weight:700; color:var(--text-primary); margin:20px 0 10px; }
.secao-content :deep(h3), .secao-content :deep(h4) { font-size:14px; font-weight:600; color:var(--accent2); margin:16px 0 8px; }
.secao-content :deep(strong) { color:var(--text-primary); }
.secao-content :deep(ul) { padding-left:20px; margin:8px 0; }
.secao-content :deep(li) { margin-bottom:6px; }
.secao-content :deep(p) { margin:0 0 12px; }
.secao-desc { padding:16px 20px; color:var(--text-muted); font-size:13px; font-style:italic; }

.markdown-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; padding:28px; }
.markdown-body { color:var(--text-secondary); font-size:14px; line-height:1.8; }
.markdown-body :deep(h1) { font-size:20px; font-weight:800; color:var(--text-primary); margin:24px 0 12px; }
.markdown-body :deep(h2) { font-size:17px; font-weight:700; color:var(--text-primary); margin:20px 0 10px; }
.markdown-body :deep(h3) { font-size:14px; font-weight:600; color:var(--accent2); margin:16px 0 8px; }
.markdown-body :deep(strong) { color:var(--text-primary); }
.markdown-body :deep(ul) { padding-left:20px; }
.markdown-body :deep(li) { margin-bottom:6px; }
.markdown-body :deep(p) { margin:0 0 14px; }

.vazio { text-align:center; padding:48px; color:var(--text-muted); font-size:14px; }

/* Analytics */
.analytics { display:flex; flex-direction:column; gap:16px; }
.metrics-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.metric-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; padding:16px 18px; display:flex; flex-direction:column; gap:4px; }
.metric-label { font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.5px; }
.metric-val { font-size:24px; font-weight:800; color:var(--text-primary); font-family:var(--font-mono); }
.metric-val.tw { color:#1da1f2; }
.metric-val.rd { color:#ff4500; }
.metric-val.pk { color:var(--accent); font-size:18px; }
.metric-sub { font-size:11px; color:var(--text-muted); }

.chart-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px; padding:20px; }
.chart-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
.chart-titulo { font-size:14px; font-weight:600; color:var(--text-primary); margin:0 0 12px; }
.chart-legend { display:flex; gap:12px; font-size:11px; }
.legend-tw { color:#1da1f2; }
.legend-rd { color:#ff4500; }
.chart-svg { width:100%; height:auto; display:block; }

/* Barras */
.bar-list { display:flex; flex-direction:column; gap:8px; }
.bar-row { display:flex; align-items:center; gap:10px; }
.bar-name { font-size:12px; color:var(--text-secondary); min-width:140px; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bar-track { flex:1; height:6px; background:var(--border); border-radius:3px; overflow:hidden; }
.bar-fill { height:100%; border-radius:3px; transition:width .4s; }
.bar-val { font-size:12px; color:var(--text-primary); font-family:var(--font-mono); min-width:24px; text-align:right; }
.bar-likes { font-size:11px; color:var(--text-muted); min-width:44px; }

/* Agentes */
.agents-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
.agent-card { background:var(--bg-raised); border:1px solid var(--border); border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:6px; }
.agent-rank { font-size:10px; font-weight:700; color:var(--accent2); font-family:var(--font-mono); }
.agent-name { font-size:13px; font-weight:600; color:var(--text-primary); }
.agent-bio { font-size:11px; color:var(--text-muted); line-height:1.5; }
.agent-stats { display:flex; gap:8px; flex-wrap:wrap; font-size:11px; color:var(--text-muted); margin-top:4px; }

/* Posts */
.posts-section { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.posts-col { display:flex; flex-direction:column; gap:10px; }
.posts-header { display:flex; align-items:center; gap:10px; margin-bottom:4px; }
.tw-badge { background:rgba(29,161,242,.15); color:#1da1f2; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; }
.rd-badge { background:rgba(255,69,0,.15); color:#ff4500; font-size:11px; font-weight:700; padding:3px 10px; border-radius:20px; }
.posts-subtitle { font-size:12px; color:var(--text-muted); }
.post-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:10px; padding:14px; display:flex; flex-direction:column; gap:8px; transition:border-color .2s; }
.post-card:hover { border-color:var(--border-md); }
.tw-card { border-left:3px solid #1da1f2; }
.rd-card { border-left:3px solid #ff4500; }
.post-author { font-size:12px; font-weight:600; color:var(--text-secondary); }
.post-content { font-size:13px; color:var(--text-primary); line-height:1.6; }
.post-stats { display:flex; gap:12px; font-size:12px; }
.stat-like { color:#f5a623; }
.stat-dis { color:var(--danger); }
.stat-rep { color:var(--text-muted); }

@media (max-width: 1080px) {
  .metrics-grid { grid-template-columns:repeat(2,1fr); }
  .agents-grid  { grid-template-columns:repeat(2,1fr); }
  .posts-section { grid-template-columns:1fr; }
}
</style>
