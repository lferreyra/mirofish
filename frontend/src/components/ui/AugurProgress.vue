<script setup>
defineProps({ value: { type: Number, default: 0 }, height: { type: Number, default: 4 } })
</script>
<template>
  <div class="track" :style="{ height: `${height}px` }">
    <div class="fill" :style="{ width: `${Math.max(0, Math.min(100, value))}%` }" />
  </div>
</template>
<style scoped>
.track { width:100%; background:var(--bg-overlay); border-radius:999px; overflow:hidden; }
.fill { height:100%; background:var(--accent); transition:width var(--t-mid); }
</style>
