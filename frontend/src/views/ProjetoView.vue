<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'
import { useToast } from '../composables/useToast'

const route  = useRoute()
const router = useRouter()
const toast  = useToast()

const projeto       = ref(null)
const simulacoes    = ref([])
const carregando    = ref(true)
const confirmDelete = ref(false)
const deletando     = ref(false)

// ─── Modal nova simulação ─────────────────────────────────────
const modal     = ref(false)
const mEtapa    = ref(1)
const mTitulo   = ref('')
const mCenario  = ref('')
const mHipotese = ref('')
const mAgentes  = ref(50)
const mRodadas  = ref(20)
const mGerando  = ref(false)
const mCriando  = ref(false)

const pid = computed(() => route.params.projectId)

const mE1ok    = computed(() => mTitulo.value.trim().length >= 3 && mHipotese.value.trim().length >= 10)
const mEstMin  = computed(() => Math.round(Math.max(2, mAgentes.value * mRodadas.value * 0.04)))
const mEstCusto = computed(() => (mAgentes.value * mRodadas.value * 0.0008).toFixed(2))
const mDescAg  = computed(() => {
  if (mAgentes.value <= 20)  return 'Teste rápido — ideal para validar a hipótese'
  if (mAgentes.value <= 100) return 'Bom equilíbrio entre velocidade e precisão'
  if (mAgentes.value <= 250) return 'Alta fidelidade — captura nuances importantes'
  return 'Máxima riqueza — simulação de alta complexidade'
})
const mDescRd  = computed(() => {
  if (mRodadas.value <= 5)  return 'Reação imediata ao evento'
  if (mRodadas.value <= 25) return 'Captura tendências de curto prazo'
  if (mRodadas.value <= 60) return 'Evolução completa da opinião ao longo do tempo'
  return 'Análise profunda — evolução de longo prazo'
})

// ─── Carregar ─────────────────────────────────────────────────
async function carregar() {
  carregando.value = true
  try {
    const [pr, sr] = await Promise.allSettled([
      service.get(`/api/graph/project/${pid.value}`),
      service.get('/api/simulation/list', { params: { project_id: pid.value } })
    ])
    if (pr.status === 'fulfilled') {
      const raw = pr.value?.data || pr.value
      projeto.value = raw?.data || raw
    }
    if (sr.status === 'fulfilled') {
      const raw = sr.value?.data || sr.value
      const lista = Array.isArray(raw) ? raw : (raw?.data || raw?.simulations || [])
      simulacoes.value = lista.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    }
  } catch {
    toast.error('Erro ao carregar projeto.')
  } finally {
    carregando.value = false
  }
}

// ─── Modal ────────────────────────────────────────────────────
function abrirModal() {
  mEtapa.value    = 1
  mTitulo.value   = ''
  mCenario.value  = ''
  mHipotese.value = ''
  mAgentes.value  = 50
  mRodadas.value  = 20
  modal.value     = true
}

async function gerarHipotese() {
  if (!mCenario.value.trim()) return
  mGerando.value = true
  try {
    const res = await service.post('/api/graph/generate-hypothesis', { cenario: mCenario.value, segmento: '' })
    const d   = res.data || res
    if (d.hipotese) mHipotese.value = d.hipotese
    toast.success('Hipótese gerada!')
  } catch {
    mHipotese.value = `Como ${mCenario.value.toLowerCase()} vai impactar o mercado nos próximos meses?`
  } finally {
    mGerando.value = false
  }
}

// Criar nova simulação — o SimulationView cuida do grafo internamente
async function criarSimulacao() {
  mCriando.value = true
  try {
    modal.value = false
    // Passa os parâmetros para o pipeline — ele decide se precisa construir o grafo ou não
    router.push(
      `/simulacao/${pid.value}?agentes=${mAgentes.value}&rodadas=${mRodadas.value}&titulo=${encodeURIComponent(mTitulo.value)}&hipotese=${encodeURIComponent(mHipotese.value)}`
    )
  } finally {
    mCriando.value = false
  }
}

// ─── Gerar relatório manualmente ─────────────────────────────
async function gerarRelatorio(simId) {
  toast.info('Gerando relatório... isso pode levar alguns minutos.')
  try {
    const res = await service.post('/api/report/generate', { simulation_id: simId })
    const data = res?.data?.data || res?.data || res
    toast.success('Relatório em geração! Aguarde e recarregue a página.')
    // Recarregar lista após 3s para pegar o report_id
    setTimeout(carregar, 5000)
  } catch (e) {
    toast.error('Não foi possível gerar o relatório.')
  }
}

// ─── Excluir projeto ─────────────────────────────────────────
async function excluir() {
  deletando.value = true
  try {
    await service.delete(`/api/graph/project/${pid.value}`)
    toast.success('Projeto excluído.')
    router.push('/')
  } catch {
    toast.error('Não foi possível excluir.')
    deletando.value = false
  }
}

// ─── Helpers visuais simulações ───────────────────────────────
function statusSim(sim) {
  const s = sim.runner_status || sim.status
  const map = {
    running:   { label: 'Em execução', dot: 'dot-yellow' },
    completed: { label: 'Concluída',   dot: 'dot-green'  },
    stopped:   { label: 'Parada',      dot: 'dot-gray'   },
    paused:    { label: 'Pausada',     dot: 'dot-gray'   },
    failed:    { label: 'Erro',        dot: 'dot-red'    },
    ready:     { label: 'Pronta',      dot: 'dot-purple' },
    preparing: { label: 'Preparando',  dot: 'dot-purple' },
    created:   { label: 'Criada',      dot: 'dot-gray'   },
  }
  return map[s] || { label: s || '—', dot: 'dot-gray' }
}

function acaoSim(sim) {
  const s = sim.runner_status || sim.status
  if (s === 'running')
    return { label: '▶ Acompanhar ao vivo', cls: 'a-run',    fn: () => router.push(`/simulacao/${sim.simulation_id}/executar`) }
  if (sim.report_id)
    return { label: '📊 Ver Relatório',     cls: 'a-report', fn: () => router.push(`/relatorio/${sim.report_id}`) }
  if (s === 'completed')
    return { label: '📄 Gerar Relatório',   cls: 'a-report', fn: () => gerarRelatorio(sim.simulation_id) }
  if (s === 'stopped' || s === 'paused')
    return { label: '▶ Retomar',            cls: 'a-btn',    fn: () => router.push(`/simulacao/${sim.simulation_id}/executar`) }
  return   { label: '⚙ Ver Pipeline',      cls: 'a-btn',    fn: () => router.push(`/simulacao/${pid.value}`) }
}

function progresso(sim) {
  const pct = sim.progress_percent
  if (pct > 0) return Math.round(pct)
  if (sim.total_rounds && sim.current_round)
    return Math.round((sim.current_round / sim.total_rounds) * 100)
  return 0
}

function fmt(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

onMounted(carregar)
</script>

<template>
  <AppShell :title="projeto?.name || 'Projeto'">
    <template #actions>
      <button class="btn-nova" @click="abrirModal">+ Nova Simulação</button>
    </template>

    <div v-if="carregando" class="loading">
      <div class="spinner"></div> Carregando...
    </div>

    <div v-else-if="!projeto" class="not-found">
      Projeto não encontrado.
      <button class="btn-ghost" @click="router.push('/')">← Início</button>
    </div>

    <div v-else class="page">

      <!-- ─── HEADER DO PROJETO ─── -->
      <div class="proj-card">
        <div class="proj-body">
          <div class="proj-nome">{{ projeto.name }}</div>
          <div class="proj-meta">
            <span>📅 {{ fmt(projeto.created_at) }}</span>
            <span class="sep">·</span>
            <span>{{ simulacoes.length }} simulação{{ simulacoes.length !== 1 ? 'ões' : '' }}</span>
          </div>
        </div>
        <div class="proj-actions">
          <button class="btn-nova" @click="abrirModal">+ Nova Simulação</button>
          <button class="btn-grafo" @click="router.push(`/projeto/${pid}/grafo`)" title="Ver Grafo de Conhecimento">🕸 Grafo</button>
          <button class="btn-grafo" @click="router.push('/comparar')" title="Comparar Simulações">📊 Comparar</button>
          <button class="btn-del" @click="confirmDelete = true" title="Excluir">🗑</button>
        </div>
      </div>

      <!-- Confirmação de exclusão -->
      <Transition name="slide">
        <div v-if="confirmDelete" class="confirm">
          <span>⚠️ Excluir <strong>{{ projeto.name }}</strong> e todas as simulações? Irreversível.</span>
          <div class="confirm-btns">
            <button class="btn-ghost" @click="confirmDelete = false">Cancelar</button>
            <button class="btn-danger" :disabled="deletando" @click="excluir">
              {{ deletando ? 'Excluindo...' : 'Sim, excluir' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- ─── SIMULAÇÕES ─── -->
      <div class="section-header">
        <h2 class="section-titulo">Simulações</h2>
        <button class="btn-nova-sm" @click="abrirModal">+ Nova</button>
      </div>

      <!-- Vazio -->
      <div v-if="simulacoes.length === 0" class="vazio">
        <div class="vazio-emoji">🚀</div>
        <div class="vazio-titulo">Nenhuma simulação ainda</div>
        <div class="vazio-sub">Crie a primeira simulação para começar a prever o mercado.</div>
        <button class="btn-nova" style="margin-top:20px" @click="abrirModal">
          ✦ Criar primeira simulação
        </button>
      </div>

      <!-- Lista -->
      <div v-else class="sims">
        <div
          v-for="(sim, idx) in simulacoes"
          :key="sim.simulation_id"
          class="sim"
          :class="{
            'sim-running': (sim.runner_status||sim.status)==='running',
            'sim-done':    (sim.runner_status||sim.status)==='completed',
            'sim-error':   (sim.runner_status||sim.status)==='failed',
          }"
        >
          <div class="sim-top">
            <div class="sim-left">
              <div :class="['dot', statusSim(sim).dot]"></div>
              <span class="sim-idx">#{{ simulacoes.length - idx }}</span>
              <span class="sim-status">{{ statusSim(sim).label }}</span>
              <span class="sim-data">{{ fmt(sim.created_at) }}</span>
            </div>
            <div class="sim-right">
              <button v-if="(sim.runner_status||sim.status)==='completed'" class="a-sec" @click="router.push(`/simulacao/${sim.simulation_id}/agentes`)" title="Ver Agentes">🧠</button>
              <button v-if="(sim.runner_status||sim.status)==='completed'" class="a-sec" @click="router.push(`/simulacao/${sim.simulation_id}/influentes`)" title="Ranking de Influência">👑</button>
              <button v-if="sim.report_id" class="a-sec" @click="router.push(`/agentes/${sim.report_id}`)" title="Conversar com ReportAgent">💬</button>
              <button :class="['a-btn', acaoSim(sim).cls]" @click="acaoSim(sim).fn()">
                {{ acaoSim(sim).label }}
              </button>
            </div>
          </div>

          <div v-if="sim.simulation_requirement" class="sim-hipotese">
            {{ sim.simulation_requirement.length > 120
              ? sim.simulation_requirement.slice(0, 120) + '...'
              : sim.simulation_requirement }}
          </div>

          <div class="sim-stats">
            <div class="stat" v-if="sim.entities_count || sim.profiles_count">
              <span class="sl">Agentes</span>
              <span class="sv">{{ sim.entities_count || sim.profiles_count }}</span>
            </div>
            <div class="stat" v-if="sim.total_rounds">
              <span class="sl">Rodadas</span>
              <span class="sv">{{ sim.current_round || 0 }}<span class="sof">/ {{ sim.total_rounds }}</span></span>
            </div>
            <div class="stat" v-if="sim.posts_created">
              <span class="sl">Posts</span>
              <span class="sv">{{ sim.posts_created }}</span>
            </div>
            <div class="stat" v-if="sim.report_id">
              <span class="sl">Relatório</span>
              <span class="sl-link" @click="router.push(`/relatorio/${sim.report_id}`)">Ver →</span>
            </div>
          </div>

          <div v-if="sim.total_rounds" class="sim-prog">
            <div class="prog-bar">
              <div class="prog-fill"
                :class="{
                  'pf-run':  (sim.runner_status||sim.status)==='running',
                  'pf-done': (sim.runner_status||sim.status)==='completed',
                }"
                :style="{ width: progresso(sim)+'%' }"
              ></div>
            </div>
            <span class="prog-pct">{{ progresso(sim) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════ -->
    <!-- MODAL NOVA SIMULAÇÃO                                       -->
    <!-- ══════════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="modal" class="overlay" @click.self="modal = false">
          <div class="modal">

            <div class="modal-head">
              <div>
                <div class="modal-titulo">Nova Simulação</div>
                <div class="modal-sub">{{ projeto?.name }}</div>
              </div>
              <button class="modal-close" @click="modal = false">×</button>
            </div>

            <!-- Steps -->
            <div class="modal-steps">
              <div v-for="(s,i) in ['Hipótese','Parâmetros']" :key="i"
                class="mstep" :class="{ active: mEtapa===i+1, done: mEtapa>i+1 }">
                <div class="mstep-dot">
                  <svg v-if="mEtapa>i+1" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" width="10" height="10"><polyline points="2,6 5,9 10,3"/></svg>
                  <span v-else>{{ i+1 }}</span>
                </div>
                <span class="mstep-label">{{ s }}</span>
              </div>
            </div>

            <!-- Etapa 1: Hipótese -->
            <div v-if="mEtapa === 1" class="modal-body">
              <div class="mf">
                <label class="ml">Título da simulação <span class="req">*</span></label>
                <input v-model="mTitulo" class="mi" type="text"
                  placeholder="Ex: Teste preço premium, Cenário 1º turno" autofocus/>
              </div>
              <div class="mf">
                <label class="ml">Descreva seu cenário</label>
                <textarea v-model="mCenario" class="mt" rows="2"
                  placeholder="Em linguagem natural — a IA transforma em hipótese para você."/>
                <button class="btn-ia" :disabled="!mCenario.trim() || mGerando" @click="gerarHipotese">
                  <span v-if="mGerando" class="spin-ia"></span>
                  <span v-else>✦</span>
                  {{ mGerando ? 'Gerando...' : 'Gerar hipótese com IA' }}
                </button>
              </div>
              <div class="mf">
                <label class="ml">Hipótese de previsão <span class="req">*</span></label>
                <textarea v-model="mHipotese" class="mt" rows="3"
                  placeholder="Como X vai impactar Y nos próximos Z meses?"/>
                <span class="mh">Guia o comportamento de todos os agentes. Mín. 10 caracteres.</span>
              </div>
            </div>

            <!-- Etapa 2: Parâmetros -->
            <div v-else-if="mEtapa === 2" class="modal-body">
              <div class="mresumo">
                <strong>{{ mTitulo }}</strong>
                <span>{{ mHipotese.slice(0,90) }}{{ mHipotese.length>90?'...':'' }}</span>
              </div>
              <div class="mparam">
                <div class="mparam-h">
                  <span class="mparam-l">Agentes</span>
                  <span class="mparam-v">{{ mAgentes }}</span>
                </div>
                <input type="range" min="5" max="500" step="5" v-model.number="mAgentes" class="slider"/>
                <div class="mbounds"><span>5 — rápido</span><span>500 — máxima riqueza</span></div>
                <div class="mdesc">{{ mDescAg }}</div>
              </div>
              <div class="mparam">
                <div class="mparam-h">
                  <span class="mparam-l">Rodadas</span>
                  <span class="mparam-v">{{ mRodadas }}</span>
                </div>
                <input type="range" min="1" max="100" step="1" v-model.number="mRodadas" class="slider"/>
                <div class="mbounds"><span>1 — instantâneo</span><span>100 — evolução completa</span></div>
                <div class="mdesc">{{ mDescRd }}</div>
              </div>
              <div class="mest">
                <div class="me"><div class="mel">⏱ Tempo</div><div class="mev">~{{ mEstMin }} min</div></div>
                <div class="mes"></div>
                <div class="me"><div class="mel">💳 Custo</div><div class="mev">~${{ mEstCusto }}</div></div>
                <div class="mes"></div>
                <div class="me"><div class="mel">🤖 Agentes</div><div class="mev ac">{{ mAgentes }}</div></div>
                <div class="mes"></div>
                <div class="me"><div class="mel">🔄 Rodadas</div><div class="mev ac2">{{ mRodadas }}</div></div>
              </div>
            </div>

            <div class="modal-foot">
              <button class="btn-ghost" @click="mEtapa===1 ? modal=false : mEtapa--">
                {{ mEtapa===1 ? 'Cancelar' : '← Voltar' }}
              </button>
              <button v-if="mEtapa < 2" class="btn-prox" :disabled="!mE1ok" @click="mEtapa=2">
                Próximo →
              </button>
              <button v-else class="btn-iniciar" :disabled="mCriando" @click="criarSimulacao">
                <span v-if="mCriando" class="spin-sm"></span>
                <span v-else>✦</span>
                {{ mCriando ? 'Criando...' : 'Iniciar Simulação' }}
              </button>
            </div>

          </div>
        </div>
      </Transition>
    </Teleport>
  </AppShell>
</template>

<style scoped>
/* ═══ AUGUR Light Design System ═══ */
:deep(.app-content) {
  --bg-base: #f5f5fa;
  --bg-surface: #ffffff;
  --bg-raised: #fafafe;
  --bg-overlay: #f0f0f5;
  --border: #eeeef2;
  --border-md: #dddde5;
  --text-primary: #1a1a2e;
  --text-secondary: #444466;
  --text-muted: #8888aa;
  --accent: #00e5c3;
  --accent-dim: rgba(0,229,195,0.08);
  --accent2: #7c6ff7;
  --accent2-dim: rgba(124,111,247,0.08);
  --danger: #ff5a5a;
  --font-mono: 'JetBrains Mono', monospace;
}

.loading { display:flex; align-items:center; gap:10px; padding:48px; color:var(--text-muted); font-size:14px; }
.spinner { width:18px; height:18px; border:2px solid var(--border-md); border-top-color:var(--accent); border-radius:50%; animation:spin .8s linear infinite; }
@keyframes spin { to { transform:rotate(360deg) } }
.not-found { display:flex; flex-direction:column; align-items:center; gap:12px; padding:60px; color:var(--text-secondary); }
.page { display:flex; flex-direction:column; gap:16px; }

/* Projeto */
.proj-card { background:var(--bg-surface); border:1px solid var(--border); border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.04); padding:20px 24px; display:flex; align-items:center; justify-content:space-between; gap:16px; }
.proj-body { flex:1; }
.proj-nome { font-size:22px; font-weight:800; color:var(--text-primary); margin-bottom:6px; letter-spacing:-.4px; }
.proj-meta { font-size:12px; color:var(--text-muted); display:flex; align-items:center; gap:8px; }
.sep { opacity:.3; }
.proj-actions { display:flex; align-items:center; gap:10px; flex-shrink:0; }

/* Confirmação */
.confirm { background:rgba(255,90,90,.06); border:1px solid rgba(255,90,90,.2); border-radius:14px; padding:14px 18px; display:flex; align-items:center; justify-content:space-between; gap:16px; font-size:13px; color:var(--text-secondary); }
.confirm-btns { display:flex; gap:10px; }
.btn-danger { background:var(--danger); color:#fff; border:none; border-radius:8px; padding:7px 16px; font-size:12px; cursor:pointer; font-weight:600; }
.btn-danger:disabled { opacity:.5; }

/* Section */
.section-header { display:flex; align-items:center; justify-content:space-between; }
.section-titulo { font-size:16px; font-weight:700; color:var(--text-primary); margin:0; }
.btn-nova-sm { background:var(--accent2-dim); color:var(--accent2); border:1px solid rgba(124,111,247,.3); border-radius:8px; padding:6px 14px; font-size:12px; font-weight:600; cursor:pointer; transition:all .15s; }
.btn-nova-sm:hover { background:var(--accent2); color:#fff; }

/* Vazio */
.vazio { text-align:center; padding:56px 20px; background:var(--bg-surface); border:1px dashed var(--border-md); border-radius:14px; }
.vazio-emoji { font-size:52px; margin-bottom:14px; }
.vazio-titulo { font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:8px; }
.vazio-sub { font-size:13px; color:var(--text-secondary); max-width:380px; margin:0 auto; line-height:1.7; }

/* Simulações */
.sims { display:flex; flex-direction:column; gap:12px; }
.sim { background:var(--bg-surface); border:1px solid var(--border); border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.04); padding:16px 20px; transition:border-color .2s; }
.sim:hover { border-color:var(--border-md); }
.sim-running { border-color:rgba(245,166,35,.35)!important; }
.sim-done    { border-color:rgba(0,229,195,.2)!important; }
.sim-error   { border-color:rgba(255,90,90,.2)!important; }

.sim-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; gap:12px; }
.sim-left  { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.sim-right { display:flex; align-items:center; gap:8px; flex-shrink:0; }

.dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
.dot-green  { background:var(--accent); }
.dot-yellow { background:#f5a623; animation:pulse 1.4s infinite; }
.dot-purple { background:var(--accent2); }
.dot-red    { background:var(--danger); }
.dot-gray   { background:var(--text-muted); opacity:.4; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:.3} }

.sim-idx    { font-size:11px; color:var(--text-muted); font-family:var(--font-mono); }
.sim-status { font-size:12px; font-weight:600; color:var(--text-secondary); }
.sim-running .sim-status { color:#f5a623; }
.sim-done    .sim-status { color:var(--accent); }
.sim-error   .sim-status { color:var(--danger); }
.sim-data   { font-size:11px; color:var(--text-muted); }

.a-btn    { background:none; border:1px solid var(--border-md); color:var(--accent2); border-radius:8px; padding:5px 12px; font-size:12px; cursor:pointer; transition:all .15s; white-space:nowrap; }
.a-btn:hover { background:var(--accent2-dim); }
.a-run    { background:rgba(245,166,35,.1); border:1px solid rgba(245,166,35,.4); color:#f5a623; border-radius:8px; padding:5px 12px; font-size:12px; cursor:pointer; white-space:nowrap; }
.a-run:hover { background:rgba(245,166,35,.2); }
.a-report { background:rgba(0,229,195,.1); border:1px solid rgba(0,229,195,.3); color:var(--accent); border-radius:8px; padding:5px 12px; font-size:12px; cursor:pointer; white-space:nowrap; }
.a-report:hover { background:rgba(0,229,195,.2); }
.a-sec { background:none; border:1px solid var(--border); color:var(--text-muted); border-radius:8px; padding:5px 8px; font-size:12px; cursor:pointer; }
.a-sec:hover { color:var(--text-primary); }

.sim-hipotese { font-size:12px; color:var(--text-muted); line-height:1.6; margin-bottom:10px; border-left:2px solid var(--border-md); padding-left:10px; }

.sim-stats { display:flex; gap:24px; flex-wrap:wrap; margin-bottom:6px; }
.stat { display:flex; flex-direction:column; gap:2px; }
.sl { font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.5px; }
.sv { font-size:15px; font-weight:700; color:var(--text-primary); font-family:var(--font-mono); }
.sof { font-size:11px; font-weight:400; color:var(--text-muted); }
.sl-link { font-size:12px; font-weight:600; color:var(--accent2); cursor:pointer; }
.sl-link:hover { text-decoration:underline; }

.sim-prog { display:flex; align-items:center; gap:10px; margin-top:8px; }
.prog-bar { flex:1; height:4px; background:var(--border); border-radius:2px; overflow:hidden; }
.prog-fill { height:100%; border-radius:2px; background:var(--accent2); transition:width .4s; }
.pf-run  { background:#f5a623; animation:shimmer 1.5s infinite; }
.pf-done { background:var(--accent); }
@keyframes shimmer { 0%,100%{opacity:1}50%{opacity:.5} }
.prog-pct { font-size:11px; color:var(--text-muted); min-width:32px; text-align:right; font-family:var(--font-mono); }

/* Botões globais */
.btn-nova { background:var(--accent); color:#000; border:none; border-radius:8px; padding:9px 18px; font-size:13px; font-weight:700; cursor:pointer; transition:opacity .15s; white-space:nowrap; }
.btn-nova:hover { opacity:.85; }
.btn-del { background:none; border:1px solid var(--border); color:var(--text-muted); border-radius:8px; padding:7px 10px; cursor:pointer; font-size:14px; transition:all .15s; }
.btn-grafo { background:none; border:1px solid var(--border); color:var(--accent2); border-radius:8px; padding:7px 14px; cursor:pointer; font-size:13px; font-weight:600; transition:all .15s; }
.btn-grafo:hover { background:var(--accent2-dim); border-color:var(--accent2); }
.btn-del:hover { border-color:var(--danger); color:var(--danger); }
.btn-ghost { background:transparent; border:none; color:var(--text-secondary); cursor:pointer; font-size:13px; padding:8px 14px; border-radius:8px; transition:color .15s; }
.btn-ghost:hover { color:var(--text-primary); }

/* Transitions */
.slide-enter-active,.slide-leave-active { transition:all .2s ease; }
.slide-enter-from,.slide-leave-to { opacity:0; transform:translateY(-6px); }

/* Modal */
.overlay { position:fixed; inset:0; background:rgba(0,0,0,.72); display:flex; align-items:center; justify-content:center; z-index:1000; padding:16px; backdrop-filter:blur(4px); }
.modal { background:var(--bg-surface); border:1px solid var(--border-md); border-radius:16px; width:100%; max-width:500px; box-shadow:0 24px 64px rgba(0,0,0,.5); display:flex; flex-direction:column; max-height:90vh; overflow:hidden; }
.modal-head { padding:20px 22px 0; position:relative; flex-shrink:0; }
.modal-titulo { font-size:17px; font-weight:700; color:var(--text-primary); margin-bottom:2px; }
.modal-sub { font-size:12px; color:var(--text-muted); }
.modal-close { position:absolute; top:16px; right:18px; background:none; border:none; color:var(--text-muted); font-size:22px; cursor:pointer; line-height:1; }
.modal-close:hover { color:var(--text-primary); }
.modal-steps { display:flex; align-items:center; gap:8px; padding:14px 22px 0; flex-shrink:0; }
.mstep { display:flex; align-items:center; gap:6px; }
.mstep-dot { width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; background:var(--bg-raised); border:2px solid var(--border-md); color:var(--text-muted); transition:all .3s; }
.mstep.active .mstep-dot { background:var(--accent2); border-color:var(--accent2); color:#fff; }
.mstep.done   .mstep-dot { background:var(--accent);  border-color:var(--accent);  color:#000; }
.mstep-label { font-size:12px; color:var(--text-muted); margin-right:8px; }
.mstep.active .mstep-label { color:var(--accent2); font-weight:600; }
.modal-body { padding:16px 22px; display:flex; flex-direction:column; gap:14px; overflow-y:auto; }
.mf { display:flex; flex-direction:column; gap:6px; }
.ml { font-size:13px; font-weight:600; color:var(--text-secondary); }
.req { color:var(--accent); font-weight:400; }
.mh { font-size:11px; color:var(--text-muted); }
.mi { background:var(--bg-raised); border:1px solid var(--border-md); border-radius:8px; color:var(--text-primary); font-size:13px; padding:10px 12px; outline:none; transition:border-color .15s; width:100%; }
.mi:focus { border-color:var(--accent2); }
.mt { background:var(--bg-raised); border:1px solid var(--border-md); border-radius:8px; color:var(--text-primary); font-size:13px; padding:10px 12px; outline:none; resize:vertical; font-family:inherit; line-height:1.6; transition:border-color .15s; }
.mt:focus { border-color:var(--accent2); }
.btn-ia { background:var(--accent2); color:#fff; border:none; border-radius:8px; padding:8px 14px; font-size:12px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:7px; transition:all .2s; align-self:flex-start; }
.btn-ia:hover:not(:disabled) { opacity:.85; }
.btn-ia:disabled { opacity:.4; cursor:not-allowed; }
.spin-ia { width:12px; height:12px; border:2px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
.mresumo { background:var(--bg-raised); border-radius:8px; padding:10px 14px; border-left:3px solid var(--accent2); display:flex; flex-direction:column; gap:4px; }
.mresumo strong { font-size:13px; color:var(--text-primary); }
.mresumo span { font-size:12px; color:var(--text-muted); }
.mparam { display:flex; flex-direction:column; gap:7px; }
.mparam-h { display:flex; justify-content:space-between; align-items:center; }
.mparam-l { font-size:14px; font-weight:600; color:var(--text-primary); }
.mparam-v { font-size:24px; font-weight:800; color:var(--accent2); font-family:var(--font-mono); }
.mbounds { display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); }
.mdesc { font-size:12px; color:var(--text-secondary); background:var(--bg-raised); border-radius:8px; padding:7px 11px; }
.slider { width:100%; accent-color:var(--accent2); cursor:pointer; }
.mest { display:flex; background:var(--bg-raised); border:1px solid var(--border); border-radius:14px; overflow:hidden; }
.me { flex:1; padding:10px 12px; }
.mel { font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.4px; margin-bottom:3px; }
.mev { font-size:15px; font-weight:700; color:var(--text-primary); font-family:var(--font-mono); }
.mes { width:1px; background:var(--border); margin:8px 0; }
.ac  { color:var(--accent); }
.ac2 { color:var(--accent2); }
.modal-foot { padding:14px 22px; border-top:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; flex-shrink:0; }
.btn-prox { background:var(--accent2); color:#fff; border:none; border-radius:14px; padding:10px 20px; font-size:14px; font-weight:700; cursor:pointer; transition:all .2s; }
.btn-prox:hover:not(:disabled) { opacity:.85; }
.btn-prox:disabled { opacity:.3; cursor:not-allowed; }
.btn-iniciar { background:var(--accent); color:#000; border:none; border-radius:14px; padding:10px 20px; font-size:14px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:8px; transition:all .2s; }
.btn-iniciar:hover:not(:disabled) { opacity:.85; }
.btn-iniciar:disabled { opacity:.3; cursor:not-allowed; }
.spin-sm { width:13px; height:13px; border:2px solid rgba(0,0,0,.2); border-top-color:#000; border-radius:50%; animation:spin .7s linear infinite; }
.modal-enter-active { transition:all .3s cubic-bezier(.34,1.56,.64,1); }
.modal-leave-active { transition:all .2s ease; }
.modal-enter-from   { opacity:0; transform:scale(.93); }
.modal-leave-to     { opacity:0; transform:scale(.97); }
</style>
