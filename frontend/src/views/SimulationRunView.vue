<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'
import { usePolling } from '../composables/usePolling'
import { useToast } from '../composables/useToast'

const route  = useRoute()
const router = useRouter()
const toast  = useToast()

const status = ref({
  current_round: 0, total_rounds: 0, progress_percent: 0,
  runner_status: null, project_id: null,
  twitter_actions_count: 0, reddit_actions_count: 0, total_actions_count: 0,
  twitter_running: false, reddit_running: false,
  twitter_completed: false, reddit_completed: false,
  report_id: null, error: null,
})

const concluida        = ref(false)
const showCusto        = ref(false)

// Custo estimado da operação
const custoEstimado = computed(() => {
  const agentes = Object.keys(realAgentMap.value).length || status.value.total_agents || 20
  const rodadas = status.value.total_rounds || 12
  const episodios = Math.round(agentes * 8.65) // ~8.65 episódios por agente no Zep
  const zepUSD = episodios * 0.00625 // $25 / 4000 episódios
  const zepBRL = zepUSD * 5.5
  const openaiCalls = agentes + 10 // perfis + config + report
  const openaiBRL = openaiCalls * 0.03 // ~R$0.03 por call GPT-4o-mini
  const total = zepBRL + openaiBRL
  return {
    episodios,
    zepBRL: zepBRL.toFixed(2),
    openaiBRL: openaiBRL.toFixed(2),
    total: total.toFixed(2),
    agentes,
    rodadas
  }
})
const parada           = ref(false)
const erroExec         = ref('')
const parando          = ref(false)
const erroCount        = ref(0)
const gerandoRelatorio = ref(false)
const reportTaskId     = ref(null)
const reportPollTimer  = ref(null)

// Histórico local acumulado por poll
const roundHistory = ref([])
const lastRound    = ref(0)
const eventLog     = ref([])
const realActions  = ref([])
const realAgentMap = ref({})

const simStatus    = computed(() => status.value.runner_status)
const temRelatorio = computed(() => !!status.value.report_id)

const progresso = computed(() => {
  if (status.value.progress_percent > 0) return Math.round(status.value.progress_percent)
  if (status.value.total_rounds > 0 && status.value.current_round > 0)
    return Math.round((status.value.current_round / status.value.total_rounds) * 100)
  return 0
})

const pageTitle = computed(() => {
  if (concluida.value) return '✅ Simulação Concluída'
  if (parada.value)    return '⏸ Simulação Parada'
  if (erroExec.value)  return '❌ Erro na Execução'
  return '⏳ Execução ao vivo'
})

// Métricas derivadas
const totalAcoes = computed(() => Math.max(status.value.total_actions_count, 1))

const consenso = computed(() => {
  const twR  = status.value.twitter_actions_count / totalAcoes.value
  const prog = progresso.value
  return Math.min(99, Math.max(0, Math.round(twR * 65 + prog * 0.32 + 8)))
})
const inovacao = computed(() => {
  const rdR  = status.value.reddit_actions_count / totalAcoes.value
  const prog = progresso.value
  return Math.min(99, Math.max(0, Math.round(rdR * 80 + prog * 0.28 + 15)))
})
const tensao = computed(() => {
  const prog = progresso.value
  return Math.max(5, Math.round(52 - prog * 0.38 + Math.sin(prog * 0.1) * 6))
})

// SVG gauge arc
function gaugePath(pct, r = 36, cx = 50, cy = 56) {
  const start = Math.PI
  const end   = Math.PI + (pct / 100) * Math.PI
  const large = pct > 50 ? 1 : 0
  const sx = cx + r * Math.cos(start)
  const sy = cy + r * Math.sin(start)
  const ex = cx + r * Math.cos(end)
  const ey = cy + r * Math.sin(end)
  return `M ${sx.toFixed(1)} ${sy.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${ex.toFixed(1)} ${ey.toFixed(1)}`
}

// Gráfico de evolução
const CW = 400; const CH = 140
const cp = { t: 12, r: 10, b: 26, l: 30 }

const evoChart = computed(() => {
  const h = roundHistory.value
  if (h.length < 2) return null
  const n  = h.length
  const w  = CW - cp.l - cp.r
  const ht = CH - cp.t - cp.b
  const x  = i => cp.l + (i / Math.max(n - 1, 1)) * w
  const y  = v => cp.t + ht - (v / 100) * ht
  const path = fn => h.map((p, i) => `${i===0?'M':'L'}${x(i).toFixed(1)},${y(fn(p)).toFixed(1)}`).join(' ')
  const labels = h.filter((_, i) => i % Math.max(Math.floor(n / 6), 1) === 0)
    .map(p => ({ r: p.r, x: x(h.indexOf(p)) }))
  return {
    c:   path(p => p.c),
    iv:  path(p => p.iv),
    ts:  path(p => p.ts),
    labels,
    yLines: [0, 25, 50, 75, 100].map(v => ({ v, y: y(v) }))
  }
})

// Rede de agentes (layout radial)
const NET = 190
const agentNodes = computed(() => {
  const map = realAgentMap.value
  const names = Object.keys(map)
  
  // Se não tem dados reais ainda, gerar placeholder baseado no progresso
  if (names.length === 0) {
    const count = Math.max(8, Math.min(30, status.value.total_entities || 14))
    const prog = progresso.value
    return Array.from({ length: count }, (_, i) => {
      const angle = (i / count) * 2 * Math.PI
      const r = 35 + (i % 3) * 20
      const roles = ['inovador', 'conservador', 'mediador', 'lider', 'opositor']
      return {
        x: NET / 2 + r * Math.cos(angle) + Math.sin(i * 17) * 6,
        y: NET / 2 + r * Math.sin(angle) + Math.cos(i * 13) * 5,
        role: roles[i % roles.length],
        active: i <= Math.floor((prog / 100) * count) + 2,
        size: 3.5 + (i % 3) * 0.8,
        name: '',
      }
    })
  }
  
  // Rede REAL baseada em dados de interação
  const maxActions = Math.max(...Object.values(map).map(a => a.actions), 1)
  return names.map((id, i) => {
    const agent = map[id]
    const angle = (i / names.length) * 2 * Math.PI
    const r = 30 + Math.min(agent.actions / maxActions, 1) * 50
    // Classificar por tipo dominante de ação
    const types = agent.types || {}
    let role = 'mediador'
    if ((types.CREATE_POST || 0) > (types.LIKE_POST || 0)) role = 'lider'
    else if ((types.LIKE_POST || 0) > 3) role = 'conservador'
    if ((types.REPOST || 0) > 2) role = 'inovador'
    if ((types.CREATE_COMMENT || 0) > 2) role = 'opositor'
    
    return {
      x: NET / 2 + r * Math.cos(angle),
      y: NET / 2 + r * Math.sin(angle),
      role,
      active: true,
      size: 3 + (agent.actions / maxActions) * 5,
      name: (agent.name || '').split(' ')[0],
      agentId: id,
    }
  })
})

const netEdges = computed(() => {
  const actions = realActions.value
  const nodes = agentNodes.value
  
  // Se não tem dados reais, usar proximidade
  if (!actions.length || !Object.keys(realAgentMap.value).length) {
    const edges = []
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y
        if (Math.sqrt(dx*dx + dy*dy) < 55 && edges.length < 20) {
          edges.push({ x1: nodes[i].x, y1: nodes[i].y, x2: nodes[j].x, y2: nodes[j].y, w: 1 })
        }
      }
    }
    return edges
  }
  
  // Edges REAIS: interações entre agentes
  const interactions = {}
  actions.forEach(a => {
    // LIKE_POST e CREATE_COMMENT implicam interação com o autor do post
    if (['LIKE_POST','REPOST','CREATE_COMMENT','LIKE_COMMENT'].includes(a.action_type) && a.action_args?.target_agent_id !== undefined) {
      const key = [a.agent_id, a.action_args.target_agent_id].sort().join('-')
      interactions[key] = (interactions[key] || 0) + 1
    }
  })
  
  // Mapear agent_id → node index
  const idToIdx = {}
  Object.keys(realAgentMap.value).forEach((id, i) => { idToIdx[id] = i })
  
  const edges = []
  Object.entries(interactions).forEach(([key, count]) => {
    const [a, b] = key.split('-')
    const ni = nodes[idToIdx[a]], nj = nodes[idToIdx[b]]
    if (ni && nj) {
      edges.push({ x1: ni.x, y1: ni.y, x2: nj.x, y2: nj.y, w: Math.min(count, 4) })
    }
  })
  
  // Se não encontrou edges por target, usar co-ocorrência na mesma rodada
  if (edges.length < 3) {
    const roundAgents = {}
    actions.forEach(a => {
      if (!roundAgents[a.round_num]) roundAgents[a.round_num] = new Set()
      roundAgents[a.round_num].add(a.agent_id ?? a.agent_name)
    })
    Object.values(roundAgents).forEach(agentSet => {
      const arr = [...agentSet]
      for (let i = 0; i < arr.length && edges.length < 30; i++) {
        for (let j = i + 1; j < arr.length && edges.length < 30; j++) {
          const ni = nodes[idToIdx[arr[i]]], nj = nodes[idToIdx[arr[j]]]
          if (ni && nj && !edges.some(e => e.x1===ni.x && e.y1===ni.y && e.x2===nj.x && e.y2===nj.y)) {
            edges.push({ x1: ni.x, y1: ni.y, x2: nj.x, y2: nj.y, w: 1 })
          }
        }
      }
    })
  }
  
  return edges.slice(0, 40)
})

const ROLE_COLORS = { inovador: '#00e5c3', conservador: '#7c6ff7', mediador: '#f5a623', lider: '#1da1f2', opositor: '#ff5a5a' }

const eventsFeed = computed(() => [...eventLog.value].reverse().slice(0, 8))

// Polling
async function carregarStatus() {
  try {
    const res = await service.get(`/api/simulation/${route.params.simulationId}/run-status`)
    const raw = res?.data?.data || res?.data || res
    status.value = { ...status.value, ...raw }

    const s = simStatus.value

    if (raw.current_round > lastRound.value) {
      lastRound.value = raw.current_round
      roundHistory.value.push({
        r: raw.current_round,
        tw: raw.twitter_actions_count,
        rd: raw.reddit_actions_count,
        tot: raw.total_actions_count,
        c:  consenso.value,
        iv: inovacao.value,
        ts: tensao.value,
      })
      // Carregar ações reais da rodada
      try {
        const dRes = await service.get(`/api/simulation/${route.params.simulationId}/run-status/detail`)
        const dRaw = dRes?.data?.data || dRes?.data || {}
        const actions = dRaw?.all_actions || dRaw?.twitter_actions || []
        realActions.value = actions

        // Construir mapa de agentes reais
        const agMap = {}
        actions.forEach(a => {
          const id = a.agent_id ?? a.agent_name
          if (!agMap[id]) agMap[id] = { name: a.agent_name || `Agente ${a.agent_id}`, actions: 0, types: {} }
          agMap[id].actions++
          agMap[id].types[a.action_type] = (agMap[id].types[a.action_type] || 0) + 1
        })
        realAgentMap.value = agMap

        // Gerar feed de eventos reais (últimos da rodada)
        const roundActions = actions.filter(a => a.round_num === raw.current_round).slice(-3)
        roundActions.forEach(a => {
          const tipoLabel = {
            'CREATE_POST': 'publicou um post',
            'LIKE_POST': 'curtiu um post',
            'REPOST': 'repostou conteúdo',
            'FOLLOW': 'seguiu alguém',
            'CREATE_COMMENT': 'comentou em um post',
            'LIKE_COMMENT': 'curtiu um comentário',
          }[a.action_type] || a.action_type
          eventLog.value.push({
            round: a.round_num,
            platform: a.platform === 'twitter' ? 'Twitter' : 'Reddit',
            agent: a.agent_name || `Agente ${a.agent_id}`,
            acao: tipoLabel,
            time: new Date().toLocaleTimeString('pt-BR', { hour:'2-digit', minute:'2-digit' })
          })
        })
      } catch { /* detail é opcional */ }
    }

    if ((s === 'completed' || s === 'finished') && !concluida.value) {
      concluida.value = true; poll.stop()
      toast.success('🎉 Simulação concluída! Gerando relatório...', 5000)
      await iniciarGeracaoRelatorio()
    } else if ((s === 'stopped' || s === 'paused') && !parada.value) {
      parada.value = true; poll.stop()
      toast.warn('Simulação interrompida na rodada ' + raw.current_round)
    } else if (s === 'failed' && !erroExec.value) {
      erroExec.value = raw.error || 'A simulação falhou.'
      poll.stop(); toast.error('Erro na execução da simulação')
    }
    erroCount.value = 0
  } catch {
    erroCount.value++
    if (erroCount.value >= 5) {
      erroExec.value = 'Não foi possível conectar ao servidor.'
      poll.stop()
    }
  }
}

async function iniciarGeracaoRelatorio() {
  try {
    const check = await service.get(`/api/report/by-simulation/${route.params.simulationId}`)
    const d = check?.data?.data || check?.data || check
    if (d?.report_id) { status.value.report_id = d.report_id; toast.success('📊 Relatório disponível!', 5000); return }
  } catch { /* não existe ainda */ }

  gerandoRelatorio.value = true
  try {
    const res  = await service.post('/api/report/generate', { simulation_id: route.params.simulationId })
    const data = res?.data?.data || res?.data || res
    reportTaskId.value = data.task_id || null
    if (data.report_id) { status.value.report_id = data.report_id; gerandoRelatorio.value = false; toast.success('📊 Relatório disponível!', 5000); return }
    pollRelatorio()
  } catch { gerandoRelatorio.value = false; toast.error('Não foi possível gerar o relatório.') }
}

function pollRelatorio() {
  let tentativas = 0
  reportPollTimer.value = setInterval(async () => {
    tentativas++
    if (tentativas > 60) { clearInterval(reportPollTimer.value); gerandoRelatorio.value = false; toast.warn('Relatório demorando. Tente pelo projeto.'); return }
    try {
      const payload = { simulation_id: route.params.simulationId }
      if (reportTaskId.value) payload.task_id = reportTaskId.value
      const res = await service.post('/api/report/generate/status', payload)
      const d   = res?.data?.data || res?.data || res
      if (d.status === 'completed' || d.report_id) {
        clearInterval(reportPollTimer.value); gerandoRelatorio.value = false
        if (d.report_id) { status.value.report_id = d.report_id }
        else {
          try {
            const c = await service.get(`/api/report/by-simulation/${route.params.simulationId}`)
            const cd = c?.data?.data || c?.data || c
            if (cd?.report_id) status.value.report_id = cd.report_id
          } catch { /* ignorar */ }
        }
        if (status.value.report_id) toast.success('📊 Relatório pronto!', 8000)
      } else if (d.status === 'failed') { clearInterval(reportPollTimer.value); gerandoRelatorio.value = false; toast.error('Falha ao gerar relatório.') }
    } catch { /* ignorar */ }
  }, 5000)
}

async function pararSimulacao() {
  parando.value = true
  try {
    await service.post('/api/simulation/stop', { simulation_id: route.params.simulationId })
    parada.value = true; poll.stop()
    toast.warn('Simulação pausada na rodada ' + status.value.current_round)
  } catch { toast.error('Não foi possível pausar.') } finally { parando.value = false }
}

function verRelatorio() { if (temRelatorio.value) router.push(`/relatorio/${status.value.report_id}`) }

function voltarProjeto() {
  const pid = status.value.project_id
  router.push(pid ? `/projeto/${pid}` : '/')
}

const poll = usePolling(carregarStatus, 5000)

async function carregarProjectId() {
  try {
    const res = await service.get('/api/simulation/list', { params: { limit: 500 } })
    const raw = res?.data?.data || res?.data || res
    const lista = Array.isArray(raw) ? raw : (raw?.simulations || raw?.data || [])
    const sim = lista.find(s => s.simulation_id === route.params.simulationId)
    if (sim?.project_id) status.value.project_id = sim.project_id
  } catch { /* ignorar */ }
}

onMounted(async () => {
  carregarProjectId()
  poll.start()
  // Carregar dados retroativos se simulação já concluída
  try {
    const res = await service.get(`/api/simulation/${route.params.simulationId}/run-status`)
    const raw = res?.data?.data || res?.data || {}
    const s = (raw.status || '').toLowerCase()
    if (s === 'completed' || s === 'finished') {
      try {
        const aRes = await service.get(`/api/analytics/${route.params.simulationId}`)
        const ana = aRes?.data?.data || aRes?.data || {}
        const twR = ana?.twitter?.rounds || []
        const rdR = ana?.reddit?.rounds || []
        const byRound = {}
        ;[...twR, ...rdR].forEach(r => {
          const rn = r.round_num ?? r.round ?? 0
          if (!byRound[rn]) byRound[rn] = { tw: 0, rd: 0 }
          if (r.platform === 'twitter') byRound[rn].tw += (r.actions || r.count || 1)
          else byRound[rn].rd += (r.actions || r.count || 1)
        })
        const rounds = Object.keys(byRound).map(Number).sort((a,b) => a - b)
        if (rounds.length > 1 && roundHistory.value.length <= 1) {
          roundHistory.value = rounds.map(r => ({
            r, tw: byRound[r].tw, rd: byRound[r].rd,
            tot: byRound[r].tw + byRound[r].rd,
            c: 80, iv: 70, ts: 15
          }))
          lastRound.value = rounds[rounds.length - 1]
        }
      } catch {}
    }
  } catch {}
})
onUnmounted(() => { if (reportPollTimer.value) clearInterval(reportPollTimer.value) })
</script>

<template>
  <AppShell :title="pageTitle">
    <template #actions>
      <div class="round-badge">Rodada {{ status.current_round }}/{{ status.total_rounds || '?' }}</div>
      <AugurButton v-if="!concluida && !parada && !erroExec" variant="ghost" :disabled="parando" @click="pararSimulacao">
        {{ parando ? 'Parando...' : '⏸ Pausar' }}
      </AugurButton>
      <AugurButton v-if="temRelatorio" @click="verRelatorio">📊 Ver Relatório</AugurButton>
      <div v-else-if="gerandoRelatorio" class="gerando-tag"><div class="mspin"></div>Gerando relatório...</div>
      <AugurButton variant="ghost" @click="voltarProjeto">← Projeto</AugurButton>
    </template>

    <!-- Banners -->
    <Transition name="sd">
      <div v-if="concluida" class="banner banner-done">
        <span class="bi">🎉</span>
        <div class="bb"><div class="bt">Simulação concluída!</div><div class="bs" v-if="temRelatorio">Relatório pronto.</div><div class="bs" v-else-if="gerandoRelatorio">Gerando relatório...</div></div>
        <div class="banner-actions">
          <button class="btn-sec" @click="router.push(`/simulacao/${route.params.simulationId}/agentes`)">🧠 Agentes</button>
          <button class="btn-sec" @click="router.push(`/simulacao/${route.params.simulationId}/influentes`)">👑 Influentes</button>
          <button class="btn-sec" @click="router.push(`/simulacao/${route.params.simulationId}/posts`)">📝 Posts</button>
          <button v-if="temRelatorio" class="btn-rel" @click="verRelatorio">📊 Ver Relatório →</button>
          <div v-else-if="gerandoRelatorio" class="gerando-tag"><div class="mspin"></div></div>
          <button v-else class="btn-g" @click="voltarProjeto">← Projeto</button>
        </div>
      </div>
    </Transition>
    <Transition name="sd">
      <div v-if="parada && !concluida" class="banner banner-paused">
        <span class="bi">⏸</span>
        <div class="bb"><div class="bt">Simulação pausada</div><div class="bs">Rodada {{ status.current_round }}/{{ status.total_rounds }}.</div></div>
        <button class="btn-g" @click="voltarProjeto">← Projeto</button>
      </div>
    </Transition>
    <Transition name="sd">
      <div v-if="erroExec" class="banner banner-error">
        <span class="bi">⚠️</span>
        <div class="bb"><div class="bt">Erro na execução</div><div class="bs">{{ erroExec }}</div></div>
        <button class="btn-g" @click="voltarProjeto">← Projeto</button>
      </div>
    </Transition>

    <!-- KPI Top -->
    <div class="kpi-top">
      <div class="kpi-blk">
        <div class="kpi-n">{{ status.total_rounds || '—' }}</div>
        <div class="kpi-l">Rodadas</div>
      </div>
      <div class="kpi-d"></div>
      <div class="kpi-blk">
        <div class="kpi-n">{{ status.total_actions_count }}</div>
        <div class="kpi-l">Interações</div>
      </div>
      <div class="kpi-d"></div>
      <div class="kpi-blk kpi-hl">
        <div class="kpi-n" style="color:var(--accent)">{{ consenso }}%</div>
        <div class="kpi-l">Consenso</div>
      </div>
      <div class="kpi-d"></div>
      <div class="kpi-blk">
        <div class="kpi-n" style="color:#f5a623">{{ progresso }}%</div>
        <div class="kpi-l">Progresso</div>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="mgrid">

      <!-- Gauges -->
      <div class="cg">
        <div class="st">MÉTRICAS ATUAIS</div>

        <div class="gauge-item">
          <svg viewBox="0 0 100 72" class="gsv">
            <defs><linearGradient id="gc" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#00b89c"/><stop offset="100%" stop-color="#00e5c3"/>
            </linearGradient></defs>
            <path d="M 14 56 A 36 36 0 0 1 86 56" fill="none" stroke="rgba(0,229,195,0.1)" stroke-width="10" stroke-linecap="round"/>
            <path :d="gaugePath(consenso)" fill="none" stroke="url(#gc)" stroke-width="10" stroke-linecap="round"/>
            <text x="50" y="50" text-anchor="middle" font-size="20" font-weight="800" fill="#00e5c3" font-family="monospace">{{ consenso }}%</text>
          </svg>
          <div class="glbl">Consenso</div>
        </div>

        <div class="gauge-item">
          <svg viewBox="0 0 100 72" class="gsv">
            <defs><linearGradient id="gi" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#5046a8"/><stop offset="100%" stop-color="#7c6ff7"/>
            </linearGradient></defs>
            <path d="M 14 56 A 36 36 0 0 1 86 56" fill="none" stroke="rgba(124,111,247,0.1)" stroke-width="10" stroke-linecap="round"/>
            <path :d="gaugePath(inovacao)" fill="none" stroke="url(#gi)" stroke-width="10" stroke-linecap="round"/>
            <text x="50" y="50" text-anchor="middle" font-size="20" font-weight="800" fill="#7c6ff7" font-family="monospace">{{ inovacao }}%</text>
          </svg>
          <div class="glbl">Inovação</div>
        </div>

        <div class="gauge-item">
          <svg viewBox="0 0 100 72" class="gsv">
            <defs><linearGradient id="gt" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stop-color="#cc2222"/><stop offset="100%" stop-color="#ff5a5a"/>
            </linearGradient></defs>
            <path d="M 14 56 A 36 36 0 0 1 86 56" fill="none" stroke="rgba(255,90,90,0.1)" stroke-width="10" stroke-linecap="round"/>
            <path :d="gaugePath(tensao)" fill="none" stroke="url(#gt)" stroke-width="10" stroke-linecap="round"/>
            <text x="50" y="50" text-anchor="middle" font-size="20" font-weight="800" fill="#ff5a5a" font-family="monospace">{{ tensao }}%</text>
          </svg>
          <div class="glbl">Tensão Social</div>
        </div>
      </div>

      <!-- Evolução -->
      <div class="cc">
        <div class="st-row">
          <span class="st">EVOLUÇÃO POR RODADA</span>
          <div class="evo-leg">
            <span style="color:#00e5c3;font-size:11px;font-weight:600">— Consenso</span>
            <span style="color:#7c6ff7;font-size:11px;font-weight:600">— Inovação</span>
            <span style="color:#ff5a5a;font-size:11px;font-weight:600">— Tensão</span>
          </div>
        </div>

        <div class="prog-line">
          <div class="prog-b"><div class="prog-f" :class="{'pf-run':!concluida&&!parada,'pf-done':concluida}" :style="{width:progresso+'%'}"></div></div>
          <span class="prog-p">{{ progresso }}%</span>
        </div>

        <div class="round-st">
          <span v-if="concluida" style="color:var(--accent)">✅ Concluída</span>
          <span v-else-if="parada" style="color:#f5a623">⏸ Pausada na R{{ status.current_round }}</span>
          <span v-else style="color:var(--text-secondary)">▶ R{{ status.current_round }}/{{ status.total_rounds||'?' }}</span>
        </div>

        <!-- Chart -->
        <div class="chart-box">
          <div v-if="!evoChart" class="chart-ph">
            <template v-if="!concluida"><div class="mspin"></div><span>Aguardando dados das primeiras rodadas...</span></template><span v-else style="color:var(--text-secondary,#8888aa)">Dados nao disponiveis para esta simulacao.</span>
          </div>
          <svg v-else :viewBox="`0 0 ${CW} ${CH}`" class="chart-svg" preserveAspectRatio="xMidYMid meet">
            <g v-for="l in evoChart.yLines" :key="l.v">
              <line :x1="cp.l" :y1="l.y" :x2="CW-cp.r" :y2="l.y" stroke="rgba(0,0,0,0.08)" stroke-width="1" stroke-dasharray="3,3"/>
              <text :x="cp.l-4" :y="l.y+4" text-anchor="end" fill="rgba(0,0,0,0.3)" font-size="8">{{ l.v }}%</text>
            </g>
            <g v-for="lb in evoChart.labels" :key="lb.r">
              <text :x="lb.x" :y="CH-cp.b+14" text-anchor="middle" fill="rgba(0,0,0,0.3)" font-size="8">R{{ lb.r }}</text>
            </g>
            <path :d="evoChart.c"  fill="none" stroke="#00e5c3" stroke-width="2"   stroke-linejoin="round"/>
            <path :d="evoChart.iv" fill="none" stroke="#7c6ff7" stroke-width="2"   stroke-linejoin="round"/>
            <path :d="evoChart.ts" fill="none" stroke="#ff5a5a" stroke-width="1.5" stroke-linejoin="round" stroke-dasharray="4,2"/>
          </svg>
        </div>

        <!-- Quick stats -->
        <div class="qstats">
          <div class="qs"><div class="qv" style="color:#1da1f2">{{ status.twitter_actions_count }}</div><div class="ql">Twitter</div></div>
          <div class="qd"></div>
          <div class="qs"><div class="qv" style="color:#ff4500">{{ status.reddit_actions_count }}</div><div class="ql">Reddit</div></div>
          <div class="qd"></div>
          <div class="qs"><div class="qv">{{ roundHistory.length }}</div><div class="ql">Rodadas log</div></div>
        </div>
      </div>

      <!-- Rede + Feed -->
      <div class="cr">
        <div class="st">REDE DE AGENTES</div>
        <svg :viewBox="`0 0 ${NET} ${NET}`" class="net-svg" preserveAspectRatio="xMidYMid meet">
          <circle :cx="NET/2" :cy="NET/2" r="45" fill="none" stroke="rgba(0,0,0,0.06)"/>
          <circle :cx="NET/2" :cy="NET/2" r="75" fill="none" stroke="rgba(0,0,0,0.04)"/>
          <line v-for="(e,i) in netEdges" :key="'e'+i"
            :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
            :stroke-width="e.w || 1" stroke="rgba(0,0,0,0.12)" stroke-linecap="round"/>
          <g v-for="(n,i) in agentNodes" :key="'n'+i">
            <circle :cx="n.x" :cy="n.y" :r="n.size+2" :fill="ROLE_COLORS[n.role]" opacity="0.12"/>
            <circle :cx="n.x" :cy="n.y" :r="n.size"
              :fill="n.active ? ROLE_COLORS[n.role] : 'rgba(0,0,0,0.08)'"
              :opacity="n.active ? 0.95 : 0.3"
              :class="{'np': n.active && !concluida}"/>
            <text v-if="n.name" :x="n.x" :y="n.y + n.size + 8" text-anchor="middle"
              fill="var(--text-secondary)" font-size="4" font-weight="600" opacity="0.8">{{ n.name }}</text>
          </g>
        </svg>
        <div class="net-leg">
          <span v-for="(cor, r) in ROLE_COLORS" :key="r" :style="{color:cor}">● {{ r }}</span>
        </div>
        <div v-if="Object.keys(realAgentMap).length" class="net-info">
          {{ Object.keys(realAgentMap).length }} agentes · {{ realActions.length }} interações
        </div>

        <div class="feed-sep"></div>
        <div class="st">FEED DE EVENTOS</div>
        <div v-if="!eventsFeed.length" class="feed-ph"><template v-if="!concluida"><div class="mspin"></div><span>Aguardando rodadas...</span></template><span v-else style="color:var(--text-secondary,#8888aa)">Sem eventos registrados.</span></div>
        <div class="feed-list" v-else>
          <div v-for="(ev,i) in eventsFeed" :key="i" class="fi">
            <span class="fi-r">R{{ ev.round }}</span>
            <div class="fi-b">
              <span class="fi-a">{{ ev.agent }}</span>
              <span class="fi-t">{{ ev.acao }} <span :class="['fi-p', ev.platform==='Twitter'?'ptw':'prd']">{{ ev.platform }}</span></span>
            </div>
            <span class="fi-tm">{{ ev.time }}</span>
          </div>
        </div>
      </div>

    </div>

    <!-- CTA após conclusão -->
    <Transition name="pop">
      <div v-if="concluida" class="cta">
        <span style="font-size:26px">📊</span>
        <div style="flex:1"><div class="cta-t">{{ temRelatorio ? 'Análise pronta!' : 'Gerando análise...' }}</div><div class="cta-s">{{ temRelatorio ? 'Relatório com cenários, riscos e recomendações estratégicas.' : 'Processando dados...' }}</div></div>
        <button v-if="temRelatorio" class="btn-rel" @click="verRelatorio">Ver Relatório →</button>
        <div v-else class="mspin"></div>
      </div>
    </Transition>

    <!-- Cost toggle -->
    <button class="cost-toggle" @click="showCusto = !showCusto" title="Custo da operação">💰</button>
    <Transition name="fade">
      <div v-if="showCusto" class="cost-panel">
        <h4>💰 Custo Estimado</h4>
        <div class="cp-row"><span>Agentes</span><span>{{ custoEstimado.agentes }}</span></div>
        <div class="cp-row"><span>Rodadas</span><span>{{ custoEstimado.rodadas }}</span></div>
        <div class="cp-row"><span>Episódios Zep</span><span>{{ custoEstimado.episodios }}</span></div>
        <div class="cp-row"><span>Zep Cloud</span><span>R$ {{ custoEstimado.zepBRL }}</span></div>
        <div class="cp-row"><span>OpenAI</span><span>R$ {{ custoEstimado.openaiBRL }}</span></div>
        <div class="cp-row cp-total"><span>TOTAL</span><span>R$ {{ custoEstimado.total }}</span></div>
        <div class="cp-note">Estimativa baseada em ~8,65 episódios/agente (Zep $25/4k) + ~R$0,03/call OpenAI</div>
      </div>
    </Transition>
  </AppShell>
</template>

<style scoped>
/* Actions bar */
.round-badge { padding:5px 12px;border-radius:999px;background:var(--accent-dim);color:var(--accent);font-size:13px;font-weight:500;font-family:monospace; }
.gerando-tag { display:flex;align-items:center;gap:7px;font-size:12px;color:var(--text-muted); }
.btn-rel { background:var(--accent);color:#000;border:none;border-radius:8px;padding:7px 16px;font-size:13px;font-weight:700;cursor:pointer; }
.btn-rel:hover { opacity:.85; }
.btn-sec { background:none;border:1px solid var(--border-md);color:var(--accent2);border-radius:8px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s; }
.btn-sec:hover { background:var(--accent2-dim);border-color:var(--accent2); }
.banner-actions { display:flex;gap:8px;align-items:center; }
.btn-g { background:none;border:1px solid var(--border);color:var(--text-secondary);border-radius:8px;padding:6px 14px;font-size:13px;cursor:pointer; }

/* Banners */
.banner { display:flex;align-items:center;gap:14px;border-radius:12px;padding:13px 18px;margin-bottom:12px; }
.banner-done   { background:rgba(0,229,195,0.07);  border:1px solid rgba(0,229,195,0.22); }
.banner-paused { background:rgba(124,111,247,0.07); border:1px solid rgba(124,111,247,0.2); }
.banner-error  { background:rgba(255,90,90,0.07);   border:1px solid rgba(255,90,90,0.2); }
.bi { font-size:22px;flex-shrink:0; }
.bb { flex:1; }
.bt { font-size:14px;font-weight:600;color:var(--text-primary); }
.bs { font-size:12px;color:var(--text-secondary);margin-top:2px; }

/* KPI top */
.kpi-top { display:flex;align-items:stretch;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;overflow:hidden; }
.kpi-blk { flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:14px 10px;gap:4px; }
.kpi-hl  { background:rgba(0,229,195,0.04); }
.kpi-d   { width:1px;background:var(--border);margin:10px 0; }
.kpi-n   { font-size:26px;font-weight:900;color:var(--text-primary);font-family:monospace;line-height:1; }
.kpi-l   { font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px; }

/* Main grid */
.mgrid { display:grid;grid-template-columns:190px 1fr 210px;gap:12px;align-items:start; }

/* Shared */
.st { font-size:10px;font-weight:700;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase; }
.st-row { display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap; }

/* Gauges col */
.cg { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:12px;align-items:center; }
.gauge-item { display:flex;flex-direction:column;align-items:center;gap:2px;width:100%; }
.gsv { width:120px;height:auto; }
.glbl { font-size:11px;color:var(--text-secondary);font-weight:500;text-align:center; }

/* Center col */
.cc { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;gap:10px; }
.prog-line { display:flex;align-items:center;gap:10px; }
.prog-b { flex:1;height:6px;background:var(--bg-overlay);border-radius:3px;overflow:hidden; }
.prog-f { height:100%;border-radius:3px;transition:width .6s ease; }
.pf-run { background:linear-gradient(90deg,#00b89c,#00e5c3);animation:shim 2s infinite; }
.pf-done { background:var(--accent); }
/* Cost panel */
.cost-toggle { position:fixed;bottom:20px;right:20px;background:var(--accent2);color:#fff;border:none;width:42px;height:42px;border-radius:50%;font-size:18px;cursor:pointer;z-index:50;box-shadow:var(--shadow-md);transition:transform .15s; }
.cost-toggle:hover { transform:scale(1.1); }
.cost-panel { position:fixed;bottom:72px;right:20px;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px;width:260px;z-index:50;box-shadow:var(--shadow-lg); }
.cost-panel h4 { font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px; }
.cp-row { display:flex;justify-content:space-between;padding:4px 0;font-size:12px;color:var(--text-secondary); }
.cp-row span:last-child { font-weight:700;font-family:monospace;color:var(--text-primary); }
.cp-total { border-top:1px solid var(--border);margin-top:6px;padding-top:8px;font-weight:700;font-size:13px;color:var(--accent2); }
.cp-note { font-size:10px;color:var(--text-muted);margin-top:8px;line-height:1.4; }

.fade-enter-active,.fade-leave-active{transition:opacity .2s}.fade-enter-from,.fade-leave-to{opacity:0}
@keyframes shim { 0%,100%{opacity:1}50%{opacity:.7} }
.prog-p { font-size:12px;color:var(--text-muted);font-family:monospace;min-width:30px;text-align:right; }
.round-st { font-size:12px; }
.evo-leg { display:flex;gap:10px;flex-wrap:wrap; }

.chart-box { min-height:110px;display:flex;align-items:center;justify-content:center; }
.chart-svg { width:100%;height:auto;display:block; }
.chart-ph  { display:flex;align-items:center;gap:10px;color:var(--text-muted);font-size:11px; }

.qstats { display:flex;align-items:center;background:var(--bg-raised);border-radius:8px;overflow:hidden; }
.qs { flex:1;padding:7px 10px;text-align:center; }
.qv { font-size:15px;font-weight:700;color:var(--text-primary);font-family:monospace; }
.ql { font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px;margin-top:2px; }
.qd { width:1px;background:var(--border);margin:5px 0; }

/* Right col */
.cr { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:8px;overflow:hidden; }
.net-svg { width:100%;height:auto;display:block;max-height:150px; }
.net-leg { display:flex;flex-wrap:wrap;gap:4px 8px; }
.net-leg span { font-size:9px;font-weight:600;text-transform:capitalize; }
.net-info { font-size:9px;color:var(--text-muted);margin-top:4px;text-align:center; }
.np { animation:np 2.2s ease-in-out infinite; }
@keyframes np { 0%,100%{opacity:1}50%{opacity:.45} }
.feed-sep { height:1px;background:var(--border);margin:4px 0; }
.feed-ph  { display:flex;align-items:center;gap:8px;color:var(--text-muted);font-size:11px; }
.feed-list { display:flex;flex-direction:column;gap:5px;max-height:180px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border-md) transparent; }
.fi { display:flex;align-items:flex-start;gap:7px;padding:5px 0;border-bottom:1px solid var(--border);font-size:10px; }
.fi:last-child { border-bottom:none; }
.fi-r  { font-size:9px;font-weight:700;color:var(--accent2);background:var(--accent2-dim);border-radius:3px;padding:2px 5px;flex-shrink:0;font-family:monospace; }
.fi-b  { flex:1;display:flex;flex-direction:column;gap:1px; }
.fi-a  { font-weight:600;color:var(--text-primary);font-size:10px; }
.fi-t  { color:var(--text-muted);font-size:9px;line-height:1.4; }
.fi-p  { font-size:8px;font-weight:700;padding:1px 4px;border-radius:3px;margin-left:3px; }
.ptw { background:rgba(29,161,242,0.15);color:#1da1f2; }
.prd { background:rgba(255,69,0,0.15);color:#ff4500; }
.fi-tm { font-size:9px;color:var(--text-muted);font-family:monospace;flex-shrink:0; }

/* CTA */
.cta { display:flex;align-items:center;gap:14px;background:rgba(0,229,195,0.06);border:1px solid rgba(0,229,195,0.2);border-radius:12px;padding:14px 18px;margin-top:4px; }
.cta-t { font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:2px; }
.cta-s { font-size:11px;color:var(--text-muted); }

/* Spinner */
.mspin { width:13px;height:13px;border:2px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .8s linear infinite;flex-shrink:0; }
@keyframes sp { to{transform:rotate(360deg)} }

/* Transitions */
.sd-enter-active { transition:all .35s cubic-bezier(.34,1.56,.64,1); }
.sd-leave-active { transition:all .2s ease; }
.sd-enter-from,.sd-leave-to { opacity:0;transform:translateY(-10px) scale(.97); }
.pop-enter-active { transition:all .5s cubic-bezier(.34,1.56,.64,1); }
.pop-enter-from   { opacity:0;transform:scale(.93); }

/* Responsive */
@media (max-width:1100px) { .mgrid { grid-template-columns:160px 1fr 180px; } }
@media (max-width:900px) {
  .mgrid { grid-template-columns:1fr 1fr; }
  .cr { grid-column:1/-1; }
}
@media (max-width:600px) { .mgrid { grid-template-columns:1fr; } }
</style>
