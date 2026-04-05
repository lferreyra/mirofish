<script setup>
import { computed } from 'vue'
const props = defineProps({ positive: Number, neutral: Number, negative: Number, label: String })
const total = computed(() => (props.positive || 0) + (props.neutral || 0) + (props.negative || 0) || 1)
const pct = (v) => `${Math.round(((v || 0) / total.value) * 100)}%`
</script>
<template>
  <section class="wrap">
    <div class="header">{{ label }}</div>
    <div class="bar">
      <span class="pos" :style="{ width: pct(positive) }" />
      <span class="neu" :style="{ width: pct(neutral) }" />
      <span class="neg" :style="{ width: pct(negative) }" />
    </div>
    <div class="legend">
      <small>Positivo {{ pct(positive) }}</small>
      <small>Neutro {{ pct(neutral) }}</small>
      <small>Negativo {{ pct(negative) }}</small>
    </div>
  </section>
</template>
<style scoped>
.wrap { background:var(--bg-raised); border:1px solid var(--border); border-radius:var(--r-md); padding:12px; }
.header { margin-bottom:8px; color:var(--text-secondary); }
.bar { height:10px; border-radius:999px; overflow:hidden; display:flex; background:var(--bg-overlay); }
.pos { background:#00e5c3; }
.neu { background:#7c6ff7; }
.neg { background:#ff5a5a; }
.legend { margin-top:8px; display:flex; justify-content:space-between; color:var(--text-muted); font-size:12px; }
</style>
