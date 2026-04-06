<script setup>
import { onMounted, ref, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import service from '../api'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const route  = useRoute()
const router = useRouter()

// ─── State ─────────────────────────────────────────────────
const carregando    = ref(true)
const erro          = ref('')
const report        = ref(null)
const simulationId  = ref('')
const messages      = ref([])
const prompt        = ref('')
const enviando      = ref(false)
const chatBox       = ref(null)

// ─── Suggested questions ───────────────────────────────────
const sugestoes = [
  'Quais são os principais riscos?',
  'Como os agentes estão se comportando?',
  'Qual o cenário mais provável?',
  'O que recomenda como próximo passo?',
]

const titulo = computed(() => report.value?.outline?.title || 'Conversar com ReportAgent')

// ─── Load report to get simulation_id ──────────────────────
onMounted(async () => {
  carregando.value = true
  try {
    const res = await service.get(`/api/report/${route.params.reportId}`)
    const raw = res?.data?.data || res?.data || res
    report.value = raw
    simulationId.value = raw?.simulation_id || ''
    if (!simulationId.value) {
      erro.value = 'Relatório não possui simulation_id associado.'
    }
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao carregar relatório.'
  } finally {
    carregando.value = false
  }
})

// ─── Build chat history for context ────────────────────────
function buildHistory() {
  return messages.value.map(m => ({
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.text
  }))
}

// ─── Send message ──────────────────────────────────────────
async function enviar(texto) {
  const msg = (texto || prompt.value || '').trim()
  if (!msg || enviando.value || !simulationId.value) return

  messages.value.push({ role: 'user', text: msg, ts: Date.now() })
  prompt.value = ''
  enviando.value = true
  scrollToBottom()

  try {
    const res = await service.post('/api/report/chat', {
      simulation_id: simulationId.value,
      message: msg,
      chat_history: buildHistory().slice(0, -1) // exclude current msg
    })
    const raw = res?.data?.data || res?.data || res
    const resposta = raw?.response || raw?.message || raw?.answer || 'Sem resposta do agente.'
    messages.value.push({ role: 'assistant', text: resposta, ts: Date.now() })
  } catch (e) {
    const errMsg = e?.response?.data?.error || e?.message || 'Erro ao comunicar com o agente.'
    messages.value.push({ role: 'error', text: errMsg, ts: Date.now() })
  } finally {
    enviando.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

function voltarRelatorio() {
  router.push(`/relatorio/${route.params.reportId}`)
}

// Simple markdown for agent responses
function mdSimple(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^[-•]\s(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>')
}
</script>

<template>
  <AppShell :title="titulo">
    <template #actions>
      <AugurButton variant="ghost" @click="voltarRelatorio">← Relatório</AugurButton>
    </template>

    <!-- Loading -->
    <div v-if="carregando" class="state-box">
      <div class="spin"></div>
      <div class="state-text">Carregando contexto da simulação...</div>
    </div>

    <!-- Error -->
    <div v-else-if="erro" class="state-box state-err">
      <div class="state-icon">⚠️</div>
      <div class="state-text">{{ erro }}</div>
      <AugurButton variant="ghost" @click="voltarRelatorio">← Voltar ao Relatório</AugurButton>
    </div>

    <!-- Chat -->
    <div v-else class="chat-layout">

      <!-- Header info -->
      <div class="chat-header">
        <div class="ch-icon">🤖</div>
        <div class="ch-info">
          <div class="ch-title">ReportAgent — Análise Interativa</div>
          <div class="ch-sub">Faça perguntas sobre os resultados da simulação, cenários, riscos e recomendações.</div>
        </div>
      </div>

      <!-- Messages -->
      <div ref="chatBox" class="chat-messages">
        <!-- Welcome -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">💬</div>
          <div class="welcome-title">Pergunte qualquer coisa sobre a simulação</div>
          <div class="welcome-sub">O ReportAgent tem acesso a todos os dados simulados e pode buscar informações adicionais automaticamente.</div>
          <div class="suggestions">
            <button v-for="s in sugestoes" :key="s" class="sug-btn" @click="enviar(s)">{{ s }}</button>
          </div>
        </div>

        <!-- Message bubbles -->
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="'msg-' + m.role">
          <div class="msg-avatar">{{ m.role === 'user' ? '👤' : m.role === 'error' ? '⚠️' : '🤖' }}</div>
          <div class="msg-body">
            <div class="msg-sender">{{ m.role === 'user' ? 'Você' : m.role === 'error' ? 'Erro' : 'ReportAgent' }}</div>
            <div class="msg-text" v-if="m.role === 'user'">{{ m.text }}</div>
            <div class="msg-text md-body" v-else-if="m.role === 'error'" style="color:var(--danger)">{{ m.text }}</div>
            <div class="msg-text md-body" v-else v-html="mdSimple(m.text)"></div>
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="enviando" class="msg msg-assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-body">
            <div class="msg-sender">ReportAgent</div>
            <div class="typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input">
        <input
          v-model="prompt"
          :disabled="enviando"
          placeholder="Pergunte sobre a simulação..."
          @keyup.enter="enviar()"
        />
        <button class="send-btn" :disabled="!prompt.trim() || enviando" @click="enviar()">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>

      <!-- Footer -->
      <div class="chat-footer">
        Faça perguntas sobre os resultados, padrões e comportamentos dos agentes
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
/* ─── States ──────────────────────────────────────────── */
.state-box { display:flex;flex-direction:column;align-items:center;gap:14px;padding:60px;text-align:center; }
.state-icon { font-size:42px; }
.state-text { font-size:14px;color:var(--text-muted); }
.state-err .state-text { color:var(--danger); }
.spin { width:24px;height:24px;border:3px solid var(--border-md);border-top-color:var(--accent);border-radius:50%;animation:sp .7s linear infinite; }
@keyframes sp { to { transform:rotate(360deg) } }

/* ─── Chat layout ─────────────────────────────────────── */
.chat-layout { display:flex;flex-direction:column;height:calc(100vh - 80px);max-height:800px;background:var(--bg-surface);border:1px solid var(--border);border-radius:14px;overflow:hidden; }

.chat-header { display:flex;align-items:center;gap:14px;padding:16px 20px;border-bottom:1px solid var(--border);background:var(--bg-raised); }
.ch-icon { font-size:28px; }
.ch-title { font-size:14px;font-weight:700;color:var(--text-primary); }
.ch-sub { font-size:11px;color:var(--text-muted);margin-top:2px; }

/* ─── Messages ────────────────────────────────────────── */
.chat-messages { flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px; }

.welcome { text-align:center;padding:40px 20px; }
.welcome-icon { font-size:42px;margin-bottom:12px; }
.welcome-title { font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:6px; }
.welcome-sub { font-size:12.5px;color:var(--text-muted);max-width:400px;margin:0 auto 20px;line-height:1.6; }
.suggestions { display:flex;flex-wrap:wrap;gap:8px;justify-content:center; }
.sug-btn { background:var(--bg-raised);border:1px solid var(--border);color:var(--text-secondary);padding:8px 14px;border-radius:20px;font-size:12px;cursor:pointer;transition:all .15s; }
.sug-btn:hover { border-color:var(--accent2);color:var(--accent2);background:rgba(124,111,247,0.06); }

.msg { display:flex;gap:10px;align-items:flex-start;max-width:85%; }
.msg-user { align-self:flex-end;flex-direction:row-reverse; }
.msg-assistant,.msg-error { align-self:flex-start; }
.msg-avatar { font-size:18px;flex-shrink:0;width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:var(--bg-raised);border-radius:50%;border:1px solid var(--border); }
.msg-body { display:flex;flex-direction:column;gap:4px; }
.msg-sender { font-size:10px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px; }
.msg-user .msg-sender { text-align:right; }
.msg-text { font-size:13.5px;color:var(--text-secondary);line-height:1.7;background:var(--bg-raised);border:1px solid var(--border);border-radius:12px;padding:10px 14px; }
.msg-user .msg-text { background:rgba(124,111,247,0.1);border-color:rgba(124,111,247,0.2);color:var(--text-primary); }
.msg-error .msg-text { background:rgba(255,90,90,0.08);border-color:rgba(255,90,90,0.2); }

/* Markdown in responses */
.md-body :deep(strong) { color:var(--text-primary); }
.md-body :deep(em) { color:var(--accent);font-style:normal; }
.md-body :deep(blockquote) { border-left:2px solid var(--accent2);padding-left:10px;margin:8px 0;color:var(--text-muted);font-style:italic; }
.md-body :deep(ul) { padding-left:18px;margin:6px 0; }
.md-body :deep(li) { margin-bottom:4px; }

/* ─── Typing indicator ────────────────────────────────── */
.typing { display:flex;gap:4px;padding:10px 14px;background:var(--bg-raised);border:1px solid var(--border);border-radius:12px; }
.typing span { width:7px;height:7px;background:var(--text-muted);border-radius:50%;animation:bounce .6s infinite alternate; }
.typing span:nth-child(2) { animation-delay:.2s; }
.typing span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { to { transform:translateY(-6px);opacity:.3; } }

/* ─── Input ───────────────────────────────────────────── */
.chat-input { display:flex;gap:8px;padding:12px 20px;border-top:1px solid var(--border);background:var(--bg-raised); }
.chat-input input { flex:1;background:var(--bg-overlay);border:1px solid var(--border-md);color:var(--text-primary);padding:10px 14px;border-radius:10px;font-size:13px;outline:none;transition:border-color .15s; }
.chat-input input:focus { border-color:var(--accent2); }
.chat-input input:disabled { opacity:.5; }
.send-btn { background:var(--accent2);color:#fff;border:none;border-radius:10px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:opacity .15s;flex-shrink:0; }
.send-btn:hover { opacity:.85; }
.send-btn:disabled { opacity:.3;cursor:not-allowed; }

.chat-footer { text-align:center;font-size:11px;color:var(--text-muted);padding:8px;opacity:.6; }

/* ─── Responsive ──────────────────────────────────────── */
@media (max-width:680px) {
  .msg { max-width:95%; }
  .chat-header { padding:12px 14px; }
  .chat-input { padding:10px 14px; }
}
</style>
