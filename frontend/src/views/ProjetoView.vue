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
const confirmandoDelete = ref(false)

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
      simulacoes.value = lista.sort((a, b) =>
        new Date(b.created_at || 0) - new Date(a.created_at || 0)
      )
    }
  } catch (e) {
    console.error('Erro ao carregar projeto:', e)
  } finally {
    carregando.value = false
  }
}

async function excluirProjeto() {
  try {
    await service.delete(`/api/graph/project/${projectId.value}`)
    router.push('/')
  } catch (e) {
    console.error('Erro ao excluir:', e)
  }
}

function acaoPrincipal(sim) {
  const status = sim.runner_status || sim.status
  if (status === 'running') {
    router.push(`/simulacao/${sim.simulation_id}/executar`)
    return
  }
  if (sim.report_id) {
    router.push(`/relatorio/${sim.report_id}`)
    return
  }
  if (status === 'completed' || status === 'stopped' || status === 'paused') {
    router.push(`/simulacao/${sim.simulation_id}/executar`)
    return
  }
  router.push(`/simulacao/${projectId.value}`)
}

function labelAcao(sim) {
  const status = sim.runner_status || sim.status
  if (status === 'running') return 'Acompanhar ao vivo →'
  if (sim.report_id) return 'Ver Relatório →'
  if (status === 'completed') return 'Ver Resultados →'
  if (status === 'stopped' || status === 'paused') return 'Retomar →'
  if (status === 'ready' || status === 'preparing') return 'Ver Pipeline →'
  return 'Abrir →'
}

function badgeSim(sim) {
  const status = sim.runner_status || sim.status
  const map = {
    running: { label: 'Em execução', cls: 'b-running' },
    completed: { label: 'Concluído', cls: 'b-done' },
    stopped: { label: 'Parado', cls: 'b-paused' },
    paused: { label: 'Pausado', cls: 'b-paused' },
    failed: { label: 'Erro', cls: 'b-error' },
    ready: { label: 'Pronto', cls: 'b-ready' },
    preparing: { label: 'Preparando', cls: 'b-ready' },
    created: { label: 'Criado', cls: 'b-draft' },
  }
  return map[status] || { label: status || 'Rascunho', cls: 'b-draft' }
}

function badgeProjeto(p) {
  if (!p) return { label: '', cls: '' }
  const map = {
    graph_completed: { label: 'Pronto para simular', cls: 'b-done' },
    graph_building: { label: 'Construindo grafo', cls: 'b-ready' },
    ontology_generated: { label: 'Ontologia gerada', cls: 'b-ready' },
    created: { label: 'Criado', cls: 'b-draft' },
    failed: { label: 'Erro', cls: 'b-error' },
  }
  return map[p.status] || { label: p.status || '', cls: 'b-draft' }
}

function formatarData(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function progresso(sim) {
  if (!sim.total_rounds || !sim.current_round) return 0
  return Math.round((sim.current_round / sim.total_rounds) * 100)
}

onMounted(carregar)
</script>

<template>
  <AppShell :title="projeto?.name || 'Projeto'">

    <!-- Carregando -->
    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando projeto...</span>
    </div>

    <div v-else-if="!projeto" class="empty-state">
      <div>Projeto não encontrado.</div>
      <button class="btn-back" @click="router.push('/')">← Voltar ao início</button>
    </div>

    <div v-else class="projeto-page">

      <!-- Header do projeto -->
      <div class="projeto-header">
        <div class="projeto-header-left">
          <div class="projeto-titulo">{{ projeto.name }}</div>
          <div class="projeto-meta">
            <span>Criado em {{ formatarData(projeto.created_at) }}</span>
            <span class="sep">·</span>
            <span>{{ (projeto.files || []).length }} arquivo{{ (projeto.files || []).length !== 1 ? 's' : '' }}</span>
            <span class="sep">·</span>
            <span>{{ simulacoes.length }} simulação{{ simulacoes.length !== 1 ? 'ões' : '' }}</span>
          </div>
          <div v-if="projeto.simulation_requirement" class="projeto-hipotese">
            {{ projeto.simulation_requirement }}
          </div>
        </div>
        <div class="projeto-header-right">
          <span :class="['badge', badgeProjeto(projeto).cls]">{{ badgeProjeto(projeto).label }}</span>
          <button class="btn-nova-sim" @click="router.push('/novo')">+ Nova Simulação</button>
          <button class="btn-delete" @click="confirmandoDelete = true" title="Excluir projeto">🗑</button>
        </div>
      </div>

      <!-- Confirmação de delete -->
      <div v-if="confirmandoDelete" class="confirm-delete">
        <span>Tem certeza? Esta ação não pode ser desfeita.</span>
        <button class="btn-confirmar-delete" @click="excluirProjeto">Sim, excluir</button>
        <button class="btn-cancelar" @click="confirmandoDelete = false">Cancelar</button>
      </div>

      <!-- Seção de simulações -->
      <div class="secao-titulo">
        <span>Simulações</span>
        <button class="btn-nova-sim-sm" @click="router.push('/novo')">+ Nova</button>
      </div>

      <!-- Estado vazio -->
      <div v-if="simulacoes.length === 0" class="sim-vazia">
        <div class="sim-vazia-icon">🚀</div>
        <div class="sim-vazia-titulo">Nenhuma simulação ainda</div>
        <div class="sim-vazia-sub">O grafo está pronto. Crie uma simulação para começar a prever reações do mercado.</div>
        <button class="btn-nova-sim" @click="router.push('/novo')" style="margin-top:16px;">
          + Criar primeira simulação
        </button>
      </div>

      <!-- Lista de simulações -->
      <div v-else class="sims-lista">
        <div
          v-for="sim in simulacoes"
          :key="sim.simulation_id"
          class="sim-card"
          :class="{ 'sim-running': (sim.runner_status || sim.status) === 'running' }"
        >
          <div class="sim-card-header">
            <div class="sim-card-left">
              <span :class="['badge', badgeSim(sim).cls]">{{ badgeSim(sim).label }}</span>
              <span class="sim-data">{{ formatarData(sim.created_at) }}</span>
            </div>
            <button class="sim-acao" @click="acaoPrincipal(sim)">
              {{ labelAcao(sim) }}
            </button>
          </div>

          <div v-if="sim.simulation_requirement" class="sim-hipotese">
            {{ sim.simulation_requirement.length > 120
              ? sim.simulation_requirement.slice(0, 120) + '...'
              : sim.simulation_requirement }}
          </div>

          <div class="sim-stats">
            <div class="sim-stat">
              <span class="stat-label">Agentes</span>
              <span class="stat-val">{{ sim.entities_count || sim.profiles_count || '—' }}</span>
            </div>
            <div class="sim-stat" v-if="sim.total_rounds">
              <span class="stat-label">Rodadas</span>
              <span class="stat-val">{{ sim.current_round || 0 }} / {{ sim.total_rounds }}</span>
            </div>
            <div class="sim-stat" v-if="sim.report_id">
              <span class="stat-label">Relatório</span>
              <span class="stat-val stat-link" @click.stop="router.push(`/relatorio/${sim.report_id}`)">Disponível →</span>
            </div>
          </div>

          <!-- Barra de progresso se em execução ou parado no meio -->
          <div v-if="sim.total_rounds && sim.current_round" class="sim-prog">
            <div class="sim-prog-fill" :style="{ width: progresso(sim) + '%' }"></div>
            <span class="sim-prog-label">{{ progresso(sim) }}%</span>
          </div>
        </div>
      </div>
    </div>

  </AppShell>
</template>

<style scoped>
.loading { display: flex; align-items: center; gap: 12px; padding: 40px; color: var(--text-muted); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { padding: 40px; text-align: center; color: var(--text-secondary); }
.btn-back { margin-top: 16px; background: none; border: 1px solid var(--border); color: var(--text-secondary); padding: 8px 16px; border-radius: 8px; cursor: pointer; }

.projeto-page { display: flex; flex-direction: column; gap: 20px; }

.projeto-header {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.projeto-header-left { flex: 1; }
.projeto-titulo { font-size: 20px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.projeto-meta { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.sep { opacity: 0.4; }
.projeto-hipotese { font-size: 13px; color: var(--text-secondary); line-height: 1.6; background: var(--bg-raised); border-radius: 8px; padding: 10px 14px; border-left: 3px solid var(--accent2); }

.projeto-header-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.btn-nova-sim {
  background: var(--accent); color: #000; border: none; border-radius: 8px;
  padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-nova-sim:hover { opacity: 0.85; }

.btn-delete {
  background: none; border: 1px solid var(--border); color: var(--text-muted);
  border-radius: 8px; padding: 7px 10px; cursor: pointer; font-size: 14px; transition: all 0.15s;
}
.btn-delete:hover { border-color: var(--danger); color: var(--danger); }

.confirm-delete {
  background: rgba(255,90,90,0.08); border: 1px solid rgba(255,90,90,0.25);
  border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; gap: 14px;
  font-size: 13px; color: var(--danger);
}
.btn-confirmar-delete {
  background: var(--danger); color: #fff; border: none; border-radius: 6px;
  padding: 6px 14px; font-size: 12px; cursor: pointer;
}
.btn-cancelar {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer;
}

.secao-titulo {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 14px; font-weight: 600; color: var(--text-primary);
}
.btn-nova-sim-sm {
  background: var(--accent2-dim); color: var(--accent2);
  border: 1px solid rgba(124,111,247,0.3); border-radius: 6px;
  padding: 5px 12px; font-size: 12px; cursor: pointer; transition: all 0.15s;
}
.btn-nova-sim-sm:hover { background: var(--accent2); color: #fff; }

.sim-vazia { text-align: center; padding: 48px 20px; background: var(--bg-surface); border: 1px dashed var(--border-md); border-radius: 12px; }
.sim-vazia-icon { font-size: 40px; margin-bottom: 12px; }
.sim-vazia-titulo { font-size: 16px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; }
.sim-vazia-sub { font-size: 13px; color: var(--text-secondary); max-width: 400px; margin: 0 auto; line-height: 1.6; }

.sims-lista { display: flex; flex-direction: column; gap: 12px; }

.sim-card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 20px; transition: border-color 0.2s;
}
.sim-card:hover { border-color: var(--border-md); }
.sim-card.sim-running { border-color: rgba(245,166,35,0.3); }

.sim-card-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}
.sim-card-left { display: flex; align-items: center; gap: 10px; }
.sim-data { font-size: 11px; color: var(--text-muted); }

.sim-acao {
  background: none; border: 1px solid var(--border-md); color: var(--accent2);
  border-radius: 6px; padding: 5px 12px; font-size: 12px; cursor: pointer; transition: all 0.15s;
}
.sim-acao:hover { background: var(--accent2-dim); border-color: var(--accent2); }

.sim-hipotese {
  font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px;
}

.sim-stats { display: flex; gap: 20px; }
.sim-stat { display: flex; flex-direction: column; gap: 2px; }
.stat-label { font-size: 11px; color: var(--text-muted); }
.stat-val { font-size: 14px; font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); }
.stat-link { color: var(--accent2); cursor: pointer; font-family: inherit; font-weight: 500; }
.stat-link:hover { text-decoration: underline; }

.sim-prog {
  display: flex; align-items: center; gap: 10px; margin-top: 12px;
}
.sim-prog { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; flex: 1; position: relative; }
.sim-prog-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.4s; }
.sim-prog-label { font-size: 11px; color: var(--text-muted); white-space: nowrap; position: absolute; right: 0; top: -16px; }

/* Badges */
.badge { padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 500; }
.b-done { background: rgba(0,229,195,0.1); color: var(--accent); }
.b-running { background: rgba(245,166,35,0.1); color: #f5a623; }
.b-paused { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-error { background: rgba(255,90,90,0.1); color: var(--danger); }
.b-ready { background: rgba(124,111,247,0.1); color: var(--accent2); }
.b-draft { background: rgba(107,107,128,0.15); color: var(--text-muted); }
</style>
