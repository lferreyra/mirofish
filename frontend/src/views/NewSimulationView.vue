<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import AugurProgress from '../components/ui/AugurProgress.vue'
import AgentCard from '../components/simulation/AgentCard.vue'
import { usePolling } from '../composables/usePolling'

const router = useRouter()
const step = ref(1)
const file = ref(null)
const projectName = ref('')
const objective = ref('')
const cenario = ref('')
const hipotese = ref('')
const params = ref({ agents: 100, rounds: 60, hours: 72, twitter: true, reddit: true })
const graphTaskId = ref('')
const graphProgress = ref(0)
const entities = ref([])
const prepareTaskId = ref('')
const agents = ref([])
const simulationId = ref('')

const steps = ['Documento','Grafo','Parâmetros','Agentes','Confirmar']

const upload = async () => {
  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('project_name', projectName.value)
  const response = await service.post('/api/graph/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  const data = response.data || response
  graphTaskId.value = data.task_id
  step.value = 2
  graphPoll.start()
}

const pollGraph = async () => {
  if (!graphTaskId.value) return
  const response = await service.get(`/api/graph/status/${graphTaskId.value}`)
  const data = response.data || response
  graphProgress.value = data.progress || 0
  if (data.status === 'completed') {
    entities.value = data.entities || []
    graphPoll.stop()
  }
}
const graphPoll = usePolling(pollGraph, 3000)

const prepareAgents = async () => {
  const response = await service.post('/api/simulation/prepare', {
    project_name: projectName.value,
    objective: objective.value,
    agent_count: params.value.agents,
    max_rounds: params.value.rounds,
    hours: params.value.hours,
    enable_twitter: params.value.twitter,
    enable_reddit: params.value.reddit
  })
  const data = response.data || response
  prepareTaskId.value = data.task_id
  preparePoll.start()
}

const pollPrepare = async () => {
  if (!prepareTaskId.value) return
  const response = await service.post('/api/simulation/prepare/status', { task_id: prepareTaskId.value })
  const data = response.data || response
  agents.value = data.agents || []
  simulationId.value = data.simulation_id || simulationId.value
  if (data.status === 'completed') {
    preparePoll.stop()
    step.value = 5
  }
}
const preparePoll = usePolling(pollPrepare, 3000)

const startSimulation = async () => {
  const response = await service.post('/api/simulation/start', { simulation_id: simulationId.value })
  const data = response.data || response
  const projectId = data.project_id || data.simulation_id || simulationId.value
  router.push(`/simulacao/${projectId}?agentes=${agentes.value}&rodadas=${rodadas.value}`)
}

const canUpload = computed(() => file.value && projectName.value.trim())
const agentes = computed(() => params.value.agents)
const rodadas = computed(() => params.value.rounds)

function selecionarExemplo(ex) {
  const limpo = ex.replace(/['''"""]/g, '')
  cenario.value = limpo
  hipotese.value = limpo
  titulo.value = limpo.slice(0, 60)
}
</script>
<template>
  <AppShell title="Nova Simulação">
    <section class="wizard">
      <ol>
        <li v-for="(label, idx) in steps" :key="label" :class="{ active: step === idx + 1, done: step > idx + 1 }">{{ idx + 1 }}. {{ label }}</li>
      </ol>

      <div v-if="step===1" class="panel">
        <h3>Documento</h3>
        <input type="text" v-model="projectName" placeholder="Nome do projeto" />
        <input type="file" @change="file = $event.target.files?.[0]" />
        <AugurButton :disabled="!canUpload" @click="upload">Construir Grafo →</AugurButton>
      </div>

      <div v-else-if="step===2" class="panel">
        <h3>Construindo grafo</h3>
        <AugurProgress :value="graphProgress" :height="8" />
        <p>{{ graphProgress }}%</p>
        <div class="tags"><span v-for="entity in entities" :key="entity">{{ entity }}</span></div>
        <AugurButton v-if="graphProgress===100" @click="step=3">Configurar Simulação →</AugurButton>
      </div>

      <div v-else-if="step===3" class="panel">
        <h3>Parâmetros</h3>
        <textarea v-model="objective" placeholder="Objetivo da simulação" rows="4" />
        <label>Agentes {{ params.agents }}<input type="range" min="10" max="500" v-model.number="params.agents" /></label>
        <label>Rodadas {{ params.rounds }}<input type="range" min="5" max="200" v-model.number="params.rounds" /></label>
        <label>Horas {{ params.hours }}<input type="range" min="6" max="168" v-model.number="params.hours" /></label>
        <label><input type="checkbox" v-model="params.twitter" /> Twitter</label>
        <label><input type="checkbox" v-model="params.reddit" /> Reddit</label>
        <AugurButton @click="step=4">Revisar Agentes →</AugurButton>
      </div>

      <div v-else-if="step===4" class="panel">
        <h3>Prévia de agentes</h3>
        <AugurButton @click="prepareAgents">Preparar agentes</AugurButton>
        <div class="agent-grid"><AgentCard v-for="(agent, idx) in agents.slice(0,12)" :key="idx" :agent="agent" /></div>
      </div>

      <div v-else class="panel">
        <h3>Confirmar e iniciar</h3>
        <p><strong>Projeto:</strong> {{ projectName }}</p>
        <p><strong>Objetivo:</strong> {{ objective }}</p>
        <p><strong>Configuração:</strong> {{ params.agents }} agentes · {{ params.rounds }} rodadas · {{ params.hours }} horas</p>
        <AugurButton @click="startSimulation">🚀 Iniciar Simulação</AugurButton>
      </div>
    </section>
  </AppShell>
</template>
<style scoped>
.wizard{max-width:760px;margin:0 auto;display:grid;gap:14px}
ol{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;padding:0;list-style:none}
li{padding:8px;border-radius:var(--r-sm);background:var(--bg-surface);color:var(--text-muted);font-size:12px;text-align:center}
li.active{background:var(--accent-dim);color:var(--accent)}
li.done{color:var(--text-primary)}
.panel{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px;display:grid;gap:10px}
input,textarea{background:var(--bg-overlay);border:1px solid var(--border-md);border-radius:var(--r-sm);color:var(--text-primary);padding:10px}
.tags{display:flex;gap:8px;flex-wrap:wrap}.tags span{padding:4px 8px;background:var(--bg-overlay);border-radius:999px;font-size:12px}
.agent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
</style>
