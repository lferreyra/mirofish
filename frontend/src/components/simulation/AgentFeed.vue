<script setup>
import { ref, computed } from 'vue'
import service from '../../api'
import { usePolling } from '../../composables/usePolling'

const props = defineProps({
  simulationId: String,
  platform: { type: String, default: 'twitter' },
  limit: { type: Number, default: 8 }
})

const posts = ref([])
const total = ref(0)

const cores = ['#00e5c3','#7c6ff7','#1da1f2','#f5a623','#ff5a5a','#e91e9c','#4caf50','#ff9800','#9c27b0','#00bcd4']

function iniciais(name) {
  return (name || '??').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
}
function corAvatar(name) {
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return cores[Math.abs(hash) % cores.length]
}

// Sentimento simples baseado em likes/dislikes
function sentimento(post) {
  const likes = post.num_likes || 0
  const dislikes = post.num_dislikes || 0
  if (likes > dislikes * 2) return 'positivo'
  if (dislikes > likes) return 'negativo'
  return 'neutro'
}
function sentCor(sent) {
  if (sent === 'positivo') return '#00e5c3'
  if (sent === 'negativo') return '#ff5a5a'
  return 'var(--text-muted)'
}

const load = async () => {
  if (!props.simulationId) return
  try {
    const res = await service.get(`/api/simulation/${props.simulationId}/posts`, {
      params: { platform: props.platform, limit: props.limit }
    })
    const raw = res?.data?.data || res?.data || res
    posts.value = raw?.posts || raw?.items || []
    total.value = raw?.count || posts.value.length
  } catch { /* silencioso */ }
}

const { start, stop } = usePolling(load, 4000)
start()
defineExpose({ start, stop })

const platformIcon = computed(() => props.platform === 'twitter' ? '🐦' : '🔴')
const platformName = computed(() => props.platform === 'twitter' ? 'Twitter' : 'Reddit')
</script>

<template>
  <section class="feed">
    <header class="feed-header">
      <div class="fh-left">
        <span class="fh-icon">{{ platformIcon }}</span>
        <span class="fh-name">{{ platformName }}</span>
        <span class="fh-live">ao vivo</span>
      </div>
      <span class="fh-count" v-if="total">{{ total }} posts</span>
    </header>

    <div class="posts-list">
      <article v-for="(post, idx) in posts" :key="post.post_id || idx" class="post" :class="'post-' + sentimento(post)">
        <div class="post-top">
          <div class="avatar" :style="{background: corAvatar(post.author || post.username || post.user_name)}">
            {{ iniciais(post.author || post.username || post.user_name) }}
          </div>
          <div class="post-meta">
            <div class="post-author">{{ post.author || post.username || post.user_name || 'Agente' }}</div>
            <div class="post-time" v-if="post.created_at">{{ new Date(post.created_at).toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'}) }}</div>
          </div>
          <div class="sent-dot" :style="{background: sentCor(sentimento(post))}" :title="sentimento(post)"></div>
        </div>
        <div class="post-body">{{ (post.content || post.text || 'Sem conteúdo.').slice(0, 200) }}</div>
        <div class="post-stats" v-if="post.num_likes || post.num_dislikes || post.num_comments">
          <span v-if="post.num_likes" class="stat-like">❤️ {{ post.num_likes }}</span>
          <span v-if="post.num_dislikes" class="stat-dislike">👎 {{ post.num_dislikes }}</span>
          <span v-if="post.num_comments" class="stat-comment">💬 {{ post.num_comments }}</span>
        </div>
      </article>

      <div v-if="!posts.length" class="empty">
        <div class="empty-icon">💬</div>
        <div>Aguardando posts dos agentes...</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.feed { background:var(--bg-surface);border:1px solid var(--border);border-radius:12px;overflow:hidden; }

.feed-header { display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border);background:var(--bg-raised); }
.fh-left { display:flex;align-items:center;gap:6px; }
.fh-icon { font-size:14px; }
.fh-name { font-size:13px;font-weight:700;color:var(--text-primary); }
.fh-live { font-size:10px;color:var(--accent);font-weight:600;background:rgba(0,229,195,0.1);padding:2px 6px;border-radius:8px; }
.fh-count { font-size:11px;color:var(--text-muted); }

.posts-list { display:flex;flex-direction:column;gap:1px;max-height:400px;overflow-y:auto; }

.post { padding:12px 16px;display:flex;flex-direction:column;gap:6px;border-left:3px solid transparent;transition:background .1s; }
.post:hover { background:var(--bg-raised); }
.post-positivo { border-left-color:#00e5c3; }
.post-negativo { border-left-color:#ff5a5a; }
.post-neutro { border-left-color:var(--border); }

.post-top { display:flex;align-items:center;gap:10px; }
.avatar { width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:#fff;flex-shrink:0; }
.post-meta { flex:1; }
.post-author { font-size:12px;font-weight:700;color:var(--text-primary); }
.post-time { font-size:10px;color:var(--text-muted); }
.sent-dot { width:8px;height:8px;border-radius:50%;flex-shrink:0; }

.post-body { font-size:12.5px;color:var(--text-secondary);line-height:1.6; }

.post-stats { display:flex;gap:10px;font-size:11px;color:var(--text-muted); }
.stat-like { color:#ff5a5a; }

.empty { text-align:center;padding:28px 16px;color:var(--text-muted);font-size:12px; }
.empty-icon { font-size:24px;margin-bottom:6px; }
</style>
