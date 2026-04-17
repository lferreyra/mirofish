<template>
  <div class="chat-layout">

    <!-- Left: agent list -->
    <div class="chat-agents-panel">
      <div class="chat-agents-title">RELATIONAL AGENTS</div>
      <div
        v-for="agent in chatAgents"
        :key="agent.agent_id"
        class="chat-agent-item"
        :class="{ 'is-selected': selectedAgentId === agent.agent_id }"
        @click="selectedAgentId = agent.agent_id"
      >
        <div class="agent-avatar">{{ initials(agent.entity_name) }}</div>
        <div class="agent-info">
          <div class="agent-name">{{ agent.entity_name }}</div>
          <div class="agent-type">{{ agent.relational_link_type }}</div>
        </div>
        <div class="agent-stance-dot" :class="'stance-' + agent.stance"></div>
      </div>
      <div v-if="chatAgents.length === 0" class="chat-agents-empty">Loading agents…</div>
    </div>

    <!-- Right: chat -->
    <div class="chat-main">
      <div class="chat-messages" ref="chatMessagesEl">
        <div v-if="!selectedAgentId" class="chat-placeholder">
          Select an agent on the left to start a conversation.
        </div>
        <template v-else>
          <div
            v-for="(msg, idx) in currentMessages"
            :key="idx"
            class="chat-msg"
            :class="msg.role === 'user' ? 'chat-msg--user' : 'chat-msg--agent'"
          >
            <div class="chat-msg-label">{{ msg.role === 'user' ? 'You' : selectedAgentName }}</div>
            <div class="chat-msg-text">{{ msg.content }}</div>
          </div>
          <div v-if="isChatLoading" class="chat-msg chat-msg--agent">
            <div class="chat-msg-label">{{ selectedAgentName }}</div>
            <div class="chat-msg-text chat-thinking">
              <span></span><span></span><span></span>
            </div>
          </div>
        </template>
      </div>

      <div class="chat-input-row" v-if="selectedAgentId">
        <textarea
          class="chat-input"
          v-model="chatInput"
          placeholder="Ask this agent a question…"
          rows="2"
          @keydown.enter.exact.prevent="sendChat"
        ></textarea>
        <button class="chat-send-btn" :disabled="!chatInput.trim() || isChatLoading" @click="sendChat">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { interviewAgents } from '../../api/simulation.js'
import { initials } from '../../utils/private.js'

const props = defineProps({
  simId: { type: String, required: true },
  chatAgents: { type: Array, required: true },
})

const selectedAgentId = ref(null)
const chatMessages = reactive({})
const chatInput = ref('')
const isChatLoading = ref(false)
const chatMessagesEl = ref(null)

const selectedAgentName = computed(() => {
  const agent = props.chatAgents.find(a => a.agent_id === selectedAgentId.value)
  return agent?.entity_name || `Agent ${selectedAgentId.value}`
})

const currentMessages = computed(() => {
  return chatMessages[selectedAgentId.value] || []
})

const scrollChat = () => {
  if (chatMessagesEl.value) {
    chatMessagesEl.value.scrollTop = chatMessagesEl.value.scrollHeight
  }
}

const sendChat = async () => {
  if (!chatInput.value.trim() || !selectedAgentId.value || isChatLoading.value) return

  const userMsg = chatInput.value.trim()
  chatInput.value = ''

  if (!chatMessages[selectedAgentId.value]) chatMessages[selectedAgentId.value] = []
  chatMessages[selectedAgentId.value].push({ role: 'user', content: userMsg })

  await nextTick()
  scrollChat()

  isChatLoading.value = true
  try {
    const history = chatMessages[selectedAgentId.value]
      .slice(0, -1)
      .map(m => ({ role: m.role, content: m.content }))

    const historyContext = history
      .map(m => `${m.role === 'user' ? 'User' : 'You'}: ${m.content}`)
      .join('\n')
    const prompt = historyContext
      ? `Previous conversation:\n${historyContext}\n\nNew question: ${userMsg}`
      : userMsg

    const res = await interviewAgents({
      simulation_id: props.simId,
      interviews: [{
        agent_id: selectedAgentId.value,
        prompt,
      }],
    })

    let reply = '(no response)'
    if (res.success && res.data) {
      const resultData = res.data.result || res.data
      const resultsDict = resultData.results || resultData
      const first = Object.values(resultsDict || {}).find(v => v && v.response)
      if (first?.response) reply = first.response
    }
    chatMessages[selectedAgentId.value].push({ role: 'agent', content: reply })
  } catch (e) {
    chatMessages[selectedAgentId.value].push({ role: 'agent', content: `Error: ${e.message}` })
  } finally {
    isChatLoading.value = false
    await nextTick()
    scrollChat()
  }
}
</script>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
  height: calc(100vh - 172px);
}

.chat-agents-panel { border: 1.5px solid #EFEFEF; border-radius: 4px; overflow-y: auto; }
.chat-agents-title { padding: 10px 14px; font-size: 9px; font-weight: 700; letter-spacing: 0.14em; color: #AAA; border-bottom: 1px solid #F0F0F0; background: #FAFAFA; }

.chat-agent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #F5F5F5;
  cursor: pointer;
  transition: background 0.12s;
}

.chat-agent-item:hover { background: #F9F9F9; }
.chat-agent-item.is-selected { background: #F2F2F2; }

.agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #000;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.agent-info { flex: 1; min-width: 0; }
.agent-name { font-size: 12px; font-weight: 600; color: #000; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-type { font-size: 10px; color: #999; text-transform: capitalize; }

.agent-stance-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stance-supportive { background: #4CAF50; }
.stance-opposing { background: #F44336; }
.stance-neutral { background: #9E9E9E; }
.stance-observer { background: #2196F3; }

.chat-agents-empty { padding: 20px 14px; font-size: 11px; color: #CCC; }

.chat-main { border: 1.5px solid #EFEFEF; border-radius: 4px; display: flex; flex-direction: column; }

.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }

.chat-placeholder { font-size: 13px; color: #CCC; text-align: center; margin: auto; }

.chat-msg { display: flex; flex-direction: column; gap: 4px; max-width: 70%; }
.chat-msg--user { align-self: flex-end; }
.chat-msg--agent { align-self: flex-start; }

.chat-msg-label { font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: #AAA; }

.chat-msg-text {
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
}

.chat-msg--user .chat-msg-text { background: #000; color: #fff; border-radius: 4px 4px 2px 4px; }
.chat-msg--agent .chat-msg-text { background: #F5F5F5; color: #000; border-radius: 4px 4px 4px 2px; }

.chat-thinking {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 12px 14px;
}

.chat-thinking span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #999;
  animation: bounce 1s infinite;
}

.chat-thinking span:nth-child(2) { animation-delay: 0.2s; }
.chat-thinking span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); opacity: 0.5; }
  50% { transform: translateY(-4px); opacity: 1; }
}

.chat-input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #EFEFEF;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  resize: none;
  line-height: 1.4;
  transition: border-color 0.15s;
}

.chat-input:focus { outline: none; border-color: #000; }

.chat-send-btn {
  padding: 10px 14px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.chat-send-btn:hover { background: #222; }
.chat-send-btn:disabled { background: #CCC; cursor: not-allowed; }
</style>
