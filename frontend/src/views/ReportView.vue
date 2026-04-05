<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import SentimentBar from '../components/ui/SentimentBar.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()

const report = ref(null)
const carregando = ref(true)
const erro = ref('')

onMounted(async () => {
  carregando.value = true
  erro.value = ''
  try {
    const res = await service.get(`/api/report/${route.params.reportId}`)
    const raw = res.data || res
    report.value = {
      summary: raw.summary || raw.executive_summary || '',
      insights: raw.insights || [],
      metrics: raw.metrics || {},
      keywords: raw.keywords || [],
      project_name: raw.project_name || raw.title || '',
      project_id: raw.project_id || '',
      simulation_id: raw.simulation_id || '',
      agents_count: raw.agents_count || raw.metrics?.agents_reached || 0,
      created_at: raw.created_at || raw.generated_at || '',
    }
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar relatório.'
  } finally {
    carregando.value = false
  }
})

const colorByTag = (tag) => ({
  'Oportunidade': '#00e5c3',
  'Risco': '#ff5a5a',
  'Observação': '#7c6ff7',
  'Tendência': '#f5a623',
}[tag] || '#9898b0')

const temInsights = computed(() => (report.value?.insights?.length || 0) > 0)
const sentimento = computed(() => ({
  positive: report.value?.metrics?.positive || report.value?.metrics?.sentiment_positive || 0,
  neutral: report.value?.metrics?.neutral || report.value?.metrics?.sentiment_neutral || 0,
  negative: report.value?.metrics?.negative || report.value?.metrics?.sentiment_negative || 0,
}))

function formatarData(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function voltar() {
  if (report.value?.project_id) {
    router.push(`/projeto/${report.value.project_id}`)
  } else {
    router.push('/')
  }
}
</script>

<template>
  <AppShell :title="report?.project_name || 'Relatório'">
    <template #actions>
      <AugurButton variant="ghost" @click="voltar">← Voltar ao projeto</AugurButton>
      <AugurButton variant="ghost" @click="router.push(`/agentes/${route.params.reportId}`)">
        💬 Entrevistar Agentes
      </AugurButton>
    </template>

    <!-- Loading skeleton -->
    <div v-if="carregando" class="loading-state">
      <div class="skeleton-header"></div>
      <div class="skeleton-body">
        <div class="skeleton-main">
          <div class="skeleton-block tall"></div>
          <div class="skeleton-block"></div>
          <div class="skeleton-block"></div>
        </div>
        <div class="skeleton-side">
          <div class="skeleton-block"></div>
          <div class="skeleton-block short"></div>
          <div class="skeleton-block short"></div>
        </div>
      </div>
      <div class="loading-msg">
        <div class="mini-spinner"></div>
        Carregando relatório...
      </div>
    </div>

    <!-- Erro -->
    <div v-else-if="erro" class="error-state">
      <div class="error-icon">⚠️</div>
      <div class="error-titulo">Não foi possível carregar o relatório</div>
      <div class="error-msg">{{ erro }}</div>
      <div class="error-actions">
        <button class="btn-ghost" @click="voltar">← Voltar</button>
        <button class="btn-retry" @click="$router.go(0)">↺ Tentar novamente</button>
      </div>
    </div>

    <!-- Relatório -->
    <div v-else-if="report" class="relatorio">

      <!-- Header do relatório -->
      <div class="rel-header">
        <div class="rel-header-left">
          <div class="rel-titulo">{{ report.project_name || 'Análise de Simulação' }}</div>
          <div class="rel-meta">
            <span v-if="report.created_at">📅 Gerado em {{ formatarData(report.created_at) }}</span>
            <span v-if="report.agents_count" class="sep">·</span>
            <span v-if="report.agents_count">🤖 {{ report.agents_count }} agentes</span>
          </div>
        </div>
        <div class="rel-badge-conclusao">✅ Análise Concluída</div>
      </div>

      <div class="layout">
        <!-- Coluna principal -->
        <div class="main">

          <!-- Sumário executivo -->
          <article class="summary">
            <div class="sec-titulo">
              <span class="sec-ico">📋</span>
              Sumário Executivo
            </div>
            <div class="summary-body">
              <p v-if="report.summary">{{ report.summary }}</p>
              <p v-else class="sem-dados">Sumário não disponível para esta simulação.</p>
            </div>
          </article>

          <!-- Insights -->
          <article class="card" v-if="temInsights">
            <div class="sec-titulo">
              <span class="sec-ico">💡</span>
              Insights Detalhados
              <span class="insight-count">{{ report.insights.length }} análises</span>
            </div>
            <div class="insights-lista">
              <div v-for="(insight, idx) in report.insights" :key="idx" class="insight">
                <div class="insight-header">
                  <span class="insight-tag" :style="{ color: colorByTag(insight.tag || 'Observação'), borderColor: colorByTag(insight.tag || 'Observação') }">
                    {{ insight.tag || 'Observação' }}
                  </span>
                  <span v-if="insight.confidence" class="insight-conf">
                    Confiança: {{ insight.confidence }}%
                  </span>
                </div>
                <p class="insight-text">{{ insight.text || insight.description }}</p>
              </div>
            </div>
          </article>

          <!-- Sem insights -->
          <div v-else class="card sem-insights">
            <div class="sem-ico">🔍</div>
            <div>Nenhum insight detalhado disponível para esta simulação.</div>
          </div>

        </div>

        <!-- Coluna lateral -->
        <aside class="side">

          <!-- Sentimento geral -->
          <div class="card">
            <div class="sec-titulo-sm">Sentimento Geral</div>
            <SentimentBar
              label=""
              :positive="sentimento.positive"
              :neutral="sentimento.neutral"
              :negative="sentimento.negative"
            />
          </div>

          <!-- Métricas principais -->
          <div class="card">
            <div class="sec-titulo-sm">Métricas da Simulação</div>
            <div class="metricas-lista">
              <div class="metrica-item" v-if="report.metrics.agents_reached">
                <span class="met-label">Agentes alcançados</span>
                <span class="met-val">{{ report.metrics.agents_reached }}</span>
              </div>
              <div class="metrica-item" v-if="report.metrics.posts_generated">
                <span class="met-label">Posts gerados</span>
                <span class="met-val">{{ report.metrics.posts_generated }}</span>
              </div>
              <div class="metrica-item" v-if="report.metrics.purchase_intent !== undefined">
                <span class="met-label">Intenção de compra</span>
                <span class="met-val accent">{{ report.metrics.purchase_intent }}%</span>
              </div>
              <div class="metrica-item" v-if="report.metrics.viral_probability !== undefined">
                <span class="met-label">Probabilidade viral</span>
                <span class="met-val accent2">{{ report.metrics.viral_probability }}%</span>
              </div>
              <div class="metrica-item" v-if="sentimento.positive">
                <span class="met-label">Tom positivo</span>
                <span class="met-val accent">{{ sentimento.positive }}%</span>
              </div>
              <div class="metrica-item" v-if="sentimento.negative">
                <span class="met-label">Tom negativo</span>
                <span class="met-val danger">{{ sentimento.negative }}%</span>
              </div>
              <div v-if="!Object.keys(report.metrics).length" class="sem-dados">
                Métricas não disponíveis.
              </div>
            </div>
          </div>

          <!-- Palavras-chave -->
          <div class="card" v-if="report.keywords?.length">
            <div class="sec-titulo-sm">Palavras-chave Identificadas</div>
            <div class="keywords">
              <span v-for="(kw, idx) in report.keywords" :key="idx">{{ kw }}</span>
            </div>
          </div>

          <!-- CTA entrevista -->
          <div class="card card-cta">
            <div class="cta-ico">💬</div>
            <div class="cta-body">
              <div class="cta-titulo">Quer saber mais?</div>
              <div class="cta-sub">Entreviste os agentes diretamente e aprofunde as análises.</div>
            </div>
            <button class="btn-entrevistar" @click="router.push(`/agentes/${route.params.reportId}`)">
              Entrevistar →
            </button>
          </div>

        </aside>
      </div>
    </div>

  </AppShell>
</template>

<style scoped>
/* Loading skeleton */
.loading-state { display: flex; flex-direction: column; gap: 16px; }
.skeleton-header { height: 80px; background: var(--bg-raised); border-radius: 12px; animation: shimmer 1.5s infinite; }
.skeleton-body { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; }
.skeleton-main, .skeleton-side { display: flex; flex-direction: column; gap: 10px; }
.skeleton-block { height: 120px; background: var(--bg-raised); border-radius: 10px; animation: shimmer 1.5s infinite; }
.skeleton-block.tall { height: 180px; }
.skeleton-block.short { height: 80px; }
@keyframes shimmer { 0%,100% { opacity:0.5; } 50% { opacity:1; } }
.loading-msg { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-muted); justify-content: center; padding: 12px; }
.mini-spinner { width: 16px; height: 16px; border: 2px solid var(--border-md); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Erro */
.error-state { text-align: center; padding: 60px 20px; }
.error-icon { font-size: 48px; margin-bottom: 16px; }
.error-titulo { font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.error-msg { font-size: 13px; color: var(--danger); margin-bottom: 20px; }
.error-actions { display: flex; gap: 12px; justify-content: center; }
.btn-ghost { background: none; border: 1px solid var(--border); color: var(--text-secondary); border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; }
.btn-retry { background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }

/* Relatório */
.relatorio { display: flex; flex-direction: column; gap: 16px; }

.rel-header { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.rel-titulo { font-size: 20px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; letter-spacing: -0.3px; }
.rel-meta { font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
.sep { opacity: 0.4; }
.rel-badge-conclusao { background: rgba(0,229,195,0.1); color: var(--accent); border: 1px solid rgba(0,229,195,0.2); border-radius: 20px; padding: 5px 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }

/* Layout */
.layout { display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }
.main, .side { display: flex; flex-direction: column; gap: 12px; }

/* Cards */
.card { background: var(--bg-raised); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }

.sec-titulo { font-size: 14px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.sec-ico { font-size: 16px; }
.insight-count { font-size: 11px; color: var(--text-muted); font-weight: 400; background: var(--bg-overlay); padding: 2px 8px; border-radius: 20px; margin-left: auto; }

.sec-titulo-sm { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }

/* Sumário */
.summary { border-left: 3px solid var(--accent); background: var(--bg-raised); border-radius: 0 12px 12px 0; border: 1px solid var(--border); border-left-color: var(--accent); border-left-width: 3px; padding: 18px 20px; }
.summary-body p { font-size: 14px; color: var(--text-secondary); line-height: 1.8; margin: 0; }

/* Insights */
.insights-lista { display: flex; flex-direction: column; gap: 0; }
.insight { padding: 14px 0; border-bottom: 1px solid var(--border); }
.insight:last-child { border-bottom: none; padding-bottom: 0; }
.insight:first-child { padding-top: 0; }
.insight-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.insight-tag { border: 1px solid; border-radius: 20px; padding: 2px 10px; font-size: 11px; font-weight: 600; }
.insight-conf { font-size: 11px; color: var(--text-muted); }
.insight-text { font-size: 13px; color: var(--text-secondary); line-height: 1.7; margin: 0; }

.sem-insights { text-align: center; padding: 32px; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; gap: 10px; }
.sem-ico { font-size: 32px; }
.sem-dados { font-size: 12px; color: var(--text-muted); font-style: italic; }

/* Métricas */
.metricas-lista { display: flex; flex-direction: column; gap: 0; }
.metrica-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.metrica-item:last-child { border-bottom: none; }
.met-label { color: var(--text-muted); }
.met-val { font-weight: 600; color: var(--text-primary); font-family: var(--font-mono); }
.accent { color: var(--accent); }
.accent2 { color: var(--accent2); }
.danger { color: var(--danger); }

/* Keywords */
.keywords { display: flex; gap: 8px; flex-wrap: wrap; }
.keywords span { background: var(--accent-dim); color: var(--accent); padding: 4px 10px; border-radius: 999px; font-size: 12px; }

/* CTA */
.card-cta { display: flex; align-items: center; gap: 12px; border-color: rgba(124,111,247,0.2); background: rgba(124,111,247,0.04); }
.cta-ico { font-size: 24px; flex-shrink: 0; }
.cta-body { flex: 1; }
.cta-titulo { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cta-sub { font-size: 12px; color: var(--text-muted); }
.btn-entrevistar { background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 7px 14px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.btn-entrevistar:hover { opacity: 0.85; }

@media (max-width: 1080px) { .layout { grid-template-columns: 1fr; } .skeleton-body { grid-template-columns: 1fr; } }
</style>
