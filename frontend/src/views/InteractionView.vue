<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'
import AgentCard from '../components/simulation/AgentCard.vue'

const route = useRoute()
const agents = ref([])
const selected = ref(null)
const messages = ref([])
const prompt = ref('')
const groupPrompt = ref('')
const languageWarning = ref('')
const hasCJK = (value = '') => /[\u3400-\u9FFF]/.test(value)
const sanitizeText = (value = '') => hasCJK(value) ? 'Resposta em idioma não-português detectada. Solicite novamente em português.' : value

onMounted(async () => {
  const report = await service.get(`/api/report/${route.params.reportId}`)
  const raw = report.data || report
  agents.value = raw.agents || []
  if (agents.value.some((a) => hasCJK(a?.description || a?.role || ''))) {
    languageWarning.value = '⚠️ Alguns agentes retornaram conteúdo em idioma não-português. As respostas exibidas serão higienizadas.'
  }
  selected.value = agents.value[0] || null
})

const send = async () => {
  if (!selected.value || !prompt.value) return
  messages.value.push({ role: 'Você', text: prompt.value })
  const response = await service.post('/api/simulation/interview', { report_id: route.params.reportId, agent_id: selected.value.id, message: prompt.value })
  const raw = response.data || response
  messages.value.push({ role: selected.value.name, text: sanitizeText(raw.answer || raw.message || 'Sem resposta.') })
  prompt.value = ''
}

const sendAll = async () => {
  if (!groupPrompt.value) return
  await service.post('/api/simulation/interview/all', { report_id: route.params.reportId, message: groupPrompt.value })
  groupPrompt.value = ''
}
</script>
<template>
  <AppShell title="Entrevistar Agentes">
    <template #actions>
      <select v-model="selected" class="select">
        <option v-for="agent in agents" :key="agent.id" :value="agent">{{ agent.name }}</option>
      </select>
      <AugurButton variant="ghost" @click="sendAll">Entrevistar todos</AugurButton>
    </template>

    <section class="layout">
      <div class="chat">
        <article class="warn" v-if="languageWarning">{{ languageWarning }}</article>
        <article class="profile" v-if="selected">
          <h3>{{ selected.name }}</h3>
          <p>{{ selected.role || 'Analista de opinião pública' }}</p>
        </article>
        <article class="messages">
          <p v-for="(m, idx) in messages" :key="idx"><strong>{{ m.role }}:</strong> {{ m.text }}</p>
          <p v-if="!messages.length">Faça sua primeira pergunta para iniciar a entrevista.</p>
        </article>
        <div class="input-row">
          <input v-model="prompt" placeholder="Enviar pergunta ao agente..." @keyup.enter="send" />
          <AugurButton @click="send">Enviar</AugurButton>
        </div>
      </div>
      <aside class="side">
        <div class="agents"><AgentCard v-for="agent in agents" :key="agent.id" :agent="agent" :selected="selected?.id===agent.id" @select="selected = $event" /></div>
        <div class="group">
          <textarea rows="5" v-model="groupPrompt" placeholder="Pergunta para todos os agentes ao mesmo tempo..." />
          <AugurButton variant="ghost" @click="sendAll">Enviar para todos os agentes</AugurButton>
        </div>
      </aside>
    </section>
  </AppShell>
</template>
<style scoped>
.layout{display:grid;grid-template-columns:55% 45%;gap:12px}.chat,.side{display:grid;gap:10px}
.profile,.messages,.group{background:var(--bg-raised);border:1px solid var(--border);border-radius:var(--r-md);padding:12px}
.warn{background:rgba(255,166,0,.12);border:1px solid rgba(255,166,0,.4);padding:10px;border-radius:var(--r-sm);font-size:13px}
.messages{min-height:260px;max-height:420px;overflow:auto}.input-row{display:flex;gap:8px}
input,textarea,.select{background:var(--bg-overlay);border:1px solid var(--border-md);color:var(--text-primary);padding:10px;border-radius:var(--r-sm);width:100%}
.agents{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
@media(max-width:1080px){.layout{grid-template-columns:1fr}.agents{grid-template-columns:1fr}}
</style>
