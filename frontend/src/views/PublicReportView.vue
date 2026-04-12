<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import service from '../api'

function md(text) {
  if (!text) return ''
  let r = text
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^[-•]\s(.+)$/gm, '<li>$1</li>')
    .replace(/\n\n+/g, '</p><p>')
    .replace(/\n/g, '<br>')
  return '<p>' + r + '</p>'
}

const route = useRoute()
const report = ref(null)
const carregando = ref(true)
const erro = ref('')
const clientName = ref('')
const shareCode = ref('')

onMounted(async () => {
  const code = route.params.code
  shareCode.value = code
  try {
    const res = await service.get(`/api/share/${code}`)
    const raw = res?.data?.data || res?.data || res
    report.value = raw
    clientName.value = raw?.client_name || ''
  } catch (e) {
    erro.value = e?.response?.data?.error || 'Codigo invalido ou expirado.'
  } finally {
    carregando.value = false
  }
})

const titulo = computed(() => report.value?.outline?.title || 'Relatorio')
const sections = computed(() => report.value?.outline?.sections || [])
const summary = computed(() => report.value?.outline?.summary || '')
</script>

<template>
  <div class="pub-wrap">
    <!-- Loading -->
    <div v-if="carregando" class="pub-loading">
      <div class="pub-spinner"></div>
      <p>Carregando relatorio...</p>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="pub-error">
      <h2>Acesso negado</h2>
      <p>{{ erro }}</p>
    </div>

    <!-- Report -->
    <div v-else class="pub-report">
      <!-- Header -->
      <header class="pub-header">
        <div class="pub-brand">🔭 AUGUR</div>
        <div class="pub-meta">
          <h1>{{ titulo }}</h1>
          <p v-if="clientName">Preparado para: <strong>{{ clientName }}</strong></p>
          <p class="pub-date">{{ report?.completed_at?.slice(0, 10) }}</p>
        </div>
      </header>

      <!-- Summary -->
      <section class="pub-summary" v-if="summary">
        <div class="pub-summary-text md-body" v-html="md(summary)"></div>
      </section>

      <!-- Sections -->
      <section v-for="(s, i) in sections" :key="i" class="pub-section">
        <h2 class="pub-sec-title">
          <span class="pub-sec-num">{{ String(i + 1).padStart(2, '0') }}</span>
          {{ s.title }}
        </h2>
        <div class="pub-sec-content md-body" v-html="md(s.content || '')"></div>
      </section>

      <!-- Footer -->
      <footer class="pub-footer">
        <div class="pub-footer-brand">🔭 AUGUR</div>
        <p>Preveja o futuro. Antes que ele aconteca.</p>
        <p class="pub-footer-small">augur.itcast.com.br</p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.pub-wrap { max-width:800px; margin:0 auto; padding:24px 16px 80px; font-family:'Space Grotesk',-apple-system,sans-serif; }
.pub-loading { text-align:center; padding:80px 0; color:#888; }
.pub-spinner { width:32px; height:32px; border:3px solid #e5e7eb; border-top-color:#00e5c3; border-radius:50%; animation:spin 1s linear infinite; margin:0 auto 16px; }
@keyframes spin { to { transform:rotate(360deg); } }
.pub-error { text-align:center; padding:80px 0; }
.pub-error h2 { color:#ff5a5a; margin-bottom:8px; }

.pub-header { text-align:center; padding:40px 0; border-bottom:2px solid #00e5c3; margin-bottom:32px; }
.pub-brand { font-size:14px; font-weight:700; color:#00e5c3; letter-spacing:3px; margin-bottom:16px; }
.pub-header h1 { font-size:24px; font-weight:700; color:#1a1a2e; line-height:1.3; margin-bottom:8px; }
.pub-header strong { color:#00e5c3; }
.pub-date { font-size:12px; color:#888; }

.pub-summary { background:#f0fdf9; border:1px solid #d1fae5; border-radius:12px; padding:20px; margin-bottom:32px; }
.pub-summary-text { font-size:14px; line-height:1.7; color:#333; }

.pub-section { margin-bottom:32px; }
.pub-sec-title { display:flex; align-items:center; gap:12px; font-size:18px; font-weight:700; color:#1a1a2e; margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid #e5e7eb; }
.pub-sec-num { font-size:12px; font-weight:800; color:#00e5c3; background:#f0fdf9; padding:4px 10px; border-radius:8px; font-family:'JetBrains Mono',monospace; }

.pub-sec-content { font-size:14px; line-height:1.8; color:#444; }
.pub-sec-content :deep(h3) { font-size:16px; font-weight:700; color:#1a1a2e; margin:20px 0 8px; }
.pub-sec-content :deep(blockquote) { border-left:3px solid #7c6ff7; background:#f8f7ff; padding:12px 16px; margin:12px 0; border-radius:0 8px 8px 0; font-style:italic; color:#555; }
.pub-sec-content :deep(strong) { color:#1a1a2e; }
.pub-sec-content :deep(ul), .pub-sec-content :deep(ol) { padding-left:20px; margin:8px 0; }
.pub-sec-content :deep(li) { margin:4px 0; }

.pub-footer { text-align:center; padding:40px 0; border-top:2px solid #00e5c3; margin-top:40px; }
.pub-footer-brand { font-size:18px; font-weight:700; color:#00e5c3; margin-bottom:8px; }
.pub-footer p { font-size:13px; color:#888; font-style:italic; }
.pub-footer-small { font-size:11px; color:#bbb; margin-top:8px; }

@media print {
  .pub-wrap { max-width:100%; }
  .pub-section { break-inside:avoid; }
}
</style>
