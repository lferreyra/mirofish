<script setup>
const props = defineProps({ currentRound: Number, totalRounds: Number, roundData: { type:Array, default:()=>[] } })
const bars = Array.from({ length: props.totalRounds || 0 }, (_, i) => i + 1)
const getHeight = (round) => `${Math.max(20, Math.min(100, (props.roundData[round - 1]?.activity || round * 3) % 100))}%`
</script>
<template>
  <div class="timeline">
    <div v-for="round in bars" :key="round" class="bar-wrap">
      <span class="bar" :class="round < currentRound ? 'done' : round === currentRound ? 'current' : 'future'" :style="{ height: getHeight(round) }"/>
      <small>{{ round }}</small>
    </div>
  </div>
</template>
<style scoped>
.timeline{display:flex;gap:6px;align-items:flex-end;min-height:130px;overflow:auto;padding-top:16px}
.bar-wrap{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:16px}
.bar{width:10px;border-radius:8px;background:var(--bg-surface)}
.done{background:rgba(0,229,195,.5)}
.current{background:var(--accent)}
.future{background:var(--bg-surface)}
small{font-size:10px;color:var(--text-muted)}
</style>
