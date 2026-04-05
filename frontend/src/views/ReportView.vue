<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import SentimentBar from '../components/ui/SentimentBar.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()
const report = ref({ summary: '', insights: [], metrics: {}, keywords: [] })

onMounted(async () => {
  const response = await service.get(`/api/report/${route.params.reportId}`)
  const raw = response.data || response
  report.value = {
    summary: raw.summary || raw.executive_summary || 'Sem sumário disponível.',
    insights: raw.insights || [],
    metrics: raw.metrics || {},
    keywords: raw.keywords || []
  }
})

const colorByTag = (tag) => ({ Oportunidade: '#00e5c3', Risco: '#ff5a5a', Observação: '#7c6ff7' }[tag] || '#9898b0')
</script>
<template>
  <AppShell title="Relatório">
    <template #actions>
      <AugurButton variant="ghost">Exportar PDF</AugurButton>
      <AugurButton @click="router.push(`/agentes/${route.params.reportId}`)">Entrevistar Agentes</AugurButton>
    </template>
    <section class="layout">
      <div class="main">
        <article class="summary"><h3>Sumário Executivo</h3><p>{{ report.summary }}</p></article>
        <article class="card">
          <h3>Insights detalhados</h3>
          <div v-for="(insight, idx) in report.insights" :key="idx" class="insight">
            <span class="tag" :style="{ color: colorByTag(insight.tag), borderColor: colorByTag(insight.tag) }">{{ insight.tag || 'Observação' }}</span>
            <p>{{ insight.text || insight.description }}</p>
            <small>Confiança: {{ insight.confidence || 0 }}%</small>
          </div>
        </article>
      </div>
      <aside class="side">
        <SentimentBar label="Sentimento geral" :positive="report.metrics.positive || 50" :neutral="report.metrics.neutral || 30" :negative="report.metrics.negative || 20" />
        <article class="card"><h3>Principais métricas</h3><p>Agentes alcançados: {{ report.metrics.agents_reached || 0 }}</p><p>Posts gerados: {{ report.metrics.posts_generated || 0 }}</p><p>Intenção de compra: {{ report.metrics.purchase_intent || 0 }}%</p><p>Probabilidade de viral: {{ report.metrics.viral_probability || 0 }}%</p></article>
        <article class="card"><h3>Palavras-chave</h3><div class="keywords"><span v-for="(keyword,idx) in report.keywords" :key="idx">{{ keyword }}</span></div></article>
      </aside>
    </section>
  </AppShell>
</template>
<style scoped>
.layout{display:grid;grid-template-columns:2fr 1fr;gap:12px}.main,.side{display:grid;gap:10px}
.summary{border-left:3px solid var(--accent);background:var(--bg-raised);padding:14px;border-radius:var(--r-md);border:1px solid var(--border)}
.card{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:14px}
.insight{border-top:1px solid var(--border);padding-top:10px;margin-top:10px}.tag{border:1px solid;padding:2px 7px;border-radius:999px;font-size:12px}
.keywords{display:flex;gap:8px;flex-wrap:wrap}.keywords span{background:var(--accent-dim);padding:4px 8px;border-radius:999px}
@media(max-width:1080px){.layout{grid-template-columns:1fr}}
</style>
