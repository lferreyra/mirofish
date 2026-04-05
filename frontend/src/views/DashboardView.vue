<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const props = defineProps({ projectId: { type: String, default: '' } })
const router = useRouter()

const loading = ref(false)
const projetos = ref([])

async function carregarDados() {
  loading.value = true
  try {
    const [projRes, simRes] = await Promise.all([
      service.get('/api/graph/project/list'),
      service.get('/api/simulation/history', { params: { limit: 20 } })
    ])
    const projetosData = projRes.data || projRes
    const simsData = simRes.data || simRes
    const lista = Array.isArray(projetosData) ? projetosData : (projetosData.data || [])
    const sims = Array.isArray(simsData) ? simsData : (simsData.data || simsData.history || simsData.items || [])
    projetos.value = lista.map((p) => ({
      ...p,
      simulacoes: sims.filter((s) => String(s.project_id) === String(p.project_id))
    }))
  } finally {
    loading.value = false
  }
}

const projetosFiltrados = computed(() => {
  return [...projetos.value]
    .filter((p) => !props.projectId || String(p.project_id) === String(props.projectId))
    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
})

const formatarData = (v) => (v ? new Date(v).toLocaleString('pt-BR') : 'Data não informada')

const statusNorm = (status = '') => {
  const s = String(status).toLowerCase()
  if (s.includes('complete') || s.includes('conclu')) return 'completed'
  if (s.includes('running') || s.includes('exec')) return 'running'
  if (s.includes('prepar') || s.includes('build') || s.includes('generat')) return 'preparing'
  if (s.includes('fail') || s.includes('erro')) return 'failed'
  return 'draft'
}

const statusLabel = (status) => ({
  completed: 'Concluído',
  running: 'Em execução',
  preparing: 'Preparando',
  failed: 'Erro',
  draft: 'Sem simulações'
}[statusNorm(status)] || 'Sem simulações')

const truncar = (txt) => {
  if (!txt) return 'Hipótese não informada'
  return txt.length > 80 ? `${txt.slice(0, 80)}...` : txt
}

const abrirSimulacao = (sim) => {
  const status = statusNorm(sim.status || sim.runner_status)
  if (status === 'completed' && sim.report_id) return router.push(`/relatorio/${sim.report_id}`)
  if (status === 'running') return router.push(`/simulacao/${sim.simulation_id || sim.id}/executar`)
  return router.push(`/simulacao/${sim.project_id}`)
}

onMounted(carregarDados)
</script>

<template>
  <AppShell title="Dashboard">
    <template #actions>
      <AugurButton variant="ghost" @click="router.push('/novo')">Nova Simulação</AugurButton>
    </template>

    <section v-if="loading" class="empty">Carregando projetos...</section>

    <section v-else-if="!projetosFiltrados.length" class="empty">
      <h3>Nenhum projeto ainda</h3>
      <p>Crie sua primeira simulação para começar.</p>
      <AugurButton @click="router.push('/novo')">Nova Simulação</AugurButton>
    </section>

    <section v-else class="project-list">
      <article
        v-for="projeto in projetosFiltrados"
        :key="projeto.project_id"
        class="project-card"
        :class="{ running: projeto.simulacoes.some((s) => statusNorm(s.status || s.runner_status) === 'running') }"
      >
        <header>
          <div>
            <h3>{{ projeto.name || `Projeto ${projeto.project_id}` }}</h3>
            <small>{{ formatarData(projeto.created_at) }}</small>
          </div>
          <span class="badge" :class="projeto.simulacoes.length ? statusNorm(projeto.simulacoes[0].status || projeto.simulacoes[0].runner_status) : 'draft'">
            {{ projeto.simulacoes.length ? statusLabel(projeto.simulacoes[0].status || projeto.simulacoes[0].runner_status) : 'Sem simulações' }}
          </span>
        </header>

        <p class="meta">{{ projeto.simulacoes.length }} simulação(ões)</p>

        <div v-if="projeto.simulacoes.length" class="sim-list">
          <button
            v-for="sim in projeto.simulacoes"
            :key="sim.simulation_id"
            class="sim-item"
            @click="abrirSimulacao(sim)"
          >
            <div class="row">
              <strong>{{ truncar(sim.hypothesis || sim.objective || sim.name) }}</strong>
              <span class="badge" :class="statusNorm(sim.status || sim.runner_status)">{{ statusLabel(sim.status || sim.runner_status) }}</span>
            </div>
            <small>{{ sim.entities_count || sim.agent_count || 0 }} agentes · {{ sim.total_rounds || sim.rounds || 0 }} rodadas</small>
            <small class="link" v-if="sim.report_id">Ver relatório</small>
          </button>
        </div>

        <p v-else class="empty-inline">Sem simulações</p>
      </article>
    </section>
  </AppShell>
</template>

<style scoped>
.project-list { display: grid; gap: 12px; }
.project-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 14px; display: grid; gap: 10px; }
.project-card.running { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-dim) inset; }
header { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
h3 { margin: 0; }
small { color: var(--text-muted); }
.meta { margin: 0; color: var(--text-secondary); }
.sim-list { display: grid; gap: 8px; }
.sim-item { width: 100%; text-align: left; background: var(--bg-raised); border: 1px solid var(--border); border-radius: var(--r-sm); padding: 10px; cursor: pointer; color: var(--text-primary); }
.row { display: flex; justify-content: space-between; gap: 10px; }
.badge { padding: 3px 8px; border-radius: 999px; font-size: 12px; color: var(--text-primary); background: var(--bg-overlay); }
.badge.completed { color: #05231f; background: var(--accent); }
.badge.running { color: #1f1405; background: var(--warn); }
.badge.preparing { color: #f0edff; background: var(--accent2); }
.badge.failed { color: #fff; background: var(--danger); }
.badge.draft { color: var(--text-secondary); background: var(--bg-overlay); }
.link { color: var(--accent); }
.empty { background: var(--bg-surface); border: 1px dashed var(--border-md); border-radius: var(--r-md); padding: 24px; display: grid; gap: 8px; justify-items: start; }
.empty-inline { color: var(--text-muted); margin: 0; }
</style>
