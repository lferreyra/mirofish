<script setup>
import { onMounted, ref } from 'vue'
import * as d3 from 'd3'
import { useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import MetricCard from '../components/ui/MetricCard.vue'
import SentimentBar from '../components/ui/SentimentBar.vue'
import SimulationCard from '../components/simulation/SimulationCard.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const router = useRouter()
const simulations = ref([])
const metrics = ref({ simulations: 0, agents: 0, accuracy: '0%', reports: 0 })
const activitySvg = ref(null)

const fetchHistory = async () => {
  const response = await service.get('/api/simulation/history', { params: { limit: 10 } })
  const raw = response.data || response
  simulations.value = raw.history || raw.items || raw.simulations || []
  metrics.value = {
    simulations: simulations.value.length,
    agents: simulations.value.reduce((acc, s) => acc + (s.agent_count || 0), 0),
    accuracy: `${Math.round((simulations.value.reduce((acc, s) => acc + (s.accuracy || 0), 0) / (simulations.value.length || 1)) * 100)}%`,
    reports: simulations.value.filter((s) => s.report_id).length
  }
  renderBars()
}

const openSimulation = (sim) => {
  if (sim.status === 'running') return router.push(`/simulacao/${sim.id || sim.simulation_id}/executar`)
  if (sim.report_id) return router.push(`/relatorio/${sim.report_id}`)
  return router.push(`/simulacao/${sim.project_id || sim.id}`)
}

const renderBars = () => {
  if (!activitySvg.value) return
  const data = simulations.value.slice(0, 7).map((s, i) => ({ day: i + 1, value: s.activity || s.posts_created || Math.round(Math.random() * 100) + 10 }))
  const svg = d3.select(activitySvg.value)
  svg.selectAll('*').remove()
  const width = 360
  const height = 170
  const x = d3.scaleBand().domain(data.map((d) => d.day)).range([0, width]).padding(0.2)
  const y = d3.scaleLinear().domain([0, d3.max(data, (d) => d.value) || 1]).range([height, 0])
  svg.attr('viewBox', `0 0 ${width} ${height}`)
  svg.selectAll('rect').data(data).enter().append('rect').attr('x', (d) => x(d.day)).attr('y', (d) => y(d.value)).attr('width', x.bandwidth()).attr('height', (d) => height - y(d.value)).attr('fill', '#00e5c3').attr('rx', 4)
}

onMounted(fetchHistory)
</script>

<template>
  <AppShell title="Dashboard">
    <template #actions>
      <AugurButton variant="ghost" @click="$router.push('/novo')">+ Nova Simulação</AugurButton>
    </template>

    <section class="grid-metrics">
      <MetricCard title="Simulações" :value="metrics.simulations" sub="Projetos monitorados" trend="up" />
      <MetricCard title="Agentes Totais" :value="metrics.agents" sub="Base ativa" trend="up" />
      <MetricCard title="Precisão Média" :value="metrics.accuracy" sub="Últimos relatórios" trend="up" />
      <MetricCard title="Relatórios" :value="metrics.reports" sub="Concluídos" />
    </section>

    <section class="grid-main">
      <div class="list">
        <h3>Simulações Recentes</h3>
        <SimulationCard v-for="sim in simulations" :key="sim.id || sim.simulation_id" :simulation="sim" @click="openSimulation" />
        <p v-if="!simulations.length" class="empty">Nenhuma simulação ainda. Crie sua primeira simulação para começar.</p>
      </div>
      <div class="right">
        <div class="chart">
          <h3>Atividade dos Agentes</h3>
          <svg ref="activitySvg" />
        </div>
        <SentimentBar label="Sentimento médio — última semana" :positive="58" :neutral="27" :negative="15" />
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.grid-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.grid-main{margin-top:18px;display:grid;grid-template-columns:1.1fr .9fr;gap:14px}
.list,.chart,.right{display:grid;gap:10px}
.empty{background:var(--bg-raised);border:1px dashed var(--border-md);padding:20px;border-radius:var(--r-md);color:var(--text-secondary)}
.chart{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:12px}
svg{width:100%;height:170px}
@media (max-width: 1080px){.grid-metrics{grid-template-columns:repeat(2,1fr)}.grid-main{grid-template-columns:1fr}}
</style>
