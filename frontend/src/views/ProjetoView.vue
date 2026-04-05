<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'
import { useToast } from '../composables/useToast'

const route  = useRoute()
const router = useRouter()
const toast  = useToast()

const projeto      = ref(null)
const simulacoes   = ref([])
const carregando   = ref(true)
const confirmDelete = ref(false)
const deletando    = ref(false)

// ─── Modal nova simulação ─────────────────────────────────────
const modalAberto      = ref(false)
const modalAgentes     = ref(50)
const modalRodadas     = ref(20)
const modalCriando     = ref(false)
const modalHipotese    = ref('')

const projectId = computed(() => route.params.projectId)

// ─── Carregar dados ───────────────────────────────────────────
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
      // Pré-preencher hipótese com a do projeto
      if (projeto.value?.simulation_requirement) {
        modalHipotese.value = projeto.value.simulation_requirement
      }
    }
    if (simRes.status === 'fulfilled') {
      const raw = simRes.value?.data || simRes.value
      const lista = Array.isArray(raw) ? raw : (raw?.data || raw?.simulations || [])
      simulacoes.value = lista.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    }
  } catch (e) {
    toast.error('Não foi possível carregar o projeto.')
  } finally {
    carregando.value = false
  }
}

// ─── Excluir projeto ─────────────────────────────────────────
async function excluir() {
  deletando.value = true
  try {
    await service.delete(`/api/graph/project/${projectId.value}`)
    toast.success('Projeto excluído com sucesso.')
    router.push('/')
  } catch (e) {
    toast.error('Não foi possível excluir o projeto.')
    deletando.value = false
  }
}

// ─── Abrir modal nova simulação ───────────────────────────────
function abrirModal() {
  if (badgeProjeto(projeto.value).cls !== 'b-done') {
    toast.warn('O grafo ainda está sendo construído. Aguarde para criar uma simulação.')
    return
  }
  modalAberto.value = true
}

// ─── Criar nova simulação no projeto existente ────────────────
async function criarNovaSimulacao() {
  if (!projeto.value?.graph_id) {
    toast.error('Grafo não encontrado. O projeto pode estar incompleto.')
    return
  }
  modalCriando.value = true
  try {
    // Criar simulação diretamente usando o grafo existente
    const res = await service.post('/api/simulation/create', {
      project_id: projectId.value,
      graph_id: projeto.value.graph_id
    })
    const data = res.data?.data || res.data || res
    const simId = data.simulation_id

    if (!simId) throw new Error('simulation_id não retornado')

    modalAberto.value = false
    toast.success('Simulação criada! Preparando agentes...')

    // Navegar para o pipeline com os parâmetros escolhidos
    router.push(`/simulacao/${projectId.value}?agentes=${modalAgentes.value}&rodadas=${modalRodadas.value}&sim_id=${simId}`)
  } catch (e) {
    toast.error(e?.response?.data?.error || 'Erro ao criar simulação. Tente novamente.')
  } finally {
    modalCriando.value = false
  }
}

// ─── Helpers visuais ─────────────────────────────────────────
function badgeProjeto(p) {
  if (!p) return { label: '', cls: 'b-draft' }
  const map = {
    graph_completed:   { label: 'Pronto para simular', cls: 'b-done' },
    graph_building:    { label: 'Construindo grafo',   cls: 'b-building' },
    ontology_generated:{ label: 'Processando',        cls: 'b-building' },
    failed:            { label: 'Erro',                cls: 'b-error' },
  }
  return map[p.status] || { label: 'Criado', cls: 'b-draft' }
}

function badgeSim(sim) {
  const s = sim.runner_status || sim.status
  const map = {
    running:   { label: 'Em execução', cls: 'b-running' },
    completed: { label: 'Concluída',   cls: 'b-done'    },
    stopped:   { label: 'Parada',      cls: 'b-paused'  },
    paused:    { label: 'Pausada',     cls: 'b-paused'  },
    failed:    { label: 'Erro',        cls: 'b-error'   },
    ready:     { label: 'Pronta',      cls: 'b-building'},
    preparing: { label: 'Preparando',  cls: 'b-building'},
    created:   { label: 'Criada',      cls: 'b-draft'   },
  }
  return map[s] || { label: s || 'Rascunho', cls: 'b-draft' }
}

function acaoPrincipal(sim) {
  const s = sim.runner_status || sim.status
  if (s === 'running') return {
    label: '▶ Acompanhar ao vivo',
    cls: 'btn-acao-running',
    action: () => router.push(`/simulacao/${sim.simulation_id}/executar`)
  }
  if (sim.report_id) return {
    label: '📊 Ver Relatório',
    cls: 'btn-acao-report',
    action: () => router.push(`/relatorio/${sim.report_id}`)
  }
  if (s === 'completed') return {
    label: '📊 Ver Resultados',
    cls: 'btn-acao-report',
    action: () => router.push(`/simulacao/${sim.simulation_id}/executar`)
  }
  if (s === 'stopped' || s === 'paused') return {
    label: '▶ Retomar',
    cls: 'btn-acao',
    action: () => router.push(`/simulacao/${sim.simulation_id}/executar`)
  }
  if (s === 'preparing' || s === 'ready') return {
    label: '⚙️ Ver Pipeline',
    cls: 'btn-acao',
    action: () => router.push(`/simulacao/${projectId.value}`)
  }
  return {
    label: 'Abrir',
    cls: 'btn-acao',
    action: () => router.push(`/simulacao/${projectId.value}`)
  }
}

function acaoSecundaria(sim) {
  if (sim.report_id) return {
    label: '💬 Entrevistar',
    action: () => router.push(`/agentes/${sim.report_id}`)
  }
  return null
}

function progresso(sim) {
  const pct = sim.progress_percent || sim.progress
  if (pct > 0) return Math.round(pct)
  if (!sim.total_rounds || !sim.current_round) return 0
  return Math.round((sim.current_round / sim.total_rounds) * 100)
}

function formatarData(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('pt-BR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

const estimativaMinutos = computed(() =>
  Math.round(Math.max(2, modalAgentes.value * modalRodadas.value * 0.04))
)
const estimativaCusto = computed(() =>
  (modalAgentes.value * modalRodadas.value * 0.0008).toFixed(2)
)

onMounted(carregar)
</script>

<template>
  <AppShell :title="projeto?.name || 'Projeto'">
    <template #actions>
      <button v-if="projeto" class="btn-nova-sim" @click="abrirModal">+ Nova Simulação</button>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="loading">
      <div class="spinner"></div>
      <span>Carregando projeto...</span>
    </div>

    <!-- Não encontrado -->
    <div v-else-if="!projeto" class="not-found">
      <div class="nf-icon">🔍</div>
      <div class="nf-titulo">Projeto não encontrado</div>
      <div class="nf-sub">Este projeto pode ter sido excluído ou o ID é inválido.</div>
      <button class="btn-ghost" @click="router.push('/')">← Voltar ao início</button>
    </div>

    <div v-else class="page">

      <!-- ─── HEADER DO PROJETO ─── -->
      <div class="proj-header">
        <div class="proj-header-body">
          <div class="proj-nome">{{ projeto.name }}</div>
          <div class="proj-meta">
            <span>📅 {{ formatarData(projeto.created_at) }}</span>
            <span class="sep">·</span>
            <span>📁 {{ (projeto.files || []).length }} material{{ (projeto.files || []).length !== 1 ? 'is' : '' }}</span>
            <span class="sep">·</span>
            <span>🔬 {{ simulacoes.length }} simulação{{ simulacoes.length !== 1 ? 'ões' : '' }}</span>
          </div>
          <div v-if="projeto.simulation_requirement" class="proj-briefing">
            <span class="briefing-label">Hipótese central:</span>
            {{ projeto.simulation_requirement }}
          </div>
        </div>
        <div class="proj-header-actions">
          <span :class="['badge', badgeProjeto(projeto).cls]">{{ badgeProjeto(projeto).label }}</span>
          <button class="btn-delete" @click="confirmDelete = true" title="Excluir projeto">🗑</button>
        </div>
      </div>

      <!-- ─── CONFIRMAÇÃO EXCLUSÃO ─── -->
      <Transition name="slide">
        <div v-if="confirmDelete" class="confirm-box">
          <span>⚠️ Excluir <strong>{{ projeto.name }}</strong> e todas as suas simulações? Esta ação é irreversível.</span>
          <div class="confirm-actions">
            <button class="btn-ghost" @click="confirmDelete = false">Cancelar</button>
            <button class="btn-delete-confirm" :disabled="deletando" @click="excluir">
              {{ deletando ? 'Excluindo...' : 'Sim, excluir tudo' }}
            </button>
          </div>
        </div>
      </Transition>

      <!-- ─── SEÇÃO SIMULAÇÕES ─── -->
      <div class="section-header">
        <div class="section-title">Simulações</div>
        <button
          class="btn-nova-sim-sm"
          :disabled="badgeProjeto(projeto).cls !== 'b-done'"
          @click="abrirModal"
          :title="badgeProjeto(projeto).cls !== 'b-done' ? 'Aguarde o grafo ser construído' : ''"
        >
          + Nova Simulação
        </button>
      </div>

      <!-- ─── ESTADO VAZIO ─── -->
      <div v-if="simulacoes.length === 0" class="sims-vazio">
        <div class="vazio-icon">🚀</div>
        <div class="vazio-titulo">Nenhuma simulação ainda</div>
        <div class="vazio-sub" v-if="badgeProjeto(projeto).cls === 'b-done'">
          O grafo de conhecimento está pronto. Crie sua primeira simulação para prever como o mercado vai reagir.
        </div>
        <div class="vazio-sub" v-else-if="badgeProjeto(projeto).cls === 'b-building'">
          <div class="building-info">
            <div class="mini-spinner"></div>
            O grafo de conhecimento ainda está sendo construído. Aguarde — isso pode levar alguns minutos.
          </div>
        </div>
        <div class="vazio-sub" v-else>
          O projeto está sendo processado. Aguarde a conclusão para criar simulações.
        </div>
        <button
          v-if="badgeProjeto(projeto).cls === 'b-done'"
          class="btn-nova-sim"
          @click="abrirModal"
          style="margin-top:20px"
        >
          ✦ Criar primeira simulação
        </button>
      </div>

      <!-- ─── LISTA DE SIMULAÇÕES ─── -->
      <div v-else class="sims-lista">
        <div
          v-for="(sim, idx) in simulacoes"
          :key="sim.simulation_id"
          class="sim-card"
          :class="{
            'sim-running': (sim.runner_status || sim.status) === 'running',
            'sim-done': (sim.runner_status || sim.status) === 'completed'
          }"
        >
          <!-- Topo -->
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
              <button
                :class="['btn-acao', acaoPrincipal(sim).cls]"
                @click="acaoPrincipal(sim).action()"
              >
                {{ acaoPrincipal(sim).label }}
              </button>
            </div>
          </div>

          <!-- Hipótese (se diferente do projeto) -->
          <div
            v-if="sim.simulation_requirement && sim.simulation_requirement !== projeto.simulation_requirement"
            class="sim-hipotese"
          >
            {{ sim.simulation_requirement.length > 140
              ? sim.simulation_requirement.slice(0,140) + '...'
              : sim.simulation_requirement }}
          </div>

          <!-- Stats -->
          <div class="sim-stats">
            <div class="stat">
              <div class="stat-label">Agentes</div>
              <div class="stat-val">{{ sim.entities_count || sim.profiles_count || sim.agent_count || '—' }}</div>
            </div>
            <div class="stat" v-if="sim.total_rounds">
              <div class="stat-label">Rodadas</div>
              <div class="stat-val">{{ sim.current_round || 0 }}<span class="stat-total">/ {{ sim.total_rounds }}</span></div>
            </div>
            <div class="stat" v-if="sim.posts_created || sim.twitter_actions_count">
              <div class="stat-label">Posts</div>
              <div class="stat-val">{{ sim.posts_created || (sim.twitter_actions_count + (sim.reddit_actions_count || 0)) }}</div>
            </div>
            <div class="stat" v-if="sim.report_id">
              <div class="stat-label">Relatório</div>
              <div class="stat-val stat-link" @click="router.push(`/relatorio/${sim.report_id}`)">
                Disponível →
              </div>
            </div>
          </div>

          <!-- Barra de progresso -->
          <div v-if="sim.total_rounds" class="sim-prog-wrap">
            <div class="sim-prog-bar">
              <div
                class="sim-prog-fill"
                :class="{
                  'prog-running': (sim.runner_status || sim.status) === 'running',
                  'prog-done': (sim.runner_status || sim.status) === 'completed'
                }"
                :style="{ width: progresso(sim) + '%' }"
              ></div>
            </div>
            <span class="sim-prog-pct">{{ progresso(sim) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── MODAL NOVA SIMULAÇÃO ─── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="modalAberto" class="modal-overlay" @click.self="modalAberto = false">
          <div class="modal">
            <div class="modal-header">
              <div class="modal-titulo">Nova Simulação</div>
              <div class="modal-sub">Configure os parâmetros para este projeto</div>
              <button class="modal-close" @click="modalAberto = false">×</button>
            </div>

            <div class="modal-body">
              <!-- Projeto info -->
              <div class="modal-projeto">
                <span class="modal-projeto-label">Projeto:</span>
                <span class="modal-projeto-nome">{{ projeto?.name }}</span>
              </div>

              <!-- Hipótese -->
              <div class="modal-field">
                <label class="modal-label">Hipótese</label>
                <textarea
                  v-model="modalHipotese"
                  class="modal-textarea"
                  rows="3"
                  placeholder="Deixe em branco para usar a hipótese original do projeto"
                />
                <div class="modal-hint">Opcional. Permite testar variações da hipótese original.</div>
              </div>

              <!-- Agentes -->
              <div class="modal-field">
                <div class="modal-slider-header">
                  <label class="modal-label">Número de Agentes</label>
                  <span class="modal-val">{{ modalAgentes }}</span>
                </div>
                <input type="range" min="5" max="500" step="5" v-model.number="modalAgentes" class="slider"/>
                <div class="modal-bounds">
                  <span>5 (rápido)</span>
                  <span>500 (máxima riqueza)</span>
                </div>
              </div>

              <!-- Rodadas -->
              <div class="modal-field">
                <div class="modal-slider-header">
                  <label class="modal-label">Número de Rodadas</label>
                  <span class="modal-val">{{ modalRodadas }}</span>
                </div>
                <input type="range" min="1" max="100" step="1" v-model.number="modalRodadas" class="slider"/>
                <div class="modal-bounds">
                  <span>1 (instantâneo)</span>
                  <span>100 (evolução completa)</span>
                </div>
              </div>

              <!-- Estimativas -->
              <div class="modal-estimativas">
                <div class="est-item">
                  <span class="est-label">⏱ Tempo estimado</span>
                  <span class="est-val">~{{ estimativaMinutos }} min</span>
                </div>
                <div class="est-sep"></div>
                <div class="est-item">
                  <span class="est-label">💳 Custo estimado</span>
                  <span class="est-val">~${{ estimativaCusto }}</span>
                </div>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn-ghost" @click="modalAberto = false">Cancelar</button>
              <button class="btn-criar-sim" :disabled="modalCriando" @click="criarNovaSimulacao">
                <span v-if="modalCriando" class="spinner-sm"></span>
                <span v-else>✦</span>
                {{ modalCriando ? 'Criando...' : 'Iniciar Simulação' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </AppShell>
</template>

<style scoped>
.loading { display: flex; align-items: center; gap: 12px; padding: 48px; color: var(--text-muted); }
.spinner { width: 20px; height: 20px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.not-found { text-align: center; padding: 64px 20px; }
.nf-icon  { font-size: 48px; margin-bottom: 16px; }
.nf-titulo{ font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.nf-sub   { font-size: 13px; color: var(--text-secondary); margin-bottom: 20px; }

.page { display: flex; flex-direction: column; gap: 20px; }

/* Header */
.proj-header { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.proj-nome { font-size: 22px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; letter-spacing: -0.4px; }
.proj-meta { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.sep { opacity: 0.3; }
.proj-briefing { font-size: 13px; color: var(--text-secondary); line-height: 1.7; background: var(--bg-raised); border-left: 3px solid var(--accent2); border-radius: 0 8px 8px 0; padding: 10px 14px; }
.briefing-label { font-weight: 600; color: var(--accent2); margin-right: 6px; }
.proj-header-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.btn-nova-sim { background: var(--accent); color: #000; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer; transition: opacity 0.15s; }
.btn-nova-sim:hover:not(:disabled) { opacity: 0.85; }
.btn-delete { background: none; border: 1px solid var(--border); color: var(--text-muted); border-radius: 8px; padding: 7px 10px; cursor: pointer; font-size: 14px; transition: all 0.15s; }
.btn-delete:hover { border-color: var(--danger); color: var(--danger); }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; transition: all 0.15s; }
.btn-ghost:hover { color: var(--text-primary); border-color: var(--border-md); }

/* Confirm */
.confirm-box { background: rgba(255,90,90,0.07); border: 1px solid rgba(255,90,90,0.25); border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 13px; color: var(--text-secondary); }
.confirm-actions { display: flex; gap: 10px; flex-shrink: 0; }
.btn-delete-confirm { background: var(--danger); color: #fff; border: none; border-radius: 6px; padding: 7px 16px; font-size: 12px; cursor: pointer; font-weight: 600; }
.btn-delete-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

/* Section */
.section-header { display: flex; align-items: center; justify-content: space-between; }
.section-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.btn-nova-sim-sm { background: var(--accent2-dim); color: var(--accent2); border: 1px solid rgba(124,111,247,0.3); border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-nova-sim-sm:hover:not(:disabled) { background: var(--accent2); color: #fff; }
.btn-nova-sim-sm:disabled { opacity: 0.4; cursor: not-allowed; }

/* Vazio */
.sims-vazio { text-align: center; padding: 56px 20px; background: var(--bg-surface); border: 1px dashed var(--border-md); border-radius: 12px; }
.vazio-icon { font-size: 44px; margin-bottom: 14px; }
.vazio-titulo { font-size: 17px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.vazio-sub { font-size: 13px; color: var(--text-secondary); max-width: 440px; margin: 0 auto; line-height: 1.7; }
.building-info { display: flex; align-items: center; gap: 10px; justify-content: center; }
.mini-spinner { width: 14px; height: 14px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }

/* Simulações */
.sims-lista { display: flex; flex-direction: column; gap: 12px; }
.sim-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; transition: border-color 0.2s; }
.sim-card:hover { border-color: var(--border-md); }
.sim-card.sim-running { border-color: rgba(245,166,35,0.4); box-shadow: 0 0 0 1px rgba(245,166,35,0.1); }
.sim-card.sim-done    { border-color: rgba(0,229,195,0.2); }

.sim-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 12px; }
.sim-top-left  { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sim-top-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.sim-num  { font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); }
.sim-data { font-size: 11px; color: var(--text-muted); }

.btn-acao { background: none; border: 1px solid var(--border-md); color: var(--accent2); border-radius: 6px; padding: 5px 12px; font-size: 12px; cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.btn-acao:hover { background: var(--accent2-dim); border-color: var(--accent2); }
.btn-acao-running { background: rgba(245,166,35,0.1); border-color: rgba(245,166,35,0.4); color: #f5a623; }
.btn-acao-running:hover { background: rgba(245,166,35,0.2); }
.btn-acao-report { background: rgba(0,229,195,0.1); border-color: rgba(0,229,195,0.3); color: var(--accent); }
.btn-acao-report:hover { background: rgba(0,229,195,0.2); }
.btn-sec { background: none; border: 1px solid var(--border); color: var(--text-muted); border-radius: 6px; padding: 5px 10px; font-size: 11px; cursor: pointer; transition: all 0.15s; }
.btn-sec:hover { color: var(--text-primary); border-color: var(--border-md); }

.sim-hipotese { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 12px; font-style: italic; border-left: 2px solid var(--border-md); padding-left: 10px; }

.sim-stats { display: flex; gap: 28px; margin-bottom: 6px; flex-wrap: wrap; }
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px; }
.stat-val { font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.stat-total { font-size: 12px; font-weight: 400; color: var(--text-muted); }
.stat-link { color: var(--accent2); cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 600; }
.stat-link:hover { text-decoration: underline; }

.sim-prog-wrap { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.sim-prog-bar { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.sim-prog-fill { height: 100%; border-radius: 2px; transition: width 0.4s; background: var(--accent2); }
.sim-prog-fill.prog-running { background: #f5a623; animation: shimmer 1.5s infinite; }
.sim-prog-fill.prog-done    { background: var(--accent); }
@keyframes shimmer { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
.sim-prog-pct { font-size: 11px; color: var(--text-muted); min-width: 34px; text-align: right; font-family: var(--font-mono); }

/* Badges */
.badge { padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.b-done     { background: rgba(0,229,195,0.1);    color: var(--accent); }
.b-running  { background: rgba(245,166,35,0.1);   color: #f5a623; }
.b-paused   { background: rgba(124,111,247,0.1);  color: var(--accent2); }
.b-building { background: rgba(124,111,247,0.1);  color: var(--accent2); }
.b-error    { background: rgba(255,90,90,0.1);    color: var(--danger); }
.b-draft    { background: rgba(107,107,128,0.15); color: var(--text-muted); }

/* ─── MODAL ─── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 20px; backdrop-filter: blur(4px);
}
.modal {
  background: var(--bg-surface); border: 1px solid var(--border-md);
  border-radius: 16px; width: 100%; max-width: 520px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.5);
  display: flex; flex-direction: column;
  max-height: 90vh; overflow: hidden;
}
.modal-header { padding: 20px 24px 0; position: relative; }
.modal-titulo { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.modal-sub    { font-size: 13px; color: var(--text-muted); margin-bottom: 0; }
.modal-close  { position: absolute; top: 16px; right: 20px; background: none; border: none; color: var(--text-muted); font-size: 22px; cursor: pointer; line-height: 1; }
.modal-close:hover { color: var(--text-primary); }

.modal-body { padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; overflow-y: auto; }

.modal-projeto { background: var(--bg-raised); border-radius: 8px; padding: 10px 14px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
.modal-projeto-label { color: var(--text-muted); }
.modal-projeto-nome  { color: var(--text-primary); font-weight: 500; }

.modal-field { display: flex; flex-direction: column; gap: 8px; }
.modal-label { font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.modal-textarea { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 13px; padding: 10px 12px; outline: none; resize: vertical; font-family: inherit; line-height: 1.6; transition: border-color 0.15s; }
.modal-textarea:focus { border-color: var(--accent2); }
.modal-hint { font-size: 11px; color: var(--text-muted); }
.modal-slider-header { display: flex; justify-content: space-between; align-items: center; }
.modal-val { font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--accent2); }
.modal-bounds { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.slider { width: 100%; accent-color: var(--accent2); cursor: pointer; }

.modal-estimativas { background: var(--bg-raised); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; display: flex; }
.est-item { flex: 1; padding: 12px 16px; }
.est-label { font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px; }
.est-val { font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.est-sep { width: 1px; background: var(--border); margin: 8px 0; }

.modal-footer { padding: 16px 24px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.btn-criar-sim { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 11px 24px; font-size: 14px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
.btn-criar-sim:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-criar-sim:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
.spinner-sm { width: 13px; height: 13px; border: 2px solid rgba(0,0,0,0.2); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }

/* Transitions */
.slide-enter-active, .slide-leave-active { transition: all 0.25s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); }
.modal-enter-active { transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1); }
.modal-leave-active { transition: all 0.2s ease; }
.modal-enter-from   { opacity: 0; transform: scale(0.92); }
.modal-leave-to     { opacity: 0; transform: scale(0.95); }
</style>
