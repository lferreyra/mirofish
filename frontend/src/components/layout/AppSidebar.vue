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
/* ═══ AUGUR Light Design System ═══ */
:root {
  --bg-base: #f5f5fa;
  --bg-surface: #ffffff;
  --bg-raised: #fafafe;
  --bg-overlay: #f0f0f5;
  --border: #eeeef2;
  --border-md: #dddde5;
  --text-primary: #1a1a2e;
  --text-secondary: #444466;
  --text-muted: #8888aa;
  --accent: #00e5c3;
  --accent-dim: rgba(0,229,195,0.08);
  --accent2: #7c6ff7;
  --accent2-dim: rgba(124,111,247,0.08);
  --danger: #ff5a5a;
  --font-mono: 'JetBrains Mono', monospace;
}

.topbar { height:56px; border-bottom:1px solid var(--border); background:var(--bg-surface); padding:0 20px; display:flex; align-items:center; justify-content:space-between; }
h1 { font-size:16px; margin:0; color:var(--text-primary); }
.actions { display:flex; gap:10px; align-items:center; }
</style>
