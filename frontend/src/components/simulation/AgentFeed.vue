<script setup>
import { ref } from 'vue'
import service from '../../api'
import { usePolling } from '../../composables/usePolling'

const props = defineProps({ simulationId: String, platform: { type: String, default: 'twitter' } })
const posts = ref([])

const load = async () => {
  if (!props.simulationId) return
  const response = await service.get(`/api/simulation/${props.simulationId}/posts`, { params: { platform: props.platform, limit: 5 } })
  const raw = response.data || response
  posts.value = raw.posts || raw.items || []
}

const { start, stop } = usePolling(load, 3000)
start()
defineExpose({ start, stop })
</script>
<template>
  <section class="feed">
    <header>{{ platform === 'twitter' ? 'Twitter' : 'Reddit' }} · <span class="live">ao vivo</span></header>
    <article v-for="(post, idx) in posts" :key="idx" class="post">
      <strong>{{ post.author || post.username || 'Agente' }}</strong>
      <p>{{ post.content || post.text || 'Sem conteúdo.' }}</p>
    </article>
    <p v-if="!posts.length" class="empty">Aguardando novos posts...</p>
  </section>
</template>
<style scoped>
.feed{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:12px;display:grid;gap:10px}
header{font-weight:600}.live{color:var(--accent)}
.post{background:var(--bg-overlay);border-radius:var(--r-sm);padding:9px}
.post p{margin:4px 0 0;color:var(--text-secondary)}
.empty{color:var(--text-muted)}
</style>
