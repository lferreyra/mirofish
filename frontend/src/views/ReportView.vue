<script setup>
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route  = useRoute()
const router = useRouter()
const report     = ref(null)
const activeTab = ref('decisao')
const printMode = ref(false)

// Detectar impressao
if (typeof window !== 'undefined') {
  window.addEventListener('beforeprint', () => { printMode.value = true })
  window.addEventListener('afterprint', () => { printMode.value = false })
}
const expandedSections = ref(new Set())
const shareCode = ref('')
const shareLoading = ref(false)

function toggleSection(id) {
  if (expandedSections.value.has(id)) expandedSections.value.delete(id)
  else expandedSections.value.add(id)
}
function isExpanded(id) { return expandedSections.value.has(id) }

async function compartilhar() {
  const rid = route.params.reportId
  if (!rid) return
  shareLoading.value = true
  try {
    const clientName = prompt('Nome do cliente (aparece no relatorio):') || ''
    const res = await service.post('/api/share/create', { report_id: rid, client_name: clientName })
    const data = res?.data?.data || res?.data
    shareCode.value = data.code
    const url = window.location.origin + '/relatorio-publico/' + data.code
    await navigator.clipboard.writeText(url)
    alert('Link copiado!\n\n' + url + '\n\nCompartilhe com seu cliente.')
  } catch (e) {
    alert('Erro ao gerar link: ' + (e?.message || 'Tente novamente'))
  } finally {
    shareLoading.value = false
  }
}

const analytics  = ref(null)
const posts      = ref([])
const carregando = ref(true)
const erro       = ref('')
const deepTab    = ref(0)
let reportPollTimer = null

function hasReportContent(raw) {
  const sections = raw?.outline?.sections || []
  // Exigir pelo menos 2 seções com conteúdo substancial (50+ chars)
  const sectionsWithContent = sections.filter(s => (s?.content || '').trim().length > 50)
  return sectionsWithContent.length >= 2
}

async function carregarRelatorio() {
  const rRes = await service.get(`/api/report/${route.params.reportId}`).catch(e => ({ error: e }))
  if (rRes.error) throw rRes.error
  const raw = rRes?.data?.data || rRes?.data || rRes
  report.value = raw
  return raw
}

function iniciarPollingSeNecessario(raw) {
  const status = raw?.status
  const precisaPolling = ['pending', 'planning', 'generating'].includes(status) || !hasReportContent(raw)
  if (!precisaPolling) return
  if (reportPollTimer) clearInterval(reportPollTimer)
  reportPollTimer = setInterval(async () => {
    try {
      const atualizado = await carregarRelatorio()
      if (atualizado?.status === 'completed' && hasReportContent(atualizado)) {
        clearInterval(reportPollTimer)
        reportPollTimer = null
      }
    } catch {
      // Polling silencioso; não bloquear UI
    }
  }, 3000)
}

onMounted(async () => {
  carregando.value = true
  try {
    const raw = await carregarRelatorio()
    iniciarPollingSeNecessario(raw)
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

onUnmounted(() => {
  if (reportPollTimer) {
    clearInterval(reportPollTimer)
    reportPollTimer = null
  }
})

// Watch para recarregar quando mudar de relatório sem remount
watch(() => route.params.reportId, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    carregando.value = true
    erro.value = ''
    if (reportPollTimer) { clearInterval(reportPollTimer); reportPollTimer = null }
    try {
      const raw = await carregarRelatorio()
      iniciarPollingSeNecessario(raw)
      if (raw?.simulation_id) {
        try {
          const aRes = await service.get(`/api/analytics/${raw.simulation_id}`)
          analytics.value = aRes?.data?.data || aRes?.data || null
        } catch {}
      }
    } catch (e) {
      erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar relatório.'
    } finally {
      carregando.value = false
    }
  }
})

// ─── Dados base ───────────────────────────────────────────────
const titulo   = computed(() => report.value?.outline?.title   || 'Relatório de Previsão')
const dataFormatada = computed(() => {
  const d = report.value?.completed_at || report.value?.created_at || ''
  if (!d) return ''
  try { const dt = new Date(d); return dt.toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' }) } catch { return '' }
})
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
  // PT-BR
  if (t.includes('resumo') || t.includes('executive') || t.includes('摘要') || t.includes('总结') || t.includes('执行')) return 'resumo'
  if (t.includes('cenario') || t.includes('scenario') || t.includes('场景') || t.includes('情景')) return 'cenarios'
  if (t.includes('risco') || t.includes('risk') || t.includes('风险') || t.includes('挑战')) return 'riscos'
  if (t.includes('recomend') || t.includes('recommend') || t.includes('建议') || t.includes('策略')) return 'recomendacoes'
  if (t.includes('previs') || t.includes('predict') || t.includes('forecast') || t.includes('预测') || t.includes('趋势')) return 'previsoes'
  if (t.includes('insight') || t.includes('发现') || t.includes('洞察')) return 'insights'
  if ((t.includes('mapa') && t.includes('forca')) || t.includes('market') || t.includes('竞争') || t.includes('格局') || t.includes('演变')) return 'deep_mapa'
  if (t.includes('cronolog') || t.includes('chronol') || t.includes('时间')) return 'deep_crono'
  if (t.includes('padro') || t.includes('pattern') || t.includes('消费') || t.includes('行为') || t.includes('转变')) return 'deep_padroes'
  if (t.includes('hipotes') || t.includes('hypothes') || t.includes('品牌') || t.includes('叙事') || t.includes('机会')) return 'deep_hipoteses'
  if (t.includes('anomal') || t.includes('未来') || t.includes('潜在')) return 'deep_anomalias'
  if (t.includes('emocio') || t.includes('emotion') || t.includes('sentimento')) return 'emocional'
  if (t.includes('comunica') || t.includes('mensag') || t.includes('comunicação') || t.includes('messaging')) return 'comunicacao'
  if (t.includes('posicionamento') || t.includes('perceb') || t.includes('positioning') || t.includes('gap')) return 'posicionamento'
  if (t.includes('valor da analise') || t.includes('valor da análise') || t.includes('roi') || t.includes('investimento')) return 'valor_analise'
  if (t.includes('timeline') || t.includes('linha do tempo')) return 'timeline'
  return 'generic'
}

// Seções organizadas por categoria
const secResumo = computed(() => secoes.value.find(s => categ(s.title) === 'resumo') || secoes.value[0])
const secCenarios = computed(() => secoes.value.find(s => categ(s.title) === 'cenarios') || secoes.value[1])
const secRiscos = computed(() => secoes.value.find(s => categ(s.title) === 'riscos') || secoes.value.find(s => categ(s.title) === 'deep_anomalias'))
const secRecomendacoes = computed(() => secoes.value.find(s => categ(s.title) === 'recomendacoes') || secoes.value.find(s => categ(s.title) === 'previsoes'))
const secPrevisoes = computed(() => secoes.value.find(s => categ(s.title) === 'previsoes') || secoes.value.find(s => categ(s.title) === 'recomendacoes'))
const secInsights = computed(() => secoes.value.find(s => categ(s.title) === 'insights'))
const secEmocional = computed(() => secoes.value.find(s => categ(s.title) === 'emocional'))
const secComunicacao = computed(() => secoes.value.find(s => categ(s.title) === 'comunicacao'))
const secPosicionamento = computed(() => secoes.value.find(s => categ(s.title) === 'posicionamento'))
const secValorAnalise = computed(() => secoes.value.find(s => categ(s.title) === 'valor_analise'))

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
    'deep_mapa','deep_crono','deep_padroes','deep_hipoteses','deep_anomalias','timeline','emocional','comunicacao','posicionamento','valor_analise']
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

// Briefing CEO: versão objetiva para decisão
const briefingCEO = computed(() => {
  const cenarioPrincipal = cenarios.value?.[0]?.nome || 'Sem cenário dominante'
  
  // Decisão: da recomendação OU extrair do resumo executivo
  let decisao = (parsedRecomendacoes.value?.[0]?.name || '').replace(/\*\*/g, '').replace(/^#+\s*/g, '')
  if (!decisao) {
    const resumo = secResumo.value?.content || ''
    const decMatch = resumo.match(/(?:recomend|suger|deve|precis)[^.]*\./) 
    decisao = decMatch ? decMatch[0].replace(/\*\*/g, '').trim().slice(0, 120) : 'Revisar detalhes no relatório completo'
  }
  
  // Risco: do parser OU extrair do resumo
  let risco = (parsedRiscos.value?.[0]?.name || '').replace(/\*\*/g, '').replace(/^#+\s*/g, '')
  if (!risco) {
    const resumo = secResumo.value?.content || ''
    const riskMatch = resumo.match(/(?:risco|desafio|ameaça|preocup)[^.]*\./)
    risco = riskMatch ? riskMatch[0].replace(/\*\*/g, '').trim().slice(0, 120) : 'Ver seção de riscos'
  }
  
  const sentimento = sentimentData.value?.geral
  const tom = sentimento
    ? (sentimento.pos >= 50 ? 'Majoritariamente positivo'
      : sentimento.neg >= 40 ? 'Atenção: pressão negativa relevante'
      : 'Predomínio neutro com sinais mistos')
    : 'Sem base de sentimento suficiente'

  return {
    decisao,
    cenario: cenarioPrincipal,
    risco,
    tom
  }
})

// Veredicto GO/NO-GO extraído do resumo
const veredicto = computed(() => {
  const sum = (report.value?.outline?.summary || '').toUpperCase()
  const content = (secResumo.value?.content || '').toUpperCase()
  const all = sum + ' ' + content
  if (all.includes('NÃO LANÇAR') || all.includes('NO-GO') || all.includes('NOGO')) return { label: 'NÃO LANÇAR', color: '#ff5a5a', icon: '🔴' }
  if (all.includes('AJUSTAR') || all.includes('ADJUST')) return { label: 'AJUSTAR ANTES', color: '#f5a623', icon: '🟡' }
  if (all.includes('LANÇAR') || all.includes('GO')) return { label: 'LANÇAR', color: '#00e5c3', icon: '🟢' }
  return { label: 'EM ANÁLISE', color: '#8888aa', icon: '⚪' }
})

const resumoRodadas = computed(() => {
  return (rounds.value || []).slice(-5).map(r => ({
    rodada: r.round,
    total: r.total || 0,
    twitter: r.twitter || 0,
    reddit: r.reddit || 0
  }))
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
  // Tentar seção de insights dedicada primeiro, depois resumo
  const insContent = secInsights.value?.content || ''
  const resumoContent = secResumo.value?.content || ''
  const src = insContent || resumoContent
  if (!src) return []
  
  const achados = []
  
  // Estratégia 1: itens numerados (1. 2. 3.)
  const numbered = [...src.matchAll(/(?:^|\n)\s*\d+[.)\s]+(.{20,200}?)(?=\n\s*\d+[.)\s]|$)/gs)]
  numbered.forEach(m => {
    const text = m[1].replace(/\*\*/g, '').replace(/\n/g, ' ').trim()
    if (text.length > 15) achados.push({ text })
  })
  
  // Estratégia 2: bullets (- ou •)
  if (achados.length < 3) {
    const bullets = [...src.matchAll(/(?:^|\n)\s*[-•]\s+(.{15,200})/g)]
    bullets.forEach(m => {
      const text = m[1].replace(/\*\*/g, '').trim()
      if (text.length > 15 && !achados.some(a => a.text.includes(text.slice(0, 30)))) {
        achados.push({ text })
      }
    })
  }
  
  // Estratégia 3: frases com negrito como destaque
  if (achados.length < 3) {
    const bolds = [...src.matchAll(/\*\*([^*]{10,100})\*\*/g)]
    bolds.forEach(m => {
      const text = m[1].trim()
      if (!achados.some(a => a.text.includes(text.slice(0, 20)))) {
        achados.push({ text })
      }
    })
  }
  
  // Estratégia 4: parágrafos significativos (fallback)
  if (achados.length < 3) {
    const paragraphs = src.split(/\n\n+/).filter(p => p.trim().length > 40 && p.trim().length < 300)
    paragraphs.slice(0, 5 - achados.length).forEach(p => {
      const text = p.replace(/\*\*/g, '').replace(/\n/g, ' ').trim()
      const firstSentence = text.match(/^[^.!?]+[.!?]/)?.[0] || text.slice(0, 200)
      if (!achados.some(a => a.text.includes(firstSentence.slice(0, 30)))) {
        achados.push({ text: firstSentence })
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
  { label:'Riscos',    val: parsedRiscos.value.length || (secRiscos.value?.content ? '✓' : 0),    color:'#f5a623', icon:'⚠️' },
  { label:'Insights',  val: parsedInsights.value.length || (secInsights.value?.content ? '✓' : 0),  color:'#7c6ff7', icon:'💡' },
  { label:'Recomend.', val: parsedRecomendacoes.value.length || (secRecomendacoes.value?.content ? '✓' : 0), color:'#1da1f2', icon:'🎯' },
].filter(b => b.val))

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
        cards.push({ label: label.replace(/\*\*/g,'').replace(/^[-•#]\s*/,'').trim(), valor: valor.replace(/\*\*/g,'').replace(/^[-•#]\s*/,'').trim(), trend: trendFrom(valor) })
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
  
  // Extrair nomes: bold, headings, ou "Cenário X"
  const headings = [...content.matchAll(/\*\*([^*]{5,60})\*\*|(?:###?\s+)([^\n]{5,60})|(?:^|\n)(Cenário\s+[^\n]{3,50})/gim)]
    .map(m => (m[1] || m[2] || m[3] || '').trim())
    .filter(n => n.length > 3 && !n.toLowerCase().includes('probabilidade') && !n.toLowerCase().includes('impacto'))
    .slice(0, 3)
  
  // Extrair probabilidades e NORMALIZAR para somar 100%
  const rawProbs = [...content.matchAll(/(?:probabilidade|prob)[^\d]*(\d{1,3})\s*%/gi)]
    .map(m => parseInt(m[1])).filter(n => n >= 1 && n <= 99)
  // Se nao achou com "probabilidade", pegar qualquer %
  const allProbs = rawProbs.length >= 2 ? rawProbs : [...content.matchAll(/(\d{1,3})\s*%/g)]
    .map(m => parseInt(m[1])).filter(n => n >= 5 && n <= 95)
  const raw3 = allProbs.slice(0, 3)
  // Normalizar para somar 100
  const sum = raw3.reduce((a, b) => a + b, 0)
  const ps = raw3.length >= 3 && sum > 0 ? raw3.map(p => Math.round(p * 100 / sum)) : [70, 20, 10]
  // Garantir que soma = 100
  if (ps.length === 3) { ps[0] = 100 - ps[1] - ps[2] }
  
  // Nomes: filtrar nomes que sao titulos de secao
  const nomes = headings.length >= 3 
    ? headings.filter(n => !n.toLowerCase().startsWith('cenarios') && !n.toLowerCase().startsWith('cenários') && !n.startsWith(',') && !n.startsWith('.') && n.length > 5 && !/^\d+$/.test(n))
    : []
  if (nomes.length < 3) {
    // Fallback com nomes mais especificos
    while (nomes.length < 3) nomes.push(['Crescimento Sustentavel', 'Estagnacao', 'Crise'][nomes.length])
  }
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
  
  // Split por múltiplos padrões: **bold**, numerados, ou parágrafos com probabilidade
  const blocks = content.split(/(?=\*\*[^*]+\*\*|(?:^|\n)\d+[.)\s])/m).filter(b => b.trim().length > 20)
  
  for (const block of blocks) {
    // Extrair nome: bold OU primeira frase significativa
    const nameMatch = block.match(/\*\*#?\d*\s*([^*]+)\*\*/) || block.match(/\d+[.)\s]+([^\n.]{10,80})/) || block.match(/^([^\n.]{10,80})/)
    if (!nameMatch) continue
    let name = nameMatch[1].trim().replace(/^[-•]\s*/, '')
    if (name.length < 5 || name.length > 100) continue
    // Skip se é parágrafo genérico (não um risco nomeado)
    if (name.toLowerCase().startsWith('por meio') || name.toLowerCase().startsWith('a análise') || name.toLowerCase().startsWith('no futuro')) continue
    
    const probMatch = block.match(/(\d{1,3})\s*%/)
    const prob = probMatch ? parseInt(probMatch[1]) : 30
    const impMatch = block.match(/\b(alto|médio|medio|baixo)\b/i)
    const impacto = impMatch ? impMatch[1].charAt(0).toUpperCase() + impMatch[1].slice(1).toLowerCase() : 'Médio'
    
    // Descrição: tudo após o nome, limpo
    let desc = block.replace(/\*\*#?[^*]*\*\*/g, '').replace(/^#+\s*/gm, '').replace(/\d+[.)\s]/, '')
      .replace(/probabilidade[^\n]*/gi, '').replace(/impacto[^\n]*/gi, '')
      .replace(/\n+/g, ' ').trim().slice(0, 250)
    if (desc.length < 10) desc = block.replace(/\*\*/g, '').replace(/\n+/g, ' ').trim().slice(0, 250)
    
    risks.push({
      name: name.replace(/\*\*/g, '').replace(/^#+\s*/, '').trim(),
      desc,
      prob: Math.min(prob, 100),
      impacto: impacto.replace('Medio', 'Médio'),
      color: impacto.toLowerCase().includes('alt') ? '#ff5a5a' : '#f5a623'
    })
    if (risks.length >= 5) break
  }
  
  // Fallback: se não parseou nada, dividir por parágrafos
  if (risks.length === 0) {
    const paras = content.split(/\n\n+/).filter(p => p.trim().length > 30)
    paras.slice(0, 4).forEach((p, i) => {
      const firstLine = p.split('\n')[0].replace(/\*\*/g, '').trim()
      const probM = p.match(/(\d{1,3})\s*%/)
      risks.push({
        name: firstLine.slice(0, 80) || `Risco ${i+1}`,
        desc: p.replace(/\*\*/g, '').replace(/\n/g, ' ').trim().slice(0, 250),
        prob: probM ? parseInt(probM[1]) : 30,
        impacto: 'Médio',
        color: '#f5a623'
      })
    })
  }
  
  return risks
})

// Recomendações parser
const parsedRecomendacoes = computed(() => {
  const content = secRecomendacoes.value?.content || ''
  if (!content) return []
  const recs = []
  
  // Split por bold, numerados ou parágrafos
  const blocks = content.split(/(?=\*\*#?\d*\s*[^*]+\*\*|(?:^|\n)\d+[.)\s])/m).filter(b => b.trim().length > 15)
  
  for (const block of blocks) {
    const nameMatch = block.match(/\*\*#?\d*\s*([^*]+)\*\*/) || block.match(/\d+[.)\s]+([^\n]{10,80})/) || block.match(/^([^\n.]{10,80})/)
    if (!nameMatch) continue
    let name = nameMatch[1].trim().replace(/^[-•]\s*/, '')
    if (name.length < 5 || name.length > 100) continue
    if (name.toLowerCase().startsWith('para ') || name.toLowerCase().startsWith('a ') || name.toLowerCase().startsWith('os ')) continue
    
    const urgMatch = block.match(/\b(urgente|alta|média|media|baixa|critical|high|medium|low)\b/i)
    const urgencia = urgMatch ? urgMatch[1].charAt(0).toUpperCase() + urgMatch[1].slice(1).toLowerCase() : 'Média'
    const prazoMatch = block.match(/(?:prazo|próximos?|timeline|meses?)\s*:?\s*([^\n.]{5,40})/i)
    const prazo = prazoMatch ? prazoMatch[1].trim() : 'Próximos 3 meses'
    
    let desc = block.replace(/\*\*[^*]*\*\*/g, '').replace(/\d+[.)\s]/, '')
      .replace(/urgência[^\n]*/gi, '').replace(/prazo[^\n]*/gi, '')
      .replace(/\n+/g, ' ').trim().slice(0, 300)
    if (desc.length < 10) desc = block.replace(/\*\*/g, '').replace(/\n/g, ' ').trim().slice(0, 300)
    
    recs.push({
      name: name.replace(/\*\*/g, '').replace(/^#+\s*/, '').trim(),
      desc,
      urgencia: urgencia.replace('Media', 'Média'),
      prazo,
      urgColor: ['urgente','critical'].includes(urgencia.toLowerCase()) ? '#ff5a5a' : ['alta','high'].includes(urgencia.toLowerCase()) ? '#f5a623' : '#00e5c3'
    })
    if (recs.length >= 5) break
  }
  
  // Fallback
  if (recs.length === 0) {
    const paras = content.split(/\n\n+/).filter(p => p.trim().length > 30)
    paras.slice(0, 4).forEach((p, i) => {
      const firstLine = p.split('\n')[0].replace(/\*\*/g, '').trim()
      recs.push({
        name: firstLine.slice(0, 80) || `Recomendação ${i+1}`,
        desc: p.replace(/\*\*/g, '').replace(/\n/g, ' ').trim().slice(0, 300),
        urgencia: i === 0 ? 'Alta' : 'Média',
        prazo: 'Próximos 3 meses',
        urgColor: i === 0 ? '#f5a623' : '#00e5c3'
      })
    })
  }
  
  return recs
})

// Previsões parser
const parsedPrevisoes = computed(() => {
  const content = secPrevisoes.value?.content || ''
  if (!content) return []
  const preds = []
  
  // Estratégia 1: itens numerados
  const numbered = [...content.matchAll(/(?:^|\n)\s*\d+[.)\s]+(.{20,}?)(?=\n\s*\d+[.)\s]|\n\n|$)/gs)]
  if (numbered.length >= 2) {
    numbered.forEach(m => {
      const text = m[1].replace(/\*\*/g, '').replace(/\n/g, ' ').trim()
      if (text.length > 20) preds.push({ text: text.slice(0, 300) + (text.length > 300 ? '...' : '') })
    })
    return preds.slice(0, 5)
  }
  
  // Estratégia 2: parágrafos com indicadores de previsão
  const paras = content.split(/\n\n+/).filter(p => p.trim().length > 30)
  for (const p of paras) {
    const text = p.replace(/\*\*/g, '').replace(/\n/g, ' ').trim()
    // Pegar primeiro período longo o suficiente
    if (text.length > 30) {
      preds.push({ text: text.slice(0, 300) + (text.length > 300 ? '...' : '') })
    }
    if (preds.length >= 4) break
  }
  
  // Estratégia 3: frases com datas/probabilidades
  if (preds.length === 0) {
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 25)
    sentences.forEach(s => {
      const text = s.replace(/\*\*/g, '').trim()
      if (text.length > 25 && preds.length < 4) {
        preds.push({ text: text + '.' })
      }
    })
  }
  
  return preds.slice(0, 5)
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
  // Tentar gerar PDF primeiro
  const reportId = route.params.reportId
  const downloadUrl = (import.meta.env.VITE_API_BASE_URL || '') + '/api/report/' + reportId + '/download'
  try {
    const res = await fetch(downloadUrl)
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('pdf')) {
      // PDF real disponivel
      window.open(downloadUrl, '_blank')
      return
    }
  } catch {}
  // Fallback: imprimir a pagina atual (Ctrl+P)
  window.print()
}

function abrirChat() {
  // Navigate to interaction/chat view if available
  const rid = route.params.reportId
  router.push(`/agentes/${rid}`)
}
</script>


<template>
  <AppShell>
    <!-- Loading -->
    <div v-if="carregando" class="rpt-loading">
      <div class="ld-spinner"></div>
      <p>Gerando relatório de previsão...</p>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="rpt-error">
      <div class="err-icon">⚠️</div>
      <h3>Não foi possível carregar o relatório</h3>
      <p>{{ erro }}</p>
      <AugurButton @click="$router.go(-1)">Voltar</AugurButton>
    </div>

    <!-- Report -->
    <div v-else class="rpt-wrap">

      <!-- ═══ TOP BAR ═══ -->
      <header class="rpt-topbar">
        <div class="tb-left">
          <div class="tb-breadcrumb">
            <span class="bc-link" @click="router.push('/')">Dashboard</span>
            <span class="bc-sep">›</span>
            <span class="bc-current">Relatório</span>
          </div>
          <h1 class="tb-title">{{ titulo }}</h1>
          <p class="tb-date" v-if="geradoEm">Relatório de Previsão · {{ geradoEm }}</p>
        </div>
        <div class="tb-actions">
          <AugurButton variant="ghost" @click="router.push(`/projeto/${report?.project_id}`)" class="tb-btn" v-if="report?.project_id">← Projeto</AugurButton>
          <AugurButton variant="ghost" @click="router.push(`/agentes/${route.params.reportId}`)" class="tb-btn" v-if="report?.simulation_id">🧠 Agentes</AugurButton>
          <AugurButton variant="ghost" @click="router.push(`/simulacao/${report?.simulation_id}/posts`)" class="tb-btn" v-if="report?.simulation_id">📝 Posts</AugurButton>
          <AugurButton variant="ghost" @click="router.push(`/simulacao/${report?.simulation_id}/influentes`)" class="tb-btn" v-if="report?.simulation_id">👑 Influentes</AugurButton>
          <AugurButton variant="ghost" @click="compartilhar()" class="tb-btn" :disabled="shareLoading">🔗 {{ shareLoading ? 'Gerando...' : 'Compartilhar' }}</AugurButton>
          <AugurButton variant="primary" @click="exportarPDF()" class="tb-btn">📄 Exportar PDF</AugurButton>
        </div>
      </header>

      <!-- ═══ CONTEXTO DA ANÁLISE ═══ -->
      <section class="ctx-page">
        <div class="ctx-header">
          <div class="ctx-logo">🔭</div>
          <div>
            <h2 class="ctx-title">{{ titulo }}</h2>
            <p class="ctx-sub">Relatório de Previsão · {{ dataFormatada }}</p>
          </div>
        </div>
        <div class="ctx-grid">
          <div class="ctx-card">
            <span class="ctx-icon">📋</span>
            <div class="ctx-label">HIPÓTESE TESTADA</div>
            <div class="ctx-value ctx-hipotese">{{ truncar(simReq || 'Não disponível', 250) }}</div>
          </div>
          <div class="ctx-stats">
            <div class="ctx-stat"><span class="ctx-stat-val">{{ report?.outline?.sections?.length || 0 }}</span><span class="ctx-stat-lbl">seções</span></div>
            <div class="ctx-stat"><span class="ctx-stat-val">{{ confianca }}%</span><span class="ctx-stat-lbl">confiança</span></div>
            <div class="ctx-stat"><span class="ctx-stat-val">{{ cenarios.length }}</span><span class="ctx-stat-lbl">cenários</span></div>
          </div>
        </div>
        <div class="ctx-disclaimer">
          Esta análise simula a reação de agentes autônomos ao cenário descrito. Os resultados representam cenários possíveis baseados em interação multiagente com inteligência artificial e não garantem resultados futuros.
        </div>
      </section>

      <!-- ═══ TABS ═══ -->
      <nav class="rpt-tabs">
        <button class="rpt-tab" :class="{'rpt-tab-on': activeTab === 'decisao'}" @click="activeTab = 'decisao'">⚡ Decisão</button>
        <button class="rpt-tab" :class="{'rpt-tab-on': activeTab === 'analise'}" @click="activeTab = 'analise'">📊 Análise</button>
        <button class="rpt-tab" :class="{'rpt-tab-on': activeTab === 'estrategia'}" @click="activeTab = 'estrategia'">🎯 Estratégia</button>
        <button class="rpt-tab" :class="{'rpt-tab-on': activeTab === 'profunda'}" @click="activeTab = 'profunda'">🔬 Profunda</button>
      </nav>

      <!-- ═══ TAB: DECISÃO ═══ -->
      <div v-show="activeTab === 'decisao' || printMode">

      <div class="layer-label"><span class="ll-icon">⚡</span> Decisão em 30 segundos</div>

      <!-- ═══ 1. HERO: RESUMO EXECUTIVO ═══ -->
      <section class="rpt-hero">
        <div class="hero-gauge">
          <svg viewBox="0 0 120 90" class="gauge-svg">
            <path d="M 16 75 A 52 52 0 0 1 104 75" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" stroke-linecap="round"/>
            <path :d="gaugePath(confianca)" fill="none" stroke="url(#gGrad)" stroke-width="10" stroke-linecap="round" class="gauge-fill"/>
            <defs><linearGradient id="gGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7c6ff7"/><stop offset="100%" stop-color="#00e5c3"/></linearGradient></defs>
            <text x="60" y="62" text-anchor="middle" fill="var(--c-text)" font-size="28" font-weight="800">{{ confianca }}%</text>
            <text x="60" y="78" text-anchor="middle" fill="var(--c-muted)" font-size="9" font-weight="600" letter-spacing="1.5">CONFIANÇA</text>
          </svg>
        </div>
        <div class="hero-content">
          <div class="hero-veredicto" :style="{background: veredicto.color + '15', borderColor: veredicto.color + '44', color: veredicto.color}">
              {{ veredicto.icon }} {{ veredicto.label }}
            </div>
            <h2 class="hero-label">RESUMO EXECUTIVO</h2>
          <div v-if="secResumo?.content" class="hero-text md-body" 
               :class="{'hero-collapsed': !isExpanded('resumo')}"
               v-html="md(secResumo.content)"></div>
          <button v-if="secResumo?.content?.length > 500" class="hero-toggle" @click="toggleSection('resumo')">
            {{ isExpanded('resumo') ? '▲ Recolher' : '▼ Ver resumo completo' }}
          </button>
          <div v-if="simReq" class="hero-hipotese">
            <strong>Hipótese:</strong> {{ truncar(simReq, 300) }}
          </div>
        </div>
        <div class="hero-badges">
          <div v-for="b in countBadges" :key="b.label" class="hb-item" :style="{'--bc': b.color}">
            <span class="hb-icon">{{ b.icon }}</span>
            <span class="hb-val">{{ b.val }}</span>
            <span class="hb-label">{{ b.label }}</span>
          </div>
        </div>
      </section>

      <!-- ═══ 2. BRIEFING CEO ═══ -->
      <section class="rpt-section ceo-section">
        <div class="sec-header">
          <span class="sec-icon">🧭</span>
          <h3>Briefing CEO — 1 Minuto</h3>
        </div>
        <div class="ceo-grid">
          <div class="ceo-card">
            <div class="ceo-label">DECISÃO RECOMENDADA</div>
            <div class="ceo-value">{{ (briefingCEO.decisao || '').length > 150 ? (briefingCEO.decisao || '').slice(0, 147) + '...' : briefingCEO.decisao }}</div>
          </div>
          <div class="ceo-card">
            <div class="ceo-label">CENÁRIO MAIS PROVÁVEL</div>
            <div class="ceo-value">{{ (briefingCEO.cenario || '').length > 150 ? (briefingCEO.cenario || '').slice(0, 147) + '...' : briefingCEO.cenario }}</div>
          </div>
          <div class="ceo-card">
            <div class="ceo-label">RISCO CRÍTICO AGORA</div>
            <div class="ceo-value ceo-risk">{{ (briefingCEO.risco || '').length > 150 ? (briefingCEO.risco || '').slice(0, 147) + '...' : briefingCEO.risco }}</div>
          </div>
          <div class="ceo-card">
            <div class="ceo-label">SENTIMENTO GERAL</div>
            <div class="ceo-value">{{ briefingCEO.tom }}</div>
          </div>
        </div>
      </section>

      <!-- ═══ 3. KPI CARDS ═══ -->
      <section v-if="kpiCards.length" class="kpi-strip">
        <div v-for="k in kpiCards" :key="k.label" class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-name">{{ k.label.replace(/\*\*/g, "") }}</span>
            <span class="kpi-trend" :class="k.trend">
              <template v-if="k.trend==='up'">↗</template>
              <template v-else-if="k.trend==='down'">↘</template>
              <template v-else>→</template>
            </span>
          </div>
          <div class="kpi-val">{{ (k.valor || "").replace(/\*\*/g, "").slice(0, 60) }}</div>
        </div>
      </section>

      <!-- ═══ 4. EVOLUÇÃO + RADAR ═══ -->
      <section class="rpt-charts" v-if="lineChart || analytics">
        <div class="chart-card" v-if="lineChart">
          <div class="sec-header-sm">
            <span>📈 Evolução da Simulação</span>
            <div class="chart-legend">
              <span class="leg-tw">● Twitter</span>
              <span class="leg-rd">● Reddit</span>
              <span class="leg-tot">● Total</span>
            </div>
          </div>
          <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="evo-chart" preserveAspectRatio="xMidYMid meet">
            <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00e5c3" stop-opacity="0.15"/><stop offset="100%" stop-color="#00e5c3" stop-opacity="0"/></linearGradient></defs>
            <g v-for="l in lineChart.yLines" :key="l.val"><line :x1="cp.l" :y1="l.y" :x2="chartW-cp.r" :y2="l.y" stroke="rgba(255,255,255,0.05)" stroke-width="1"/><text :x="cp.l-4" :y="l.y+4" text-anchor="end" fill="rgba(255,255,255,0.25)" font-size="9">{{ l.val }}</text></g>
            <g v-for="lb in lineChart.labels" :key="lb.r"><text :x="lb.x" :y="chartH-cp.b+14" text-anchor="middle" fill="rgba(255,255,255,0.25)" font-size="9">R{{ lb.r }}</text></g>
            <path :d="lineChart.area" fill="url(#ag)"/>
            <path :d="lineChart.tw" fill="none" stroke="#1da1f2" stroke-width="2" stroke-linejoin="round" opacity="0.8"/>
            <path :d="lineChart.rd" fill="none" stroke="#ff4500" stroke-width="2" stroke-linejoin="round" opacity="0.8"/>
            <path :d="lineChart.total" fill="none" stroke="#00e5c3" stroke-width="2.5" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="chart-card" v-if="sentimentData">
          <div class="sec-header-sm"><span>💬 Sentimento</span></div>
          <div class="sent-bars">
            <div class="sent-row" v-if="sentimentData.twitter">
              <span class="sent-plat">Twitter</span>
              <div class="sent-bar-wrap">
                <div class="sent-pos" :style="{width: sentimentData.twitter.pos+'%'}"></div>
                <div class="sent-neu" :style="{width: sentimentData.twitter.neu+'%'}"></div>
                <div class="sent-neg" :style="{width: sentimentData.twitter.neg+'%'}"></div>
              </div>
              <span class="sent-pct">{{ sentimentData.twitter.pos }}%</span>
            </div>
            <div class="sent-row" v-if="sentimentData.reddit">
              <span class="sent-plat">Reddit</span>
              <div class="sent-bar-wrap">
                <div class="sent-pos" :style="{width: sentimentData.reddit.pos+'%'}"></div>
                <div class="sent-neu" :style="{width: sentimentData.reddit.neu+'%'}"></div>
                <div class="sent-neg" :style="{width: sentimentData.reddit.neg+'%'}"></div>
              </div>
              <span class="sent-pct">{{ sentimentData.reddit.pos }}%</span>
            </div>
          </div>
          <div class="sent-legend">
            <span class="sl-pos">● Positivo</span>
            <span class="sl-neu">● Neutro</span>
            <span class="sl-neg">● Negativo</span>
          </div>
        </div>
      </section>

      </div><!-- /tab decisao -->

      <!-- ═══ TAB: ANÁLISE ═══ -->
      <div v-show="activeTab === 'analise' || printMode">

      <div class="layer-label"><span class="ll-icon">📊</span> Análise executiva</div>

      <!-- ═══ 5. CENÁRIOS FUTUROS ═══ -->
      <section class="rpt-section" v-if="cenarios.length">
        <div class="sec-header"><span class="sec-icon">🎯</span><h3>Cenários Futuros</h3><span class="sec-count">{{ cenarios.length }}</span></div>
        <div class="prob-bar-wrap">
          <div class="prob-label">Probabilidade por cenário</div>
          <div class="prob-bar">
            <div v-for="c in cenarios" :key="c.nome" class="prob-seg" :style="{width: c.prob+'%', background: c.cor}" :title="c.nome+': '+c.prob+'%'"></div>
          </div>
          <div class="prob-legend">
            <span v-for="c in cenarios" :key="c.nome"><span class="pl-dot" :style="{background: c.cor}"></span>{{ c.nome }} {{ c.prob }}%</span>
          </div>
        </div>
        <div class="cenario-cards">
          <div v-for="c in cenarios" :key="c.nome" class="cenario-card" :style="{'--cc': c.cor, '--cci': c.corI}">
            <div class="cc-header">
              <h4>{{ c.nome }}</h4>
              <span class="cc-badge" :style="{background: c.corI, color: c.cor, borderColor: c.cor+'44'}">{{ c.impacto }}</span>
            </div>
            <p class="cc-desc" v-if="c.desc">{{ c.desc }}</p>
            <div class="cc-prob">
              <span>Probabilidade</span>
              <div class="cc-prob-bar"><div :style="{width: c.prob+'%', background: c.cor}"></div></div>
              <strong :style="{color: c.cor}">{{ c.prob }}%</strong>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══ 6. INSIGHTS PRINCIPAIS ═══ -->
      <section class="rpt-section" v-if="secInsights?.content || achadosRelevantes.length">
        <div class="sec-header"><span class="sec-icon">💡</span><h3>Insights Principais</h3></div>
        <!-- Cards se parser funcionou bem (2+ itens com texto > 20 chars) -->
        <div class="insights-list" v-if="achadosRelevantes.length >= 2 && achadosRelevantes.every(a => a.text.length > 20)">
          <div v-for="(a, i) in achadosRelevantes" :key="i" class="insight-item">
            <span class="ins-num">{{ i + 1 }}</span>
            <p>{{ a.text }}</p>
          </div>
        </div>
        <!-- Fallback: renderizar markdown completo (qualidade garantida) -->
        <div v-else-if="secInsights?.content" class="md-body" v-html="md(secInsights.content)"></div>
      </section>

      <!-- ═══ 6b. ANÁLISE EMOCIONAL ═══ -->
      <section class="rpt-section" v-if="secEmocional?.content">
        <div class="sec-header sec-collapsible" @click="toggleSection('emocional')">
          <span class="sec-icon">🎭</span><h3>Análise Emocional</h3>
          <span class="sec-toggle">{{ isExpanded('emocional') ? '▾' : '▸' }}</span>
        </div>
        <div class="sec-collapse" :class="{'sec-open': isExpanded('emocional')}">
          <div class="md-body" v-html="md(secEmocional.content)"></div>
        </div>
      </section>

      <!-- ═══ 7. FATORES DE RISCO ═══ -->
      <section class="rpt-section" v-if="secRiscos?.content || parsedRiscos.length">
        <div class="sec-header"><span class="sec-icon">⚠️</span><h3>Fatores de Risco</h3></div>
        <!-- Cards se parser funcionou bem (2+ riscos com nomes reais) -->
        <div class="risk-cards" v-if="parsedRiscos.length >= 2">
          <div v-for="(r, i) in parsedRiscos" :key="i" class="risk-card" :style="{'--rc': r.color}">
            <div class="rc-header">
              <h4>{{ r.name.replace(/^[#*\s]+/, "").replace(/[*#]+/g, "") }}</h4>
              <span class="rc-badge" :style="{background: r.color+'18', color: r.color, border: '1px solid '+r.color+'44'}">{{ r.impacto }}</span>
            </div>
            <p class="rc-desc">{{ r.desc.replace(/\*\*/g, "").replace(/^[#*\s]+/, "").slice(0, 200) }}</p>
            <div class="rc-prob">
              <span>Probabilidade de ocorrência</span>
              <div class="rc-prob-bar"><div :style="{width: r.prob+'%', background: r.color}"></div></div>
              <strong>{{ r.prob }}%</strong>
            </div>
          </div>
        </div>
        <!-- Fallback: markdown completo -->
        <div v-else-if="secRiscos?.content" class="md-body" v-html="md(secRiscos.content)"></div>
      </section>

      <!-- ═══ 8. RECOMENDAÇÕES ESTRATÉGICAS ═══ -->
      <section class="rpt-section" v-if="secRecomendacoes?.content || parsedRecomendacoes.length">
        <div class="sec-header"><span class="sec-icon">⚡</span><h3>Recomendações Estratégicas</h3></div>
        <!-- Cards se parser funcionou (2+ recomendações) -->
        <div class="rec-cards" v-if="parsedRecomendacoes.length >= 2">
          <div v-for="(r, i) in parsedRecomendacoes" :key="i" class="rec-card" :class="{'rec-highlight': i === 0}">
            <div class="rec-num">{{ i + 1 }}</div>
            <div class="rec-body">
              <div class="rec-top-row">
                <h4>{{ r.name.replace(/^[#*\s]+/, "").replace(/[*#]+/g, "") }}</h4>
                <span v-if="r.urgencia" class="rec-urg" :style="{background: r.urgColor+'18', color: r.urgColor, border: '1px solid '+r.urgColor+'44'}">{{ r.urgencia }}</span>
              </div>
              <p>{{ r.desc.replace(/\*\*/g, "").replace(/^#+\s*/g, "").replace(/^#/g, "") }}</p>
              <div class="rec-prazo" v-if="r.prazo">🕐 {{ r.prazo }}</div>
            </div>
          </div>
        </div>
        <!-- Fallback: markdown -->
        <div v-else-if="secRecomendacoes?.content" class="md-body" v-html="md(secRecomendacoes.content)"></div>
      </section>

      </div><!-- /tab analise -->

      <!-- ═══ TAB: ESTRATÉGIA ═══ -->
      <div v-show="activeTab === 'estrategia' || printMode">

      <!-- ═══ 8b. ESTRATÉGIA DE COMUNICAÇÃO ═══ -->
      <section class="rpt-section" v-if="secComunicacao?.content">
        <div class="sec-header sec-collapsible" @click="toggleSection('comm')">
          <span class="sec-icon">📣</span><h3>Estratégia de Comunicação</h3>
          <span class="sec-toggle">{{ isExpanded('comm') ? '▾' : '▸' }}</span>
        </div>
        <div class="sec-collapse" :class="{'sec-open': isExpanded('comm')}">
          <div class="md-body" v-html="md(secComunicacao.content)"></div>
        </div>
      </section>

      <!-- ═══ POSICIONAMENTO PERCEBIDO vs DESEJADO ═══ -->
      <section class="rpt-section" v-if="secPosicionamento?.content">
        <div class="sec-header sec-collapsible" @click="toggleSection('posic')">
          <span class="sec-icon">🎯</span><h3>Posicionamento Percebido vs Desejado</h3>
          <span class="sec-toggle">{{ isExpanded('posic') ? '▾' : '▸' }}</span>
        </div>
        <div class="sec-collapse" :class="{'sec-open': isExpanded('posic')}">
          <div class="md-body" v-html="md(secPosicionamento.content)"></div>
        </div>
      </section>

      <!-- ═══ 9. PREVISÕES ═══ -->
      <section class="rpt-section" v-if="secPrevisoes?.content || parsedPrevisoes.length">
        <div class="sec-header"><span class="sec-icon">🔮</span><h3>Previsões</h3></div>
        <!-- Cards se parser funcionou -->
        <div class="prev-list" v-if="parsedPrevisoes.length >= 2 && parsedPrevisoes.every(p => p.text.length > 30)">
          <div v-for="(p, i) in parsedPrevisoes" :key="i" class="prev-item">
            <span class="prev-num">{{ i + 1 }}</span>
            <p>{{ p.text }}</p>
          </div>
        </div>
        <!-- Fallback: markdown -->
        <div v-else-if="secPrevisoes?.content" class="md-body" v-html="md(secPrevisoes.content)"></div>
      </section>

      </div><!-- /tab estrategia -->

      <!-- ═══ TAB: PROFUNDA ═══ -->
      <div v-show="activeTab === 'profunda' || printMode">

      <div class="layer-label"><span class="ll-icon">🔬</span> Análise profunda</div>

      <!-- ═══ 10. ANÁLISE PROFUNDA ═══ -->
      <section class="rpt-section" v-if="deepSections.length">
        <div class="sec-header"><span class="sec-icon">🔬</span><h3>Análise Profunda</h3></div>
        <div class="deep-tabs">
          <button v-for="(d, i) in deepSections" :key="i" class="dt-btn" :class="{active: deepTab === i}" @click="deepTab = i">
            {{ d.icon }} {{ d.label }}
          </button>
        </div>
        <div class="deep-content md-body" v-if="deepSections[deepTab]" v-html="md(deepSections[deepTab].content || '')"></div>
        <div v-else-if="!deepSections.length && secResumo?.content" class="md-body deep-fallback">
          <p style="color:var(--c-dim);font-style:italic">Analise profunda nao disponivel para esta simulacao. Os dados completos estao distribuidos nas secoes acima.</p>
        </div>
      </section>

      <!-- ═══ 11. NUVEM DE PALAVRAS ═══ -->
      <section class="rpt-section" v-if="wordCloud.length">
        <div class="sec-header"><span class="sec-icon">☁️</span><h3>Nuvem de Palavras</h3></div>
        <div class="wc-wrap">
          <span v-for="w in wordCloud" :key="w.word" class="wc-word" :style="{fontSize: w.size+'px', color: w.color, opacity: w.opacity}">{{ w.word }}</span>
        </div>
      </section>

      <!-- ═══ 12. POSTS RELEVANTES ═══ -->
      <section class="rpt-section" v-if="topPosts.length">
        <div class="sec-header"><span class="sec-icon">📱</span><h3>Posts Relevantes</h3></div>
        <div class="posts-grid">
          <div v-for="(p, i) in topPosts" :key="i" class="post-card">
            <div class="pc-head">
              <span class="pc-plat" :class="p.platform">{{ p.platform === 'twitter' ? '𝕏' : '🔴' }}</span>
              <span class="pc-user">{{ p.user_name || p.username || 'Agente' }}</span>
              <span class="pc-likes">❤️ {{ p.num_likes || 0 }}</span>
            </div>
            <p class="pc-text">{{ truncar(p.content || p.text || '', 180) }}</p>
          </div>
        </div>
      </section>

      <!-- ═══ VALOR DA ANÁLISE ═══ -->
      <section class="rpt-section valor-section" v-if="secValorAnalise?.content">
        <div class="sec-header sec-collapsible" @click="toggleSection('valor')">
          <span class="sec-icon">💎</span><h3>Valor da Análise</h3>
          <span class="sec-toggle">{{ isExpanded('valor') ? '▾' : '▸' }}</span>
        </div>
        <div class="sec-collapse" :class="{'sec-open': isExpanded('valor')}">
          <div class="md-body" v-html="md(secValorAnalise.content)"></div>
        </div>
      </section>

      </div><!-- /tab profunda -->

      <!-- ═══ SEÇÃO DE FECHAMENTO (always visible) ═══ -->
      <section class="closing-page">
        <div class="closing-inner">
          <div class="closing-verdict" :style="{color: veredicto.color}">
            <span class="closing-icon">{{ veredicto.icon }}</span>
            <h2>{{ veredicto.label }}</h2>
          </div>
          <p class="closing-summary">{{ (report?.outline?.summary || '').replace(/VEREDICTO:[^.]*\./i, '').trim() }}</p>
          
          <div class="closing-trio">
            <div class="closing-item">
              <span class="ci-icon">🎯</span>
              <h4>Cenário mais provável</h4>
              <p>{{ cenarios[0]?.nome || '—' }} ({{ cenarios[0]?.prob || 0 }}%)</p>
            </div>
            <div class="closing-item ci-action">
              <span class="ci-icon">⚡</span>
              <h4>Ação prioritária</h4>
              <p>{{ (parsedRecomendacoes[0]?.name || briefingCEO.decisao || "").replace(/[#*]/g, "").trim() }}</p>
            </div>
            <div class="closing-item">
              <span class="ci-icon">⚠️</span>
              <h4>Risco principal</h4>
              <p>{{ (parsedRiscos[0]?.name || briefingCEO.risco || "").replace(/[#*]/g, "").trim() }}</p>
            </div>
          </div>

          <div class="closing-footer">
            <div class="closing-brand">
              <span class="closing-logo">🔭</span>
              <span>AUGUR</span>
            </div>
            <p class="closing-tagline">Preveja o futuro. Antes que ele aconteça.</p>
          </div>
        </div>
      </section>

      <!-- ═══ SEÇÕES GENÉRICAS ═══ -->
      <section v-for="s in genericSections" :key="s.title" class="rpt-section">
        <div class="sec-header"><h3>{{ s.title }}</h3></div>
        <div class="md-body" v-html="md(s.content || '')"></div>
      </section>

      <!-- ═══ CTA: ANÁLISE PROFUNDA ═══ -->
      <section class="rpt-cta" v-if="report?.simulation_id">
        <h3>Quer aprofundar a análise?</h3>
        <p>Converse com o ReportAgent ou com agentes individuais para explorar cenários alternativos, questionar previsões e obter insights adicionais.</p>
        <AugurButton variant="primary" @click="router.push(`/agentes/${route.params.reportId}`)">Conversar com Agentes</AugurButton>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
/* ═══ AUGUR REPORT — CEO GRADE ═══ */
:root { --c-bg: #09090f; --c-surface: #111118; --c-card: #16161f; --c-border: rgba(255,255,255,0.06);
  --c-text: #f0f0ff; --c-muted: #8888aa; --c-dim: #555570; --c-accent: #00e5c3; --c-purple: #7c6ff7;
  --c-danger: #ff5a5a; --c-gold: #f5a623; --c-blue: #1da1f2; --c-radius: 16px; }

/* Loading & Error */
.rpt-loading { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:60vh; gap:16px; color:var(--c-muted); }
.ld-spinner { width:40px; height:40px; border:3px solid var(--c-border); border-top-color:var(--c-accent); border-radius:50%; animation:spin 1s linear infinite; }
@keyframes spin { to { transform:rotate(360deg) } }
.rpt-error { text-align:center; padding:80px 20px; }
.rpt-error h3 { color:var(--c-text); margin:16px 0 8px; }
.rpt-error p { color:var(--c-muted); margin-bottom:20px; }
.err-icon { font-size:48px; }

/* Wrap */
.rpt-wrap { max-width:1100px; margin:0 auto; padding:0 20px 60px; }

/* ═══ TOP BAR ═══ */
.rpt-topbar { display:flex; justify-content:space-between; align-items:flex-start; padding:24px 0 20px; border-bottom:1px solid var(--c-border); margin-bottom:28px; flex-wrap:wrap; gap:12px; }
.tb-breadcrumb { display:flex; gap:6px; font-size:12px; color:var(--c-dim); margin-bottom:6px; }
.bc-link { cursor:pointer; color:var(--c-muted); transition:color .2s; }
.bc-link:hover { color:var(--c-accent); }
.bc-sep { opacity:0.4; }
.bc-current { color:var(--c-muted); }
.tb-title { font-size:clamp(16px,2.5vw,22px); font-weight:700; color:var(--c-text); line-height:1.3; }
.tb-date { font-size:12px; color:var(--c-dim); margin-top:4px; }
.tb-actions { display:flex; gap:6px; flex-wrap:wrap; }
.tb-btn { font-size:12px !important; padding:6px 12px !important; }

/* ═══ HERO: RESUMO EXECUTIVO ═══ */
.rpt-hero { display:grid; grid-template-columns:auto 1fr auto; gap:24px; align-items:start;
  background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04));
  border:1px solid var(--c-border); border-radius:var(--c-radius); padding:clamp(20px,3vw,32px); margin-bottom:24px; }
.hero-gauge { display:flex; align-items:center; justify-content:center; }
.gauge-svg { width:clamp(100px,14vw,140px); height:auto; filter:drop-shadow(0 0 20px rgba(0,229,195,0.15)); }
.gauge-fill { transition:stroke-dashoffset 1.5s cubic-bezier(0.16,1,0.3,1); }
.hero-content { min-width:0; }
.hero-label { font-size:11px; font-weight:700; letter-spacing:2px; color:var(--c-accent); margin-bottom:8px; text-transform:uppercase; }
.hero-text { font-size:14px; color:var(--c-muted); line-height:1.75; }
.hero-collapsed { max-height:180px; overflow:hidden; position:relative; }
.hero-collapsed::after { content:''; position:absolute; bottom:0; left:0; right:0; height:60px; background:linear-gradient(rgba(255,255,255,0), #ffffff); }
.hero-toggle { display:block; margin:8px auto 0; padding:6px 20px; border:1px solid var(--c-border); background:white; border-radius:20px; font-size:12px; color:var(--c-accent); font-weight:600; cursor:pointer; transition:all .2s; }
.hero-toggle:hover { background:rgba(0,229,195,0.05); border-color:var(--c-accent); }
.hero-text :deep(strong) { color:var(--c-text); font-weight:600; }
.hero-hipotese { font-size:12px; color:var(--c-dim); margin-top:12px; padding:10px 14px; background:rgba(124,111,247,0.06); border-left:3px solid var(--c-purple); border-radius:0 8px 8px 0; }
.hero-badges { display:flex; flex-direction:column; gap:10px; }
.hb-item { display:flex; flex-direction:column; align-items:center; padding:10px 14px; border-radius:12px; background:var(--c-card); border:1px solid var(--c-border); min-width:70px; }
.hb-icon { font-size:16px; margin-bottom:2px; }
.hb-val { font-size:22px; font-weight:800; color:var(--bc); font-family:'JetBrains Mono',monospace; }
.hb-label { font-size:9px; color:var(--c-dim); text-transform:uppercase; letter-spacing:0.5px; font-weight:600; }

/* ═══ VEREDICTO ═══ */
.hero-veredicto { display:inline-flex; align-items:center; gap:6px; padding:6px 18px; border-radius:20px; font-size:13px; font-weight:800; letter-spacing:1px; border:2px solid; text-transform:uppercase; margin-bottom:10px; }

/* ═══ CEO BRIEFING ═══ */
.ceo-section { background:linear-gradient(135deg, rgba(0,229,195,0.04), rgba(124,111,247,0.03)); }
.ceo-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.ceo-card { background:var(--c-card); border:1px solid var(--c-border); border-radius:12px; padding:16px; transition:border-color .2s; }
.ceo-card:hover { border-color:var(--c-accent); }
.ceo-label { font-size:9px; font-weight:700; letter-spacing:1.5px; color:var(--c-dim); text-transform:uppercase; margin-bottom:8px; }
.ceo-value { font-size:12px; font-weight:600; color:var(--c-text); line-height:1.4; }
.ceo-risk { color:var(--c-danger); }

/* ═══ KPI STRIP ═══ */
.kpi-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:24px; }
.kpi-card { word-break:break-word; overflow-wrap:anywhere; background:var(--c-card); border:1px solid var(--c-border); border-radius:12px; padding:16px 18px; }
.kpi-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.kpi-name { font-size:11px; color:var(--c-muted); font-weight:500; }
.kpi-trend { font-size:14px; font-weight:700; }
.kpi-trend.up { color:var(--c-accent); }
.kpi-trend.down { color:var(--c-danger); }
.kpi-trend.stable { color:var(--c-dim); }
.kpi-val { font-size:clamp(13px,1.8vw,16px); font-weight:800; color:var(--c-text); font-family:'JetBrains Mono',monospace; }

/* ═══ SECTION COMMON ═══ */
.rpt-section { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--c-radius); padding:clamp(20px,3vw,28px); margin-bottom:20px; }
.sec-header { display:flex; align-items:center; gap:10px; margin-bottom:20px; padding-bottom:14px; border-bottom:1px solid var(--c-border); }
.sec-header h3 { font-size:clamp(15px,2vw,18px); font-weight:700; color:var(--c-text); flex:1; }
.sec-icon { font-size:20px; }
.sec-count { background:var(--c-accent); color:#09090f; font-size:12px; font-weight:800; width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; }
.sec-header-sm { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; font-size:13px; font-weight:600; color:var(--c-text); }

/* ═══ CHARTS ═══ */
.rpt-charts { display:grid; grid-template-columns:1.5fr 1fr; gap:16px; margin-bottom:24px; }
.chart-card { background:var(--c-surface); border:1px solid var(--c-border); border-radius:var(--c-radius); padding:20px; }
.evo-chart { width:100%; height:auto; }
.chart-legend { display:flex; gap:12px; font-size:11px; color:var(--c-muted); }
.leg-tw { color:#1da1f2; } .leg-rd { color:#ff4500; } .leg-tot { color:#00e5c3; }

/* Sentiment */
.sent-bars { display:flex; flex-direction:column; gap:12px; margin-top:12px; }
.sent-row { display:flex; align-items:center; gap:8px; }
.sent-plat { font-size:11px; color:var(--c-muted); width:50px; font-weight:600; }
.sent-bar-wrap { flex:1; height:20px; border-radius:10px; background:var(--c-card); display:flex; overflow:hidden; }
.sent-pos { background:var(--c-accent); transition:width .5s; } .sent-neu { background:#6b6b80; transition:width .5s; } .sent-neg { background:var(--c-danger); transition:width .5s; }
.sent-pct { font-size:11px; color:var(--c-muted); font-weight:600; width:32px; text-align:right; font-family:'JetBrains Mono',monospace; }
.sent-legend { display:flex; gap:12px; margin-top:10px; font-size:10px; color:var(--c-dim); }
.sl-pos { color:var(--c-accent); } .sl-neu { color:#6b6b80; } .sl-neg { color:var(--c-danger); }

/* ═══ CENÁRIOS ═══ */
.prob-bar-wrap { margin-bottom:20px; }
.prob-label { font-size:11px; color:var(--c-dim); font-weight:600; margin-bottom:6px; text-transform:uppercase; letter-spacing:1px; }
.prob-bar { display:flex; height:28px; border-radius:14px; overflow:hidden; background:var(--c-card); }
.prob-seg { transition:width .8s cubic-bezier(0.16,1,0.3,1); min-width:2%; }
.prob-legend { display:flex; gap:16px; margin-top:8px; font-size:11px; color:var(--c-muted); flex-wrap:wrap; }
.pl-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; vertical-align:middle; }
.cenario-cards { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }
.cenario-card { background:var(--cci); border:1px solid var(--cc); border-left:4px solid var(--cc); border-radius:12px; padding:18px; }
.cc-header { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:10px; }
.cc-header h4 { font-size:14px; font-weight:700; color:var(--c-text); line-height:1.3; }
.cc-badge { font-size:10px; font-weight:700; padding:3px 10px; border-radius:20px; border:1px solid; white-space:nowrap; }
.cc-desc { font-size:12px; color:var(--c-muted); line-height:1.6; margin-bottom:12px; }
.cc-prob { display:flex; align-items:center; gap:8px; font-size:11px; color:var(--c-dim); }
.cc-prob-bar { flex:1; height:6px; background:var(--c-card); border-radius:3px; overflow:hidden; }
.cc-prob-bar div { height:100%; border-radius:3px; transition:width .8s; }

/* ═══ INSIGHTS ═══ */
.insights-list { display:flex; flex-direction:column; gap:10px; }
.insight-item { display:flex; gap:14px; align-items:flex-start; padding:14px 16px; background:var(--c-card); border-radius:10px; border:1px solid var(--c-border); }
.ins-num { font-size:14px; font-weight:800; color:var(--c-purple); background:rgba(124,111,247,0.1); width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.insight-item p { font-size:13px; color:var(--c-muted); line-height:1.6; }

/* ═══ RISKS ═══ */
.risk-cards { display:flex; flex-direction:column; gap:12px; }
.risk-card { background:var(--c-card); border:1px solid var(--c-border); border-left:4px solid var(--rc); border-radius:12px; padding:18px; }
.rc-header { display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:8px; }
.rc-header h4 { font-size:14px; font-weight:700; color:var(--c-text); }
.rc-badge { font-size:10px; font-weight:700; padding:3px 10px; border-radius:20px; white-space:nowrap; }
.rc-desc { font-size:12px; color:var(--c-muted); line-height:1.6; margin-bottom:12px; }
.rc-prob { display:flex; align-items:center; gap:8px; font-size:11px; color:var(--c-dim); }
.rc-prob-bar { flex:1; height:6px; background:rgba(255,255,255,0.04); border-radius:3px; overflow:hidden; }
.rc-prob-bar div { height:100%; border-radius:3px; transition:width .8s; }

/* ═══ RECOMMENDATIONS ═══ */
.rec-cards { display:flex; flex-direction:column; gap:12px; }
.rec-card { display:flex; gap:14px; background:var(--c-card); border:1px solid var(--c-border); border-radius:12px; padding:18px; }
.rec-num { font-size:16px; font-weight:800; color:var(--c-accent); background:rgba(0,229,195,0.08); width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-family:'JetBrains Mono',monospace; }
.rec-body { flex:1; min-width:0; }
.rec-top { display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:6px; }
.rec-top h4 { font-size:14px; font-weight:700; color:var(--c-text); }
.rec-urg { font-size:10px; font-weight:700; padding:3px 10px; border-radius:20px; white-space:nowrap; }
.rec-body p { font-size:12px; color:var(--c-muted); line-height:1.6; }
.rec-prazo { font-size:11px; color:var(--c-dim); margin-top:8px; }

/* ═══ PREDICTIONS ═══ */
.prev-list { display:flex; flex-direction:column; gap:10px; }
.prev-item { display:flex; gap:14px; align-items:flex-start; padding:14px 16px; background:var(--c-card); border-radius:10px; border:1px solid var(--c-border); }
.prev-num { font-size:14px; font-weight:800; color:var(--c-gold); background:rgba(245,166,35,0.1); width:28px; height:28px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-family:'JetBrains Mono',monospace; }
.prev-item p { font-size:13px; color:var(--c-muted); line-height:1.6; }

/* ═══ DEEP ANALYSIS ═══ */
.deep-tabs { display:flex; gap:4px; margin-bottom:16px; flex-wrap:wrap; }
.dt-btn { background:var(--c-card); border:1px solid var(--c-border); border-radius:8px; padding:8px 14px; font-size:12px; color:var(--c-muted); cursor:pointer; transition:all .2s; font-weight:500; }
.dt-btn.active { background:var(--c-accent); color:#09090f; font-weight:700; border-color:var(--c-accent); }
.dt-btn:hover:not(.active) { border-color:var(--c-accent); color:var(--c-text); }
.deep-content { font-size:13px; color:var(--c-muted); line-height:1.8; }

/* ═══ WORD CLOUD ═══ */
.wc-wrap { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:baseline; justify-content:center; padding:20px; }
.wc-word { font-weight:600; transition:transform .2s; cursor:default; }
.wc-word:hover { transform:scale(1.15); }

/* ═══ POSTS ═══ */
.posts-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:12px; }
.post-card { background:var(--c-card); border:1px solid var(--c-border); border-radius:10px; padding:14px; }
.pc-head { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.pc-plat { font-size:14px; } .pc-plat.twitter { color:#1da1f2; } .pc-plat.reddit { color:#ff4500; }
.pc-user { font-size:12px; font-weight:600; color:var(--c-text); flex:1; }
.pc-likes { font-size:11px; color:var(--c-muted); }
.pc-text { font-size:12px; color:var(--c-muted); line-height:1.5; }

/* ═══ CTA ═══ */
.rpt-cta { text-align:center; padding:40px; background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid var(--c-border); border-radius:var(--c-radius); margin-top:8px; }
.rpt-cta h3 { font-size:18px; color:var(--c-text); margin-bottom:8px; }
.rpt-cta p { font-size:13px; color:var(--c-muted); margin-bottom:20px; max-width:500px; margin-left:auto; margin-right:auto; line-height:1.6; }

/* ═══ MARKDOWN BODY ═══ */
.md-body :deep(p) { margin-bottom:10px; color:var(--c-muted); font-size:13px; line-height:1.75; }
.md-body :deep(strong) { color:var(--c-text); font-weight:600; }
.md-body :deep(blockquote) { border-left:3px solid var(--c-purple); padding:8px 14px; margin:12px 0; background:rgba(124,111,247,0.05); border-radius:0 8px 8px 0; font-style:italic; }
.md-body :deep(ul), .md-body :deep(ol) { padding-left:20px; margin:8px 0; }
.md-body :deep(li) { margin-bottom:4px; color:var(--c-muted); font-size:13px; line-height:1.6; }
.md-body :deep(h1), .md-body :deep(h2), .md-body :deep(h3), .md-body :deep(h4) { color:var(--c-text); margin:16px 0 8px; }

/* ═══ LAYER LABELS ═══ */
.layer-label { display:flex; align-items:center; gap:8px; padding:8px 16px; margin:28px 0 12px; font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--c-dim); border-left:3px solid var(--c-accent); background:linear-gradient(90deg, rgba(0,229,195,0.04), transparent); border-radius:0 8px 8px 0; }
.ll-icon { font-size:14px; }

/* ═══ STACK RANKING — #1 HIGHLIGHTED ═══ */
.rec-highlight { border:2px solid var(--c-accent) !important; background:linear-gradient(135deg, rgba(0,229,195,0.06), rgba(124,111,247,0.03)) !important; position:relative; }
.rec-highlight::after { content:'#1 PRIORIDADE'; position:absolute; top:-10px; right:16px; background:var(--c-accent); color:#09090f; font-size:9px; font-weight:800; padding:2px 10px; border-radius:10px; letter-spacing:1px; }
.rec-highlight .rec-num { background:var(--c-accent) !important; color:#09090f !important; font-size:18px; width:40px; height:40px; }

/* ═══ VALOR DA ANÁLISE ═══ */
.valor-section { background:linear-gradient(135deg, rgba(245,166,35,0.04), rgba(0,229,195,0.03)) !important; border-color:rgba(245,166,35,0.2) !important; }

/* ═══ TABS ═══ */
.rpt-tabs { display:flex; gap:4px; background:var(--c-card); border:1px solid var(--c-border); border-radius:14px; padding:6px; margin-bottom:28px; z-index:10; }
.rpt-tab { flex:1; padding:12px 16px; border:none; background:none; border-radius:10px; font-size:13px; font-weight:600; color:var(--c-muted); cursor:pointer; transition:all .2s; white-space:nowrap; }
.rpt-tab:hover { background:rgba(255,255,255,0.04); color:var(--c-text); }
.rpt-tab-on { background:var(--c-accent) !important; color:#09090f !important; box-shadow:0 2px 8px rgba(0,229,195,0.25); }

/* ═══ COLLAPSIBLE ═══ */
.sec-collapsible { cursor:pointer; user-select:none; }
.sec-collapsible:hover { opacity:0.85; }
.sec-toggle { font-size:14px; color:var(--c-dim); margin-left:auto; }
.sec-collapse { max-height:200px; overflow:hidden; position:relative; transition:max-height .4s ease; }
.sec-collapse::after { content:''; position:absolute; bottom:0; left:0; right:0; height:80px; background:linear-gradient(rgba(255,255,255,0), #ffffff); pointer-events:none; z-index:1; }
.sec-collapse.sec-open { max-height:none; overflow:visible; }
.sec-collapse.sec-open::after { display:none; }

/* ═══ CONTEXT PAGE ═══ */
.ctx-page { background:linear-gradient(135deg, rgba(124,111,247,0.06), rgba(0,229,195,0.04)); border:1px solid rgba(124,111,247,0.15); border-radius:20px; padding:32px; margin-bottom:24px; }
.ctx-header { display:flex; gap:16px; align-items:center; margin-bottom:20px; }
.ctx-logo { font-size:36px; }
.ctx-title { font-size:20px; font-weight:700; color:var(--c-text); line-height:1.3; }
.ctx-sub { font-size:12px; color:var(--c-dim); margin-top:2px; }
.ctx-grid { display:grid; grid-template-columns:1fr auto; gap:20px; margin-bottom:16px; }
.ctx-card { background:var(--c-card); border:1px solid var(--c-border); border-radius:14px; padding:18px; }
.ctx-icon { font-size:18px; }
.ctx-label { font-size:9px; font-weight:700; letter-spacing:1.5px; color:var(--c-dim); text-transform:uppercase; margin:6px 0 8px; }
.ctx-value { font-size:14px; color:var(--c-muted); line-height:1.65; }
.ctx-hipotese { font-style:italic; }
.ctx-stats { display:flex; flex-direction:column; gap:8px; justify-content:center; }
.ctx-stat { display:flex; align-items:center; gap:10px; background:var(--c-card); border:1px solid var(--c-border); border-radius:10px; padding:10px 16px; min-width:140px; }
.ctx-stat-val { font-size:18px; font-weight:800; color:var(--c-accent); font-family:'JetBrains Mono',monospace; }
.ctx-stat-lbl { font-size:11px; color:var(--c-dim); font-weight:600; }
.ctx-disclaimer { font-size:11px; color:var(--c-dim); line-height:1.6; padding-top:14px; border-top:1px solid var(--c-border); }

/* ═══ CLOSING PAGE ═══ */
.closing-page { background:linear-gradient(135deg, rgba(0,229,195,0.04), rgba(124,111,247,0.06)); border:2px solid rgba(0,229,195,0.15); border-radius:20px; padding:40px 32px; margin:32px 0 24px; text-align:center; }
.closing-inner { max-width:700px; margin:0 auto; }
.closing-verdict { display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:16px; }
.closing-icon { font-size:36px; }
.closing-verdict h2 { font-size:28px; font-weight:800; letter-spacing:2px; }
.closing-summary { font-size:14px; color:var(--c-muted); line-height:1.7; margin-bottom:28px; max-width:600px; margin-left:auto; margin-right:auto; }
.closing-trio { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:32px; }
.closing-item { background:var(--c-card); border:1px solid var(--c-border); border-radius:14px; padding:20px 16px; }
.ci-action { border-color:rgba(0,229,195,0.3); background:rgba(0,229,195,0.04); }
.ci-icon { font-size:22px; display:block; margin-bottom:8px; }
.closing-item h4 { font-size:10px; font-weight:700; letter-spacing:1px; color:var(--c-dim); text-transform:uppercase; margin-bottom:8px; }
.closing-item p { font-size:13px; color:var(--c-text); font-weight:600; line-height:1.4; }
.closing-footer { padding-top:24px; border-top:1px solid var(--c-border); }
.closing-brand { display:flex; align-items:center; justify-content:center; gap:8px; font-size:16px; font-weight:700; color:var(--c-accent); margin-bottom:6px; }
.closing-logo { font-size:20px; }
.closing-tagline { font-size:12px; color:var(--c-dim); font-style:italic; }

/* ═══ REC TOP ROW ═══ */
.rec-top-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }

/* ═══ RESPONSIVE CONTEXT/CLOSING ═══ */
@media (max-width:768px) { .ctx-grid { grid-template-columns:1fr; } .ctx-stats { flex-direction:row; flex-wrap:wrap; } .closing-trio { grid-template-columns:1fr; } }

/* ═══ PRINT ═══ */
@media print {
  .rpt-topbar, nav, aside, .tb-btn, .cta-section, .rpt-tabs { display:none !important; }
  .rpt-wrap { max-width:100% !important; padding:0 !important; margin:0 !important; }
  .rpt-wrap > div[v-show], .rpt-wrap > div { display:block !important; visibility:visible !important; }
  .rpt-section { break-inside:avoid; page-break-inside:avoid; margin-bottom:16px; }
  .rpt-hero { break-after:page; }
  .closing-page { break-before:page; }
  .ctx-page { break-after:page; }
  .sec-collapse { max-height:none !important; overflow:visible !important; }
  .sec-collapse::after { display:none !important; }
  .sec-toggle { display:none !important; }
  * { color-adjust:exact !important; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
  body, html { overflow:visible !important; }
}
/* ═══ PRINT ═══ */
@media print {
  .rpt-topbar, .tb-actions, .rpt-cta { display:none !important; }
  .rpt-wrap { max-width:100%; padding:0; }
  .rpt-section, .rpt-hero, .chart-card { break-inside:avoid; border:1px solid #ddd; }
  * { color:#222 !important; background:white !important; }
  .prob-seg, .sent-pos, .sent-neg, .cc-prob-bar div, .rc-prob-bar div { print-color-adjust:exact; -webkit-print-color-adjust:exact; }
}

/* ═══ RESPONSIVE ═══ */
@media (max-width:768px) {
  .rpt-hero { grid-template-columns:1fr; text-align:center; }
  .hero-badges { flex-direction:row; justify-content:center; }
  .ceo-grid { grid-template-columns:1fr 1fr; }
  .cenario-cards { grid-template-columns:1fr; }
  .rpt-charts { grid-template-columns:1fr; }
  .posts-grid { grid-template-columns:1fr; }
}
</style>
