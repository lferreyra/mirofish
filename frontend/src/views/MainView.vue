<template>
  <div class="main-view" :class="{ 'is-private-mode': isPrivateMode }">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MIROFISH</div>
        <div v-if="isPrivateMode" class="mode-badge">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          {{ t('private.modeBadge') }}
        </div>
      </div>

      <div class="header-center" v-if="!isPrivateMode">
        <div class="view-switcher">
          <button
            v-for="mode in ['graph', 'split', 'workbench']"
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: $t('main.layoutGraph'), split: $t('main.layoutSplit'), workbench: $t('main.layoutWorkbench') }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <LanguageSwitcher />
        <div class="step-divider"></div>
        <div class="workflow-step">
          <span class="step-num">Step {{ currentStep }}/{{ currentStepNames.length }}</span>
          <span class="step-name">{{ currentStepNames[currentStep - 1] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- ══════════════════════════════════════════════════════════
         MODE PUBLIC — Graph + Step Panel
    ══════════════════════════════════════════════════════════ -->
    <main v-if="!isPrivateMode" class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="currentPhase"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step Components -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <!-- Step 1: 图谱构建 -->
        <Step1GraphBuild
          v-if="currentStep === 1"
          mode="public"
          :currentPhase="currentPhase"
          :projectData="projectData"
          :ontologyProgress="ontologyProgress"
          :buildProgress="buildProgress"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @next-step="handleNextStep"
        />
        <!-- Step 2: 环境搭建 -->
        <Step2EnvSetup
          v-else-if="currentStep === 2"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
        />
      </div>
    </main>

    <!-- ══════════════════════════════════════════════════════════
         MODE PRIVATE — Bifurcation complète
    ══════════════════════════════════════════════════════════ -->
    <template v-else>
      <!-- Step breadcrumb (private) -->
      <div class="steps-bar" v-if="currentStep >= 2">
        <div
          v-for="(name, idx) in privateBreadcrumb"
          :key="idx"
          class="step-node"
          :class="{
            'is-active': currentStep === idx + 2,
            'is-done': currentStep > idx + 2,
          }"
          @click="currentStep > idx + 2 ? goToPrivateStep(idx + 2) : null"
        >
          <div class="step-circle">
            <svg v-if="currentStep > idx + 2" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <span class="step-node-name">{{ name }}</span>
          <div v-if="idx < privateBreadcrumb.length - 1" class="step-connector" :class="{ 'is-done': currentStep > idx + 2 }"></div>
        </div>
      </div>

      <!-- Error banner (private) -->
      <div v-if="privateError" class="error-banner">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        {{ privateError }}
        <button class="error-close" @click="privateError = null">×</button>
      </div>

      <!-- Step 1 — Graph build (commun, mode=private) -->
      <main v-if="currentStep === 1" class="content-area split-view">
        <div class="panel-wrapper left" style="width:50%;">
          <GraphPanel
            :graphData="graphData"
            :loading="graphLoading"
            :currentPhase="currentPhase"
            @refresh="refreshGraph"
            @toggle-maximize="toggleMaximize('graph')"
          />
        </div>
        <div class="panel-wrapper right" style="width:50%;">
          <Step1GraphBuild
            mode="private"
            :currentPhase="currentPhase"
            :projectData="projectData"
            :ontologyProgress="ontologyProgress"
            :buildProgress="buildProgress"
            :graphData="graphData"
            :systemLogs="systemLogs"
            @next-step="handleNextStep"
          />
        </div>
      </main>

      <!-- Step 2 — Private Requirement (Decision form + Prepare results) -->
      <main v-else-if="currentStep === 2" class="content-area private-area">
        <div v-if="!privatePrepareReady">
          <Step2PrivateDecision
            :form="privateForm"
            :agentCounts="privateAgentCounts"
            :projectId="currentProjectId"
            :projectData="projectData"
            @prepare="runPrivatePrepare"
          />
        </div>

        <div v-else class="centered-panel">
          <div v-if="privateIsLoading" class="loading-block">
            <div class="loading-ring"></div>
            <p class="loading-label">Generating relational profiles and behavioural parameters…</p>
            <p class="loading-hint">This may take a few seconds per agent. The LLM is building the simulation config.</p>
          </div>

          <div v-else-if="privatePrepareResult" class="prepare-results">
            <div class="result-badge result-badge--ok">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Simulation ready
            </div>

            <div class="result-stats">
              <div class="stat-card">
                <span class="stat-value mono">{{ privatePrepareResult.agent_count }}</span>
                <span class="stat-label">Agents generated</span>
              </div>
              <div class="stat-card">
                <span class="stat-value mono">{{ privateForm.horizonDays }}d</span>
                <span class="stat-label">Temporal horizon</span>
              </div>
              <div class="stat-card">
                <span class="stat-value mono">{{ privateForm.relationalTypes.length }}</span>
                <span class="stat-label">Relation types</span>
              </div>
            </div>

            <div class="relation-tags">
              <span
                v-for="t in privateForm.relationalTypes"
                :key="t"
                class="relation-tag"
              >{{ t }}</span>
            </div>

            <div class="sim-id-block">
              <span class="sim-id-label">SIM ID</span>
              <span class="sim-id-value mono">{{ privateSimId }}</span>
            </div>

            <div class="result-actions">
              <button class="btn-secondary" @click="privatePrepareReady = false; privatePrepareResult = null">← Back</button>
              <button class="btn-primary" @click="runPrivateStart">
                Launch Simulation
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </main>

      <!-- Step 3 — Private Sim Running -->
      <main v-else-if="currentStep === 3" class="content-area private-area">
        <Step3PrivateSim
          :simStatus="privateSimStatus"
          :recentActions="privateRecentActions"
          @stop="handlePrivateStop"
          @report="runPrivateReport"
        />
      </main>

      <!-- Step 4 — Private Report -->
      <main v-else-if="currentStep === 4" class="content-area private-area">
        <Step4PrivateReport
          :reportResult="privateReportResult"
          :isLoading="privateIsLoading"
          :reportProgress="privateReportProgress"
          :simId="privateSimId"
          @retry="runPrivateReport"
          @next="goToPrivateStep(5)"
        />
      </main>

      <!-- Step 5 — Private Interaction -->
      <main v-else-if="currentStep === 5" class="content-area private-area">
        <Step5PrivateInteraction
          :simId="privateSimId"
          :chatAgents="privateChatAgents"
        />
      </main>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { useI18n } from 'vue-i18n'
import GraphPanel from '../components/GraphPanel.vue'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import Step2PrivateDecision from '../components/private/Step2PrivateDecision.vue'
import Step3PrivateSim from '../components/private/Step3PrivateSim.vue'
import Step4PrivateReport from '../components/private/Step4PrivateReport.vue'
import Step5PrivateInteraction from '../components/private/Step5PrivateInteraction.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { generateOntology, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getReport } from '../api/report.js'
import {
  preparePrivateSimulation,
  startPrivateSimulation,
  getPrivateStatus,
  stopPrivateSimulation,
  getPrivateActions,
  generatePrivateReport,
  getPrivateReportStatus,
} from '../api/private.js'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'
import { RELATIONAL_TYPE_LABELS } from '../constants/private.js'
import { buildRequirement } from '../utils/private.js'

const route = useRoute()
const router = useRouter()
const { t, tm } = useI18n()

// ── Mode detection ─────────────────────────────────────────────────────────
const isPrivateMode = computed(() => route.query.mode === 'private')

// ── Layout State ──────────────────────────────────────────────────────────
const viewMode = ref('split')

// ── Step State ────────────────────────────────────────────────────────────
const currentStep = ref(1)
const publicStepNames = computed(() => tm('public.stepNames'))
const privateStepNames = computed(() => tm('private.stepNames'))
const privateBreadcrumb = computed(() => privateStepNames.value.slice(1))
const currentStepNames = computed(() => isPrivateMode.value ? privateStepNames.value : publicStepNames.value)
const stepNames = publicStepNames

// ── Data State (commun Step 1) ────────────────────────────────────────────
const currentProjectId = ref(route.params.projectId)
const loading = ref(false)
const graphLoading = ref(false)
const error = ref('')
const projectData = ref(null)
const graphData = ref(null)
const currentPhase = ref(-1)
const ontologyProgress = ref(null)
const buildProgress = ref(null)
const systemLogs = ref([])

// Public polling timers
let pollTimer = null
let graphPollTimer = null

// ── Private State ─────────────────────────────────────────────────────────
const privateSimId = ref(null)
const privateSimStatus = ref(null)
const privatePrepareResult = ref(null)
const privatePrepareReady = ref(false)
const privateReportResult = ref(null)
const privateIsLoading = ref(false)
const privateError = ref(null)
const privateReportProgress = ref('')
const privateRecentActions = ref([])
const privateChatAgents = ref([])

const privateForm = reactive({
  decisionMakerName: '',
  decisionMakerRole: '',
  decisionMakerCompany: '',
  decisionText: '',
  decisionContext: '',
  relationalTypes: ['ouvrier_production', 'technicien', 'commercial', 'manager', 'codir'],
  horizonDays: 3,
  questionsToMeasure: '',
})
const privateAgentCounts = reactive({})

// Private polling timers
let privatePollingTimer = null
let privateReportPollingTimer = null

// ── Computed Layout Styles ────────────────────────────────────────────────
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// ── Status Computed ───────────────────────────────────────────────────────
const statusClass = computed(() => {
  if (isPrivateMode.value) {
    const s = privateSimStatus.value?.runner_status
    if (s === 'running') return 'processing'
    if (s === 'completed') return 'completed'
    if (s === 'failed') return 'error'
    if (privateIsLoading.value) return 'processing'
    if (privateError.value || error.value) return 'error'
    if (currentPhase.value >= 2) return 'completed'
    return 'processing'
  }
  if (error.value) return 'error'
  if (currentPhase.value >= 2) return 'completed'
  return 'processing'
})

const statusText = computed(() => {
  if (isPrivateMode.value) {
    if (privateIsLoading.value) return 'Processing'
    const s = privateSimStatus.value?.runner_status
    if (s === 'running') return 'Running'
    if (s === 'completed') return 'Completed'
    if (s === 'failed') return 'Failed'
    if (currentPhase.value >= 2) return 'Ready'
    if (currentPhase.value === 1) return 'Building Graph'
    if (currentPhase.value === 0) return 'Generating Ontology'
    return 'Initializing'
  }
  if (error.value) return 'Error'
  if (currentPhase.value >= 2) return 'Ready'
  if (currentPhase.value === 1) return 'Building Graph'
  if (currentPhase.value === 0) return 'Generating Ontology'
  return 'Initializing'
})

// ── Helpers ───────────────────────────────────────────────────────────────
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 100) systemLogs.value.shift()
}

// ── Layout Methods ────────────────────────────────────────────────────────
const toggleMaximize = (target) => {
  if (viewMode.value === target) viewMode.value = 'split'
  else viewMode.value = target
}

const handleNextStep = (params = {}) => {
  if (currentStep.value < 5) {
    currentStep.value++
    addLog(t('log.enterStep', { step: currentStep.value, name: currentStepNames.value[currentStep.value - 1] }))
    if (!isPrivateMode.value && currentStep.value === 3 && params.maxRounds) {
      addLog(t('log.customSimRounds', { rounds: params.maxRounds }))
    }
  }
}

const handleGoBack = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog(t('log.returnToStep', { step: currentStep.value, name: currentStepNames.value[currentStep.value - 1] }))
  }
}

const goToPrivateStep = (n) => {
  currentStep.value = n
}

// ── Data Logic (commune Step 1) ───────────────────────────────────────────
const initProject = async () => {
  addLog('Project view initialized.')
  if (currentProjectId.value === 'new') {
    await handleNewProject()
  } else {
    await loadProject()
  }
}

const handleNewProject = async () => {
  const pending = getPendingUpload()
  if (!pending.isPending || pending.files.length === 0) {
    error.value = 'No pending files found.'
    addLog('Error: No pending files found for new project.')
    return
  }

  try {
    loading.value = true
    currentPhase.value = 0
    ontologyProgress.value = { message: 'Uploading and analyzing docs...' }
    addLog('Starting ontology generation: Uploading files...')

    const formData = new FormData()
    pending.files.forEach(f => formData.append('files', f))
    formData.append('simulation_requirement', pending.simulationRequirement)

    const res = await generateOntology(formData)
    if (res.success) {
      clearPendingUpload()
      currentProjectId.value = res.data.project_id
      projectData.value = res.data

      const queryMode = route.query.mode
      router.replace({
        name: 'Process',
        params: { projectId: res.data.project_id },
        query: queryMode ? { mode: queryMode } : {},
      })

      ontologyProgress.value = null
      addLog(`Ontology generated successfully for project ${res.data.project_id}`)
      await startBuildGraph()
    } else {
      error.value = res.error || 'Ontology generation failed'
      addLog(`Error generating ontology: ${error.value}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in handleNewProject: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const loadProject = async () => {
  try {
    loading.value = true
    addLog(`Loading project ${currentProjectId.value}...`)
    const res = await getProject(currentProjectId.value)
    if (res.success) {
      projectData.value = res.data
      updatePhaseByStatus(res.data.status)
      addLog(`Project loaded. Status: ${res.data.status}`)

      if (res.data.status === 'ontology_generated' && !res.data.graph_id) {
        await startBuildGraph()
      } else if (res.data.status === 'graph_building' && res.data.graph_build_task_id) {
        currentPhase.value = 1
        startPollingTask(res.data.graph_build_task_id)
        startGraphPolling()
      } else if (res.data.status === 'graph_completed' && res.data.graph_id) {
        currentPhase.value = 2
        await loadGraph(res.data.graph_id)
      }
    } else {
      error.value = res.error
      addLog(`Error loading project: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in loadProject: ${err.message}`)
  } finally {
    loading.value = false
  }
}

const updatePhaseByStatus = (status) => {
  switch (status) {
    case 'created':
    case 'ontology_generated': currentPhase.value = 0; break
    case 'graph_building': currentPhase.value = 1; break
    case 'graph_completed': currentPhase.value = 2; break
    case 'failed': error.value = 'Project failed'; break
  }
}

const startBuildGraph = async () => {
  try {
    currentPhase.value = 1
    buildProgress.value = { progress: 0, message: 'Starting build...' }
    addLog('Initiating graph build...')

    const res = await buildGraph({ project_id: currentProjectId.value })
    if (res.success) {
      addLog(`Graph build task started. Task ID: ${res.data.task_id}`)
      startGraphPolling()
      startPollingTask(res.data.task_id)
    } else {
      error.value = res.error
      addLog(`Error starting build: ${res.error}`)
    }
  } catch (err) {
    error.value = err.message
    addLog(`Exception in startBuildGraph: ${err.message}`)
  }
}

const startGraphPolling = () => {
  addLog('Started polling for graph data...')
  fetchGraphData()
  graphPollTimer = setInterval(fetchGraphData, 10000)
}

const fetchGraphData = async () => {
  try {
    const projRes = await getProject(currentProjectId.value)
    if (projRes.success && projRes.data.graph_id) {
      const gRes = await getGraphData(projRes.data.graph_id)
      if (gRes.success) {
        graphData.value = gRes.data
        const nodeCount = gRes.data.node_count || gRes.data.nodes?.length || 0
        const edgeCount = gRes.data.edge_count || gRes.data.edges?.length || 0
        addLog(`Graph data refreshed. Nodes: ${nodeCount}, Edges: ${edgeCount}`)
      }
    }
  } catch (err) {
    console.warn('Graph fetch error:', err)
  }
}

const startPollingTask = (taskId) => {
  pollTaskStatus(taskId)
  pollTimer = setInterval(() => pollTaskStatus(taskId), 2000)
}

const pollTaskStatus = async (taskId) => {
  try {
    const res = await getTaskStatus(taskId)
    if (res.success) {
      const task = res.data

      if (task.message && task.message !== buildProgress.value?.message) {
        addLog(task.message)
      }

      buildProgress.value = { progress: task.progress || 0, message: task.message }

      if (task.status === 'completed') {
        addLog('Graph build task completed.')
        stopPolling()
        stopGraphPolling()
        currentPhase.value = 2

        const projRes = await getProject(currentProjectId.value)
        if (projRes.success && projRes.data.graph_id) {
          projectData.value = projRes.data
          await loadGraph(projRes.data.graph_id)
        }
      } else if (task.status === 'failed') {
        stopPolling()
        error.value = task.error
        addLog(`Graph build task failed: ${task.error}`)
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  addLog(`Loading full graph data: ${graphId}`)
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('Graph data loaded successfully.')
    } else {
      addLog(`Failed to load graph data: ${res.error}`)
    }
  } catch (e) {
    addLog(`Exception loading graph: ${e.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    addLog('Manual graph refresh triggered.')
    loadGraph(projectData.value.graph_id)
  }
}

const stopPolling = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

const stopGraphPolling = () => {
  if (graphPollTimer) { clearInterval(graphPollTimer); graphPollTimer = null; addLog('Graph polling stopped.') }
}

// ── Private Flow ──────────────────────────────────────────────────────────
const runPrivatePrepare = async () => {
  if (!projectData.value?.graph_id) {
    privateError.value = 'No graph_id found for this project. Build the graph first.'
    return
  }
  privateError.value = null
  privateIsLoading.value = true
  privatePrepareReady.value = true

  try {
    const res = await preparePrivateSimulation({
      graph_id: projectData.value.graph_id,
      simulation_requirement: buildRequirement(privateForm, privateAgentCounts, RELATIONAL_TYPE_LABELS),
      decision_context: privateForm.decisionContext,
      entity_types: privateForm.relationalTypes,
    })
    privateSimId.value = res.data.sim_id
    privatePrepareResult.value = res.data
  } catch (e) {
    privateError.value = `Prepare failed: ${e.message}`
    privatePrepareReady.value = false
  } finally {
    privateIsLoading.value = false
  }
}

const runPrivateStart = async () => {
  privateError.value = null
  privateIsLoading.value = true
  currentStep.value = 3

  try {
    await startPrivateSimulation({ sim_id: privateSimId.value })
    startPrivatePolling()
  } catch (e) {
    privateError.value = `Start failed: ${e.message}`
    currentStep.value = 2
  } finally {
    privateIsLoading.value = false
  }
}

const startPrivatePolling = () => {
  privatePollingTimer = setInterval(pollPrivateStatus, 3000)
  pollPrivateStatus()
}

const stopPrivatePolling = () => {
  if (privatePollingTimer) { clearInterval(privatePollingTimer); privatePollingTimer = null }
}

const pollPrivateStatus = async () => {
  if (!privateSimId.value) return
  try {
    const res = await getPrivateStatus(privateSimId.value)
    privateSimStatus.value = res.data
    privateRecentActions.value = res.data.recent_actions || []

    const status = res.data.runner_status
    if (status === 'completed' || status === 'stopped' || status === 'failed') {
      stopPrivatePolling()
      try {
        const actRes = await getPrivateActions(privateSimId.value)
        privateRecentActions.value = actRes.data || []
      } catch { /* keep last */ }
    }
  } catch (e) {
    console.error('Private status poll error:', e)
  }
}

const handlePrivateStop = async () => {
  try {
    stopPrivatePolling()
    await stopPrivateSimulation(privateSimId.value)
    const res = await getPrivateStatus(privateSimId.value)
    privateSimStatus.value = res.data
  } catch (e) {
    privateError.value = `Stop failed: ${e.message}`
  }
}

const runPrivateReport = async () => {
  privateError.value = null
  privateIsLoading.value = true
  privateReportProgress.value = 'Initialising Report Agent…'
  currentStep.value = 4

  try {
    const res = await generatePrivateReport(privateSimId.value)
    const reportId = res.data.report_id
    const taskId = res.data.task_id

    if (res.data.already_generated) {
      const fullRes = await getReport(reportId)
      privateReportResult.value = fullRes.data
      privateIsLoading.value = false
      return
    }

    startPrivateReportPolling(taskId, reportId)
  } catch (e) {
    privateError.value = `Report trigger failed: ${e.message}`
    privateIsLoading.value = false
  }
}

const startPrivateReportPolling = (taskId, reportId) => {
  privateReportPollingTimer = setInterval(() => pollPrivateReport(taskId, reportId), 4000)
  pollPrivateReport(taskId, reportId)
}

const stopPrivateReportPolling = () => {
  if (privateReportPollingTimer) { clearInterval(privateReportPollingTimer); privateReportPollingTimer = null }
}

const pollPrivateReport = async (taskId, reportId) => {
  try {
    const res = await getPrivateReportStatus(taskId)
    const status = res.data?.status
    privateReportProgress.value = res.data?.message || 'Generating…'

    if (status === 'completed') {
      stopPrivateReportPolling()
      const finalReportId = res.data?.result?.report_id || reportId
      const fullRes = await getReport(finalReportId)
      privateReportResult.value = fullRes.data
      privateIsLoading.value = false
    } else if (status === 'failed') {
      stopPrivateReportPolling()
      privateError.value = `Report failed: ${res.data?.error || res.data?.message}`
      privateIsLoading.value = false
    }
  } catch (e) {
    console.error('Private report poll error:', e)
  }
}

const loadPrivateChatAgents = async () => {
  try {
    const res = await getPrivateActions(privateSimId.value)
    const agentMap = {}
    for (const action of (res.data || [])) {
      if (!agentMap[action.agent_id]) {
        agentMap[action.agent_id] = {
          agent_id: action.agent_id,
          entity_name: action.agent_name || `Agent ${action.agent_id}`,
          relational_link_type: action.action_args?.relational_link_type || '',
          stance: action.action_args?.stance || 'neutral',
        }
      }
    }
    privateChatAgents.value = Object.values(agentMap)
  } catch (e) {
    console.error('Could not load agents:', e)
  }
}

watch(() => currentStep.value, (step) => {
  if (isPrivateMode.value && step === 5 && privateChatAgents.value.length === 0) {
    loadPrivateChatAgents()
  }
})

// ── Timer Cleanup ─────────────────────────────────────────────────────────
const cleanupPublicTimers = () => {
  stopPolling()
  stopGraphPolling()
}

const cleanupPrivateTimers = () => {
  stopPrivatePolling()
  stopPrivateReportPolling()
}

const cleanupAllTimers = () => {
  cleanupPublicTimers()
  cleanupPrivateTimers()
}

// ── Mode watcher (reset transient state when mode changes) ────────────────
watch(isPrivateMode, () => {
  currentStep.value = 1
  privatePrepareReady.value = false
  cleanupPrivateTimers()
})

// ── Lifecycle ─────────────────────────────────────────────────────────────
onMounted(() => {
  initProject()
})

onBeforeRouteLeave(() => {
  cleanupAllTimers()
})

onBeforeRouteUpdate((to, from) => {
  if (to.params.projectId !== from.params.projectId) {
    cleanupAllTimers()
  }
})

onUnmounted(() => {
  cleanupAllTimers()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 1px solid #EAEAEA;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #FFF;
  z-index: 100;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  cursor: pointer;
}

.mode-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  background: #000;
  color: #fff;
  padding: 4px 10px;
  border-radius: 2px;
}

.view-switcher {
  display: flex;
  background: #F5F5F5;
  padding: 4px;
  border-radius: 6px;
  gap: 4px;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: #FFF;
  color: #000;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: #999;
}

.step-name {
  font-weight: 700;
  color: #000;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: #E0E0E0;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #CCC;
}

.status-indicator.processing .dot { background: #FF5722; animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: #4CAF50; }
.status-indicator.error .dot { background: #F44336; }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.content-area.split-view {
  display: flex;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 1px solid #EAEAEA;
}

/* ── Private area ─────────────────────────────────────────────────────── */
.private-area {
  display: block;
  overflow-y: auto;
  padding: 24px 32px;
}

/* Steps bar (private) */
.steps-bar {
  display: flex;
  align-items: center;
  padding: 12px 32px;
  border-bottom: 1px solid #EFEFEF;
  background: #FAFAFA;
  flex-shrink: 0;
  gap: 0;
}

.step-node {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.step-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1.5px solid #D0D0D0;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #999;
  flex-shrink: 0;
  transition: all 0.2s;
}

.step-node.is-active .step-circle { border-color: #000; background: #000; color: #fff; }
.step-node.is-done .step-circle { border-color: #4CAF50; background: #4CAF50; color: #fff; }

.step-node-name {
  font-size: 11px;
  font-weight: 600;
  color: #AAA;
  white-space: nowrap;
}

.step-node.is-active .step-node-name { color: #000; }
.step-node.is-done { cursor: pointer; }
.step-node.is-done .step-node-name { color: #555; }

.step-connector {
  width: 32px;
  height: 1.5px;
  background: #E0E0E0;
  margin: 0 8px;
  flex-shrink: 0;
}

.step-connector.is-done { background: #4CAF50; }

/* Error banner */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 32px;
  background: #FFF3F3;
  border-bottom: 1px solid #FFCDD2;
  font-size: 12px;
  color: #C62828;
}

.error-close {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #C62828;
  padding: 0 4px;
}

/* Private centered panel (step 2 after prepare) */
.centered-panel {
  max-width: 680px;
  margin: 0 auto;
}

.loading-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 60px 0;
  text-align: center;
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid #E5E7EB;
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-label { font-size: 14px; font-weight: 600; color: #000; }
.loading-hint { font-size: 12px; color: #888; max-width: 400px; line-height: 1.5; }

.prepare-results { display: flex; flex-direction: column; gap: 20px; padding: 20px 0; }

.result-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 6px 12px;
  border-radius: 2px;
}

.result-badge--ok { background: #E8F5E9; color: #2E7D32; }

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-card {
  border: 1.5px solid #E8E8E8;
  border-radius: 4px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value { font-size: 28px; font-weight: 700; color: #000; }
.stat-label { font-size: 10px; font-weight: 600; letter-spacing: 0.1em; color: #888; text-transform: uppercase; }

.relation-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.relation-tag { font-size: 11px; padding: 3px 8px; background: #F0F0F0; border-radius: 2px; color: #444; font-weight: 500; text-transform: capitalize; }

.sim-id-block { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #F7F7F7; border-radius: 3px; }
.sim-id-label { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: #999; }
.sim-id-value { font-size: 12px; color: #333; }

.result-actions { display: flex; gap: 10px; }

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover { background: #222; }
.btn-primary:disabled { background: #CCC; cursor: not-allowed; }

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: #fff;
  color: #000;
  border: 1.5px solid #000;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-secondary:hover { background: #F5F5F5; }

.mono { font-family: 'JetBrains Mono', monospace; }
</style>
