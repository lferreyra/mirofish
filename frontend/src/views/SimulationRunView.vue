<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import MetricCard from '../components/ui/MetricCard.vue'
import AugurProgress from '../components/ui/AugurProgress.vue'
import SentimentBar from '../components/ui/SentimentBar.vue'
import AgentFeed from '../components/simulation/AgentFeed.vue'
import RoundTimeline from '../components/simulation/RoundTimeline.vue'
import service from '../api'
import { usePolling } from '../composables/usePolling'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()

// ─── Estado principal ─────────────────────────────────────────
const status = ref({
  current_round: 0, total_rounds: 0, progress_percent: 0,
  posts_created: 0, active_agents: 0, dominant_tone: 'Aguardando...',
  topics: [], top_agents: [], report_id: null,
  runner_status: null, project_id: null,
  twitter_actions_count: 0, reddit_actions_count: 0,
  twitter_sentiment: null, reddit_sentiment: null,
  round_data: []
})

// ─── Estado de fase ───────────────────────────────────────────
const concluida   = ref(false)
const parada      = ref(false)
const erroExec    = ref('')
const parando     = ref(false)
const erroCount   = ref(0)

// ─── Estado de geração de relatório ──────────────────────────
const gerandoRelatorio = ref(false)
const reportTaskId     = ref(null)
const reportPollTimer  = ref(null)

// ─── Computed ─────────────────────────────────────────────────
const simStatus   = computed(() => status.value.runner_status || status.value.status)
const temRelatorio = computed(() => !!status.value.report_id)

// FIX: backend retorna progress_percent, não progress
const progresso = computed(() => {
  if (status.value.progress_percent > 0) return Math.round(status.value.progress_percent)
  if (status.value.total_rounds > 0 && status.value.current_round > 0) {
    return Math.round((status.value.current_round / status.value.total_rounds) * 100)
  }
  return 0
})

const toneTrend = computed(() => {
  const t = (status.value.dominant_tone || '').toLowerCase()
  return (t.includes('neg') || t.includes('negat') || t.includes('critic')) ? 'down' : 'up'
})

const pageTitle = computed(() => {
  if (concluida.value) return '✅ Simulação Concluída'
  if (parada.value) return '⏸ Simulação Parada'
  if (erroExec.value) return '❌ Erro na Execução'
  return '⏳ Execução ao vivo'
})

// ─── Polling de status ────────────────────────────────────────
async function carregarStatus() {
  try {
    const res = await service.get(`/api/simulation/${route.params.simulationId}/run-status`)
    const raw = res.data?.data || res.data || res
    status.value = { ...status.value, ...raw }

    const s = simStatus.value

    if ((s === 'completed' || s === 'finished') && !concluida.value) {
      concluida.value = true
      poll.stop()
      toast.success('🎉 Simulação concluída! Gerando relatório...', 5000)
      await iniciarGeracaoRelatorio()
    } else if ((s === 'stopped' || s === 'paused') && !parada.value) {
      parada.value = true
      poll.stop()
      toast.warn('Simulação interrompida na rodada ' + status.value.current_round)
    } else if (s === 'failed' && !erroExec.value) {
      erroExec.value = raw.error || 'A simulação falhou durante a execução.'
      poll.stop()
      toast.error('Erro na execução da simulação')
    }

    erroCount.value = 0
  } catch (e) {
    erroCount.value++
    if (erroCount.value >= 5) {
      erroExec.value = 'Não foi possível conectar ao servidor. Verifique sua conexão e recarregue a página.'
      poll.stop()
    }
  }
}

// ─── Gerar relatório automaticamente ─────────────────────────
async function iniciarGeracaoRelatorio() {
  // Verificar se já existe relatório (pode ter sido gerado antes)
  try {
    const check = await service.get(`/api/report/by-simulation/${route.params.simulationId}`)
    const data = check.data?.data || check.data || check
    if (data?.report_id) {
      status.value.report_id = data.report_id
      toast.success('📊 Relatório disponível!', 5000)
      return
    }
  } catch { /* não existe ainda, gerar */ }

  gerandoRelatorio.value = true
  try {
    const res = await service.post('/api/report/generate', {
      simulation_id: route.params.simulationId
    })
    const data = res.data?.data || res.data || res
    reportTaskId.value = data.task_id || null

    // Se já tem report_id direto na resposta
    if (data.report_id) {
      status.value.report_id = data.report_id
      gerandoRelatorio.value = false
      toast.success('📊 Relatório disponível!', 5000)
      return
    }

    // Polling do status do relatório
    pollRelatorio()
  } catch (e) {
    gerandoRelatorio.value = false
    toast.error('Não foi possível gerar o relatório automaticamente. Tente manualmente.')
  }
}

function pollRelatorio() {
  let tentativas = 0
  const maxTentativas = 60 // 5 minutos

  reportPollTimer.value = setInterval(async () => {
    tentativas++
    if (tentativas > maxTentativas) {
      clearInterval(reportPollTimer.value)
      gerandoRelatorio.value = false
      toast.warn('O relatório está demorando. Tente acessá-lo pelo projeto.')
      return
    }

    try {
      const payload = {}
      if (reportTaskId.value) payload.task_id = reportTaskId.value
      payload.simulation_id = route.params.simulationId

      const res = await service.post('/api/report/generate/status', payload)
      const data = res.data?.data || res.data || res

      if (data.status === 'completed' || data.report_id) {
        clearInterval(reportPollTimer.value)
        gerandoRelatorio.value = false

        // Buscar report_id se não veio
        if (data.report_id) {
          status.value.report_id = data.report_id
        } else {
          try {
            const check = await service.get(`/api/report/by-simulation/${route.params.simulationId}`)
            const d = check.data?.data || check.data || check
            if (d?.report_id) status.value.report_id = d.report_id
          } catch { /* ignorar */ }
        }

        if (status.value.report_id) {
          toast.success('📊 Relatório pronto! Clique para visualizar.', 8000)
        }
      } else if (data.status === 'failed') {
        clearInterval(reportPollTimer.value)
        gerandoRelatorio.value = false
        toast.error('Falha ao gerar relatório. Tente novamente pelo projeto.')
      }
    } catch { /* ignorar erros transientes */ }
  }, 5000)
}

// ─── Parar simulação ──────────────────────────────────────────
async function pararSimulacao() {
  parando.value = true
  try {
    await service.post('/api/simulation/stop', { simulation_id: route.params.simulationId })
    parada.value = true
    poll.stop()
    toast.warn('Simulação pausada na rodada ' + status.value.current_round)
  } catch (e) {
    toast.error('Não foi possível pausar a simulação.')
  } finally {
    parando.value = false
  }
}

function verRelatorio() {
  if (temRelatorio.value) router.push(`/relatorio/${status.value.report_id}`)
}

function voltarProjeto() {
  const pid = status.value.project_id
  if (pid) router.push(`/projeto/${pid}`)
  else router.push('/')
}

const poll = usePolling(carregarStatus, 5000)

// ─── Carregar project_id (não vem no run-status) ──────────────
async function carregarProjectId() {
  try {
    // Tenta via simulation list para obter project_id
    const res = await service.get('/api/simulation/list', {
      params: { limit: 100 }
    })
    const raw = res?.data?.data || res?.data || res
    const lista = Array.isArray(raw) ? raw : (raw?.simulations || raw?.history || [])
    const sim = lista.find(s => s.simulation_id === route.params.simulationId)
    if (sim?.project_id) {
      status.value.project_id = sim.project_id
    }
  } catch { /* ignorar — voltarProjeto cai em '/' */ }
}

onMounted(() => {
  carregarProjectId()
  poll.start()
})
</script>

<template>
  <AppShell :title="pageTitle">
    <template #actions>
      <span class="round-badge">
        Rodada {{ status.current_round }}/{{ status.total_rounds || '?' }}
      </span>
      <AugurButton
        v-if="!concluida && !parada && !erroExec"
        variant="ghost"
        :disabled="parando"
        @click="pararSimulacao"
      >
        {{ parando ? 'Parando...' : '⏸ Pausar' }}
      </AugurButton>
      <AugurButton v-if="temRelatorio" @click="verRelatorio">
        📊 Ver Relatório
      </AugurButton>
      <div v-else-if="gerandoRelatorio" class="btn-gerando">
        <div class="mini-spinner"></div>
        Gerando relatório...
      </div>
      <AugurButton variant="ghost" @click="voltarProjeto">
        ← Projeto
      </AugurButton>
    </template>

    <!-- ─── BANNER CONCLUSÃO ─── -->
    <Transition name="banner">
      <div v-if="concluida" class="banner banner-done">
        <div class="banner-icon">🎉</div>
        <div class="banner-body">
          <div class="banner-titulo">Simulação concluída com sucesso!</div>
          <div class="banner-sub" v-if="temRelatorio">
            O relatório com todos os insights está pronto. Clique para visualizar.
          </div>
          <div class="banner-sub" v-else-if="gerandoRelatorio">
            Analisando os dados e gerando o relatório... Isso pode levar alguns minutos.
          </div>
          <div class="banner-sub" v-else>
            A análise foi concluída. Acesse o projeto para ver os resultados.
          </div>
        </div>
        <div class="banner-actions">
          <button v-if="temRelatorio" class="btn-relatorio" @click="verRelatorio">
            📊 Ver Relatório →
          </button>
          <div v-else-if="gerandoRelatorio" class="gerando-wrap">
            <div class="mini-spinner"></div>
            <span>Gerando relatório...</span>
          </div>
          <button v-else class="btn-ghost" @click="voltarProjeto">← Ver Projeto</button>
        </div>
      </div>
    </Transition>

    <!-- ─── BANNER PARADA ─── -->
    <Transition name="banner">
      <div v-if="parada && !concluida" class="banner banner-paused">
        <div class="banner-icon">⏸</div>
        <div class="banner-body">
          <div class="banner-titulo">Simulação pausada</div>
          <div class="banner-sub">
            Interrompida na rodada {{ status.current_round }} de {{ status.total_rounds || '?' }}.
            Os dados até aqui foram salvos.
          </div>
        </div>
        <button class="btn-ghost" @click="voltarProjeto">← Voltar ao projeto</button>
      </div>
    </Transition>

    <!-- ─── BANNER ERRO ─── -->
    <Transition name="banner">
      <div v-if="erroExec" class="banner banner-error">
        <div class="banner-icon">⚠️</div>
        <div class="banner-body">
          <div class="banner-titulo">Erro na execução</div>
          <div class="banner-sub">{{ erroExec }}</div>
        </div>
        <button class="btn-ghost" @click="voltarProjeto">← Voltar ao projeto</button>
      </div>
    </Transition>

    <!-- ─── MÉTRICAS ─── -->
    <section class="metrics">
      <MetricCard
        title="Rodada atual"
        :value="status.current_round"
        :sub="`de ${status.total_rounds || '?'} rodadas`"
      />
      <MetricCard
        title="Interações totais"
        :value="status.twitter_actions_count + status.reddit_actions_count"
        sub="Posts + comentários"
        trend="up"
      />
      <MetricCard
        title="Agentes ativos"
        :value="status.active_agents"
        sub="Online agora"
        trend="up"
      />
      <MetricCard
        title="Tom dominante"
        :value="status.dominant_tone"
        sub="Sentimento geral"
        :trend="toneTrend"
      />
    </section>

    <!-- ─── PROGRESSO ─── -->
    <div class="prog-wrap">
      <AugurProgress :value="progresso" :height="10" />
      <div class="prog-info">
        <span class="prog-label">
          <span v-if="concluida">✅ Concluída</span>
          <span v-else-if="parada">⏸ Pausada na rodada {{ status.current_round }}</span>
          <span v-else-if="erroExec">❌ Erro</span>
          <span v-else>▶ Rodada {{ status.current_round }} de {{ status.total_rounds || '?' }}</span>
        </span>
        <span class="prog-pct">{{ progresso }}%</span>
      </div>
    </div>

    <!-- ─── LAYOUT PRINCIPAL ─── -->
    <section class="layout">
      <div class="left">
        <AgentFeed :simulation-id="String(route.params.simulationId)" platform="twitter" />
        <AgentFeed :simulation-id="String(route.params.simulationId)" platform="reddit" />
        <div class="card">
          <h3 class="card-title">Timeline de rodadas — sentimento acumulado</h3>
          <RoundTimeline
            :current-round="status.current_round"
            :total-rounds="status.total_rounds || 30"
            :round-data="status.round_data || []"
          />
        </div>
      </div>

      <div class="right">
        <SentimentBar
          label="Sentimento — Twitter"
          :positive="status.twitter_sentiment?.positive || 0"
          :neutral="status.twitter_sentiment?.neutral || 0"
          :negative="status.twitter_sentiment?.negative || 0"
        />
        <SentimentBar
          label="Sentimento — Reddit"
          :positive="status.reddit_sentiment?.positive || 0"
          :neutral="status.reddit_sentiment?.neutral || 0"
          :negative="status.reddit_sentiment?.negative || 0"
        />

        <div class="card">
          <h3 class="card-title">Tópicos em alta</h3>
          <div class="tags">
            <span v-for="topic in status.topics" :key="topic">{{ topic }}</span>
            <span v-if="!status.topics?.length" class="tag-vazio">Aguardando dados das primeiras rodadas...</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Top agentes</h3>
          <div v-if="status.top_agents?.length">
            <div v-for="(agent, i) in status.top_agents.slice(0,5)" :key="agent.name" class="agent-row">
              <div class="agent-rank">#{{ i + 1 }}</div>
              <span class="agent-name">{{ agent.name }}</span>
              <span class="agent-count">{{ agent.interactions }} interações</span>
            </div>
          </div>
          <p v-else class="sem-dados">Aguardando primeiras rodadas...</p>
        </div>

        <!-- Card CTA relatório quando concluída -->
        <Transition name="cta">
          <div v-if="concluida" class="card card-cta">
            <div class="cta-icon">📊</div>
            <div class="cta-texto">
              <div class="cta-title">
                {{ temRelatorio ? 'Análise pronta!' : 'Gerando análise...' }}
              </div>
              <div class="cta-sub">
                {{ temRelatorio
                  ? 'Veja insights, sentimento e métricas detalhadas.'
                  : 'Processando dados da simulação. Aguarde...' }}
              </div>
            </div>
            <button v-if="temRelatorio" class="btn-relatorio" @click="verRelatorio">Ver →</button>
            <div v-else class="mini-spinner"></div>
          </div>
        </Transition>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.round-badge {
  padding: 6px 12px; border-radius: 999px;
  background: var(--accent-dim); color: var(--accent);
  font-size: 13px; font-weight: 500; font-family: var(--font-mono);
}
.btn-gerando {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-muted); padding: 6px 12px;
}

/* Banners */
.banner {
  display: flex; align-items: center; gap: 16px;
  border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
}
.banner-done   { background: rgba(0,229,195,0.08);   border: 1px solid rgba(0,229,195,0.25); }
.banner-paused { background: rgba(124,111,247,0.07); border: 1px solid rgba(124,111,247,0.2); }
.banner-error  { background: rgba(255,90,90,0.07);   border: 1px solid rgba(255,90,90,0.2); }
.banner-icon   { font-size: 28px; flex-shrink: 0; }
.banner-body   { flex: 1; }
.banner-titulo { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 3px; }
.banner-sub    { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
.banner-actions { flex-shrink: 0; }
.gerando-wrap  { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }

.btn-relatorio {
  background: var(--accent); color: #000; border: none; border-radius: 8px;
  padding: 9px 18px; font-size: 13px; font-weight: 700; cursor: pointer;
  transition: opacity 0.15s; white-space: nowrap;
}
.btn-relatorio:hover { opacity: 0.85; }
.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  border-radius: 8px; padding: 8px 14px; font-size: 13px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.btn-ghost:hover { color: var(--text-primary); border-color: var(--border-md); }

.mini-spinner {
  width: 14px; height: 14px; border: 2px solid var(--border-md);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.8s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Métricas */
.metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 14px; }

/* Progresso */
.prog-wrap { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.prog-info { display: flex; justify-content: space-between; font-size: 12px; }
.prog-label { color: var(--text-secondary); }
.prog-pct { color: var(--text-muted); font-family: var(--font-mono); }

/* Layout */
.layout { display: grid; grid-template-columns: 60% 40%; gap: 12px; }
.left, .right { display: flex; flex-direction: column; gap: 10px; }

.card { background: var(--bg-raised); border: 1px solid var(--border); border-radius: var(--r-md); padding: 14px; }
.card-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 10px; }

.tags { display: flex; gap: 8px; flex-wrap: wrap; }
.tags span { background: var(--bg-overlay); padding: 4px 10px; border-radius: 999px; font-size: 12px; color: var(--text-secondary); }
.tag-vazio { color: var(--text-muted); font-style: italic; font-size: 12px; }

.agent-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.agent-row:last-child { border-bottom: none; }
.agent-rank { font-size: 10px; color: var(--text-muted); font-family: var(--font-mono); min-width: 20px; }
.agent-name { flex: 1; color: var(--text-primary); }
.agent-count { color: var(--text-muted); font-family: var(--font-mono); font-size: 11px; }
.sem-dados { font-size: 12px; color: var(--text-muted); font-style: italic; margin: 0; }

.card-cta { display: flex; align-items: center; gap: 12px; border-color: rgba(0,229,195,0.2); background: rgba(0,229,195,0.04); }
.cta-icon { font-size: 24px; flex-shrink: 0; }
.cta-texto { flex: 1; }
.cta-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cta-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* Transitions */
.banner-enter-active { transition: all 0.4s cubic-bezier(0.34,1.56,0.64,1); }
.banner-leave-active { transition: all 0.2s ease; }
.banner-enter-from  { opacity: 0; transform: translateY(-12px) scale(0.97); }
.banner-leave-to    { opacity: 0; transform: translateY(-8px); }
.cta-enter-active   { transition: all 0.4s cubic-bezier(0.34,1.56,0.64,1); }
.cta-enter-from     { opacity: 0; transform: scale(0.95); }

@media (max-width: 1080px) {
  .metrics { grid-template-columns: repeat(2,1fr); }
  .layout  { grid-template-columns: 1fr; }
}
</style>
