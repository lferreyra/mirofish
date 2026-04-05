<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import logoPath from '../../assets/logo/augur-logo.svg'

const route = useRoute()
const groups = [
  { title: 'PRINCIPAL', items: [
    { label: 'Dashboard', to: '/' },
    { label: 'Nova Simulação', to: '/novo' },
    { label: 'Em Execução', to: '/simulacao/execucao' }
  ] },
  { title: 'ANÁLISE', items: [
    { label: 'Relatórios', to: '/relatorio/ultimo' },
    { label: 'Entrevistar Agentes', to: '/agentes/ultimo' }
  ] },
  { title: 'SISTEMA', items: [
    { label: 'Configurações', to: '/configuracoes' }
  ] }
]

const isActive = (path) => computed(() => route.path === path || route.path.startsWith(path + '/')).value
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <img :src="logoPath" alt="AUGUR" />
      <div>
        <strong>AUGUR</strong>
        <small>by itcast</small>
      </div>
    </div>

    <div v-for="group in groups" :key="group.title" class="group">
      <p>{{ group.title }}</p>
      <RouterLink
        v-for="item in group.items"
        :key="item.to"
        :to="item.to"
        class="item"
        :class="{ active: isActive(item.to) }"
      >
        {{ item.label }}
      </RouterLink>
    </div>

    <div class="footer">Workspace</div>
  </aside>
</template>

<style scoped>
.sidebar { width:220px; flex-shrink:0; background:var(--bg-surface); border-right:1px solid var(--border); padding:14px 0; display:flex; flex-direction:column; overflow:auto; }
.brand { display:flex; gap:10px; align-items:center; padding:0 14px 18px; border-bottom:1px solid var(--border); }
.brand img { width:32px; height:32px; }
.brand strong { display:block; font-size:14px; }
.brand small { color:var(--text-secondary); }
.group { padding:14px 10px 0; }
.group p { margin:0 8px 8px; color:var(--text-muted); font-size:11px; letter-spacing:.8px; }
.item { display:block; color:var(--text-secondary); text-decoration:none; padding:9px 10px; border-radius:var(--r-sm); border-left:2px solid transparent; transition:var(--t-fast); }
.item:hover { background:var(--bg-raised); color:var(--text-primary); }
.item.active { border-left-color:var(--accent); background:var(--accent-dim); color:var(--accent); }
.footer { margin-top:auto; padding:14px; border-top:1px solid var(--border); color:var(--text-muted); }
@media (max-width: 768px) {
  .sidebar { width:72px; }
  .brand div, .group p, .footer { display:none; }
  .item { font-size:0; height:36px; }
  .item::before { content:'•'; font-size:20px; color:currentColor; display:block; text-align:center; line-height:18px; }
}
</style>
