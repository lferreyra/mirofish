<template>
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
          @click="$emit('stop')"
        >
          Stop Simulation
        </button>
        <button
          v-if="simStatus?.runner_status === 'completed' || simStatus?.runner_status === 'stopped'"
          class="btn-primary"
          @click="$emit('report')"
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
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import { ACTION_COLORS } from '../../constants/private.js'
import { shortTime, actionTypeClass, nodeColor } from '../../utils/private.js'

const props = defineProps({
  simStatus: { type: Object, default: null },
  recentActions: { type: Array, default: () => [] },
})

defineEmits(['stop', 'report'])

const graphContainer = ref(null)
const feedPanel = ref(null)

let simulation = null
let svgEl = null
let linkGroup = null
let nodeGroup = null

const roundProgress = computed(() => {
  if (props.simStatus?.progress_percent != null) return props.simStatus.progress_percent
  const total = props.simStatus?.private_total_rounds || 0
  const current = props.simStatus?.private_current_round || 0
  if (!total) return 0
  return Math.round((current / total) * 100)
})

const actionTypeCounts = computed(() => {
  const counts = {}
  for (const action of props.recentActions) {
    counts[action.action_type] = (counts[action.action_type] || 0) + 1
  }
  return counts
})

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

  const staticAgents = props.simStatus?.agents || []
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

  const staticEdges = props.simStatus?.relational_edges || []
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
    .attr('fill', d => nodeColor(d.dominant, ACTION_COLORS))
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5)
  nodeMerge.select('text')
    .text(d => d.name.slice(0, 12))
}

onMounted(async () => {
  await nextTick()
  initGraph()
  updateGraph(props.recentActions || [])
})

onUnmounted(() => {
  if (simulation) simulation.stop()
})

watch(() => props.recentActions.length, () => {
  nextTick(() => {
    if (feedPanel.value) feedPanel.value.scrollTop = feedPanel.value.scrollHeight
  })
  updateGraph(props.recentActions)
})

watch(
  () => (props.simStatus?.agents?.length || 0) + (props.simStatus?.relational_edges?.length || 0),
  () => updateGraph(props.recentActions || [])
)
</script>

<style scoped>
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

.mono { font-family: 'JetBrains Mono', monospace; }
</style>
