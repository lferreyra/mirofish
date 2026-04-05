<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()

const phase = ref('init')
const error = ref('')
const progress = ref(0)
const statusMsg = ref('Iniciando...')
const detalhe = ref('')
const projectData = ref(null)
const simulationId = ref(null)
let pollTimer = null

const maxRounds = computed(() => Number(route.query.rodadas) || 20)
const maxAgents = computed(() => Number(route.query.agentes) || 50)
const origemNovoProjeto = computed(() => route.query.origem === 'novo_projeto')

const fases = [
  { key: 'building_graph', label: 'Construindo Grafo', desc: 'Analisando documentos e criando rede de conhecimento' },
  { key: 'creating_sim',   label: 'Criando Simulação', desc: 'Configurando o ambiente de simulação' },
  { key: 'preparing',      label: 'Gerando Agentes',   desc: 'Criando perfis únicos para cada agente com IA' },
  { key: 'starting',       label: 'Iniciando',         desc: 'Lançando a simulação multiagente' },
]

const faseAtual = computed(() => fases.findIndex(f => f.key === phase.value))
const phaseLabel = computed(() => {
  const f = fases.find(f => f.key === phase.value)
  if (phase.value === 'running') return 'Simulação Iniciada! ✅'
  if (phase.value === 'error') return 'Erro no pipeline'
  return f?.label || 'Inicializando...'
})

function traduzir(msg) {
  if (!msg) return ''
  if (/[\u4e00-\u9fff]/.test(msg)) return 'Processando...'
  const map = [
    ['building', 'Construindo grafo de conhecimento...'],
    ['entity', 'Extraindo entidades e relacionamentos...'],
    ['chunk', 'Processando blocos de texto...'],
    ['batch', 'Processando lote de dados...'],
    ['sending', 'Enviando dados para o grafo...'],
    ['graph', 'Atualizando grafo de conhecimento...'],
    ['completed', 'Concluído com sucesso!'],
    ['failed', 'Falhou'],
    ['preparing', 'Preparando agentes de IA...'],
    ['generating', 'Gerando perfis dos agentes...'],
    ['profile', 'Criando perfil do agente...'],
    ['ready', 'Tudo pronto!'],
    ['starting', 'Iniciando simulação...'],
    ['processing', 'Processando...'],
    ['analyzing', 'Analisando documentos...'],
    ['extracting', 'Extraindo informações...'],
  ]
  const lower = msg.toLowerCase()
  for (const [k, v] of map) {
    if (lower.includes(k)) return v
  }
  return msg
}

onMounted(async () => {
  try { await runPipeline() }
  catch (e) { handleError(e) }
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

async function runPipeline() {
  const projectId = route.params.projectId

  // 1. Verificar projeto e aguardar grafo
  phase.value = 'building_graph'
  statusMsg.value = 'Verificando construção do grafo...'
  detalhe.value = 'Isso pode levar alguns minutos dependendo do tamanho dos documentos.'
  progress.value = 5

  const project = await getProject(projectId)
  projectData.value = project

  if (project.status === 'graph_building' && project.graph_build_task_id) {
    statusMsg.value = 'Construindo rede de conhecimento...'
    await waitForGraphBuild(project.graph_build_task_id, projectId)
  } else if (project.status === 'ontology_generated') {
    phase.value = 'error'
    error.value = 'O build do grafo não foi iniciado. Volte e crie o projeto novamente.'
    return
  }

  // Projeto atualizado com graph_id
  const updated = await getProject(projectId)
  projectData.value = updated
  if (!updated.graph_id) {
    phase.value = 'error'
    error.value = 'Grafo construído mas ID não encontrado. Tente novamente.'
    return
  }

  // 2. Criar simulação
  phase.value = 'creating_sim'
  statusMsg.value = 'Criando registro da simulação...'
  detalhe.value = ''
  progress.value = 45

  const simData = await createSimulation(projectId, updated.graph_id)
  simulationId.value = simData.simulation_id

  // 3. Preparar agentes
  phase.value = 'preparing'
  statusMsg.value = 'Gerando perfis dos agentes com IA...'
  detalhe.value = 'Cada agente recebe uma personalidade, histórico e comportamento únicos.'
  progress.value = 50

  const prepResult = await prepareSimulation(simData.simulation_id)
  if (prepResult.already_prepared) {
    statusMsg.value = 'Agentes já estavam prontos!'
    progress.value = 85
  } else if (prepResult.task_id) {
    await waitForPrepare(prepResult.task_id, simData.simulation_id)
  }

  // 4. Iniciar
  phase.value = 'starting'
  statusMsg.value = 'Lançando simulação...'
  detalhe.value = 'Os agentes estão sendo ativados.'
  progress.value = 90

  await startSimulation(simData.simulation_id)

  // 5. Pronto
  phase.value = 'running'
  statusMsg.value = 'Simulação iniciada com sucesso!'
  detalhe.value = 'Redirecionando para o monitoramento ao vivo...'
  progress.value = 100

  setTimeout(() => {
    router.push(`/simulacao/${simData.simulation_id}/executar`)
  }, 1800)
}

async function getProject(id) {
  const res = await service.get(`/api/graph/project/${id}`)
  return res.data || res
}

async function createSimulation(projectId, graphId) {
  const res = await service.post('/api/simulation/create', { project_id: projectId, graph_id: graphId })
  return res.data || res
}

async function prepareSimulation(simId) {
  const res = await service.post('/api/simulation/prepare', { simulation_id: simId })
  return res.data || res
}

async function startSimulation(simId) {
  const res = await service.post('/api/simulation/start', {
    simulation_id: simId,
    platform: 'parallel',
    max_rounds: maxRounds.value
  })
  return res.data || res
}

function waitForGraphBuild(taskId, projectId) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const maxWait = 900000 // 15 min
    const interval = 5000

    pollTimer = setInterval(async () => {
      elapsed += interval
      if (elapsed > maxWait) {
        clearInterval(pollTimer)
        reject(new Error('Timeout: construção do grafo demorou mais de 15 minutos.'))
        return
      }
      try {
        const res = await service.get(`/api/graph/task/${taskId}`)
        const task = res.data || res
        if (task.progress) progress.value = 5 + Math.round((task.progress / 100) * 35)
        if (task.message) { statusMsg.value = traduzir(task.message); detalhe.value = '' }
        if (task.status === 'completed') { clearInterval(pollTimer); resolve() }
        else if (task.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error(traduzir(task.error || task.message) || 'Falha na construção do grafo.'))
        }
      } catch {
        try {
          const proj = await getProject(projectId)
          if (proj.status === 'graph_completed') { clearInterval(pollTimer); resolve() }
        } catch { /* ignorar */ }
      }
    }, interval)
  })
}

function waitForPrepare(taskId, simId) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const maxWait = 900000
    const interval = 5000

    pollTimer = setInterval(async () => {
      elapsed += interval
      if (elapsed > maxWait) {
        clearInterval(pollTimer)
        reject(new Error('Timeout: preparação dos agentes demorou mais de 15 minutos.'))
        return
      }
      try {
        const res = await service.post('/api/simulation/prepare/status', { task_id: taskId, simulation_id: simId })
        const data = res.data || res
        if (data.progress) progress.value = 50 + Math.round((data.progress / 100) * 35)
        if (data.message) { statusMsg.value = traduzir(data.message); detalhe.value = '' }
        if (data.status === 'ready' || data.status === 'completed' || data.already_prepared) {
          clearInterval(pollTimer)
          progress.value = 85
          resolve()
        } else if (data.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error(traduzir(data.message) || 'Falha na preparação dos agentes.'))
        }
      } catch (e) { console.warn('prepare status error:', e) }
    }, interval)
  })
}

function handleError(e) {
  phase.value = 'error'
  error.value = e?.response?.data?.error || e?.message || 'Erro inesperado. Tente novamente.'
}

function retry() {
  error.value = ''
  phase.value = 'init'
  progress.value = 0
  statusMsg.value = 'Reiniciando...'
  runPipeline().catch(handleError)
}

function voltar() {
  if (projectData.value) {
    router.push(`/projeto/${route.params.projectId}`)
  } else {
    router.push('/')
  }
}
</script>

<template>
  <AppShell title="Preparando Simulação">
    <div class="pipeline">

      <!-- Barra de progresso global -->
      <div class="prog-global">
        <div class="prog-bar">
          <div
            class="prog-fill"
            :class="{ 'prog-error': phase === 'error', 'prog-done': phase === 'running' }"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <span class="prog-pct">{{ progress }}%</span>
      </div>

      <!-- Card central de status -->
      <div class="status-card" :class="{ 'card-error': phase === 'error', 'card-done': phase === 'running' }">
        <!-- Ícone animado -->
        <div class="status-icon" :class="phase">
          <svg v-if="phase === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="30" height="30">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <svg v-else-if="phase === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="30" height="30">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <div v-else class="spinner-icon"></div>
        </div>

        <h2 class="status-titulo">{{ phaseLabel }}</h2>
        <p class="status-msg">{{ statusMsg }}</p>
        <p v-if="detalhe" class="status-detalhe">{{ detalhe }}</p>

        <!-- Tempo estimado quando construindo grafo -->
        <div v-if="phase === 'building_graph'" class="aviso-tempo">
          ⏱ Este processo pode levar entre 2 e 15 minutos. Não feche esta aba.
        </div>
        <div v-if="phase === 'preparing'" class="aviso-tempo">
          ⏱ Geração dos perfis pode levar alguns minutos. Aguarde.
        </div>
      </div>

      <!-- Timeline de fases -->
      <div class="timeline">
        <div v-for="(fase, idx) in fases" :key="fase.key" class="tl-item">
          <!-- Linha conectora -->
          <div class="tl-left">
            <div
              class="tl-dot"
              :class="{
                'tl-active': phase === fase.key,
                'tl-done': faseAtual > idx || phase === 'running',
                'tl-error': phase === 'error' && faseAtual === idx
              }"
            >
              <svg v-if="faseAtual > idx || phase === 'running'" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12">
                <polyline points="2,6 5,9 10,3"/>
              </svg>
              <div v-else-if="phase === fase.key && phase !== 'error'" class="dot-spin"></div>
            </div>
            <div v-if="idx < fases.length - 1" class="tl-line" :class="{ 'tl-line-done': faseAtual > idx || phase === 'running' }"></div>
          </div>
          <!-- Texto da fase -->
          <div class="tl-content" :class="{ 'tl-content-active': phase === fase.key, 'tl-content-done': faseAtual > idx || phase === 'running' }">
            <div class="tl-label">{{ fase.label }}</div>
            <div class="tl-desc">{{ fase.desc }}</div>
          </div>
        </div>
      </div>

      <!-- Erro -->
      <div v-if="phase === 'error'" class="error-card">
        <div class="error-icon">⚠️</div>
        <div class="error-msg">{{ error }}</div>
        <div class="error-actions">
          <button class="btn-ghost" @click="voltar">← Voltar ao projeto</button>
          <button class="btn-retry" @click="retry">↺ Tentar novamente</button>
        </div>
      </div>

      <!-- Info do projeto -->
      <div v-if="projectData" class="info-card">
        <div class="info-title">Projeto em processamento</div>
        <div class="info-row">
          <span class="info-key">Nome</span>
          <span class="info-val">{{ projectData.name }}</span>
        </div>
        <div class="info-row">
          <span class="info-key">Materiais</span>
          <span class="info-val">{{ (projectData.files || []).length }} arquivo(s)</span>
        </div>
        <div v-if="maxAgents > 50 || maxRounds > 20">
          <div class="info-row">
            <span class="info-key">Agentes</span>
            <span class="info-val accent">{{ maxAgents }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">Rodadas</span>
            <span class="info-val accent2">{{ maxRounds }}</span>
          </div>
        </div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
.pipeline { max-width: 580px; margin: 0 auto; padding: 8px 0 60px; display: flex; flex-direction: column; gap: 20px; }

/* Progresso global */
.prog-global { display: flex; align-items: center; gap: 12px; }
.prog-bar { flex: 1; height: 8px; background: var(--bg-overlay); border-radius: 999px; overflow: hidden; }
.prog-fill { height: 100%; border-radius: 999px; background: var(--accent); transition: width 0.6s ease; }
.prog-fill.prog-error { background: var(--danger); }
.prog-fill.prog-done { background: var(--accent); }
.prog-pct { font-size: 13px; color: var(--text-secondary); min-width: 38px; text-align: right; font-family: var(--font-mono); }

/* Status card */
.status-card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 36px 32px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  transition: border-color 0.4s;
}
.status-card.card-error { border-color: rgba(255,90,90,0.3); }
.status-card.card-done { border-color: rgba(0,229,195,0.3); }

.status-icon {
  width: 64px; height: 64px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-dim); color: var(--accent);
  margin-bottom: 6px;
}
.status-icon.error { background: rgba(255,90,90,0.12); color: var(--danger); }
.status-icon.running { background: var(--accent-dim); color: var(--accent); }

.spinner-icon {
  width: 32px; height: 32px;
  border: 3px solid var(--accent-dim);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.status-titulo { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0; }
.status-msg { font-size: 14px; color: var(--text-secondary); margin: 0; }
.status-detalhe { font-size: 12px; color: var(--text-muted); margin: 0; font-style: italic; }

.aviso-tempo {
  font-size: 12px; color: #f5a623;
  background: rgba(245,166,35,0.08); border: 1px solid rgba(245,166,35,0.2);
  border-radius: 8px; padding: 8px 14px; margin-top: 4px;
}

/* Timeline */
.timeline { display: flex; flex-direction: column; gap: 0; }
.tl-item { display: flex; gap: 14px; }
.tl-left { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.tl-dot {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-overlay); border: 2px solid var(--border-md);
  color: var(--text-muted); transition: all 0.3s; flex-shrink: 0;
}
.tl-dot.tl-active { border-color: var(--accent2); background: var(--accent2); color: #fff; }
.tl-dot.tl-done { border-color: var(--accent); background: var(--accent); color: #000; }
.tl-dot.tl-error { border-color: var(--danger); background: rgba(255,90,90,0.1); color: var(--danger); }
.dot-spin { width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }
.tl-line { width: 2px; flex: 1; background: var(--border-md); margin: 4px 0; min-height: 20px; transition: background 0.4s; }
.tl-line.tl-line-done { background: var(--accent); }

.tl-content { padding: 4px 0 16px; }
.tl-label { font-size: 13px; font-weight: 600; color: var(--text-muted); transition: color 0.3s; }
.tl-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.tl-content.tl-content-active .tl-label { color: var(--accent2); }
.tl-content.tl-content-done .tl-label { color: var(--text-secondary); }

/* Erro */
.error-card {
  background: rgba(255,90,90,0.07); border: 1px solid rgba(255,90,90,0.25);
  border-radius: 12px; padding: 20px 24px;
  display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center;
}
.error-icon { font-size: 32px; }
.error-msg { font-size: 14px; color: var(--danger); line-height: 1.6; }
.error-actions { display: flex; gap: 12px; }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; transition: all 0.15s; }
.btn-ghost:hover { color: var(--text-primary); border-color: var(--border-md); }
.btn-retry { background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-retry:hover { opacity: 0.85; }

/* Info card */
.info-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.info-title { font-size: 11px; font-weight: 600; color: var(--text-muted); padding: 10px 16px 6px; text-transform: uppercase; letter-spacing: 0.6px; }
.info-row { display: flex; justify-content: space-between; padding: 8px 16px; border-top: 1px solid var(--border); font-size: 13px; }
.info-key { color: var(--text-muted); }
.info-val { color: var(--text-primary); font-weight: 500; }
.accent { color: var(--accent); }
.accent2 { color: var(--accent2); }
</style>
