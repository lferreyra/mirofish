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
                  <span class="checkbox-label">{{ t }}</span>
                </label>
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">TEMPORAL HORIZON — {{ form.horizonDays }} days</label>
              <div class="slider-group">
                <input
                  type="range"
                  class="field-slider"
                  v-model.number="form.horizonDays"
                  min="7" max="90" step="1"
                />
                <div class="slider-ticks">
                  <span>7d</span><span>30d</span><span>60d</span><span>90d</span>
                </div>
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
            :disabled="!form.decisionText.trim() || form.relationalTypes.length === 0"
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

        <!-- Right: Live action feed -->
        <div class="run-feed-panel" ref="feedPanel">
          <div class="feed-header">LIVE ACTION FEED</div>
          <div class="feed-list">
            <div
              v-for="(action, idx) in recentActions"
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

          <h2 class="report-title">{{ reportResult.title }}</h2>
          <p class="report-summary">{{ reportResult.summary }}</p>

          <div class="report-sections" v-if="reportResult.sections">
            <div v-for="(section, idx) in reportResult.sections" :key="idx" class="report-section">
              <div class="rs-header" @click="toggleSection(idx)">
                <span class="rs-num">{{ String(idx + 1).padStart(2, '0') }}</span>
                <span class="rs-title">{{ section.title }}</span>
                <svg class="rs-chevron" :class="{ 'is-open': !collapsedSections.has(idx) }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </div>
              <div v-show="!collapsedSections.has(idx)" class="rs-body">
                <p>{{ section.content }}</p>
              </div>
            </div>
          </div>

          <div class="result-actions">
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
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { getProject } from '../api/graph.js'
import { interviewAgents } from '../api/simulation.js'
import { getReportStatus, getReport } from '../api/report.js'
import {
  preparePrivateSimulation,
  startPrivateSimulation,
  getPrivateStatus,
  stopPrivateSimulation,
  getPrivateActions,
  generatePrivateReport,
} from '../api/private.js'

const props = defineProps({
  projectId: { type: String, required: true },
})

const router = useRouter()

// ── Constants ──────────────────────────────────────────────────────────────

const RELATIONAL_TYPES = [
  'employee', 'manager', 'client', 'competitor',
  'partner', 'familymember', 'colleague', 'investor',
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

// Step 3 - live feed
const recentActions = ref([])
const feedPanel = ref(null)
let pollingTimer = null

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
  relationalTypes: ['employee', 'manager', 'client', 'partner', 'familymember'],
  horizonDays: 30,
  questionsToMeasure: '',
})

// ── Computed ───────────────────────────────────────────────────────────────

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
  const total = simStatus.value?.total_rounds || 0
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

// ── Data loading ───────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const res = await getProject(props.projectId)
    projectData.value = res.data
  } catch (e) {
    error.value = `Could not load project: ${e.message}`
  }
})

onUnmounted(() => {
  stopPolling()
  stopReportPolling()
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
    startReportPolling(reportId)
  } catch (e) {
    error.value = `Report trigger failed: ${e.message}`
    isLoading.value = false
  }
}

const startReportPolling = (reportId) => {
  reportPollingTimer = setInterval(() => pollReport(reportId), 4000)
  pollReport(reportId)
}

const stopReportPolling = () => {
  if (reportPollingTimer) { clearInterval(reportPollingTimer); reportPollingTimer = null }
}

const pollReport = async (reportId) => {
  try {
    const res = await getReportStatus(reportId)
    const status = res.data?.status
    reportProgress.value = res.data?.message || 'Generating…'

    if (status === 'completed') {
      stopReportPolling()
      const fullRes = await getReport(reportId)
      reportResult.value = fullRes.data
      isLoading.value = false
    } else if (status === 'failed') {
      stopReportPolling()
      error.value = `Report failed: ${res.data?.error}`
      isLoading.value = false
    }
  } catch (e) {
    console.error('Report poll error:', e)
  }
}

// ── Step 5: Interaction ────────────────────────────────────────────────────

watch(() => currentStep.value, async (step) => {
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

    const res = await interviewAgents({
      simulation_id: simId.value,
      agent_ids: [selectedAgentId.value],
      prompt: userMsg,
      chat_history: history,
    })
    const reply = res.data?.[0]?.response || res.data?.response || '(no response)'
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

// Auto-scroll feed
watch(() => recentActions.value.length, () => {
  nextTick(() => {
    if (feedPanel.value) feedPanel.value.scrollTop = feedPanel.value.scrollHeight
  })
})
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

/* ── Feed panel (step 3 right) ───────────────────────────────────────────── */
.run-feed-panel {
  border: 1.5px solid #EFEFEF;
  border-radius: 4px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
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
.report-title { font-size: 22px; font-weight: 700; color: #000; line-height: 1.3; }
.report-summary { font-size: 14px; color: #555; line-height: 1.6; }

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

/* ── Mono utility ────────────────────────────────────────────────────────── */
.mono { font-family: 'JetBrains Mono', monospace; }
</style>
