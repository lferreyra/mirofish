<script setup>
const props = defineProps({ title: String, value: [String, Number], sub: String, trend: String })
</script>
<template>
  <article class="card">
    <small>{{ title }}</small>
    <h3>{{ value }}</h3>
    <footer :class="trend">{{ sub }}</footer>
  </article>
</template>
<style scoped>
.card { background:var(--bg-raised); border:1px solid var(--border); border-radius:var(--r-md); padding:14px; }
small { color:var(--text-muted); display:block; margin-bottom:8px; }
h3 { margin:0; font-family:var(--font-mono); font-size:28px; }
footer { margin-top:8px; color:var(--text-secondary); font-size:13px; }
footer.up { color:var(--success); }
footer.down { color:var(--danger); }
</style>
