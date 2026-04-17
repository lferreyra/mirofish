<template>
  <div class="centered-panel">

    <!-- Generating -->
    <div v-if="isLoading" class="loading-block">
      <div class="loading-ring"></div>
      <p class="loading-label">Report Agent is analysing the simulation…</p>
      <p class="loading-hint">{{ reportProgress }}</p>
    </div>

    <!-- Report ready -->
    <div v-else-if="reportResult" class="report-ready">
      <div class="result-badge result-badge--ok">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12" />
        </svg>
        Report ready
      </div>

      <div class="report-sections" v-if="reportResult.outline?.sections?.length">
        <div v-for="(section, idx) in reportResult.outline.sections" :key="idx" class="report-section">
          <div class="rs-header" @click="toggleSection(idx)">
            <span class="rs-num">{{ String(idx + 1).padStart(2, '0') }}</span>
            <span class="rs-title">{{ section.title || ('Section ' + String(idx + 1).padStart(2, '0')) }}</span>
            <svg class="rs-chevron" :class="{ 'is-open': !collapsedSections.has(idx) }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
          <div v-show="!collapsedSections.has(idx)" class="rs-body">
            <p>{{ section.content }}</p>
          </div>
        </div>
      </div>
      <pre v-else-if="reportResult.markdown_content" class="report-markdown">{{ reportResult.markdown_content }}</pre>

      <div class="result-actions">
        <button class="btn-secondary" @click="onExport">
          Export .md
        </button>
        <button class="btn-secondary" @click="$emit('next')">
          Talk to Agents →
        </button>
      </div>
    </div>

    <!-- Error generating report -->
    <div v-else class="error-placeholder">
      <p>Report generation did not complete. Check logs and retry.</p>
      <button class="btn-secondary" @click="$emit('retry')">Retry</button>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { exportReportMarkdown } from '../../utils/private.js'

const props = defineProps({
  reportResult: { type: Object, default: null },
  isLoading: { type: Boolean, default: false },
  reportProgress: { type: String, default: '' },
  simId: { type: String, default: null },
})

defineEmits(['retry', 'next'])

const collapsedSections = ref(new Set())

const toggleSection = (idx) => {
  const s = new Set(collapsedSections.value)
  s.has(idx) ? s.delete(idx) : s.add(idx)
  collapsedSections.value = s
}

const onExport = () => {
  exportReportMarkdown(props.reportResult, props.simId)
}
</script>

<style scoped>
.centered-panel {
  max-width: 680px;
  margin: 0 auto;
}

.loading-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 60px 0;
  text-align: center;
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid #E5E7EB;
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-label { font-size: 14px; font-weight: 600; color: #000; }
.loading-hint { font-size: 12px; color: #888; max-width: 400px; line-height: 1.5; }

.result-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  padding: 6px 12px;
  border-radius: 2px;
}

.result-badge--ok { background: #E8F5E9; color: #2E7D32; }

.result-actions { display: flex; gap: 10px; }

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: #fff;
  color: #000;
  border: 1.5px solid #000;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-secondary:hover { background: #F5F5F5; }

.report-ready { display: flex; flex-direction: column; gap: 20px; padding: 20px 0; }
.report-markdown { white-space: pre-wrap; font-size: 13px; line-height: 1.7; color: #222; font-family: inherit; background: #FAFAFA; border: 1.5px solid #E8E8E8; border-radius: 4px; padding: 20px; margin: 0; }

.report-sections { display: flex; flex-direction: column; gap: 0; border: 1.5px solid #E8E8E8; border-radius: 4px; overflow: hidden; }

.report-section { border-bottom: 1px solid #F0F0F0; }
.report-section:last-child { border-bottom: none; }

.rs-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  background: #FAFAFA;
  transition: background 0.12s;
}

.rs-header:hover { background: #F3F3F3; }
.rs-num { font-size: 11px; font-weight: 700; color: #CCC; min-width: 24px; }
.rs-title { flex: 1; font-size: 13px; font-weight: 600; color: #000; }
.rs-chevron { flex-shrink: 0; transition: transform 0.2s; transform: rotate(-90deg); }
.rs-chevron.is-open { transform: rotate(0deg); }
.rs-body { padding: 14px 16px 14px 52px; font-size: 13px; color: #444; line-height: 1.6; background: #fff; }

.error-placeholder { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 40px 0; font-size: 13px; color: #888; }
</style>
