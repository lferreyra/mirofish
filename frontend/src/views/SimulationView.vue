<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import service from '../api'

const route = useRoute()
const router = useRouter()
const data = ref(null)

onMounted(async () => {
  const response = await service.get('/api/simulation/history', { params: { limit: 10 } })
  const raw = response.data || response
  data.value = (raw.history || raw.items || []).find((item) => String(item.project_id || item.id) === String(route.params.projectId))
})
</script>
<template>
  <AppShell title="Detalhes da Simulação">
    <section class="panel">
      <h3>{{ data?.name || 'Projeto AUGUR' }}</h3>
      <p>Visualize os parâmetros da simulação e inicie a execução.</p>
      <ul>
        <li>Agentes: {{ data?.agent_count || '-' }}</li>
        <li>Rodadas: {{ data?.max_rounds || data?.rounds || '-' }}</li>
        <li>Status: {{ data?.status || 'rascunho' }}</li>
      </ul>
      <AugurButton @click="router.push(`/simulacao/${data?.id || route.params.projectId}/executar`)">Executar Simulação</AugurButton>
    </section>
  </AppShell>
</template>
<style scoped>.panel{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:18px}</style>
