<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const router = useRouter()

// ─── Estado do wizard ───────────────────────────────────────────
const step = ref(1)
const isLoading = ref(false)
const error = ref('')
const uploadNotice = ref('')

// ─── Etapa 1: Hipótese ──────────────────────────────────────────
const segmento = ref('')
const cenario = ref('')
const titulo = ref('')
const hipotese = ref('')
const gerandoHipotese = ref(false)
const cenarioA = ref('')
const cenarioB = ref('')
const cenarioC = ref('')
const estrategiaSelecionada = ref('A')
const resumoCopiado = ref(false)
const outcomeAdocaoReal = ref('')
const outcomeRiscoReal = ref('')
const outcomeConfiancaReal = ref('')
const historicoBenchmarks = ref([])

// ─── Etapa 2: Materiais ─────────────────────────────────────────
const arquivos = ref([])
const fileInput = ref(null)

// ─── Etapa 3: Parâmetros ─────────────────────────────────────────
const agentes = ref(50)
const rodadas = ref(20)
const dataReferencia = ref(new Date().toISOString().split('T')[0])

// ─── Segmentos ──────────────────────────────────────────────────
const segmentos = [
  {
    id: 'politica',
    label: 'Política & Opinião',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3h18v4H3zM7 10h10M7 14h6M5 21h14a2 2 0 0 0 2-2v-5H3v5a2 2 0 0 0 2 2z"/></svg>`,
    exemplos: [
      '"Como diferentes grupos vão reagir à aprovação da reforma tributária?"',
      '"Qual será o impacto eleitoral de um escândalo de corrupção?"',
      '"Como a população vai responder a uma nova lei ambiental?"'
    ]
  },
  {
    id: 'negocios',
    label: 'Negócios & Mercado',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>`,
    exemplos: [
      '"Como o lançamento de um produto vai ser recebido pelo mercado?"',
      '"Qual a reação dos clientes a uma mudança de preços?"',
      '"Como a entrada de um concorrente vai afetar nossa base?"'
    ]
  },
  {
    id: 'comportamento',
    label: 'Comportamento Social',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    exemplos: [
      '"Como diferentes gerações vão reagir a uma mudança cultural?"',
      '"Qual será o comportamento das redes sociais após um evento viral?"',
      '"Como a sociedade vai absorver uma nova tecnologia?"'
    ]
  },
  {
    id: 'rh',
    label: 'Organizações & RH',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>`,
    exemplos: [
      '"Como os colaboradores vão reagir a uma mudança de política interna?"',
      '"Qual o impacto de uma reestruturação organizacional no engajamento?"',
      '"Como comunicar uma demissão em massa para minimizar danos?"'
    ]
  },
  {
    id: 'saude',
    label: 'Saúde & Bem-estar',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`,
    exemplos: [
      '"Como a população vai reagir a uma nova política de saúde pública?"',
      '"Qual será a adesão a uma campanha de vacinação?"',
      '"Como comunicar riscos de saúde sem gerar pânico?"'
    ]
  },
  {
    id: 'educacao',
    label: 'Educação & Pesquisa',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>`,
    exemplos: [
      '"Como estudantes e professores vão reagir a uma reforma curricular?"',
      '"Qual será o impacto de uma nova metodologia de ensino?"',
      '"Como a comunidade acadêmica vai receber uma descoberta científica?"'
    ]
  },
  {
    id: 'sustentabilidade',
    label: 'Sustentabilidade',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    exemplos: [
      '"Como consumidores vão reagir a um produto com embalagem sustentável?"',
      '"Qual será o impacto de uma política de carbono zero?"',
      '"Como comunicar iniciativas ESG para diferentes públicos?"'
    ]
  },
  {
    id: 'tecnologia',
    label: 'Inovação & Tecnologia',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
    exemplos: [
      '"Como o mercado vai reagir ao lançamento de uma IA generativa?"',
      '"Qual será a adoção de uma nova tecnologia B2B?"',
      '"Como diferentes grupos vão reagir à automação de empregos?"'
    ]
  }
]

const segmentoAtual = computed(() => segmentos.find(s => s.id === segmento.value))
const exemplosAtuais = computed(() => segmentoAtual.value?.exemplos || [])

// ─── Estimativas em tempo real ──────────────────────────────────
const estimativaMinutos = computed(() => {
  const base = agentes.value * rodadas.value * 0.04
  return Math.round(Math.max(2, base))
})
const estimativaCusto = computed(() => {
  const custo = agentes.value * rodadas.value * 0.0008
  return custo.toFixed(2)
})
const descricaoAgentes = computed(() => {
  if (agentes.value <= 20) return 'Teste rápido — ideal para validar a hipótese'
  if (agentes.value <= 100) return 'Bom equilíbrio entre velocidade e precisão'
  if (agentes.value <= 250) return 'Alta fidelidade — captura nuances importantes'
  return 'Máxima riqueza — simulação de alta complexidade'
})
const descricaoRodadas = computed(() => {
  if (rodadas.value <= 5) return 'Instantâneo — reação imediata ao evento'
  if (rodadas.value <= 25) return 'Captura tendências de curto prazo'
  if (rodadas.value <= 60) return 'Evolução completa da opinião ao longo do tempo'
  return 'Análise profunda — evolução de longo prazo'
})
const prontidaoDecisao = computed(() => {
  const base = Math.min(40, titulo.value.trim().length >= 8 ? 40 : titulo.value.trim().length * 5)
  const hipoteseScore = Math.min(30, Math.floor(hipotese.value.trim().length / 8))
  const materiaisScore = Math.min(20, arquivos.value.length * 5)
  const simulacaoScore = Math.min(10, agentes.value >= 50 && rodadas.value >= 20 ? 10 : 6)
  return Math.min(100, base + hipoteseScore + materiaisScore + simulacaoScore)
})
const prontidaoLabel = computed(() => {
  if (prontidaoDecisao.value < 45) return 'Inicial'
  if (prontidaoDecisao.value < 75) return 'Estruturada'
  if (prontidaoDecisao.value < 90) return 'Alta'
  return 'Executiva'
})
const cenariosComparativos = computed(() => {
  const score = (text) => {
    const len = text.trim().length
    if (!len) return 0
    const densidade = Math.min(60, Math.floor(len / 2))
    const materiaisBonus = Math.min(20, arquivos.value.length * 4)
    const estruturaBonus = titulo.value.trim() && hipotese.value.trim().length >= 20 ? 20 : 8
    return Math.min(100, densidade + materiaisBonus + estruturaBonus)
  }
  return [
    { id: 'A', titulo: 'Estratégia A', texto: cenarioA.value, score: score(cenarioA.value) },
    { id: 'B', titulo: 'Estratégia B', texto: cenarioB.value, score: score(cenarioB.value) },
    { id: 'C', titulo: 'Estratégia C', texto: cenarioC.value, score: score(cenarioC.value) }
  ]
})
const melhorCenario = computed(() => {
  return cenariosComparativos.value.reduce((best, curr) => (curr.score > best.score ? curr : best), cenariosComparativos.value[0])
})
const metricasExecutivas = computed(() => {
  const maturidade = prontidaoDecisao.value
  return {
    adocao: Math.min(95, Math.max(28, Math.round(maturidade * 0.82))),
    riscoReputacional: Math.max(8, 100 - Math.round(maturidade * 0.7)),
    confianca: Math.min(97, Math.round((maturidade + melhorCenario.value.score) / 2))
  }
})
const metricasExecutivasCalibradas = computed(() => {
  const adocaoReal = Number(outcomeAdocaoReal.value)
  const riscoReal = Number(outcomeRiscoReal.value)
  const confiancaReal = Number(outcomeConfiancaReal.value)
  return {
    adocao: Number.isFinite(adocaoReal) && adocaoReal > 0
      ? Math.round((metricasExecutivas.value.adocao * 0.6) + (adocaoReal * 0.4))
      : metricasExecutivas.value.adocao,
    riscoReputacional: Number.isFinite(riscoReal) && riscoReal > 0
      ? Math.round((metricasExecutivas.value.riscoReputacional * 0.6) + (riscoReal * 0.4))
      : metricasExecutivas.value.riscoReputacional,
    confianca: Number.isFinite(confiancaReal) && confiancaReal > 0
      ? Math.round((metricasExecutivas.value.confianca * 0.6) + (confiancaReal * 0.4))
      : metricasExecutivas.value.confianca
  }
})
const plano72h = computed(() => {
  return [
    `Priorizar execução da ${melhorCenario.value.titulo.toLowerCase()} com mensagem central validada.`,
    `Testar criativos e narrativas em 2 segmentos críticos antes do lançamento amplo.`,
    `Monitorar risco reputacional (meta: < ${metricasExecutivasCalibradas.value.riscoReputacional}%) e ajustar comunicação diariamente.`
  ]
})
const benchmarkMedias = computed(() => {
  if (!historicoBenchmarks.value.length) return null
  const total = historicoBenchmarks.value.reduce((acc, item) => {
    acc.adocao += item.adocao
    acc.risco += item.risco
    acc.confianca += item.confianca
    return acc
  }, { adocao: 0, risco: 0, confianca: 0 })
  const n = historicoBenchmarks.value.length
  return {
    adocao: Math.round(total.adocao / n),
    risco: Math.round(total.risco / n),
    confianca: Math.round(total.confianca / n)
  }
})
const comparativoBenchmark = computed(() => {
  if (!benchmarkMedias.value) return null
  return {
    adocao: metricasExecutivasCalibradas.value.adocao - benchmarkMedias.value.adocao,
    risco: metricasExecutivasCalibradas.value.riscoReputacional - benchmarkMedias.value.risco,
    confianca: metricasExecutivasCalibradas.value.confianca - benchmarkMedias.value.confianca
  }
})
const resumoExecutivo = computed(() => {
  return [
    `Título: ${titulo.value || 'Não informado'}`,
    `Hipótese: ${hipotese.value || 'Não informada'}`,
    `Estratégia recomendada: ${melhorCenario.value.titulo}`,
    `Adoção prevista: ${metricasExecutivasCalibradas.value.adocao}%`,
    `Risco reputacional: ${metricasExecutivasCalibradas.value.riscoReputacional}%`,
    `Confiança da recomendação: ${metricasExecutivasCalibradas.value.confianca}%`,
    'Plano 72h:',
    ...plano72h.value.map((item, i) => `${i + 1}. ${item}`)
  ].join('\n')
})

// ─── Qualidade dos materiais ────────────────────────────────────
const qualidadeMateriais = computed(() => {
  const n = arquivos.value.length
  if (n === 0) return { label: 'Sem materiais', cor: '#6b6b80', desc: 'Os agentes usarão apenas a hipótese como base' }
  if (n === 1) return { label: 'Básico', cor: '#f5a623', desc: 'Um documento fornece contexto inicial' }
  if (n <= 3) return { label: 'Bom', cor: '#7c6ff7', desc: 'Múltiplos documentos enriquecem os agentes' }
  return { label: 'Excelente', cor: '#00e5c3', desc: 'Base de conhecimento robusta para simulação precisa' }
})

// ─── Validações ─────────────────────────────────────────────────
const etapa1Valida = computed(() => titulo.value.trim().length >= 3 && hipotese.value.trim().length >= 10)
const etapa3Valida = computed(() => agentes.value >= 5 && rodadas.value >= 1)

// ─── Gerar hipótese com IA ──────────────────────────────────────
async function gerarHipotese() {
  if (!cenario.value.trim()) return
  gerandoHipotese.value = true
  error.value = ''
  try {
    const res = await service.post('/api/graph/generate-hypothesis', {
      cenario: cenario.value,
      segmento: segmento.value
    })
    const data = res.data || res
    if (data.titulo) titulo.value = data.titulo
    if (data.hipotese) hipotese.value = data.hipotese
  } catch (e) {
    // fallback: estruturar localmente
    titulo.value = cenario.value.slice(0, 60)
    hipotese.value = `Como ${cenario.value.toLowerCase()} vai impactar a opinião pública nos próximos meses?`
  } finally {
    gerandoHipotese.value = false
  }
}

// ─── Upload de arquivos ─────────────────────────────────────────
function onFileChange(event) {
  const files = Array.from(event.target.files || [])
  adicionarArquivos(files)
}

function onDrop(event) {
  event.preventDefault()
  dragOver.value = false
  const files = Array.from(event.dataTransfer.files || [])
  adicionarArquivos(files)
}

function adicionarArquivos(files) {
  let rejeitados = 0
  let duplicados = 0
  let adicionados = 0
  files.forEach(f => {
    if (f.size > 16 * 1024 * 1024) {
      rejeitados++
      return
    }
    const allowed = ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','image/png','image/jpeg']
    if (!allowed.includes(f.type) && !f.name.match(/\.(pdf|docx|txt|png|jpg|jpeg)$/i)) {
      rejeitados++
      return
    }
    if (!arquivos.value.find(a => a.name === f.name)) {
      arquivos.value.push(f)
      adicionados++
    } else {
      duplicados++
    }
  })
  const parts = []
  if (adicionados) parts.push(`${adicionados} adicionado(s)`)
  if (duplicados) parts.push(`${duplicados} duplicado(s) ignorado(s)`)
  if (rejeitados) parts.push(`${rejeitados} rejeitado(s)`)
  uploadNotice.value = parts.join(' • ')
}

function removerArquivo(idx) {
  arquivos.value.splice(idx, 1)
}

const dragOver = ref(false)

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function fileIcon(name) {
  if (name.match(/\.pdf$/i)) return '📄'
  if (name.match(/\.docx?$/i)) return '📝'
  if (name.match(/\.txt$/i)) return '📃'
  if (name.match(/\.(png|jpg|jpeg)$/i)) return '🖼️'
  return '📎'
}

function sanitizeQuotedText(text = '') {
  return text.replace(/['"]/g, '')
}

function applyExample(exemplo) {
  const sanitized = sanitizeQuotedText(exemplo)
  cenario.value = sanitized
  hipotese.value = sanitized
}

function getScenarioPlaceholder() {
  if (!segmentoAtual.value) {
    return 'Ex: Quero entender como diferentes grupos da população vão reagir a um aumento de impostos sobre combustíveis...'
  }
  return `Ex: ${sanitizeQuotedText(segmentoAtual.value.exemplos[0])}`
}

// ─── Criar simulação ────────────────────────────────────────────
async function criarSimulacao() {
  if (!etapa3Valida.value) return
  isLoading.value = true
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('project_name', titulo.value)
    formData.append('simulation_requirement', hipotese.value)
    formData.append('segmento', segmento.value)
    formData.append('agent_count', agentes.value)
    formData.append('max_rounds', rodadas.value)
    formData.append('data_referencia', dataReferencia.value)
    arquivos.value.forEach(f => formData.append('files', f))

    const res = await service.post('/api/graph/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const data = res.data || res
    const projectId = data.project_id || data.id
    router.push(`/simulacao/${projectId}`)
  } catch (e) {
    error.value = 'Erro ao criar simulação. Tente novamente.'
  } finally {
    isLoading.value = false
  }
}

function proximaEtapa() {
  if (step.value === 1 && !etapa1Valida.value) return
  if (step.value < 3) step.value++
}
function etapaAnterior() {
  if (step.value > 1) step.value--
}
function irParaEtapa(target) {
  if (target < 1 || target > 3) return
  if (target === 1) {
    step.value = 1
    return
  }
  if (target === 2 && etapa1Valida.value) {
    step.value = 2
    return
  }
  if (target === 3 && etapa1Valida.value) {
    step.value = 3
  }
}
function selecionarEstrategia(id) {
  estrategiaSelecionada.value = id
}
function aplicarMelhorEstrategia() {
  const texto = melhorCenario.value?.texto?.trim()
  if (texto) hipotese.value = texto
}
async function copiarResumoExecutivo() {
  try {
    await navigator.clipboard.writeText(resumoExecutivo.value)
    resumoCopiado.value = true
    setTimeout(() => { resumoCopiado.value = false }, 1800)
  } catch {
    resumoCopiado.value = false
  }
}
function salvarBenchmarks() {
  localStorage.setItem('mirofish_benchmarks', JSON.stringify(historicoBenchmarks.value))
}
function carregarBenchmarks() {
  try {
    const raw = localStorage.getItem('mirofish_benchmarks')
    historicoBenchmarks.value = raw ? JSON.parse(raw) : []
  } catch {
    historicoBenchmarks.value = []
  }
}
function adicionarAoBenchmark() {
  historicoBenchmarks.value.unshift({
    id: Date.now(),
    nome: titulo.value || `Simulação ${new Date().toLocaleDateString('pt-BR')}`,
    adocao: metricasExecutivasCalibradas.value.adocao,
    risco: metricasExecutivasCalibradas.value.riscoReputacional,
    confianca: metricasExecutivasCalibradas.value.confianca
  })
  historicoBenchmarks.value = historicoBenchmarks.value.slice(0, 10)
  salvarBenchmarks()
}
function removerBenchmark(id) {
  historicoBenchmarks.value = historicoBenchmarks.value.filter(item => item.id !== id)
  salvarBenchmarks()
}
function baixarBoardHtml() {
  const html = `<!doctype html><html><head><meta charset="utf-8"/><title>Board Ready - ${titulo.value || 'Simulação'}</title></head><body><pre style="font-family:system-ui;white-space:pre-wrap">${resumoExecutivo.value}</pre></body></html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `board-ready-${(titulo.value || 'simulacao').replace(/\s+/g, '-').toLowerCase()}.html`
  a.click()
  URL.revokeObjectURL(url)
}
function baixarSlideTxt() {
  const lines = [
    `# ${titulo.value || 'Lançamento'}`,
    '',
    `## Recomendação`,
    `- Estratégia: ${melhorCenario.value.titulo}`,
    `- Adoção: ${metricasExecutivasCalibradas.value.adocao}%`,
    `- Risco: ${metricasExecutivasCalibradas.value.riscoReputacional}%`,
    `- Confiança: ${metricasExecutivasCalibradas.value.confianca}%`,
    '',
    '## Plano 72h',
    ...plano72h.value.map((item, i) => `${i + 1}. ${item}`)
  ].join('\n')
  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `board-slide-${(titulo.value || 'simulacao').replace(/\s+/g, '-').toLowerCase()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
onMounted(() => {
  carregarBenchmarks()
})
</script>

<template>
  <AppShell title="Nova Simulação">
    <div class="wizard-shell">

      <!-- Breadcrumb -->
      <div class="breadcrumb">
        <span class="bc-link" @click="router.push('/')">← Simulações</span>
        <span class="bc-sep">›</span>
        <span class="bc-current">Nova Simulação</span>
      </div>

      <!-- Header -->
      <div class="wizard-header">
        <h1 class="wizard-title">Nova Simulação</h1>
        <p class="wizard-sub">Configure sua hipótese e deixe a inteligência de enxame revelar o futuro.</p>
      </div>

      <!-- Steps indicator -->
      <div class="steps-track">
        <div
          v-for="(label, i) in ['Hipótese', 'Materiais', 'Parâmetros']"
          :key="i"
          class="step-item"
          :class="{ active: step === i + 1, done: step > i + 1 }"
          @click="irParaEtapa(i + 1)"
          @keydown.enter.prevent="irParaEtapa(i + 1)"
          @keydown.space.prevent="irParaEtapa(i + 1)"
          tabindex="0"
          role="button"
        >
          <div class="step-dot">
            <span v-if="step > i + 1" class="step-check">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3,8 6.5,12 13,4"/></svg>
            </span>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="step-connector" v-if="i < 2" :class="{ done: step > i + 1 }"></div>
          <div class="step-label">{{ label }}</div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ETAPA 1: HIPÓTESE                                      -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-if="step === 1" class="step-content">

        <!-- Bloco: Segmento -->
        <div class="card">
          <div class="card-head">
            <span class="card-icon">💡</span>
            <div>
              <div class="card-title">Qual é o seu contexto?</div>
              <div class="card-sub">Selecione o segmento mais próximo do seu tema para receber exemplos e sugestões personalizadas.</div>
            </div>
          </div>
          <div class="segment-grid">
            <button
              v-for="seg in segmentos"
              :key="seg.id"
              class="segment-btn"
              :class="{ selected: segmento === seg.id }"
              @click="segmento = seg.id"
            >
              <span class="seg-icon" v-html="seg.icon"></span>
              <span class="seg-label">{{ seg.label }}</span>
            </button>
          </div>
        </div>

        <!-- Bloco: Exemplos dinâmicos -->
        <transition name="fade">
          <div v-if="exemplosAtuais.length" class="card card-slim">
            <div class="examples-label">
              <span class="ex-icon">✦</span>
              Exemplos de hipóteses para este segmento:
            </div>
            <div class="examples-list">
              <button
                v-for="ex in exemplosAtuais"
                :key="ex"
                class="example-chip"
                @click="applyExample(ex)"
              >
                {{ ex }}
              </button>
            </div>
          </div>
        </transition>

        <!-- Bloco: Cenário + IA -->
        <div class="card">
          <div class="card-head">
            <span class="card-icon">✦</span>
            <div>
              <div class="card-title">O que você quer testar?</div>
              <div class="card-sub">Descreva em linguagem natural o que quer prever ou entender. A IA vai estruturar sua hipótese automaticamente.</div>
            </div>
          </div>

          <div class="field">
            <div class="field-label-row">
              <label class="field-label">Descreva seu cenário</label>
            </div>
            <textarea
              v-model="cenario"
              class="field-textarea"
              :placeholder="getScenarioPlaceholder()"
              rows="3"
            />
            <div class="field-hint">Quanto mais contexto você fornecer, mais precisa será a simulação.</div>
          </div>

          <button
            class="btn-generate"
            :class="{ loading: gerandoHipotese }"
            :disabled="!cenario.trim() || gerandoHipotese"
            @click="gerarHipotese"
          >
            <span v-if="gerandoHipotese" class="spinner"></span>
            <span v-else>✦</span>
            {{ gerandoHipotese ? 'Gerando hipótese...' : 'Gerar hipótese com IA' }}
          </button>
        </div>

        <div class="card">
          <div class="card-head">
            <span class="card-icon">⚔️</span>
            <div>
              <div class="card-title">Comparativo estratégico (A/B/C)</div>
              <div class="card-sub">Opcional, porém recomendado para decisões de lançamento. Defina 3 narrativas para comparar no resumo executivo.</div>
            </div>
          </div>
          <div class="ab-grid">
            <div class="field">
              <label class="field-label">Estratégia A</label>
              <textarea v-model="cenarioA" class="field-textarea" rows="2" placeholder="Ex: Posicionamento premium focado em inovação e status." />
            </div>
            <div class="field">
              <label class="field-label">Estratégia B</label>
              <textarea v-model="cenarioB" class="field-textarea" rows="2" placeholder="Ex: Posicionamento acessível focado em custo-benefício." />
            </div>
            <div class="field">
              <label class="field-label">Estratégia C</label>
              <textarea v-model="cenarioC" class="field-textarea" rows="2" placeholder="Ex: Posicionamento sustentável focado em impacto positivo." />
            </div>
          </div>
        </div>

        <!-- Bloco: Campos manuais -->
        <div class="card">
          <div class="card-divider-label">Prefere preencher diretamente? Use os campos abaixo.</div>

          <div class="field">
            <label class="field-label">Título <span class="required">*</span></label>
            <input
              v-model="titulo"
              class="field-input"
              type="text"
              placeholder="Ex: Impacto da reforma tributária na opinião pública"
            />
          </div>

          <div class="field">
            <label class="field-label">Hipótese de Previsão <span class="required">*</span></label>
            <textarea
              v-model="hipotese"
              class="field-textarea"
              placeholder="Como X vai impactar Y nos próximos Z meses?"
              rows="3"
            />
          </div>
        </div>

        <div class="step-nav">
          <button class="btn-cancel" @click="router.push('/')">← Cancelar</button>
          <button
            class="btn-next"
            :disabled="!etapa1Valida"
            @click="proximaEtapa"
          >
            Próximo: Materiais →
          </button>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ETAPA 2: MATERIAIS                                     -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-else-if="step === 2" class="step-content">

        <div class="card">
          <div class="card-head">
            <span class="card-icon">📁</span>
            <div>
              <div class="card-title">
                Materiais de Sementes
                <span class="optional-badge">opcional, mas recomendado</span>
              </div>
              <div class="card-sub">Carregue relatórios, notícias, pesquisas ou qualquer documento relevante. Eles alimentam o grafo de conhecimento e tornam os agentes muito mais precisos.</div>
            </div>
          </div>

          <!-- Dica de qualidade -->
          <div class="quality-tip">
            <span class="tip-icon">💡</span>
            Dica: Documentos de qualidade fazem uma diferença enorme. Pesquisas acadêmicas, relatórios de mercado e dados históricos são os melhores insumos.
          </div>

          <!-- Drop zone -->
          <div
            class="drop-zone"
            :class="{ 'drag-over': dragOver, 'has-files': arquivos.length > 0 }"
            @dragover.prevent="dragOver = true"
            @dragleave="dragOver = false"
            @drop="onDrop"
            @click="fileInput?.click()"
            @keydown.enter.prevent="fileInput?.click()"
            @keydown.space.prevent="fileInput?.click()"
            tabindex="0"
            role="button"
            aria-label="Selecionar materiais para a simulação"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
              style="display:none"
              @change="onFileChange"
            />
            <div class="drop-content">
              <div class="drop-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>
              <div class="drop-title">{{ dragOver ? 'Solte os arquivos aqui' : 'Toque para selecionar arquivos' }}</div>
              <div class="drop-sub">PDF, DOCX, TXT, PNG, JPG — até 16MB cada</div>
            </div>
          </div>

          <!-- Lista de arquivos -->
          <transition-group name="file-list" tag="div" class="files-list" v-if="arquivos.length">
            <div v-for="(arq, idx) in arquivos" :key="arq.name" class="file-item">
              <span class="file-icon">{{ fileIcon(arq.name) }}</span>
              <div class="file-info">
                <div class="file-name">{{ arq.name }}</div>
                <div class="file-size">{{ formatBytes(arq.size) }}</div>
              </div>
              <button class="file-remove" @click="removerArquivo(idx)" title="Remover">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/>
                </svg>
              </button>
            </div>
          </transition-group>

          <!-- Indicador de qualidade -->
          <div class="quality-indicator">
            <div class="quality-bar">
              <div
                class="quality-fill"
                :style="{ width: Math.min(100, arquivos.length * 25) + '%', background: qualidadeMateriais.cor }"
              ></div>
            </div>
            <div class="quality-info">
              <span class="quality-label" :style="{ color: qualidadeMateriais.cor }">{{ qualidadeMateriais.label }}</span>
              <span class="quality-desc">{{ qualidadeMateriais.desc }}</span>
            </div>
          </div>
          <div v-if="uploadNotice" class="upload-notice">{{ uploadNotice }}</div>
        </div>

        <div class="step-nav">
          <button class="btn-back" @click="etapaAnterior">← Voltar</button>
          <button class="btn-next" @click="proximaEtapa">Próximo: Parâmetros →</button>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- ETAPA 3: PARÂMETROS                                    -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div v-else-if="step === 3" class="step-content">

        <div class="card">
          <div class="card-title-lg">Parâmetros da Simulação</div>
          <div class="card-sub-lg">Mais agentes e rodadas = análise mais rica e precisa, porém mais lenta.</div>

          <!-- Slider: Agentes -->
          <div class="param-block">
            <div class="param-header">
              <label class="param-label">Número de Agentes</label>
              <span class="param-value accent">{{ agentes }}</span>
            </div>
            <input
              type="range"
              min="5"
              max="500"
              step="5"
              v-model.number="agentes"
              class="slider"
            />
            <div class="param-bounds">
              <span>5 (teste rápido)</span>
              <span>500 (máxima riqueza)</span>
            </div>
            <div class="param-desc">{{ descricaoAgentes }}</div>
          </div>

          <!-- Slider: Rodadas -->
          <div class="param-block">
            <div class="param-header">
              <label class="param-label">Número de Rodadas</label>
              <span class="param-value accent">{{ rodadas }}</span>
            </div>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              v-model.number="rodadas"
              class="slider"
            />
            <div class="param-bounds">
              <span>1 (instantâneo)</span>
              <span>100 (evolução completa)</span>
            </div>
            <div class="param-desc">{{ descricaoRodadas }}</div>
          </div>

          <!-- Data de referência -->
          <div class="param-block">
            <div class="param-header">
              <label class="param-label">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14" style="margin-right:6px;vertical-align:middle">
                  <rect x="1" y="3" width="14" height="12" rx="1.5"/><line x1="5" y1="1" x2="5" y2="5"/><line x1="11" y1="1" x2="11" y2="5"/><line x1="1" y1="7" x2="15" y2="7"/>
                </svg>
                Data de Referência Temporal
              </label>
            </div>
            <div class="param-sub">O sistema usará esta data como "hoje" em todas as análises e cenários.</div>
            <input type="date" v-model="dataReferencia" class="field-input date-input" />
            <div class="param-tip">💡 Dica: altere para simular cenários em diferentes momentos (ex: 6 meses atrás, 1 ano no futuro).</div>
          </div>
        </div>

        <!-- Resumo -->
        <div class="card summary-card">
          <div class="summary-title">Resumo da sua simulação</div>
          <div class="readiness-row">
            <span class="summary-key">Prontidão para decisão</span>
            <span class="summary-val"><strong>{{ prontidaoDecisao }}%</strong> — {{ prontidaoLabel }}</span>
          </div>
          <div class="summary-grid">
            <div class="summary-row">
              <span class="summary-key">Hipótese</span>
              <span class="summary-val">{{ hipotese.length > 80 ? hipotese.slice(0, 80) + '...' : hipotese }}</span>
            </div>
            <div class="summary-row" v-if="arquivos.length">
              <span class="summary-key">Materiais</span>
              <span class="summary-val">{{ arquivos.length }} arquivo{{ arquivos.length > 1 ? 's' : '' }}</span>
            </div>
            <div class="summary-row">
              <span class="summary-key">Agentes</span>
              <span class="summary-val accent">{{ agentes }}</span>
            </div>
            <div class="summary-row">
              <span class="summary-key">Rodadas</span>
              <span class="summary-val accent">{{ rodadas }}</span>
            </div>
          </div>

          <div class="exec-panel">
            <div class="summary-title">Painel Executivo de Lançamento</div>
            <div class="exec-metrics">
              <div class="exec-chip">Adoção prevista: <strong>{{ metricasExecutivasCalibradas.adocao }}%</strong></div>
              <div class="exec-chip">Risco reputacional: <strong>{{ metricasExecutivasCalibradas.riscoReputacional }}%</strong></div>
              <div class="exec-chip">Confiança da recomendação: <strong>{{ metricasExecutivasCalibradas.confianca }}%</strong></div>
            </div>
            <div class="calibration-grid">
              <input v-model="outcomeAdocaoReal" class="field-input" type="number" min="0" max="100" placeholder="Adoção real histórica (%)" />
              <input v-model="outcomeRiscoReal" class="field-input" type="number" min="0" max="100" placeholder="Risco real histórico (%)" />
              <input v-model="outcomeConfiancaReal" class="field-input" type="number" min="0" max="100" placeholder="Confiança real histórica (%)" />
            </div>
            <div class="scenario-compare">
              <div
                v-for="item in cenariosComparativos"
                :key="item.id"
                class="scenario-row"
                :class="{ selected: estrategiaSelecionada === item.id }"
                @click="selecionarEstrategia(item.id)"
              >
                <span>{{ item.titulo }}</span>
                <span class="accent">{{ item.score }}%</span>
              </div>
            </div>
            <div class="exec-recommend">
              Recomendação: priorizar <strong>{{ melhorCenario.titulo }}</strong> no lançamento inicial.
            </div>
            <div class="exec-actions-row">
              <button class="btn-inline" @click="aplicarMelhorEstrategia">Aplicar estratégia recomendada à hipótese</button>
              <button class="btn-inline" @click="copiarResumoExecutivo">
                {{ resumoCopiado ? 'Resumo copiado ✓' : 'Copiar resumo executivo' }}
              </button>
              <button class="btn-inline" @click="baixarBoardHtml">Exportar board-ready (HTML)</button>
              <button class="btn-inline" @click="baixarSlideTxt">Exportar slide (TXT)</button>
              <button class="btn-inline" @click="adicionarAoBenchmark">Salvar no benchmark</button>
            </div>
            <ul class="exec-actions">
              <li v-for="acao in plano72h" :key="acao">{{ acao }}</li>
            </ul>
            <div class="benchmark-box" v-if="benchmarkMedias">
              <div class="summary-title">Benchmark histórico (últimas {{ historicoBenchmarks.length }})</div>
              <div class="exec-metrics">
                <div class="exec-chip">Média adoção: <strong>{{ benchmarkMedias.adocao }}%</strong></div>
                <div class="exec-chip">Média risco: <strong>{{ benchmarkMedias.risco }}%</strong></div>
                <div class="exec-chip">Média confiança: <strong>{{ benchmarkMedias.confianca }}%</strong></div>
              </div>
              <div class="benchmark-delta">
                Delta atual vs histórico: adoção <strong>{{ comparativoBenchmark.adocao > 0 ? '+' : '' }}{{ comparativoBenchmark.adocao }}%</strong>,
                risco <strong>{{ comparativoBenchmark.risco > 0 ? '+' : '' }}{{ comparativoBenchmark.risco }}%</strong>,
                confiança <strong>{{ comparativoBenchmark.confianca > 0 ? '+' : '' }}{{ comparativoBenchmark.confianca }}%</strong>.
              </div>
              <div class="benchmark-list">
                <div class="benchmark-row" v-for="item in historicoBenchmarks" :key="item.id">
                  <span>{{ item.nome }}</span>
                  <span>A {{ item.adocao }}% • R {{ item.risco }}% • C {{ item.confianca }}%</span>
                  <button class="btn-inline" @click="removerBenchmark(item.id)">Remover</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Estimativas -->
          <div class="estimates">
            <div class="estimate-item">
              <div class="estimate-icon">⏱</div>
              <div>
                <div class="estimate-label">Tempo estimado</div>
                <div class="estimate-value">~{{ estimativaMinutos }} min</div>
              </div>
            </div>
            <div class="estimate-divider"></div>
            <div class="estimate-item">
              <div class="estimate-icon">💳</div>
              <div>
                <div class="estimate-label">Custo estimado</div>
                <div class="estimate-value">~${{ estimativaCusto }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Erro -->
        <div v-if="error" class="error-msg">{{ error }}</div>

        <div class="step-nav">
          <button class="btn-back" @click="etapaAnterior">← Voltar</button>
          <button
            class="btn-create"
            :class="{ loading: isLoading }"
            :disabled="!etapa3Valida || isLoading"
            @click="criarSimulacao"
          >
            <span v-if="isLoading" class="spinner"></span>
            <span v-else>✦</span>
            {{ isLoading ? 'Criando...' : 'Criar Simulação' }}
          </button>
        </div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
.wizard-shell {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 60px;
}

/* Breadcrumb */
.breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); }
.bc-link { cursor: pointer; color: var(--text-secondary); transition: color 0.15s; }
.bc-link:hover { color: var(--text-primary); }
.bc-sep { color: var(--text-muted); }
.bc-current { color: var(--text-primary); }

/* Header */
.wizard-title { font-size: 26px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; letter-spacing: -0.5px; }
.wizard-sub { font-size: 14px; color: var(--text-secondary); }

/* Steps track */
.steps-track {
  display: flex;
  align-items: flex-start;
  padding: 4px 0;
}
.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
  cursor: pointer;
}
.step-dot {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; z-index: 1;
  background: var(--bg-raised); border: 2px solid var(--border-md);
  color: var(--text-muted); transition: all 0.3s;
}
.step-item.active .step-dot {
  background: var(--accent2); border-color: var(--accent2); color: #fff;
}
.step-item.done .step-dot {
  background: var(--accent); border-color: var(--accent); color: #000;
}
.step-check { display: flex; align-items: center; justify-content: center; }
.step-check svg { width: 16px; height: 16px; }
.step-connector {
  position: absolute;
  top: 15px; left: 50%;
  width: 100%; height: 2px;
  background: var(--border-md);
  z-index: 0; transition: background 0.3s;
}
.step-connector.done { background: var(--accent); }
.step-label {
  font-size: 11px; color: var(--text-muted); margin-top: 6px;
  text-align: center; white-space: nowrap;
}
.step-item.active .step-label { color: var(--accent2); font-weight: 500; }
.step-item.done .step-label { color: var(--text-secondary); }

/* Cards */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-slim { padding: 16px 20px; gap: 12px; }
.card-head { display: flex; align-items: flex-start; gap: 12px; }
.card-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.card-title { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.card-sub { font-size: 13px; color: var(--text-secondary); margin-top: 2px; line-height: 1.5; }
.card-title-lg { font-size: 17px; font-weight: 600; color: var(--text-primary); }
.card-sub-lg { font-size: 13px; color: var(--text-secondary); }

/* Segment grid */
.segment-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.segment-btn {
  background: var(--bg-raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  color: var(--text-secondary);
}
.segment-btn:hover {
  border-color: var(--border-md);
  color: var(--text-primary);
  background: var(--bg-overlay);
}
.segment-btn.selected {
  border-color: var(--accent2);
  background: var(--accent2-dim);
  color: var(--text-primary);
}
.seg-icon { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
.seg-icon :deep(svg) { width: 20px; height: 20px; }
.seg-label { font-size: 11px; text-align: center; line-height: 1.3; }

/* Exemplos */
.examples-label {
  font-size: 12px; color: var(--accent2);
  display: flex; align-items: center; gap: 6px;
}
.ex-icon { font-size: 10px; }
.examples-list { display: flex; flex-direction: column; gap: 6px; }
.ab-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.example-chip {
  background: var(--bg-overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  text-align: left;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
}
.example-chip:hover {
  border-color: var(--accent2);
  color: var(--text-primary);
  background: var(--accent2-dim);
}

/* Fields */
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label-row { display: flex; justify-content: space-between; align-items: center; }
.field-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.required { color: var(--accent); }
.field-input {
  background: var(--bg-raised);
  border: 1px solid var(--border-md);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  padding: 11px 14px;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
}
.field-input:focus { border-color: var(--accent2); }
.field-textarea {
  background: var(--bg-raised);
  border: 1px solid var(--border-md);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  padding: 11px 14px;
  outline: none;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
  transition: border-color 0.15s;
}
.field-textarea:focus { border-color: var(--accent2); }
.field-hint { font-size: 12px; color: var(--text-muted); }
.date-input { max-width: 200px; }

/* Botão gerar com IA */
.btn-generate {
  background: var(--accent2);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 13px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  letter-spacing: -0.2px;
}
.btn-generate:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-generate:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* Divider label */
.card-divider-label {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  position: relative;
  padding: 0 12px;
}
.card-divider-label::before,
.card-divider-label::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 30%;
  height: 1px;
  background: var(--border);
}
.card-divider-label::before { left: 0; }
.card-divider-label::after { right: 0; }

/* Drop zone */
.drop-zone {
  border: 2px dashed var(--border-md);
  border-radius: 12px;
  padding: 36px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-raised);
}
.drop-zone:hover, .drop-zone.drag-over {
  border-color: var(--accent);
  background: rgba(0,229,195,0.04);
}
.drop-content { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.drop-icon { color: var(--text-muted); margin-bottom: 4px; }
.drop-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.drop-sub { font-size: 12px; color: var(--text-muted); }

/* Optional badge */
.optional-badge {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-overlay);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2px 8px;
  margin-left: 8px;
  vertical-align: middle;
}

/* Quality tip */
.quality-tip {
  background: rgba(124,111,247,0.08);
  border: 1px solid rgba(124,111,247,0.2);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: var(--accent2);
  display: flex;
  gap: 8px;
  line-height: 1.5;
}

/* Files list */
.files-list { display: flex; flex-direction: column; gap: 8px; }
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-overlay);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
}
.file-icon { font-size: 18px; flex-shrink: 0; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-size: 11px; color: var(--text-muted); }
.file-remove {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  transition: color 0.15s;
}
.file-remove:hover { color: var(--danger); }

/* Quality indicator */
.quality-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.quality-fill { height: 100%; border-radius: 2px; transition: all 0.4s; }
.quality-info { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
.quality-label { font-size: 12px; font-weight: 600; }
.quality-desc { font-size: 12px; color: var(--text-muted); }
.upload-notice { font-size: 12px; color: var(--text-secondary); }

/* Params */
.param-block { display: flex; flex-direction: column; gap: 8px; }
.param-header { display: flex; justify-content: space-between; align-items: center; }
.param-label { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.param-value { font-size: 18px; font-weight: 600; font-family: var(--font-mono); }
.param-bounds { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.param-desc { font-size: 12px; color: var(--text-secondary); background: var(--bg-raised); border-radius: 6px; padding: 8px 12px; }
.param-sub { font-size: 12px; color: var(--text-secondary); }
.param-tip { font-size: 12px; color: var(--accent2); }

.slider {
  width: 100%;
  accent-color: var(--accent2);
  height: 4px;
  cursor: pointer;
}

/* Summary */
.summary-card { background: var(--bg-raised); }
.summary-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.readiness-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px dashed var(--border-md);
  border-radius: 8px;
  background: var(--bg-overlay);
}
.summary-grid { display: flex; flex-direction: column; gap: 0; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.summary-row:last-child { border-bottom: none; }
.summary-key { color: var(--text-muted); }
.summary-val { color: var(--text-primary); max-width: 60%; text-align: right; }
.exec-panel {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg-overlay);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.exec-metrics { display: flex; flex-wrap: wrap; gap: 8px; }
.calibration-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.exec-chip {
  font-size: 12px;
  border: 1px solid var(--border-md);
  border-radius: 20px;
  padding: 4px 10px;
  background: var(--bg-raised);
}
.scenario-compare {
  border: 1px dashed var(--border-md);
  border-radius: 8px;
  overflow: hidden;
}
.scenario-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s;
}
.scenario-row:last-child { border-bottom: none; }
.scenario-row:hover { background: var(--bg-raised); }
.scenario-row.selected { background: var(--accent2-dim); }
.exec-recommend { font-size: 13px; color: var(--text-primary); }
.exec-actions-row { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-inline {
  border: 1px solid var(--border-md);
  background: var(--bg-raised);
  color: var(--text-primary);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.btn-inline:hover { border-color: var(--accent2); }
.exec-actions { margin: 0; padding-left: 18px; color: var(--text-secondary); font-size: 12px; display: grid; gap: 6px; }
.benchmark-box {
  border: 1px solid var(--border-md);
  border-radius: 8px;
  padding: 10px;
  background: var(--bg-raised);
  display: grid;
  gap: 8px;
}
.benchmark-delta { font-size: 12px; color: var(--text-secondary); }
.benchmark-list { display: grid; gap: 6px; }
.benchmark-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 8px;
}

/* Estimates */
.estimates {
  display: flex;
  align-items: center;
  background: var(--bg-overlay);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.estimate-item { display: flex; align-items: center; gap: 12px; padding: 14px 20px; flex: 1; }
.estimate-icon { font-size: 22px; }
.estimate-label { font-size: 11px; color: var(--text-muted); }
.estimate-value { font-size: 16px; font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); }
.estimate-divider { width: 1px; height: 40px; background: var(--border); }

/* Nav buttons */
.step-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.btn-back, .btn-cancel {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 10px 16px;
  border-radius: 8px;
  transition: color 0.15s;
}
.btn-back:hover, .btn-cancel:hover { color: var(--text-primary); }
.btn-next {
  background: var(--accent2);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-next:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-next:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
.btn-create {
  background: var(--accent);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 13px 28px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  letter-spacing: -0.3px;
}
.btn-create:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-create:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }

/* Accent color */
.accent { color: var(--accent); }

/* Spinner */
.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(0,0,0,0.3);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.btn-generate .spinner { border-color: rgba(255,255,255,0.3); border-top-color: #fff; }

@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.error-msg {
  background: rgba(255,90,90,0.1);
  border: 1px solid rgba(255,90,90,0.3);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--danger);
}

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: all 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(-8px); }
.file-list-enter-active, .file-list-leave-active { transition: all 0.2s ease; }
.file-list-enter-from, .file-list-leave-to { opacity: 0; transform: translateX(-10px); }
.step-content { display: flex; flex-direction: column; gap: 16px; animation: stepIn 0.3s ease; }
@keyframes stepIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }

@media (max-width: 900px) {
  .ab-grid { grid-template-columns: 1fr; }
  .exec-metrics { flex-direction: column; }
  .calibration-grid { grid-template-columns: 1fr; }
  .benchmark-row { grid-template-columns: 1fr; }
}
</style>
