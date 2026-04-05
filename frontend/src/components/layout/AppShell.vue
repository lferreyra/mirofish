<script setup>
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

defineProps({ title: { type: String, default: '' } })
</script>

<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopbar :title="title">
        <template #actions><slot name="actions" /></template>
      </AppTopbar>
      <main class="app-content"><slot /></main>
    </div>
  </div>
</template>

<style scoped>
.app-shell { display:flex; min-height:100vh; background:var(--bg-base); }
.app-main { flex:1; min-width:0; display:flex; flex-direction:column; }
.app-content { padding:24px; overflow:auto; height:calc(100vh - 56px); }
</style>
