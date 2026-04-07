<script setup>
import { onMounted, ref, computed, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import service from '../api'
import { marked } from 'marked'

const route = useRoute()
const token = computed(() => route.params.token)

const report = ref(null)
const carregando = ref(true)
const erro = ref('')
const chatOpen = ref(false)
const chatMsg = ref('')
const chatHistory = ref([])
const chatLoading = ref(false)
const activeTab = ref('report') // report | chat

function md(txt) { return marked.parse(txt || '', { breaks: true }) }
function truncar(t, n) { return (t || '').length > n ? t.slice(0, n) + '...' : t }

const titulo = computed(() => report.value?.outline?.title || 'Relatório de Previsão')
const secoes = computed(() => report.value?.outline?.sections || [])
const simReq = computed(() => report.value?.simulation_requirement || report.value?.outline?.summary || '')
const confianca = computed(() => {
  const src = (secoes.value[0]?.content || '') + ' ' + (report.value?.outline?.summary || '')
  const m = src.match(/(\d{1,3})%/)
  return m ? parseInt(m[1]) : 72
})

onMounted(async () => {
  carregando.value = true
  try {
    const res = await service.get(`/api/public/report/${token.value}`)
    report.value = res?.data?.data || res?.data || null
    if (!report.value) erro.value = 'Relatório não encontrado ou link expirado.'
  } catch (e) {
    erro.value = e?.response?.data?.error || 'Link inválido ou expirado.'
  } finally {
    carregando.value = false
  }
})

async function enviarChat() {
  if (!chatMsg.value.trim() || chatLoading.value) return
  const msg = chatMsg.value.trim()
  chatHistory.value.push({ role: 'user', content: msg })
  chatMsg.value = ''
  chatLoading.value = true

  try {
    const res = await service.post(`/api/public/report/${token.value}/chat`, {
      message: msg,
      chat_history: chatHistory.value.slice(-10)
    })
    const resp = res?.data?.data?.response || 'Sem resposta.'
    chatHistory.value.push({ role: 'assistant', content: resp })
  } catch {
    chatHistory.value.push({ role: 'assistant', content: '⚠️ Erro ao processar. Tente novamente.' })
  } finally {
    chatLoading.value = false
    await nextTick()
    const el = document.querySelector('.chat-messages')
    if (el) el.scrollTop = el.scrollHeight
  }
}
</script>

<template>
  <div class="pub-page">
    <!-- Header -->
    <header class="pub-header">
      <div class="ph-brand">🔭 <strong>AUGUR</strong> <span class="ph-sep">·</span> Análise Preditiva</div>
      <div class="ph-tabs">
        <button :class="['ph-tab', {active: activeTab==='report'}]" @click="activeTab='report'">📊 Relatório</button>
        <button :class="['ph-tab', {active: activeTab==='chat'}]" @click="activeTab='chat'">💬 Conversar com IA</button>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="carregando" class="pub-state"><div class="spin"></div>Carregando relatório...</div>
    <div v-else-if="erro" class="pub-state pub-err">⚠️ {{ erro }}</div>

    <!-- Report Tab -->
    <main v-else-if="activeTab==='report'" class="pub-content">
      <h1 class="pub-title">{{ titulo }}</h1>
      <p class="pub-sub">{{ truncar(simReq, 200) }}</p>

      <!-- Confiança -->
      <div class="conf-bar">
        <div class="conf-fill" :style="{width: confianca + '%'}"></div>
        <span class="conf-label">Confiança: {{ confianca }}%</span>
      </div>

      <!-- Seções -->
      <div v-for="(sec, i) in secoes" :key="i" class="pub-section">
        <details :open="i < 3">
          <summary class="sec-title">
            <span class="sec-num">{{ String(i+1).padStart(2,'0') }}</span>
            {{ sec.title }}
          </summary>
          <div class="sec-body md-body" v-html="md(sec.content || '')"></div>
        </details>
      </div>

      <!-- CTA Chat -->
      <div class="pub-cta">
        <p>Tem perguntas sobre este relatório?</p>
        <button class="pub-btn" @click="activeTab='chat'">💬 Conversar com a IA</button>
      </div>

      <footer class="pub-footer">
        AUGUR by itcast · Análise gerada por simulação multiagente com IA
      </footer>
    </main>

    <!-- Chat Tab -->
    <main v-else-if="activeTab==='chat'" class="pub-chat">
      <div class="chat-header">
        <h2>💬 Converse sobre o relatório</h2>
        <p>Pergunte sobre cenários, riscos, agentes ou qualquer aspecto da análise.</p>
      </div>

      <div class="chat-messages">
        <div v-if="!chatHistory.length" class="chat-empty">
          <div class="ce-icon">🔭</div>
          <div class="ce-text">Faça uma pergunta para começar</div>
          <div class="ce-suggestions">
            <button @click="chatMsg='Quais são os principais riscos?'; enviarChat()">⚠️ Riscos</button>
            <button @click="chatMsg='Resuma os cenários futuros'; enviarChat()">🔭 Cenários</button>
            <button @click="chatMsg='Quais são as recomendações?'; enviarChat()">🎯 Recomendações</button>
          </div>
        </div>

        <div v-for="(m, i) in chatHistory" :key="i" :class="['chat-msg', m.role]">
          <div class="msg-avatar">{{ m.role === 'user' ? '👤' : '🔭' }}</div>
          <div class="msg-content" v-html="m.role === 'assistant' ? md(m.content) : m.content"></div>
        </div>

        <div v-if="chatLoading" class="chat-msg assistant">
          <div class="msg-avatar">🔭</div>
          <div class="msg-content typing">Analisando<span class="dots">...</span></div>
        </div>
      </div>

      <div class="chat-input">
        <input v-model="chatMsg" @keydown.enter="enviarChat" placeholder="Pergunte sobre o relatório..." :disabled="chatLoading" />
        <button @click="enviarChat" :disabled="chatLoading || !chatMsg.trim()">Enviar</button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pub-page { min-height:100vh;background:#f8f9fc;color:#1a1a2e;font-family:'Helvetica Neue',-apple-system,Arial,sans-serif; }

/* Header */
.pub-header { display:flex;align-items:center;justify-content:space-between;padding:12px 24px;background:#fff;border-bottom:1px solid rgba(0,0,0,0.08);position:sticky;top:0;z-index:10; }
.ph-brand { font-size:14px;color:#4a4a6a; }
.ph-brand strong { color:#1a1a2e; }
.ph-sep { color:#ccc;margin:0 4px; }
.ph-tabs { display:flex;gap:4px; }
.ph-tab { background:none;border:1px solid rgba(0,0,0,0.08);color:#4a4a6a;padding:6px 16px;border-radius:8px;font-size:13px;cursor:pointer;font-weight:600;transition:all .15s; }
.ph-tab.active { background:#6c5ce7;color:#fff;border-color:#6c5ce7; }

/* States */
.pub-state { display:flex;flex-direction:column;align-items:center;gap:12px;padding:80px;color:#8888a0;font-size:14px; }
.pub-err { color:#e74c3c; }
.spin { width:24px;height:24px;border:3px solid #ddd;border-top-color:#6c5ce7;border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to{transform:rotate(360deg)} }

/* Content */
.pub-content { max-width:800px;margin:0 auto;padding:32px 24px; }
.pub-title { font-size:24px;font-weight:800;color:#1a1a2e;margin-bottom:8px; }
.pub-sub { font-size:14px;color:#4a4a6a;line-height:1.7;margin-bottom:24px; }

/* Confidence bar */
.conf-bar { position:relative;height:32px;background:#e8e9f0;border-radius:8px;overflow:hidden;margin-bottom:32px; }
.conf-fill { height:100%;background:linear-gradient(90deg,#6c5ce7,#00b894);border-radius:8px;transition:width 1s ease; }
.conf-label { position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.3); }

/* Sections */
.pub-section { margin-bottom:8px; }
.pub-section details { background:#fff;border:1px solid rgba(0,0,0,0.06);border-radius:12px;overflow:hidden; }
.sec-title { padding:16px 20px;cursor:pointer;font-size:15px;font-weight:700;color:#1a1a2e;display:flex;align-items:center;gap:12px;list-style:none; }
.sec-title::-webkit-details-marker { display:none; }
.sec-num { background:#6c5ce7;color:#fff;width:28px;height:28px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;flex-shrink:0; }
.sec-body { padding:0 20px 20px;border-top:1px solid rgba(0,0,0,0.04); }
.md-body { font-size:14px;color:#4a4a6a;line-height:1.8; }
.md-body :deep(h1),.md-body :deep(h2),.md-body :deep(h3) { color:#1a1a2e;margin:16px 0 8px; }
.md-body :deep(blockquote) { border-left:3px solid #6c5ce7;padding-left:12px;margin:12px 0;color:#6c5ce7;font-style:italic; }
.md-body :deep(strong) { color:#1a1a2e; }
.md-body :deep(ul),.md-body :deep(ol) { padding-left:20px;margin:8px 0; }

/* CTA */
.pub-cta { text-align:center;padding:32px;background:linear-gradient(135deg,rgba(108,92,231,0.06),rgba(0,184,148,0.06));border:1px solid rgba(108,92,231,0.15);border-radius:16px;margin-top:32px; }
.pub-cta p { font-size:14px;color:#4a4a6a;margin-bottom:12px; }
.pub-btn { background:#6c5ce7;color:#fff;border:none;padding:10px 24px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;transition:transform .15s; }
.pub-btn:hover { transform:translateY(-1px); }

/* Footer */
.pub-footer { text-align:center;padding:24px;font-size:11px;color:#8888a0;margin-top:32px; }

/* ═══ Chat ═══ */
.pub-chat { max-width:800px;margin:0 auto;display:flex;flex-direction:column;height:calc(100vh - 56px); }
.chat-header { padding:24px 24px 16px;text-align:center; }
.chat-header h2 { font-size:18px;color:#1a1a2e; }
.chat-header p { font-size:13px;color:#8888a0;margin-top:4px; }

.chat-messages { flex:1;overflow-y:auto;padding:12px 24px;display:flex;flex-direction:column;gap:12px; }
.chat-empty { text-align:center;padding:40px;color:#8888a0; }
.ce-icon { font-size:48px;margin-bottom:8px; }
.ce-text { font-size:14px;margin-bottom:16px; }
.ce-suggestions { display:flex;gap:8px;justify-content:center;flex-wrap:wrap; }
.ce-suggestions button { background:#fff;border:1px solid rgba(0,0,0,0.08);color:#4a4a6a;padding:8px 14px;border-radius:8px;font-size:12px;cursor:pointer;transition:all .15s; }
.ce-suggestions button:hover { border-color:#6c5ce7;color:#6c5ce7; }

.chat-msg { display:flex;gap:10px;max-width:85%; }
.chat-msg.user { align-self:flex-end;flex-direction:row-reverse; }
.msg-avatar { width:32px;height:32px;border-radius:50%;background:#e8e9f0;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0; }
.chat-msg.assistant .msg-avatar { background:#6c5ce7;color:#fff; }
.msg-content { background:#fff;border:1px solid rgba(0,0,0,0.06);border-radius:12px;padding:10px 14px;font-size:13px;line-height:1.7;color:#1a1a2e; }
.chat-msg.user .msg-content { background:#6c5ce7;color:#fff;border:none; }
.typing { color:#8888a0; }
.dots { animation:blink 1s infinite; }
@keyframes blink { 0%,100%{opacity:1}50%{opacity:0.3} }

.chat-input { display:flex;gap:8px;padding:16px 24px;border-top:1px solid rgba(0,0,0,0.06);background:#fff; }
.chat-input input { flex:1;background:#f8f9fc;border:1px solid rgba(0,0,0,0.08);padding:10px 14px;border-radius:10px;font-size:13px;outline:none;color:#1a1a2e; }
.chat-input input:focus { border-color:#6c5ce7; }
.chat-input button { background:#6c5ce7;color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer; }
.chat-input button:disabled { opacity:0.5; }

@media(max-width:600px) { .pub-content,.pub-chat{padding:16px} .ph-tabs{gap:2px} .ph-tab{font-size:11px;padding:6px 10px} }
</style>
