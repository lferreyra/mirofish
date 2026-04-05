<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import MetricCard from '../components/ui/MetricCard.vue'

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
  } catch (e) {
    console.error(e)
  } finally {
    carregando.value = false
  }
}

const metrics = computed(() => ({
  projetos: projetos.value.length,
  simulacoes: simulacoes.value.length,
  agentes: simulacoes.value.reduce((a, s) => a + (s.entities_count || s.agent_count || 0), 0),
  relatorios: simulacoes.value.filter(s => s.report_id).length
}))

const emExecucao = computed(() =>
  simulacoes.value.filter(s => (s.runner_status || s.status) === 'running')
)

const recentes = computed(() => projetos.value.slice(0, 6))

function badgeProjeto(p) {
  const sim = simulacoes.value
    .filter(s => s.project_id === (p.project_id || p.id))
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))[0]
  const simStatus = sim ? (sim.runner_status || sim.status) : null
  if (simStatus === 'running') return { label: '⏳ Em execução', cls: 'b-running' }
  if (simStatus === 'completed') return { label: '✅ Concluído', cls: 'b-done' }
  if (p.status === 'graph_building') return { label: '⚙️ Construindo', cls: 'b-building' }
  if (p.status === 'graph_completed') return { label: 'Pronto', cls: 'b-ready' }
  return { label: 'Criado', cls: 'b-draft' }
}

function formatarData(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function simCount(p) {
  return simulacoes.value.filter(s => s.project_id === (p.project_id || p.id)).length
}

onMounted(carregar)
</script>

<template>
  <AppShell title="Dashboard">
    <template #actions>
      <button class="btn-nova" @click="router.push('/projeto/novo')">+ Novo Projeto</button>
    </template>

    <!-- Métricas -->
    <section class="metrics">
      <MetricCard title="Projetos" :value="metrics.projetos" sub="No workspace" trend="up" />
      <MetricCard title="Simulações" :value="metrics.simulacoes" sub="Total executadas" trend="up" />
      <MetricCard title="Agentes" :value="metrics.agentes" sub="Criados no total" trend="up" />
      <MetricCard title="Relatórios" :value="metrics.relatorios" sub="Concluídos" />
    </section>

    <!-- Carregando -->
    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando workspace...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="projetos.length === 0" class="empty">
      <div class="empty-icon">🔭</div>
      <div class="empty-title">Bem-vindo ao AUGUR</div>
      <div class="empty-sub">
        Crie seu primeiro projeto para começar a prever como o mercado vai reagir
        antes de lançar seu produto, marca ou serviço.
      </div>
      <button class="btn-nova-lg" @click="router.push('/projeto/novo')">
        ✦ Criar primeiro projeto
      </button>
    </div>

    <div v-else>

      <!-- Em execução -->
      <div v-if="emExecucao.length" class="alert-execucao">
        <span class="alert-dot"></span>
        <span>
          {{ emExecucao.length }} simulação{{ emExecucao.length > 1 ? 'ões' : '' }} em execução agora
        </span>
        <button class="alert-link" @click="router.push(`/simulacao/${emExecucao[0].simulation_id}/executar`)">
          Acompanhar →
        </button>
      </div>

      <!-- Projetos recentes -->
      <div class="section-header">
        <h3 class="section-title">Projetos recentes</h3>
        <span class="section-sub">Clique para ver simulações e relatórios</span>
      </div>

      <div class="projetos-grid">
        <div
          v-for="p in recentes"
          :key="p.project_id || p.id"
          class="projeto-card"
          @click="router.push(`/projeto/${p.project_id || p.id}`)"
        >
          <div class="card-top">
            <span :class="['badge', badgeProjeto(p).cls]">{{ badgeProjeto(p).label }}</span>
            <span class="card-data">{{ formatarData(p.created_at) }}</span>
          </div>
          <div class="card-nome">{{ p.name || 'Projeto sem nome' }}</div>
          <div v-if="p.simulation_requirement" class="card-briefing">
            {{ p.simulation_requirement.length > 90
              ? p.simulation_requirement.slice(0, 90) + '...'
              : p.simulation_requirement }}
          </div>
          <div class="card-footer">
            <span class="card-meta">{{ simCount(p) }} simulação{{ simCount(p) !== 1 ? 'ões' : '' }}</span>
            <span class="card-meta">{{ (p.files || []).length }} arquivo{{ (p.files || []).length !== 1 ? 's' : '' }}</span>
            <span class="card-arrow">›</span>
          </div>
        </div>

        <!-- Card de adicionar -->
        <div class="projeto-card card-add" @click="router.push('/projeto/novo')">
          <div class="card-add-icon">+</div>
          <div class="card-add-label">Novo Projeto</div>
        </div>
      </div>

      <div v-if="projetos.length > 6" class="ver-mais">
        Veja todos os {{ projetos.length }} projetos no menu lateral
      </div>
    </div>

  </AppShell>
</template>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 28px; }

.btn-nova { background: var(--accent); color: #000; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s; }
.btn-nova:hover { opacity: 0.85; }

.loading { display: flex; align-items: center; gap: 12px; padding: 48px; color: var(--text-muted); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty { text-align: center; padding: 64px 20px; }
.empty-icon { font-size: 56px; margin-bottom: 20px; }
.empty-title { font-size: 24px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.empty-sub { font-size: 14px; color: var(--text-secondary); max-width: 460px; margin: 0 auto 28px; line-height: 1.8; }
.btn-nova-lg { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 13px 28px; font-size: 15px; font-weight: 700; cursor: pointer; transition: opacity 0.15s; }
.btn-nova-lg:hover { opacity: 0.85; }

.alert-execucao {
  display: flex; align-items: center; gap: 10px;
  background: rgba(245,166,35,0.08); border: 1px solid rgba(245,166,35,0.25);
  border-radius: 10px; padding: 12px 16px; margin-bottom: 20px;
  font-size: 13px; color: #f5a623;
}
.alert-dot { width: 8px; height: 8px; border-radius: 50%; background: #f5a623; animation: pulse 1.4s infinite; flex-shrink: 0; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
.alert-link { margin-left: auto; background: none; border: 1px solid rgba(245,166,35,0.4); color: #f5a623; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.alert-link:hover { background: rgba(245,166,35,0.1); }

.section-header { margin-bottom: 14px; }
.section-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.section-sub { font-size: 12px; color: var(--text-muted); }

.projetos-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }

.projeto-card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 18px;
  cursor: pointer; transition: all 0.18s;
  display: flex; flex-direction: column; gap: 8px;
}
.projeto-card:hover { border-color: var(--border-md); background: var(--bg-raised); transform: translateY(-1px); }

.card-top { display: flex; align-items: center; justify-content: space-between; }
.card-data { font-size: 11px; color: var(--text-muted); }
.card-nome { font-size: 14px; font-weight: 600; color: var(--text-primary); line-height: 1.4; }
.card-briefing { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
.card-footer { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.card-meta { font-size: 11px; color: var(--text-muted); background: var(--bg-overlay); padding: 2px 7px; border-radius: 20px; }
.card-arrow { margin-left: auto; font-size: 18px; color: var(--text-muted); }

.card-add {
  border-style: dashed; border-color: var(--border-md);
  align-items: center; justify-content: center;
  min-height: 120px; color: var(--text-muted);
}
.card-add:hover { border-color: var(--accent); color: var(--accent); }
.card-add-icon { font-size: 28px; font-weight: 200; margin-bottom: 6px; }
.card-add-label { font-size: 13px; font-weight: 500; }

.ver-mais { font-size: 12px; color: var(--text-muted); text-align: center; margin-top: 16px; }

/* Badges */
.badge { padding: 3px 8px; border-radius: 20px; font-size: 11px; font-weight: 500; }
.b-done { background: rgba(0,229,195,0.1); color: var(--accent); }
.b-running { background: rgba(245,166,35,0.1); color: #f5a623; }
.b-ready { background: rgba(0,229,195,0.08); color: var(--accent); }
.b-building { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-error { background: rgba(255,90,90,0.1); color: var(--danger); }
.b-draft { background: rgba(107,107,128,0.12); color: var(--text-muted); }

@media (max-width: 1080px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
  .projetos-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 680px) {
  .projetos-grid { grid-template-columns: 1fr; }
}
</style>
