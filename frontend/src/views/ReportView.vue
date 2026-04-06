<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route  = useRoute()
const router = useRouter()
const report     = ref(null)
const analytics  = ref(null)
const carregando = ref(true)
const erro       = ref('')
// Accordion: qual seção está aberta (null = todas abertas na versão desktop)
const secaoAberta = ref(null)

onMounted(async () => {
  carregando.value = true
  try {
    const rRes = await service.get(`/api/report/${route.params.reportId}`).catch(e => ({ error: e }))
    if (rRes.error) throw rRes.error
    const raw = rRes?.data?.data || rRes?.data || rRes
    report.value = raw
    if (raw?.simulation_id) {
      try {
        const aRes = await service.get(`/api/analytics/${raw.simulation_id}`)
        analytics.value = aRes?.data?.data || aRes?.data || null
      } catch { /* opcional */ }
    }
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar relatório.'
  } finally {
    carregando.value = false
  }
})

// ─── Dados base ───────────────────────────────────────────────
const titulo   = computed(() => report.value?.outline?.title   || 'Relatório de Previsão')
const secoes   = computed(() => report.value?.outline?.sections || [])
const simReq   = computed(() => report.value?.simulation_requirement || '')
const geradoEm = computed(() => {
  const d = report.value?.completed_at || report.value?.created_at
  if (!d) return ''
  return new Date(d).toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric', hour:'2-digit', minute:'2-digit' })
})

// ─── Analytics ────────────────────────────────────────────────
const rounds       = computed(() => analytics.value?.combined?.rounds || [])
const twTotals     = computed(() => analytics.value?.twitter?.totals  || {})
const rdTotals     = computed(() => analytics.value?.reddit?.totals   || {})
const twTopAgents  = computed(() => analytics.value?.twitter?.top_agents || [])
const twEngagement = computed(() => analytics.value?.twitter?.engagement || [])
const totalAcoes   = computed(() => analytics.value?.combined?.total_interactions || 0)
const totalRodadas = computed(() => analytics.value?.combined?.total_rounds || rounds.value.length || 0)
const peakRound    = computed(() => analytics.value?.combined?.peak_round || {})

// ─── PARSERS ─────────────────────────────────────────────────

// 1. Confiança: primeiro número grande no resumo executivo
const confianca = computed(() => {
  const src = (secoes.value[0]?.content || '') + ' ' + (report.value?.outline?.summary || '')
  const m = src.match(/(\d{2,3})\s*%/)
  return m ? Math.min(parseInt(m[1]), 99) : 72
})

// 2. Badges de contagem
const countBadges = computed(() => {
  const s = secoes.value
  return [
    { label: 'Cenários',   val: 3,            color: '#00e5c3', icon: '🔭' },
    { label: 'Riscos',     val: countItems(s[2]?.content, 3, 5),   color: '#f5a623', icon: '⚠️' },
    { label: 'Insights',   val: countItems(s[5]?.content || s[4]?.content, 3, 6), color: '#7c6ff7', icon: '💡' },
    { label: 'Recomend.',  val: countItems(s[7]?.content, 3, 5),   color: '#1da1f2', icon: '🎯' },
  ]
})
function countItems(content, min, max) {
  if (!content) return min
  const bullets = (content.match(/^[-•*]\s/gm) || []).length
  const numbered = (content.match(/^\d+\./gm) || []).length
  const total = bullets + numbered
  return Math.min(Math.max(total || min, min), max)
}

// 3. KPI Cards: extrair métricas das seções
const kpiCards = computed(() => {
  const cards = []
  secoes.value.forEach(s => {
    if (!s.content) return
    // Padrão: **Nome**: valor% ou **Nome**: valor + adjetivo
    const re = /\*\*([^*:]+)\*\*[:\s]+([^.\n,]+(?:%|\d+)[^.\n,]*)/g
    let m
    while ((m = re.exec(s.content)) !== null && cards.length < 5) {
      const label = m[1].trim()
      const valor = m[2].trim().slice(0, 40)
      if (label.length > 3 && label.length < 40 && !label.toLowerCase().includes('seção')) {
        cards.push({ label, valor, trend: trendFrom(valor) })
      }
    }
  })
  // Fallback se não encontrou nada
  if (cards.length === 0) {
    return extractFallbackKPIs()
  }
  return cards.slice(0, 5)
})
function trendFrom(s) {
  if (!s) return 'neutral'
  const low = s.toLowerCase()
  if (low.includes('cresce') || low.includes('alta') || low.includes('aumento') || low.includes('positiv')) return 'up'
  if (low.includes('queda') || low.includes('baixa') || low.includes('reduz') || low.includes('negat')) return 'down'
  return 'neutral'
}
function extractFallbackKPIs() {
  const cards = []
  if (twTotals.value.posts)     cards.push({ label:'Posts Twitter', valor: String(twTotals.value.posts), trend:'up' })
  if (rdTotals.value.posts)     cards.push({ label:'Posts Reddit',  valor: String(rdTotals.value.posts),  trend:'up' })
  if (twTotals.value.likes)     cards.push({ label:'Curtidas',      valor: String(twTotals.value.likes),  trend:'up' })
  if (totalAcoes.value)         cards.push({ label:'Interações',    valor: totalAcoes.value.toLocaleString('pt-BR'), trend:'up' })
  if (totalRodadas.value)       cards.push({ label:'Rodadas',       valor: String(totalRodadas.value),    trend:'neutral' })
  return cards
}

// 4. Cenários com probabilidade
const cenarios = computed(() => {
  const content = secoes.value[1]?.content || ''
  if (!content) return defaultCenarios()

  // Extrair nomes dos cenários (headings ou bold)
  const headings = [...content.matchAll(/(?:###?\s+|^|\n)\*{0,2}(Cenário\s+\w+[^*\n]*)\*{0,2}/gi)]
    .map(m => m[1].trim()).filter(n => n.length > 3).slice(0, 3)

  // Extrair probabilidades (%): pegar os primeiros 3
  const probs = [...content.matchAll(/(\d{1,3})\s*%/g)]
    .map(m => parseInt(m[1])).filter(n => n >= 1 && n <= 100).slice(0, 6)

  const nomes = headings.length >= 3
    ? headings
    : ['Crescimento Sustentável', 'Cenário Base', 'Crise Operacional']

  // Encontrar probabilidades distintas para os 3 cenários
  const ps = probs.length >= 3 ? probs.slice(0, 3) : [70, 20, 10]

  return [
    { nome: nomes[0] || 'Crescimento Sustentável', prob: ps[0], cor:'#00e5c3', impacto:'Alto impacto',  corI:'rgba(0,229,195,0.15)'  },
    { nome: nomes[1] || 'Cenário Base',            prob: ps[1], cor:'#f5a623', impacto:'Médio impacto', corI:'rgba(245,166,35,0.12)' },
    { nome: nomes[2] || 'Crise Operacional',       prob: ps[2], cor:'#ff5a5a', impacto:'Alto impacto',  corI:'rgba(255,90,90,0.12)'  },
  ]
})
function defaultCenarios() {
  return [
    { nome:'Crescimento Sustentável', prob:70, cor:'#00e5c3', impacto:'Alto impacto',  corI:'rgba(0,229,195,0.15)'  },
    { nome:'Estagnação',              prob:20, cor:'#f5a623', impacto:'Médio impacto', corI:'rgba(245,166,35,0.12)' },
    { nome:'Crise Operacional',       prob:10, cor:'#ff5a5a', impacto:'Alto impacto',  corI:'rgba(255,90,90,0.12)'  },
  ]
}

// ─── CHARTS ──────────────────────────────────────────────────

// Gráfico de linha (evolução por rodada)
const chartW = 460; const chartH = 160
const cp = { t:14, r:12, b:28, l:34 }
const lineChart = computed(() => {
  const rds = rounds.value
  if (rds.length < 2) return null
  const maxVal = Math.max(...rds.map(r => r.total), 1)
  const w = chartW - cp.l - cp.r
  const h = chartH - cp.t - cp.b
  const x = i => cp.l + (i / Math.max(rds.length-1,1)) * w
  const y = v => cp.t + h - (v / maxVal) * h
  const path = fn => rds.map((r,i) => `${i===0?'M':'L'}${x(i).toFixed(1)},${y(fn(r)).toFixed(1)}`).join(' ')
  const n = rds.length
  const labels = rds.filter((_,i) => i % Math.max(Math.floor(n/7),1) === 0)
    .map(r => ({ r: r.round, x: x(rds.indexOf(r)) }))
  return {
    tw: path(r=>r.twitter), rd: path(r=>r.reddit), total: path(r=>r.total),
    area: `${path(r=>r.total)} L${x(n-1).toFixed(1)},${(cp.t+h).toFixed(1)} L${cp.l},${(cp.t+h).toFixed(1)} Z`,
    labels, maxVal,
    yLines: [0,.33,.66,1].map(f => ({ val: Math.round(maxVal*f), y: y(maxVal*f) }))
  }
})

// Radar chart (5 eixos)
const radarSize = 90
const radarCenter = { x: 110, y: 110 }
const radarAxes = ['Consenso', 'Engajamento', 'Cobertura', 'Inovação', 'Tensão']

const radarVals = computed(() => {
  const tw = twTotals.value; const rd = rdTotals.value
  const tot = totalAcoes.value || 1
  const maxPosts  = Math.max(tw.posts||0, rd.posts||0, 1)
  const maxLikes  = Math.max(tw.likes||0, 1)
  // Normalizar 0-1
  return [
    Math.min((tw.posts||0) / maxPosts, 1),           // Consenso proxy
    Math.min((tw.likes||0) / Math.max(maxLikes, 1), 1), // Engajamento
    Math.min((rd.posts||0) / maxPosts, 1),            // Cobertura
    Math.min((tw.comments||0) / Math.max(tw.posts||1, 1) / 3, 1), // Inovação
    Math.min(1 - ((tw.posts||0) / maxPosts), 1),      // Tensão (inverso)
  ]
})

function radarPoints(vals, size) {
  return vals.map((v, i) => {
    const angle = (i / vals.length) * 2 * Math.PI - Math.PI / 2
    const r = v * size
    return { x: radarCenter.x + r * Math.cos(angle), y: radarCenter.y + r * Math.sin(angle) }
  })
}
function radarGridPoints(f) {
  return radarAxes.map((_, i) => {
    const angle = (i / radarAxes.length) * 2 * Math.PI - Math.PI / 2
    const r = f * radarSize
    return { x: radarCenter.x + r * Math.cos(angle), y: radarCenter.y + r * Math.sin(angle) }
  })
}
function pts(arr) { return arr.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') }

const radarData = computed(() => ({
  data:   radarPoints(radarVals.value, radarSize),
  grid25: radarGridPoints(0.25),
  grid50: radarGridPoints(0.5),
  grid75: radarGridPoints(0.75),
  grid100: radarGridPoints(1),
  axes: radarAxes.map((label, i) => {
    const angle = (i / radarAxes.length) * 2 * Math.PI - Math.PI / 2
    return {
      label,
      x1: radarCenter.x, y1: radarCenter.y,
      x2: radarCenter.x + radarSize * Math.cos(angle),
      y2: radarCenter.y + radarSize * Math.sin(angle),
      lx: radarCenter.x + (radarSize + 18) * Math.cos(angle),
      ly: radarCenter.y + (radarSize + 18) * Math.sin(angle),
    }
  })
}))

// Gauge path SVG
function gaugePath(pct) {
  const r = 44; const cx = 60; const cy = 65
  const startAngle = Math.PI
  const endAngle   = Math.PI + (pct / 100) * Math.PI
  const sx = cx + r * Math.cos(startAngle)
  const sy = cy + r * Math.sin(startAngle)
  const ex = cx + r * Math.cos(endAngle)
  const ey = cy + r * Math.sin(endAngle)
  const large = pct > 50 ? 1 : 0
  return `M ${sx.toFixed(1)} ${sy.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${ex.toFixed(1)} ${ey.toFixed(1)}`
}

// Markdown renderer
function md(text) {
  if (!text) return ''
  return text
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm,  '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,   '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,    '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,    '<em>$1</em>')
    .replace(/^> (.+)$/gm,    '<blockquote>$1</blockquote>')
    .replace(/^[-•]\s(.+)$/gm,'<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
    .replace(/^\d+\.\s(.+)$/gm,'<li>$1</li>')
    .replace(/\n\n/g,         '</p><p>')
    .replace(/^(?!<)(.+)$/gm, m => `<p>${m}</p>`)
    .replace(/<p><\/p>/g, '')
}

function truncar(t, n=160) { return t?.length > n ? t.slice(0,n)+'...' : (t||'') }

// Accordion
function toggleSecao(idx) {
  secaoAberta.value = secaoAberta.value === idx ? null : idx
}

// Navegar de volta
async function voltar() {
  let pid = report.value?.project_id
  if (!pid && report.value?.simulation_id) {
    try {
      const res = await service.get('/api/simulation/list', { params: { limit: 200 } })
      const lista = res?.data?.data || res?.data || []
      pid = lista.find(s => s.simulation_id === report.value.simulation_id)?.project_id
    } catch { /* ignorar */ }
  }
  router.push(pid ? `/projeto/${pid}` : '/')
}

// Exportar PDF
function exportarPDF() { window.print() }
</script>

<template>
  <AppShell :title="titulo">
    <template #actions>
      <AugurButton variant="ghost" @click="voltar" class="np">← Projeto</AugurButton>
      <AugurButton @click="exportarPDF" class="np">⬇ Exportar PDF</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="loading np">
      <div class="spin"></div>
      <div><div class="ld-t">Carregando relatório...</div><div class="ld-s">Processando análises</div></div>
    </div>

    <!-- Erro -->
    <div v-else-if="erro" class="erro-st np">
      <div style="font-size:48px">⚠️</div>
      <div style="color:var(--danger);font-size:14px">{{ erro }}</div>
      <button class="btn-g" @click="voltar">← Voltar</button>
    </div>

    <div v-else-if="report" class="page">

      <!-- breadcrumb cabeçalho -->
      <div class="page-head np">
        <div class="bc">
          <span class="bc-link" @click="voltar">← Projeto</span>
          <span class="bc-sep">›</span>
          <span class="bc-cur">Relatório</span>
        </div>
        <div class="page-meta">
          <span v-if="geradoEm" class="meta-item">🕐 {{ geradoEm }}</span>
          <span class="meta-item">📊 Análise Preditiva — AUGUR by itcast</span>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- BLOCO 1 — RESUMO EXECUTIVO                    -->
      <!-- ══════════════════════════════════════════════ -->
      <div class="bloco resumo-bloco">
        <div class="bloco-label">RESUMO EXECUTIVO</div>

        <div class="resumo-inner">
          <!-- Gauge de confiança -->
          <div class="gauge-wrap">
            <svg viewBox="0 0 120 80" class="gauge-svg">
              <defs>
                <linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stop-color="#ff5a5a"/>
                  <stop offset="45%" stop-color="#f5a623"/>
                  <stop offset="100%" stop-color="#00e5c3"/>
                </linearGradient>
              </defs>
              <!-- Trilha -->
              <path d="M 16 65 A 44 44 0 0 1 104 65" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" stroke-linecap="round"/>
              <!-- Progresso -->
              <path :d="gaugePath(confianca)" fill="none" stroke="url(#gg)" stroke-width="10" stroke-linecap="round"/>
              <!-- Valor -->
              <text x="60" y="58" text-anchor="middle" font-size="22" font-weight="800" fill="#f0f0f8" font-family="monospace">{{ confianca }}%</text>
              <text x="60" y="74" text-anchor="middle" font-size="9" fill="#6b6b80" letter-spacing="1">CONFIANÇA</text>
            </svg>
          </div>

          <!-- Texto do resumo -->
          <div class="resumo-texto">
            <div v-if="secoes[0]?.content" class="resumo-md md-body" v-html="md(secoes[0].content)"></div>
            <div v-else-if="report?.outline?.summary" class="resumo-md md-body">{{ report.outline.summary }}</div>
            <div v-if="simReq" class="resumo-hip">
              <span class="hip-lbl">Hipótese:</span> {{ truncar(simReq, 200) }}
            </div>
          </div>

          <!-- Badges de contagem -->
          <div class="resumo-badges">
            <div v-for="b in countBadges" :key="b.label" class="count-badge" :style="{'border-color': b.color+'44', background: b.color+'11'}">
              <div class="cb-icon">{{ b.icon }}</div>
              <div class="cb-val" :style="{color: b.color}">{{ b.val }}</div>
              <div class="cb-label">{{ b.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- BLOCO 2 — KPI CARDS                          -->
      <!-- ══════════════════════════════════════════════ -->
      <div v-if="kpiCards.length" class="kpi-row">
        <div v-for="k in kpiCards" :key="k.label" class="kpi-card">
          <div class="kpi-header">
            <div class="kpi-label">{{ k.label }}</div>
            <div class="kpi-trend" :class="k.trend">
              <svg v-if="k.trend==='up'"   viewBox="0 0 10 10" width="10" height="10"><polyline points="1,8 5,2 9,8" fill="none" stroke="#00e5c3" stroke-width="2"/></svg>
              <svg v-else-if="k.trend==='down'" viewBox="0 0 10 10" width="10" height="10"><polyline points="1,2 5,8 9,2" fill="none" stroke="#ff5a5a" stroke-width="2"/></svg>
              <svg v-else viewBox="0 0 10 10" width="10" height="10"><line x1="1" y1="5" x2="9" y2="5" stroke="#6b6b80" stroke-width="2"/></svg>
            </div>
          </div>
          <div class="kpi-valor">{{ k.valor }}</div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- BLOCO 3 — EVOLUÇÃO + RADAR                   -->
      <!-- ══════════════════════════════════════════════ -->
      <div class="bloco-2col" v-if="lineChart || analytics">
        <!-- Linha -->
        <div class="bloco chart-bloco" v-if="lineChart">
          <div class="bloco-label-row">
            <span class="bloco-label-sm">EVOLUÇÃO POR RODADA</span>
            <div class="chart-leg">
              <span style="color:#1da1f2">■ Twitter</span>
              <span style="color:#ff4500">■ Reddit</span>
              <span style="color:#00e5c3">— Total</span>
            </div>
          </div>
          <div class="chart-axis-label">Métricas por rodada</div>
          <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart-svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#00e5c3" stop-opacity="0.18"/>
                <stop offset="100%" stop-color="#00e5c3" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <g v-for="l in lineChart.yLines" :key="l.val">
              <line :x1="cp.l" :y1="l.y" :x2="chartW-cp.r" :y2="l.y" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
              <text :x="cp.l-4" :y="l.y+4" text-anchor="end" fill="rgba(255,255,255,0.3)" font-size="9">{{ l.val }}</text>
            </g>
            <g v-for="lb in lineChart.labels" :key="lb.r">
              <text :x="lb.x" :y="chartH-cp.b+14" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-size="9">R{{ lb.r }}</text>
            </g>
            <path :d="lineChart.area"  fill="url(#ag)" stroke="none"/>
            <path :d="lineChart.tw"    fill="none" stroke="#1da1f2" stroke-width="2"   stroke-linejoin="round"/>
            <path :d="lineChart.rd"    fill="none" stroke="#ff4500" stroke-width="2"   stroke-linejoin="round"/>
            <path :d="lineChart.total" fill="none" stroke="#00e5c3" stroke-width="2.5" stroke-linejoin="round"/>
          </svg>
        </div>

        <!-- Radar -->
        <div class="bloco chart-bloco" v-if="analytics">
          <div class="bloco-label-sm" style="margin-bottom:8px">RADAR DE MÉTRICAS</div>
          <svg viewBox="0 0 220 220" class="radar-svg" preserveAspectRatio="xMidYMid meet">
            <!-- Grids -->
            <polygon :points="pts(radarData.grid100)" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid75)"  fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid50)"  fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid25)"  fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <!-- Eixos -->
            <line v-for="ax in radarData.axes" :key="ax.label"
              :x1="ax.x1" :y1="ax.y1" :x2="ax.x2" :y2="ax.y2"
              stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
            <!-- Labels -->
            <text v-for="ax in radarData.axes" :key="ax.label+'l'"
              :x="ax.lx" :y="ax.ly" text-anchor="middle" dominant-baseline="middle"
              fill="rgba(255,255,255,0.45)" font-size="9">{{ ax.label }}</text>
            <!-- Dados -->
            <polygon :points="pts(radarData.data)"
              fill="rgba(0,229,195,0.15)" stroke="#00e5c3" stroke-width="2"/>
            <!-- Pontos -->
            <circle v-for="(pt,i) in radarData.data" :key="i"
              :cx="pt.x" :cy="pt.y" r="3" fill="#00e5c3"/>
          </svg>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- BLOCO 4 — CENÁRIOS FUTUROS                   -->
      <!-- ══════════════════════════════════════════════ -->
      <div class="bloco" v-if="secoes[1]">
        <div class="bloco-label-row">
          <span class="bloco-label">CENÁRIOS FUTUROS</span>
          <span class="bloco-count">{{ cenarios.length }}</span>
        </div>

        <!-- Barras de probabilidade -->
        <div class="prob-section">
          <div class="prob-title">Probabilidade por cenário</div>
          <div class="prob-bars">
            <div v-for="c in cenarios" :key="c.nome" class="prob-bar-row">
              <div class="pb-label">{{ truncar(c.nome, 24) }}</div>
              <div class="pb-track">
                <div class="pb-fill" :style="{width: c.prob+'%', background: c.cor}"></div>
              </div>
              <div class="pb-pct" :style="{color: c.cor}">{{ c.prob }}%</div>
            </div>
          </div>
        </div>

        <!-- Cards de cenários -->
        <div class="cen-grid">
          <div v-for="c in cenarios" :key="c.nome+'c'" class="cen-card" :style="{borderColor: c.cor+'44', background: c.corI}">
            <div class="cen-top">
              <div class="cen-nome">{{ c.nome }}</div>
              <div class="cen-impacto" :style="{background: c.cor+'22', color: c.cor}">{{ c.impacto }}</div>
            </div>
            <div class="cen-prob-bar">
              <div class="cpb-fill" :style="{width: c.prob+'%', background: c.cor}"></div>
            </div>
            <div class="cen-probval" :style="{color: c.cor}">Probabilidade <strong>{{ c.prob }}%</strong></div>
          </div>
        </div>

        <!-- Conteúdo completo da seção de cenários -->
        <div class="sec-content" v-if="secoes[1].content">
          <div class="md-body" v-html="md(secoes[1].content)"></div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- BLOCOS 5-9 — SEÇÕES RESTANTES (accordion)    -->
      <!-- ══════════════════════════════════════════════ -->
      <div v-for="(s, idx) in secoes.slice(2)" :key="idx+2" class="bloco secao-bloco">
        <button class="secao-toggle" @click="toggleSecao(idx+2)" :class="{ active: secaoAberta === idx+2 }">
          <div class="toggle-left">
            <span class="sec-num">{{ String(idx+3).padStart(2,'0') }}</span>
            <span class="sec-nom">{{ s.title }}</span>
          </div>
          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"
            :style="{transform: secaoAberta===idx+2 ? 'rotate(180deg)' : 'rotate(0deg)', transition:'transform .2s'}">
            <polyline points="2,4 6,8 10,4"/>
          </svg>
        </button>

        <Transition name="drop">
          <div v-show="secaoAberta !== idx+2 || secaoAberta === null" class="sec-body-inner">
            <div v-if="s.content" class="md-body" v-html="md(s.content)"></div>
            <div v-else-if="s.description" class="sec-desc">{{ s.description }}</div>
          </div>
        </Transition>
      </div>

      <!-- ══════════════════════════════════════════════ -->
      <!-- ANALYTICS EXTRA (se disponível)              -->
      <!-- ══════════════════════════════════════════════ -->
      <div v-if="analytics && twTopAgents.length" class="bloco np">
        <div class="bloco-label">TOP AGENTES — ANÁLISE DE INFLUÊNCIA</div>
        <div class="agents-grid">
          <div v-for="(ag,i) in twTopAgents.slice(0,6)" :key="ag.user_id||i" class="agent-card">
            <div class="ag-rank">#{{ i+1 }}</div>
            <div class="ag-nome">{{ ag.name || ag.user_name }}</div>
            <div class="ag-bio">{{ truncar(ag.bio, 70) }}</div>
            <div class="ag-stats">
              <span>📝 {{ ag.posts_count }}</span>
              <span>❤️ {{ ag.total_likes_received }}</span>
              <span>👥 {{ ag.num_followers }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Rodapé -->
      <div class="doc-foot">
        <div>AUGUR by itcast — Documento Confidencial</div>
        <div v-if="geradoEm">{{ geradoEm }}</div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ─── Base ──────────────────────────────────────────────────── */
.loading { display:flex;align-items:center;gap:16px;padding:60px; }
.spin { width:28px;height:28px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .8s linear infinite;flex-shrink:0; }
@keyframes sp { to{transform:rotate(360deg)} }
.ld-t { font-size:15px;font-weight:600;color:var(--text-primary); }
.ld-s { font-size:13px;color:var(--text-muted);margin-top:4px; }
.erro-st { text-align:center;padding:60px;display:flex;flex-direction:column;align-items:center;gap:14px; }
.btn-g { background:none;border:1px solid var(--border);color:var(--text-secondary);border-radius:8px;padding:8px 16px;font-size:13px;cursor:pointer; }
.page { display:flex;flex-direction:column;gap:16px;padding-bottom:40px; }

/* ─── Page head ─────────────────────────────────────────────── */
.page-head { display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;padding-bottom:4px; }
.bc { display:flex;align-items:center;gap:6px;font-size:13px; }
.bc-link { color:var(--accent2);cursor:pointer; }
.bc-link:hover { text-decoration:underline; }
.bc-sep { color:var(--text-muted); }
.bc-cur { color:var(--text-secondary); }
.page-meta { display:flex;gap:14px;font-size:11px;color:var(--text-muted); }
.meta-item { display:flex;align-items:center;gap:5px; }

/* ─── Blocos ─────────────────────────────────────────────────── */
.bloco { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:22px 24px;display:flex;flex-direction:column;gap:16px; }
.bloco-label { font-size:10px;font-weight:700;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase; }
.bloco-label-row { display:flex;align-items:center;justify-content:space-between; }
.bloco-label-sm { font-size:10px;font-weight:700;color:var(--text-muted);letter-spacing:1.2px;text-transform:uppercase; }
.bloco-count { font-size:11px;font-weight:700;color:var(--accent2);background:var(--accent2-dim);border-radius:20px;padding:2px 10px; }

/* ─── Resumo Executivo ──────────────────────────────────────── */
.resumo-bloco { background:linear-gradient(135deg,var(--bg-surface) 0%,rgba(124,111,247,0.04) 100%);border-color:rgba(124,111,247,0.15); }
.resumo-inner { display:grid;grid-template-columns:auto 1fr auto;gap:24px;align-items:start; }
.gauge-wrap { display:flex;flex-direction:column;align-items:center;gap:4px;flex-shrink:0; }
.gauge-svg { width:130px;height:auto; }
.resumo-texto { display:flex;flex-direction:column;gap:10px; }
.resumo-md { font-size:13px;line-height:1.8; }
.resumo-hip { font-size:12px;color:var(--text-muted);background:var(--bg-raised);border-left:3px solid var(--accent2);padding:8px 12px;border-radius:0 6px 6px 0;line-height:1.6; }
.hip-lbl { font-weight:600;color:var(--accent2);margin-right:4px; }
.resumo-badges { display:flex;flex-direction:column;gap:8px;flex-shrink:0; }
.count-badge { border:1px solid;border-radius:10px;padding:10px 14px;display:flex;flex-direction:column;align-items:center;gap:2px;min-width:76px; }
.cb-icon { font-size:16px; }
.cb-val { font-size:22px;font-weight:800;font-family:monospace; }
.cb-label { font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px; }

/* ─── KPI Cards ─────────────────────────────────────────────── */
.kpi-row { display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px; }
.kpi-card { background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:6px;transition:border-color .2s; }
.kpi-card:hover { border-color:var(--border-md); }
.kpi-header { display:flex;align-items:center;justify-content:space-between; }
.kpi-label { font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;font-weight:500; }
.kpi-valor { font-size:18px;font-weight:700;color:var(--text-primary);line-height:1.3;font-family:monospace; }

/* ─── Charts ─────────────────────────────────────────────────── */
.bloco-2col { display:grid;grid-template-columns:60% 40%;gap:12px; }
.chart-bloco { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:20px 22px;display:flex;flex-direction:column;gap:8px; }
.chart-axis-label { font-size:10px;color:var(--text-muted);margin-bottom:2px; }
.chart-leg { display:flex;gap:12px;font-size:11px;font-weight:600; }
.chart-svg { width:100%;height:auto;display:block; }
.radar-svg { width:100%;height:auto;max-width:220px;margin:0 auto;display:block; }

/* ─── Cenários ──────────────────────────────────────────────── */
.prob-section { background:var(--bg-raised);border-radius:10px;padding:16px 20px;display:flex;flex-direction:column;gap:10px; }
.prob-title { font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px;font-weight:500; }
.prob-bars { display:flex;flex-direction:column;gap:8px; }
.prob-bar-row { display:flex;align-items:center;gap:12px; }
.pb-label { font-size:12px;color:var(--text-secondary);min-width:140px;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.pb-track { flex:1;height:8px;background:var(--bg-overlay);border-radius:4px;overflow:hidden; }
.pb-fill { height:100%;border-radius:4px;transition:width .6s ease; }
.pb-pct { font-size:12px;font-weight:700;min-width:36px;text-align:right;font-family:monospace; }

.cen-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:12px; }
.cen-card { border:1px solid;border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:10px; }
.cen-top { display:flex;align-items:flex-start;justify-content:space-between;gap:8px; }
.cen-nome { font-size:14px;font-weight:700;color:var(--text-primary);line-height:1.3; }
.cen-impacto { font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;white-space:nowrap;flex-shrink:0; }
.cen-prob-bar { height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden; }
.cpb-fill { height:100%;border-radius:3px; }
.cen-probval { font-size:12px;color:var(--text-muted); }

.sec-content { border-top:1px solid var(--border);padding-top:16px; }

/* ─── Seções accordion ──────────────────────────────────────── */
.secao-bloco { gap:0;padding:0;overflow:hidden; }
.secao-toggle { width:100%;display:flex;align-items:center;justify-content:space-between;padding:16px 22px;background:none;border:none;cursor:pointer;text-align:left;color:var(--text-primary);transition:background .15s; }
.secao-toggle:hover { background:var(--bg-raised); }
.secao-toggle.active { background:rgba(124,111,247,0.06); }
.toggle-left { display:flex;align-items:center;gap:12px; }
.sec-num { font-size:11px;font-weight:800;color:var(--accent2);background:rgba(124,111,247,0.12);border:1px solid rgba(124,111,247,0.2);padding:3px 9px;border-radius:5px;font-family:monospace;flex-shrink:0; }
.sec-nom { font-size:15px;font-weight:600;color:var(--text-primary); }
.sec-body-inner { padding:4px 22px 20px; }
.sec-desc { color:var(--text-muted);font-size:13px;font-style:italic;padding:8px 0; }

/* ─── Agents ─────────────────────────────────────────────────── */
.agents-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:10px; }
.agent-card { background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:6px; }
.ag-rank { font-size:10px;font-weight:700;color:var(--accent2);font-family:monospace; }
.ag-nome { font-size:13px;font-weight:600;color:var(--text-primary); }
.ag-bio  { font-size:11px;color:var(--text-muted);line-height:1.5; }
.ag-stats { display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:var(--text-muted);margin-top:2px; }

/* ─── Markdown ──────────────────────────────────────────────── */
.md-body { color:var(--text-secondary);font-size:13.5px;line-height:1.88; }
.md-body :deep(h1),.md-body :deep(h2) { font-size:15px;font-weight:700;color:var(--text-primary);margin:18px 0 9px;border-bottom:1px solid var(--border);padding-bottom:5px; }
.md-body :deep(h3),.md-body :deep(h4) { font-size:13px;font-weight:600;color:var(--accent2);margin:14px 0 6px; }
.md-body :deep(strong) { color:var(--text-primary); }
.md-body :deep(em) { color:var(--accent);font-style:normal;font-weight:500; }
.md-body :deep(blockquote) { border-left:3px solid var(--accent2);background:rgba(124,111,247,0.06);padding:9px 14px;margin:12px 0;border-radius:0 8px 8px 0;color:var(--text-secondary);font-style:italic; }
.md-body :deep(ul) { padding-left:20px;margin:9px 0; }
.md-body :deep(li) { margin-bottom:7px; }
.md-body :deep(p) { margin:0 0 12px; }

/* ─── Doc footer ─────────────────────────────────────────────── */
.doc-foot { display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);padding:12px 4px;border-top:1px solid var(--border); }

/* ─── Transition accordion ──────────────────────────────────── */
.drop-enter-active,.drop-leave-active { transition:all .2s ease;overflow:hidden; }
.drop-enter-from,.drop-leave-to { opacity:0;max-height:0; }
.drop-enter-to,.drop-leave-from { opacity:1;max-height:2000px; }

/* ─── PRINT ─────────────────────────────────────────────────── */
@media print {
  * { -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
  .np { display:none !important; }
  @page { size:A4; margin:15mm; }
  .page { gap:14px; }
  .bloco { page-break-inside:avoid;break-inside:avoid; }
  .bloco-2col { grid-template-columns:1fr 1fr; }
  .cen-grid { grid-template-columns:repeat(3,1fr); }
  .resumo-inner { grid-template-columns:auto 1fr auto; }
  .agents-grid { grid-template-columns:repeat(3,1fr); }
  .sec-body-inner { display:block !important; }
  .doc-foot { display:flex !important; }
  /* Cores para branco */
  .bloco,.kpi-card,.chart-bloco,.cen-card,.agent-card,.prob-section { background:#fff !important;border-color:#e0e0ee !important; }
  .md-body { color:#2a2a3e !important; }
  .md-body :deep(*) { color:#2a2a3e !important; }
  .sec-nom,.cb-val,.kpi-valor,.cen-nome { color:#1a1a2e !important; }
  .bloco-label,.bloco-label-sm,.sec-num,.cb-label,.kpi-label,.prob-title { color:#6b6b80 !important; }
  .doc-foot { color:#9898b0 !important;border-color:#e0e0ee !important; }
  .page-head { display:none !important; }
}

/* ─── Responsive ─────────────────────────────────────────────── */
@media (max-width: 1080px) {
  .resumo-inner { grid-template-columns:auto 1fr; }
  .resumo-badges { flex-direction:row;flex-wrap:wrap; }
  .bloco-2col { grid-template-columns:1fr; }
  .cen-grid { grid-template-columns:1fr; }
  .agents-grid { grid-template-columns:repeat(2,1fr); }
}
@media (max-width: 680px) {
  .bloco { padding:16px 16px; }
  .kpi-row { grid-template-columns:repeat(2,1fr); }
  .resumo-inner { grid-template-columns:1fr; }
  .gauge-wrap { width:100%;align-items:center; }
}
</style>
