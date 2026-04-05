<script setup>
import { computed, onMounted, ref, watch } from 'vue'
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

const route = useRoute()
const router = useRouter()

const status = ref({
  current_round: 0, total_rounds: 0, progress: 0,
  posts_created: 0, active_agents: 0, dominant_tone: 'Aguardando...',
  topics: [], top_agents: [], report_id: null,
  runner_status: null, status: null
})

const concluida = ref(false)
const parada = ref(false)
const erroExecucao = ref('')
const tentativasErro = ref(0)
const parando = ref(false)

// Status derivado
const simStatus = computed(() => status.value.runner_status || status.value.status)
const temRelatorio = computed(() => !!status.value.report_id)
const progresso = computed(() => {
  if (status.value.progress > 0) return status.value.progress
  if (status.value.total_rounds > 0) {
    return Math.round((status.value.current_round / status.value.total_rounds) * 100)
  }
  return 0
})
const toneTrend = computed(() => {
  const t = status.value.dominant_tone?.toLowerCase() || ''
  if (t.includes('neg') || t.includes('negat')) return 'down'
  return 'up'
})

async function carregarStatus() {
  try {
    const res = await service.get(`/api/simulation/${route.params.simulationId}/run-status`)
    const raw = res.data || res
    status.value = { ...status.value, ...raw }

    const s = simStatus.value
    if (s === 'completed' || s === 'finished' || progresso.value >= 100) {
      concluida.value = true
      poll.stop()
    } else if (s === 'stopped' || s === 'paused') {
      parada.value = true
      poll.stop()
    } else if (s === 'failed') {
      erroExecucao.value = raw.error || 'A simulação falhou durante a execução.'
      poll.stop()
    }
    tentativasErro.value = 0
  } catch (e) {
    tentativasErro.value++
    if (tentativasErro.value >= 5) {
      erroExecucao.value = 'Não foi possível obter o status da simulação. Verifique sua conexão.'
      poll.stop()
    }
  }
}

async function pararSimulacao() {
  parando.value = true
  try {
    await service.post('/api/simulation/stop', { simulation_id: route.params.simulationId })
    parada.value = true
    poll.stop()
  } catch (e) {
    console.error(e)
  } finally {
    parando.value = false
  }
}

function verRelatorio() {
  if (temRelatorio.value) {
    router.push(`/relatorio/${status.value.report_id}`)
  }
}

function voltarProjeto() {
  router.push(`/projeto/${status.value.project_id || route.params.simulationId}`)
}

const poll = usePolling(carregarStatus, 5000)
onMounted(poll.start)
</script>

<template>
  <AppShell :title="concluida ? '✅ Simulação Concluída' : parada ? '⏸ Simulação Parada' : '⏳ Execução ao vivo'">
    <template #actions>
      <span class="round-badge">
        Rodada {{ status.current_round }}/{{ status.total_rounds || '?' }}
      </span>
      <AugurButton
        v-if="!concluida && !parada && !erroExecucao"
        variant="ghost"
        :disabled="parando"
        @click="pararSimulacao"
      >
        {{ parando ? 'Parando...' : '⏸ Pausar' }}
      </AugurButton>
      <AugurButton
        v-if="temRelatorio"
        @click="verRelatorio"
      >
        📊 Ver Relatório
      </AugurButton>
      <AugurButton v-else-if="concluida && !temRelatorio" variant="ghost" disabled>
        Gerando relatório...
      </AugurButton>
    </template>

    <!-- Banner de conclusão -->
    <div v-if="concluida" class="banner banner-done">
      <div class="banner-icon">🎉</div>
      <div class="banner-body">
        <div class="banner-titulo">Simulação concluída com sucesso!</div>
        <div class="banner-sub">
          {{ temRelatorio
            ? 'O relatório com todos os insights está pronto para você.'
            : 'O relatório está sendo gerado. Aguarde alguns instantes...' }}
        </div>
      </div>
      <div class="banner-actions">
        <button v-if="temRelatorio" class="btn-relatorio" @click="verRelatorio">
          📊 Ver Relatório →
        </button>
        <div v-else class="gerando-relatorio">
          <div class="mini-spinner"></div>
          Gerando relatório...
        </div>
      </div>
    </div>

    <!-- Banner de parada -->
    <div v-else-if="parada" class="banner banner-paused">
      <div class="banner-icon">⏸</div>
      <div class="banner-body">
        <div class="banner-titulo">Simulação pausada</div>
        <div class="banner-sub">A execução foi interrompida na rodada {{ status.current_round }}.</div>
      </div>
      <button class="btn-ghost" @click="voltarProjeto">← Voltar ao projeto</button>
    </div>

    <!-- Banner de erro -->
    <div v-else-if="erroExecucao" class="banner banner-error">
      <div class="banner-icon">⚠️</div>
      <div class="banner-body">
        <div class="banner-titulo">Erro na execução</div>
        <div class="banner-sub">{{ erroExecucao }}</div>
      </div>
      <button class="btn-ghost" @click="voltarProjeto">← Voltar ao projeto</button>
    </div>

    <!-- Métricas -->
    <section class="metrics">
      <MetricCard title="Rodada atual" :value="status.current_round" :sub="`de ${status.total_rounds || '?'} rodadas`" />
      <MetricCard title="Posts criados" :value="status.posts_created" sub="Volume total" trend="up" />
      <MetricCard title="Agentes ativos" :value="status.active_agents" sub="Online agora" trend="up" />
      <MetricCard title="Tom dominante" :value="status.dominant_tone" sub="Sentimento geral" :trend="toneTrend" />
    </section>

    <!-- Barra de progresso com label -->
    <div class="prog-wrap">
      <AugurProgress :value="progresso" :height="10" />
      <div class="prog-info">
        <span class="prog-label">
          {{ concluida ? '✅ Concluída' : parada ? '⏸ Pausada' : `▶ Rodada ${status.current_round} de ${status.total_rounds || '?'}` }}
        </span>
        <span class="prog-pct">{{ progresso }}%</span>
      </div>
    </div>

    <!-- Layout principal -->
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
            <span v-if="!status.topics?.length" class="tag-vazio">Aguardando dados...</span>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">Top agentes</h3>
          <div v-if="status.top_agents?.length">
            <div v-for="agent in status.top_agents.slice(0,5)" :key="agent.name" class="agent-row">
              <span class="agent-name">{{ agent.name }}</span>
              <span class="agent-count">{{ agent.interactions }} interações</span>
            </div>
          </div>
          <p v-else class="sem-dados">Sem dados ainda. Aguarde as primeiras rodadas.</p>
        </div>

        <!-- Ação rápida ao relatório se concluída -->
        <div v-if="concluida" class="card card-cta">
          <div class="cta-icon">📊</div>
          <div class="cta-texto">
            <div class="cta-title">Análise pronta</div>
            <div class="cta-sub">{{ temRelatorio ? 'Veja os insights e métricas da simulação.' : 'Gerando relatório...' }}</div>
          </div>
          <button v-if="temRelatorio" class="btn-relatorio" @click="verRelatorio">Ver →</button>
          <div v-else class="mini-spinner"></div>
        </div>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
/* Badges e round */
.round-badge { padding: 6px 12px; border-radius: 999px; background: var(--accent-dim); color: var(--accent); font-size: 13px; font-weight: 500; font-family: var(--font-mono); }

/* Banners */
.banner {
  display: flex; align-items: center; gap: 16px;
  border-radius: 12px; padding: 16px 20px; margin-bottom: 4px;
}
.banner-done { background: rgba(0,229,195,0.08); border: 1px solid rgba(0,229,195,0.25); }
.banner-paused { background: rgba(124,111,247,0.07); border: 1px solid rgba(124,111,247,0.2); }
.banner-error { background: rgba(255,90,90,0.07); border: 1px solid rgba(255,90,90,0.2); }
.banner-icon { font-size: 28px; flex-shrink: 0; }
.banner-body { flex: 1; }
.banner-titulo { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 3px; }
.banner-sub { font-size: 13px; color: var(--text-secondary); }
.banner-actions { flex-shrink: 0; }

.btn-relatorio {
  background: var(--accent); color: #000; border: none; border-radius: 8px;
  padding: 9px 18px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s;
}
.btn-relatorio:hover { opacity: 0.85; }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; transition: all 0.15s; }
.btn-ghost:hover { color: var(--text-primary); border-color: var(--border-md); }

.gerando-relatorio { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
.mini-spinner { width: 14px; height: 14px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Métricas */
.metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 12px; }

/* Progresso */
.prog-wrap { display: flex; flex-direction: column; gap: 6px; margin-bottom: 4px; }
.prog-info { display: flex; justify-content: space-between; font-size: 12px; }
.prog-label { color: var(--text-secondary); }
.prog-pct { color: var(--text-muted); font-family: var(--font-mono); }

/* Layout */
.layout { margin-top: 14px; display: grid; grid-template-columns: 60% 40%; gap: 12px; }
.left, .right { display: flex; flex-direction: column; gap: 10px; }

.card { background: var(--bg-raised); border: 1px solid var(--border); border-radius: var(--r-md); padding: 14px; }
.card-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 0 0 10px; }

.tags { display: flex; gap: 8px; flex-wrap: wrap; }
.tags span { background: var(--bg-overlay); padding: 4px 10px; border-radius: 999px; font-size: 12px; color: var(--text-secondary); }
.tag-vazio { color: var(--text-muted); font-style: italic; font-size: 12px; }

.agent-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.agent-row:last-child { border-bottom: none; }
.agent-name { color: var(--text-primary); }
.agent-count { color: var(--text-muted); font-family: var(--font-mono); font-size: 12px; }
.sem-dados { font-size: 12px; color: var(--text-muted); font-style: italic; margin: 0; }

/* CTA card */
.card-cta { display: flex; align-items: center; gap: 12px; border-color: rgba(0,229,195,0.2); background: rgba(0,229,195,0.04); }
.cta-icon { font-size: 24px; }
.cta-texto { flex: 1; }
.cta-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cta-sub { font-size: 12px; color: var(--text-muted); }

@media (max-width: 1080px) {
  .metrics { grid-template-columns: repeat(2,1fr); }
  .layout { grid-template-columns: 1fr; }
}
</style>
