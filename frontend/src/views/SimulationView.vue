<script setup>
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()

// ─── Estado do pipeline ───
const phase = ref('init') // init → building_graph → creating_sim → preparing → starting → running → error
const error = ref('')
const progress = ref(0)
const statusMsg = ref('Iniciando...')
const projectData = ref(null)
const simulationId = ref(null)
const prepareTaskId = ref(null)
let pollTimer = null

// Parâmetros recebidos do wizard via query string
const maxRounds = computed(() => Number(route.query.rodadas) || 20)
const maxAgents = computed(() => Number(route.query.agentes) || 50)

const phaseLabels = {
  init: 'Inicializando',
  building_graph: 'Construindo Grafo de Conhecimento',
  creating_sim: 'Criando Simulação',
  preparing: 'Preparando Agentes',
  starting: 'Iniciando Simulação',
  running: 'Simulação Iniciada!',
  error: 'Erro'
}

const phaseLabel = computed(() => phaseLabels[phase.value] || phase.value)

// ─── Pipeline principal ───
onMounted(async () => {
  try {
    await runPipeline()
  } catch (e) {
    handleError(e)
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function runPipeline() {
  const projectId = route.params.projectId

  // 1. Buscar dados do projeto (inclui task_id do graph build)
  phase.value = 'building_graph'
  statusMsg.value = 'Verificando construção do grafo...'
  progress.value = 5

  const project = await getProject(projectId)
  projectData.value = project

  // 2. Se o grafo ainda está construindo, esperar
  if (project.status === 'graph_building' && project.graph_build_task_id) {
    statusMsg.value = 'Construindo grafo de conhecimento no Zep...'
    await waitForGraphBuild(project.graph_build_task_id, projectId)
  } else if (project.status === 'ontology_generated') {
    // Graph build pode não ter sido iniciado ainda — raro mas possível
    statusMsg.value = 'Grafo ainda não iniciado. Verifique o wizard.'
    phase.value = 'error'
    error.value = 'O build do grafo não foi iniciado. Volte ao wizard e tente novamente.'
    return
  }
  // Se já está graph_completed, prosseguir

  // Buscar projeto atualizado para pegar graph_id
  const updatedProject = await getProject(projectId)
  projectData.value = updatedProject

  if (!updatedProject.graph_id) {
    phase.value = 'error'
    error.value = 'Grafo construído mas graph_id não encontrado.'
    return
  }

  // 3. Criar simulação
  phase.value = 'creating_sim'
  statusMsg.value = 'Criando registro da simulação...'
  progress.value = 45

  const simData = await createSimulation(projectId, updatedProject.graph_id)
  simulationId.value = simData.simulation_id

  // 4. Preparar simulação (gera perfis dos agentes via LLM)
  phase.value = 'preparing'
  statusMsg.value = 'Gerando perfis dos agentes com IA...'
  progress.value = 50

  const prepareResult = await prepareSimulation(simData.simulation_id)

  if (prepareResult.already_prepared) {
    statusMsg.value = 'Agentes já preparados!'
    progress.value = 85
  } else if (prepareResult.task_id) {
    prepareTaskId.value = prepareResult.task_id
    await waitForPrepare(prepareResult.task_id, simData.simulation_id)
  }

  // 5. Iniciar simulação
  phase.value = 'starting'
  statusMsg.value = 'Lançando simulação...'
  progress.value = 90

  await startSimulation(simData.simulation_id)

  // 6. Navegar para a tela de execução
  phase.value = 'running'
  statusMsg.value = 'Simulação rodando! Redirecionando...'
  progress.value = 100

  setTimeout(() => {
    router.push(`/simulacao/${simData.simulation_id}/executar`)
  }, 1500)
}

// ─── API helpers ───

async function getProject(projectId) {
  const res = await service.get(`/api/graph/project/${projectId}`)
  return res.data || res
}

async function createSimulation(projectId, graphId) {
  const res = await service.post('/api/simulation/create', {
    project_id: projectId,
    graph_id: graphId
  })
  return res.data || res
}

async function prepareSimulation(simId) {
  const res = await service.post('/api/simulation/prepare', {
    simulation_id: simId
  })
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

// ─── Polling helpers ───

function waitForGraphBuild(taskId, projectId) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const maxWait = 600000 // 10 minutos
    const interval = 5000

    pollTimer = setInterval(async () => {
      try {
        elapsed += interval
        if (elapsed > maxWait) {
          clearInterval(pollTimer)
          reject(new Error('Timeout: construção do grafo demorou mais de 10 minutos.'))
          return
        }

        // Verificar task
        const res = await service.get(`/api/graph/task/${taskId}`)
        const task = res.data || res

        if (task.progress) {
          progress.value = 5 + Math.round((task.progress / 100) * 35) // 5% → 40%
        }
        if (task.message) {
          statusMsg.value = task.message
        }

        if (task.status === 'completed') {
          clearInterval(pollTimer)
          resolve()
        } else if (task.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error(task.error || task.message || 'Falha na construção do grafo.'))
        }
      } catch (e) {
        // Também checar se o projeto já completou (fallback)
        try {
          const proj = await getProject(projectId)
          if (proj.status === 'graph_completed') {
            clearInterval(pollTimer)
            resolve()
            return
          }
        } catch (_) { /* ignorar */ }
      }
    }, interval)
  })
}

function waitForPrepare(taskId, simId) {
  return new Promise((resolve, reject) => {
    let elapsed = 0
    const maxWait = 600000 // 10 minutos
    const interval = 5000

    pollTimer = setInterval(async () => {
      try {
        elapsed += interval
        if (elapsed > maxWait) {
          clearInterval(pollTimer)
          reject(new Error('Timeout: preparação demorou mais de 10 minutos.'))
          return
        }

        const res = await service.post('/api/simulation/prepare/status', {
          task_id: taskId,
          simulation_id: simId
        })
        const data = res.data || res

        if (data.progress) {
          progress.value = 50 + Math.round((data.progress / 100) * 35) // 50% → 85%
        }
        if (data.message) {
          statusMsg.value = data.message
        }

        if (data.status === 'ready' || data.status === 'completed' || data.already_prepared) {
          clearInterval(pollTimer)
          resolve()
        } else if (data.status === 'failed') {
          clearInterval(pollTimer)
          reject(new Error(data.message || 'Falha na preparação da simulação.'))
        }
      } catch (e) {
        console.warn('Erro ao verificar prepare status:', e)
      }
    }, interval)
  })
}

// ─── Error handling ───

function handleError(e) {
  console.error('Pipeline error:', e)
  phase.value = 'error'
  error.value = e?.response?.data?.error || e?.message || 'Erro inesperado no pipeline de simulação.'
}

function retry() {
  error.value = ''
  phase.value = 'init'
  progress.value = 0
  runPipeline().catch(handleError)
}
</script>

<template>
  <AppShell title="Preparando Simulação">
    <div class="pipeline-container">
      <!-- Progress visual -->
      <div class="progress-wrapper">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }" :class="{ error: phase === 'error' }"></div>
        </div>
        <span class="progress-pct">{{ progress }}%</span>
      </div>

      <!-- Phase indicator -->
      <div class="phase-card">
        <div class="phase-icon" :class="phase">
          <svg v-if="phase === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <svg v-else-if="phase === 'running'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <div v-else class="spinner"></div>
        </div>

        <h2>{{ phaseLabel }}</h2>
        <p class="status-msg">{{ statusMsg }}</p>
      </div>

      <!-- Steps timeline -->
      <div class="steps">
        <div class="step" :class="{ active: phase === 'building_graph', done: ['creating_sim','preparing','starting','running'].includes(phase) }">
          <div class="step-dot"></div>
          <span>Construir Grafo</span>
        </div>
        <div class="step-line"></div>
        <div class="step" :class="{ active: phase === 'creating_sim', done: ['preparing','starting','running'].includes(phase) }">
          <div class="step-dot"></div>
          <span>Criar Simulação</span>
        </div>
        <div class="step-line"></div>
        <div class="step" :class="{ active: phase === 'preparing', done: ['starting','running'].includes(phase) }">
          <div class="step-dot"></div>
          <span>Preparar Agentes</span>
        </div>
        <div class="step-line"></div>
        <div class="step" :class="{ active: phase === 'starting', done: ['running'].includes(phase) }">
          <div class="step-dot"></div>
          <span>Iniciar</span>
        </div>
      </div>

      <!-- Error state -->
      <div v-if="phase === 'error'" class="error-box">
        <p>{{ error }}</p>
        <div class="error-actions">
          <AugurButton variant="ghost" @click="router.push('/novo')">← Voltar ao Wizard</AugurButton>
          <AugurButton @click="retry">Tentar Novamente</AugurButton>
        </div>
      </div>

      <!-- Project info -->
      <div v-if="projectData" class="info-card">
        <h4>Projeto</h4>
        <div class="info-row"><span>Nome</span><span>{{ projectData.name }}</span></div>
        <div class="info-row"><span>Arquivos</span><span>{{ projectData.files?.length || 0 }}</span></div>
        <div class="info-row"><span>Agentes</span><span class="accent">{{ maxAgents }}</span></div>
        <div class="info-row"><span>Rodadas</span><span class="accent2">{{ maxRounds }}</span></div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.pipeline-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 32px 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-overlay);
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 999px;
  transition: width 0.5s ease;
}
.progress-fill.error { background: var(--danger); }
.progress-pct {
  font-size: 13px;
  color: var(--text-secondary);
  min-width: 40px;
  text-align: right;
}

.phase-card {
  background: var(--bg-raised);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: 32px;
  text-align: center;
}
.phase-card h2 {
  margin: 16px 0 8px;
  font-size: 20px;
}
.status-msg {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.phase-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent-dim);
  color: var(--accent);
}
.phase-icon.error { background: rgba(255,90,90,0.12); color: var(--danger); }
.phase-icon.running { background: var(--accent-dim); color: var(--accent); }
.phase-icon svg { width: 28px; height: 28px; }

.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--accent-dim);
  border-top: 3px solid var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Steps timeline */
.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
}
.step span {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}
.step-dot {
  width: 14px; height: 14px;
  border-radius: 50%;
  background: var(--bg-overlay);
  border: 2px solid var(--border-md);
  transition: all var(--t-mid);
}
.step.active .step-dot { border-color: var(--accent); background: var(--accent); box-shadow: 0 0 10px rgba(0,229,195,0.4); }
.step.active span { color: var(--accent); }
.step.done .step-dot { border-color: var(--accent); background: var(--accent); }
.step.done span { color: var(--text-secondary); }
.step-line {
  width: 40px; height: 2px;
  background: var(--border-md);
  margin: 0 4px;
  margin-bottom: 20px;
}

/* Error */
.error-box {
  background: rgba(255,90,90,0.08);
  border: 1px solid rgba(255,90,90,0.25);
  border-radius: var(--r-md);
  padding: 16px;
}
.error-box p { color: var(--danger); font-size: 14px; margin: 0 0 12px; }
.error-actions { display: flex; gap: 12px; justify-content: flex-end; }

/* Info card */
.info-card {
  background: var(--bg-raised);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
  padding: 16px;
}
.info-card h4 { margin: 0 0 12px; font-size: 14px; color: var(--text-secondary); }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; border-bottom: 1px solid var(--border); }
.info-row:last-child { border-bottom: none; }
.accent { color: var(--accent); font-weight: 600; }
.accent2 { color: var(--accent2); font-weight: 600; }
</style>
