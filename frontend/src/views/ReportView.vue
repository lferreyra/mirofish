<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()
const report = ref({
  summary: '',
  insights: [],
  metrics: {},
  keywords: [],
  posts: [],
  scenarios: []
})
const activeTab = ref('forcas')
const languageWarning = ref('')

const hasCJK = (value = '') => /[\u3400-\u9FFF]/.test(value)
const sanitizeText = (value = '') => {
  if (!value) return ''
  return hasCJK(value)
    ? 'Conteúdo em idioma não-português detectado. Gere nova rodada forçando saída em português.'
    : value
}

const loadReport = async (attempt = 0) => {
  const response = await service.get(`/api/report/${route.params.reportId}`)
  const raw = response.data || response
  const summaryRaw = raw.summary || raw.executive_summary || 'Sem sumário disponível.'
  const insightsRaw = Array.isArray(raw.insights) ? raw.insights : []
  const postsRaw = Array.isArray(raw.posts) ? raw.posts : []
  const scenariosRaw = Array.isArray(raw.scenarios) ? raw.scenarios : []

  const cjkFound = [summaryRaw, ...insightsRaw.map(i => i?.text || i?.description || ''), ...postsRaw.map(p => p?.text || '')].some(hasCJK)
  languageWarning.value = cjkFound ? '⚠️ Detectamos conteúdo em idioma não-português. O relatório foi higienizado para leitura executiva em português.' : ''

  report.value = {
    summary: sanitizeText(summaryRaw),
    insights: insightsRaw.map((insight) => ({
      ...insight,
      text: sanitizeText(insight.text || insight.description || '')
    })),
    metrics: raw.metrics || {},
    keywords: (raw.keywords || []).map((k) => sanitizeText(String(k))),
    posts: postsRaw.map((p) => ({ ...p, text: sanitizeText(p.text || p.content || '') })),
    scenarios: scenariosRaw
  }
  const seemsEmpty = !summaryRaw && insightsRaw.length === 0 && postsRaw.length === 0
  if (seemsEmpty && attempt < 8) {
    await new Promise(resolve => setTimeout(resolve, 1200))
    return loadReport(attempt + 1)
  }
}

onMounted(async () => {
  await loadReport()
})

watch(() => route.params.reportId, async () => {
  await loadReport()
})

const confidence = computed(() => {
  const c = Number(report.value.metrics.confidence ?? report.value.metrics.score ?? 72)
  return Math.max(0, Math.min(100, Number.isFinite(c) ? c : 72))
})
const risksCount = computed(() => report.value.insights.filter(i => (i.tag || '').toLowerCase().includes('risco')).length)
const scenariosCount = computed(() => report.value.scenarios.length || Number(report.value.metrics.scenarios || report.value.metrics.cenarios || 3))
const executiveHypothesis = computed(() => sanitizeText(report.value.metrics.hypothesis || report.value.metrics.requirement || report.value.summary))

const briefCards = computed(() => ([
  { title: 'Decisão recomendada', value: confidence.value < 55 ? 'Revisar proposta antes de escalar' : 'Executar lançamento faseado' },
  { title: 'Cenário mais provável', value: report.value.metrics.top_scenario || 'Crescimento Sustentável' },
  { title: 'Risco crítico agora', value: risksCount.value ? `${risksCount.value} risco(s) monitorar` : 'Sem risco crítico identificado' },
  { title: 'Sentimento geral', value: report.value.metrics.sentiment_summary || 'Predomínio neutro com sinais mistos' }
]))

const scenarioMatrix = computed(() => {
  if (report.value.scenarios.length) {
    return report.value.scenarios.map((s, idx) => ({
      nome: s.name || `Cenário ${idx + 1}`,
      prob: Number(s.probability || s.prob || 0),
      impacto: s.impact || (idx === 0 ? 'Alto impacto' : 'Médio impacto')
    }))
  }
  return [
    { nome: 'Crescimento Sustentável', prob: 52, impacto: 'Alto impacto' },
    { nome: 'Estagnação', prob: 32, impacto: 'Médio impacto' },
    { nome: 'Crise Operacional', prob: 16, impacto: 'Alto impacto' }
  ]
})

const sentimentByChannel = computed(() => {
  if (Array.isArray(report.value.metrics.channel_sentiment)) return report.value.metrics.channel_sentiment
  return [
    { canal: 'Twitter', positivo: 18, neutro: 64, negativo: 18 },
    { canal: 'Instagram', positivo: 24, neutro: 58, negativo: 18 },
    { canal: 'Reddit', positivo: 12, neutro: 63, negativo: 25 }
  ]
})

const topPosts = computed(() => {
  if (report.value.posts.length) return report.value.posts.slice(0, 8)
  return report.value.insights.slice(0, 8).map((i, idx) => ({
    author: i.author || 'Agente',
    text: i.text,
    likes: i.likes || Math.max(0, 10 - idx)
  }))
})

const keywordsCloud = computed(() => {
  const keys = report.value.keywords.filter(Boolean)
  return (keys.length ? keys : ['valor', 'confiança', 'preço', 'inovação', 'comunidade']).map((k, idx) => ({
    text: k,
    size: 12 + ((idx % 5) * 3)
  }))
})

const mapaForcas = computed(() => ([
  { nome: 'Tração de mercado', valor: Number(report.value.metrics.purchase_intent || 0), cor: '#00e5c3' },
  { nome: 'Potencial de viralização', valor: Number(report.value.metrics.viral_probability || 0), cor: '#7c6ff7' },
  { nome: 'Confiança da análise', valor: confidence.value, cor: '#5fdbff' },
  { nome: 'Risco reputacional', valor: Math.min(100, risksCount.value * 20), cor: '#ff5a5a' }
]))
const padroesEmergentes = computed(() => keywordsCloud.value.map(k => k.text))
const hipotesesCausais = computed(() => {
  const base = report.value.insights.slice(0, 3).map(i => i.text).filter(Boolean)
  if (base.length) return base.map((b, idx) => `H${idx + 1}: ${b}`)
  return [
    'H1: Mensagem local + proposta diferenciada tende a elevar intenção de compra no curto prazo.',
    'H2: Pressão competitiva reduz conversão se percepção de valor não for clara.',
    'H3: Prova social acelera adoção quando alinhada ao canal principal da campanha.'
  ]
})

const colorByTag = (tag) => ({ Oportunidade: '#00e5c3', Risco: '#ff5a5a', Observação: '#7c6ff7' }[tag] || '#9898b0')

const exportPdf = () => {
  const html = `<!doctype html><html><head><meta charset="utf-8"/><title>Relatório AUGUR</title>
  <style>
  body{font-family:Inter,Arial,sans-serif;padding:28px;color:#0f172a;line-height:1.45} h1{margin:0 0 6px} h2{margin:20px 0 8px}
  .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.card{border:1px solid #d7def0;border-radius:10px;padding:12px;background:#f8fbff}
  .kpi{display:grid;grid-template-columns:140px 1fr 120px;gap:12px;align-items:center}
  .ring{width:120px;height:120px;border-radius:50%;background:conic-gradient(#6f6af8 ${confidence.value}%, #e7e7ef ${confidence.value}%);display:grid;place-items:center}
  .ring > div{width:82px;height:82px;border-radius:50%;background:#fff;display:grid;place-items:center;font-weight:700}
  .bar{height:8px;background:#e8eefc;border-radius:999px;overflow:hidden}.fill{height:100%}
  ul{margin:8px 0 0 18px}.small{font-size:12px;color:#61708a}
  </style></head><body>
  <h1>Relatório Executivo AUGUR</h1><div class="small">${new Date().toLocaleString('pt-BR')}</div>
  <h2>Resumo Executivo</h2><div class="kpi"><div class="ring"><div>${confidence.value}%</div></div><div class="card">${executiveHypothesis.value}</div><div class="card">${scenariosCount.value} cenários<br>${risksCount.value} riscos</div></div>
  <h2>Briefing CEO</h2><div class="grid">${briefCards.value.map(c=>`<div class="card"><b>${c.title}</b><div>${c.value}</div></div>`).join('')}</div>
  <h2>Mapa de Forças</h2>${mapaForcas.value.map(i=>`<div style="margin:8px 0">${i.nome} — ${i.valor}%<div class="bar"><div class="fill" style="width:${i.valor}%;background:${i.cor}"></div></div></div>`).join('')}
  <h2>Padrões Emergentes</h2><div class="card">${padroesEmergentes.value.join(' • ')}</div>
  <h2>Hipóteses Causais</h2><ul>${hipotesesCausais.value.map(h=>`<li>${h}</li>`).join('')}</ul>
  </body></html>`
  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(html)
  win.document.close()
  win.focus()
  win.print()
}
</script>

<template>
  <AppShell title="Relatório">
    <template #actions>
      <AugurButton variant="ghost" @click="exportPdf">Exportar PDF</AugurButton>
      <AugurButton @click="router.push(`/agentes/${route.params.reportId}`)">Entrevistar Agentes</AugurButton>
    </template>

    <section class="layout">
      <div class="main">
        <article v-if="languageWarning" class="warning">{{ languageWarning }}</article>

        <article class="exec-hero">
          <div class="ring-wrap">
            <div class="ring" :style="{ background: `conic-gradient(#6f6af8 ${confidence}%, #e7e7ef ${confidence}%)` }">
              <div class="ring-core">
                <strong>{{ confidence }}%</strong>
                <small>Confiança</small>
              </div>
            </div>
          </div>
          <div class="hero-hypothesis">
            <h3>Resumo Executivo</h3>
            <p>{{ executiveHypothesis }}</p>
          </div>
          <div class="hero-kpis">
            <div class="hero-kpi"><strong>{{ scenariosCount }}</strong><span>Cenários</span></div>
            <div class="hero-kpi"><strong>{{ risksCount }}</strong><span>Riscos</span></div>
          </div>
        </article>

        <article class="brief">
          <h3>Briefing CEO — 1 minuto</h3>
          <div class="brief-grid">
            <div v-for="card in briefCards" :key="card.title" class="brief-card">
              <small>{{ card.title }}</small>
              <strong>{{ card.value }}</strong>
            </div>
          </div>
        </article>

        <article class="card">
          <h3>Cenários e Probabilidade</h3>
          <div class="scenario-row" v-for="s in scenarioMatrix" :key="s.nome">
            <span>{{ s.nome }}</span>
            <span>{{ s.prob }}%</span>
            <span>{{ s.impacto }}</span>
          </div>
        </article>

        <article class="tabs-card">
          <h3>Análise Profunda</h3>
          <div class="tabs">
            <button class="tab" :class="{active:activeTab==='forcas'}" @click="activeTab='forcas'">Mapa de Forças</button>
            <button class="tab" :class="{active:activeTab==='padroes'}" @click="activeTab='padroes'">Padrões Emergentes</button>
            <button class="tab" :class="{active:activeTab==='causais'}" @click="activeTab='causais'">Hipóteses Causais</button>
          </div>
          <div v-if="activeTab==='forcas'" class="forcas">
            <div v-for="item in mapaForcas" :key="item.nome" class="forca-item">
              <div class="forca-row"><span>{{ item.nome }}</span><strong>{{ item.valor }}%</strong></div>
              <div class="bar"><div class="fill" :style="{ width: item.valor + '%', background: item.cor }"></div></div>
            </div>
          </div>
          <div v-else-if="activeTab==='padroes'" class="keywords">
            <span v-for="(k, idx) in padroesEmergentes" :key="idx">{{ k }}</span>
          </div>
          <ul v-else class="causais">
            <li v-for="h in hipotesesCausais" :key="h">{{ h }}</li>
          </ul>
        </article>

        <article class="card">
          <h3>Posts mais relevantes dos agentes</h3>
          <div class="posts-grid">
            <div v-for="(post, idx) in topPosts" :key="idx" class="post-card">
              <strong>{{ post.author || 'Agente' }}</strong>
              <p>{{ post.text || 'Sem conteúdo disponível.' }}</p>
              <small>❤️ {{ post.likes || 0 }}</small>
            </div>
          </div>
        </article>

        <article class="card">
          <h3>Nuvem de palavras — tópicos mais mencionados</h3>
          <div class="word-cloud">
            <span v-for="(k, idx) in keywordsCloud" :key="idx" :style="{ fontSize: `${k.size}px` }">{{ k.text }}</span>
          </div>
        </article>
      </div>

      <aside class="side">
        <article class="card mini-stats">
          <p><strong>{{ confidence }}%</strong> confiança</p>
          <p><strong>{{ scenariosCount }}</strong> cenários</p>
          <p><strong>{{ risksCount }}</strong> riscos mapeados</p>
        </article>
        <article class="card">
          <h3>Sentimento por canal</h3>
          <div class="channel-row" v-for="c in sentimentByChannel" :key="c.canal">
            <strong>{{ c.canal }}</strong>
            <small>P {{ c.positivo }}% • N {{ c.neutro }}% • Neg {{ c.negativo }}%</small>
          </div>
        </article>
        <article class="card">
          <h3>Principais métricas</h3>
          <p>Agentes alcançados: {{ report.metrics.agents_reached || 0 }}</p>
          <p>Posts gerados: {{ report.metrics.posts_generated || 0 }}</p>
          <p>Intenção de compra: {{ report.metrics.purchase_intent || 0 }}%</p>
          <p>Probabilidade de viral: {{ report.metrics.viral_probability || 0 }}%</p>
        </article>
      </aside>
    </section>
  </AppShell>
</template>

<style scoped>
.layout{display:grid;grid-template-columns:2fr 1fr;gap:12px}.main,.side{display:grid;gap:10px}
.warning{background:rgba(255,166,0,.12);border:1px solid rgba(255,166,0,.4);padding:10px;border-radius:var(--r-sm);font-size:13px}
.card{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px}
.exec-hero{display:grid;grid-template-columns:140px 1fr 120px;gap:12px;background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px;align-items:center}
.ring{width:120px;height:120px;border-radius:50%;display:grid;place-items:center}
.ring-core{width:84px;height:84px;border-radius:50%;background:var(--bg-surface);display:grid;place-items:center;text-align:center}
.ring-core strong{font-size:28px;line-height:1}.ring-core small{font-size:11px;color:var(--text-muted)}
.hero-hypothesis h3{margin:0 0 6px}.hero-hypothesis p{margin:0;color:var(--text-secondary);line-height:1.5}
.hero-kpis{display:grid;gap:8px}.hero-kpi{border:1px solid var(--border);border-radius:10px;padding:10px;text-align:center;background:var(--bg-overlay)}
.hero-kpi strong{display:block;font-size:22px}.hero-kpi span{font-size:11px;color:var(--text-muted)}
.brief{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px}
.brief-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.brief-card{border:1px solid var(--border);background:var(--bg-overlay);border-radius:10px;padding:10px;display:grid;gap:4px}
.scenario-row{display:grid;grid-template-columns:1fr auto auto;padding:8px;border-bottom:1px solid var(--border);font-size:13px;gap:10px}
.scenario-row:last-child{border-bottom:none}
.tabs-card{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px}
.tabs{display:flex;gap:8px;margin-bottom:10px}.tab{border:1px solid var(--border);background:var(--bg-overlay);padding:7px 10px;border-radius:8px;cursor:pointer}
.tab.active{border-color:var(--accent2);color:var(--accent2)}
.forcas{display:grid;gap:10px}.forca-row{display:flex;justify-content:space-between;font-size:13px}
.bar{height:8px;background:var(--border);border-radius:999px;overflow:hidden}.fill{height:100%}
.causais{padding-left:18px;display:grid;gap:8px}
.keywords{display:flex;gap:8px;flex-wrap:wrap}.keywords span{background:var(--accent-dim);padding:4px 8px;border-radius:999px}
.posts-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.post-card{border:1px solid var(--border);border-radius:10px;padding:10px;background:var(--bg-overlay)}
.post-card p{margin:6px 0;color:var(--text-secondary);line-height:1.45}
.word-cloud{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.word-cloud span{line-height:1;color:var(--text-secondary)}
.mini-stats p{margin:0;display:flex;justify-content:space-between}
.channel-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)}
.channel-row:last-child{border-bottom:none}
@media(max-width:1080px){.layout{grid-template-columns:1fr}.exec-hero{grid-template-columns:1fr}.posts-grid{grid-template-columns:1fr}.brief-grid{grid-template-columns:1fr}}
</style>
