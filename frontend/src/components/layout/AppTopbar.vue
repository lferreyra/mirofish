<script setup>
defineProps({
  title: { type: String, default: '' }
})
</script>

<template>
  <header class="topbar">
    <h1>{{ title }}</h1>
    <div class="actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.topbar { height:56px; border-bottom:1px solid var(--border); background:var(--bg-surface); padding:0 20px; display:flex; align-items:center; justify-content:space-between; }
h1 { font-size:16px; margin:0; color:var(--text-primary); }
.actions { display:flex; gap:10px; align-items:center; }
</style>
