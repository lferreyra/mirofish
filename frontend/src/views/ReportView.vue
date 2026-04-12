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

function scrollTo(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

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
const projectName = computed(() => report.value?.project_name || str.value?.meta?.projeto || '')
const clientName = computed(() => {
  const pn = projectName.value
  if (pn.includes(' — ')) return pn.split(' — ')[0].trim()
  if (pn.includes(' - ')) return pn.split(' - ')[0].trim()
  return ''
})
const projectLabel = computed(() => {
  const pn = projectName.value
  if (pn.includes(' — ')) return pn.split(' — ').slice(1).join(' — ').trim()
  if (pn.includes(' - ')) return pn.split(' - ').slice(1).join(' - ').trim()
  return pn
})
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
  let decisao = (parsedRecomendacoes.value?.[0]?.name || '').replace(/\*\*/g, '').replace(/^#+\s*/g, '').replace(/^\d+[.)\s]*/,'').split(';')[0].split(',').slice(0,2).join(',').trim()
  if (!decisao) {
    const resumo = secResumo.value?.content || ''
    const decMatch = resumo.match(/(?:recomend|suger|deve|precis)[^.]*\./) 
    decisao = decMatch ? decMatch[0].replace(/\*\*/g, '').trim().slice(0, 120) : 'Revisar detalhes no relatório completo'
  }
  
  // Risco: do parser OU extrair do resumo
  let risco = (parsedRiscos.value?.[0]?.name || '').replace(/\*\*/g, '').replace(/^#+\s*/g, '').replace(/^\d+[.)\s]*/,'').split(':')[0].trim()
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
  // Preferir structured se disponível
  const s = report.value?.structured?.veredicto
  if (s) {
    const tipo = (s.tipo || '').toUpperCase()
    if (tipo.includes('NO-GO') || tipo.includes('NOGO') || tipo.includes('NÃO')) return { label: 'NÃO LANÇAR', color: '#ff5a5a', icon: '🔴', score: s.score_viabilidade, frase: s.frase_chave, resumo: s.resumo_executivo, acao: s.leitura_para_decisao, fatos: s.top5_fatos || [] }
    if (tipo.includes('AJUSTAR')) return { label: 'AJUSTAR ANTES', color: '#f5a623', icon: '🟡', score: s.score_viabilidade, frase: s.frase_chave, resumo: s.resumo_executivo, acao: s.leitura_para_decisao, fatos: s.top5_fatos || [] }
    if (tipo.includes('GO') || tipo.includes('LANÇAR')) return { label: 'LANÇAR', color: '#00e5c3', icon: '🟢', score: s.score_viabilidade, frase: s.frase_chave, resumo: s.resumo_executivo, acao: s.leitura_para_decisao, fatos: s.top5_fatos || [] }
    return { label: tipo || 'EM ANÁLISE', color: '#8888aa', icon: '⚪', score: s.score_viabilidade, frase: s.frase_chave, resumo: s.resumo_executivo, acao: s.leitura_para_decisao, fatos: s.top5_fatos || [] }
  }
  // Fallback texto
  const sum = (report.value?.outline?.summary || '').toUpperCase()
  const content = (secResumo.value?.content || '').toUpperCase()
  const all = sum + ' ' + content
  if (all.includes('NÃO LANÇAR') || all.includes('NO-GO') || all.includes('NOGO')) return { label: 'NÃO LANÇAR', color: '#ff5a5a', icon: '🔴' }
  if (all.includes('AJUSTAR') || all.includes('ADJUST')) return { label: 'AJUSTAR ANTES', color: '#f5a623', icon: '🟡' }
  if (all.includes('LANÇAR') || all.includes('GO')) return { label: 'LANÇAR', color: '#00e5c3', icon: '🟢' }
  return { label: 'EM ANÁLISE', color: '#8888aa', icon: '⚪' }
})

// ─── STRUCTURED DATA (Pipeline v2) ──────────────────────────
const hasStructured = computed(() => !!report.value?.structured)
const str = computed(() => report.value?.structured || {})

const strDashboard = computed(() => {
  const d = str.value?.dashboard || {}
  if (!d || Object.keys(d).length < 3) return null
  const kpis = [
    { k: 'ticket_medio', label: 'Ticket Médio', icon: '💰' },
    { k: 'volume_breakeven', label: 'Break-even', icon: '📊' },
    { k: 'margem_bruta_alvo', label: 'Margem Bruta', icon: '📈' },
    { k: 'capital_giro_necessario', label: 'Capital de Giro', icon: '🏦' },
    { k: 'recompra_alvo', label: 'Recompra', icon: '🔄' },
    { k: 'prob_sobrevivencia_24m', label: 'Sobrevivência 24m', icon: '🎯' },
    { k: 'faturamento_maduro', label: 'Faturamento Maduro', icon: '💎' },
    { k: 'investimento_total_estimado', label: 'Investimento Total', icon: '💼' },
    { k: 'conversao_inicial', label: 'Conversão Inicial', icon: '🎪' },
    { k: 'contatos_mes_inicial', label: 'Contatos/Mês', icon: '📞' },
    { k: 'breakeven_cenario1', label: 'Break-even Período', icon: '📅' },
    { k: 'vendas_por_indicacao', label: 'Vendas Indicação', icon: '🤝' },
    { k: 'erosao_margem_sazonal', label: 'Erosão Sazonal', icon: '📉' },
  ].filter(kpi => d[kpi.k])
  return kpis.map(kpi => ({ ...kpi, valor: d[kpi.k] }))
})

const strCenarios = computed(() => {
  const c = str.value?.cenarios?.cenarios || []
  if (!c.length) return null
  const colors = ['#00e5c3', '#f5a623', '#ff5a5a']
  return c.map((cen, i) => ({ ...cen, color: colors[i] || '#8888aa' }))
})

const strRiscos = computed(() => {
  const r = str.value?.riscos?.riscos || []
  if (!r.length) return null
  return r.map(risco => ({
    ...risco,
    impactoColor: risco.impacto === 'CRITICO' ? '#ff5a5a' : risco.impacto === 'ALTO' ? '#f5a623' : risco.impacto === 'MODERADO' ? '#7c6ff7' : '#00e5c3',
    probWidth: risco.probabilidade || 50,
  }))
})

const strRecomendacoes = computed(() => str.value?.recomendacoes || null)
const strPrevisoes = computed(() => str.value?.previsoes || null)
const strCronologia = computed(() => str.value?.cronologia?.fases || null)
const strRoi = computed(() => str.value?.roi || null)
const strSintese = computed(() => str.value?.sintese || null)
const strChecklist = computed(() => str.value?.checklist || null)
const strPosicionamento = computed(() => str.value?.posicionamento || null)
const strEmocional = computed(() => str.value?.emocional || null)
const strAgentes = computed(() => str.value?.agentes || null)
const strForcas = computed(() => str.value?.forcas || null)

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
      const label = m[1].trim().replace(/\*\*/g,'').replace(/^[-#\d.)\s]+/,'').replace(/:/g,'').trim()
      const valor = m[2].trim().replace(/\*\*/g,'').replace(/^[-#\s]+/,'').trim().slice(0, 50)
      if (label.length > 3 && label.length < 50 && !label.toLowerCase().includes('seção')) {
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
const wordCloudWords = computed(() => {
  const text = secoes.value.map(s => s.content || '').join(' ')
  const words = text.toLowerCase().replace(/[^a-záàâãéèêíïóôõúüçñ\s]/gi, ' ').split(/\s+/)
  const freq = {}
  const stop = new Set(['que','para','com','uma','por','como','mais','mas','não','nao','dos','das','esse','essa','este','esta','são','ser','tem','pode','seu','sua','foi','quando','entre','sobre','muito','sem','nos','pelo','pela','até','ela','ele','isso','isto','cada','após','onde','bem','ainda','mesmo','todo','toda','já','ou','ao','aos','num','numa','ter','ver','dar','fazer','suas','seus'])
  words.forEach(w => { if (w.length > 3 && !stop.has(w)) freq[w] = (freq[w]||0) + 1 })
  return Object.entries(freq)
    .sort((a,b) => b[1] - a[1])
    .slice(0, 30)
    .map(([text, count], i, arr) => {
      const maxCount = arr[0]?.[1] || 1
      const ratio = count / maxCount
      return { text, size: Math.round(12 + ratio * 26) }
    })
})

const secoesExtras = computed(() => {
  const known = ['resumo','cenarios','riscos','recomendacoes','emocional','comunicacao','posicionamento','previsoes','insights','deep_mapa','deep_cronologia','deep_padroes','deep_hipoteses','valor']
  return secoes.value.filter(s => !known.includes(categ(s.title)))
})

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
    <div v-if="carregando" class="aug-loading">
      <div class="aug-spinner"></div>
      <p>Gerando relatório de previsão...</p>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="aug-error">
      <div class="aug-err-icon">⚠️</div>
      <h3>Não foi possível carregar o relatório</h3>
      <p>{{ erro }}</p>
      <AugurButton @click="$router.go(-1)">Voltar</AugurButton>
    </div>

    <!-- ═══ REPORT ═══ -->
    <div v-else class="aug-report">

      <!-- HEADER -->
      <header class="aug-header">
        <div class="aug-header-top">
          <div class="aug-breadcrumb">
            <span @click="router.push('/')">Dashboard</span>
            <span class="aug-bc-sep">›</span>
            <span>Relatório</span>
          </div>
          <div class="aug-actions">
            <button class="aug-btn-ghost" @click="router.push(`/projeto/${report?.project_id}`)" v-if="report?.project_id">← Projeto</button>
            <button class="aug-btn-ghost" @click="router.push(`/agentes/${route.params.reportId}`)">🧠 Agentes</button>
            <button class="aug-btn-ghost" @click="router.push(`/simulacao/${report?.simulation_id}/posts`)" v-if="report?.simulation_id">📝 Posts</button>
            <button class="aug-btn-ghost" @click="router.push(`/simulacao/${report?.simulation_id}/influentes`)" v-if="report?.simulation_id">👑 Influentes</button>
            <button class="aug-btn-ghost" @click="compartilhar()" :disabled="shareLoading">🔗 {{ shareLoading ? '...' : 'Compartilhar' }}</button>
            <button class="aug-btn-primary" @click="exportarPDF()">📄 Exportar PDF</button>
          </div>
        </div>
        <div v-if="projectName" class="aug-project-badge">
          <span class="aug-project-client" v-if="clientName">{{ clientName }}</span>
          <span class="aug-project-name">{{ projectLabel }}</span>
        </div>
        <h1 class="aug-title">{{ titulo }}</h1>
        <p class="aug-subtitle" v-if="geradoEm">{{ geradoEm }}</p>
      </header>

      <!-- LAYOUT: NAV + CONTENT -->
      <div class="aug-layout">

        <!-- SIDEBAR NAV -->
        <nav class="aug-nav">
          <div class="aug-nav-inner">
            <a class="aug-nav-item aug-nav-active" @click="scrollTo('ctx')">Contexto</a>
            <a class="aug-nav-item" @click="scrollTo('resumo')">Resumo Executivo</a>
            <a v-if="strDashboard" class="aug-nav-item" @click="scrollTo('dashboard')">Dashboard</a>
            <a class="aug-nav-item" @click="scrollTo('ceo')">Briefing CEO</a>
            <a class="aug-nav-item" @click="scrollTo('cenarios')">Cenários</a>
            <a class="aug-nav-item" @click="scrollTo('insights')" v-if="secInsights?.content || achadosRelevantes.length">Insights</a>
            <a class="aug-nav-item" @click="scrollTo('emocional')" v-if="secEmocional?.content">Emocional</a>
            <a class="aug-nav-item" @click="scrollTo('riscos')">Riscos</a>
            <a class="aug-nav-item" @click="scrollTo('recs')">Recomendações</a>
            <a class="aug-nav-item" @click="scrollTo('comm')" v-if="secComunicacao?.content">Comunicação</a>
            <a class="aug-nav-item" @click="scrollTo('posic')" v-if="secPosicionamento?.content">Posicionamento</a>
            <a class="aug-nav-item" @click="scrollTo('previsoes')">Previsões</a>
            <a class="aug-nav-item" @click="scrollTo('profunda')">Análise Profunda</a>
            <a class="aug-nav-item" @click="scrollTo('closing')">Conclusão</a>
          </div>
        </nav>

        <!-- MAIN CONTENT -->
        <main class="aug-main">

          <!-- TABS -->
          <nav class="aug-tabs">
            <button class="aug-tab" :class="{'aug-tab-on': activeTab==='decisao'}" @click="activeTab='decisao'">⚡ Decisão</button>
            <button class="aug-tab" :class="{'aug-tab-on': activeTab==='analise'}" @click="activeTab='analise'">📊 Análise</button>
            <button class="aug-tab" :class="{'aug-tab-on': activeTab==='estrategia'}" @click="activeTab='estrategia'">🎯 Estratégia</button>
            <button class="aug-tab" :class="{'aug-tab-on': activeTab==='profunda'}" @click="activeTab='profunda'">🔬 Profunda</button>
          </nav>

          <!-- CONTEXTO (sempre visível) -->
          <section id="ctx" class="aug-card aug-card-accent">
            <div class="aug-ctx-row">
              <div class="aug-ctx-left">
                <div class="aug-ctx-badge">📋 HIPÓTESE TESTADA</div>
                <p class="aug-ctx-text">{{ truncar(simReq || 'Não disponível', 300) }}</p>
              </div>
              <div class="aug-ctx-stats">
                <div class="aug-stat"><span class="aug-stat-val">{{ report?.outline?.sections?.length || 0 }}</span><span class="aug-stat-label">seções</span></div>
                <div class="aug-stat"><span class="aug-stat-val">{{ confianca }}%</span><span class="aug-stat-label">confiança</span></div>
                <div class="aug-stat"><span class="aug-stat-val">{{ cenarios.length }}</span><span class="aug-stat-label">cenários</span></div>
              </div>
            </div>
            <p class="aug-disclaimer">Esta análise simula a reação de agentes autônomos ao cenário descrito. Os resultados representam cenários possíveis e não garantem resultados futuros.</p>
          </section>

          <!-- TAB: DECISÃO -->
          <div v-show="activeTab==='decisao' || printMode">

          <!-- RESUMO EXECUTIVO -->
          <section id="resumo" class="aug-card">
            <div class="aug-card-header">
              <div class="aug-veredicto" :style="{background: veredicto.color + '12', color: veredicto.color, borderColor: veredicto.color + '33'}">
                {{ veredicto.icon }} {{ veredicto.label }}
              </div>
              <div class="aug-gauge" v-if="veredicto.score">
                <svg viewBox="0 0 80 50" class="aug-gauge-svg">
                  <path d="M 8 42 A 32 32 0 0 1 72 42" fill="none" stroke="#e8e8ef" stroke-width="7" stroke-linecap="round"/>
                  <path :d="gaugePath(veredicto.score)" fill="none" stroke="url(#gGrad)" stroke-width="7" stroke-linecap="round"/>
                  <defs><linearGradient id="gGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7c6ff7"/><stop offset="100%" stop-color="#00e5c3"/></linearGradient></defs>
                  <text x="40" y="38" text-anchor="middle" fill="#1a1a2e" font-size="16" font-weight="800">{{ veredicto.score }}%</text>
                </svg>
              </div>
              <div class="aug-gauge" v-else>
                <svg viewBox="0 0 80 50" class="aug-gauge-svg">
                  <path d="M 8 42 A 32 32 0 0 1 72 42" fill="none" stroke="#e8e8ef" stroke-width="7" stroke-linecap="round"/>
                  <path :d="gaugePath(confianca)" fill="none" stroke="url(#gGrad2)" stroke-width="7" stroke-linecap="round"/>
                  <defs><linearGradient id="gGrad2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7c6ff7"/><stop offset="100%" stop-color="#00e5c3"/></linearGradient></defs>
                  <text x="40" y="38" text-anchor="middle" fill="#1a1a2e" font-size="16" font-weight="800">{{ confianca }}%</text>
                </svg>
              </div>
            </div>

            <!-- Structured: frase-chave + fatos -->
            <template v-if="veredicto.frase">
              <h2 class="aug-section-title">Resumo Executivo</h2>
              <p class="aug-frase-chave" :style="{color: veredicto.color}">{{ veredicto.frase }}</p>
              <div v-if="veredicto.resumo" class="aug-prose" v-html="md(veredicto.resumo)"></div>
              <div v-if="veredicto.acao" class="aug-acao-box">
                <div class="aug-acao-label">📌 O que fazer segunda-feira:</div>
                <div class="aug-acao-text">{{ veredicto.acao }}</div>
              </div>
              <div v-if="veredicto.fatos?.length" class="aug-fatos">
                <div class="aug-fatos-title">Top {{ veredicto.fatos.length }} fatos decisivos</div>
                <div v-for="(f, i) in veredicto.fatos" :key="i" class="aug-fato">
                  <span class="aug-fato-num">{{ i+1 }}</span>
                  <div><strong>{{ f.titulo }}</strong><br><span class="aug-fato-desc">{{ f.descricao }}</span></div>
                </div>
              </div>
            </template>

            <!-- Fallback: texto livre -->
            <template v-else>
              <h2 class="aug-section-title">Resumo Executivo</h2>
              <div v-if="secResumo?.content" class="aug-prose" 
                   :class="{'aug-collapsed': !isExpanded('resumo')}"
                   v-html="md(secResumo.content)"></div>
              <button v-if="secResumo?.content?.length > 500" class="aug-expand" @click="toggleSection('resumo')">
                {{ isExpanded('resumo') ? '▲ Recolher' : '▼ Ver resumo completo' }}
              </button>
            </template>
          </section>

          <!-- DASHBOARD KPIs (structured only) -->
          <section v-if="strDashboard" id="dashboard" class="aug-card">
            <h2 class="aug-section-title">📊 Dashboard de Indicadores</h2>
            <div class="aug-kpi-grid">
              <div v-for="kpi in strDashboard" :key="kpi.k" class="aug-kpi">
                <span class="aug-kpi-icon">{{ kpi.icon }}</span>
                <div class="aug-kpi-val">{{ kpi.valor }}</div>
                <div class="aug-kpi-label">{{ kpi.label }}</div>
              </div>
            </div>
          </section>

          <!-- BRIEFING CEO -->
          <section id="ceo" class="aug-card">
            <h2 class="aug-section-title">🧭 Briefing CEO — 1 Minuto</h2>
            <div class="aug-ceo-grid">
              <div class="aug-ceo-item">
                <div class="aug-ceo-label">DECISÃO</div>
                <div class="aug-ceo-val">{{ (briefingCEO.decisao || '').replace(/\*\*/g,'').replace(/^#+\s*/g,'').slice(0,150) }}</div>
              </div>
              <div class="aug-ceo-item">
                <div class="aug-ceo-label">CENÁRIO PROVÁVEL</div>
                <div class="aug-ceo-val">{{ (briefingCEO.cenario || '').replace(/\*\*/g,'').slice(0,150) }}</div>
              </div>
              <div class="aug-ceo-item">
                <div class="aug-ceo-label">RISCO CRÍTICO</div>
                <div class="aug-ceo-val">{{ (briefingCEO.risco || '').replace(/\*\*/g,'').replace(/^#+\s*/g,'').slice(0,150) }}</div>
              </div>
              <div class="aug-ceo-item">
                <div class="aug-ceo-label">SENTIMENTO</div>
                <div class="aug-ceo-val">{{ briefingCEO.sentimento || 'Neutro' }}</div>
              </div>
            </div>
            <div class="aug-kpi-row" v-if="kpiCards.length">
              <div v-for="k in kpiCards" :key="k.label" class="aug-kpi">
                <div class="aug-kpi-label">{{ (k.label || '').replace(/\*\*/g,'') }}</div>
                <div class="aug-kpi-val">{{ (k.valor || '').replace(/\*\*/g,'').slice(0,50) }}</div>
              </div>
            </div>
          </section>

          <!-- CENÁRIOS -->
          <section id="cenarios" class="aug-card" v-if="cenarios.length">
            <h2 class="aug-section-title">🎯 Cenários Futuros</h2>
            <div class="aug-prob-bar">
              <div v-for="c in cenarios" :key="c.nome" class="aug-prob-seg" :style="{width: c.prob+'%', background: c.cor}" :title="c.nome+': '+c.prob+'%'"></div>
            </div>
            <div class="aug-prob-legend">
              <span v-for="c in cenarios" :key="c.nome"><span class="aug-dot" :style="{background: c.cor}"></span>{{ c.nome }} {{ c.prob }}%</span>
            </div>
            <div class="aug-cenarios-grid" :class="{'aug-collapsed': !isExpanded('cenarios')}">
              <div v-for="c in cenarios" :key="c.nome" class="aug-cenario" :style="{'border-top-color': c.cor}">
                <div class="aug-cenario-head">
                  <h3>{{ c.nome }}</h3>
                  <span class="aug-cenario-badge" :style="{color: c.cor}">{{ c.impacto }}</span>
                </div>
                <p class="aug-cenario-desc" v-if="c.desc">{{ c.desc }}</p>
                <div class="aug-cenario-prob">
                  <span>Probabilidade</span>
                  <div class="aug-prob-mini"><div :style="{width: c.prob+'%', background: c.cor}"></div></div>
                  <strong :style="{color: c.cor}">{{ c.prob }}%</strong>
                </div>
              </div>
            </div>
          </section>

          </div><!-- /decisao -->

          <!-- TAB: ANÁLISE -->
          <div v-show="activeTab==='analise' || printMode">

          <!-- INSIGHTS -->
          <section id="insights" class="aug-card" v-if="secInsights?.content || achadosRelevantes.length">
            <h2 class="aug-section-title">💡 Insights Principais</h2>
            <div class="aug-insights" v-if="achadosRelevantes.length >= 2 && achadosRelevantes.every(a => a.text.length > 20)">
              <div v-for="(a, i) in achadosRelevantes" :key="i" class="aug-insight">
                <span class="aug-insight-num">{{ i + 1 }}</span>
                <p>{{ a.text }}</p>
              </div>
            </div>
            <div v-else-if="secInsights?.content" class="aug-prose" v-html="md(secInsights.content)"></div>
          </section>

          <!-- ANÁLISE EMOCIONAL -->
          <section id="emocional" class="aug-card" v-if="secEmocional?.content">
            <div class="aug-section-header" @click="toggleSection('emocional')">
              <h2 class="aug-section-title">🎭 Análise Emocional</h2>
              <span class="aug-toggle">{{ isExpanded('emocional') ? '−' : '+' }}</span>
            </div>
            <div class="aug-collapsible" :class="{'aug-open': isExpanded('emocional')}">
              <div class="aug-prose" v-html="md(secEmocional.content)"></div>
            </div>
          </section>

          <!-- RISCOS -->
          <section id="riscos" class="aug-card" v-if="secRiscos?.content || parsedRiscos.length">
            <h2 class="aug-section-title">⚠️ Fatores de Risco</h2>
            <div v-if="parsedRiscos.length >= 2" class="aug-risks">
              <div v-for="(r, i) in parsedRiscos" :key="i" class="aug-risk" :style="{'--rc': r.color}">
                <div class="aug-risk-head">
                  <h4>{{ r.name.replace(/[#*]/g,'').trim() }}</h4>
                  <span class="aug-risk-badge" :style="{color: r.color}">{{ r.impacto }}</span>
                </div>
                <p>{{ r.desc.replace(/\*\*/g,'').replace(/^#+\s*/g,'').slice(0,200) }}</p>
                <div class="aug-risk-bar">
                  <span>Probabilidade</span>
                  <div class="aug-bar-track"><div :style="{width: r.prob+'%', background: r.color}"></div></div>
                  <strong>{{ r.prob }}%</strong>
                </div>
              </div>
            </div>
            <div v-else-if="secRiscos?.content" class="aug-prose" v-html="md(secRiscos.content)"></div>
          </section>

          <!-- RECOMENDAÇÕES -->
          <section id="recs" class="aug-card" v-if="secRecomendacoes?.content || parsedRecomendacoes.length">
            <h2 class="aug-section-title">⚡ Recomendações Estratégicas</h2>
            <div v-if="parsedRecomendacoes.length >= 2" class="aug-recs">
              <div v-for="(r, i) in parsedRecomendacoes" :key="i" class="aug-rec" :class="{'aug-rec-top': i === 0}">
                <div class="aug-rec-num">{{ i + 1 }}</div>
                <div class="aug-rec-body">
                  <h4>{{ r.name.replace(/[#*]/g,'').trim() }}</h4>
                  <p>{{ r.desc.replace(/\*\*/g,'').replace(/^#+\s*/g,'').slice(0,250) }}</p>
                  <div class="aug-rec-meta" v-if="r.prazo">🕐 {{ r.prazo }}</div>
                </div>
              </div>
            </div>
            <div v-else-if="secRecomendacoes?.content" class="aug-prose" v-html="md(secRecomendacoes.content)"></div>
          </section>

          </div><!-- /analise -->

          <!-- TAB: ESTRATÉGIA -->
          <div v-show="activeTab==='estrategia' || printMode">

          <!-- COMUNICAÇÃO -->
          <section id="comm" class="aug-card" v-if="secComunicacao?.content">
            <div class="aug-section-header" @click="toggleSection('comm')">
              <h2 class="aug-section-title">📣 Estratégia de Comunicação</h2>
              <span class="aug-toggle">{{ isExpanded('comm') ? '−' : '+' }}</span>
            </div>
            <div class="aug-collapsible" :class="{'aug-open': isExpanded('comm')}">
              <div class="aug-prose" v-html="md(secComunicacao.content)"></div>
            </div>
          </section>

          <!-- POSICIONAMENTO -->
          <section id="posic" class="aug-card" v-if="secPosicionamento?.content">
            <div class="aug-section-header" @click="toggleSection('posic')">
              <h2 class="aug-section-title">🎯 Posicionamento Percebido vs Desejado</h2>
              <span class="aug-toggle">{{ isExpanded('posic') ? '−' : '+' }}</span>
            </div>
            <div class="aug-collapsible" :class="{'aug-open': isExpanded('posic')}">
              <div class="aug-prose" v-html="md(secPosicionamento.content)"></div>
            </div>
          </section>

          <!-- PREVISÕES -->
          <section id="previsoes" class="aug-card" v-if="secPrevisoes?.content || parsedPrevisoes.length">
            <h2 class="aug-section-title">🔮 Previsões</h2>
            <div v-if="parsedPrevisoes.length >= 2 && parsedPrevisoes.every(p => p.text.length > 30)" class="aug-insights">
              <div v-for="(p, i) in parsedPrevisoes" :key="i" class="aug-insight">
                <span class="aug-insight-num">{{ i + 1 }}</span>
                <p>{{ p.text }}</p>
              </div>
            </div>
            <div v-else-if="secPrevisoes?.content" class="aug-prose" v-html="md(secPrevisoes.content)"></div>
          </section>

          </div><!-- /estrategia -->

          <!-- TAB: PROFUNDA -->
          <div v-show="activeTab==='profunda' || printMode">

          <!-- ANÁLISE PROFUNDA -->
          <section id="profunda" class="aug-card" v-if="deepSections.length">
            <h2 class="aug-section-title">🔬 Análise Profunda</h2>
            <div class="aug-deep-tabs">
              <button v-for="(ds, i) in deepSections" :key="i" 
                      class="aug-deep-tab" :class="{'aug-deep-on': deepTab === i}"
                      @click="deepTab = i">
                {{ ds.icon }} {{ ds.label }}
              </button>
            </div>
            <div class="aug-prose" v-if="deepSections[deepTab]"
                 :class="{'aug-collapsed': !isExpanded('deep'+deepTab)}"
                 v-html="md(deepSections[deepTab].content || '')"></div>
            <button v-if="(deepSections[deepTab]?.content||'').length > 800" class="aug-expand" @click="toggleSection('deep'+deepTab)">
              {{ isExpanded('deep'+deepTab) ? '▲ Recolher' : '▼ Ver conteúdo completo' }}
            </button>
            <div v-if="!deepSections.length" class="aug-empty">Análise profunda não disponível para esta simulação.</div>
          </section>

          </div><!-- /profunda -->

          <!-- VALOR (sempre visível) -->
          <!-- VALOR DA ANÁLISE -->
          <section class="aug-card" v-if="secValorAnalise?.content">
            <div class="aug-section-header" @click="toggleSection('valor')">
              <h2 class="aug-section-title">💎 Valor da Análise</h2>
              <span class="aug-toggle">{{ isExpanded('valor') ? '−' : '+' }}</span>
            </div>
            <div class="aug-collapsible" :class="{'aug-open': isExpanded('valor')}">
              <div class="aug-prose" v-html="md(secValorAnalise.content)"></div>
            </div>
          </section>

          <!-- NUVEM DE PALAVRAS -->
          <section class="aug-card" v-if="wordCloudWords.length">
            <h2 class="aug-section-title">☁️ Nuvem de Palavras</h2>
            <div class="aug-cloud">
              <span v-for="w in wordCloudWords" :key="w.text" :style="{fontSize: w.size+'px', opacity: 0.5 + w.size/40}">{{ w.text }}</span>
            </div>
          </section>

          <!-- POSTS -->
          <section class="aug-card" v-if="posts.length">
            <h2 class="aug-section-title">📱 Posts Relevantes</h2>
            <div class="aug-posts">
              <div v-for="(p, i) in posts.slice(0, 8)" :key="i" class="aug-post">
                <div class="aug-post-head">
                  <span class="aug-post-platform">{{ p.platform === 'twitter' ? '𝕏' : '🔴' }}</span>
                  <span class="aug-post-author">{{ p.agent_name || p.user_name || 'Agente' }}</span>
                  <span class="aug-post-likes">❤️ {{ p.likes || 0 }}</span>
                </div>
                <p class="aug-post-text">{{ (p.content || p.text || '').slice(0, 200) }}</p>
              </div>
            </div>
          </section>

          <!-- SEÇÕES GENÉRICAS -->
          <section class="aug-card" v-for="s in secoesExtras" :key="s.title">
            <h2 class="aug-section-title">{{ s.title }}</h2>
            <div class="aug-prose" v-html="md(s.content || '')"></div>
          </section>

          <!-- CONCLUSÃO -->
          <section id="closing" class="aug-card aug-card-closing">
            <div class="aug-closing-verdict" :style="{color: veredicto.color}">
              <span class="aug-closing-icon">{{ veredicto.icon }}</span>
              <h2>{{ veredicto.label }}</h2>
            </div>
            <p class="aug-closing-summary">{{ (report?.outline?.summary || '').replace(/VEREDICTO:[^.]*\./i, '').trim() }}</p>
            <div class="aug-closing-trio">
              <div class="aug-trio-item">
                <div class="aug-trio-label">CENÁRIO MAIS PROVÁVEL</div>
                <div class="aug-trio-val">{{ cenarios[0]?.nome || '—' }} ({{ cenarios[0]?.prob || 0 }}%)</div>
              </div>
              <div class="aug-trio-item aug-trio-accent">
                <div class="aug-trio-label">AÇÃO PRIORITÁRIA</div>
                <div class="aug-trio-val">{{ (parsedRecomendacoes[0]?.name || briefingCEO.decisao || '').replace(/[#*]/g,'').trim().slice(0,100) }}</div>
              </div>
              <div class="aug-trio-item">
                <div class="aug-trio-label">RISCO PRINCIPAL</div>
                <div class="aug-trio-val">{{ (parsedRiscos[0]?.name || briefingCEO.risco || '').replace(/[#*]/g,'').trim().slice(0,100) }}</div>
              </div>
            </div>
            <div class="aug-closing-brand">
              <span>🔭 AUGUR</span>
              <p>Preveja o futuro. Antes que ele aconteça.</p>
            </div>
          </section>

          <!-- CTA -->
          <section class="aug-card aug-cta">
            <h3>Quer aprofundar a análise?</h3>
            <p>Converse com os agentes para explorar cenários alternativos.</p>
            <AugurButton variant="primary" @click="router.push(`/agentes/${route.params.reportId}`)">Conversar com Agentes</AugurButton>
          </section>

        </main>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ═══ DESIGN SYSTEM ═══ */
.aug-report { max-width:1200px; margin:0 auto; padding:0 16px 80px; font-family:'DM Sans','Segoe UI',system-ui,sans-serif; color:#1a1a2e; }

/* Header */
.aug-header { margin-bottom:32px; }
.aug-header-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:8px; }
.aug-breadcrumb { font-size:13px; color:#8888aa; }
.aug-breadcrumb span { cursor:pointer; }
.aug-breadcrumb span:first-child:hover { color:#00e5c3; }
.aug-bc-sep { margin:0 6px; color:#ccc; }
.aug-actions { display:flex; gap:6px; flex-wrap:wrap; }
.aug-btn-ghost { padding:7px 14px; border:1px solid #e0e0e8; background:#fff; border-radius:8px; font-size:12px; font-weight:600; color:#555570; cursor:pointer; transition:all .15s; }
.aug-btn-ghost:hover { border-color:#00e5c3; color:#00e5c3; }
.aug-btn-primary { padding:7px 18px; border:none; background:#00e5c3; border-radius:8px; font-size:12px; font-weight:700; color:#09090f; cursor:pointer; }
.aug-btn-primary:hover { opacity:.9; }
.aug-title { font-size:26px; font-weight:800; line-height:1.25; color:#1a1a2e; letter-spacing:-0.3px; }
.aug-subtitle { font-size:13px; color:#8888aa; margin-top:6px; }

/* Layout */
.aug-layout { display:grid; grid-template-columns:200px 1fr; gap:32px; align-items:start; }

/* Sidebar Nav */
.aug-nav { position:sticky; top:24px; }
.aug-nav-inner { display:flex; flex-direction:column; gap:2px; }
.aug-nav-item { padding:8px 12px; font-size:12px; font-weight:500; color:#8888aa; border-radius:6px; cursor:pointer; transition:all .15s; text-decoration:none; border-left:2px solid transparent; }
.aug-nav-item:hover { color:#1a1a2e; background:#f5f5fa; }
.aug-nav-active { color:#00e5c3 !important; border-left-color:#00e5c3; background:rgba(0,229,195,0.06); font-weight:600; }

/* Tabs */
.aug-tabs { display:flex; gap:4px; background:#fff; border:1px solid #eeeef2; border-radius:12px; padding:4px; margin-bottom:20px; }
.aug-tab { flex:1; padding:10px 16px; border:none; background:none; border-radius:8px; font-size:13px; font-weight:600; color:#8888aa; cursor:pointer; transition:all .2s; }
.aug-tab:hover { color:#1a1a2e; background:#f5f5fa; }
.aug-tab-on { background:#00e5c3 !important; color:#09090f !important; box-shadow:0 2px 8px rgba(0,229,195,0.25); }

/* Cards */
.aug-card { background:#fff; border:1px solid #eeeef2; border-radius:16px; padding:28px 32px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.04); transition:box-shadow .2s; }
.aug-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.06); }
.aug-card-accent { border-left:4px solid #00e5c3; background:linear-gradient(135deg,#fafffe,#f8f7ff); }
.aug-card-closing { text-align:center; background:linear-gradient(180deg,#fafbfe,#f0f4ff); border:none; padding:40px; }

/* Section titles */
.aug-section-title { font-size:18px; font-weight:700; color:#1a1a2e; margin:0 0 16px; letter-spacing:-0.2px; }
.aug-section-header { display:flex; justify-content:space-between; align-items:center; cursor:pointer; }
.aug-section-header:hover .aug-section-title { color:#00e5c3; }
.aug-toggle { width:28px; height:28px; border-radius:50%; border:1px solid #e0e0e8; display:flex; align-items:center; justify-content:center; font-size:16px; color:#8888aa; background:#fafafe; flex-shrink:0; }

/* Prose */
.aug-prose { font-size:14px; line-height:1.8; color:#444466; }
.aug-prose :deep(h2) { font-size:16px; font-weight:700; color:#1a1a2e; margin:20px 0 8px; }
.aug-prose :deep(h3) { font-size:15px; font-weight:700; color:#1a1a2e; margin:16px 0 8px; }
.aug-prose :deep(h4) { font-size:14px; font-weight:700; color:#1a1a2e; margin:12px 0 6px; }
.aug-prose :deep(strong) { color:#1a1a2e; font-weight:600; }
.aug-prose :deep(blockquote) { border-left:3px solid #7c6ff7; background:#f8f7ff; padding:12px 16px; margin:12px 0; border-radius:0 10px 10px 0; font-style:italic; color:#555570; font-size:13px; }
.aug-prose :deep(ul), .aug-prose :deep(ol) { padding-left:20px; margin:8px 0; }
.aug-prose :deep(li) { margin:4px 0; }

/* Collapsible */
.aug-collapsible { max-height:200px; overflow:hidden; position:relative; transition:max-height .4s ease; }
.aug-collapsible::after { content:''; position:absolute; bottom:0; left:0; right:0; height:80px; background:linear-gradient(transparent,#ffffff); pointer-events:none; }
.aug-open { max-height:none; overflow:visible; }
.aug-open::after { display:none; }
.aug-collapsed { max-height:200px; overflow:hidden; position:relative; }
.aug-collapsed::after { content:''; position:absolute; bottom:0; left:0; right:0; height:60px; background:linear-gradient(transparent,#ffffff); }
.aug-expand { display:block; margin:12px auto 0; padding:8px 24px; border:1px solid #e0e0e8; background:#fafafe; border-radius:20px; font-size:12px; color:#7c6ff7; font-weight:600; cursor:pointer; }
.aug-expand:hover { border-color:#7c6ff7; background:#f8f7ff; }

/* Context */
.aug-ctx-row { display:flex; gap:32px; align-items:flex-start; }
.aug-ctx-left { flex:1; }
.aug-ctx-badge { font-size:10px; font-weight:700; letter-spacing:1.5px; color:#7c6ff7; margin-bottom:8px; }
.aug-ctx-text { font-size:14px; color:#444466; line-height:1.7; }
.aug-ctx-stats { display:flex; gap:20px; flex-shrink:0; }
.aug-stat { text-align:center; }
.aug-stat-val { display:block; font-size:28px; font-weight:800; color:#1a1a2e; font-family:'JetBrains Mono',monospace; }
.aug-stat-label { font-size:10px; color:#8888aa; text-transform:uppercase; letter-spacing:0.5px; }
.aug-disclaimer { font-size:11px; color:#aaaabc; margin-top:12px; padding-top:12px; border-top:1px solid #eeeef2; }

/* Veredicto */
.aug-veredicto { display:inline-flex; align-items:center; gap:6px; padding:6px 16px; border-radius:20px; font-size:13px; font-weight:700; border:1px solid; }
.aug-gauge { width:80px; flex-shrink:0; }
.aug-gauge-svg { width:100%; }
.aug-card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }

/* CEO Grid */
.aug-ceo-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
.aug-ceo-item { padding:16px; background:#fafafe; border-radius:10px; border:1px solid #eeeef2; }
.aug-ceo-label { font-size:9px; font-weight:700; letter-spacing:1px; color:#8888aa; text-transform:uppercase; margin-bottom:6px; }
.aug-ceo-val { font-size:13px; font-weight:600; color:#1a1a2e; line-height:1.5; }
.aug-kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; }
.aug-kpi { padding:12px 14px; background:#f8f7ff; border-radius:8px; border-left:3px solid #7c6ff7; }
.aug-kpi-label { font-size:10px; font-weight:700; color:#7c6ff7; letter-spacing:0.5px; margin-bottom:4px; }
.aug-kpi-val { font-size:13px; font-weight:600; color:#1a1a2e; }

/* Cenários */
.aug-prob-bar { display:flex; height:8px; border-radius:4px; overflow:hidden; margin-bottom:8px; }
.aug-prob-seg { transition:width .8s ease; }
.aug-prob-legend { display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap; font-size:12px; color:#555570; }
.aug-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; vertical-align:middle; }
.aug-cenarios-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }
.aug-cenario { padding:20px; background:#fafafe; border-radius:12px; border:1px solid #eeeef2; border-top:3px solid; }
.aug-cenario-head { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px; }
.aug-cenario h3 { font-size:14px; font-weight:700; color:#1a1a2e; margin:0; line-height:1.4; }
.aug-cenario-badge { font-size:10px; font-weight:700; letter-spacing:0.5px; flex-shrink:0; }
.aug-cenario-desc { font-size:13px; color:#555570; line-height:1.6; margin-bottom:12px; }
.aug-cenario-prob { display:flex; align-items:center; gap:8px; font-size:12px; color:#8888aa; }
.aug-prob-mini { flex:1; height:4px; background:#eeeef2; border-radius:2px; overflow:hidden; }
.aug-prob-mini div { height:100%; border-radius:2px; }

/* Insights */
.aug-insights { display:flex; flex-direction:column; gap:12px; }
.aug-insight { display:flex; gap:14px; align-items:flex-start; padding:14px 16px; background:#fafafe; border-radius:10px; border:1px solid #eeeef2; }
.aug-insight-num { width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#7c6ff7,#00e5c3); color:#fff; font-size:12px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.aug-insight p { margin:0; font-size:13px; line-height:1.6; color:#444466; }

/* Risks */
.aug-risks { display:flex; flex-direction:column; gap:12px; }
.aug-risk { padding:18px 20px; background:#fafafe; border-radius:12px; border:1px solid #eeeef2; border-left:3px solid var(--rc,#ff5a5a); }
.aug-risk-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }
.aug-risk h4 { font-size:14px; font-weight:700; color:#1a1a2e; margin:0; }
.aug-risk-badge { font-size:10px; font-weight:700; }
.aug-risk p { font-size:13px; color:#555570; line-height:1.6; margin:0 0 10px; }
.aug-risk-bar { display:flex; align-items:center; gap:8px; font-size:11px; color:#8888aa; }
.aug-bar-track { flex:1; height:4px; background:#eeeef2; border-radius:2px; overflow:hidden; }
.aug-bar-track div { height:100%; border-radius:2px; }

/* Recs */
.aug-recs { display:flex; flex-direction:column; gap:10px; }
.aug-rec { display:flex; gap:14px; padding:16px 18px; background:#fafafe; border-radius:12px; border:1px solid #eeeef2; }
.aug-rec-top { background:#f0fdf9; border-color:#00e5c3; }
.aug-rec-num { width:32px; height:32px; border-radius:50%; background:#00e5c3; color:#09090f; font-size:14px; font-weight:800; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.aug-rec-body h4 { font-size:14px; font-weight:700; color:#1a1a2e; margin:0 0 4px; }
.aug-rec-body p { font-size:13px; color:#555570; line-height:1.6; margin:0; }
.aug-rec-meta { font-size:11px; color:#7c6ff7; margin-top:6px; }

/* Deep tabs */
.aug-deep-tabs { display:flex; gap:4px; margin-bottom:16px; flex-wrap:wrap; }
.aug-deep-tab { padding:8px 14px; border:1px solid #e0e0e8; background:#fff; border-radius:8px; font-size:12px; cursor:pointer; color:#555570; }
.aug-deep-tab:hover { border-color:#7c6ff7; }
.aug-deep-on { background:#7c6ff7; color:#fff; border-color:#7c6ff7; }

/* Word cloud */
.aug-cloud { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; padding:12px; }
.aug-cloud span { color:#7c6ff7; font-weight:600; line-height:1; }

/* Posts */
.aug-posts { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:10px; }
.aug-post { padding:14px 16px; background:#fafafe; border-radius:10px; border:1px solid #eeeef2; }
.aug-post-head { display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:12px; }
.aug-post-platform { font-size:16px; }
.aug-post-author { font-weight:600; color:#1a1a2e; }
.aug-post-likes { margin-left:auto; color:#8888aa; }
.aug-post-text { font-size:13px; color:#555570; line-height:1.6; margin:0; }

/* Closing */
.aug-closing-icon { font-size:36px; }
.aug-closing-verdict h2 { font-size:28px; font-weight:800; margin:8px 0; }
.aug-closing-summary { font-size:14px; color:#555570; line-height:1.7; max-width:700px; margin:0 auto 24px; }
.aug-closing-trio { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:24px; }
.aug-trio-item { padding:16px; background:#fff; border-radius:12px; border:1px solid #eeeef2; }
.aug-trio-accent { background:#f0fdf9; border-color:#00e5c3; }
.aug-trio-label { font-size:9px; font-weight:700; letter-spacing:1px; color:#8888aa; text-transform:uppercase; margin-bottom:6px; }
.aug-trio-val { font-size:13px; font-weight:600; color:#1a1a2e; line-height:1.4; }
.aug-closing-brand { margin-top:24px; font-size:18px; font-weight:700; color:#00e5c3; letter-spacing:2px; }
.aug-closing-brand p { font-size:12px; color:#8888aa; font-weight:400; font-style:italic; margin:4px 0 0; letter-spacing:0; }

/* CTA */
.aug-cta { text-align:center; background:linear-gradient(135deg,rgba(0,229,195,0.04),rgba(124,111,247,0.04)); border:1px dashed rgba(0,229,195,0.3); }
.aug-cta h3 { font-size:16px; font-weight:700; color:#1a1a2e; margin:0 0 4px; }
.aug-cta p { font-size:13px; color:#8888aa; margin:0 0 14px; }

/* Loading/Error */
.aug-loading { text-align:center; padding:80px 0; color:#8888aa; }
.aug-spinner { width:32px; height:32px; border:3px solid #eeeef2; border-top-color:#00e5c3; border-radius:50%; animation:spin 1s linear infinite; margin:0 auto 16px; }
@keyframes spin { to { transform:rotate(360deg); } }
.aug-error { text-align:center; padding:80px 0; }
.aug-error h3 { color:#ff5a5a; }
.aug-empty { text-align:center; padding:24px; color:#8888aa; font-size:13px; }

/* Responsive */
@media (max-width:900px) {
  .aug-layout { grid-template-columns:1fr; }
  .aug-nav { display:none; }
  .aug-ceo-grid { grid-template-columns:repeat(2,1fr); }
  .aug-closing-trio { grid-template-columns:1fr; }
  .aug-ctx-row { flex-direction:column; }
}

/* Print */
@media print {
  .aug-header-top, .aug-nav, .aug-cta, .aug-expand, .aug-toggle { display:none !important; }
  .aug-report { max-width:100%; padding:0; }
  .aug-layout { grid-template-columns:1fr; }
  .aug-card { box-shadow:none; border:1px solid #ddd; break-inside:avoid; page-break-inside:avoid; margin-bottom:12px; }
  .aug-collapsible, .aug-collapsed { max-height:none !important; overflow:visible !important; }
  .aug-collapsible::after, .aug-collapsed::after { display:none !important; }
  .aug-card-closing { break-before:page; }
  * { print-color-adjust:exact !important; -webkit-print-color-adjust:exact !important; }
}

/* ─── Structured: Frase-chave ─── */
.aug-frase-chave { font-size:20px; font-weight:800; line-height:1.4; margin:12px 0 16px; padding:0; }

/* ─── Structured: Ação do CEO ─── */
.aug-acao-box { background:linear-gradient(135deg, rgba(0,229,195,0.06), rgba(124,111,247,0.04)); border:1px solid rgba(0,229,195,0.2); border-radius:12px; padding:16px 20px; margin:16px 0; }
.aug-acao-label { font-size:11px; font-weight:800; color:var(--accent, #00e5c3); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; }
.aug-acao-text { font-size:14px; color:var(--text-primary, #1a1a2e); font-weight:600; line-height:1.6; }

/* ─── Structured: Top 5 Fatos ─── */
.aug-fatos { margin-top:20px; }
.aug-fatos-title { font-size:13px; font-weight:700; color:var(--text-secondary, #555570); margin-bottom:10px; }
.aug-fato { display:flex; gap:12px; align-items:flex-start; padding:10px 0; border-bottom:1px solid var(--border, #eeeef2); }
.aug-fato:last-child { border-bottom:none; }
.aug-fato-num { width:24px; height:24px; border-radius:8px; background:var(--accent2, #7c6ff7); color:#fff; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:800; flex-shrink:0; }
.aug-fato-desc { font-size:12px; color:var(--text-secondary, #555570); margin-top:2px; }

/* ─── Structured: Dashboard KPIs ─── */
.aug-kpi-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:10px; }
.aug-kpi { background:var(--bg-raised, #fafafe); border:1px solid var(--border, #eeeef2); border-radius:12px; padding:14px; text-align:center; transition:box-shadow .2s; }
.aug-kpi:hover { box-shadow:0 2px 8px rgba(0,0,0,0.05); }
.aug-kpi-icon { font-size:20px; display:block; margin-bottom:4px; }
.aug-kpi-val { font-size:16px; font-weight:800; color:var(--text-primary, #1a1a2e); font-family:var(--font-mono, 'JetBrains Mono', monospace); }
.aug-kpi-label { font-size:10px; font-weight:600; color:var(--text-muted, #8888aa); text-transform:uppercase; letter-spacing:0.3px; margin-top:4px; }

/* ─── Project/Client Badge ─── */
.aug-project-badge { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.aug-project-client { font-size:13px; font-weight:800; color:var(--accent2, #7c6ff7); background:rgba(124,111,247,0.08); padding:4px 12px; border-radius:8px; }
.aug-project-name { font-size:13px; font-weight:600; color:var(--text-secondary, #555570); }
</style>
