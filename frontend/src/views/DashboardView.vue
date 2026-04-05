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

async function carregarDados() {
  carregando.value = true
  try {
    const [projRes, simRes] = await Promise.allSettled([
      service.get('/api/graph/project/list'),
      service.get('/api/simulation/history', { params: { limit: 5 } })
    ])
    if (projRes.status === 'fulfilled') {
      const raw = projRes.value?.data || projRes.value
      projetos.value = Array.isArray(raw) ? raw : (raw?.data || raw?.projects || raw?.items || [])
    }
    if (simRes.status === 'fulfilled') {
      const raw = simRes.value?.data || simRes.value
      simulacoes.value = Array.isArray(raw) ? raw : (raw?.data || raw?.history || raw?.simulations || [])
    }
  } catch (e) {
    console.error('Erro ao carregar dashboard:', e)
  } finally {
    carregando.value = false
  }
}

const metrics = computed(() => ({
  projetos: projetos.value.length,
  simulacoes: simulacoes.value.length,
  agentes: simulacoes.value.reduce((acc, s) => acc + (s.entities_count || s.agent_count || 0), 0),
  relatorios: simulacoes.value.filter(s => s.report_id).length
}))

const recentes = computed(() =>
  projetos.value.slice().sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).slice(0, 5)
)

function badgeProjeto(p) {
  const map = {
    graph_completed: { label: 'Pronto', cls: 'b-done' },
    graph_building: { label: 'Construindo', cls: 'b-ready' },
    ontology_generated: { label: 'Processando', cls: 'b-ready' },
    failed: { label: 'Erro', cls: 'b-error' },
  }
  return map[p.status] || { label: 'Criado', cls: 'b-draft' }
}

function formatarData(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(carregarDados)
</script>

<template>
  <AppShell title="Dashboard">
    <template #actions>
      <button class="btn-nova" @click="router.push('/novo')">+ Nova Simulação</button>
    </template>

    <section class="metrics">
      <MetricCard title="Projetos" :value="metrics.projetos" sub="No workspace" trend="up" />
      <MetricCard title="Simulações" :value="metrics.simulacoes" sub="Total executadas" trend="up" />
      <MetricCard title="Agentes" :value="metrics.agentes" sub="Criados no total" trend="up" />
      <MetricCard title="Relatórios" :value="metrics.relatorios" sub="Concluídos" />
    </section>

    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando...</span>
    </div>

    <div v-else-if="projetos.length === 0" class="empty">
      <div class="empty-icon">🔭</div>
      <div class="empty-title">Bem-vindo ao AUGUR</div>
      <div class="empty-sub">Crie sua primeira simulação para prever como o mercado vai reagir antes de lançar seu produto, marca ou serviço.</div>
      <button class="btn-nova-lg" @click="router.push('/novo')">✦ Criar primeira simulação</button>
    </div>

    <div v-else>
      <div class="secao-header">
        <h3 class="secao-titulo">Projetos recentes</h3>
        <span class="secao-sub">Clique em um projeto para ver suas simulações</span>
      </div>
      <div class="projetos-lista">
        <div
          v-for="p in recentes"
          :key="p.project_id || p.id"
          class="projeto-card"
          @click="router.push(`/projeto/${p.project_id || p.id}`)"
        >
          <div class="projeto-left">
            <div class="projeto-nome">{{ p.name || 'Projeto sem nome' }}</div>
            <div class="projeto-meta">
              {{ formatarData(p.created_at) }}
              <span class="sep">·</span>
              {{ (p.files || []).length }} arquivo{{ (p.files || []).length !== 1 ? 's' : '' }}
            </div>
          </div>
          <div class="projeto-right">
            <span :class="['badge', badgeProjeto(p).cls]">{{ badgeProjeto(p).label }}</span>
            <span class="arrow">›</span>
          </div>
        </div>
      </div>
      <div v-if="projetos.length > 5" class="ver-todos">Veja todos os projetos no menu lateral</div>
    </div>
  </AppShell>
</template>

<style scoped>
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 28px; }
.btn-nova { background: var(--accent); color: #000; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-nova:hover { opacity: 0.85; }
.loading { display: flex; align-items: center; gap: 12px; padding: 40px; color: var(--text-muted); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 20px; }
.empty-icon { font-size: 52px; margin-bottom: 16px; }
.empty-title { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
.empty-sub { font-size: 14px; color: var(--text-secondary); max-width: 460px; margin: 0 auto 24px; line-height: 1.7; }
.btn-nova-lg { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 13px 28px; font-size: 15px; font-weight: 700; cursor: pointer; }
.btn-nova-lg:hover { opacity: 0.85; }
.secao-header { margin-bottom: 14px; }
.secao-titulo { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.secao-sub { font-size: 12px; color: var(--text-muted); }
.projetos-lista { display: flex; flex-direction: column; gap: 10px; }
.projeto-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: all 0.15s; }
.projeto-card:hover { border-color: var(--border-md); background: var(--bg-raised); }
.projeto-nome { font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
.projeto-meta { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.sep { opacity: 0.4; }
.projeto-right { display: flex; align-items: center; gap: 12px; }
.arrow { font-size: 20px; color: var(--text-muted); }
.ver-todos { font-size: 12px; color: var(--text-muted); text-align: center; margin-top: 16px; }
.badge { padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 500; }
.b-done { background: rgba(0,229,195,0.1); color: var(--accent); }
.b-ready { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-error { background: rgba(255,90,90,0.1); color: var(--danger); }
.b-draft { background: rgba(107,107,128,0.15); color: var(--text-muted); }
@media (max-width: 1080px) { .metrics { grid-template-columns: repeat(2, 1fr); } }
</style>
