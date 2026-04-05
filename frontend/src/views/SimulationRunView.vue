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

const route = useRoute()
const router = useRouter()
const status = ref({ current_round: 0, total_rounds: 0, progress: 0, posts_created: 0, active_agents: 0, dominant_tone: 'Neutro', topics: [], top_agents: [] })

const loadStatus = async () => {
  const response = await service.get(`/api/simulation/${route.params.simulationId}/run-status`)
  const raw = response.data || response
  status.value = { ...status.value, ...raw }
}

const stop = async () => {
  await service.post('/api/simulation/stop', { simulation_id: route.params.simulationId })
}

const toneTrend = computed(() => status.value.dominant_tone?.toLowerCase().includes('neg') ? 'down' : 'up')
const poll = usePolling(loadStatus, Number(import.meta.env.VITE_POLL_INTERVAL) || 5000)
onMounted(poll.start)
</script>
<template>
  <AppShell title="Execução ao vivo">
    <template #actions>
      <span class="round">Rodada {{ status.current_round }}/{{ status.total_rounds }}</span>
      <AugurButton variant="ghost" @click="stop">Pausar</AugurButton>
      <AugurButton @click="router.push(`/relatorio/${status.report_id || route.params.simulationId}`)">Ver Relatório</AugurButton>
    </template>

    <section class="metrics">
      <MetricCard title="Rodada" :value="status.current_round" sub="Atual" />
      <MetricCard title="Posts criados" :value="status.posts_created" sub="Volume total" trend="up" />
      <MetricCard title="Agentes ativos" :value="status.active_agents" sub="Online" trend="up" />
      <MetricCard title="Tom dominante" :value="status.dominant_tone" :sub="'Atualizado agora'" :trend="toneTrend" />
    </section>

    <AugurProgress :value="status.progress" :height="8" />

    <section class="layout">
      <div class="left">
        <AgentFeed :simulation-id="String(route.params.simulationId)" platform="twitter" />
        <AgentFeed :simulation-id="String(route.params.simulationId)" platform="reddit" />
        <div class="card">
          <h3>Timeline de rodadas — sentimento acumulado</h3>
          <RoundTimeline :current-round="status.current_round" :total-rounds="status.total_rounds || 30" :round-data="status.round_data || []" />
        </div>
      </div>
      <div class="right">
        <SentimentBar label="Sentimento — Twitter" :positive="status.twitter_sentiment?.positive || 52" :neutral="status.twitter_sentiment?.neutral || 30" :negative="status.twitter_sentiment?.negative || 18" />
        <SentimentBar label="Sentimento — Reddit" :positive="status.reddit_sentiment?.positive || 44" :neutral="status.reddit_sentiment?.neutral || 28" :negative="status.reddit_sentiment?.negative || 28" />
        <div class="card"><h3>Tópicos em alta</h3><div class="tags"><span v-for="topic in status.topics" :key="topic">{{ topic }}</span><span v-if="!status.topics?.length">#aguardando</span></div></div>
        <div class="card"><h3>Top agentes</h3><p v-for="agent in status.top_agents" :key="agent.name">{{ agent.name }} · {{ agent.interactions }} interações</p><p v-if="!status.top_agents?.length">Sem dados ainda.</p></div>
      </div>
    </section>
  </AppShell>
</template>
<style scoped>
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px}.round{padding:6px 10px;border-radius:999px;background:var(--accent-dim);color:var(--accent)}
.layout{margin-top:14px;display:grid;grid-template-columns:60% 40%;gap:12px}.left,.right{display:grid;gap:10px}
.card{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:12px}
.tags{display:flex;gap:8px;flex-wrap:wrap}.tags span{background:var(--bg-overlay);padding:4px 8px;border-radius:999px}
@media(max-width:1080px){.metrics{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}}
</style>
