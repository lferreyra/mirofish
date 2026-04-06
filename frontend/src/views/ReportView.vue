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
const posts      = ref([])
const carregando = ref(true)
const erro       = ref('')
const deepTab    = ref(0)

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
      // Carregar posts dos agentes
      try {
        const twPosts = await service.get(`/api/simulation/${raw.simulation_id}/posts`, { params: { platform: 'twitter', limit: 50 } })
        const rdPosts = await service.get(`/api/simulation/${raw.simulation_id}/posts`, { params: { platform: 'reddit', limit: 50 } })
        const tw = (twPosts?.data?.data?.posts || twPosts?.data?.posts || []).map(p => ({ ...p, platform: 'twitter' }))
        const rd = (rdPosts?.data?.data?.posts || rdPosts?.data?.posts || []).map(p => ({ ...p, platform: 'reddit' }))
        posts.value = [...tw, ...rd].sort((a, b) => (b.num_likes || 0) - (a.num_likes || 0))
      } catch { /* posts sao opcionais */ }
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

// ─── Categorizar seções por tipo ──────────────────────────────
function categ(title) {
  const t = (title || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'')
  if (t.includes('resumo')) return 'resumo'
  if (t.includes('cenario')) return 'cenarios'
  if (t.includes('risco')) return 'riscos'
  if (t.includes('recomend')) return 'recomendacoes'
  if (t.includes('previs')) return 'previsoes'
  if (t.includes('insight')) return 'insights'
  if (t.includes('mapa') && t.includes('forca')) return 'deep_mapa'
  if (t.includes('cronolog')) return 'deep_crono'
  if (t.includes('padro')) return 'deep_padroes'
  if (t.includes('hipotes')) return 'deep_hipoteses'
  if (t.includes('anomal')) return 'deep_anomalias'
  if (t.includes('timeline') || t.includes('linha do tempo')) return 'timeline'
  return 'generic'
}

// Seções organizadas por categoria
const secResumo = computed(() => secoes.value.find(s => categ(s.title) === 'resumo') || secoes.value[0])
const secCenarios = computed(() => secoes.value.find(s => categ(s.title) === 'cenarios') || secoes.value[1])
const secRiscos = computed(() => secoes.value.find(s => categ(s.title) === 'riscos'))
const secRecomendacoes = computed(() => secoes.value.find(s => categ(s.title) === 'recomendacoes'))
const secPrevisoes = computed(() => secoes.value.find(s => categ(s.title) === 'previsoes'))
const secInsights = computed(() => secoes.value.find(s => categ(s.title) === 'insights'))

const deepSections = computed(() => {
  const types = ['deep_mapa','deep_crono','deep_padroes','deep_hipoteses','deep_anomalias']
  const icons = ['🏛','📡','🔄','🔬','🧩']
  const labels = ['Mapa de Forças','Cronologia Causal','Padrões Emergentes','Hipóteses Causais','Anomalias']
  const found = []
  secoes.value.forEach(s => {
    const c = categ(s.title)
    const idx = types.indexOf(c)
    if (idx >= 0) found.push({ ...s, icon: icons[idx], label: labels[idx], sortIdx: idx })
  })
  found.sort((a,b) => a.sortIdx - b.sortIdx)
  return found
})

// Seções genéricas (que não foram categorizadas)
const genericSections = computed(() => {
  const knownTypes = ['resumo','cenarios','riscos','recomendacoes','previsoes','insights',
    'deep_mapa','deep_crono','deep_padroes','deep_hipoteses','deep_anomalias','timeline']
  return secoes.value.filter(s => !knownTypes.includes(categ(s.title)))
})

// ─── Analytics ────────────────────────────────────────────────
const rounds       = computed(() => analytics.value?.combined?.rounds || [])
const twTotals     = computed(() => analytics.value?.twitter?.totals  || {})
const rdTotals     = computed(() => analytics.value?.reddit?.totals   || {})
const twTopAgents  = computed(() => analytics.value?.twitter?.top_agents || [])
const totalAcoes   = computed(() => analytics.value?.combined?.total_interactions || 0)
const totalRodadas = computed(() => analytics.value?.combined?.total_rounds || rounds.value.length || 0)

// Posts mais relevantes (top likes)
const topPosts = computed(() => posts.value.slice(0, 8))

// Sentimento por plataforma
const sentimentData = computed(() => {
  if (!posts.value.length) return null
  const tw = posts.value.filter(p => p.platform === 'twitter')
  const rd = posts.value.filter(p => p.platform === 'reddit')
  const calcSentiment = (arr) => {
    const pos = arr.filter(p => (p.num_likes || 0) > (p.num_dislikes || 0)).length
    const neg = arr.filter(p => (p.num_dislikes || 0) > (p.num_likes || 0)).length
    const neu = arr.length - pos - neg
    const total = Math.max(arr.length, 1)
    return { pos: Math.round(pos/total*100), neg: Math.round(neg/total*100), neu: Math.round(neu/total*100), total: arr.length }
  }
  return {
    twitter: calcSentiment(tw),
    reddit: calcSentiment(rd),
    geral: calcSentiment(posts.value)
  }
})

// Nuvem de palavras — extrair keywords dos posts
const wordCloud = computed(() => {
  if (posts.value.length < 3) return []
  const stopwords = new Set(['de','do','da','dos','das','em','no','na','nos','nas','um','uma','uns','umas',
    'o','a','os','as','e','é','ou','que','se','com','por','para','não','mais','como','mas','foi',
    'ser','ter','está','são','tem','sua','seu','isso','este','esta','esse','essa','ao','aos',
    'pelo','pela','já','muito','também','pode','bem','só','ainda','sobre','entre','até','quando',
    'ela','ele','eles','elas','nos','me','meu','minha','seu','sua','the','and','to','of','is','in','it','for','on','that','this','with','are','was','be','has','have','from','or','an','but','not','at','by','as'])
  
  const freq = {}
  posts.value.forEach(p => {
    const text = (p.content || p.text || '').toLowerCase()
    const words = text.replace(/[^\wàáâãéêíóôõúüç\s]/g, '').split(/\s+/)
    words.forEach(w => {
      if (w.length > 3 && !stopwords.has(w) && !/^\d+$/.test(w)) {
        freq[w] = (freq[w] || 0) + 1
      }
    })
  })
  
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30)
    .map(([word, count], i) => ({
      word,
      count,
      size: Math.max(11, Math.min(28, 10 + count * 3)),
      color: ['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50'][i % 7],
      opacity: Math.max(0.5, 1 - i * 0.02)
    }))
})

// Achados Relevantes — extrair pontos-chave do relatório
const achadosRelevantes = computed(() => {
  const achados = []
  const allContent = secoes.value.map(s => s.content || '').join('\n')
  if (!allContent) return []
  
  // Padrões que indicam achados relevantes
  const patterns = [
    /(?:importante|crucial|crítico|significativo|destaque|notável|surpreendente)[\s:]+([^.]+\.)/gi,
    /(?:descobrimos|identificamos|observamos|constatamos|revelou)[\s:]+([^.]+\.)/gi,
    /(?:ponto de inflexão|mudança significativa|virada)[\s:]+([^.]+\.)/gi,
  ]
  
  patterns.forEach(re => {
    let m
    while ((m = re.exec(allContent)) !== null && achados.length < 5) {
      const text = m[1]?.trim() || m[0]?.trim()
      if (text.length > 20 && text.length < 250) {
        achados.push({ text: text.replace(/\*\*/g, ''), tipo: 'achado' })
      }
    }
  })
  
  // Se não encontrou padrões, pegar frases com ** (negrito = destaque)
  if (achados.length < 3) {
    const boldPatterns = [...allContent.matchAll(/\*\*([^*]{15,120})\*\*/g)]
    boldPatterns.slice(0, 5 - achados.length).forEach(m => {
      const text = m[1].trim()
      if (!achados.some(a => a.text.includes(text.slice(0, 20)))) {
        achados.push({ text, tipo: 'destaque' })
      }
    })
  }
  
  return achados.slice(0, 5)
})

// Mapa de calor — sentimento por rodada (usando dados do analytics)
const heatmapData = computed(() => {
  const rds = rounds.value
  if (rds.length < 2) return null
  
  // Usar as métricas disponíveis por rodada
  const metrics = ['twitter', 'reddit', 'total']
  const maxVal = Math.max(...rds.map(r => r.total || 0), 1)
  
  return {
    rounds: rds.map(r => ({
      round: r.round,
      twitter: r.twitter || 0,
      reddit: r.reddit || 0,
      total: r.total || 0,
      intensity: (r.total || 0) / maxVal
    })),
    maxVal
  }
})

// ─── PARSERS ─────────────────────────────────────────────────

// Confiança
const confianca = computed(() => {
  const src = (secResumo.value?.content || '') + ' ' + (report.value?.outline?.summary || '')
  const m = src.match(/(\d{2,3})\s*%/)
  return m ? Math.min(parseInt(m[1]), 99) : 72
})

// Badges de contagem
const countBadges = computed(() => [
  { label:'Cenários',  val: cenarios.value.length,       color:'#00e5c3', icon:'🔭' },
  { label:'Riscos',    val: parsedRiscos.value.length,    color:'#f5a623', icon:'⚠️' },
  { label:'Insights',  val: parsedInsights.value.length,  color:'#7c6ff7', icon:'💡' },
  { label:'Recomend.', val: parsedRecomendacoes.value.length, color:'#1da1f2', icon:'🎯' },
])

// KPI Cards
const kpiCards = computed(() => {
  const cards = []
  secoes.value.forEach(s => {
    if (!s.content) return
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
  if (cards.length === 0) {
    if (twTotals.value.posts) cards.push({ label:'Posts Twitter', valor: String(twTotals.value.posts), trend:'up' })
    if (rdTotals.value.posts) cards.push({ label:'Posts Reddit',  valor: String(rdTotals.value.posts),  trend:'up' })
    if (totalAcoes.value)     cards.push({ label:'Interações',    valor: totalAcoes.value.toLocaleString('pt-BR'), trend:'up' })
    if (totalRodadas.value)   cards.push({ label:'Rodadas',       valor: String(totalRodadas.value),    trend:'neutral' })
  }
  return cards.slice(0, 5)
})
function trendFrom(s) {
  if (!s) return 'neutral'
  const low = s.toLowerCase()
  if (low.includes('cresce') || low.includes('alta') || low.includes('aumento') || low.includes('elev') || low.includes('positiv')) return 'up'
  if (low.includes('queda') || low.includes('baixa') || low.includes('reduz') || low.includes('negat') || low.includes('dimin')) return 'down'
  return 'neutral'
}

// Cenários
const cenarios = computed(() => {
  const content = secCenarios.value?.content || ''
  if (!content) return defaultCenarios()
  const headings = [...content.matchAll(/(?:###?\s+|^|\n)\*{0,2}(Cenário\s+\w+[^*\n]*)\*{0,2}/gi)]
    .map(m => m[1].trim()).filter(n => n.length > 3).slice(0, 3)
  const probs = [...content.matchAll(/(\d{1,3})\s*%/g)]
    .map(m => parseInt(m[1])).filter(n => n >= 1 && n <= 100).slice(0, 6)
  const nomes = headings.length >= 3 ? headings : ['Crescimento Sustentável', 'Cenário Base', 'Crise Operacional']
  const ps = probs.length >= 3 ? probs.slice(0, 3) : [70, 20, 10]
  // Extrair descrições (texto entre cenários)
  const descs = extractCenarioDescriptions(content, nomes)
  return [
    { nome: nomes[0], prob: ps[0], cor:'#00e5c3', impacto:'Alto impacto',  corI:'rgba(0,229,195,0.08)', desc: descs[0] },
    { nome: nomes[1], prob: ps[1], cor:'#f5a623', impacto:'Médio impacto', corI:'rgba(245,166,35,0.08)', desc: descs[1] },
    { nome: nomes[2], prob: ps[2], cor:'#ff5a5a', impacto:'Alto impacto',  corI:'rgba(255,90,90,0.08)',  desc: descs[2] },
  ]
})
function defaultCenarios() {
  return [
    { nome:'Crescimento Sustentável', prob:70, cor:'#00e5c3', impacto:'Alto impacto',  corI:'rgba(0,229,195,0.08)', desc:'' },
    { nome:'Estagnação',              prob:20, cor:'#f5a623', impacto:'Médio impacto', corI:'rgba(245,166,35,0.08)', desc:'' },
    { nome:'Crise Operacional',       prob:10, cor:'#ff5a5a', impacto:'Alto impacto',  corI:'rgba(255,90,90,0.08)',  desc:'' },
  ]
}
function extractCenarioDescriptions(content, nomes) {
  const descs = ['','','']
  // Split content by scenario headings and grab text between
  for (let i = 0; i < nomes.length; i++) {
    const escapedName = nomes[i].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(escapedName + '[^\\n]*\\n([\\s\\S]*?)(?=(?:Cenário|$))', 'i')
    const m = content.match(re)
    if (m) {
      // Limpar markdown e pegar primeiras 2 frases
      let txt = m[1].replace(/\*\*/g,'').replace(/^[-•*#]+\s/gm,'').replace(/\n+/g,' ').trim()
      // Remove probability line
      txt = txt.replace(/\d{1,3}\s*%\s*(de\s+)?probabilidade/gi, '').trim()
      // Pegar até 200 chars
      descs[i] = txt.slice(0, 200).replace(/\s+\S*$/, '') + (txt.length > 200 ? '...' : '')
    }
  }
  return descs
}

// Riscos parser
const parsedRiscos = computed(() => {
  const content = secRiscos.value?.content || ''
  if (!content) return []
  const risks = []
  // Pattern: **Nome do Risco** seguido de descrição, probabilidade%, impacto
  const blocks = content.split(/(?=\*\*[^*]+\*\*)/).filter(b => b.trim())
  for (const block of blocks) {
    const nameMatch = block.match(/\*\*([^*]+)\*\*/)
    if (!nameMatch) continue
    const name = nameMatch[1].trim()
    if (name.length < 5 || name.length > 80) continue
    const probMatch = block.match(/(\d{1,3})\s*%/)
    const prob = probMatch ? parseInt(probMatch[1]) : null
    const impMatch = block.match(/\b(alto|médio|medio|baixo)\b/i)
    const impacto = impMatch ? impMatch[1].charAt(0).toUpperCase() + impMatch[1].slice(1).toLowerCase() : 'Médio'
    const desc = block.replace(/\*\*[^*]+\*\*/,'').replace(/\d{1,3}\s*%/,'').replace(/\b(alto|médio|medio|baixo)\b/gi,'')
      .replace(/[-•*]\s/g,'').replace(/\n+/g,' ').trim().slice(0, 200)
    if (name.toLowerCase().includes('risco') || name.toLowerCase().includes('fator') || prob || risks.length < 5) {
      risks.push({ name, desc, prob: prob || 30, impacto: impacto.replace('Medio','Médio'), color: impacto.toLowerCase().includes('alt') ? '#ff5a5a' : '#f5a623' })
    }
    if (risks.length >= 5) break
  }
  return risks.length ? risks : fallbackItems(content, 3, 5)
})

// Recomendações parser
const parsedRecomendacoes = computed(() => {
  const content = secRecomendacoes.value?.content || ''
  if (!content) return []
  const recs = []
  const blocks = content.split(/(?=\*\*[^*]+\*\*|\d+\.\s)/).filter(b => b.trim())
  for (const block of blocks) {
    const nameMatch = block.match(/\*\*([^*]+)\*\*/) || block.match(/\d+\.\s+(.+?)(?:\n|$)/)
    if (!nameMatch) continue
    const name = nameMatch[1].trim()
    if (name.length < 5 || name.length > 100) continue
    const urgMatch = block.match(/\b(urgente|alta|média|media|baixa)\b/i)
    const urgencia = urgMatch ? urgMatch[1].charAt(0).toUpperCase() + urgMatch[1].slice(1).toLowerCase() : null
    const prazoMatch = block.match(/(?:prazo|próximos?)\s*:?\s*([^\n.]+)/i)
    const prazo = prazoMatch ? prazoMatch[1].trim().slice(0, 40) : null
    const desc = block.replace(/\*\*[^*]+\*\*/,'').replace(/\d+\.\s/,'')
      .replace(/\b(urgente|alta|média|media|baixa)\b/gi,'').replace(/[-•*]\s/g,'')
      .replace(/\n+/g,' ').trim().slice(0, 250)
    recs.push({
      name, desc, urgencia: urgencia?.replace('Media','Média'),
      prazo: prazo || 'Próximos 3 meses',
      urgColor: urgencia?.toLowerCase() === 'urgente' ? '#ff5a5a' : urgencia?.toLowerCase() === 'alta' ? '#f5a623' : '#00e5c3'
    })
    if (recs.length >= 5) break
  }
  return recs
})

// Previsões parser
const parsedPrevisoes = computed(() => {
  const content = secPrevisoes.value?.content || ''
  if (!content) return []
  const preds = []
  // Split by numbered items or bold items
  const items = content.split(/(?=\d+\.\s|\*\*[^*]+\*\*)/).filter(b => b.trim().length > 20)
  for (const item of items) {
    const text = item.replace(/\*\*/g,'').replace(/\d+\.\s/,'').replace(/[-•]\s/g,'').replace(/\n+/g,' ').trim()
    if (text.length > 20) {
      preds.push({ text: text.slice(0, 250) + (text.length > 250 ? '...' : '') })
    }
    if (preds.length >= 4) break
  }
  return preds
})

// Insights parser
const parsedInsights = computed(() => {
  const content = secInsights.value?.content || ''
  if (!content) return []
  const items = []
  const parts = content.split(/(?=\d+\.\s|\*\*[^*]+\*\*|^[-•]\s)/m).filter(b => b.trim().length > 15)
  for (const part of parts) {
    const text = part.replace(/\*\*/g,'').replace(/\d+\.\s/,'').replace(/^[-•]\s/,'').replace(/\n+/g,' ').trim()
    if (text.length > 15) {
      items.push({ text: text.slice(0, 220) + (text.length > 220 ? '...' : '') })
    }
    if (items.length >= 6) break
  }
  return items
})

// Timeline parser
const parsedTimeline = computed(() => {
  const sec = secoes.value.find(s => categ(s.title) === 'timeline')
  const content = sec?.content || secPrevisoes.value?.content || ''
  if (!content) return []
  const events = []
  // Look for date patterns followed by descriptions
  const dateBlocks = content.split(/(?=(?:Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|Até|Em)\s)/i)
  for (const block of dateBlocks) {
    const dateMatch = block.match(/^((?:Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|Até|Em)[^\n.]+)/i)
    if (!dateMatch) continue
    const date = dateMatch[1].trim().slice(0, 60)
    const rest = block.slice(dateMatch[0].length).replace(/\*\*/g,'').replace(/\n+/g,' ').trim()
    const probMatch = rest.match(/(\d{1,3})\s*%/)
    const prob = probMatch ? parseInt(probMatch[1]) : null
    const desc = rest.replace(/\d{1,3}\s*%\s*(de\s+)?probabilidade/gi,'').trim().slice(0, 200)
    if (desc.length > 10) {
      events.push({ date, desc, prob })
    }
    if (events.length >= 5) break
  }
  return events
})

// Hipóteses confidence badges
const hipotesesBadges = computed(() => {
  const sec = deepSections.value.find(s => categ(s.title || s.label) === 'deep_hipoteses')
  if (!sec?.content) return []
  const badges = []
  const matches = [...sec.content.matchAll(/confiança\s*:?\s*(alta|média|media|baixa)/gi)]
  for (const m of matches) {
    const val = m[1].charAt(0).toUpperCase() + m[1].slice(1).toLowerCase()
    badges.push({ label: val.replace('Media','Média'), color: val.toLowerCase().includes('alt') ? '#00e5c3' : val.toLowerCase().includes('méd') || val.toLowerCase().includes('med') ? '#f5a623' : '#ff5a5a' })
  }
  return badges
})

function fallbackItems(content, min, max) {
  const items = []
  const parts = content.split(/\n\n+/).filter(p => p.trim().length > 20)
  for (const p of parts.slice(0, max)) {
    items.push({ name: p.slice(0, 50), desc: p.slice(50, 200), prob: 30, impacto: 'Médio', color: '#f5a623' })
  }
  return items.slice(0, Math.max(min, items.length))
}

// ─── CHARTS ──────────────────────────────────────────────────
const chartW = 460; const chartH = 160
const cp = { t:14, r:12, b:28, l:34 }
const lineChart = computed(() => {
  const rds = rounds.value
  if (rds.length < 2) return null
  const maxVal = Math.max(...rds.map(r => r.total), 1)
  const w = chartW - cp.l - cp.r; const h = chartH - cp.t - cp.b
  const x = i => cp.l + (i / Math.max(rds.length-1,1)) * w
  const y = v => cp.t + h - (v / maxVal) * h
  const path = fn => rds.map((r,i) => `${i===0?'M':'L'}${x(i).toFixed(1)},${y(fn(r)).toFixed(1)}`).join(' ')
  const n = rds.length
  const labels = rds.filter((_,i) => i % Math.max(Math.floor(n/7),1) === 0).map(r => ({ r: r.round, x: x(rds.indexOf(r)) }))
  return {
    tw: path(r=>r.twitter), rd: path(r=>r.reddit), total: path(r=>r.total),
    area: `${path(r=>r.total)} L${x(n-1).toFixed(1)},${(cp.t+h).toFixed(1)} L${cp.l},${(cp.t+h).toFixed(1)} Z`,
    labels, maxVal, yLines: [0,.33,.66,1].map(f => ({ val: Math.round(maxVal*f), y: y(maxVal*f) }))
  }
})

const radarSize = 90; const radarCenter = { x: 110, y: 110 }
const radarAxes = computed(() => {
  const r = rounds.value
  if (!r.length) return ['Consenso','Engajamento','Cobertura','Inovação','Tensão']
  // Use real metric names from analytics if available
  return Object.keys(r[0] || {}).filter(k => !['round','total','twitter','reddit'].includes(k)).slice(0,5)
    .map(k => k.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase()))
    .concat(['Consenso','Engajamento','Cobertura','Inovação','Tensão']).slice(0,5)
})
const radarVals = computed(() => {
  const tw = twTotals.value; const rd = rdTotals.value
  const maxPosts = Math.max(tw.posts||0, rd.posts||0, 1)
  const maxLikes = Math.max(tw.likes||0, 1)
  return [
    Math.min((tw.posts||0) / maxPosts, 1),
    Math.min((tw.likes||0) / maxLikes, 1),
    Math.min((rd.posts||0) / maxPosts, 1),
    Math.min((tw.comments||0) / Math.max(tw.posts||1,1) / 3, 1),
    Math.min(1 - ((tw.posts||0) / maxPosts), 1),
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
  return radarAxes.value.map((_, i) => {
    const angle = (i / radarAxes.value.length) * 2 * Math.PI - Math.PI / 2
    return { x: radarCenter.x + f * radarSize * Math.cos(angle), y: radarCenter.y + f * radarSize * Math.sin(angle) }
  })
}
function pts(arr) { return arr.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') }
const radarData = computed(() => ({
  data: radarPoints(radarVals.value, radarSize),
  grid25: radarGridPoints(0.25), grid50: radarGridPoints(0.5),
  grid75: radarGridPoints(0.75), grid100: radarGridPoints(1),
  axes: radarAxes.value.map((label, i) => {
    const angle = (i / radarAxes.value.length) * 2 * Math.PI - Math.PI / 2
    return { label, x1:radarCenter.x, y1:radarCenter.y,
      x2:radarCenter.x+radarSize*Math.cos(angle), y2:radarCenter.y+radarSize*Math.sin(angle),
      lx:radarCenter.x+(radarSize+18)*Math.cos(angle), ly:radarCenter.y+(radarSize+18)*Math.sin(angle) }
  })
}))

function gaugePath(pct) {
  const r=44, cx=60, cy=65, sa=Math.PI, ea=Math.PI+(pct/100)*Math.PI
  const sx=cx+r*Math.cos(sa), sy=cy+r*Math.sin(sa), ex=cx+r*Math.cos(ea), ey=cy+r*Math.sin(ea)
  return `M ${sx.toFixed(1)} ${sy.toFixed(1)} A ${r} ${r} 0 ${pct>50?1:0} 1 ${ex.toFixed(1)} ${ey.toFixed(1)}`
}

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
    .replace(/\n\n/g,'</p><p>')
    .replace(/^(?!<)(.+)$/gm, m => `<p>${m}</p>`)
    .replace(/<p><\/p>/g, '')
}
function truncar(t, n=160) { return t?.length > n ? t.slice(0,n)+'...' : (t||'') }

async function voltar() {
  let pid = report.value?.project_id
  if (!pid && report.value?.simulation_id) {
    try {
      const res = await service.get('/api/simulation/list', { params: { limit: 200 } })
      const lista = res?.data?.data || res?.data || []
      pid = lista.find(s => s.simulation_id === report.value.simulation_id)?.project_id
    } catch {}
  }
  router.push(pid ? `/projeto/${pid}` : '/')
}
const gerandoPDF = ref(false)
const pageRef = ref(null)

async function exportarPDF() {
  gerandoPDF.value = true
  
  try {
    // Carregar html2pdf.js do CDN
    if (!window.html2pdf) {
      await new Promise((resolve, reject) => {
        const s = document.createElement('script')
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js'
        s.onload = resolve
        s.onerror = reject
        document.head.appendChild(s)
      })
    }
    
    // Expandir TODA a analise profunda antes de capturar
    const prevTab = deepTab.value
    const el = pageRef.value
    if (!el) return
    
    // Criar clone para nao alterar a tela
    const clone = el.cloneNode(true)
    
    // No clone: mostrar TODAS as deep sections, esconder tabs
    clone.querySelectorAll('.deep-tabs').forEach(t => t.style.display = 'none')
    clone.querySelectorAll('.deep-content').forEach(c => c.style.display = 'none')
    clone.querySelectorAll('.deep-print-all').forEach(p => p.style.display = 'block')
    // Expandir accordions
    clone.querySelectorAll('.sec-body-inner').forEach(s => s.style.display = 'block')
    // Esconder botoes e CTA
    clone.querySelectorAll('.np').forEach(n => n.style.display = 'none')
    // Mostrar print-header
    const ph = clone.querySelector('.print-header')
    if (ph) ph.style.display = 'block'
    
    // Aplicar estilos de impressao
    clone.style.background = '#ffffff'
    clone.style.color = '#1a1a2e'
    clone.style.padding = '20px'
    clone.querySelectorAll('.bloco, .kpi-card, .chart-bloco, .cen-card, .risk-card, .rec-card, .insight-card, .pred-card, .sent-card, .post-card, .achado-card').forEach(b => {
      b.style.background = '#ffffff'
      b.style.borderColor = '#e0e0ee'
      b.style.color = '#2a2a3e'
    })
    clone.querySelectorAll('.bloco-label, .bloco-label-sm, .kpi-label, .prob-title').forEach(l => {
      l.style.color = '#6b6b80'
    })
    clone.querySelectorAll('.md-body, .cen-desc, .risk-desc, .rec-desc, .insight-text, .pred-text, .tl-desc, .post-content, .sent-label').forEach(t => {
      t.style.color = '#3a3a4e'
    })
    clone.querySelectorAll('.sec-nom, .cb-val, .kpi-valor, .cen-nome, .risk-name, .rec-name').forEach(t => {
      t.style.color = '#1a1a2e'
    })
    clone.querySelectorAll('.deep-print-header').forEach(h => {
      h.style.color = '#7c6ff7'
      h.style.borderBottom = '2px solid #7c6ff7'
      h.style.paddingBottom = '6px'
      h.style.marginBottom = '12px'
      h.style.fontSize = '16px'
      h.style.fontWeight = '700'
    })
    // Timeline fix
    clone.querySelectorAll('.timeline').forEach(t => t.style.borderLeftColor = '#ccc')
    clone.querySelectorAll('.tl-dot').forEach(d => { d.style.borderColor = '#7c6ff7'; d.style.background = '#fff' })
    
    // Montar temporariamente no DOM (invisivel)
    const wrapper = document.createElement('div')
    wrapper.style.position = 'fixed'
    wrapper.style.left = '-9999px'
    wrapper.style.top = '0'
    wrapper.style.width = '210mm'
    wrapper.appendChild(clone)
    document.body.appendChild(wrapper)
    
    const nomeArquivo = (titulo.value || 'Relatorio-AUGUR')
      .replace(/[^a-zA-Z0-9À-ú\s-]/g, '')
      .replace(/\s+/g, '_')
      .slice(0, 60)
    
    await window.html2pdf()
      .set({
        margin: [10, 12, 10, 12],
        filename: `${nomeArquivo}.pdf`,
        image: { type: 'jpeg', quality: 0.95 },
        html2canvas: { 
          scale: 2, 
          useCORS: true, 
          letterRendering: true,
          scrollY: 0,
          windowWidth: 800
        },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .from(clone)
      .save()
    
    document.body.removeChild(wrapper)
    
  } catch (e) {
    console.error('Erro ao gerar PDF:', e)
    alert('Erro ao gerar PDF. Tente novamente.')
  } finally {
    gerandoPDF.value = false
  }
}
function abrirChat() {
  // Navigate to interaction/chat view if available
  const rid = route.params.reportId
  router.push(`/agentes/${rid}`)
}
</script>

<template>
  <AppShell :title="titulo">
    <template #actions>
      <AugurButton variant="ghost" @click="voltar" class="np">← Projeto</AugurButton>
      <AugurButton @click="exportarPDF" :disabled="gerandoPDF" class="np">
        <span v-if="gerandoPDF">⏳ Gerando PDF...</span>
        <span v-else>⬇ Exportar PDF</span>
      </AugurButton>
    </template>

    <div v-if="carregando" class="loading np">
      <div class="spin"></div>
      <div><div class="ld-t">Carregando relatório...</div><div class="ld-s">Processando análises</div></div>
    </div>

    <div v-else-if="erro" class="erro-st np">
      <div style="font-size:48px">⚠️</div>
      <div style="color:var(--danger);font-size:14px">{{ erro }}</div>
      <button class="btn-g" @click="voltar">← Voltar</button>
    </div>

    <div v-else-if="report" ref="pageRef" class="page">

      <!-- Print-only header -->
      <div class="print-header">
        <div class="print-logo">AUGUR</div>
        <div class="print-title">{{ titulo }}</div>
        <div class="print-meta">
          <span v-if="geradoEm">{{ geradoEm }}</span>
          <span>Análise Preditiva — AUGUR by itcast</span>
        </div>
      </div>

      <!-- Breadcrumb -->
      <div class="page-head np">
        <div class="bc">
          <span class="bc-link" @click="voltar">← Projeto</span>
          <span class="bc-sep">›</span>
          <span class="bc-cur">Relatório</span>
        </div>
        <div class="page-meta">
          <span class="meta-item" v-if="geradoEm">🕐 {{ geradoEm }}</span>
          <span class="meta-item">📊 Análise Preditiva — AUGUR by itcast</span>
        </div>
      </div>

      <!-- ══════════ 1. RESUMO EXECUTIVO ══════════ -->
      <div class="bloco resumo-bloco">
        <div class="bloco-label">RESUMO EXECUTIVO</div>
        <div class="resumo-inner">
          <div class="gauge-wrap">
            <svg viewBox="0 0 120 80" class="gauge-svg">
              <path d="M 16 65 A 44 44 0 0 1 104 65" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="8" stroke-linecap="round"/>
              <path :d="gaugePath(confianca)" fill="none" stroke="url(#gaugeGrad)" stroke-width="8" stroke-linecap="round"/>
              <defs><linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7c6ff7"/><stop offset="100%" stop-color="#00e5c3"/></linearGradient></defs>
              <text x="60" y="56" text-anchor="middle" fill="var(--text-primary)" font-size="24" font-weight="800">{{ confianca }}%</text>
              <text x="60" y="72" text-anchor="middle" fill="var(--text-muted)" font-size="8" font-weight="600" letter-spacing="1">CONFIANÇA</text>
            </svg>
          </div>

          <div class="resumo-texto">
            <div v-if="secResumo?.content" class="resumo-md md-body" v-html="md(secResumo.content)"></div>
            <div v-if="simReq" class="resumo-hip">
              <span class="hip-lbl">Hipótese:</span> {{ truncar(simReq, 250) }}
            </div>
          </div>

          <div class="resumo-badges">
            <div v-for="b in countBadges" :key="b.label" class="count-badge" :style="{borderColor: b.color+'44'}">
              <div class="cb-icon">{{ b.icon }}</div>
              <div class="cb-val" :style="{color: b.color}">{{ b.val }}</div>
              <div class="cb-label">{{ b.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ 2. KPI CARDS ══════════ -->
      <div v-if="kpiCards.length" class="kpi-row">
        <div v-for="k in kpiCards" :key="k.label" class="kpi-card">
          <div class="kpi-header">
            <div class="kpi-label">{{ k.label }}</div>
            <svg v-if="k.trend==='up'" viewBox="0 0 10 10" width="10" height="10"><polyline points="1,8 5,2 9,8" fill="none" stroke="#00e5c3" stroke-width="2"/></svg>
            <svg v-else-if="k.trend==='down'" viewBox="0 0 10 10" width="10" height="10"><polyline points="1,2 5,8 9,2" fill="none" stroke="#ff5a5a" stroke-width="2"/></svg>
            <svg v-else viewBox="0 0 10 10" width="10" height="10"><line x1="1" y1="5" x2="9" y2="5" stroke="#6b6b80" stroke-width="2"/></svg>
          </div>
          <div class="kpi-valor">{{ k.valor }}</div>
        </div>
      </div>

      <!-- ══════════ 3. EVOLUÇÃO + RADAR ══════════ -->
      <div class="bloco-2col" v-if="lineChart || analytics">
        <div class="bloco chart-bloco" v-if="lineChart">
          <div class="bloco-label-row">
            <span class="bloco-label-sm">Evolução da Simulação</span>
            <div class="chart-leg">
              <span style="color:#1da1f2">■ Twitter</span>
              <span style="color:#ff4500">■ Reddit</span>
              <span style="color:#00e5c3">— Total</span>
            </div>
          </div>
          <div class="chart-axis-label">Métricas por rodada</div>
          <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart-svg" preserveAspectRatio="xMidYMid meet">
            <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00e5c3" stop-opacity="0.18"/><stop offset="100%" stop-color="#00e5c3" stop-opacity="0"/></linearGradient></defs>
            <g v-for="l in lineChart.yLines" :key="l.val"><line :x1="cp.l" :y1="l.y" :x2="chartW-cp.r" :y2="l.y" stroke="rgba(255,255,255,0.06)" stroke-width="1"/><text :x="cp.l-4" :y="l.y+4" text-anchor="end" fill="rgba(255,255,255,0.3)" font-size="9">{{ l.val }}</text></g>
            <g v-for="lb in lineChart.labels" :key="lb.r"><text :x="lb.x" :y="chartH-cp.b+14" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-size="9">R{{ lb.r }}</text></g>
            <path :d="lineChart.area" fill="url(#ag)" stroke="none"/>
            <path :d="lineChart.tw" fill="none" stroke="#1da1f2" stroke-width="2" stroke-linejoin="round"/>
            <path :d="lineChart.rd" fill="none" stroke="#ff4500" stroke-width="2" stroke-linejoin="round"/>
            <path :d="lineChart.total" fill="none" stroke="#00e5c3" stroke-width="2.5" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="bloco chart-bloco" v-if="analytics">
          <div class="bloco-label-sm" style="margin-bottom:8px">Radar de métricas</div>
          <svg viewBox="0 0 220 220" class="radar-svg" preserveAspectRatio="xMidYMid meet">
            <polygon :points="pts(radarData.grid100)" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid75)" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid50)" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
            <polygon :points="pts(radarData.grid25)" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line v-for="ax in radarData.axes" :key="ax.label" :x1="ax.x1" :y1="ax.y1" :x2="ax.x2" :y2="ax.y2" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>
            <text v-for="ax in radarData.axes" :key="ax.label+'l'" :x="ax.lx" :y="ax.ly" text-anchor="middle" dominant-baseline="middle" fill="rgba(255,255,255,0.45)" font-size="9">{{ ax.label }}</text>
            <polygon :points="pts(radarData.data)" fill="rgba(0,229,195,0.15)" stroke="#00e5c3" stroke-width="2"/>
            <circle v-for="(pt,i) in radarData.data" :key="i" :cx="pt.x" :cy="pt.y" r="3" fill="#00e5c3"/>
          </svg>
        </div>
      </div>

      <!-- ══════════ 4. CENÁRIOS FUTUROS ══════════ -->
      <div class="bloco" v-if="secCenarios">
        <div class="bloco-label-row">
          <span class="bloco-label">🔭 Cenários Futuros</span>
          <span class="bloco-count">{{ cenarios.length }}</span>
        </div>
        <div class="prob-section">
          <div class="prob-title">Probabilidade por cenário</div>
          <div class="prob-bars">
            <div v-for="c in cenarios" :key="c.nome" class="prob-bar-row">
              <div class="pb-label">{{ truncar(c.nome, 24) }}</div>
              <div class="pb-track"><div class="pb-fill" :style="{width: c.prob+'%', background: c.cor}"></div></div>
              <div class="pb-pct" :style="{color: c.cor}">{{ c.prob }}%</div>
            </div>
          </div>
        </div>
        <div class="cen-grid">
          <div v-for="c in cenarios" :key="c.nome" class="cen-card" :style="{borderColor: c.cor+'44', background: c.corI}">
            <div class="cen-top">
              <div class="cen-nome">{{ c.nome }}</div>
              <div class="cen-impacto" :style="{background: c.cor+'22', color: c.cor}">{{ c.impacto }}</div>
            </div>
            <div v-if="c.desc" class="cen-desc">{{ c.desc }}</div>
            <div class="cen-prob-bar"><div class="cpb-fill" :style="{width: c.prob+'%', background: c.cor}"></div></div>
            <div class="cen-probval" :style="{color: c.cor}">Probabilidade <strong>{{ c.prob }}%</strong></div>
          </div>
        </div>
      </div>

      <!-- ══════════ 5. INSIGHTS PRINCIPAIS ══════════ -->
      <div class="bloco" v-if="parsedInsights.length">
        <div class="bloco-label-row">
          <span class="bloco-label">💡 Insights Principais</span>
          <span class="bloco-count">{{ parsedInsights.length }}</span>
        </div>
        <div class="insights-grid">
          <div v-for="(ins, i) in parsedInsights" :key="i" class="insight-card">
            <div class="insight-num" :style="{background: i%2===0 ? 'rgba(124,111,247,0.15)' : 'rgba(0,229,195,0.15)', color: i%2===0 ? '#7c6ff7' : '#00e5c3'}">{{ i + 1 }}</div>
            <div class="insight-text">{{ ins.text }}</div>
          </div>
        </div>
      </div>

      <!-- ══════════ 6. FATORES DE RISCO ══════════ -->
      <div class="bloco" v-if="parsedRiscos.length">
        <div class="bloco-label-row">
          <span class="bloco-label">⚠️ Fatores de Risco</span>
          <span class="bloco-count">{{ parsedRiscos.length }}</span>
        </div>
        <div class="risk-list">
          <div v-for="(r, i) in parsedRiscos" :key="i" class="risk-card">
            <div class="risk-top">
              <div class="risk-name">{{ r.name }}</div>
              <div class="risk-badge" :style="{background: r.color+'22', color: r.color}">{{ r.impacto }}</div>
            </div>
            <div class="risk-desc" v-if="r.desc">{{ r.desc }}</div>
            <div class="risk-prob-row">
              <span class="risk-prob-label">Probabilidade de ocorrência</span>
              <div class="risk-prob-track"><div class="risk-prob-fill" :style="{width: r.prob+'%', background: r.color}"></div></div>
              <span class="risk-prob-pct" :style="{color: r.color}">{{ r.prob }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ 7. RECOMENDAÇÕES ESTRATÉGICAS ══════════ -->
      <div class="bloco" v-if="parsedRecomendacoes.length">
        <div class="bloco-label-row">
          <span class="bloco-label">🎯 Recomendações Estratégicas</span>
          <span class="bloco-count">{{ parsedRecomendacoes.length }}</span>
        </div>
        <div class="rec-list">
          <div v-for="(r, i) in parsedRecomendacoes" :key="i" class="rec-card">
            <div class="rec-num">{{ i + 1 }}</div>
            <div class="rec-body">
              <div class="rec-top">
                <div class="rec-name">{{ r.name }}</div>
                <div v-if="r.urgencia" class="rec-urg" :style="{background: r.urgColor+'22', color: r.urgColor}">{{ r.urgencia }}</div>
              </div>
              <div class="rec-desc" v-if="r.desc">{{ r.desc }}</div>
              <div class="rec-prazo" v-if="r.prazo">🕐 {{ r.prazo }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ 8. PREVISÕES ══════════ -->
      <div class="bloco" v-if="parsedPrevisoes.length">
        <div class="bloco-label-row">
          <span class="bloco-label">🚀 Previsões</span>
          <span class="bloco-count">{{ parsedPrevisoes.length }}</span>
        </div>
        <div class="pred-grid">
          <div v-for="(p, i) in parsedPrevisoes" :key="i" class="pred-card">
            <div class="pred-num" :style="{background: ['rgba(0,229,195,0.15)','rgba(124,111,247,0.15)','rgba(29,161,242,0.15)','rgba(245,166,35,0.15)'][i%4], color: ['#00e5c3','#7c6ff7','#1da1f2','#f5a623'][i%4]}">{{ i + 1 }}</div>
            <div class="pred-text">{{ p.text }}</div>
          </div>
        </div>
      </div>

      <!-- ══════════ 9. TIMELINE DE EVENTOS ══════════ -->
      <div class="bloco" v-if="parsedTimeline.length">
        <div class="bloco-label-row">
          <span class="bloco-label">🕐 Timeline de Eventos</span>
          <span class="bloco-count">{{ parsedTimeline.length }}</span>
        </div>
        <div class="timeline">
          <div v-for="(ev, i) in parsedTimeline" :key="i" class="tl-item">
            <div class="tl-dot"></div>
            <div class="tl-content">
              <div class="tl-top">
                <div class="tl-date">{{ ev.date }}</div>
                <div v-if="ev.prob" class="tl-prob">{{ ev.prob }}% de probabilidade</div>
              </div>
              <div class="tl-desc">{{ ev.desc }}</div>
              <div v-if="ev.prob" class="tl-bar"><div class="tl-bar-fill" :style="{width: ev.prob+'%'}"></div></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ SENTIMENTO DA SIMULAÇÃO ══════════ -->
      <div class="bloco" v-if="sentimentData">
        <div class="bloco-label-row">
          <span class="bloco-label">💭 Análise de Sentimento</span>
          <span class="bloco-count">{{ sentimentData.geral.total }} posts</span>
        </div>
        <div class="sentiment-grid">
          <div class="sent-card">
            <div class="sent-title">Geral</div>
            <div class="sent-bars">
              <div class="sent-row">
                <span class="sent-label">Positivo</span>
                <div class="sent-track"><div class="sent-fill sent-pos" :style="{width: sentimentData.geral.pos+'%'}"></div></div>
                <span class="sent-pct" style="color:#00e5c3">{{ sentimentData.geral.pos }}%</span>
              </div>
              <div class="sent-row">
                <span class="sent-label">Neutro</span>
                <div class="sent-track"><div class="sent-fill sent-neu" :style="{width: sentimentData.geral.neu+'%'}"></div></div>
                <span class="sent-pct" style="color:#6b6b80">{{ sentimentData.geral.neu }}%</span>
              </div>
              <div class="sent-row">
                <span class="sent-label">Negativo</span>
                <div class="sent-track"><div class="sent-fill sent-neg" :style="{width: sentimentData.geral.neg+'%'}"></div></div>
                <span class="sent-pct" style="color:#ff5a5a">{{ sentimentData.geral.neg }}%</span>
              </div>
            </div>
          </div>
          <div class="sent-card" v-if="sentimentData.twitter.total">
            <div class="sent-title">🐦 Twitter <span class="sent-count">{{ sentimentData.twitter.total }}</span></div>
            <div class="sent-bars">
              <div class="sent-row"><span class="sent-label">Positivo</span><div class="sent-track"><div class="sent-fill sent-pos" :style="{width: sentimentData.twitter.pos+'%'}"></div></div><span class="sent-pct" style="color:#00e5c3">{{ sentimentData.twitter.pos }}%</span></div>
              <div class="sent-row"><span class="sent-label">Neutro</span><div class="sent-track"><div class="sent-fill sent-neu" :style="{width: sentimentData.twitter.neu+'%'}"></div></div><span class="sent-pct" style="color:#6b6b80">{{ sentimentData.twitter.neu }}%</span></div>
              <div class="sent-row"><span class="sent-label">Negativo</span><div class="sent-track"><div class="sent-fill sent-neg" :style="{width: sentimentData.twitter.neg+'%'}"></div></div><span class="sent-pct" style="color:#ff5a5a">{{ sentimentData.twitter.neg }}%</span></div>
            </div>
          </div>
          <div class="sent-card" v-if="sentimentData.reddit.total">
            <div class="sent-title">🔴 Reddit <span class="sent-count">{{ sentimentData.reddit.total }}</span></div>
            <div class="sent-bars">
              <div class="sent-row"><span class="sent-label">Positivo</span><div class="sent-track"><div class="sent-fill sent-pos" :style="{width: sentimentData.reddit.pos+'%'}"></div></div><span class="sent-pct" style="color:#00e5c3">{{ sentimentData.reddit.pos }}%</span></div>
              <div class="sent-row"><span class="sent-label">Neutro</span><div class="sent-track"><div class="sent-fill sent-neu" :style="{width: sentimentData.reddit.neu+'%'}"></div></div><span class="sent-pct" style="color:#6b6b80">{{ sentimentData.reddit.neu }}%</span></div>
              <div class="sent-row"><span class="sent-label">Negativo</span><div class="sent-track"><div class="sent-fill sent-neg" :style="{width: sentimentData.reddit.neg+'%'}"></div></div><span class="sent-pct" style="color:#ff5a5a">{{ sentimentData.reddit.neg }}%</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ TOP POSTS DOS AGENTES ══════════ -->
      <div class="bloco" v-if="topPosts.length">
        <div class="bloco-label-row">
          <span class="bloco-label">📝 Posts Mais Relevantes dos Agentes</span>
          <span class="bloco-count">{{ topPosts.length }}</span>
        </div>
        <div class="posts-grid">
          <div v-for="(p, i) in topPosts" :key="i" class="post-card">
            <div class="post-header">
              <div class="post-author">{{ p.author || p.username || p.user_name || 'Agente' }}</div>
              <div class="post-platform" :class="p.platform">{{ p.platform === 'twitter' ? '🐦' : '🔴' }}</div>
            </div>
            <div class="post-content">{{ (p.content || p.text || '').slice(0, 180) }}{{ (p.content || p.text || '').length > 180 ? '...' : '' }}</div>
            <div class="post-stats">
              <span class="ps-like">❤️ {{ p.num_likes || 0 }}</span>
              <span class="ps-dislike" v-if="p.num_dislikes">👎 {{ p.num_dislikes }}</span>
              <span class="ps-comments" v-if="p.num_comments">💬 {{ p.num_comments }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════ ACHADOS RELEVANTES ══════════ -->
      <div class="bloco" v-if="achadosRelevantes.length">
        <div class="bloco-label-row">
          <span class="bloco-label">⭐ Achados Relevantes</span>
          <span class="bloco-count">{{ achadosRelevantes.length }}</span>
        </div>
        <div class="achados-list">
          <div v-for="(a, i) in achadosRelevantes" :key="i" class="achado-card">
            <div class="achado-badge" :class="a.tipo">{{ a.tipo === 'achado' ? '🔍 Achado' : '⭐ Destaque' }}</div>
            <div class="achado-text">{{ a.text }}</div>
          </div>
        </div>
      </div>

      <!-- ══════════ NUVEM DE PALAVRAS ══════════ -->
      <div class="bloco" v-if="wordCloud.length">
        <div class="bloco-label-row">
          <span class="bloco-label">☁️ Nuvem de Palavras — Tópicos Mais Mencionados</span>
          <span class="bloco-count">{{ wordCloud.length }}</span>
        </div>
        <div class="wordcloud">
          <span v-for="(w, i) in wordCloud" :key="i" class="wc-word"
            :style="{fontSize: w.size+'px', color: w.color, opacity: w.opacity}">
            {{ w.word }}
          </span>
        </div>
      </div>

      <!-- ══════════ MAPA DE CALOR — ATIVIDADE POR RODADA ══════════ -->
      <div class="bloco" v-if="heatmapData">
        <div class="bloco-label-row">
          <span class="bloco-label">🔥 Mapa de Atividade por Rodada</span>
        </div>
        <div class="heatmap">
          <div class="hm-labels">
            <div class="hm-lbl">Twitter</div>
            <div class="hm-lbl">Reddit</div>
            <div class="hm-lbl">Total</div>
          </div>
          <div class="hm-grid">
            <div class="hm-row">
              <div v-for="r in heatmapData.rounds" :key="'tw'+r.round" class="hm-cell"
                :style="{background: `rgba(29,161,242,${Math.min(r.twitter/heatmapData.maxVal, 1) * 0.8 + 0.1})`}"
                :title="`R${r.round}: ${r.twitter} interações (Twitter)`">
                <span v-if="r.twitter">{{ r.twitter }}</span>
              </div>
            </div>
            <div class="hm-row">
              <div v-for="r in heatmapData.rounds" :key="'rd'+r.round" class="hm-cell"
                :style="{background: `rgba(255,69,0,${Math.min(r.reddit/heatmapData.maxVal, 1) * 0.8 + 0.1})`}"
                :title="`R${r.round}: ${r.reddit} interações (Reddit)`">
                <span v-if="r.reddit">{{ r.reddit }}</span>
              </div>
            </div>
            <div class="hm-row">
              <div v-for="r in heatmapData.rounds" :key="'tot'+r.round" class="hm-cell"
                :style="{background: `rgba(0,229,195,${r.intensity * 0.8 + 0.1})`}"
                :title="`R${r.round}: ${r.total} total`">
                <span v-if="r.total">{{ r.total }}</span>
              </div>
            </div>
          </div>
          <div class="hm-rounds">
            <span v-for="r in heatmapData.rounds" :key="'lbl'+r.round" class="hm-rlbl">R{{ r.round }}</span>
          </div>
        </div>
      </div>

      <!-- ══════════ 10. ANÁLISE PROFUNDA ══════════ -->
      <div class="bloco deep-bloco" v-if="deepSections.length">
        <div class="bloco-label-row">
          <span class="bloco-label">ℹ️ Análise Profunda</span>
        </div>
        <div class="deep-tabs">
          <button v-for="(ds, i) in deepSections" :key="i" class="deep-tab" :class="{active: deepTab === i}" @click="deepTab = i">
            <span class="deep-tab-icon">{{ ds.icon }}</span>
            <span class="deep-tab-label">{{ ds.label }}</span>
            <!-- Badges for Hipóteses -->
            <template v-if="ds.label === 'Hipóteses Causais' && hipotesesBadges.length">
              <span v-for="(b, bi) in hipotesesBadges.slice(0,5)" :key="bi" class="hyp-badge" :style="{background: b.color+'22', color: b.color}">{{ b.label }}</span>
            </template>
          </button>
        </div>
        <div class="deep-content" v-if="deepSections[deepTab]">
          <div class="md-body" v-html="md(deepSections[deepTab].content || '')"></div>
        </div>
        <!-- Print: show ALL sections (hidden on screen, visible in print) -->
        <div class="deep-print-all">
          <div v-for="(ds, i) in deepSections" :key="'print-'+i" class="deep-print-section">
            <div class="deep-print-header">{{ ds.icon }} {{ ds.label }}</div>
            <div class="md-body" v-html="md(ds.content || '')"></div>
          </div>
        </div>
      </div>

      <!-- ══════════ SEÇÕES GENÉRICAS (se houver) ══════════ -->
      <div v-for="(s, idx) in genericSections" :key="'gen-'+idx" class="bloco secao-bloco">
        <div class="sec-head" @click="s._open = !s._open">
          <div class="toggle-left">
            <span class="sec-num">{{ String(idx+1).padStart(2,'0') }}</span>
            <span class="sec-nom">{{ s.title }}</span>
          </div>
          <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14" :style="{transform: s._open ? 'rotate(180deg)' : '', transition:'transform .2s'}"><polyline points="2,4 6,8 10,4"/></svg>
        </div>
        <div v-if="!s._open" class="sec-body-inner">
          <div v-if="s.content" class="md-body" v-html="md(s.content)"></div>
          <div v-else-if="s.description" class="sec-desc">{{ s.description }}</div>
        </div>
      </div>

      <!-- ══════════ TOP AGENTES ══════════ -->
      <div v-if="analytics && twTopAgents.length" class="bloco">
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

      <!-- ══════════ CTA — CONVERSAR COM REPORTAGENT ══════════ -->
      <div class="cta-bar np">
        <div class="cta-inner">
          <div class="cta-text">
            <div class="cta-title">Quer aprofundar a análise?</div>
            <div class="cta-sub">Converse com o ReportAgent ou com agentes individuais para explorar cenários alternativos, questionar previsões e obter insights adicionais.</div>
          </div>
          <button class="cta-btn" @click="abrirChat">💬 Conversar com ReportAgent</button>
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
.bloco-label { font-size:11px;font-weight:700;color:var(--text-muted);letter-spacing:1.2px;text-transform:uppercase; }
.bloco-label-row { display:flex;align-items:center;justify-content:space-between; }
.bloco-label-sm { font-size:11px;font-weight:700;color:var(--text-muted);letter-spacing:1px;text-transform:uppercase; }
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
.cen-desc { font-size:12px;color:var(--text-muted);line-height:1.6; }
.cen-impacto { font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;white-space:nowrap;flex-shrink:0; }
.cen-prob-bar { height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden; }
.cpb-fill { height:100%;border-radius:3px; }
.cen-probval { font-size:12px;color:var(--text-muted); }

/* ─── Insights ──────────────────────────────────────────────── */
.insights-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:12px; }
.insight-card { display:flex;gap:14px;align-items:flex-start;background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:16px; }
.insight-num { width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;flex-shrink:0; }
.insight-text { font-size:13px;color:var(--text-secondary);line-height:1.6; }

/* ─── Riscos ──────────────────────────────────────────────── */
.risk-list { display:flex;flex-direction:column;gap:12px; }
.risk-card { background:var(--bg-raised);border:1px solid var(--border);border-radius:12px;padding:18px 20px;display:flex;flex-direction:column;gap:10px;transition:border-color .2s; }
.risk-card:hover { border-color:var(--border-md); }
.risk-top { display:flex;align-items:center;justify-content:space-between;gap:12px; }
.risk-name { font-size:14px;font-weight:700;color:var(--text-primary); }
.risk-badge { font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;white-space:nowrap; }
.risk-desc { font-size:12.5px;color:var(--text-muted);line-height:1.6; }
.risk-prob-row { display:flex;align-items:center;gap:10px; }
.risk-prob-label { font-size:11px;color:var(--text-muted);white-space:nowrap; }
.risk-prob-track { flex:1;height:6px;background:var(--bg-overlay);border-radius:3px;overflow:hidden; }
.risk-prob-fill { height:100%;border-radius:3px;transition:width .6s ease; }
.risk-prob-pct { font-size:12px;font-weight:700;min-width:30px;text-align:right;font-family:monospace; }

/* ─── Recomendações ──────────────────────────────────────────── */
.rec-list { display:flex;flex-direction:column;gap:12px; }
.rec-card { display:flex;gap:16px;align-items:flex-start;background:var(--bg-raised);border:1px solid var(--border);border-radius:12px;padding:18px 20px;transition:border-color .2s; }
.rec-card:hover { border-color:var(--border-md); }
.rec-num { width:32px;height:32px;background:rgba(29,161,242,0.12);color:#1da1f2;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;flex-shrink:0; }
.rec-body { flex:1;display:flex;flex-direction:column;gap:6px; }
.rec-top { display:flex;align-items:center;gap:10px;flex-wrap:wrap; }
.rec-name { font-size:14px;font-weight:700;color:var(--text-primary); }
.rec-urg { font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;white-space:nowrap; }
.rec-desc { font-size:12.5px;color:var(--text-muted);line-height:1.6; }
.rec-prazo { font-size:11px;color:var(--text-muted);opacity:.7; }

/* ─── Previsões ──────────────────────────────────────────────── */
.pred-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:12px; }
.pred-card { display:flex;gap:14px;align-items:flex-start;background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:16px; }
.pred-num { width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;flex-shrink:0; }
.pred-text { font-size:13px;color:var(--text-secondary);line-height:1.6; }

/* ─── Timeline ──────────────────────────────────────────────── */
.timeline { display:flex;flex-direction:column;gap:0;padding-left:20px;border-left:2px solid var(--border); }
.tl-item { position:relative;padding:16px 0 16px 24px; }
.tl-dot { position:absolute;left:-27px;top:22px;width:12px;height:12px;border-radius:50%;background:var(--bg-surface);border:2px solid var(--accent2); }
.tl-content { display:flex;flex-direction:column;gap:6px; }
.tl-top { display:flex;align-items:center;justify-content:space-between;gap:8px; }
.tl-date { font-size:12px;font-weight:700;color:var(--accent);text-transform:capitalize; }
.tl-prob { font-size:11px;color:var(--text-muted); }
.tl-desc { font-size:13px;color:var(--text-secondary);line-height:1.6; }
.tl-bar { height:5px;background:var(--bg-overlay);border-radius:3px;overflow:hidden;margin-top:4px; }
.tl-bar-fill { height:100%;background:var(--accent2);border-radius:3px;transition:width .6s ease; }

/* ─── Análise Profunda ──────────────────────────────────────── */
.deep-bloco { gap:0;padding:0;overflow:hidden; }
.deep-bloco .bloco-label-row { padding:18px 22px 0; }
.deep-tabs { display:flex;gap:0;border-bottom:1px solid var(--border);overflow-x:auto;padding:12px 22px 0; }
.deep-tab { background:none;border:none;color:var(--text-muted);font-size:12px;font-weight:600;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;display:flex;align-items:center;gap:6px;white-space:nowrap; }
.deep-tab:hover { color:var(--text-secondary); }
.deep-tab.active { color:var(--accent2);border-bottom-color:var(--accent2); }
.deep-tab-icon { font-size:14px; }
.deep-tab-label { font-size:12px; }
.hyp-badge { font-size:9px;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:2px; }
.deep-content { padding:20px 22px; }

/* ─── Seções genéricas ──────────────────────────────────────── */
.secao-bloco { gap:0;padding:0;overflow:hidden; }
.sec-head { width:100%;display:flex;align-items:center;justify-content:space-between;padding:16px 22px;background:none;border:none;cursor:pointer;text-align:left;color:var(--text-primary);transition:background .15s; }
.sec-head:hover { background:var(--bg-raised); }
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
.ag-bio { font-size:11px;color:var(--text-muted);line-height:1.5; }
.ag-stats { display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:var(--text-muted);margin-top:2px; }

/* ─── CTA ─────────────────────────────────────────────────── */
.cta-bar { background:linear-gradient(135deg,rgba(124,111,247,0.08) 0%,rgba(0,229,195,0.06) 100%);border:1px solid rgba(124,111,247,0.2);border-radius:14px;padding:24px; }
.cta-inner { display:flex;align-items:center;justify-content:space-between;gap:20px; }
.cta-text { flex:1; }
.cta-title { font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:6px; }
.cta-sub { font-size:12.5px;color:var(--text-muted);line-height:1.5; }
.cta-btn { background:var(--accent2);color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;transition:opacity .15s; }
.cta-btn:hover { opacity:.85; }

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

/* ─── Sentiment ──────────────────────────────────────────────── */
.sentiment-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:12px; }
.sent-card { background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:14px; }
.sent-title { font-size:13px;font-weight:700;color:var(--text-primary);margin-bottom:10px; }
.sent-count { font-size:11px;color:var(--text-muted);font-weight:400;margin-left:6px; }
.sent-bars { display:flex;flex-direction:column;gap:6px; }
.sent-row { display:flex;align-items:center;gap:8px; }
.sent-label { font-size:11px;color:var(--text-muted);min-width:55px; }
.sent-track { flex:1;height:6px;background:var(--bg-overlay);border-radius:3px;overflow:hidden; }
.sent-fill { height:100%;border-radius:3px;transition:width .6s ease; }
.sent-pos { background:#00e5c3; }
.sent-neu { background:#6b6b80; }
.sent-neg { background:#ff5a5a; }
.sent-pct { font-size:11px;font-weight:700;min-width:30px;text-align:right;font-family:monospace; }

/* ─── Posts ──────────────────────────────────────────────── */
.posts-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:10px; }
.post-card { background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px; }
.post-header { display:flex;align-items:center;justify-content:space-between; }
.post-author { font-size:13px;font-weight:700;color:var(--text-primary); }
.post-platform { font-size:14px; }
.post-content { font-size:12.5px;color:var(--text-secondary);line-height:1.6; }
.post-stats { display:flex;gap:12px;font-size:11px;color:var(--text-muted); }
.ps-like { color:#ff5a5a; }

/* ─── Achados Relevantes ─────────────────────────────────── */
.achados-list { display:flex;flex-direction:column;gap:10px; }
.achado-card { background:var(--bg-raised);border:1px solid var(--border);border-left:3px solid #f5a623;border-radius:0 10px 10px 0;padding:14px 16px;display:flex;flex-direction:column;gap:6px; }
.achado-badge { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px; }
.achado-badge.achado { color:#f5a623; }
.achado-badge.destaque { color:#7c6ff7; }
.achado-text { font-size:13px;color:var(--text-secondary);line-height:1.7; }

/* ─── Word Cloud ─────────────────────────────────────── */
.wordcloud { display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:center;padding:20px 10px;min-height:80px; }
.wc-word { font-weight:700;line-height:1.3;cursor:default;transition:transform .15s; }
.wc-word:hover { transform:scale(1.15); }

/* ─── Heatmap ─────────────────────────────────────── */
.heatmap { display:flex;flex-direction:column;gap:4px; }
.hm-labels { display:flex;flex-direction:column;gap:4px;position:absolute;left:0;top:0; }
.heatmap { position:relative;padding-left:60px; }
.hm-lbl { font-size:10px;color:var(--text-muted);height:32px;display:flex;align-items:center;position:absolute;left:0; }
.hm-lbl:nth-child(1) { top:0; }
.hm-lbl:nth-child(2) { top:36px; }
.hm-lbl:nth-child(3) { top:72px; }
.hm-grid { display:flex;flex-direction:column;gap:4px; }
.hm-row { display:flex;gap:3px; }
.hm-cell { height:32px;flex:1;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:rgba(255,255,255,0.8);min-width:24px;cursor:default;transition:transform .1s; }
.hm-cell:hover { transform:scale(1.1);z-index:1; }
.hm-cell span { text-shadow:0 1px 2px rgba(0,0,0,0.5); }
.hm-rounds { display:flex;gap:3px;margin-top:2px; }
.hm-rlbl { flex:1;text-align:center;font-size:9px;color:var(--text-muted);font-weight:600; }

/* ─── Doc footer ─────────────────────────────────────────────── */
.doc-foot { display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);padding:12px 4px;border-top:1px solid var(--border); }

/* ─── Print-only elements ─────────────────────────────────── */
.print-header { display:none; }
.deep-print-all { display:none; }
.deep-print-section { margin-bottom:24px; }
.deep-print-header { font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid var(--accent2); }

/* ─── PRINT ─────────────────────────────────────────────────── */
@media print {
  * { -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
  .np { display:none !important; }
  @page { size:A4; margin:12mm 15mm; }
  .page { gap:10px; }

  /* Show print header */
  .print-header { display:block !important;text-align:center;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #7c6ff7; }
  .print-logo { font-size:28px;font-weight:900;color:#7c6ff7;letter-spacing:4px; }
  .print-title { font-size:16px;font-weight:700;color:#1a1a2e;margin-top:6px; }
  .print-meta { font-size:10px;color:#6b6b80;margin-top:4px;display:flex;justify-content:center;gap:16px; }

  /* Page breaks */
  .bloco { page-break-inside:avoid;break-inside:avoid; }
  .deep-bloco { page-break-inside:auto; }
  .deep-print-section { page-break-inside:avoid;break-inside:avoid; }
  .risk-card,.rec-card { page-break-inside:avoid; }

  /* Layout fixes */
  .bloco-2col { grid-template-columns:1fr 1fr; }
  .cen-grid { grid-template-columns:repeat(3,1fr); }
  .resumo-inner { grid-template-columns:auto 1fr auto; }
  .agents-grid { grid-template-columns:repeat(3,1fr); }
  .insights-grid,.pred-grid { grid-template-columns:repeat(2,1fr); }
  .sec-body-inner { display:block !important; }
  .doc-foot { display:flex !important; }

  /* Deep analysis: hide tabs, show ALL content */
  .deep-tabs { display:none !important; }
  .deep-content { display:none !important; }
  .deep-print-all { display:block !important; }
  .deep-print-header { color:#7c6ff7 !important;border-color:#7c6ff7 !important; }

  /* White background for ALL cards */
  .bloco,.kpi-card,.chart-bloco,.cen-card,.agent-card,.prob-section,
  .risk-card,.rec-card,.insight-card,.pred-card,.cta-bar,.deep-bloco,.sent-card,.post-card,.achado-card { background:#fff !important;border-color:#e0e0ee !important; }

  /* Text colors for readability */
  .md-body,.md-body :deep(*) { color:#2a2a3e !important; }
  .sec-nom,.cb-val,.kpi-valor,.cen-nome,.risk-name,.rec-name,.cta-title,.deep-print-header { color:#1a1a2e !important; }
  .bloco-label,.bloco-label-sm,.sec-num,.cb-label,.kpi-label,.prob-title,
  .risk-prob-label,.rec-prazo,.tl-prob,.tl-date { color:#6b6b80 !important; }
  .cen-desc,.risk-desc,.rec-desc,.insight-text,.pred-text,.tl-desc,.ag-bio,.cta-sub { color:#3a3a4e !important; }
  .doc-foot { color:#9898b0 !important;border-color:#e0e0ee !important; }
  .page-head { display:none !important; }

  /* Timeline fix for print */
  .timeline { border-left-color:#ccc !important; }
  .tl-dot { border-color:#7c6ff7 !important;background:#fff !important; }
  .tl-bar { background:#eee !important; }
  .tl-bar-fill { background:#7c6ff7 !important; }
}

/* ─── Responsive ─────────────────────────────────────────────── */
@media (max-width: 1080px) {
  .resumo-inner { grid-template-columns:auto 1fr; }
  .resumo-badges { flex-direction:row;flex-wrap:wrap; }
  .bloco-2col { grid-template-columns:1fr; }
  .cen-grid { grid-template-columns:1fr; }
  .insights-grid,.pred-grid { grid-template-columns:1fr; }
  .sentiment-grid { grid-template-columns:1fr; }
  .posts-grid { grid-template-columns:1fr; }
  .agents-grid { grid-template-columns:repeat(2,1fr); }
  .deep-tabs { flex-wrap:wrap; }
  .cta-inner { flex-direction:column;text-align:center; }
}
@media (max-width: 680px) {
  .bloco { padding:16px 16px; }
  .kpi-row { grid-template-columns:repeat(2,1fr); }
  .resumo-inner { grid-template-columns:1fr; }
  .gauge-wrap { width:100%;align-items:center; }
}
</style>
