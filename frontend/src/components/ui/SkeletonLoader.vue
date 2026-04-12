<template>
  <div class="skeleton" :class="variant">
    <div v-for="n in lines" :key="n" class="sk-line" :style="{width: lineWidth(n), height: height}"></div>
  </div>
</template>
<script setup>
const props = defineProps({
  lines: { type: Number, default: 3 },
  height: { type: String, default: '12px' },
  variant: { type: String, default: 'text' } // text, card, metric
})
function lineWidth(n) {
  if (props.variant === 'metric') return '100%'
  if (props.variant === 'card') return '100%'
  const widths = ['100%', '85%', '70%', '90%', '60%']
  return widths[(n - 1) % widths.length]
}
</script>
<style scoped>
.skeleton { display:flex;flex-direction:column;gap:8px;padding:4px 0; }
.skeleton.card { gap:12px; }
.skeleton.metric { gap:6px; }
.sk-line { background:linear-gradient(90deg, var(--bg-overlay) 25%, var(--bg-raised) 50%, var(--bg-overlay) 75%);background-size:200% 100%;border-radius:6px;animation:shimmer 1.5s infinite; }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
</style>
