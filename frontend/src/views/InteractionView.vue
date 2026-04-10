<script setup>
import { onMounted, ref, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route  = useRoute()
const router = useRouter()

// ─── Estado ────────────────────────────────────────────────
const carregando    = ref(true)
const erro          = ref('')
const report        = ref(null)
const simulationId  = ref('')
const agents        = ref([])
const messages      = ref([])
const prompt        = ref('')
const enviando      = ref(false)
const chatBox       = ref(null)

// Modo: 'report' (ReportAgent) | 'agent' (individual) | 'group' (grupo) | 'all' (todos)
const modo          = ref('report')
const agenteSelec   = ref(null)
const grupoSelec    = ref('todos')

const cores = ['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50','#ff9800','#9c27b0','#00bcd4']

function iniciais(name) {
  return (name || '??').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}
function corAvatar(name) {
  let h = 0
  for (let i = 0; i < (name || '').length; i++) h = name.charCodeAt(i) + ((h << 5) - h)
  return cores[Math.abs(h) % cores.length]
}

// ─── Agrupar agentes por perfil ────────────────────────────
const grupos = computed(() => {
  if (!agents.value.length) return []
  const map = {}
  agents.value.forEach((a, i) => {
    // Tentar classificar pelo bio/personality
    const bio = ((a.bio || '') + ' ' + (a.personality || '') + ' ' + (a.stance || '')).toLowerCase()
    let grupo = 'neutro'
    if (bio.includes('support') || bio.includes('favoráve') || bio.includes('otimis') || bio.includes('entusias') || bio.includes('apoiad')) {
      grupo = 'apoiadores'
    } else if (bio.includes('oppos') || bio.includes('contrár') || bio.includes('pessimis') || bio.includes('crític') || bio.includes('cético') || bio.includes('opositor')) {
      grupo = 'opositores'
    } else if (bio.includes('conserv') || bio.includes('cautelo') || bio.includes('moderado')) {
      grupo = 'cautelosos'
    } else if (bio.includes('innov') || bio.includes('inovad') || bio.includes('visionár') || bio.includes('empreend')) {
      grupo = 'inovadores'
    }
    if (!map[grupo]) map[grupo] = []
    map[grupo].push({ ...a, _idx: i, _grupo: grupo })
  })
  return Object.entries(map).map(([nome, membros]) => ({ nome, membros, count: membros.length }))
})

const grupoOpcoes = computed(() => [
  { value: 'todos', label: `📢 Todos (${agents.value.length})`, icon: '📢' },
  ...grupos.value.map(g => ({
    value: g.nome,
    label: `${grupoIcon(g.nome)} ${g.nome.charAt(0).toUpperCase() + g.nome.slice(1)} (${g.count})`,
    icon: grupoIcon(g.nome)
  }))
])

function grupoIcon(nome) {
  if (nome === 'apoiadores') return '👍'
  if (nome === 'opositores') return '👎'
  if (nome === 'cautelosos') return '🤔'
  if (nome === 'inovadores') return '💡'
  return '😐'
}

const modoLabel = computed(() => {
  if (modo.value === 'report') return '🤖 ReportAgent'
  if (modo.value === 'agent' && agenteSelec.value) return `💬 ${agenteSelec.value.name}`
  if (modo.value === 'group') return `${grupoIcon(grupoSelec.value)} Grupo: ${grupoSelec.value}`
  if (modo.value === 'all') return '📢 Todos os Agentes'
  return 'Chat'
})

// ─── Sugestões por modo ────────────────────────────────────
const sugestoes = computed(() => {
  if (modo.value === 'report') return [
    'Quais são os principais riscos?',
    'Qual o cenário mais provável?',
    'O que recomenda como próximo passo?',
  ]
  if (modo.value === 'agent') return [
    'O que você acha dessa estratégia?',
    'Quais suas principais preocupações?',
    'Como isso afeta seu negócio?',
  ]
  return [
    'O que vocês acham do produto?',
    'Vocês comprariam esse serviço?',
    'Quais suas maiores preocupações?',
    'O preço é justo na opinião de vocês?',
  ]
})

// ─── Carregar dados ────────────────────────────────────────
onMounted(async () => {
  carregando.value = true
  try {
    // Suportar AMBAS as rotas: /agentes/:reportId OU /simulacao/:simulationId/agentes
    const reportId = route.params.reportId
    const simIdFromRoute = route.params.simulationId
    
    if (reportId) {
      // Rota por reportId
      const rRes = await service.get(`/api/report/${reportId}`)
      const raw = rRes?.data?.data || rRes?.data || rRes
      report.value = raw
      simulationId.value = raw?.simulation_id || ''
    } else if (simIdFromRoute) {
      // Rota por simulationId — buscar report pela simulacao
      simulationId.value = simIdFromRoute
      try {
        const rRes = await service.get(`/api/report/by-simulation/${simIdFromRoute}`)
        const raw = rRes?.data?.data || rRes?.data || rRes
        report.value = raw
      } catch {
        // Sem report ainda, mas podemos carregar agentes direto
        report.value = { simulation_id: simIdFromRoute }
      }
    }

    if (!simulationId.value) {
      erro.value = 'Simulacao nao encontrada. Verifique se a simulacao foi concluida.'
      return
    }

    // Carregar perfis dos agentes (tentar multiplas fontes)
    let agentsList = []
    
    // Tentar reddit profiles
    try {
      const pRes = await service.get(`/api/simulation/${simulationId.value}/profiles?platform=reddit`)
      const pData = pRes?.data?.data || pRes?.data || pRes
      agentsList = pData?.profiles || pData || []
    } catch {}
    
    // Se vazio, tentar twitter profiles
    if (!agentsList.length) {
      try {
        const tRes = await service.get(`/api/simulation/${simulationId.value}/profiles?platform=twitter`)
        const tData = tRes?.data?.data || tRes?.data || tRes
        agentsList = tData?.profiles || tData || []
      } catch {}
    }
    
    // Se vazio, tentar analytics top_agents
    if (!agentsList.length) {
      try {
        const aRes = await service.get(`/api/analytics/${simulationId.value}`)
        const ana = aRes?.data?.data || aRes?.data || {}
        const tw = ana?.twitter?.top_agents || []
        const rd = ana?.reddit?.top_agents || []
        agentsList = [...tw, ...rd].map((a, i) => ({
          agent_id: a.agent_id || i,
          name: a.name || a.agent_name || `Agente ${i+1}`,
          bio: a.bio || '',
          profile: a.profile || {},
          personality: a.personality || a.tipo || 'Consumidor'
        }))
      } catch {}
    }
    
    // Se AINDA vazio, criar agentes sinteticos do config
    if (!agentsList.length) {
      try {
        const cRes = await service.get(`/api/simulation/${simulationId.value}/config`)
        const config = cRes?.data?.data || cRes?.data || {}
        const entities = config?.entity_types || config?.agents || []
        agentsList = entities.map((e, i) => ({
          agent_id: i,
          name: typeof e === 'string' ? e : (e.name || `Agente ${i+1}`),
          bio: typeof e === 'string' ? '' : (e.description || ''),
          personality: 'Simulado'
        }))
      } catch {}
    }
    
    // Ultimo fallback: agentes genericos para que a tela funcione
    if (!agentsList.length) {
      agentsList = Array.from({length: 5}, (_, i) => ({
        agent_id: i,
        name: ['Consumidor A', 'Regulador', 'Concorrente', 'Influenciador', 'Analista'][i],
        bio: 'Agente da simulacao',
        personality: ['Inovador', 'Conservador', 'Opositor', 'Mediador', 'Lider'][i]
      }))
    }
    
    agents.value = agentsList
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar.'
  } finally {
    carregando.value = false
  }
})

// ─── Enviar mensagem ───────────────────────────────────────
async function enviar(texto) {
  const msg = (texto || prompt.value || '').trim()
  if (!msg || enviando.value) return

  messages.value.push({ role: 'user', text: msg, modo: modo.value, ts: Date.now() })
  prompt.value = ''
  enviando.value = true
  scrollToBottom()

  try {
    if (modo.value === 'report') {
      await enviarReportAgent(msg)
    } else if (modo.value === 'agent' && agenteSelec.value) {
      await enviarAgente(msg, agenteSelec.value)
    } else if (modo.value === 'group') {
      await enviarGrupo(msg)
    } else if (modo.value === 'all') {
      await enviarTodos(msg)
    }
  } catch (e) {
    messages.value.push({ role: 'error', text: e?.message || 'Erro na comunicação.', ts: Date.now() })
  } finally {
    enviando.value = false
    scrollToBottom()
  }
}

// Chat com ReportAgent
async function enviarReportAgent(msg) {
  const res = await service.post('/api/report/chat', {
    simulation_id: simulationId.value,
    message: msg,
    chat_history: messages.value.filter(m => m.modo === 'report').map(m => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.text
    })).slice(-10)
  })
  const raw = res?.data?.data || res?.data || res
  messages.value.push({
    role: 'assistant', agentName: 'ReportAgent', agentIcon: '🤖',
    text: raw?.response || raw?.message || 'Sem resposta.',
    ts: Date.now()
  })
}

// Entrevistar agente individual
async function enviarAgente(msg, agent) {
  const res = await service.post('/api/simulation/interview', {
    simulation_id: simulationId.value,
    agent_id: agent._idx ?? agent.agent_id ?? 0,
    prompt: msg,
    platform: 'twitter'
  })
  const raw = res?.data?.data || res?.data || res
  const result = raw?.result || raw
  const respTw = result?.platforms?.twitter?.response || result?.response || ''
  const respRd = result?.platforms?.reddit?.response || ''

  if (respTw) {
    messages.value.push({
      role: 'assistant', agentName: agent.name, agentIcon: '🐦',
      text: respTw, platform: 'Twitter', ts: Date.now()
    })
  }
  if (respRd) {
    messages.value.push({
      role: 'assistant', agentName: agent.name, agentIcon: '🔴',
      text: respRd, platform: 'Reddit', ts: Date.now()
    })
  }
  if (!respTw && !respRd) {
    messages.value.push({
      role: 'assistant', agentName: agent.name, agentIcon: '💬',
      text: 'Agente não respondeu. A simulação pode ter encerrado.', ts: Date.now()
    })
  }
}

// Enviar para grupo
async function enviarGrupo(msg) {
  const membros = grupoSelec.value === 'todos'
    ? agents.value
    : grupos.value.find(g => g.nome === grupoSelec.value)?.membros || []

  if (!membros.length) {
    messages.value.push({ role: 'error', text: 'Nenhum agente nesse grupo.', ts: Date.now() })
    return
  }

  const interviews = membros.slice(0, 10).map((a, i) => ({
    agent_id: a._idx ?? a.agent_id ?? i,
    prompt: msg
  }))

  messages.value.push({
    role: 'system',
    text: `📡 Enviando para ${interviews.length} agentes do grupo "${grupoSelec.value}"...`,
    ts: Date.now()
  })
  scrollToBottom()

  const res = await service.post('/api/simulation/interview/batch', {
    simulation_id: simulationId.value,
    interviews,
    timeout: 120
  })
  const raw = res?.data?.data || res?.data || res
  const results = raw?.result?.results || raw?.results || {}

  const respostas = Object.entries(results)
  if (respostas.length === 0) {
    messages.value.push({ role: 'error', text: 'Nenhuma resposta recebida.', ts: Date.now() })
    return
  }

  respostas.forEach(([key, val]) => {
    const agentId = val.agent_id ?? parseInt(key.replace(/\D/g, ''))
    const agent = membros.find(a => (a._idx ?? a.agent_id) === agentId) || {}
    const platform = val.platform || (key.startsWith('twitter') ? 'Twitter' : 'Reddit')
    messages.value.push({
      role: 'assistant',
      agentName: agent.name || `Agente ${agentId}`,
      agentIcon: platform === 'Twitter' ? '🐦' : '🔴',
      text: val.response || 'Sem resposta.',
      platform,
      ts: Date.now()
    })
  })
}

// Enviar para TODOS
async function enviarTodos(msg) {
  messages.value.push({
    role: 'system',
    text: `📡 Enviando para todos os ${agents.value.length} agentes...`,
    ts: Date.now()
  })
  scrollToBottom()

  const res = await service.post('/api/simulation/interview/all', {
    simulation_id: simulationId.value,
    prompt: msg,
    timeout: 180
  })
  const raw = res?.data?.data || res?.data || res
  const results = raw?.result?.results || raw?.results || {}

  const respostas = Object.entries(results)
  if (respostas.length === 0) {
    messages.value.push({ role: 'error', text: 'Nenhuma resposta recebida. Verifique se a simulação está ativa.', ts: Date.now() })
    return
  }

  respostas.forEach(([key, val]) => {
    const agentId = val.agent_id ?? parseInt(key.replace(/\D/g, ''))
    const agent = agents.value.find((a, i) => (a._idx ?? a.agent_id ?? i) === agentId) || {}
    const platform = val.platform || (key.startsWith('twitter') ? 'Twitter' : 'Reddit')
    messages.value.push({
      role: 'assistant',
      agentName: agent.name || `Agente ${agentId}`,
      agentIcon: platform === 'Twitter' ? '🐦' : '🔴',
      text: val.response || 'Sem resposta.',
      platform,
      ts: Date.now()
    })
  })
}

function scrollToBottom() {
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

function selecionarAgente(agent) {
  agenteSelec.value = agent
  modo.value = 'agent'
}

function trocarModo(m) {
  modo.value = m
  if (m !== 'agent') agenteSelec.value = null
}

function mdSimple(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^[-•]\s(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <AppShell title="Central de Entrevistas">
    <template #actions>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simulationId}/agentes`)" v-if="simulationId">🧠 Agentes</AugurButton>
      <AugurButton variant="ghost" @click="router.push(`/simulacao/${simulationId}/posts`)" v-if="simulationId">📝 Posts</AugurButton>
      <AugurButton variant="ghost" @click="router.push(`/relatorio/${route.params.reportId}`)">← Relatório</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="state-box">
      <div class="spin"></div>
      <div>Carregando agentes e contexto...</div>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="state-box state-err">
      <div style="font-size:42px">⚠️</div>
      <div>{{ erro }}</div>
      <AugurButton variant="ghost" @click="router.push(`/relatorio/${route.params.reportId}`)">← Voltar ao Relatório</AugurButton>
    </div>

    <!-- Main layout -->
    <div v-else class="main-layout">

      <!-- ═══ SIDEBAR: Agentes ═══ -->
      <aside class="sidebar">
        <!-- Modo selector -->
        <div class="mode-selector">
          <button :class="['mode-btn', {active: modo==='report'}]" @click="trocarModo('report')">🤖 ReportAgent</button>
          <button :class="['mode-btn', {active: modo==='all'}]" @click="trocarModo('all')">📢 Todos</button>
          <button :class="['mode-btn', {active: modo==='group'}]" @click="trocarModo('group')">👥 Grupo</button>
        </div>

        <!-- Seletor de grupo -->
        <div v-if="modo==='group'" class="group-selector">
          <div v-for="g in grupoOpcoes" :key="g.value" class="group-opt" :class="{active: grupoSelec===g.value}" @click="grupoSelec=g.value">
            {{ g.label }}
          </div>
        </div>

        <!-- Lista de agentes (clicável para modo individual) -->
        <div class="agents-title">{{ agents.length }} Agentes</div>
        <div class="agents-list">
          <div v-for="(a, i) in agents" :key="a.user_id || i" class="agent-item"
            :class="{active: agenteSelec && (agenteSelec.name === a.name)}"
            @click="selecionarAgente({...a, _idx: i})">
            <div class="ai-avatar" :style="{background: corAvatar(a.name)}">{{ iniciais(a.name) }}</div>
            <div class="ai-info">
              <div class="ai-name">{{ a.name || a.user_name || 'Agente '+(i+1) }}</div>
              <div class="ai-role">{{ (a.bio || a.role || '').slice(0, 40) }}</div>
            </div>
          </div>
          <div v-if="!agents.length" class="ai-empty">Nenhum agente carregado</div>
        </div>
      </aside>

      <!-- ═══ CHAT AREA ═══ -->
      <div class="chat-area">
        <!-- Header -->
        <div class="chat-header">
          <div class="ch-badge">{{ modoLabel }}</div>
          <div class="ch-sub" v-if="modo==='report'">Pergunte sobre cenários, riscos e recomendações</div>
          <div class="ch-sub" v-else-if="modo==='agent'">Entrevista individual — o agente responde em primeira pessoa</div>
          <div class="ch-sub" v-else-if="modo==='group'">Envie para todos do grupo — cada um responde individualmente</div>
          <div class="ch-sub" v-else>Todos os agentes receberão sua pergunta simultaneamente</div>
        </div>

        <!-- Messages -->
        <div ref="chatBox" class="chat-messages">
          <!-- Welcome -->
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-icon">{{ modo==='report' ? '🤖' : '💬' }}</div>
            <div class="welcome-title">{{ modo==='report' ? 'Converse com o ReportAgent' : 'Entreviste os agentes' }}</div>
            <div class="welcome-sub">
              {{ modo==='report'
                ? 'O ReportAgent tem acesso a todos os dados simulados.'
                : 'Os agentes respondem em primeira pessoa, baseados em sua personalidade simulada.' }}
            </div>
            <div class="suggestions">
              <button v-for="s in sugestoes" :key="s" class="sug-btn" @click="enviar(s)">{{ s }}</button>
            </div>
          </div>

          <!-- Message bubbles -->
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="'msg-' + m.role">
            <!-- System messages -->
            <div v-if="m.role === 'system'" class="msg-system">{{ m.text }}</div>

            <!-- User/assistant/error -->
            <template v-else>
              <div class="msg-avatar" :style="{background: m.role==='user' ? 'var(--accent2)' : corAvatar(m.agentName || 'R')}">
                {{ m.role === 'user' ? '👤' : m.agentIcon || iniciais(m.agentName || 'R') }}
              </div>
              <div class="msg-body">
                <div class="msg-sender">
                  {{ m.role === 'user' ? 'Você' : m.role === 'error' ? 'Erro' : m.agentName || 'Agente' }}
                  <span v-if="m.platform" class="msg-platform">{{ m.platform }}</span>
                </div>
                <div class="msg-text" v-if="m.role === 'user'">{{ m.text }}</div>
                <div class="msg-text msg-error-text" v-else-if="m.role === 'error'">{{ m.text }}</div>
                <div class="msg-text md-body" v-else v-html="mdSimple(m.text)"></div>
              </div>
            </template>
          </div>

          <!-- Typing -->
          <div v-if="enviando" class="msg msg-assistant">
            <div class="msg-avatar" style="background:var(--accent2)">🤖</div>
            <div class="msg-body">
              <div class="msg-sender">{{ modo==='all' ? 'Entrevistando agentes...' : modo==='group' ? 'Enviando para o grupo...' : 'Processando...' }}</div>
              <div class="typing"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="chat-input">
          <input v-model="prompt" :disabled="enviando"
            :placeholder="modo==='report' ? 'Pergunte sobre a simulação...' : modo==='agent' ? `Perguntar para ${agenteSelec?.name || 'agente'}...` : 'Enviar pergunta para o grupo...'"
            @keyup.enter="enviar()" />
          <button class="send-btn" :disabled="!prompt.trim() || enviando" @click="enviar()">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.state-box { display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;text-align:center;color:var(--text-muted); }
.state-err { color:var(--danger); }
.spin { width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to { transform:rotate(360deg) } }

/* ─── Layout ──────────────────────────────────── */
.main-layout { display:grid;grid-template-columns:260px 1fr;gap:0;height:calc(100vh - 80px);max-height:820px;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;overflow:hidden; }

/* ─── Sidebar ─────────────────────────────────── */
.sidebar { display:flex;flex-direction:column;border-right:1px solid var(--border);background:var(--bg-raised);overflow:hidden; }

.mode-selector { display:flex;flex-wrap:wrap;gap:4px;padding:12px 12px 8px; }
.mode-btn { background:none;border:1px solid var(--border);color:var(--text-muted);padding:5px 10px;border-radius:8px;font-size:11px;cursor:pointer;transition:all .15s;flex:1;text-align:center;white-space:nowrap; }
.mode-btn.active { background:var(--accent2);color:#fff;border-color:var(--accent2); }
.mode-btn:hover:not(.active) { border-color:var(--accent2);color:var(--accent2); }

.group-selector { display:flex;flex-direction:column;gap:2px;padding:4px 12px 8px; }
.group-opt { font-size:11px;padding:6px 10px;border-radius:6px;cursor:pointer;color:var(--text-muted);transition:all .1s; }
.group-opt:hover { background:var(--bg-overlay); }
.group-opt.active { background:rgba(124,111,247,0.12);color:var(--accent2);font-weight:600; }

.agents-title { font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px;padding:8px 14px 4px; }
.agents-list { flex:1;overflow-y:auto;padding:0 8px 8px; }
.agent-item { display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;cursor:pointer;transition:background .1s; }
.agent-item:hover { background:var(--bg-overlay); }
.agent-item.active { background:rgba(0,229,195,0.1);border-left:2px solid var(--accent); }
.ai-avatar { width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#fff;flex-shrink:0; }
.ai-name { font-size:12px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px; }
.ai-role { font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:160px; }
.ai-empty { text-align:center;padding:20px;color:var(--text-muted);font-size:12px; }

/* ─── Chat ────────────────────────────────────── */
.chat-area { display:flex;flex-direction:column;overflow:hidden; }

.chat-header { padding:14px 20px;border-bottom:1px solid var(--border); }
.ch-badge { font-size:14px;font-weight:700;color:var(--text-primary); }
.ch-sub { font-size:11px;color:var(--text-muted);margin-top:2px; }

.chat-messages { flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:12px; }

.welcome { text-align:center;padding:30px 20px; }
.welcome-icon { font-size:36px;margin-bottom:10px; }
.welcome-title { font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:6px; }
.welcome-sub { font-size:12px;color:var(--text-muted);max-width:380px;margin:0 auto 16px;line-height:1.6; }
.suggestions { display:flex;flex-wrap:wrap;gap:6px;justify-content:center; }
.sug-btn { background:var(--bg-raised);border:1px solid var(--border);color:var(--text-secondary);padding:7px 12px;border-radius:16px;font-size:11px;cursor:pointer;transition:all .15s; }
.sug-btn:hover { border-color:var(--accent2);color:var(--accent2); }

.msg { display:flex;gap:8px;align-items:flex-start;max-width:90%; }
.msg-user { align-self:flex-end;flex-direction:row-reverse; }
.msg-assistant,.msg-error { align-self:flex-start; }
.msg-system { width:100%;text-align:center;font-size:11px;color:var(--accent2);padding:4px;font-weight:600; }
.msg-avatar { width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;color:#fff; }
.msg-body { display:flex;flex-direction:column;gap:3px; }
.msg-sender { font-size:10px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.3px; }
.msg-platform { font-size:9px;background:rgba(124,111,247,0.12);color:var(--accent2);padding:1px 5px;border-radius:4px;margin-left:4px;text-transform:none;letter-spacing:0; }
.msg-user .msg-sender { text-align:right; }
.msg-text { font-size:13px;color:var(--text-secondary);line-height:1.65;background:var(--bg-raised);border:1px solid var(--border);border-radius:10px;padding:8px 12px; }
.msg-user .msg-text { background:rgba(124,111,247,0.1);border-color:rgba(124,111,247,0.2);color:var(--text-primary); }
.msg-error-text { background:rgba(255,90,90,0.08);border-color:rgba(255,90,90,0.2);color:var(--danger); }

.md-body :deep(strong) { color:var(--text-primary); }
.md-body :deep(blockquote) { border-left:2px solid var(--accent2);padding-left:8px;margin:6px 0;color:var(--text-muted);font-style:italic; }
.md-body :deep(ul) { padding-left:16px;margin:4px 0; }

.typing { display:flex;gap:4px;padding:8px 12px;background:var(--bg-raised);border:1px solid var(--border);border-radius:10px; }
.typing span { width:6px;height:6px;background:var(--text-muted);border-radius:50%;animation:bounce .6s infinite alternate; }
.typing span:nth-child(2) { animation-delay:.2s; }
.typing span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { to { transform:translateY(-5px);opacity:.3; } }

.chat-input { display:flex;gap:8px;padding:12px 20px;border-top:1px solid var(--border); }
.chat-input input { flex:1;background:var(--bg-overlay);border:1px solid var(--border-md);color:var(--text-primary);padding:10px 14px;border-radius:10px;font-size:13px;outline:none; }
.chat-input input:focus { border-color:var(--accent2); }
.chat-input input:disabled { opacity:.5; }
.send-btn { background:var(--accent2);color:#fff;border:none;border-radius:10px;width:38px;height:38px;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0; }
.send-btn:disabled { opacity:.3;cursor:not-allowed; }

@media (max-width:768px) {
  .main-layout { grid-template-columns:1fr;height:auto;max-height:none; }
  .sidebar { max-height:200px;border-right:none;border-bottom:1px solid var(--border); }
  .agents-list { flex-direction:row;overflow-x:auto;gap:4px; }
  .agent-item { flex-shrink:0; }
}
</style>
