<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()
const projeto = ref(null)
const simulacoes = ref([])
const carregando = ref(true)
const confirmDelete = ref(false)
const deletando = ref(false)

const projectId = computed(() => route.params.projectId)

async function carregar() {
  carregando.value = true
  try {
    const [projRes, simRes] = await Promise.allSettled([
      service.get(`/api/graph/project/${projectId.value}`),
      service.get('/api/simulation/list', { params: { project_id: projectId.value } })
    ])
    if (projRes.status === 'fulfilled') {
      const raw = projRes.value?.data || projRes.value
      projeto.value = raw?.data || raw
    }
    if (simRes.status === 'fulfilled') {
      const raw = simRes.value?.data || simRes.value
      const lista = Array.isArray(raw) ? raw : (raw?.data || raw?.simulations || [])
      simulacoes.value = lista.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    }
  } catch (e) {
    console.error(e)
  } finally {
    carregando.value = false
  }
}

async function excluir() {
  deletando.value = true
  try {
    await service.delete(`/api/graph/project/${projectId.value}`)
    router.push('/')
  } catch (e) {
    console.error(e)
    deletando.value = false
  }
}

function badgeProjeto(p) {
  const map = {
    graph_completed: { label: 'Pronto para simular', cls: 'b-done' },
    graph_building: { label: 'Construindo grafo', cls: 'b-building' },
    ontology_generated: { label: 'Processando', cls: 'b-building' },
    failed: { label: 'Erro', cls: 'b-error' },
  }
  return map[p?.status] || { label: 'Criado', cls: 'b-draft' }
}

function badgeSim(sim) {
  const s = sim.runner_status || sim.status
  const map = {
    running: { label: 'Em execução', cls: 'b-running' },
    completed: { label: 'Concluída', cls: 'b-done' },
    stopped: { label: 'Parada', cls: 'b-paused' },
    paused: { label: 'Pausada', cls: 'b-paused' },
    failed: { label: 'Erro', cls: 'b-error' },
    ready: { label: 'Pronta', cls: 'b-building' },
    preparing: { label: 'Preparando', cls: 'b-building' },
    created: { label: 'Criada', cls: 'b-draft' },
  }
  return map[s] || { label: s || 'Rascunho', cls: 'b-draft' }
}

function acaoSim(sim) {
  const s = sim.runner_status || sim.status
  if (s === 'running') return { label: 'Acompanhar ao vivo →', action: () => router.push(`/simulacao/${sim.simulation_id}/executar`) }
  if (sim.report_id) return { label: 'Ver Relatório →', action: () => router.push(`/relatorio/${sim.report_id}`) }
  if (s === 'completed') return { label: 'Ver Resultados →', action: () => router.push(`/simulacao/${sim.simulation_id}/executar`) }
  if (s === 'stopped' || s === 'paused') return { label: '▶ Retomar →', action: () => router.push(`/simulacao/${sim.simulation_id}/executar`) }
  if (s === 'preparing' || s === 'ready') return { label: 'Ver Pipeline →', action: () => router.push(`/simulacao/${projectId.value}`) }
  return { label: 'Abrir →', action: () => router.push(`/simulacao/${projectId.value}`) }
}

function acaoSecundaria(sim) {
  if (sim.report_id) return { label: 'Entrevistar Agentes', action: () => router.push(`/agentes/${sim.report_id}`) }
  return null
}

function progresso(sim) {
  if (!sim.total_rounds || !sim.current_round) return 0
  return Math.round((sim.current_round / sim.total_rounds) * 100)
}

function formatarData(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function novaSimulacao() {
  router.push(`/novo?project_id=${projectId.value}`)
}

onMounted(carregar)
</script>

<template>
  <AppShell :title="projeto?.name || 'Projeto'">
    <template #actions>
      <button v-if="projeto" class="btn-nova-sim" @click="novaSimulacao">+ Nova Simulação</button>
    </template>

    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando projeto...</span>
    </div>

    <div v-else-if="!projeto" class="empty-state">
      <div>Projeto não encontrado.</div>
      <button class="btn-back" @click="router.push('/')">← Voltar</button>
    </div>

    <div v-else class="page">

      <!-- Header do projeto -->
      <div class="proj-header">
        <div class="proj-header-body">
          <div class="proj-nome">{{ projeto.name }}</div>
          <div class="proj-meta">
            <span>Criado {{ formatarData(projeto.created_at) }}</span>
            <span class="sep">·</span>
            <span>{{ (projeto.files || []).length }} material{{ (projeto.files || []).length !== 1 ? 'is' : '' }}</span>
            <span class="sep">·</span>
            <span>{{ simulacoes.length }} simulação{{ simulacoes.length !== 1 ? 'ões' : '' }}</span>
          </div>
          <div v-if="projeto.simulation_requirement" class="proj-briefing">
            <span class="briefing-label">Hipótese:</span>
            {{ projeto.simulation_requirement }}
          </div>
        </div>
        <div class="proj-header-actions">
          <span :class="['badge', badgeProjeto(projeto).cls]">{{ badgeProjeto(projeto).label }}</span>
          <button class="btn-delete" @click="confirmDelete = true" title="Excluir projeto">🗑</button>
        </div>
      </div>

      <!-- Confirmação de exclusão -->
      <div v-if="confirmDelete" class="confirm-box">
        <span>⚠️ Excluir projeto e todas as simulações? Esta ação não pode ser desfeita.</span>
        <div class="confirm-actions">
          <button class="btn-cancelar" @click="confirmDelete = false">Cancelar</button>
          <button class="btn-delete-confirm" :disabled="deletando" @click="excluir">
            {{ deletando ? 'Excluindo...' : 'Sim, excluir' }}
          </button>
        </div>
      </div>

      <!-- Seção simulações -->
      <div class="section-header">
        <div class="section-title">Simulações</div>
        <button class="btn-nova-sim-sm" @click="novaSimulacao">+ Nova Simulação</button>
      </div>

      <!-- Vazio -->
      <div v-if="simulacoes.length === 0" class="sims-vazio">
        <div class="vazio-icon">🚀</div>
        <div class="vazio-titulo">Nenhuma simulação ainda</div>
        <div class="vazio-sub">
          {{ badgeProjeto(projeto).cls === 'b-done'
            ? 'O grafo está pronto! Crie sua primeira simulação para prever como o mercado vai reagir.'
            : 'O grafo ainda está sendo construído. Aguarde e depois crie uma simulação.' }}
        </div>
        <button
          v-if="badgeProjeto(projeto).cls === 'b-done'"
          class="btn-nova-sim"
          @click="novaSimulacao"
          style="margin-top:16px"
        >
          + Criar primeira simulação
        </button>
      </div>

      <!-- Lista simulações -->
      <div v-else class="sims-lista">
        <div
          v-for="(sim, idx) in simulacoes"
          :key="sim.simulation_id"
          class="sim-card"
          :class="{ 'sim-running': (sim.runner_status || sim.status) === 'running' }"
        >
          <!-- Topo da simulação -->
          <div class="sim-top">
            <div class="sim-top-left">
              <span class="sim-num">#{{ simulacoes.length - idx }}</span>
              <span :class="['badge', badgeSim(sim).cls]">{{ badgeSim(sim).label }}</span>
              <span class="sim-data">{{ formatarData(sim.created_at) }}</span>
            </div>
            <div class="sim-top-right">
              <button
                v-if="acaoSecundaria(sim)"
                class="btn-sec"
                @click="acaoSecundaria(sim).action()"
              >
                {{ acaoSecundaria(sim).label }}
              </button>
              <button class="btn-acao" @click="acaoSim(sim).action()">
                {{ acaoSim(sim).label }}
              </button>
            </div>
          </div>

          <!-- Hipótese se diferente do projeto -->
          <div v-if="sim.simulation_requirement && sim.simulation_requirement !== projeto.simulation_requirement" class="sim-hipotese">
            {{ sim.simulation_requirement.length > 140 ? sim.simulation_requirement.slice(0, 140) + '...' : sim.simulation_requirement }}
          </div>

          <!-- Stats -->
          <div class="sim-stats">
            <div class="stat">
              <div class="stat-label">Agentes</div>
              <div class="stat-val">{{ sim.entities_count || sim.profiles_count || sim.agent_count || '—' }}</div>
            </div>
            <div class="stat" v-if="sim.total_rounds">
              <div class="stat-label">Rodadas</div>
              <div class="stat-val">{{ sim.current_round || 0 }} / {{ sim.total_rounds }}</div>
            </div>
            <div class="stat" v-if="sim.posts_created">
              <div class="stat-label">Posts</div>
              <div class="stat-val">{{ sim.posts_created }}</div>
            </div>
            <div class="stat" v-if="sim.report_id">
              <div class="stat-label">Relatório</div>
              <div class="stat-val stat-link" @click="router.push(`/relatorio/${sim.report_id}`)">Disponível →</div>
            </div>
          </div>

          <!-- Barra de progresso -->
          <div v-if="sim.total_rounds" class="sim-prog-wrap">
            <div class="sim-prog-bar">
              <div
                class="sim-prog-fill"
                :class="{ 'prog-running': (sim.runner_status || sim.status) === 'running' }"
                :style="{ width: progresso(sim) + '%' }"
              ></div>
            </div>
            <span class="sim-prog-pct">{{ progresso(sim) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.loading { display: flex; align-items: center; gap: 12px; padding: 48px; color: var(--text-muted); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.btn-back { margin-top: 12px; background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 7px 14px; border-radius: 8px; cursor: pointer; }

.page { display: flex; flex-direction: column; gap: 20px; }

/* Header projeto */
.proj-header { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.proj-nome { font-size: 20px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; letter-spacing: -0.3px; }
.proj-meta { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-bottom: 12px; }
.sep { opacity: 0.4; }
.proj-briefing { font-size: 13px; color: var(--text-secondary); line-height: 1.6; background: var(--bg-raised); border-left: 3px solid var(--accent2); border-radius: 0 8px 8px 0; padding: 10px 14px; }
.briefing-label { font-weight: 600; color: var(--accent2); margin-right: 6px; }
.proj-header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.btn-nova-sim { background: var(--accent); color: #000; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s; }
.btn-nova-sim:hover { opacity: 0.85; }
.btn-delete { background: none; border: 1px solid var(--border); color: var(--text-muted); border-radius: 8px; padding: 7px 10px; cursor: pointer; font-size: 14px; transition: all 0.15s; }
.btn-delete:hover { border-color: var(--danger); color: var(--danger); }

/* Confirm delete */
.confirm-box { background: rgba(255,90,90,0.07); border: 1px solid rgba(255,90,90,0.25); border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 13px; color: var(--danger); }
.confirm-actions { display: flex; gap: 10px; flex-shrink: 0; }
.btn-cancelar { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-delete-confirm { background: var(--danger); color: #fff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-delete-confirm:disabled { opacity: 0.5; }

/* Section header */
.section-header { display: flex; align-items: center; justify-content: space-between; }
.section-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.btn-nova-sim-sm { background: var(--accent2-dim); color: var(--accent2); border: 1px solid rgba(124,111,247,0.3); border-radius: 6px; padding: 5px 12px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
.btn-nova-sim-sm:hover { background: var(--accent2); color: #fff; }

/* Vazio */
.sims-vazio { text-align: center; padding: 52px 20px; background: var(--bg-surface); border: 1px dashed var(--border-md); border-radius: 12px; }
.vazio-icon { font-size: 42px; margin-bottom: 12px; }
.vazio-titulo { font-size: 16px; font-weight: 500; color: var(--text-primary); margin-bottom: 8px; }
.vazio-sub { font-size: 13px; color: var(--text-secondary); max-width: 420px; margin: 0 auto; line-height: 1.7; }

/* Simulações */
.sims-lista { display: flex; flex-direction: column; gap: 12px; }
.sim-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; transition: border-color 0.2s; }
.sim-card:hover { border-color: var(--border-md); }
.sim-card.sim-running { border-color: rgba(245,166,35,0.35); }

.sim-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 12px; }
.sim-top-left { display: flex; align-items: center; gap: 8px; }
.sim-top-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.sim-num { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
.sim-data { font-size: 11px; color: var(--text-muted); }

.btn-acao { background: none; border: 1px solid var(--border-md); color: var(--accent2); border-radius: 6px; padding: 5px 12px; font-size: 12px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.btn-acao:hover { background: var(--accent2-dim); border-color: var(--accent2); }
.btn-sec { background: none; border: 1px solid var(--border); color: var(--text-muted); border-radius: 6px; padding: 5px 10px; font-size: 11px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.btn-sec:hover { color: var(--text-primary); border-color: var(--border-md); }

.sim-hipotese { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px; font-style: italic; }

.sim-stats { display: flex; gap: 24px; margin-bottom: 4px; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.stat-val { font-size: 15px; font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); }
.stat-link { color: var(--accent2); cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 500; }
.stat-link:hover { text-decoration: underline; }

.sim-prog-wrap { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.sim-prog-bar { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.sim-prog-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.4s; }
.sim-prog-fill.prog-running { background: #f5a623; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.sim-prog-pct { font-size: 11px; color: var(--text-muted); min-width: 32px; text-align: right; font-family: var(--font-mono); }

/* Badges */
.badge { padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 500; }
.b-done { background: rgba(0,229,195,0.1); color: var(--accent); }
.b-running { background: rgba(245,166,35,0.1); color: #f5a623; }
.b-paused { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-building { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-error { background: rgba(255,90,90,0.1); color: var(--danger); }
.b-draft { background: rgba(107,107,128,0.15); color: var(--text-muted); }
</style>
