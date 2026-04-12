<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'

const router = useRouter()
const projetos = ref([])
const simulacoes = ref([])
const carregando = ref(true)

async function carregar() {
  carregando.value = true
  try {
    const [projRes, simRes] = await Promise.allSettled([
      service.get('/api/graph/project/list'),
      service.get('/api/simulation/history', { params: { limit: 50 } })
    ])
    if (projRes.status === 'fulfilled') {
      const raw = projRes.value?.data || projRes.value
      projetos.value = (Array.isArray(raw) ? raw : (raw?.data || raw?.items || []))
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    }
    if (simRes.status === 'fulfilled') {
      const raw = simRes.value?.data || simRes.value
      simulacoes.value = Array.isArray(raw) ? raw : (raw?.data || raw?.history || [])
    }
  } catch (e) { console.error(e) }
  finally { carregando.value = false }
}

onMounted(carregar)

// Metricas
const totalProjetos = computed(() => projetos.value.length)
const totalSims = computed(() => simulacoes.value.length)
const totalAgentes = computed(() => simulacoes.value.reduce((a, s) => a + (s.entities_count || s.agent_count || 0), 0))
const totalRelatorios = computed(() => simulacoes.value.filter(s => s.report_id).length)
const totalRodadas = computed(() => simulacoes.value.reduce((a, s) => a + (s.current_round || s.total_rounds || 0), 0))

const emExecucao = computed(() => simulacoes.value.filter(s => (s.runner_status || s.status) === 'running'))
const concluidas = computed(() => simulacoes.value.filter(s => (s.runner_status || s.status) === 'completed'))
const comRelatorio = computed(() => simulacoes.value.filter(s => s.report_id))
const recentes = computed(() => projetos.value.slice(0, 6))

// Taxa de sucesso
const taxaSucesso = computed(() => {
  if (!totalSims.value) return 0
  return Math.round((concluidas.value.length / totalSims.value) * 100)
})

// Atividade recente (ultimas 5 simulacoes com info)
const atividadeRecente = computed(() => {
  return simulacoes.value
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .slice(0, 5)
    .map(s => ({
      ...s,
      statusLabel: statusLabel(s),
      statusIcon: statusIcon(s),
      ago: tempoAtras(s.created_at)
    }))
})

function statusLabel(s) {
  const st = s.runner_status || s.status
  if (st === 'running') return 'Em execução'
  if (st === 'completed') return 'Concluída'
  if (st === 'failed') return 'Falhou'
  return 'Criada'
}
function statusIcon(s) {
  const st = s.runner_status || s.status
  if (st === 'running') return '⏳'
  if (st === 'completed') return '✅'
  if (st === 'failed') return '❌'
  return '📋'
}
function tempoAtras(dt) {
  if (!dt) return ''
  const diff = Date.now() - new Date(dt).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `${mins}min atrás`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h atrás`
  const days = Math.floor(hours / 24)
  return `${days}d atrás`
}

function badgeProjeto(p) {
  const sim = simulacoes.value
    .filter(s => s.project_id === (p.project_id || p.id))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))[0]
  const st = sim ? (sim.runner_status || sim.status) : null
  if (st === 'running') return { label: '⏳ Em execução', cls: 'b-running' }
  if (st === 'completed') return { label: '✅ Concluído', cls: 'b-done' }
  if (p.status === 'graph_building') return { label: '⚙️ Construindo', cls: 'b-building' }
  if (p.status === 'graph_completed') return { label: 'Pronto', cls: 'b-ready' }
  return { label: 'Criado', cls: 'b-draft' }
}

function fmtDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function simCount(p) {
  return simulacoes.value.filter(s => s.project_id === (p.project_id || p.id)).length
}

function navSim(s) {
  const st = s.runner_status || s.status
  if (st === 'running') router.push(`/simulacao/${s.simulation_id}/executar`)
  else if (s.report_id) router.push(`/relatorio/${s.report_id}`)
  else router.push(`/projeto/${s.project_id}`)
}
</script>

<template>
  <AppShell title="Dashboard">
    <template #actions>
      <button class="btn-comp" @click="router.push('/comparar')">📊 Comparar</button>
      <button class="btn-nova" @click="router.push('/projeto/novo')">+ Novo Projeto</button>
    </template>

    <!-- Carregando -->
    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando workspace...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="projetos.length === 0" class="empty">
      <div class="empty-icon">🔭</div>
      <div class="empty-title">Bem-vindo ao AUGUR</div>
      <div class="empty-demo">
        <button class="demo-btn" @click="$router.push('/demo')">
          📊 Ver relatório de demonstração
        </button>
        <span class="demo-hint">Veja um exemplo real de análise preditiva</span>
      </div>
      <div class="empty-sub">
        Crie seu primeiro projeto para começar a prever como o mercado vai reagir
        antes de lançar seu produto, marca ou serviço.
      </div>
      <button class="btn-nova-lg" @click="router.push('/projeto/novo')">✦ Criar primeiro projeto</button>
    </div>

    <div v-else>

      <!-- ══════════ WELCOME ══════════ -->
      <div class="welcome-bar">
        <div class="wb-left">
          <h2 class="wb-greeting">{{ greeting }}, Carlos</h2>
          <p class="wb-sub">{{ totalSims }} simulacoes realizadas · {{ totalRelatorios }} relatorios gerados</p>
        </div>
        <button class="wb-cta" @click="router.push('/projeto/novo')">+ Nova Analise</button>
      </div>

      <!-- ══════════ MÉTRICAS PRINCIPAIS ══════════ -->
      <div class="metrics-row">
        <div class="metric-card mc-1">
          <div class="mc-val-big">{{ totalProjetos }}</div>
          <div class="mc-label">Projetos</div>
          <div class="mc-bar"><div class="mc-fill" style="width:100%;background:var(--accent)"></div></div>
        </div>
        <div class="metric-card mc-2">
          <div class="mc-val-big">{{ totalAgentes }}</div>
          <div class="mc-label">Agentes</div>
          <div class="mc-bar"><div class="mc-fill" style="width:75%;background:var(--accent2)"></div></div>
        </div>
        <div class="metric-card mc-3">
          <div class="mc-val-big">{{ totalRelatorios }}</div>
          <div class="mc-label">Relatorios</div>
          <div class="mc-bar"><div class="mc-fill" style="width:60%;background:#f5a623"></div></div>
        </div>
        <div class="metric-card mc-4">
          <div class="mc-val-big">{{ taxaSucesso }}%</div>
          <div class="mc-label">Sucesso</div>
          <div class="mc-bar"><div class="mc-fill" :style="{width: taxaSucesso+'%', background: taxaSucesso >= 80 ? 'var(--accent)' : '#ff5a5a'}"></div></div>
        </div>
      </div>

      <!-- ══════════ ALERTA DE EXECUÇÃO ══════════ -->
      <div v-if="emExecucao.length" class="alert-bar">
        <span class="alert-dot"></span>
        <span>{{ emExecucao.length }} simulação{{ emExecucao.length > 1 ? 'ões' : '' }} em execução agora</span>
        <button class="alert-link" @click="router.push(`/simulacao/${emExecucao[0].simulation_id}/executar`)">
          Acompanhar ao vivo →
        </button>
      </div>

      <!-- ══════════ GRID PRINCIPAL ══════════ -->
      <div class="main-grid">

        <!-- COLUNA ESQUERDA: Projetos recentes -->
        <div class="section">
          <div class="sec-header">
            <h3 class="sec-title">Projetos recentes</h3>
            <span class="sec-sub">Clique para ver simulações e relatórios</span>
          </div>
          <div class="projetos-grid">
            <div v-for="p in recentes" :key="p.project_id || p.id" class="projeto-card" @click="router.push(`/projeto/${p.project_id || p.id}`)">
              <div class="card-top">
                <span :class="['badge', badgeProjeto(p).cls]">{{ badgeProjeto(p).label }}</span>
                <span class="card-data">{{ fmtDate(p.created_at) }}</span>
              </div>
              <div class="card-nome">{{ p.name || 'Projeto sem nome' }}</div>
              <div v-if="p.simulation_requirement" class="card-brief">
                {{ p.simulation_requirement.length > 80 ? p.simulation_requirement.slice(0, 80) + '...' : p.simulation_requirement }}
              </div>
              <div class="card-footer">
                <span class="card-meta">{{ simCount(p) }} sim</span>
                <span class="card-meta">{{ (p.files || []).length }} arq</span>
                <span class="card-arrow">›</span>
              </div>
            </div>

            <div class="projeto-card card-add" @click="router.push('/projeto/novo')">
              <div class="card-add-icon">+</div>
              <div class="card-add-label">Novo Projeto</div>
            </div>
          </div>
        </div>

        <!-- COLUNA DIREITA: Atividade recente -->
        <div class="section">
          <div class="sec-header">
            <h3 class="sec-title">Atividade recente</h3>
            <span class="sec-sub">Últimas simulações</span>
          </div>
          <div class="activity-list">
            <div v-for="s in atividadeRecente" :key="s.simulation_id" class="activity-item" @click="navSim(s)">
              <div class="act-icon">{{ s.statusIcon }}</div>
              <div class="act-body">
                <div class="act-title">{{ s.simulation_requirement?.slice(0, 60) || 'Simulação' }}{{ (s.simulation_requirement?.length || 0) > 60 ? '...' : '' }}</div>
                <div class="act-meta">
                  <span>{{ s.statusLabel }}</span>
                  <span v-if="s.entities_count">· {{ s.entities_count }} agentes</span>
                  <span v-if="s.current_round">· {{ s.current_round }} rodadas</span>
                </div>
              </div>
              <div class="act-time">{{ s.ago }}</div>
            </div>
            <div v-if="!atividadeRecente.length" class="act-empty">Nenhuma simulação ainda</div>
          </div>

          <!-- Resumo rápido -->
          <div class="quick-stats" v-if="concluidas.length">
            <div class="qs-title">Resumo do workspace</div>
            <div class="qs-items">
              <div class="qs-item">
                <span class="qs-val" style="color:var(--accent)">{{ concluidas.length }}</span>
                <span class="qs-label">Concluídas</span>
              </div>
              <div class="qs-item">
                <span class="qs-val" style="color:#f5a623">{{ emExecucao.length }}</span>
                <span class="qs-label">Em execução</span>
              </div>
              <div class="qs-item">
                <span class="qs-val" style="color:var(--accent2)">{{ comRelatorio.length }}</span>
                <span class="qs-label">Com relatório</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* Welcome */
.welcome-bar { display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:20px 24px;background:linear-gradient(135deg,rgba(0,229,195,0.06),rgba(124,111,247,0.06));border:1px solid rgba(0,229,195,0.12);border-radius:16px; }
.wb-greeting { font-size:20px;font-weight:700;color:var(--text-primary);margin:0; }
.wb-sub { font-size:12px;color:var(--text-muted);margin-top:4px; }
.wb-cta { background:var(--accent);color:#09090f;border:none;border-radius:10px;padding:10px 24px;font-size:13px;font-weight:700;cursor:pointer;transition:all .2s; }
.wb-cta:hover { transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,229,195,0.3); }

/* Metricas */
.metrics-row { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px; }
.metric-card { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;transition:all .2s;position:relative;overflow:hidden; }
.metric-card:hover { border-color:var(--border-md);transform:translateY(-2px); }
.mc-val-big { font-size:32px;font-weight:800;color:var(--text-primary);font-family:'JetBrains Mono',monospace;line-height:1; }
.mc-label { font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px;margin-top:6px;font-weight:600; }
.mc-bar { height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-top:12px;overflow:hidden; }
.mc-fill { height:100%;border-radius:2px;transition:width 1s ease; }
.mc-1 { border-left:3px solid var(--accent); }
.mc-2 { border-left:3px solid var(--accent2); }
.mc-3 { border-left:3px solid #f5a623; }
.mc-4 { border-left:3px solid var(--accent); }

/* Botoes */
.btn-nova { background:var(--accent);color:#000;border:none;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer; }
.btn-comp { background:none;border:1px solid var(--accent2);color:var(--accent2);border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s; }
.btn-comp:hover { background:rgba(124,111,247,0.1); }
.btn-nova:hover { opacity:.85; }
.btn-nova-lg { background:var(--accent);color:#000;border:none;border-radius:10px;padding:13px 28px;font-size:15px;font-weight:700;cursor:pointer; }

/* Loading/Empty */
.loading { display:flex;align-items:center;gap:12px;padding:48px;color:var(--text-muted); }
.spinner { width:20px;height:20px;border:2px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite; }
@keyframes spin { to { transform:rotate(360deg) } }
.empty { text-align:center;padding:64px 20px; }
.empty-icon { font-size:56px;margin-bottom:20px; }
.empty-title { font-size:24px;font-weight:600;color:var(--text-primary);margin-bottom:12px; }
.empty-sub { font-size:14px;color:var(--text-secondary);max-width:460px;margin:0 auto 28px;line-height:1.8; }

/* Alert */
.alert-bar { display:flex;align-items:center;gap:10px;background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.25);border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#f5a623; }
.alert-dot { width:8px;height:8px;border-radius:50%;background:#f5a623;animation:pulse 1.4s infinite;flex-shrink:0; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.alert-link { margin-left:auto;background:none;border:1px solid rgba(245,166,35,0.4);color:#f5a623;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer; }

/* Grid principal */
.main-grid { display:grid;grid-template-columns:60% 40%;gap:16px; }
.section { display:flex;flex-direction:column;gap:12px; }
.sec-header { margin-bottom:2px; }
.sec-title { font-size:16px;font-weight:600;color:var(--text-primary);margin:0 0 4px; }
.sec-sub { font-size:12px;color:var(--text-muted); }

/* Projetos grid */
.projetos-grid { display:grid;grid-template-columns:repeat(2,1fr);gap:10px; }
.projeto-card { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;cursor:pointer;transition:all .2s;display:flex;flex-direction:column;gap:8px;position:relative; }
.projeto-card:hover { border-color:var(--accent);transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,0.12); }
.card-top { display:flex;align-items:center;justify-content:space-between; }
.card-data { font-size:11px;color:var(--text-muted); }
.card-nome { font-size:13px;font-weight:600;color:var(--text-primary);line-height:1.4; }
.card-brief { font-size:11px;color:var(--text-muted);line-height:1.5; }
.card-footer { display:flex;align-items:center;gap:8px;margin-top:2px; }
.card-meta { font-size:10px;color:var(--text-muted);background:var(--bg-overlay);padding:2px 6px;border-radius:12px; }
.card-arrow { margin-left:auto;font-size:16px;color:var(--text-muted); }
.card-add { border-style:dashed;border-color:var(--border-md);align-items:center;justify-content:center;min-height:100px;color:var(--text-muted); }
.card-add:hover { border-color:var(--accent);color:var(--accent); }
.card-add-icon { font-size:24px;font-weight:200;margin-bottom:4px; }
.card-add-label { font-size:12px;font-weight:500; }

/* Atividade */
.activity-list { display:flex;flex-direction:column;gap:4px; }
.activity-item { display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all .2s;border-left:3px solid var(--accent); }
.activity-item:hover { border-color:var(--accent);background:var(--bg-raised);transform:translateX(4px); }
.act-icon { font-size:16px;flex-shrink:0; }
.act-body { flex:1;min-width:0; }
.act-title { font-size:13px;font-weight:600;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.act-meta { font-size:11px;color:var(--text-muted);margin-top:2px; }
.act-time { font-size:10px;color:var(--text-muted);white-space:nowrap; }
.act-empty { text-align:center;padding:24px;color:var(--text-muted);font-size:13px; }

/* Quick stats */
.quick-stats { background:linear-gradient(135deg,rgba(124,111,247,0.04),rgba(0,229,195,0.04));border:1px solid rgba(124,111,247,0.12);border-radius:14px;padding:20px;margin-top:12px; }
.qs-title { font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:12px; }
.qs-items { display:grid;grid-template-columns:repeat(3,1fr);gap:12px; }
.qs-item { text-align:center; }
.qs-val { font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace;display:block; }
.qs-label { font-size:10px;color:var(--text-muted);margin-top:2px; }

/* Badges */
.badge { padding:3px 8px;border-radius:20px;font-size:10px;font-weight:500; }
.b-done { background:rgba(0,229,195,0.1);color:var(--accent); }
.b-running { background:rgba(245,166,35,0.1);color:#f5a623; }
.b-ready { background:rgba(0,229,195,0.08);color:var(--accent); }
.b-building { background:rgba(124,111,247,0.1);color:var(--accent2); }
.b-draft { background:rgba(107,107,128,0.12);color:var(--text-muted); }

@media (max-width:1080px) {
  .metrics-row { grid-template-columns:repeat(2,1fr); }
  .main-grid { grid-template-columns:1fr; }
  .projetos-grid { grid-template-columns:repeat(2,1fr); }
}
@media (max-width:680px) {
  .metrics-row { grid-template-columns:repeat(2,1fr); }
  .projetos-grid { grid-template-columns:1fr; }
}

.empty-demo { margin-bottom:24px; display:flex; flex-direction:column; align-items:center; gap:8px; }
.demo-btn { padding:12px 28px; border-radius:10px; border:2px solid rgba(0,229,195,0.4); background:rgba(0,229,195,0.08); color:#00e5c3; font-weight:700; font-size:14px; cursor:pointer; transition:all .2s; }
.demo-btn:hover { background:rgba(0,229,195,0.15); transform:translateY(-2px); }
.demo-hint { font-size:11px; color:#555570; }
</style>
