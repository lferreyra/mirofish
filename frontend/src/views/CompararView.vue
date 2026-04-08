<script setup>
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route  = useRoute()
const router = useRouter()

const carregando = ref(true)
const erro       = ref('')
const simulacoes = ref([])
const selA       = ref(null)
const selB       = ref(null)
const dataA      = ref(null)
const dataB      = ref(null)
const reportA    = ref(null)
const reportB    = ref(null)
const comparando = ref(false)

// Carregar lista de simulações
onMounted(async () => {
  carregando.value = true
  try {
    const res = await service.get('/api/simulation/history', { params: { limit: 50 } })
    const raw = res?.data?.data || res?.data || res
    simulacoes.value = (Array.isArray(raw) ? raw : (raw?.history || []))
      .filter(s => (s.runner_status || s.status) === 'completed')
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    
    // Pre-selecionar se tiver 2+
    if (simulacoes.value.length >= 2) {
      selA.value = simulacoes.value[0].simulation_id
      selB.value = simulacoes.value[1].simulation_id
    }
  } catch (e) {
    erro.value = e?.message || 'Erro ao carregar simulações.'
  } finally {
    carregando.value = false
  }
})

// Comparar
async function comparar() {
  if (!selA.value || !selB.value) return
  if (selA.value === selB.value) { erro.value = 'Selecione duas simulações diferentes.'; return }
  comparando.value = true
  erro.value = ''
  
  try {
    const [aRes, bRes] = await Promise.all([
      service.get(`/api/analytics/${selA.value}`),
      service.get(`/api/analytics/${selB.value}`)
    ])
    dataA.value = aRes?.data?.data || aRes?.data || null
    dataB.value = bRes?.data?.data || bRes?.data || null
    
    // Tentar carregar relatórios
    const simA = simulacoes.value.find(s => s.simulation_id === selA.value)
    const simB = simulacoes.value.find(s => s.simulation_id === selB.value)
    
    if (simA?.report_id) {
      try {
        const rA = await service.get(`/api/report/${simA.report_id}`)
        reportA.value = rA?.data?.data || rA?.data || null
      } catch {}
    }
    if (simB?.report_id) {
      try {
        const rB = await service.get(`/api/report/${simB.report_id}`)
        reportB.value = rB?.data?.data || rB?.data || null
      } catch {}
    }
  } catch (e) {
    erro.value = e?.message || 'Erro ao comparar.'
  } finally {
    comparando.value = false
  }
}

// Helpers
const simLabel = (id) => {
  const s = simulacoes.value.find(x => x.simulation_id === id)
  if (!s) return id
  const req = s.simulation_requirement || ''
  return req.length > 50 ? req.slice(0, 50) + '...' : (req || `Simulação ${id}`)
}

function metric(data, path) {
  if (!data) return '—'
  const parts = path.split('.')
  let val = data
  for (const p of parts) {
    val = val?.[p]
    if (val === undefined) return '—'
  }
  return typeof val === 'number' ? val.toLocaleString('pt-BR') : val
}

function topAgents(data, platform) {
  return data?.[platform]?.top_agents?.slice(0, 5) || []
}

function totalInteractions(data) {
  const tw = data?.twitter?.totals || {}
  const rd = data?.reddit?.totals || {}
  return (tw.total_posts || 0) + (tw.total_likes || 0) + (rd.total_posts || 0) + (rd.total_likes || 0)
}

function totalPosts(data) {
  return (data?.twitter?.totals?.total_posts || 0) + (data?.reddit?.totals?.total_posts || 0)
}

function totalLikes(data) {
  return (data?.twitter?.totals?.total_likes || 0) + (data?.reddit?.totals?.total_likes || 0)
}

// Extrair confiança do relatório
function confianca(report) {
  if (!report) return '—'
  const content = JSON.stringify(report?.outline || report?.sections || '')
  const m = content.match(/(\d{2,3})\s*%/)
  return m ? m[1] + '%' : '—'
}

// Vencedor em cada métrica
function winner(valA, valB) {
  const a = parseInt(valA) || 0, b = parseInt(valB) || 0
  if (a > b) return 'a'
  if (b > a) return 'b'
  return 'tie'
}
</script>

<template>
  <AppShell title="Comparar Simulações">
    <template #actions>
      <AugurButton variant="ghost" @click="router.push('/')">← Dashboard</AugurButton>
    </template>

    <div v-if="carregando" class="state-box">
      <div class="spin"></div>
      <div>Carregando simulações...</div>
    </div>

    <div v-else-if="simulacoes.length < 2" class="state-box">
      <div style="font-size:42px">📊</div>
      <div>Você precisa de pelo menos 2 simulações concluídas para comparar.</div>
      <AugurButton @click="router.push('/')">← Dashboard</AugurButton>
    </div>

    <div v-else>
      <!-- Seletor -->
      <div class="selector-bar">
        <div class="sel-col">
          <label class="sel-label">🅰 Simulação A</label>
          <select v-model="selA" class="sel-input">
            <option v-for="s in simulacoes" :key="s.simulation_id" :value="s.simulation_id">
              {{ (s.simulation_requirement || 'Simulação').slice(0, 60) }}
            </option>
          </select>
        </div>
        <div class="sel-vs">VS</div>
        <div class="sel-col">
          <label class="sel-label">🅱 Simulação B</label>
          <select v-model="selB" class="sel-input">
            <option v-for="s in simulacoes" :key="s.simulation_id" :value="s.simulation_id">
              {{ (s.simulation_requirement || 'Simulação').slice(0, 60) }}
            </option>
          </select>
        </div>
        <AugurButton @click="comparar" :disabled="comparando || !selA || !selB">
          {{ comparando ? '⏳ Comparando...' : '📊 Comparar' }}
        </AugurButton>
      </div>

      <div v-if="erro" class="err-msg">{{ erro }}</div>

      <!-- Resultados -->
      <div v-if="dataA && dataB" class="results">

        <!-- Métricas lado a lado -->
        <div class="comp-section">
          <div class="cs-title">📊 Métricas Gerais</div>
          <div class="comp-table">
            <div class="ct-header">
              <span class="ct-metric">Métrica</span>
              <span class="ct-a">🅰 {{ simLabel(selA).slice(0, 30) }}</span>
              <span class="ct-b">🅱 {{ simLabel(selB).slice(0, 30) }}</span>
            </div>
            <div v-for="m in [
              { label: 'Total de Posts', a: totalPosts(dataA), b: totalPosts(dataB) },
              { label: 'Total de Likes', a: totalLikes(dataA), b: totalLikes(dataB) },
              { label: 'Interações Totais', a: totalInteractions(dataA), b: totalInteractions(dataB) },
              { label: 'Posts Twitter', a: metric(dataA, 'twitter.totals.total_posts'), b: metric(dataB, 'twitter.totals.total_posts') },
              { label: 'Posts Reddit', a: metric(dataA, 'reddit.totals.total_posts'), b: metric(dataB, 'reddit.totals.total_posts') },
              { label: 'Confiança', a: confianca(reportA), b: confianca(reportB) },
            ]" :key="m.label" class="ct-row">
              <span class="ct-metric">{{ m.label }}</span>
              <span class="ct-val" :class="{'ct-winner': winner(m.a, m.b)==='a'}">{{ m.a }}</span>
              <span class="ct-val" :class="{'ct-winner': winner(m.a, m.b)==='b'}">{{ m.b }}</span>
            </div>
          </div>
        </div>

        <!-- Top Agentes lado a lado -->
        <div class="comp-section">
          <div class="cs-title">👑 Top Agentes por Influência</div>
          <div class="comp-cols">
            <div class="comp-col">
              <div class="col-label">🅰</div>
              <div v-for="(a, i) in topAgents(dataA, 'twitter')" :key="'a'+i" class="agent-row">
                <span class="ar-pos">{{ i+1 }}.</span>
                <span class="ar-name">{{ a.name }}</span>
                <span class="ar-score">{{ a.total_likes_received || 0 }} ❤️</span>
              </div>
              <div v-if="!topAgents(dataA, 'twitter').length" class="no-data">Sem dados</div>
            </div>
            <div class="comp-divider"></div>
            <div class="comp-col">
              <div class="col-label">🅱</div>
              <div v-for="(a, i) in topAgents(dataB, 'twitter')" :key="'b'+i" class="agent-row">
                <span class="ar-pos">{{ i+1 }}.</span>
                <span class="ar-name">{{ a.name }}</span>
                <span class="ar-score">{{ a.total_likes_received || 0 }} ❤️</span>
              </div>
              <div v-if="!topAgents(dataB, 'twitter').length" class="no-data">Sem dados</div>
            </div>
          </div>
        </div>

        <!-- Cenários (se houver relatórios) -->
        <div v-if="reportA || reportB" class="comp-section">
          <div class="cs-title">🔭 Cenários dos Relatórios</div>
          <div class="comp-cols">
            <div class="comp-col">
              <div class="col-label">🅰</div>
              <div class="scenario-text">
                {{ reportA?.outline?.summary || reportA?.summary || 'Relatório não disponível' }}
              </div>
            </div>
            <div class="comp-divider"></div>
            <div class="comp-col">
              <div class="col-label">🅱</div>
              <div class="scenario-text">
                {{ reportB?.outline?.summary || reportB?.summary || 'Relatório não disponível' }}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.state-box { display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;text-align:center;color:var(--text-muted); }
.spin { width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to { transform:rotate(360deg) } }

.selector-bar { display:flex;align-items:flex-end;gap:16px;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:20px 24px;margin-bottom:20px; }
.sel-col { flex:1;display:flex;flex-direction:column;gap:6px; }
.sel-label { font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px; }
.sel-input { background:var(--bg-overlay);border:1px solid var(--border-md);color:var(--text-primary);padding:10px 12px;border-radius:8px;font-size:13px;outline:none;width:100%; }
.sel-input:focus { border-color:var(--accent2); }
.sel-vs { font-size:18px;font-weight:800;color:var(--accent2);padding-bottom:10px; }
.err-msg { background:rgba(255,90,90,0.08);border:1px solid rgba(255,90,90,0.2);color:var(--danger);padding:10px 16px;border-radius:8px;font-size:13px;margin-bottom:16px; }

.results { display:flex;flex-direction:column;gap:16px; }

.comp-section { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:20px 24px; }
.cs-title { font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:16px; }

/* Tabela de comparação */
.comp-table { display:flex;flex-direction:column;gap:2px; }
.ct-header { display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;padding:8px 12px;font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px; }
.ct-row { display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;padding:10px 12px;border-radius:8px;transition:background .1s; }
.ct-row:hover { background:var(--bg-raised); }
.ct-metric { font-size:13px;color:var(--text-secondary); }
.ct-val { font-size:14px;font-weight:700;color:var(--text-primary);font-family:monospace;text-align:center; }
.ct-winner { color:var(--accent);position:relative; }
.ct-winner::after { content:'✓';font-size:10px;margin-left:4px;color:var(--accent); }

/* Colunas lado a lado */
.comp-cols { display:grid;grid-template-columns:1fr auto 1fr;gap:16px; }
.comp-col { display:flex;flex-direction:column;gap:6px; }
.comp-divider { width:1px;background:var(--border);margin:0 8px; }
.col-label { font-size:12px;font-weight:700;color:var(--accent2);margin-bottom:4px; }

.agent-row { display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px; }
.agent-row:hover { background:var(--bg-raised); }
.ar-pos { font-size:11px;color:var(--text-muted);font-weight:700;min-width:20px; }
.ar-name { font-size:13px;color:var(--text-primary);flex:1; }
.ar-score { font-size:11px;color:var(--text-muted);font-family:monospace; }

.scenario-text { font-size:13px;color:var(--text-secondary);line-height:1.7;padding:8px;background:var(--bg-raised);border-radius:8px; }
.no-data { font-size:12px;color:var(--text-muted);text-align:center;padding:16px; }

@media (max-width:768px) {
  .selector-bar { flex-direction:column;align-items:stretch; }
  .sel-vs { text-align:center; }
  .comp-cols { grid-template-columns:1fr; }
  .comp-divider { width:100%;height:1px;margin:8px 0; }
}
</style>
