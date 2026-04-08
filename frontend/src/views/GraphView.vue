<script setup>
import { onMounted, onUnmounted, ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as d3 from 'd3'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route  = useRoute()
const router = useRouter()

// ─── Estado ───────────────────────────────────────────────────
const carregando  = ref(true)
const erro        = ref('')
const projeto     = ref(null)
const graphId     = ref(null)
const nodes       = ref([])
const edges       = ref([])
const filtroAtivo = ref('Todos')
const modoVista   = ref('visualizacao') // 'visualizacao' | 'lista'
const nodeSelected = ref(null)
const svgEl       = ref(null)

// D3 internals
let simulation = null
let svgSelection = null
let zoom = null

// ─── Tipos e cores ────────────────────────────────────────────
const TIPOS = {
  Conceito:     { color: '#1da1f2', bg: 'rgba(29,161,242,0.15)'  },
  Pessoa:       { color: '#f5a623', bg: 'rgba(245,166,35,0.15)'  },
  Organização:  { color: '#00e5c3', bg: 'rgba(0,229,195,0.15)'   },
  Evento:       { color: '#ff5a5a', bg: 'rgba(255,90,90,0.15)'   },
  default:      { color: '#7c6ff7', bg: 'rgba(124,111,247,0.15)' },
}

function getTipo(labels) {
  if (!labels?.length) return 'Conceito'
  for (const t of Object.keys(TIPOS)) {
    if (labels.some(l => l === t || l.toLowerCase().includes(t.toLowerCase()))) return t
  }
  return labels[0] || 'Conceito'
}

function getCor(labels) { return (TIPOS[getTipo(labels)] || TIPOS.default).color }
function getBg(labels)  { return (TIPOS[getTipo(labels)] || TIPOS.default).bg }

// ─── Computed ─────────────────────────────────────────────────
const todosOsTipos = computed(() => {
  const counts = {}
  nodes.value.forEach(n => {
    const t = getTipo(n.labels)
    counts[t] = (counts[t] || 0) + 1
  })
  return counts
})

const filtros = computed(() => [
  { label: 'Todos', count: nodes.value.length },
  ...Object.entries(todosOsTipos.value).map(([t, c]) => ({ label: t, count: c }))
])

const nodesFiltrados = computed(() => {
  if (filtroAtivo.value === 'Todos') return nodes.value
  return nodes.value.filter(n => getTipo(n.labels) === filtroAtivo.value)
})

const edgesFiltrados = computed(() => {
  const uuids = new Set(nodesFiltrados.value.map(n => n.uuid))
  return edges.value.filter(e => uuids.has(e.source_node_uuid) && uuids.has(e.target_node_uuid))
})

const nodeRelacoes = computed(() => {
  if (!nodeSelected.value) return []
  return edges.value.filter(e =>
    e.source_node_uuid === nodeSelected.value.uuid ||
    e.target_node_uuid === nodeSelected.value.uuid
  )
})

// ─── Carregar dados ────────────────────────────────────────────
onMounted(async () => {
  carregando.value = true
  try {
    const pid = route.params.projectId
    const pr  = await service.get(`/api/graph/project/${pid}`)
    const pdata = pr?.data?.data || pr?.data || pr
    projeto.value = pdata
    graphId.value  = pdata?.graph_id

    if (!graphId.value) throw new Error('Projeto ainda não tem grafo construído.')

    const gr  = await service.get(`/api/graph/data/${graphId.value}`)
    const gdata = gr?.data?.data || gr?.data || gr
    nodes.value = gdata?.nodes || []
    edges.value = gdata?.edges || []

    await nextTick()
    initGraph()
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar grafo.'
  } finally {
    carregando.value = false
  }
})

onUnmounted(() => { if (simulation) simulation.stop() })

// ─── Reiniciar grafo quando filtro muda ───────────────────────
watch([filtroAtivo, modoVista], async () => {
  if (modoVista.value === 'visualizacao') {
    await nextTick()
    initGraph()
  }
})

// ─── D3 Force Graph ───────────────────────────────────────────
function initGraph() {
  if (!svgEl.value || modoVista.value !== 'visualizacao') return
  if (simulation) simulation.stop()

  const container = svgEl.value.parentElement
  const W = container.clientWidth  || 700
  const H = container.clientHeight || 500

  // Limpar SVG anterior
  d3.select(svgEl.value).selectAll('*').remove()

  svgSelection = d3.select(svgEl.value)
    .attr('width', W)
    .attr('height', H)

  const g = svgSelection.append('g').attr('class', 'graph-root')

  // Zoom
  zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', ev => g.attr('transform', ev.transform))
  svgSelection.call(zoom)

  // Dados
  const ns = nodesFiltrados.value.map(n => ({ ...n, _x: W/2 + (Math.random()-0.5)*200, _y: H/2 + (Math.random()-0.5)*200 }))
  const nsMap = new Map(ns.map(n => [n.uuid, n]))

  const es = edgesFiltrados.value
    .map(e => ({ ...e, source: e.source_node_uuid, target: e.target_node_uuid }))
    .filter(e => nsMap.has(e.source) && nsMap.has(e.target))

  // Defs: seta
  const defs = svgSelection.append('defs')
  defs.append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -4 8 8')
    .attr('refX', 18)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-4L8,0L0,4')
    .attr('fill', 'rgba(0,0,0,0.2)')

  // Arestas
  const linkG = g.append('g').attr('class', 'links')

  const linkEl = linkG.selectAll('line')
    .data(es).enter().append('line')
    .attr('stroke', 'rgba(0,0,0,0.1)')
    .attr('stroke-width', 1.2)
    .attr('marker-end', 'url(#arrow)')

  // Labels das arestas
  const linkLabelEl = linkG.selectAll('text.edge-label')
    .data(es.filter(e => e.name || e.fact_type)).enter().append('text')
    .attr('class', 'edge-label')
    .attr('text-anchor', 'middle')
    .attr('font-size', '9')
    .attr('fill', 'rgba(0,0,0,0.25)')
    .text(e => truncLabel(e.name || e.fact_type || '', 18))

  // Nós
  const nodeG = g.append('g').attr('class', 'nodes')

  const nodeEl = nodeG.selectAll('g.node')
    .data(ns).enter().append('g')
    .attr('class', 'node')
    .style('cursor', 'pointer')
    .on('click', (_, d) => { nodeSelected.value = d })
    .call(d3.drag()
      .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end',   (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
    )

  // Círculo de fundo (glow)
  nodeEl.append('circle')
    .attr('r', 20)
    .attr('fill', d => getBg(d.labels))
    .attr('stroke', 'none')

  // Círculo principal
  nodeEl.append('circle')
    .attr('r', d => 10 + Math.min(nodeRelacaoCount(d, es) * 1.5, 10))
    .attr('fill', d => getCor(d.labels))
    .attr('fill-opacity', 0.85)
    .attr('stroke', d => getCor(d.labels))
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.5)

  // Label do nó
  nodeEl.append('text')
    .attr('y', 22)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10')
    .attr('fill', 'rgba(0,0,0,0.7)')
    .attr('font-weight', '500')
    .text(d => truncLabel(d.name || '', 14))

  // Simulação
  simulation = d3.forceSimulation(ns)
    .force('link', d3.forceLink(es).id(d => d.uuid).distance(90).strength(0.4))
    .force('charge', d3.forceManyBody().strength(-220))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(32))
    .on('tick', () => {
      linkEl
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)

      linkLabelEl
        .attr('x', d => ((d.source.x || 0) + (d.target.x || 0)) / 2)
        .attr('y', d => ((d.source.y || 0) + (d.target.y || 0)) / 2 - 4)

      nodeEl.attr('transform', d => `translate(${d.x},${d.y})`)
    })
}

function nodeRelacaoCount(node, es) {
  return es.filter(e => e.source === node.uuid || e.target === node.uuid || e.source_node_uuid === node.uuid || e.target_node_uuid === node.uuid).length
}

function truncLabel(s, n) { return s?.length > n ? s.slice(0, n) + '…' : (s || '') }

// ─── Zoom controls ────────────────────────────────────────────
function zoomIn()    { if (svgSelection && zoom) svgSelection.transition().call(zoom.scaleBy, 1.3) }
function zoomOut()   { if (svgSelection && zoom) svgSelection.transition().call(zoom.scaleBy, 0.77) }
function zoomReset() { if (svgSelection && zoom) svgSelection.transition().call(zoom.transform, d3.zoomIdentity) }

// ─── Download PNG ─────────────────────────────────────────────
function downloadPNG() {
  if (!svgEl.value) return
  const serializer = new XMLSerializer()
  const svgStr = serializer.serializeToString(svgEl.value)
  const canvas  = document.createElement('canvas')
  canvas.width  = svgEl.value.width.baseVal.value || 800
  canvas.height = svgEl.value.height.baseVal.value || 600
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#09090f'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  const img = new Image()
  img.onload = () => { ctx.drawImage(img, 0, 0); const a = document.createElement('a'); a.download = 'augur-grafo.png'; a.href = canvas.toDataURL(); a.click() }
  img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)))
}

// ─── Navegação ────────────────────────────────────────────────
function voltar() { router.push(`/projeto/${route.params.projectId}`) }

function truncar(s, n=120) { return s?.length > n ? s.slice(0, n) + '...' : (s || '') }
</script>

<template>
  <AppShell :title="projeto?.name ? `${projeto.name} — Grafo` : 'Grafo de Conhecimento'">
    <template #actions>
      <AugurButton variant="ghost" @click="voltar">← Projeto</AugurButton>
      <AugurButton variant="ghost" @click="downloadPNG">⬇ PNG</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="loading">
      <div class="spin"></div>
      <div><div class="ld-t">Carregando grafo...</div><div class="ld-s">Buscando nós e relações de {{ projeto?.name || 'projeto' }}</div></div>
    </div>

    <!-- Erro -->
    <div v-else-if="erro" class="erro-st">
      <div style="font-size:48px">🕸️</div>
      <div style="color:var(--danger);font-size:14px;text-align:center;max-width:360px">{{ erro }}</div>
      <AugurButton variant="ghost" @click="voltar">← Voltar ao projeto</AugurButton>
    </div>

    <div v-else class="wrap">

      <!-- ── Header ── -->
      <div class="graph-header">
        <div class="gh-left">
          <div class="bc">
            <span class="bc-l" @click="voltar">← Projeto</span>
            <span class="bc-s">›</span>
            <span class="bc-c">Grafo de Conhecimento</span>
          </div>
          <div class="gh-stats">
            <span class="stat-chip">🔵 {{ nodes.length }} nós</span>
            <span class="stat-chip">⟶ {{ edges.length }} relações</span>
            <span class="stat-desc">Mapa estrutural do conhecimento que guia os agentes</span>
          </div>
        </div>
        <div class="gh-right">
          <div class="vista-toggle">
            <button :class="['vt-btn', {active: modoVista==='visualizacao'}]" @click="modoVista='visualizacao'">
              <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12">
                <circle cx="3" cy="7" r="2"/><circle cx="11" cy="3" r="2"/><circle cx="11" cy="11" r="2"/>
                <line x1="5" y1="6.3" x2="9" y2="3.7"/><line x1="5" y1="7.7" x2="9" y2="10.3"/>
              </svg>
              Visualização
            </button>
            <button :class="['vt-btn', {active: modoVista==='lista'}]" @click="modoVista='lista'">
              <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12">
                <line x1="1" y1="3" x2="13" y2="3"/><line x1="1" y1="7" x2="13" y2="7"/><line x1="1" y1="11" x2="13" y2="11"/>
              </svg>
              Lista
            </button>
          </div>
        </div>
      </div>

      <!-- ── Filtros ── -->
      <div class="filtros">
        <button
          v-for="f in filtros" :key="f.label"
          :class="['filtro-btn', {active: filtroAtivo===f.label}]"
          @click="filtroAtivo=f.label; nodeSelected=null"
        >
          <span class="filtro-dot" :style="{background: f.label==='Todos' ? 'var(--text-muted)' : (TIPOS[f.label]||TIPOS.default).color}"></span>
          {{ f.label }}
          <span class="filtro-count">{{ f.count }}</span>
        </button>
      </div>

      <!-- ═══════════════════════════════════════ -->
      <!-- VISUALIZAÇÃO                            -->
      <!-- ═══════════════════════════════════════ -->
      <div v-if="modoVista==='visualizacao'" class="vis-layout">

        <!-- Canvas do grafo -->
        <div class="canvas-wrap">
          <div class="canvas-hint">Arraste os nós · Scroll para zoom · Clique para detalhes</div>

          <!-- Zoom controls -->
          <div class="zoom-controls">
            <button class="zc-btn" @click="zoomIn"  title="Zoom in">+</button>
            <button class="zc-btn" @click="zoomOut" title="Zoom out">−</button>
            <button class="zc-btn" @click="zoomReset" title="Reset">⊡</button>
          </div>

          <svg ref="svgEl" class="graph-svg"></svg>
        </div>

        <!-- Painel lateral -->
        <div class="side-panel">

          <!-- Placeholder -->
          <div v-if="!nodeSelected" class="panel-empty">
            <div class="pe-icon">🔍</div>
            <div class="pe-t">Selecione um nó</div>
            <div class="pe-s">Clique em qualquer nó do grafo para ver seus detalhes e relações</div>

            <!-- Estatísticas dos tipos -->
            <div class="tipo-stats">
              <div class="ts-title">Estatísticas</div>
              <div v-for="(count, tipo) in todosOsTipos" :key="tipo" class="ts-row">
                <div class="ts-left">
                  <div class="ts-dot" :style="{background: (TIPOS[tipo]||TIPOS.default).color}"></div>
                  <span class="ts-nome">{{ tipo }}</span>
                </div>
                <div class="ts-bar-wrap">
                  <div class="ts-bar" :style="{width: (count/nodes.length*100)+'%', background: (TIPOS[tipo]||TIPOS.default).color}"></div>
                </div>
                <span class="ts-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <!-- Detalhe do nó selecionado -->
          <div v-else class="node-detail">
            <button class="nd-close" @click="nodeSelected=null">×</button>

            <div class="nd-tipo" :style="{background: getBg(nodeSelected.labels), color: getCor(nodeSelected.labels), borderColor: getCor(nodeSelected.labels)+'44'}">
              {{ getTipo(nodeSelected.labels) }}
            </div>

            <div class="nd-nome">{{ nodeSelected.name }}</div>

            <div v-if="nodeSelected.summary" class="nd-summary">{{ nodeSelected.summary }}</div>

            <div v-if="nodeSelected.attributes && Object.keys(nodeSelected.attributes).length" class="nd-attrs">
              <div class="nd-section-title">Atributos</div>
              <div v-for="(val, key) in nodeSelected.attributes" :key="key" class="nd-attr-row">
                <span class="nd-ak">{{ key }}</span>
                <span class="nd-av">{{ truncar(String(val), 50) }}</span>
              </div>
            </div>

            <div class="nd-section-title" style="margin-top:14px">Relações ({{ nodeRelacoes.length }})</div>
            <div class="nd-relacoes">
              <div v-for="r in nodeRelacoes" :key="r.uuid" class="nd-rel">
                <div class="nd-rel-dir">
                  <span v-if="r.source_node_uuid === nodeSelected.uuid" class="rel-out">→</span>
                  <span v-else class="rel-in">←</span>
                </div>
                <div class="nd-rel-body">
                  <div class="nd-rel-nome">{{ r.name || r.fact_type || '—' }}</div>
                  <div class="nd-rel-peer">
                    {{ r.source_node_uuid === nodeSelected.uuid ? r.target_node_name : r.source_node_name }}
                  </div>
                  <div v-if="r.fact" class="nd-rel-fact">{{ truncar(r.fact, 80) }}</div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- ═══════════════════════════════════════ -->
      <!-- LISTA                                   -->
      <!-- ═══════════════════════════════════════ -->
      <div v-else class="lista-wrap">
        <div class="lista-header">
          <span>Nó</span>
          <span>Tipo</span>
          <span>Relações</span>
          <span>Resumo</span>
        </div>
        <div
          v-for="n in nodesFiltrados" :key="n.uuid"
          class="lista-row"
          @click="nodeSelected=n; modoVista='visualizacao'"
        >
          <span class="lr-nome">
            <span class="lr-dot" :style="{background: getCor(n.labels)}"></span>
            {{ n.name }}
          </span>
          <span class="lr-tipo" :style="{color: getCor(n.labels), background: getBg(n.labels)}">
            {{ getTipo(n.labels) }}
          </span>
          <span class="lr-count">
            {{ edges.filter(e => e.source_node_uuid===n.uuid || e.target_node_uuid===n.uuid).length }}
          </span>
          <span class="lr-summary">{{ truncar(n.summary, 80) }}</span>
        </div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
/* ─── Base ──────────────────────────────────────────────────── */
.loading { display:flex;align-items:center;gap:16px;padding:60px; }
.spin { width:28px;height:28px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .8s linear infinite;flex-shrink:0; }
@keyframes sp { to{transform:rotate(360deg)} }
.ld-t { font-size:15px;font-weight:600;color:var(--text-primary); }
.ld-s { font-size:13px;color:var(--text-muted);margin-top:4px; }
.erro-st { text-align:center;padding:60px;display:flex;flex-direction:column;align-items:center;gap:16px; }
.wrap { display:flex;flex-direction:column;gap:14px; }

/* ─── Header ─────────────────────────────────────────────────── */
.graph-header { display:flex;align-items:flex-start;justify-content:space-between;gap:16px; }
.gh-left { display:flex;flex-direction:column;gap:8px; }
.bc { display:flex;align-items:center;gap:6px;font-size:13px; }
.bc-l { color:var(--accent2);cursor:pointer; }
.bc-l:hover { text-decoration:underline; }
.bc-s { color:var(--text-muted); }
.bc-c { color:var(--text-secondary); }
.gh-stats { display:flex;align-items:center;gap:10px;flex-wrap:wrap; }
.stat-chip { font-size:12px;font-weight:600;color:var(--text-secondary);background:var(--bg-raised);border:1px solid var(--border);border-radius:20px;padding:3px 10px; }
.stat-desc { font-size:12px;color:var(--text-muted); }

.gh-right { flex-shrink:0; }
.vista-toggle { display:flex;background:var(--bg-raised);border:1px solid var(--border);border-radius:8px;overflow:hidden; }
.vt-btn { display:flex;align-items:center;gap:6px;padding:7px 14px;background:none;border:none;font-size:12px;font-weight:500;color:var(--text-muted);cursor:pointer;transition:all .15s; }
.vt-btn.active { background:var(--bg-overlay);color:var(--accent2); }
.vt-btn:hover:not(.active) { color:var(--text-secondary); }

/* ─── Filtros ────────────────────────────────────────────────── */
.filtros { display:flex;gap:6px;flex-wrap:wrap; }
.filtro-btn { display:flex;align-items:center;gap:6px;padding:5px 12px;background:var(--bg-surface);border:1px solid var(--border);border-radius:20px;font-size:12px;color:var(--text-muted);cursor:pointer;transition:all .15s; }
.filtro-btn:hover { border-color:var(--border-md);color:var(--text-secondary); }
.filtro-btn.active { border-color:var(--accent2);background:var(--accent2-dim);color:var(--accent2); }
.filtro-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.filtro-count { font-size:10px;font-weight:700;background:var(--bg-overlay);border-radius:10px;padding:1px 6px; }

/* ─── Layout Vis ─────────────────────────────────────────────── */
.vis-layout { display:grid;grid-template-columns:1fr 260px;gap:12px;min-height:520px; }

/* Canvas */
.canvas-wrap { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;position:relative;overflow:hidden;min-height:520px; }
.canvas-hint { position:absolute;top:10px;left:50%;transform:translateX(-50%);font-size:11px;color:rgba(0,0,0,0.2);background:var(--bg-overlay);border-radius:20px;padding:4px 12px;pointer-events:none;z-index:2;white-space:nowrap; }
.graph-svg { width:100%;height:100%;display:block;min-height:520px; }

/* Zoom controls */
.zoom-controls { position:absolute;bottom:14px;right:14px;display:flex;flex-direction:column;gap:4px;z-index:5; }
.zc-btn { width:30px;height:30px;background:var(--bg-raised);border:1px solid var(--border);border-radius:7px;color:var(--text-secondary);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s; }
.zc-btn:hover { background:var(--bg-overlay);color:var(--text-primary); }

/* ─── Side Panel ─────────────────────────────────────────────── */
.side-panel { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;padding:16px;overflow-y:auto;max-height:520px; }

.panel-empty { display:flex;flex-direction:column;align-items:center;gap:10px;padding:20px 10px;text-align:center; }
.pe-icon { font-size:32px; }
.pe-t { font-size:14px;font-weight:600;color:var(--text-primary); }
.pe-s { font-size:12px;color:var(--text-muted);line-height:1.6; }

.tipo-stats { width:100%;margin-top:10px;border-top:1px solid var(--border);padding-top:14px;text-align:left; }
.ts-title { font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px; }
.ts-row { display:flex;align-items:center;gap:8px;margin-bottom:8px; }
.ts-left { display:flex;align-items:center;gap:6px;min-width:90px; }
.ts-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.ts-nome { font-size:12px;color:var(--text-secondary); }
.ts-bar-wrap { flex:1;height:5px;background:var(--bg-overlay);border-radius:3px;overflow:hidden; }
.ts-bar { height:100%;border-radius:3px;transition:width .4s; }
.ts-count { font-size:11px;color:var(--text-muted);min-width:18px;text-align:right;font-family:monospace; }

/* Node detail */
.node-detail { display:flex;flex-direction:column;gap:12px;position:relative; }
.nd-close { position:absolute;top:0;right:0;background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;line-height:1; }
.nd-close:hover { color:var(--text-primary); }
.nd-tipo { font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;border:1px solid;border-radius:20px;padding:3px 10px;align-self:flex-start; }
.nd-nome { font-size:17px;font-weight:700;color:var(--text-primary);line-height:1.3;padding-right:20px; }
.nd-summary { font-size:12px;color:var(--text-secondary);line-height:1.7;background:var(--bg-raised);border-radius:8px;padding:10px 12px; }
.nd-attrs { display:flex;flex-direction:column;gap:5px; }
.nd-section-title { font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px; }
.nd-attr-row { display:flex;gap:8px;font-size:11px; }
.nd-ak { color:var(--text-muted);min-width:70px;flex-shrink:0; }
.nd-av { color:var(--text-secondary); }
.nd-relacoes { display:flex;flex-direction:column;gap:7px; }
.nd-rel { display:flex;gap:8px;align-items:flex-start;background:var(--bg-raised);border-radius:8px;padding:8px 10px; }
.nd-rel-dir { flex-shrink:0;font-size:14px;font-weight:700; }
.rel-out { color:var(--accent); }
.rel-in  { color:var(--accent2); }
.nd-rel-body { display:flex;flex-direction:column;gap:2px; }
.nd-rel-nome { font-size:11px;font-weight:600;color:var(--text-primary); }
.nd-rel-peer { font-size:11px;color:var(--accent2); }
.nd-rel-fact { font-size:10px;color:var(--text-muted);line-height:1.5;font-style:italic;margin-top:2px; }

/* ─── Lista ──────────────────────────────────────────────────── */
.lista-wrap { background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;overflow:hidden; }
.lista-header { display:grid;grid-template-columns:200px 100px 70px 1fr;gap:12px;padding:10px 16px;border-bottom:1px solid var(--border);font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.8px; }
.lista-row { display:grid;grid-template-columns:200px 100px 70px 1fr;gap:12px;padding:11px 16px;border-bottom:1px solid var(--border);font-size:13px;cursor:pointer;transition:background .15s;align-items:center; }
.lista-row:last-child { border-bottom:none; }
.lista-row:hover { background:var(--bg-raised); }
.lr-nome { display:flex;align-items:center;gap:8px;font-weight:500;color:var(--text-primary); }
.lr-dot  { width:8px;height:8px;border-radius:50%;flex-shrink:0; }
.lr-tipo { font-size:11px;font-weight:600;border-radius:20px;padding:2px 8px;align-self:center;width:fit-content; }
.lr-count { font-size:12px;color:var(--text-muted);font-family:monospace; }
.lr-summary { font-size:12px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }

/* ─── Responsive ─────────────────────────────────────────────── */
@media (max-width:900px) {
  .vis-layout { grid-template-columns:1fr; }
  .side-panel { max-height:300px; }
  .lista-header,.lista-row { grid-template-columns:1fr 80px 50px; }
  .lista-header span:last-child,.lr-summary { display:none; }
}
</style>
