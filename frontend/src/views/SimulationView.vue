<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const route  = useRoute()
const router = useRouter()

// ─── Tela: 'config' ou 'pipeline' ─────────────────────────────
// Se agentes e rodadas já vierem no query (do wizard/modal), pular config
const _fromWizard = !!(route.query.agentes && route.query.rodadas)
const tela = ref(_fromWizard ? 'pipeline' : 'config')

// ─── Config ───────────────────────────────────────────────────
const cfgAgentes  = ref(Number(route.query.agentes)  || 50)
const cfgRodadas  = ref(Number(route.query.rodadas)  || 20)
// Hipótese e título opcionais passados pelo ProjetoView (nova simulação)
const cfgHipotese = ref(route.query.hipotese ? decodeURIComponent(route.query.hipotese) : '')
const cfgTitulo   = ref(route.query.titulo   ? decodeURIComponent(route.query.titulo)   : '')

// ─── Pipeline ─────────────────────────────────────────────────
const phase       = ref('init')
const erro        = ref('')
const progress    = ref(0)
const statusMsg   = ref('Iniciando...')
const detalhe     = ref('')
const projectData = ref(null)
const simulationId = ref(null)
const abortado    = ref(false)
let pollTimer     = null

// ─── Seleção de Agentes ───────────────────────────────────────
const entityTypes = ref([])          // Tipos de entidade do ontology (auto-detectados)
const selectedTypes = ref([])        // Tipos selecionados pelo usuário
const customAgents = ref([])         // Agentes adicionados da biblioteca
const showAgentSelection = ref(false)
const novoAgente = ref('')
const activeCategory = ref(null)     // Categoria expandida
const showNewCategory = ref(false)
const novaCategoria = ref({ icon: '🏷', label: '', color: '#00e5c3' })
const customCategories = ref([])

// ─── Biblioteca de Agentes por Categoria ──────────────────────
const AGENT_LIBRARY_BASE = [
  { id: 'consumidores', icon: '🛒', label: 'Consumidores', color: '#00e5c3', agents: [
    { name: 'Jovem Urbano (18-25)', desc: 'Digital native, compra por impulso, influenciado por redes sociais', tags: ['varejo','tech','moda'] },
    { name: 'Mãe com Filhos', desc: 'Prioriza qualidade e segurança, sensível a preço, busca praticidade', tags: ['varejo','alimentação','saúde'] },
    { name: 'Idoso Tradicional (60+)', desc: 'Fiel a marcas, prefere atendimento presencial, resistente a mudanças', tags: ['varejo','saúde','financeiro'] },
    { name: 'Profissional Classe A', desc: 'Alto poder aquisitivo, valoriza exclusividade e experiência premium', tags: ['luxo','tech','serviços'] },
    { name: 'Consumidor Classe C', desc: 'Sensível a preço, busca parcelamento, compara muito antes de comprar', tags: ['varejo','financeiro'] },
    { name: 'Empreendedor PME', desc: 'Busca custo-benefício, decide rápido, precisa de ROI claro', tags: ['b2b','tech','serviços'] },
    { name: 'Consumidor Digital', desc: 'Compra 100% online, compara em marketplaces, valoriza frete grátis', tags: ['ecommerce','tech'] },
    { name: 'Consumidor Local', desc: 'Prefere comércio do bairro, valoriza relacionamento e confiança', tags: ['varejo','alimentação'] },
  ]},
  { id: 'reguladores', icon: '🏛', label: 'Reguladores & Governo', color: '#7c6ff7', agents: [
    { name: 'PROCON', desc: 'Defesa do consumidor — fiscaliza práticas abusivas, propaganda enganosa', tags: ['todos'] },
    { name: 'ANVISA', desc: 'Vigilância sanitária — regulamenta alimentos, cosméticos, medicamentos', tags: ['saúde','alimentação'] },
    { name: 'BACEN', desc: 'Banco Central — regula serviços financeiros, fintechs, meios de pagamento', tags: ['financeiro','fintech'] },
    { name: 'INMETRO', desc: 'Metrologia — certifica qualidade e segurança de produtos', tags: ['varejo','indústria'] },
    { name: 'IBAMA', desc: 'Meio ambiente — fiscaliza impacto ambiental e sustentabilidade', tags: ['indústria','agro'] },
    { name: 'CADE', desc: 'Defesa econômica — combate monopólio e práticas anticompetitivas', tags: ['todos'] },
    { name: 'ANATEL', desc: 'Telecomunicações — regula internet, telefonia, dados', tags: ['tech','telecom'] },
    { name: 'CVM', desc: 'Valores mobiliários — regula investimentos, tokens, crowdfunding', tags: ['financeiro','crypto'] },
    { name: 'LGPD/ANPD', desc: 'Proteção de dados pessoais — fiscaliza uso de dados do consumidor', tags: ['tech','todos'] },
  ]},
  { id: 'financeiro', icon: '💰', label: 'Mercado Financeiro', color: '#f5a623', agents: [
    { name: 'Banco Tradicional', desc: 'Conservador, burocrático, grande base de clientes, crédito restritivo', tags: ['financeiro'] },
    { name: 'Fintech', desc: 'Ágil, digital first, taxas baixas, experiência moderna', tags: ['financeiro','tech'] },
    { name: 'Investidor Anjo', desc: 'Busca oportunidades early-stage, avalia equipe e mercado', tags: ['startup'] },
    { name: 'Analista de Mercado', desc: 'Avalia riscos e oportunidades com dados, visão macro', tags: ['financeiro'] },
    { name: 'Consultor Financeiro', desc: 'Orienta clientes sobre investimentos e planejamento', tags: ['financeiro','serviços'] },
    { name: 'Operadora de Crédito', desc: 'Crediário, BNPL, parcelamento — sensível a inadimplência', tags: ['varejo','financeiro'] },
  ]},
  { id: 'influenciadores', icon: '📱', label: 'Influenciadores & Mídia', color: '#e91e9c', agents: [
    { name: 'Influenciador Digital Local', desc: 'Micro-influencer da cidade, alta credibilidade local, 5k-50k seguidores', tags: ['todos'] },
    { name: 'Creator de Nicho', desc: 'Especialista no tema, audiência engajada, review detalhado', tags: ['todos'] },
    { name: 'Jornalista/Blogueiro', desc: 'Cobertura editorial, busca fatos e novidades, amplifica narrativa', tags: ['todos'] },
    { name: 'Influenciador Nacional', desc: 'Grande alcance, 500k+ seguidores, alto custo, impacto massivo', tags: ['moda','tech','lifestyle'] },
    { name: 'Podcaster', desc: 'Formato longo, audiência fiel, análise profunda', tags: ['tech','negócios'] },
    { name: 'TikToker/Reels', desc: 'Conteúdo curto e viral, público jovem, tendências rápidas', tags: ['moda','varejo','alimentação'] },
  ]},
  { id: 'concorrentes', icon: '🏪', label: 'Concorrentes & Mercado', color: '#ff5a5a', agents: [
    { name: 'Líder de Mercado', desc: 'Marca dominante no setor, alto market share, define tendências', tags: ['todos'] },
    { name: 'Novo Entrante', desc: 'Startup ou empresa entrando no mercado, agressiva em preço', tags: ['todos'] },
    { name: 'Marketplace/E-commerce', desc: 'Shopee, Mercado Livre, Amazon — concorrência de preço e conveniência', tags: ['varejo','ecommerce'] },
    { name: 'Concorrente Regional', desc: 'Forte na região, conhece o público local, relacionamento sólido', tags: ['varejo'] },
    { name: 'Franquia Nacional', desc: 'Marca conhecida, padronização, poder de marketing', tags: ['varejo','alimentação'] },
  ]},
  { id: 'industria', icon: '🏭', label: 'Indústria & Fornecedores', color: '#4caf50', agents: [
    { name: 'Fabricante/Fornecedor', desc: 'Produz o que você vende, define preço de custo e prazos', tags: ['varejo','indústria'] },
    { name: 'Distribuidor/Atacadista', desc: 'Intermedia entre fábrica e varejo, logística e volume', tags: ['varejo'] },
    { name: 'Representante Comercial', desc: 'Vende para lojistas, conhece o mercado e as dores', tags: ['varejo','b2b'] },
    { name: 'Operador Logístico', desc: 'Entrega, frete, última milha — custo e prazo impactam tudo', tags: ['ecommerce','varejo'] },
  ]},
  { id: 'servicos', icon: '🔧', label: 'Serviços & Tech', color: '#1da1f2', agents: [
    { name: 'Cliente de Delivery', desc: 'Pede por app, sensível a tempo e preço de entrega', tags: ['delivery','alimentação'] },
    { name: 'Restaurante Parceiro', desc: 'Depende de plataformas, margem apertada, busca volume', tags: ['delivery','alimentação'] },
    { name: 'Entregador', desc: 'Gig economy, sensível a taxa por entrega, flexibilidade', tags: ['delivery'] },
    { name: 'Desenvolvedor/Tech', desc: 'Avalia produto pela tecnologia, API, integração', tags: ['tech','saas'] },
    { name: 'Usuário SaaS B2B', desc: 'Empresa que compra software, precisa de ROI e suporte', tags: ['tech','saas','b2b'] },
  ]},
  { id: 'institucional', icon: '🏢', label: 'Institucional & Social', color: '#795548', agents: [
    { name: 'Associação Comercial', desc: 'Representa o comércio local, advocacy, networking', tags: ['varejo'] },
    { name: 'Sindicato/Classe', desc: 'Representa trabalhadores, negocia direitos, influência política', tags: ['indústria','serviços'] },
    { name: 'Universidade/Pesquisador', desc: 'Análise acadêmica, dados de pesquisa, credibilidade técnica', tags: ['todos'] },
    { name: 'ONG/Instituto Social', desc: 'Causa social, sustentabilidade, impacto comunitário', tags: ['todos'] },
    { name: 'Reclame Aqui', desc: 'Plataforma de reclamações — reputação e resolução pública', tags: ['todos'] },
    { name: 'SEBRAE', desc: 'Apoio a pequenas empresas — capacitação, crédito, mentoria', tags: ['pme','varejo'] },
  ]},
]

// Biblioteca completa = base + custom
const AGENT_LIBRARY = computed(() => savedLibrary ? [...savedLibrary, ...customCategories.value] : [...AGENT_LIBRARY_BASE, ...customCategories.value])

// Carregar biblioteca do localStorage (compartilhada com AgentLibraryView)
function loadAgentLibrary() {
  try {
    const saved = localStorage.getItem('augur_agent_library')
    if (saved) return JSON.parse(saved)
  } catch {}
  return null
}
const savedLibrary = loadAgentLibrary()

// Contar agentes selecionados por categoria
const agentCounts = computed(() => {
  const counts = {}
  AGENT_LIBRARY.value.forEach(cat => { counts[cat.id] = 0 })
  customAgents.value.forEach(a => {
    if (a.categoryId) counts[a.categoryId] = (counts[a.categoryId] || 0) + 1
  })
  return counts
})

const totalSelecionados = computed(() => {
  return entityTypes.value.filter(e => e.selected).length + customAgents.value.length
})

const autoCompleteCount = computed(() => {
  return Math.max(0, cfgAgentes.value - totalSelecionados.value)
})

const maxRounds = computed(() => cfgRodadas.value)
const maxAgents = computed(() => cfgAgentes.value)

const descAgentes = computed(() => {
  if (cfgAgentes.value <= 20)  return 'Teste rápido — ideal para validar a hipótese'
  if (cfgAgentes.value <= 100) return 'Bom equilíbrio entre velocidade e precisão'
  if (cfgAgentes.value <= 250) return 'Alta fidelidade'
  return 'Máxima riqueza'
})
const descRodadas = computed(() => {
  if (cfgRodadas.value <= 5)  return 'Reação imediata ao evento'
  if (cfgRodadas.value <= 25) return 'Captura tendências de curto prazo'
  if (cfgRodadas.value <= 60) return 'Evolução completa da opinião'
  return 'Análise profunda'
})
const estMin   = computed(() => Math.round(Math.max(2, cfgAgentes.value * cfgRodadas.value * 0.04)))
const estCusto = computed(() => (cfgAgentes.value * cfgRodadas.value * 0.0008).toFixed(2))

const fases = [
  { key: 'building_graph',    label: 'Construindo Grafo',    desc: 'Analisando documentos e criando rede de conhecimento' },
  { key: 'creating_sim',      label: 'Criando Simulação',    desc: 'Configurando o ambiente de simulação' },
  { key: 'selecting_agents',  label: 'Seleção de Agentes',   desc: 'Escolha quais tipos de agentes participam da simulação' },
  { key: 'preparing',         label: 'Gerando Agentes',      desc: 'Criando perfis únicos para cada agente com IA' },
  { key: 'starting',          label: 'Iniciando',            desc: 'Lançando a simulação multiagente' },
]

const faseAtual  = computed(() => fases.findIndex(f => f.key === phase.value))
const phaseLabel = computed(() => {
  if (phase.value === 'running')  return '✅ Simulação Iniciada!'
  if (phase.value === 'error')    return 'Erro no pipeline'
  if (phase.value === 'aborted')  return 'Cancelado'
  return fases.find(f => f.key === phase.value)?.label || 'Inicializando...'
})

function traduzir(msg) {
  if (!msg) return ''
  if (/[\u4e00-\u9fff]/.test(msg)) return 'Processando...'
  const map = [
    ['building',   'Construindo grafo de conhecimento...'],
    ['entity',     'Extraindo entidades e relacionamentos...'],
    ['chunk',      'Processando blocos de texto...'],
    ['batch',      'Processando lote de dados...'],
    ['sending',    'Enviando dados para o grafo...'],
    ['graph',      'Atualizando grafo de conhecimento...'],
    ['completed',  'Concluído!'],
    ['preparing',  'Preparando agentes de IA...'],
    ['generating', 'Gerando perfis dos agentes...'],
    ['profile',    'Criando perfil do agente...'],
    ['ready',      'Tudo pronto!'],
    ['starting',   'Iniciando simulação...'],
    ['processing', 'Processando...'],
    ['analyzing',  'Analisando documentos...'],
  ]
  const lower = msg.toLowerCase()
  for (const [k, v] of map) if (lower.includes(k)) return v
  return msg
}

// ─── Iniciar pipeline após config ─────────────────────────────
function iniciar() {
  tela.value = 'pipeline'
  runPipeline().catch(handleError)
}

// ─── Cancelar ─────────────────────────────────────────────────
async function cancelar() {
  abortado.value = true
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (simulationId.value) {
    try { await service.post('/api/simulation/stop', { simulation_id: simulationId.value }) } catch { /* ignorar */ }
  }
  phase.value   = 'aborted'
  progress.value = 0
}

function voltar() {
  router.push(`/projeto/${route.params.projectId}`)
}

// ─── Pipeline ─────────────────────────────────────────────────
async function runPipeline() {
  const pid = route.params.projectId

  phase.value    = 'building_graph'
  statusMsg.value = 'Verificando projeto...'
  detalhe.value  = ''
  progress.value = 5

  const project = await getProject(pid)
  projectData.value = project

  if (abortado.value) return

  // ── Verificar grafo ──────────────────────────────────────────
  if (project.status === 'graph_completed' && project.graph_id) {
    // Grafo já pronto — pular direto para criação da simulação
    progress.value  = 40
    statusMsg.value = 'Grafo já disponível!'
  } else if (project.graph_build_task_id) {
    // Task existe — verificar se ainda está viva
    const taskViva = await verificarTask(project.graph_build_task_id)

    if (!taskViva) {
      // Task morreu (404) — precisa reconstruir
      statusMsg.value = 'Reconstruindo grafo de conhecimento...'
      detalhe.value   = 'O processo anterior foi interrompido. Reiniciando...'
      await reconstruirGrafo(pid, project)
    } else {
      // Task viva — aguardar conclusão
      statusMsg.value = 'Construindo rede de conhecimento...'
      detalhe.value   = 'Isso pode levar entre 2 e 15 minutos.'
      await waitForGraphBuild(project.graph_build_task_id, pid)
    }
  } else if (project.status === 'graph_building') {
    // Status diz building mas sem task_id — servidor reiniciou
    statusMsg.value = 'Reconstruindo grafo...'
    detalhe.value   = 'Processo anterior foi interrompido. Reiniciando...'
    await reconstruirGrafo(pid, project)
  } else {
    // Nunca foi construído
    statusMsg.value = 'Iniciando construção do grafo...'
    await reconstruirGrafo(pid, project)
  }

  if (abortado.value) return

  const updated = await getProject(pid)
  projectData.value = updated
  if (!updated.graph_id) throw new Error('Grafo não encontrado após construção. Tente novamente.')

  // ── Criar simulação ──────────────────────────────────────────
  if (abortado.value) return
  phase.value     = 'creating_sim'
  statusMsg.value = 'Criando simulação...'
  detalhe.value   = ''
  progress.value  = 45

  const simData = await createSimulation(pid, updated.graph_id)
  simulationId.value = simData.simulation_id

  // ── Seleção de Agentes ─────────────────────────────────────
  if (abortado.value) return
  phase.value = 'selecting_agents'
  statusMsg.value = 'Selecione os agentes da simulação'
  detalhe.value = ''
  progress.value = 45
  
  // Carregar entity types do ontology do projeto (traduzir para PT-BR)
  const TRANSLATE = {
    'Consumer':'Consumidor','LocalBusiness':'Negocio Local','Influencer':'Influenciador',
    'RetailChain':'Rede de Varejo','EcommercePlatform':'Plataforma E-commerce',
    'LocalInfluencer':'Influenciador Local','GovernmentAgency':'Orgao Governamental',
    'Person':'Pessoa','Organization':'Organizacao','Competitor':'Concorrente',
    'FinancialInstitution':'Instituicao Financeira','Media':'Midia',
    'Supplier':'Fornecedor','Regulator':'Regulador','Investor':'Investidor',
    'Student':'Estudante','PublicFigure':'Figura Publica','Professional':'Profissional',
    'Company':'Empresa','Brand':'Marca','Product':'Produto','Service':'Servico',
    'Market':'Mercado','Industry':'Industria','Technology':'Tecnologia',
    'Community':'Comunidade','Association':'Associacao'
  }
  const traduzir = (name) => TRANSLATE[name] || name.replace(/([A-Z])/g, ' $1').trim()
  
  const ont = projectData.value?.ontology?.entity_types || []
  entityTypes.value = ont.map(et => ({
    name: traduzir(et.name || et),
    nameOriginal: et.name || et,
    description: et.description || '',
    examples: et.examples || [],
    selected: true
  }))
  
  // Mostrar painel e PAUSAR pipeline até o usuário confirmar
  showAgentSelection.value = true
  await new Promise(resolve => { window._resolveAgentSelection = resolve })
  showAgentSelection.value = false

  // ── Preparar agentes com tipos selecionados ──────────────────
  if (abortado.value) return
  phase.value     = 'preparing'
  statusMsg.value = 'Gerando perfis dos agentes com IA...'
  detalhe.value   = `Criando ${cfgAgentes.value} agentes únicos...`
  progress.value  = 50

  const prep = await prepareSimulation(simData.simulation_id, selectedTypes.value)
  if (prep.already_prepared) {
    progress.value = 85
  } else if (prep.task_id) {
    await waitForPrepare(prep.task_id, simData.simulation_id)
  }

  // ── Iniciar ───────────────────────────────────────────────────
  if (abortado.value) return
  phase.value     = 'starting'
  statusMsg.value = 'Lançando simulação...'
  detalhe.value   = ''
  progress.value  = 90

  await startSimulation(simData.simulation_id)

  if (abortado.value) return
  phase.value     = 'running'
  statusMsg.value = 'Simulação iniciada com sucesso!'
  detalhe.value   = 'Redirecionando...'
  progress.value  = 100

  setTimeout(() => {
    if (!abortado.value) router.push(`/simulacao/${simData.simulation_id}/executar`)
  }, 1500)
}

// ─── Verificar se task existe no backend ──────────────────────
async function verificarTask(taskId) {
  try {
    const res  = await service.get(`/api/graph/task/${taskId}`)
    const task = res.data || res
    if (task.status === 'failed') return false
    return true
  } catch (e) {
    const status = e?.response?.status
    if (status === 404) return false
    return true
  }
}

// ─── Reconstruir grafo ────────────────────────────────────────
async function reconstruirGrafo(pid, project) {
  const res = await service.post('/api/graph/build', {
    project_id:             pid,
    simulation_requirement: project.simulation_requirement || cfgHipotese.value || 'Análise geral',
    force:                  true
  })
  const data = res.data || res
  if (!data.task_id) throw new Error('Falha ao iniciar construção do grafo.')
  await waitForGraphBuild(data.task_id, pid)
}

// ─── Polling do grafo com detecção de 404 ────────────────────
function waitForGraphBuild(taskId, pid) {
  return new Promise((resolve, reject) => {
    let elapsed  = 0
    let notFound = 0
    const maxWait = 900000
    const interval = 5000

    pollTimer = setInterval(async () => {
      if (abortado.value) { clearInterval(pollTimer); resolve(); return }
      elapsed += interval
      if (elapsed > maxWait) {
        clearInterval(pollTimer)
        reject(new Error('Timeout: construção do grafo demorou mais de 15 minutos.'))
        return
      }
      try {
        const res  = await service.get(`/api/graph/task/${taskId}`)
        const task = res.data || res
        notFound = 0

        if (task.progress) progress.value = 5 + Math.round((task.progress / 100) * 35)
        if (task.message) { statusMsg.value = traduzir(task.message); detalhe.value = '' }

        if (task.status === 'completed') {
          clearInterval(pollTimer); progress.value = 40; resolve()
        } else if (task.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error('Falha na construção do grafo. Tente novamente.'))
        }
      } catch (e) {
        const httpStatus = e?.response?.status

        if (httpStatus === 404) {
          notFound++
          if (notFound >= 2) {
            clearInterval(pollTimer)
            try {
              const proj = await getProject(pid)
              if (proj.status === 'graph_completed' && proj.graph_id) {
                resolve()
              } else {
                reject(new Error('O servidor foi reiniciado durante a construção do grafo. Por favor tente novamente.'))
              }
            } catch {
              reject(new Error('Não foi possível verificar o status do grafo. Tente novamente.'))
            }
          }
        }
      }
    }, interval)
  })
}

// ─── Polling da preparação ────────────────────────────────────
function waitForPrepare(taskId, simId) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const maxWait = 900000
    const interval = 5000

    pollTimer = setInterval(async () => {
      if (abortado.value) { clearInterval(pollTimer); resolve(); return }
      elapsed += interval
      if (elapsed > maxWait) {
        clearInterval(pollTimer)
        reject(new Error('Timeout: preparação dos agentes demorou mais de 15 minutos.'))
        return
      }
      try {
        const res  = await service.post('/api/simulation/prepare/status', { task_id: taskId, simulation_id: simId })
        const data = res.data || res
        if (data.progress) progress.value = 50 + Math.round((data.progress / 100) * 35)
        if (data.message) { statusMsg.value = traduzir(data.message); detalhe.value = '' }

        if (data.status === 'ready' || data.status === 'completed' || data.already_prepared) {
          clearInterval(pollTimer); progress.value = 85; resolve()
        } else if (data.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error('Falha na preparação dos agentes. Tente novamente.'))
        }
      } catch { /* ignorar erros transientes */ }
    }, interval)
  })
}

// ─── API ──────────────────────────────────────────────────────
async function getProject(id) {
  const res = await service.get(`/api/graph/project/${id}`)
  return res.data?.data || res.data || res
}
async function createSimulation(pid, graphId) {
  const res = await service.post('/api/simulation/create', { project_id: pid, graph_id: graphId })
  return res.data?.data || res.data || res
}
async function prepareSimulation(simId, entityTypesFilter = null) {
  const payload = { simulation_id: simId }
  if (entityTypesFilter && entityTypesFilter.length > 0) {
    payload.entity_types = entityTypesFilter
  }
  const res = await service.post('/api/simulation/prepare', payload)
  return res.data?.data || res.data || res
}

function confirmarAgentes() {
  const types = entityTypes.value.filter(et => et.selected).map(et => et.name)
  const customs = customAgents.value.map(a => a.name)
  selectedTypes.value = [...types, ...customs]
  
  if (window._resolveAgentSelection) {
    window._resolveAgentSelection()
    window._resolveAgentSelection = null
  }
}

function toggleEntityType(et) {
  et.selected = !et.selected
}

function toggleCategory(catId) {
  activeCategory.value = activeCategory.value === catId ? null : catId
}

function addAgentFromLibrary(agent, categoryId) {
  if (customAgents.value.some(a => a.name === agent.name)) return
  customAgents.value.push({ ...agent, categoryId, custom: false })
}

function removeAgent(idx) {
  customAgents.value.splice(idx, 1)
}

function isAgentAdded(agentName) {
  return customAgents.value.some(a => a.name === agentName)
}

function adicionarCategoria() {
  const label = novaCategoria.value.label.trim()
  if (!label) return
  const id = 'custom_' + label.toLowerCase().replace(/\s+/g, '_').slice(0, 20)
  if (customCategories.value.some(c => c.id === id)) return
  customCategories.value.push({
    id,
    icon: novaCategoria.value.icon || '🏷',
    label,
    color: novaCategoria.value.color || '#00e5c3',
    agents: []
  })
  novaCategoria.value = { icon: '🏷', label: '', color: '#00e5c3' }
  showNewCategory.value = false
  activeCategory.value = id
}

function addAgentToCustomCategory(catId) {
  const nome = novoAgente.value.trim()
  if (!nome) return
  const cat = customCategories.value.find(c => c.id === catId)
  if (!cat) return
  if (cat.agents.some(a => a.name === nome)) return
  cat.agents.push({ name: nome, desc: 'Agente personalizado', tags: [] })
  addAgentFromLibrary({ name: nome, desc: 'Agente personalizado' }, catId)
  novoAgente.value = ''
}

function adicionarAgente() {
  const nome = novoAgente.value.trim()
  if (!nome) return
  if (customAgents.value.some(a => a.name === nome)) return
  customAgents.value.push({ name: nome, desc: 'Agente personalizado', categoryId: 'custom', custom: true })
  novoAgente.value = ''
}
async function startSimulation(simId) {
  const res = await service.post('/api/simulation/start', {
    simulation_id: simId,
    platform:   'parallel',
    max_rounds: maxRounds.value
  })
  return res.data || res
}

function handleError(e) {
  if (abortado.value) return
  phase.value = 'error'
  erro.value  = e?.response?.data?.error || e?.message || 'Erro inesperado.'
}

function retry() {
  abortado.value = false
  erro.value     = ''
  phase.value    = 'init'
  progress.value = 0
  runPipeline().catch(handleError)
}

// ─── Auto-start se vier do wizard ────────────────────────────
onMounted(() => {
  if (_fromWizard) {
    runPipeline().catch(handleError)
  }
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<template>
  <AppShell title="Nova Simulação">

    <!-- ════════════════════════════ -->
    <!-- TELA DE CONFIG               -->
    <!-- ════════════════════════════ -->
    <div v-if="tela === 'config'" class="config-wrap">
      <div class="config-header">
        <div>
          <h1 class="config-titulo">Configurar Simulação</h1>
          <p class="config-sub">Defina os parâmetros antes de iniciar.</p>
        </div>
        <button class="btn-ghost" @click="voltar">← Voltar</button>
      </div>

      <div class="config-card">
        <div class="param-block">
          <div class="param-h">
            <span class="param-l">Número de Agentes</span>
            <span class="param-v">{{ cfgAgentes }}</span>
          </div>
          <input type="range" min="5" max="500" step="5" v-model.number="cfgAgentes" class="slider"/>
          <div class="param-bounds"><span>5 — rápido</span><span>500 — máxima riqueza</span></div>
          <div class="param-desc">{{ descAgentes }}</div>
        </div>

        <div class="param-block">
          <div class="param-h">
            <span class="param-l">Número de Rodadas</span>
            <span class="param-v">{{ cfgRodadas }}</span>
          </div>
          <input type="range" min="1" max="100" step="1" v-model.number="cfgRodadas" class="slider"/>
          <div class="param-bounds"><span>1 — instantâneo</span><span>100 — evolução completa</span></div>
          <div class="param-desc">{{ descRodadas }}</div>
        </div>

        <div class="estimativas">
          <div class="est"><div class="el">⏱ Tempo estimado</div><div class="ev">~{{ estMin }} min</div></div>
          <div class="es"></div>
          <div class="est"><div class="el">💳 Custo estimado</div><div class="ev">~${{ estCusto }}</div></div>
          <div class="es"></div>
          <div class="est"><div class="el">🤖 Agentes</div><div class="ev ac">{{ cfgAgentes }}</div></div>
          <div class="es"></div>
          <div class="est"><div class="el">🔄 Rodadas</div><div class="ev ac2">{{ cfgRodadas }}</div></div>
        </div>

        <button class="btn-iniciar" @click="iniciar">✦ Iniciar Simulação</button>
      </div>
    </div>

    <!-- ════════════════════════════ -->
    <!-- TELA DE PIPELINE             -->
    <!-- ════════════════════════════ -->
    <div v-else class="pipeline">

      <!-- Progresso global -->
      <div class="prog-global">
        <div class="prog-bar">
          <div class="prog-fill"
            :class="{ 'prog-error': phase==='error' || phase==='aborted', 'prog-done': phase==='running' }"
            :style="{ width: progress+'%' }"
          ></div>
        </div>
        <span class="prog-pct">{{ progress }}%</span>
      </div>

      <!-- Card de status -->
      <div class="status-card"
        :class="{ 'card-error': phase==='error', 'card-done': phase==='running', 'card-aborted': phase==='aborted' }">

        <div class="status-icon" :class="phase">
          <svg v-if="phase==='error' || phase==='aborted'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <svg v-else-if="phase==='running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="28" height="28">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <div v-else class="spinner-icon"></div>
        </div>

        <h2 class="status-titulo">{{ phaseLabel }}</h2>
        <p class="status-msg">{{ statusMsg }}</p>
        <p v-if="detalhe" class="status-detalhe">{{ detalhe }}</p>

        <div v-if="phase==='building_graph'" class="aviso-tempo">
          ⏱ Este processo pode levar entre 2 e 15 minutos. Não feche esta aba.
        </div>
        <div v-if="phase==='preparing'" class="aviso-tempo">
          ⏱ Geração dos agentes pode levar alguns minutos.
        </div>

        <button
          v-if="phase!=='running' && phase!=='error' && phase!=='aborted'"
          class="btn-cancelar"
          @click="cancelar"
        >
          ✕ Cancelar simulação
        </button>
      </div>

      <!-- ═══ SELEÇÃO DE AGENTES ═══ -->
      <div v-if="showAgentSelection" class="agent-select-panel">
        <!-- Header -->
        <div class="asp-header">
          <div class="asp-title-row">
            <h3>🎭 Monte seu Painel de Agentes</h3>
            <div class="asp-counter" :class="{'asp-counter-full': totalSelecionados >= cfgAgentes}">
              {{ totalSelecionados }} / {{ cfgAgentes }} agentes
            </div>
          </div>
          <p>Selecione quem participará da simulação. O AUGUR criará personas únicas para cada tipo escolhido.</p>
        </div>

        <!-- Auto-detectados da hipótese -->
        <div class="asp-section asp-detected" v-if="entityTypes.length">
          <h4>🔍 Detectados na sua Hipótese</h4>
          <p class="asp-section-sub">O AUGUR identificou estes participantes relevantes automaticamente</p>
          <div class="asp-detected-grid">
            <div v-for="et in entityTypes" :key="et.name" 
                 class="asp-chip" :class="{ 'asp-chip-on': et.selected }"
                 @click="toggleEntityType(et)">
              <span class="asp-chip-check">{{ et.selected ? '✓' : '' }}</span>
              <span class="asp-chip-name">{{ et.name }}</span>
              <span class="asp-chip-badge">detectado</span>
            </div>
          </div>
        </div>

        <!-- Biblioteca por Categoria -->
        <div class="asp-section">
          <h4>📚 Biblioteca de Agentes</h4>
          <p class="asp-section-sub">Adicione agentes de diferentes segmentos para enriquecer a simulação</p>
          
          <div class="asp-categories">
            <div v-for="cat in AGENT_LIBRARY" :key="cat.id" class="asp-cat">
              <!-- Category header (clickable) -->
              <div class="asp-cat-header" @click="toggleCategory(cat.id)" :style="{'--cat-color': cat.color}">
                <span class="asp-cat-icon">{{ cat.icon }}</span>
                <span class="asp-cat-label">{{ cat.label }}</span>
                <span class="asp-cat-count" v-if="agentCounts[cat.id]">{{ agentCounts[cat.id] }}</span>
                <span class="asp-cat-arrow" :class="{'asp-cat-open': activeCategory === cat.id}">›</span>
              </div>
              
              <!-- Agent list (expanded) -->
              <div class="asp-cat-agents" v-if="activeCategory === cat.id">
                <div v-for="agent in cat.agents" :key="agent.name" 
                     class="asp-agent" :class="{ 'asp-agent-added': isAgentAdded(agent.name) }"
                     @click="isAgentAdded(agent.name) ? null : addAgentFromLibrary(agent, cat.id)">
                  <div class="asp-agent-left">
                    <div class="asp-agent-dot" :style="{background: cat.color}"></div>
                    <div>
                      <div class="asp-agent-name">{{ agent.name }}</div>
                      <div class="asp-agent-desc">{{ agent.desc }}</div>
                    </div>
                  </div>
                  <button v-if="!isAgentAdded(agent.name)" class="asp-agent-add" :style="{color: cat.color}">+ Adicionar</button>
                  <span v-else class="asp-agent-ok">✓ Adicionado</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Nova Categoria -->
        <div class="asp-section">
          <div class="asp-new-cat-header">
            <h4>🏷 Criar Nova Categoria</h4>
            <button class="asp-toggle-cat" @click="showNewCategory = !showNewCategory">
              {{ showNewCategory ? '✕ Fechar' : '+ Nova Categoria' }}
            </button>
          </div>
          <div v-if="showNewCategory" class="asp-new-cat-form">
            <div class="asp-new-cat-row">
              <input v-model="novaCategoria.icon" class="asp-cat-icon-input" maxlength="2" placeholder="🏷"/>
              <input v-model="novaCategoria.label" class="asp-input" placeholder="Nome da categoria (ex: Fornecedores de Tecnologia)" @keyup.enter="adicionarCategoria()"/>
              <input v-model="novaCategoria.color" type="color" class="asp-color-input"/>
              <button class="asp-add-btn" @click="adicionarCategoria()">Criar</button>
            </div>
          </div>
        </div>

        <!-- Agente personalizado -->
        <div class="asp-section">
          <h4>✍️ Agente Personalizado</h4>
          <div class="asp-custom-row">
            <input v-model="novoAgente" placeholder="Descreva o agente (ex: Dono de academia em cidade pequena)" 
                   class="asp-input" @keyup.enter="adicionarAgente()"/>
            <button class="asp-add-btn" @click="adicionarAgente()">Adicionar</button>
          </div>
        </div>

        <!-- Agentes selecionados -->
        <div class="asp-section" v-if="customAgents.length">
          <h4>Seus Agentes Selecionados</h4>
          <div class="asp-selected-list">
            <span v-for="(a, i) in customAgents" :key="i" class="asp-sel-tag" 
                  :style="{'--tc': AGENT_LIBRARY.find(c => c.id === a.categoryId)?.color || '#00e5c3'}">
              {{ a.name }}
              <span class="asp-sel-x" @click="removeAgent(i)">✕</span>
            </span>
          </div>
        </div>

        <!-- Auto-complete info -->
        <div class="asp-auto" v-if="autoCompleteCount > 0">
          <span class="asp-auto-icon">🤖</span>
          <span>O AUGUR escolherá <strong>{{ autoCompleteCount }} agentes adicionais</strong> automaticamente, baseado na sua hipótese e nos participantes mais relevantes para o cenário.</span>
        </div>

        <!-- Footer -->
        <div class="asp-footer">
          <div class="asp-footer-info">
            <div class="asp-count-bar">
              <div class="asp-count-fill" :style="{width: Math.min(100, (totalSelecionados / cfgAgentes) * 100) + '%'}"></div>
            </div>
            <span class="asp-count-text">{{ totalSelecionados }} selecionados · {{ autoCompleteCount }} auto-complete · {{ cfgAgentes }} total</span>
          </div>
          <button class="asp-confirm" @click="confirmarAgentes()" :disabled="totalSelecionados === 0 && entityTypes.length === 0">
            Confirmar e Gerar Agentes →
          </button>
        </div>
      </div>

      <!-- Timeline -->
      <div class="timeline">
        <div v-for="(fase, idx) in fases" :key="fase.key" class="tl-item">
          <div class="tl-left">
            <div class="tl-dot"
              :class="{
                'tl-active': phase===fase.key,
                'tl-done':   faseAtual>idx || phase==='running',
                'tl-error':  (phase==='error'||phase==='aborted') && faseAtual===idx
              }"
            >
              <svg v-if="faseAtual>idx || phase==='running'" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12"><polyline points="2,6 5,9 10,3"/></svg>
              <div v-else-if="phase===fase.key && phase!=='error' && phase!=='aborted'" class="dot-spin"></div>
            </div>
            <div v-if="idx<fases.length-1" class="tl-line" :class="{ 'tl-line-done': faseAtual>idx || phase==='running' }"></div>
          </div>
          <div class="tl-content" :class="{ 'tl-content-active': phase===fase.key, 'tl-content-done': faseAtual>idx || phase==='running' }">
            <div class="tl-label">{{ fase.label }}</div>
            <div class="tl-desc">{{ fase.desc }}</div>
          </div>
        </div>
      </div>

      <!-- Erro -->
      <div v-if="phase==='error'" class="erro-card">
        <div class="erro-icon">⚠️</div>
        <div class="erro-msg">{{ erro }}</div>
        <div class="erro-actions">
          <button class="btn-ghost" @click="voltar">← Voltar ao projeto</button>
          <button class="btn-retry" @click="retry">↺ Tentar novamente</button>
        </div>
      </div>

      <!-- Cancelado -->
      <div v-if="phase==='aborted'" class="erro-card erro-aborted">
        <div class="erro-icon">🚫</div>
        <div class="erro-msg">Simulação cancelada.</div>
        <div class="erro-actions">
          <button class="btn-ghost" @click="voltar">← Voltar ao projeto</button>
          <button class="btn-retry" @click="tela='config'; abortado=false; phase='init'; progress=0">
            ↺ Configurar novamente
          </button>
        </div>
      </div>

      <!-- Info -->
      <div v-if="projectData && phase!=='error' && phase!=='aborted'" class="info-card">
        <div class="info-title">Em andamento</div>
        <div class="info-row"><span class="ik">Projeto</span><span class="iv">{{ projectData.name }}</span></div>
        <div class="info-row"><span class="ik">Agentes</span><span class="iv ac">{{ cfgAgentes }}</span></div>
        <div class="info-row"><span class="ik">Rodadas</span><span class="iv ac2">{{ cfgRodadas }}</span></div>
        <div class="info-row"><span class="ik">Materiais</span><span class="iv">{{ (projectData.files||[]).length }} arquivo(s)</span></div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
/* Config */
.config-wrap { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px; }
.config-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.config-titulo { font-size: 22px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px; letter-spacing: -.4px; }
.config-sub { font-size: 13px; color: var(--text-secondary); margin: 0; }
.config-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 28px; display: flex; flex-direction: column; gap: 24px; }

.param-block { display: flex; flex-direction: column; gap: 8px; }
.param-h { display: flex; justify-content: space-between; align-items: center; }
.param-l { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.param-v { font-size: 26px; font-weight: 800; color: var(--accent2); font-family: var(--font-mono); }
.param-bounds { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.param-desc { font-size: 12px; color: var(--text-secondary); background: var(--bg-raised); border-radius: 6px; padding: 8px 12px; }
.slider { width: 100%; accent-color: var(--accent2); cursor: pointer; }

.estimativas { display: flex; background: var(--bg-raised); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.est { flex: 1; padding: 12px 14px; }
.el { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
.ev { font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.es { width: 1px; background: var(--border); margin: 8px 0; }
.ac  { color: var(--accent); }
.ac2 { color: var(--accent2); }

.btn-iniciar { background: var(--accent); color: #000; border: none; border-radius: 12px; padding: 15px 32px; font-size: 16px; font-weight: 800; cursor: pointer; transition: all 0.2s; letter-spacing: -.2px; align-self: stretch; }
.btn-iniciar:hover { opacity: .88; transform: translateY(-2px); }

/* Pipeline */
.pipeline { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px; }

.prog-global { display: flex; align-items: center; gap: 12px; }
.prog-bar { flex: 1; height: 8px; background: var(--bg-overlay); border-radius: 999px; overflow: hidden; }
.prog-fill { height: 100%; border-radius: 999px; background: var(--accent); transition: width 0.6s ease; }
.prog-fill.prog-error  { background: var(--danger); }
.prog-fill.prog-done   { background: var(--accent); }
.prog-pct { font-size: 13px; color: var(--text-secondary); min-width: 38px; text-align: right; font-family: var(--font-mono); }

.status-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 16px; padding: 36px 32px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 10px; transition: border-color 0.4s; }
.status-card.card-error   { border-color: rgba(255,90,90,.3); }
.status-card.card-done    { border-color: rgba(0,229,195,.3); }
.status-card.card-aborted { border-color: rgba(107,107,128,.3); }

.status-icon { width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--accent-dim); color: var(--accent); margin-bottom: 6px; }
.status-icon.error, .status-icon.aborted { background: rgba(255,90,90,.12); color: var(--danger); }
.status-icon.running { background: var(--accent-dim); color: var(--accent); }
.spinner-icon { width: 32px; height: 32px; border: 3px solid var(--accent-dim); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.status-titulo { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0; }
.status-msg    { font-size: 14px; color: var(--text-secondary); margin: 0; }
.status-detalhe { font-size: 12px; color: var(--text-muted); margin: 0; font-style: italic; }

.aviso-tempo { font-size: 12px; color: #f5a623; background: rgba(245,166,35,.08); border: 1px solid rgba(245,166,35,.2); border-radius: 8px; padding: 8px 14px; margin-top: 4px; }

.btn-cancelar { background: none; border: 1px solid rgba(255,90,90,.4); color: var(--danger); border-radius: 8px; padding: 7px 18px; font-size: 12px; cursor: pointer; margin-top: 6px; transition: all 0.2s; }
.btn-cancelar:hover { background: rgba(255,90,90,.08); }

/* Timeline */
.timeline { display: flex; flex-direction: column; }
.tl-item { display: flex; gap: 14px; }
.tl-left { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.tl-dot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--bg-overlay); border: 2px solid var(--border-md); color: var(--text-muted); transition: all 0.3s; flex-shrink: 0; }
.tl-dot.tl-active { border-color: var(--accent2); background: var(--accent2); color: #fff; }
.tl-dot.tl-done   { border-color: var(--accent);  background: var(--accent);  color: #000; }
.tl-dot.tl-error  { border-color: var(--danger);  background: rgba(255,90,90,.1); color: var(--danger); }
.dot-spin { width: 12px; height: 12px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .8s linear infinite; }
.tl-line { width: 2px; flex: 1; background: var(--border-md); margin: 4px 0; min-height: 20px; transition: background 0.4s; }
.tl-line.tl-line-done { background: var(--accent); }
.tl-content { padding: 4px 0 16px; }
.tl-label { font-size: 13px; font-weight: 600; color: var(--text-muted); transition: color 0.3s; }
.tl-desc  { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.tl-content.tl-content-active .tl-label { color: var(--accent2); }
.tl-content.tl-content-done   .tl-label { color: var(--text-secondary); }

/* Erro / Cancelado */
.erro-card { background: rgba(255,90,90,.07); border: 1px solid rgba(255,90,90,.25); border-radius: 12px; padding: 20px 24px; display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
.erro-aborted { background: rgba(107,107,128,.07); border-color: rgba(107,107,128,.2); }
.erro-icon { font-size: 32px; }
.erro-msg  { font-size: 14px; color: var(--text-secondary); line-height: 1.6; }
.erro-actions { display: flex; gap: 12px; }

/* Info */
.info-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.info-title { font-size: 11px; font-weight: 600; color: var(--text-muted); padding: 10px 16px 6px; text-transform: uppercase; letter-spacing: .6px; }
.info-row { display: flex; justify-content: space-between; padding: 8px 16px; border-top: 1px solid var(--border); font-size: 13px; }
.ik { color: var(--text-muted); }
.iv { color: var(--text-primary); font-weight: 500; }

/* Global buttons */
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; transition: all .15s; }
.btn-ghost:hover { color: var(--text-primary); border-color: var(--border-md); }
.btn-retry { background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-retry:hover { opacity: .85; }

/* ═══ AGENT SELECTION ═══ */
.agent-select-panel { background:var(--bg-surface, #111118); border:1px solid rgba(255,255,255,0.08); border-radius:20px; padding:28px; margin-bottom:20px; }
.asp-header { margin-bottom:20px; }
.asp-title-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.asp-header h3 { font-size:20px; font-weight:700; color:#f0f0ff; }
.asp-header p { font-size:13px; color:#8888aa; line-height:1.6; }
.asp-counter { padding:6px 16px; border-radius:20px; font-size:13px; font-weight:700; background:rgba(0,229,195,0.08); color:#00e5c3; border:1px solid rgba(0,229,195,0.2); }
.asp-counter-full { background:rgba(0,229,195,0.15); }
.asp-section { margin-top:20px; padding-top:18px; border-top:1px solid rgba(255,255,255,0.06); }
.asp-section h4 { font-size:15px; font-weight:700; color:#f0f0ff; margin-bottom:4px; }
.asp-section-sub { font-size:12px; color:#555570; margin-bottom:12px; }

/* Detected chips */
.asp-detected { background:rgba(124,111,247,0.04); border-radius:14px; padding:18px; border-top:none; margin-top:0; }
.asp-detected-grid { display:flex; flex-wrap:wrap; gap:8px; }
.asp-chip { display:inline-flex; align-items:center; gap:6px; padding:8px 14px; border-radius:20px; border:1px solid rgba(124,111,247,0.25); background:rgba(124,111,247,0.06); cursor:pointer; transition:all .2s; }
.asp-chip:hover { border-color:rgba(124,111,247,0.5); }
.asp-chip-on { border-color:#7c6ff7; background:rgba(124,111,247,0.15); }
.asp-chip-check { width:16px; height:16px; border-radius:50%; background:rgba(124,111,247,0.2); display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; color:#7c6ff7; }
.asp-chip-on .asp-chip-check { background:#7c6ff7; color:#fff; }
.asp-chip-name { font-size:13px; font-weight:600; color:#f0f0ff; }
.asp-chip-badge { font-size:9px; font-weight:700; color:#7c6ff7; background:rgba(124,111,247,0.1); padding:2px 8px; border-radius:10px; letter-spacing:0.5px; }

/* Categories */
.asp-categories { display:flex; flex-direction:column; gap:2px; }
.asp-cat-header { display:flex; align-items:center; gap:10px; padding:12px 16px; border-radius:10px; cursor:pointer; transition:background .2s; }
.asp-cat-header:hover { background:rgba(255,255,255,0.03); }
.asp-cat-icon { font-size:20px; }
.asp-cat-label { flex:1; font-size:14px; font-weight:600; color:#f0f0ff; }
.asp-cat-count { background:var(--cat-color); color:#09090f; font-size:11px; font-weight:800; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; }
.asp-cat-arrow { font-size:18px; color:#555570; transition:transform .2s; font-weight:700; }
.asp-cat-open { transform:rotate(90deg); }

/* Agent list */
.asp-cat-agents { padding:4px 0 8px 46px; display:flex; flex-direction:column; gap:4px; }
.asp-agent { display:flex; align-items:center; justify-content:space-between; padding:10px 14px; border-radius:10px; cursor:pointer; transition:all .15s; border:1px solid transparent; }
.asp-agent:hover { background:rgba(255,255,255,0.03); border-color:rgba(255,255,255,0.06); }
.asp-agent-added { opacity:0.6; cursor:default; }
.asp-agent-left { display:flex; gap:10px; align-items:flex-start; flex:1; }
.asp-agent-dot { width:8px; height:8px; border-radius:50%; margin-top:6px; flex-shrink:0; }
.asp-agent-name { font-size:13px; font-weight:600; color:#f0f0ff; }
.asp-agent-desc { font-size:11px; color:#8888aa; margin-top:2px; line-height:1.4; }
.asp-agent-add { border:none; background:none; font-size:12px; font-weight:700; cursor:pointer; white-space:nowrap; padding:4px 10px; border-radius:6px; transition:background .2s; }
.asp-agent-add:hover { background:rgba(255,255,255,0.06); }
.asp-agent-ok { font-size:11px; color:#00e5c3; font-weight:600; }

/* Custom input */
.asp-custom-row { display:flex; gap:8px; }
.asp-input { flex:1; padding:10px 16px; border-radius:10px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); color:#f0f0ff; font-size:13px; outline:none; }
.asp-input:focus { border-color:rgba(0,229,195,0.4); }
.asp-add-btn { padding:10px 20px; border-radius:10px; border:none; background:#00e5c3; color:#09090f; font-weight:700; font-size:12px; cursor:pointer; white-space:nowrap; }

/* Selected tags */
.asp-selected-list { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
.asp-sel-tag { display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:20px; background:rgba(255,255,255,0.04); border:1px solid var(--tc); color:var(--tc); font-size:12px; font-weight:600; }
.asp-sel-x { cursor:pointer; opacity:0.6; font-size:10px; }
.asp-sel-x:hover { opacity:1; }

/* Auto-complete */
.asp-auto { display:flex; gap:12px; align-items:flex-start; padding:14px 18px; background:rgba(0,229,195,0.04); border:1px solid rgba(0,229,195,0.15); border-radius:12px; margin-top:16px; font-size:12px; color:#8888aa; line-height:1.6; }
.asp-auto strong { color:#00e5c3; }
.asp-auto-icon { font-size:20px; flex-shrink:0; }

/* Footer */
.asp-footer { display:flex; justify-content:space-between; align-items:center; margin-top:20px; padding-top:18px; border-top:1px solid rgba(255,255,255,0.06); gap:16px; }
.asp-footer-info { flex:1; }
.asp-count-bar { height:6px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden; margin-bottom:6px; }
.asp-count-fill { height:100%; background:linear-gradient(90deg, #7c6ff7, #00e5c3); border-radius:3px; transition:width .3s; }
.asp-count-text { font-size:11px; color:#555570; }
.asp-confirm { padding:14px 32px; border-radius:12px; border:none; background:linear-gradient(135deg, #00e5c3, #7c6ff7); color:#fff; font-weight:700; font-size:14px; cursor:pointer; transition:transform .2s, box-shadow .2s; white-space:nowrap; }
.asp-confirm:hover { transform:translateY(-2px); box-shadow:0 8px 25px rgba(0,229,195,0.3); }
.asp-confirm:disabled { opacity:0.4; cursor:not-allowed; transform:none; }

.asp-new-cat-header { display:flex; justify-content:space-between; align-items:center; }
.asp-toggle-cat { border:1px solid rgba(0,229,195,0.3); background:rgba(0,229,195,0.06); color:#00e5c3; font-size:12px; font-weight:600; padding:6px 14px; border-radius:8px; cursor:pointer; }
.asp-toggle-cat:hover { background:rgba(0,229,195,0.12); }
.asp-new-cat-form { margin-top:12px; }
.asp-new-cat-row { display:flex; gap:8px; align-items:center; }
.asp-cat-icon-input { width:44px; padding:10px; border-radius:10px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); color:#f0f0ff; font-size:18px; text-align:center; outline:none; }
.asp-color-input { width:40px; height:40px; border:none; border-radius:8px; cursor:pointer; background:transparent; }

@media (max-width:768px) { .asp-cat-agents { padding-left:20px; } .asp-title-row { flex-direction:column; align-items:flex-start; gap:8px; } .asp-new-cat-row { flex-wrap:wrap; } }</style>
