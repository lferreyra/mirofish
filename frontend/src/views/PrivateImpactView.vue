<template>
  <div class="private-view">

    <!-- ── Header ── -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">MIROFISH</div>
      </div>
      <div class="header-center">
        <div class="mode-badge">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          PRIVATE IMPACT
        </div>
      </div>
      <div class="header-right">
        <LanguageSwitcher />
        <div class="step-divider"></div>
        <div class="workflow-step">
          <span class="step-num">Step {{ currentStep }}/5</span>
          <span class="step-name">{{ stepNames[currentStep - 1] }}</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- ── Step breadcrumb ── -->
    <div class="steps-bar">
      <div
        v-for="(name, idx) in stepNames"
        :key="idx"
        class="step-node"
        :class="{
          'is-active': currentStep === idx + 1,
          'is-done': currentStep > idx + 1,
        }"
        @click="currentStep > idx + 1 ? goToStep(idx + 1) : null"
      >
        <div class="step-circle">
          <svg v-if="currentStep > idx + 1" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span v-else>{{ idx + 1 }}</span>
        </div>
        <span class="step-node-name">{{ name }}</span>
        <div v-if="idx < stepNames.length - 1" class="step-connector" :class="{ 'is-done': currentStep > idx + 1 }"></div>
      </div>
    </div>

    <!-- ── Error banner ── -->
    <div v-if="error" class="error-banner">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {{ error }}
      <button class="error-close" @click="error = null">×</button>
    </div>

    <!-- ══════════════════════════════════════════════════════════
         STEP 1 — Requirement Form
    ══════════════════════════════════════════════════════════ -->
    <main v-if="currentStep === 1" class="content-area">
      <div class="form-container">
        <div class="section-title-row">
          <h2 class="section-h2">Define the Decision</h2>
          <p class="section-hint">Fill in the decision context. These details will drive the simulation.</p>
        </div>

        <div
          class="drop-zone"
          :class="{ 'drop-zone--active': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
          @click="triggerImport"
        >
          <input type="file" ref="importInput" accept=".txt" style="display:none" @change="handleImport" />
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span class="drop-zone-label">Glisser le fichier ici ou cliquer pour importer</span>
          <span class="drop-zone-hint">private_impact_requirement.txt — dossier 02_simulation_params/</span>
        </div>

        <div v-if="!projectData?.graph_id" class="graph-building-notice">
          <div class="loading-ring loading-ring--sm"></div>
          <span>Graphe en construction — les champs peuvent déjà être remplis. Le bouton s'activera automatiquement.</span>
        </div>

        <div class="form-grid">
          <!-- Left column -->
          <div class="form-col">
            <div class="field-group">
              <label class="field-label">DECISION MAKER</label>
              <div class="field-row-3">
                <input class="field-input" v-model="form.decisionMakerName" placeholder="Full name" />
                <input class="field-input" v-model="form.decisionMakerRole" placeholder="Role / title" />
                <input class="field-input" v-model="form.decisionMakerCompany" placeholder="Organisation" />
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">DECISION <span class="required">*</span></label>
              <textarea
                class="field-textarea"
                v-model="form.decisionText"
                rows="5"
                placeholder="Describe the decision precisely. E.g. 'We are closing the Lyon office and transferring 40 employees to Paris by Q3.'"
              ></textarea>
            </div>

            <div class="field-group">
              <label class="field-label">ADDITIONAL CONTEXT</label>
              <textarea
                class="field-textarea"
                v-model="form.decisionContext"
                rows="3"
                placeholder="Background information, strategic rationale, known sensitivities..."
              ></textarea>
            </div>
          </div>

          <!-- Right column -->
          <div class="form-col">
            <div class="field-group">
              <label class="field-label">RELATIONAL NETWORK — types to include</label>
              <div class="checkbox-grid">
                <label
                  v-for="t in RELATIONAL_TYPES"
                  :key="t"
                  class="checkbox-item"
                  :class="{ 'is-checked': form.relationalTypes.includes(t) }"
                >
                  <input
                    type="checkbox"
                    :value="t"
                    v-model="form.relationalTypes"
                    class="checkbox-native"
                  />
                  <span class="checkbox-box"></span>
                  <span class="checkbox-label">{{ RELATIONAL_TYPE_LABELS[t] }}</span>
                </label>
              </div>

              <div v-if="form.relationalTypes.length > 0" class="agent-counts-block">
                <div v-for="t in form.relationalTypes" :key="t" class="agent-count-row">
                  <span class="agent-count-label">{{ RELATIONAL_TYPE_LABELS[t] }}</span>
                  <div class="agent-count-sep"></div>
                  <input
                    type="number"
                    class="agent-count-input"
                    v-model.number="agentCounts[t]"
                    min="1"
                    max="200"
                  />
                </div>
                <div class="agent-count-total">Total : {{ totalAgents }} agents</div>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">TEMPORAL HORIZON</label>
              <div class="horizon-btns">
                <button
                  v-for="opt in HORIZON_OPTIONS"
                  :key="opt.days"
                  type="button"
                  class="horizon-btn"
                  :class="{ 'is-active': form.horizonDays === opt.days }"
                  @click="form.horizonDays = opt.days"
                >{{ opt.label }}</button>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">QUESTIONS TO MEASURE</label>
              <textarea
                class="field-textarea"
                v-model="form.questionsToMeasure"
                rows="3"
                placeholder="What do you want to measure? E.g. 'What is the risk of collective resistance? Who are the key opinion leaders?'"
              ></textarea>
            </div>
          </div>
        </div>

        <div class="form-footer">
          <button
            class="btn-primary"
            :disabled="!form.decisionText.trim() || form.relationalTypes.length === 0 || !projectData?.graph_id"
            @click="runPrepare"
          >
            Prepare Simulation
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </div>
      </div>
    </main>

    <!-- ══════════════════════════════════════════════════════════
         STEP 2 — Prepare
    ══════════════════════════════════════════════════════════ -->
    <main v-else-if="currentStep === 2" class="content-area">
      <div class="centered-panel">

        <!-- Loading -->
        <div v-if="isLoading" class="loading-block">
          <div class="loading-ring"></div>
          <p class="loading-label">Generating relational profiles and behavioural parameters…</p>
          <p class="loading-hint">This may take a few seconds per agent. The LLM is building the simulation config.</p>
        </div>

        <!-- Results -->
        <div v-else-if="prepareResult" class="prepare-results">
          <div class="result-badge result-badge--ok">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Simulation ready
          </div>

          <div class="result-stats">
            <div class="stat-card">
              <span class="stat-value mono">{{ prepareResult.agent_count }}</span>
              <span class="stat-label">Agents generated</span>
            </div>
            <div class="stat-card">
              <span class="stat-value mono">{{ form.horizonDays }}d</span>
              <span class="stat-label">Temporal horizon</span>
            </div>
            <div class="stat-card">
              <span class="stat-value mono">{{ form.relationalTypes.length }}</span>
              <span class="stat-label">Relation types</span>
            </div>
          </div>

          <div class="relation-tags">
            <span
              v-for="t in form.relationalTypes"
              :key="t"
              class="relation-tag"
            >{{ t }}</span>
          </div>

          <div class="sim-id-block">
            <span class="sim-id-label">SIM ID</span>
            <span class="sim-id-value mono">{{ simId }}</span>
          </div>

          <div class="result-actions">
            <button class="btn-secondary" @click="goToStep(1)">← Back</button>
            <button class="btn-primary" @click="runStart">
              Launch Simulation
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
          </div>
        </div>

      </div>
    </main>

    <!-- ══════════════════════════════════════════════════════════
         STEP 3 — Running
    ══════════════════════════════════════════════════════════ -->
    <main v-else-if="currentStep === 3" class="content-area">
      <div class="run-layout">

        <!-- Left: Progress panel -->
        <div class="run-progress-panel">
          <div class="run-platform-status" :class="{ 'is-running': simStatus?.private_running, 'is-done': simStatus?.private_completed }">
            <div class="rps-header">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Private Network</span>
              <span v-if="simStatus?.private_completed" class="rps-badge-done">DONE</span>
              <span v-else-if="simStatus?.private_running" class="rps-badge-run">RUNNING</span>
              <span v-else class="rps-badge-idle">IDLE</span>
            </div>
            <div class="rps-stats">
              <div class="rps-stat">
                <span class="rps-stat-label">ROUND</span>
                <span class="rps-stat-value mono">{{ simStatus?.private_current_round || 0 }}</span>
              </div>
              <div class="rps-stat">
                <span class="rps-stat-label">DAY</span>
                <span class="rps-stat-value mono">{{ simStatus?.private_simulated_days || 0 }}</span>
              </div>
              <div class="rps-stat">
                <span class="rps-stat-label">ACTIONS</span>
                <span class="rps-stat-value mono">{{ simStatus?.private_actions_count || 0 }}</span>
              </div>
            </div>
            <!-- Progress bar -->
            <div class="rps-progress-track">
              <div
                class="rps-progress-fill"
                :style="{ width: roundProgress + '%' }"
              ></div>
            </div>
            <div class="rps-progress-label mono">{{ roundProgress }}%</div>
          </div>

          <div class="run-action-types">
            <div class="run-action-types-title">ACTION TYPES</div>
            <div v-for="(count, type) in actionTypeCounts" :key="type" class="action-type-row">
              <span class="action-type-name">{{ type }}</span>
              <span class="action-type-count mono">{{ count }}</span>
            </div>
            <div v-if="Object.keys(actionTypeCounts).length === 0" class="no-actions-yet">
              Waiting for first actions…
            </div>
          </div>

          <div class="run-controls">
            <button
              v-if="simStatus?.runner_status === 'running'"
              class="btn-stop"
              @click="handleStop"
            >
              Stop Simulation
            </button>
            <button
              v-if="simStatus?.runner_status === 'completed' || simStatus?.runner_status === 'stopped'"
              class="btn-primary"
              @click="runReport"
            >
              Generate Report →
            </button>
          </div>
        </div>

        <!-- Right col: propagation graph + reduced feed -->
        <div class="run-right-col">
          <div class="graph-panel" ref="graphContainer"></div>

          <div class="run-feed-panel" ref="feedPanel">
            <div class="feed-header">LIVE ACTION FEED</div>
            <div class="feed-list">
              <div
                v-for="(action, idx) in recentActions.slice(-10)"
                :key="idx"
                class="feed-item"
              >
                <span class="feed-round mono">#{{ action.round_num }}</span>
                <span class="feed-agent">{{ action.agent_name || `Agent ${action.agent_id}` }}</span>
                <span class="feed-action-type" :class="actionTypeClass(action.action_type)">{{ action.action_type }}</span>
                <span class="feed-time mono">{{ shortTime(action.timestamp) }}</span>
              </div>
              <div v-if="recentActions.length === 0" class="feed-empty">Waiting for simulation events…</div>
            </div>
          </div>
        </div>

      </div>
    </main>

    <!-- ══════════════════════════════════════════════════════════
         STEP 4 — Report
    ══════════════════════════════════════════════════════════ -->
    <main v-else-if="currentStep === 4" class="content-area">
      <div class="centered-panel">

        <!-- Generating -->
        <div v-if="isLoading" class="loading-block">
          <div class="loading-ring"></div>
          <p class="loading-label">Report Agent is analysing the simulation…</p>
          <p class="loading-hint">{{ reportProgress }}</p>
        </div>

        <!-- Report ready -->
        <div v-else-if="reportResult" class="report-ready">
          <div class="result-badge result-badge--ok">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Report ready
          </div>

          <div class="report-sections" v-if="reportResult.outline?.sections?.length">
            <div v-for="(section, idx) in reportResult.outline.sections" :key="idx" class="report-section">
              <div class="rs-header" @click="toggleSection(idx)">
                <span class="rs-num">{{ String(idx + 1).padStart(2, '0') }}</span>
                <span class="rs-title">{{ section.title || ('Section ' + String(idx + 1).padStart(2, '0')) }}</span>
                <svg class="rs-chevron" :class="{ 'is-open': !collapsedSections.has(idx) }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </div>
              <div v-show="!collapsedSections.has(idx)" class="rs-body">
                <p>{{ section.content }}</p>
              </div>
            </div>
          </div>
          <pre v-else-if="reportResult.markdown_content" class="report-markdown">{{ reportResult.markdown_content }}</pre>

          <div class="result-actions">
            <button class="btn-secondary" @click="exportReportMarkdown">
              Export .md
            </button>
            <button class="btn-secondary" @click="goToStep(5)">
              Talk to Agents →
            </button>
          </div>
        </div>

        <!-- Error generating report -->
        <div v-else class="error-placeholder">
          <p>Report generation did not complete. Check logs and retry.</p>
          <button class="btn-secondary" @click="runReport">Retry</button>
        </div>

      </div>
    </main>

    <!-- ══════════════════════════════════════════════════════════
         STEP 5 — Interaction
    ══════════════════════════════════════════════════════════ -->
    <main v-else-if="currentStep === 5" class="content-area">
      <div class="chat-layout">

        <!-- Left: agent list -->
        <div class="chat-agents-panel">
          <div class="chat-agents-title">RELATIONAL AGENTS</div>
          <div
            v-for="agent in chatAgents"
            :key="agent.agent_id"
            class="chat-agent-item"
            :class="{ 'is-selected': selectedAgentId === agent.agent_id }"
            @click="selectedAgentId = agent.agent_id"
          >
            <div class="agent-avatar">{{ initials(agent.entity_name) }}</div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.entity_name }}</div>
              <div class="agent-type">{{ agent.relational_link_type }}</div>
            </div>
            <div class="agent-stance-dot" :class="'stance-' + agent.stance"></div>
          </div>
          <div v-if="chatAgents.length === 0" class="chat-agents-empty">Loading agents…</div>
        </div>

        <!-- Right: chat -->
        <div class="chat-main">
          <div class="chat-messages" ref="chatMessagesEl">
            <div v-if="!selectedAgentId" class="chat-placeholder">
              Select an agent on the left to start a conversation.
            </div>
            <template v-else>
              <div
                v-for="(msg, idx) in currentMessages"
                :key="idx"
                class="chat-msg"
                :class="msg.role === 'user' ? 'chat-msg--user' : 'chat-msg--agent'"
              >
                <div class="chat-msg-label">{{ msg.role === 'user' ? 'You' : selectedAgentName }}</div>
                <div class="chat-msg-text">{{ msg.content }}</div>
              </div>
              <div v-if="isChatLoading" class="chat-msg chat-msg--agent">
                <div class="chat-msg-label">{{ selectedAgentName }}</div>
                <div class="chat-msg-text chat-thinking">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </template>
          </div>

          <div class="chat-input-row" v-if="selectedAgentId">
            <textarea
              class="chat-input"
              v-model="chatInput"
              placeholder="Ask this agent a question…"
              rows="2"
              @keydown.enter.exact.prevent="sendChat"
            ></textarea>
            <button class="chat-send-btn" :disabled="!chatInput.trim() || isChatLoading" @click="sendChat">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>

      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as d3 from 'd3'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { getProject } from '../api/graph.js'
import { interviewAgents } from '../api/simulation.js'
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

const props = defineProps({
  projectId: { type: String, required: true },
})

const router = useRouter()

// ── Constants ──────────────────────────────────────────────────────────────

const RELATIONAL_TYPES = [
  'ouvrier_production', 'technicien', 'commercial',
  'manager', 'codir', 'client_externe', 'partenaire', 'concurrent',
]

const RELATIONAL_TYPE_LABELS = {
  ouvrier_production: 'Ouvrier / Production',
  technicien: 'Technicien',
  commercial: 'Commercial',
  manager: 'Manager',
  codir: 'CODIR',
  client_externe: 'Client externe',
  partenaire: 'Partenaire',
  concurrent: 'Concurrent',
}

const HORIZON_OPTIONS = [
  { days: 3, label: '3 jours (72h)' },
  { days: 7, label: '7 jours' },
  { days: 30, label: '30 jours' },
  { days: 180, label: '6 mois (180 jours)' },
]

const stepNames = ['Requirement', 'Prepare', 'Run', 'Report', 'Interact']

// ── State ──────────────────────────────────────────────────────────────────

const currentStep = ref(1)
const projectData = ref(null)
const simId = ref(null)
const simStatus = ref(null)
const prepareResult = ref(null)
const reportResult = ref(null)
const isLoading = ref(false)
const error = ref(null)
const reportProgress = ref('')

// Step 1 - import config
const importInput = ref(null)
const isDragOver = ref(false)

// Step 3 - live feed
const recentActions = ref([])
const feedPanel = ref(null)
let pollingTimer = null

// Step 1 - graph ready polling
let graphReadyTimer = null

// Step 3 - D3 propagation graph
const graphContainer = ref(null)
let simulation = null
let svgEl = null
let linkGroup = null
let nodeGroup = null

// Step 4 - report polling
let reportPollingTimer = null
const collapsedSections = ref(new Set())

// Step 5 - chat
const chatAgents = ref([])
const selectedAgentId = ref(null)
const chatMessages = reactive({}) // agentId -> [{ role, content }]
const chatInput = ref('')
const isChatLoading = ref(false)
const chatMessagesEl = ref(null)

// Form
const form = reactive({
  decisionMakerName: '',
  decisionMakerRole: '',
  decisionMakerCompany: '',
  decisionText: '',
  decisionContext: '',
  relationalTypes: ['ouvrier_production', 'technicien', 'commercial', 'manager', 'codir'],
  horizonDays: 3,
  questionsToMeasure: '',
})

// Agent counts per relational type
const agentCounts = reactive({})

watch(() => form.relationalTypes, (types) => {
  for (const t of types) {
    if (!(t in agentCounts)) agentCounts[t] = 10
  }
  for (const key of Object.keys(agentCounts)) {
    if (!types.includes(key)) delete agentCounts[key]
  }
}, { immediate: true })

// ── Computed ───────────────────────────────────────────────────────────────

const totalAgents = computed(() =>
  Object.values(agentCounts).reduce((sum, n) => sum + (n || 0), 0)
)

const statusClass = computed(() => {
  const s = simStatus.value?.runner_status
  if (s === 'running') return 'processing'
  if (s === 'completed') return 'completed'
  if (s === 'failed') return 'error'
  if (isLoading.value) return 'processing'
  return 'idle'
})

const statusText = computed(() => {
  if (isLoading.value) return 'Processing'
  const s = simStatus.value?.runner_status
  if (s === 'running') return 'Running'
  if (s === 'completed') return 'Completed'
  if (s === 'failed') return 'Failed'
  return 'Ready'
})

const roundProgress = computed(() => {
  if (simStatus.value?.progress_percent != null) return simStatus.value.progress_percent
  const total = simStatus.value?.private_total_rounds || 0
  const current = simStatus.value?.private_current_round || 0
  if (!total) return 0
  return Math.round((current / total) * 100)
})

const actionTypeCounts = computed(() => {
  const counts = {}
  for (const action of recentActions.value) {
    counts[action.action_type] = (counts[action.action_type] || 0) + 1
  }
  return counts
})

const selectedAgentName = computed(() => {
  const agent = chatAgents.value.find(a => a.agent_id === selectedAgentId.value)
  return agent?.entity_name || `Agent ${selectedAgentId.value}`
})

const currentMessages = computed(() => {
  return chatMessages[selectedAgentId.value] || []
})

// ── D3 Graph ───────────────────────────────────────────────────────────────

const ACTION_COLORS = {
  CONFRONT: '#F44336',
  COALITION_BUILD: '#FF9800',
  VOCAL_SUPPORT: '#4CAF50',
  SILENT_LEAVE: '#616161',
  REACT_PRIVATELY: '#E0E0E0',
  DO_NOTHING: '#E0E0E0',
}

const nodeColor = (actionType) => {
  if (!actionType) return '#E0E0E0'
  const upper = actionType.toUpperCase()
  for (const [key, color] of Object.entries(ACTION_COLORS)) {
    if (upper.includes(key)) return color
  }
  return '#E0E0E0'
}

const ticked = () => {
  if (!linkGroup || !nodeGroup) return
  linkGroup.selectAll('line')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y)
  nodeGroup.selectAll('g.node')
    .attr('transform', d => `translate(${d.x},${d.y})`)
}

const initGraph = () => {
  if (!graphContainer.value) return
  const container = graphContainer.value
  const width = container.clientWidth || 600
  const height = container.clientHeight || 400

  d3.select(container).selectAll('*').remove()

  svgEl = d3.select(container)
    .append('svg')
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)

  linkGroup = svgEl.append('g').attr('class', 'links')
  nodeGroup = svgEl.append('g').attr('class', 'nodes')

  simulation = d3.forceSimulation([])
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('link', d3.forceLink([]).id(d => d.id).distance(80))
    .on('tick', ticked)
}

const updateGraph = (actions) => {
  if (!simulation || !svgEl) return

  const agentActions = {}
  const agentNames = {}
  const linkPairs = {}

  // Seed nodes from static config so the graph shows the full relational
  // network even before any action has been recorded.
  const staticAgents = simStatus.value?.agents || []
  for (const a of staticAgents) {
    if (a.agent_id === undefined || a.agent_id === null) continue
    const sid = String(a.agent_id)
    agentNames[sid] = a.entity_name || `Agent ${sid}`
  }

  for (const action of actions) {
    const id = action.agent_id
    if (id === undefined || id === null) continue
    const sid = String(id)
    agentNames[sid] = action.agent_name || agentNames[sid] || `Agent ${sid}`
    if (!agentActions[sid]) agentActions[sid] = {}
    const t = action.action_type || 'DO_NOTHING'
    agentActions[sid][t] = (agentActions[sid][t] || 0) + 1
    if (action.target_agent_id !== undefined && action.target_agent_id !== null) {
      const key = `${sid}__${String(action.target_agent_id)}`
      linkPairs[key] = (linkPairs[key] || 0) + 1
    }
  }

  const nodes = Object.keys(agentNames).map(id => {
    const counts = agentActions[id] || {}
    const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'DO_NOTHING'
    return { id, name: agentNames[id], dominant }
  })

  const nodeIds = new Set(nodes.map(n => n.id))

  // Merge static cascade_influence edges with dynamic action-based edges.
  const staticEdges = simStatus.value?.relational_edges || []
  const staticKeys = new Set()
  for (const e of staticEdges) {
    if (e.source === undefined || e.target === undefined) continue
    staticKeys.add(`${String(e.source)}__${String(e.target)}`)
  }

  const links = []
  staticKeys.forEach(key => {
    const [source, target] = key.split('__')
    if (nodeIds.has(source) && nodeIds.has(target)) {
      links.push({ source, target, count: linkPairs[key] || 0, kind: 'cascade' })
    }
  })
  Object.entries(linkPairs).forEach(([key, count]) => {
    if (staticKeys.has(key)) return
    const [source, target] = key.split('__')
    if (nodeIds.has(source) && nodeIds.has(target)) {
      links.push({ source, target, count, kind: 'action' })
    }
  })

  const existing = {}
  simulation.nodes().forEach(n => { existing[n.id] = { x: n.x, y: n.y, vx: n.vx, vy: n.vy } })
  nodes.forEach(n => {
    if (existing[n.id]) {
      n.x = existing[n.id].x; n.y = existing[n.id].y
      n.vx = existing[n.id].vx; n.vy = existing[n.id].vy
    }
  })

  simulation.nodes(nodes)
  simulation.force('link').links(links)
  simulation.alpha(0.3).restart()

  const linkSel = linkGroup.selectAll('line')
    .data(links, d => `${d.source.id || d.source}__${d.target.id || d.target}`)
  linkSel.exit().remove()
  linkSel.enter().append('line')
    .merge(linkSel)
    .attr('stroke', d => d.kind === 'cascade' && d.count === 0 ? '#E5E5E5' : '#999')
    .attr('stroke-dasharray', d => d.kind === 'cascade' && d.count === 0 ? '3,3' : null)
    .attr('stroke-width', d => Math.min(1 + d.count * 0.5, 4))

  const nodeSel = nodeGroup.selectAll('g.node').data(nodes, d => d.id)
  nodeSel.exit().remove()
  const nodeEnter = nodeSel.enter().append('g').attr('class', 'node')
  nodeEnter.append('circle').attr('r', 8)
  nodeEnter.append('text')
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .attr('font-size', '9px')
    .attr('fill', '#555')

  const nodeMerge = nodeEnter.merge(nodeSel)
  nodeMerge.select('circle')
    .attr('fill', d => nodeColor(d.dominant))
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)
  nodeMerge.select('text')
    .text(d => d.name.slice(0, 12))
}

// ── Import config (Step 1) ─────────────────────────────────────────────────

const triggerImport = () => { importInput.value?.click() }

const handleDrop = (event) => {
  isDragOver.value = false
  const file = event.dataTransfer.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => parseImportedConfig(e.target.result)
  reader.readAsText(file)
}

const handleImport = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    parseImportedConfig(e.target.result)
    event.target.value = ''
  }
  reader.readAsText(file)
}

const parseImportedConfig = (text) => {
  let configText = text
  const configMatch = text.match(/#CONFIG\n([\s\S]*?)\n#END_CONFIG/)
  if (configMatch) configText = configMatch[1]

  const labelToKey = {}
  for (const [key, label] of Object.entries(RELATIONAL_TYPE_LABELS)) {
    labelToKey[label.toLowerCase()] = key
  }

  for (const line of configText.split('\n')) {
    try {
      if (line.startsWith('Décideur :')) {
        const val = line.replace('Décideur :', '').trim()
        const [nameAndRole, company] = val.split(' at ')
        const [name, role] = (nameAndRole || '').split(' — ')
        if (name) form.decisionMakerName = name.trim()
        if (role) form.decisionMakerRole = role.trim()
        if (company) form.decisionMakerCompany = company.trim()
      } else if (line.startsWith('Décision :')) {
        form.decisionText = line.replace('Décision :', '').trim()
      } else if (line.startsWith('Réseau simulé :')) {
        const types = line.replace('Réseau simulé :', '').trim()
          .split(', ').map(s => s.trim()).filter(t => RELATIONAL_TYPES.includes(t))
        if (types.length) form.relationalTypes = types
      } else if (line.startsWith('Horizon temporel :')) {
        const days = parseInt(line.replace('Horizon temporel :', '').trim(), 10)
        if (!isNaN(days)) form.horizonDays = days
      } else if (line.startsWith('Questions to measure :')) {
        form.questionsToMeasure = line.replace('Questions to measure :', '').trim()
      } else if (line.startsWith('Agent distribution:')) {
        const entries = line.replace('Agent distribution:', '').trim().split(',')
        for (const entry of entries) {
          const parts = entry.trim().split(' × ')
          if (parts.length !== 2) continue
          const key = labelToKey[parts[0].trim().toLowerCase()]
          const count = parseInt(parts[1].trim(), 10)
          if (key && !isNaN(count)) agentCounts[key] = count
        }
      }
    } catch { /* ligne ignorée */ }
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

const buildRequirement = () => {
  const parts = []
  if (form.decisionMakerName) {
    parts.push(`Decision maker: ${form.decisionMakerName}` +
      (form.decisionMakerRole ? ` — ${form.decisionMakerRole}` : '') +
      (form.decisionMakerCompany ? ` at ${form.decisionMakerCompany}` : ''))
  }
  parts.push(`Decision: ${form.decisionText}`)
  parts.push(`Relational network: ${form.relationalTypes.join(', ')}`)
  parts.push(`Temporal horizon: ${form.horizonDays} days`)
  if (form.questionsToMeasure) parts.push(`Questions to measure: ${form.questionsToMeasure}`)
  const agentDistrib = form.relationalTypes
    .map(t => `${RELATIONAL_TYPE_LABELS[t]} × ${agentCounts[t] || 10}`)
    .join(', ')
  parts.push(`Agent distribution: ${agentDistrib}`)
  return parts.join('\n')
}

const goToStep = (n) => { currentStep.value = n }

const shortTime = (ts) => {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts.slice(11, 19) || ''
  }
}

const actionTypeClass = (type) => {
  if (!type) return ''
  const t = type.toLowerCase()
  if (t.includes('confront') || t.includes('oppos')) return 'type-hostile'
  if (t.includes('support') || t.includes('coalition')) return 'type-support'
  if (t.includes('nothing') || t.includes('idle') || t.includes('react_privately')) return 'type-passive'
  return 'type-neutral'
}

const initials = (name) => {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

const toggleSection = (idx) => {
  const s = new Set(collapsedSections.value)
  s.has(idx) ? s.delete(idx) : s.add(idx)
  collapsedSections.value = s
}

const exportReportMarkdown = () => {
  const report = reportResult.value
  if (!report) return

  let md = report.markdown_content
  if (!md) {
    const title = report.outline?.title || 'Private Impact Report'
    const summary = report.outline?.summary || ''
    const sections = report.outline?.sections || []
    md = `# ${title}\n\n`
    if (summary) md += `> ${summary}\n\n`
    sections.forEach((s, idx) => {
      const num = String(idx + 1).padStart(2, '0')
      md += `## ${num} — ${s.title || 'Section ' + num}\n\n`
      md += `${s.content || ''}\n\n`
    })
  }

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `private-impact-report-${simId.value || 'report'}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── Data loading ───────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const res = await getProject(props.projectId)
    projectData.value = res.data
    if (!res.data?.graph_id) {
      waitForGraph()
    }
  } catch (e) {
    error.value = `Could not load project: ${e.message}`
  }
})

const waitForGraph = () => {
  graphReadyTimer = setInterval(async () => {
    try {
      const res = await getProject(props.projectId)
      if (res.data?.graph_id) {
        projectData.value = res.data
        clearInterval(graphReadyTimer)
        graphReadyTimer = null
      }
    } catch { /* continue polling */ }
  }, 3000)
}

onUnmounted(() => {
  stopPolling()
  stopReportPolling()
  if (simulation) simulation.stop()
  if (graphReadyTimer) { clearInterval(graphReadyTimer); graphReadyTimer = null }
})

// ── Step 2: Prepare ────────────────────────────────────────────────────────

const runPrepare = async () => {
  if (!projectData.value?.graph_id) {
    error.value = 'No graph_id found for this project. Build the graph first.'
    return
  }
  error.value = null
  isLoading.value = true
  currentStep.value = 2

  try {
    const res = await preparePrivateSimulation({
      graph_id: projectData.value.graph_id,
      simulation_requirement: buildRequirement(),
      decision_context: form.decisionContext,
      entity_types: form.relationalTypes,
    })
    simId.value = res.data.sim_id
    prepareResult.value = res.data
  } catch (e) {
    error.value = `Prepare failed: ${e.message}`
    currentStep.value = 1
  } finally {
    isLoading.value = false
  }
}

// ── Step 3: Start + monitor ────────────────────────────────────────────────

const runStart = async () => {
  error.value = null
  isLoading.value = true
  currentStep.value = 3

  try {
    await startPrivateSimulation({ sim_id: simId.value })
    startPolling()
  } catch (e) {
    error.value = `Start failed: ${e.message}`
    currentStep.value = 2
  } finally {
    isLoading.value = false
  }
}

const startPolling = () => {
  pollingTimer = setInterval(pollStatus, 3000)
  pollStatus()
}

const stopPolling = () => {
  if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null }
}

const pollStatus = async () => {
  if (!simId.value) return
  try {
    const res = await getPrivateStatus(simId.value)
    simStatus.value = res.data
    recentActions.value = res.data.recent_actions || []

    const status = res.data.runner_status
    if (status === 'completed' || status === 'stopped' || status === 'failed') {
      stopPolling()
      // Fetch full action list for the feed
      try {
        const actRes = await getPrivateActions(simId.value)
        recentActions.value = actRes.data || []
      } catch { /* keep recent from status */ }
    }
  } catch (e) {
    console.error('Status poll error:', e)
  }
}

const handleStop = async () => {
  try {
    stopPolling()
    await stopPrivateSimulation(simId.value)
    const res = await getPrivateStatus(simId.value)
    simStatus.value = res.data
  } catch (e) {
    error.value = `Stop failed: ${e.message}`
  }
}

// ── Step 4: Report ─────────────────────────────────────────────────────────

const runReport = async () => {
  error.value = null
  isLoading.value = true
  reportProgress.value = 'Initialising Report Agent…'
  currentStep.value = 4

  try {
    const res = await generatePrivateReport(simId.value)
    const reportId = res.data.report_id
    const taskId = res.data.task_id

    if (res.data.already_generated) {
      const fullRes = await getReport(reportId)
      reportResult.value = fullRes.data
      isLoading.value = false
      return
    }

    startReportPolling(taskId, reportId)
  } catch (e) {
    error.value = `Report trigger failed: ${e.message}`
    isLoading.value = false
  }
}

const startReportPolling = (taskId, reportId) => {
  reportPollingTimer = setInterval(() => pollReport(taskId, reportId), 4000)
  pollReport(taskId, reportId)
}

const stopReportPolling = () => {
  if (reportPollingTimer) { clearInterval(reportPollingTimer); reportPollingTimer = null }
}

const pollReport = async (taskId, reportId) => {
  try {
    const res = await getPrivateReportStatus(taskId)
    const status = res.data?.status
    reportProgress.value = res.data?.message || 'Generating…'

    if (status === 'completed') {
      stopReportPolling()
      const finalReportId = res.data?.result?.report_id || reportId
      const fullRes = await getReport(finalReportId)
      reportResult.value = fullRes.data
      isLoading.value = false
    } else if (status === 'failed') {
      stopReportPolling()
      error.value = `Report failed: ${res.data?.error || res.data?.message}`
      isLoading.value = false
    }
  } catch (e) {
    console.error('Report poll error:', e)
  }
}

// ── Step 5: Interaction ────────────────────────────────────────────────────

watch(() => currentStep.value, async (step) => {
  if (step === 3) {
    await nextTick()
    initGraph()
  }
  if (step === 5 && chatAgents.value.length === 0) {
    loadChatAgents()
  }
})

const loadChatAgents = async () => {
  try {
    const res = await getPrivateActions(simId.value)
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
    chatAgents.value = Object.values(agentMap)
  } catch (e) {
    console.error('Could not load agents:', e)
  }
}

const sendChat = async () => {
  if (!chatInput.value.trim() || !selectedAgentId.value || isChatLoading.value) return

  const userMsg = chatInput.value.trim()
  chatInput.value = ''

  if (!chatMessages[selectedAgentId.value]) chatMessages[selectedAgentId.value] = []
  chatMessages[selectedAgentId.value].push({ role: 'user', content: userMsg })

  await nextTick()
  scrollChat()

  isChatLoading.value = true
  try {
    const history = chatMessages[selectedAgentId.value]
      .slice(0, -1)
      .map(m => ({ role: m.role, content: m.content }))

    const historyContext = history
      .map(m => `${m.role === 'user' ? 'User' : 'You'}: ${m.content}`)
      .join('\n')
    const prompt = historyContext
      ? `Previous conversation:\n${historyContext}\n\nNew question: ${userMsg}`
      : userMsg

    const res = await interviewAgents({
      simulation_id: simId.value,
      interviews: [{
        agent_id: selectedAgentId.value,
        prompt,
      }],
    })

    let reply = '(no response)'
    if (res.success && res.data) {
      const resultData = res.data.result || res.data
      const resultsDict = resultData.results || resultData
      const first = Object.values(resultsDict || {}).find(v => v && v.response)
      if (first?.response) reply = first.response
    }
    chatMessages[selectedAgentId.value].push({ role: 'agent', content: reply })
  } catch (e) {
    chatMessages[selectedAgentId.value].push({ role: 'agent', content: `Error: ${e.message}` })
  } finally {
    isChatLoading.value = false
    await nextTick()
    scrollChat()
  }
}

const scrollChat = () => {
  if (chatMessagesEl.value) {
    chatMessagesEl.value.scrollTop = chatMessagesEl.value.scrollHeight
  }
}

// Auto-scroll feed + update propagation graph
watch(() => recentActions.value.length, () => {
  nextTick(() => {
    if (feedPanel.value) feedPanel.value.scrollTop = feedPanel.value.scrollHeight
  })
  updateGraph(recentActions.value)
})

// Re-render graph skeleton as soon as the static cascade graph arrives,
// even if no action has been produced yet.
watch(
  () => (simStatus.value?.agents?.length || 0) + (simStatus.value?.relational_edges?.length || 0),
  () => updateGraph(recentActions.value || [])
)
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────────────── */
.private-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #fff;
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* ── Header ─────────────────────────────────────────────────────────────── */
.app-header {
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 52px;
  border-bottom: 1px solid #E8E8E8;
  background: #fff;
  flex-shrink: 0;
  gap: 16px;
}

.brand {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.12em;
  cursor: pointer;
  color: #000;
}

.header-left { min-width: 120px; }
.header-center { flex: 1; display: flex; justify-content: center; }
.header-right { min-width: 300px; display: flex; align-items: center; gap: 12px; justify-content: flex-end; }

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

.step-divider { width: 1px; height: 20px; background: #E0E0E0; }

.workflow-step { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.step-num { font-size: 10px; font-weight: 600; letter-spacing: 0.1em; color: #999; }
.step-name { font-size: 11px; font-weight: 600; color: #333; }

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: #888;
}

.status-indicator .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ccc;
}

.status-indicator.processing { color: #FF5722; }
.status-indicator.processing .dot { background: #FF5722; animation: pulse 1s infinite; }
.status-indicator.completed { color: #2E7D32; }
.status-indicator.completed .dot { background: #4CAF50; }
.status-indicator.error { color: #C62828; }
.status-indicator.error .dot { background: #F44336; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── Steps bar ───────────────────────────────────────────────────────────── */
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

.step-node.is-active .step-circle {
  border-color: #000;
  background: #000;
  color: #fff;
}

.step-node.is-done .step-circle {
  border-color: #4CAF50;
  background: #4CAF50;
  color: #fff;
}

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

/* ── Error banner ────────────────────────────────────────────────────────── */
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

/* ── Form (Step 1) ───────────────────────────────────────────────────────── */
.form-container { max-width: 1100px; margin: 0 auto; }

.section-title-row { margin-bottom: 24px; }

.graph-building-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #FFF8E1;
  border: 1px solid #FFE082;
  border-radius: 4px;
  font-size: 12px;
  color: #795548;
  margin-bottom: 20px;
}

.loading-ring--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
  flex-shrink: 0;
}

.drop-zone {
  border: 2px dashed #D0D0D0;
  border-radius: 6px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  margin-bottom: 24px;
  color: #AAA;
}
.drop-zone:hover { border-color: #000; color: #000; }
.drop-zone--active { border-color: #000; background: #F5F5F5; color: #000; }
.drop-zone-label { font-size: 13px; font-weight: 600; }
.drop-zone-hint { font-size: 10px; letter-spacing: 0.04em; }
.section-h2 { font-size: 18px; font-weight: 700; color: #000; margin-bottom: 6px; }
.section-hint { font-size: 13px; color: #777; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.form-col { display: flex; flex-direction: column; gap: 20px; }

.field-group { display: flex; flex-direction: column; gap: 8px; }

.field-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #888;
}

.required { color: #FF5722; }

.field-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }

.field-input, .field-textarea {
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 9px 12px;
  font-size: 13px;
  font-family: inherit;
  color: #000;
  background: #fff;
  transition: border-color 0.15s;
  resize: vertical;
}

.field-input:focus, .field-textarea:focus {
  outline: none;
  border-color: #000;
}

.field-input::placeholder, .field-textarea::placeholder { color: #BBB; }

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border: 1.5px solid #E8E8E8;
  border-radius: 3px;
  transition: border-color 0.15s, background 0.15s;
}

.checkbox-item.is-checked { border-color: #000; background: #FAFAFA; }

.checkbox-native { display: none; }

.checkbox-box {
  width: 14px;
  height: 14px;
  border: 1.5px solid #CCC;
  border-radius: 2px;
  flex-shrink: 0;
  background: #fff;
  transition: all 0.12s;
}

.checkbox-item.is-checked .checkbox-box {
  background: #000;
  border-color: #000;
}

.checkbox-label { font-size: 11px; font-weight: 500; color: #444; text-transform: capitalize; }

.slider-group { display: flex; flex-direction: column; gap: 6px; }

.field-slider {
  width: 100%;
  accent-color: #000;
  cursor: pointer;
}

.slider-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #AAA;
  letter-spacing: 0.04em;
}

.form-footer { margin-top: 28px; display: flex; justify-content: flex-end; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
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

.btn-stop {
  padding: 9px 18px;
  background: #fff;
  color: #C62828;
  border: 1.5px solid #C62828;
  border-radius: 3px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}

/* ── Centered panel (steps 2, 4) ─────────────────────────────────────────── */
.centered-panel {
  max-width: 680px;
  margin: 0 auto;
}

/* ── Loading ─────────────────────────────────────────────────────────────── */
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

/* ── Prepare results (step 2) ────────────────────────────────────────────── */
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

.relation-tag {
  font-size: 11px;
  padding: 3px 8px;
  background: #F0F0F0;
  border-radius: 2px;
  color: #444;
  font-weight: 500;
  text-transform: capitalize;
}

.sim-id-block { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #F7F7F7; border-radius: 3px; }
.sim-id-label { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; color: #999; }
.sim-id-value { font-size: 12px; color: #333; }

.result-actions { display: flex; gap: 10px; }

/* ── Run layout (step 3) ─────────────────────────────────────────────────── */
.run-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  height: calc(100vh - 172px);
}

.run-progress-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.run-platform-status {
  border: 1.5px solid #E0E0E0;
  border-radius: 4px;
  padding: 16px;
  transition: border-color 0.2s;
}

.run-platform-status.is-running { border-color: #FF5722; }
.run-platform-status.is-done { border-color: #4CAF50; }

.rps-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #000;
  margin-bottom: 12px;
}

.rps-badge-run { margin-left: auto; font-size: 9px; font-weight: 700; letter-spacing: 0.1em; color: #FF5722; background: #FFF3E0; padding: 2px 6px; border-radius: 2px; }
.rps-badge-done { margin-left: auto; font-size: 9px; font-weight: 700; letter-spacing: 0.1em; color: #2E7D32; background: #E8F5E9; padding: 2px 6px; border-radius: 2px; }
.rps-badge-idle { margin-left: auto; font-size: 9px; font-weight: 700; letter-spacing: 0.1em; color: #999; background: #F5F5F5; padding: 2px 6px; border-radius: 2px; }

.rps-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.rps-stat { display: flex; flex-direction: column; gap: 2px; }
.rps-stat-label { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; color: #AAA; }
.rps-stat-value { font-size: 18px; font-weight: 700; color: #000; }

.rps-progress-track { height: 4px; background: #E8E8E8; border-radius: 2px; overflow: hidden; margin-bottom: 4px; }
.rps-progress-fill { height: 100%; background: #000; border-radius: 2px; transition: width 0.5s ease; }
.rps-progress-label { font-size: 10px; color: #888; text-align: right; }

.run-action-types {
  border: 1.5px solid #EFEFEF;
  border-radius: 4px;
  padding: 12px;
}

.run-action-types-title { font-size: 9px; font-weight: 700; letter-spacing: 0.12em; color: #AAA; margin-bottom: 8px; }

.action-type-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #F5F5F5;
  font-size: 11px;
}

.action-type-name { color: #555; text-transform: uppercase; font-size: 10px; font-weight: 600; }
.action-type-count { color: #000; font-weight: 700; }
.no-actions-yet { font-size: 11px; color: #CCC; }

.run-controls { margin-top: auto; display: flex; flex-direction: column; gap: 8px; }

/* ── Right column + graph panel (step 3) ─────────────────────────────────── */
.run-right-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: calc(100vh - 172px);
}

.graph-panel {
  flex: 1;
  border: 1.5px solid #EFEFEF;
  border-radius: 4px;
  overflow: hidden;
  background: #FAFAFA;
}

/* ── Feed panel (step 3 right) ───────────────────────────────────────────── */
.run-feed-panel {
  border: 1.5px solid #EFEFEF;
  border-radius: 4px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  height: 200px;
  flex-shrink: 0;
}

.feed-header {
  padding: 10px 14px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: #AAA;
  border-bottom: 1px solid #F0F0F0;
  background: #FAFAFA;
  position: sticky;
  top: 0;
  flex-shrink: 0;
}

.feed-list { flex: 1; padding: 8px 0; }

.feed-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 14px;
  border-bottom: 1px solid #F7F7F7;
  font-size: 11px;
}

.feed-round { color: #BBB; min-width: 36px; flex-shrink: 0; }
.feed-agent { color: #333; font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.feed-time { color: #CCC; flex-shrink: 0; font-size: 10px; }

.feed-action-type {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 2px;
  flex-shrink: 0;
}

.type-hostile { background: #FFEBEE; color: #C62828; }
.type-support { background: #E8F5E9; color: #2E7D32; }
.type-passive { background: #F5F5F5; color: #999; }
.type-neutral { background: #E3F2FD; color: #1565C0; }

.feed-empty { padding: 24px 14px; font-size: 12px; color: #CCC; }

/* ── Report (step 4) ─────────────────────────────────────────────────────── */
.report-ready { display: flex; flex-direction: column; gap: 20px; padding: 20px 0; }
.report-markdown { white-space: pre-wrap; font-size: 13px; line-height: 1.7; color: #222; font-family: inherit; background: #FAFAFA; border: 1.5px solid #E8E8E8; border-radius: 4px; padding: 20px; margin: 0; }

.report-sections { display: flex; flex-direction: column; gap: 0; border: 1.5px solid #E8E8E8; border-radius: 4px; overflow: hidden; }

.report-section { border-bottom: 1px solid #F0F0F0; }
.report-section:last-child { border-bottom: none; }

.rs-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  background: #FAFAFA;
  transition: background 0.12s;
}

.rs-header:hover { background: #F3F3F3; }
.rs-num { font-size: 11px; font-weight: 700; color: #CCC; min-width: 24px; }
.rs-title { flex: 1; font-size: 13px; font-weight: 600; color: #000; }
.rs-chevron { flex-shrink: 0; transition: transform 0.2s; transform: rotate(-90deg); }
.rs-chevron.is-open { transform: rotate(0deg); }
.rs-body { padding: 14px 16px 14px 52px; font-size: 13px; color: #444; line-height: 1.6; background: #fff; }

.error-placeholder { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 40px 0; font-size: 13px; color: #888; }

/* ── Chat (step 5) ───────────────────────────────────────────────────────── */
.chat-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
  height: calc(100vh - 172px);
}

.chat-agents-panel { border: 1.5px solid #EFEFEF; border-radius: 4px; overflow-y: auto; }
.chat-agents-title { padding: 10px 14px; font-size: 9px; font-weight: 700; letter-spacing: 0.14em; color: #AAA; border-bottom: 1px solid #F0F0F0; background: #FAFAFA; }

.chat-agent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #F5F5F5;
  cursor: pointer;
  transition: background 0.12s;
}

.chat-agent-item:hover { background: #F9F9F9; }
.chat-agent-item.is-selected { background: #F2F2F2; }

.agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #000;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.agent-info { flex: 1; min-width: 0; }
.agent-name { font-size: 12px; font-weight: 600; color: #000; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-type { font-size: 10px; color: #999; text-transform: capitalize; }

.agent-stance-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stance-supportive { background: #4CAF50; }
.stance-opposing { background: #F44336; }
.stance-neutral { background: #9E9E9E; }
.stance-observer { background: #2196F3; }

.chat-agents-empty { padding: 20px 14px; font-size: 11px; color: #CCC; }

.chat-main { border: 1.5px solid #EFEFEF; border-radius: 4px; display: flex; flex-direction: column; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.chat-placeholder { font-size: 13px; color: #CCC; text-align: center; margin: auto; }

.chat-msg { display: flex; flex-direction: column; gap: 4px; max-width: 70%; }
.chat-msg--user { align-self: flex-end; }
.chat-msg--agent { align-self: flex-start; }

.chat-msg-label { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: #AAA; }

.chat-msg-text {
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
}

.chat-msg--user .chat-msg-text { background: #000; color: #fff; border-radius: 4px 4px 2px 4px; }
.chat-msg--agent .chat-msg-text { background: #F5F5F5; color: #000; border-radius: 4px 4px 4px 2px; }

.chat-thinking {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 12px 14px;
}

.chat-thinking span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #999;
  animation: bounce 1s infinite;
}

.chat-thinking span:nth-child(2) { animation-delay: 0.2s; }
.chat-thinking span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); opacity: 0.5; }
  50% { transform: translateY(-4px); opacity: 1; }
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #EFEFEF;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  resize: none;
  line-height: 1.4;
  transition: border-color 0.15s;
}

.chat-input:focus { outline: none; border-color: #000; }

.chat-send-btn {
  padding: 10px 14px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.chat-send-btn:hover { background: #222; }
.chat-send-btn:disabled { background: #CCC; cursor: not-allowed; }

/* ── Horizon buttons ─────────────────────────────────────────────────────── */
.horizon-btns { display: flex; flex-wrap: wrap; gap: 8px; }

.horizon-btn {
  padding: 7px 14px;
  border: 1.5px solid #E8E8E8;
  border-radius: 3px;
  background: #fff;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: #444;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.horizon-btn.is-active {
  border-color: #000;
  background: #FAFAFA;
  color: #000;
  font-weight: 600;
}

/* ── Agent counts block ──────────────────────────────────────────────────── */
.agent-counts-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.agent-count-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-count-label {
  min-width: 130px;
  font-size: 11px;
  font-weight: 500;
  color: #444;
  flex-shrink: 0;
}

.agent-count-sep {
  flex: 1;
  height: 1px;
  background: #E8E8E8;
}

.agent-count-input {
  width: 64px;
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 4px 8px;
  font-size: 12px;
  font-family: inherit;
  color: #000;
  text-align: right;
  background: #fff;
  flex-shrink: 0;
}

.agent-count-input:focus { outline: none; border-color: #000; }

.agent-count-total {
  font-size: 11px;
  font-weight: 700;
  color: #555;
  letter-spacing: 0.04em;
  text-align: right;
  margin-top: 4px;
}

/* ── Mono utility ────────────────────────────────────────────────────────── */
.mono { font-family: 'JetBrains Mono', monospace; }
</style>
