<template>
  <div class="preview-wrap">
    <!-- Header -->
    <div class="preview-header">
      <div>
        <h2 class="preview-title">Agentes da Simulacao</h2>
        <p class="preview-sub">{{ agents.length }} agentes prontos. Revise, remova ou adicione antes de iniciar.</p>
      </div>
      <div class="preview-balance">
        <span v-for="g in groupCounts" :key="g.tipo" class="balance-tag" :style="{background: g.color + '12', color: g.color, borderColor: g.color + '33'}">
          {{ g.icon }} {{ g.count }} {{ g.tipo }}
        </span>
      </div>
    </div>

    <!-- Warning if unbalanced -->
    <div v-if="isUnbalanced" class="preview-warn">
      ⚠️ Distribuicao desequilibrada: {{ unbalanceReason }}. Considere equilibrar para resultados mais realistas.
    </div>

    <!-- Agent Cards Grid -->
    <div class="agents-grid">
      <div v-for="(agent, idx) in agents" :key="agent.id || idx" 
           class="agent-card" :class="{'agent-removing': agent._removing}"
           :style="{'border-left': '4px solid ' + typeColor(agent.tipo || agent.source_entity_type)}">
        
        <!-- Card Header -->
        <div class="ac-header">
          <div class="ac-avatar" :style="{background: typeColor(agent.tipo || agent.source_entity_type) + '15', color: typeColor(agent.tipo || agent.source_entity_type)}">
            {{ (agent.name || agent.username || '?')[0].toUpperCase() }}
          </div>
          <div class="ac-info">
            <div class="ac-name">{{ agent.name || agent.username }}</div>
            <div class="ac-meta">
              <span v-if="agent.age">{{ agent.age }} anos</span>
              <span v-if="agent.profession"> · {{ agent.profession }}</span>
            </div>
          </div>
          <button class="ac-remove" @click="removeAgent(idx)" title="Remover agente">✕</button>
        </div>

        <!-- Card Body -->
        <div class="ac-body">
          <p class="ac-bio">{{ truncate(agent.bio || agent.persona || '', 120) }}</p>
        </div>

        <!-- Card Footer -->
        <div class="ac-footer">
          <span class="ac-type-tag" :style="{background: typeColor(agent.tipo || agent.source_entity_type) + '12', color: typeColor(agent.tipo || agent.source_entity_type)}">
            {{ translateType(agent.source_entity_type || agent.tipo || 'Agente') }}
          </span>
          <span v-if="agent.mbti" class="ac-mbti">{{ agent.mbti }}</span>
          <span v-if="agent._custom" class="ac-custom-tag">personalizado</span>
        </div>
      </div>

      <!-- Add Agent Card -->
      <div class="agent-card add-card" @click="showAddModal = true">
        <div class="add-icon">+</div>
        <div class="add-text">Adicionar Agente</div>
        <div class="add-sub">Descreva uma persona que faltou</div>
      </div>
    </div>

    <!-- Add Modal -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal-box">
        <h3>Adicionar Agente Personalizado</h3>
        <p class="modal-hint">Descreva quem e essa pessoa. O AUGUR vai gerar o perfil completo.</p>
        <textarea v-model="customDesc" class="modal-input" rows="3"
          placeholder="Ex: Marcia, 35 anos, compra tenis pela Netshoes, nunca entra em loja fisica, sensivel a frete gratis"></textarea>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showAddModal = false">Cancelar</button>
          <button class="btn-primary" @click="addCustomAgent" :disabled="!customDesc.trim() || addingAgent">
            {{ addingAgent ? 'Gerando perfil...' : 'Adicionar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Regeneration notice -->
    <div v-if="removedCount > 0 && !regenerating" class="regen-bar">
      <span>{{ removedCount }} agente(s) removido(s).</span>
      <button class="btn-regen" @click="$emit('regenerate', removedCount)">
        🔄 Regerar {{ removedCount }} para completar {{ targetCount }}
      </button>
      <span class="regen-or">ou continue com {{ agents.length }} agentes</span>
    </div>
    <div v-if="regenerating" class="regen-bar">
      <span class="regen-loading">⏳ Gerando {{ removedCount }} agentes substitutos...</span>
    </div>

    <!-- Action Bar -->
    <div class="preview-actions">
      <button class="btn-ghost" @click="$emit('back')">← Voltar</button>
      <div class="actions-right">
        <span class="agents-count">{{ agents.length }} agentes</span>
        <button class="btn-iniciar" @click="$emit('confirm', agents)">
          ✦ Confirmar e Iniciar Simulacao
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  agents: { type: Array, default: () => [] },
  targetCount: { type: Number, default: 20 },
  regenerating: { type: Boolean, default: false },
})

const emit = defineEmits(['remove', 'add', 'confirm', 'back', 'regenerate'])

const showAddModal = ref(false)
const customDesc = ref('')
const addingAgent = ref(false)
const removedCount = ref(0)

const TYPE_COLORS = {
  'Apoiador': '#00e5c3', 'Neutro': '#f5a623', 'Resistente': '#ff5a5a', 'Cauteloso': '#7c6ff7',
  'Consumer': '#00e5c3', 'LocalBusiness': '#f5a623', 'Competitor': '#ff5a5a',
  'Influencer': '#7c6ff7', 'GovernmentAgency': '#1da1f2', 'Person': '#8888aa',
  'Organization': '#8888aa', 'default': '#8888aa'
}

const TRANSLATE = {
  'Consumer':'Consumidor','LocalBusiness':'Negocio Local','Influencer':'Influenciador',
  'Competitor':'Concorrente','GovernmentAgency':'Governo','Person':'Pessoa',
  'Organization':'Organizacao','RetailChain':'Rede Varejo','EcommercePlatform':'E-commerce',
  'LocalInfluencer':'Influenciador Local','Supplier':'Fornecedor','Regulator':'Regulador',
}

function typeColor(type) {
  return TYPE_COLORS[type] || TYPE_COLORS['default']
}

function translateType(type) {
  return TRANSLATE[type] || type?.replace(/([A-Z])/g, ' $1').trim() || 'Agente'
}

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function removeAgent(idx) {
  const agent = props.agents[idx]
  agent._removing = true
  setTimeout(() => {
    emit('remove', idx)
    removedCount.value++
  }, 300)
}

async function addCustomAgent() {
  if (!customDesc.value.trim()) return
  addingAgent.value = true
  emit('add', customDesc.value.trim())
  customDesc.value = ''
  addingAgent.value = false
  showAddModal.value = false
}

const groupCounts = computed(() => {
  const counts = {}
  props.agents.forEach(a => {
    const tipo = a.tipo || a.source_entity_type || 'Outro'
    counts[tipo] = (counts[tipo] || 0) + 1
  })
  return Object.entries(counts).map(([tipo, count]) => ({
    tipo: TRANSLATE[tipo] || tipo,
    count,
    color: TYPE_COLORS[tipo] || '#8888aa',
    icon: tipo === 'Apoiador' ? '👍' : tipo === 'Resistente' ? '👎' : tipo === 'Neutro' ? '🤷' : '👤'
  }))
})

const isUnbalanced = computed(() => {
  if (props.agents.length < 5) return false
  const apoiadores = props.agents.filter(a => (a.tipo || '').includes('Apoiador')).length
  const total = props.agents.length
  return apoiadores / total > 0.7 || apoiadores / total < 0.15
})

const unbalanceReason = computed(() => {
  const apoiadores = props.agents.filter(a => (a.tipo || '').includes('Apoiador')).length
  const total = props.agents.length
  if (apoiadores / total > 0.7) return `${apoiadores} de ${total} sao apoiadores — poucos ceticos`
  if (apoiadores / total < 0.15) return `apenas ${apoiadores} apoiadores — simulacao muito pessimista`
  return ''
})
</script>

<style scoped>
.preview-wrap { max-width:1100px; margin:0 auto; }

.preview-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; flex-wrap:wrap; gap:12px; }
.preview-title { font-size:22px; font-weight:800; color:var(--text-primary, #1a1a2e); margin:0; }
.preview-sub { font-size:13px; color:var(--text-muted, #8888aa); margin-top:4px; }
.preview-balance { display:flex; gap:8px; flex-wrap:wrap; }
.balance-tag { font-size:11px; font-weight:700; padding:4px 10px; border-radius:20px; border:1px solid; }

.preview-warn { padding:10px 16px; background:rgba(245,166,35,0.08); border:1px solid rgba(245,166,35,0.25); border-radius:10px; font-size:12px; color:#b8860b; margin-bottom:16px; }

/* Grid */
.agents-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:12px; margin-bottom:20px; }

/* Agent Card */
.agent-card { background:var(--bg-surface, #fff); border:1px solid var(--border, #eeeef2); border-radius:14px; padding:16px; display:flex; flex-direction:column; gap:10px; transition:all .3s ease; }
.agent-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.06); }
.agent-removing { opacity:0; transform:scale(0.9); }

.ac-header { display:flex; gap:10px; align-items:center; }
.ac-avatar { width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:800; flex-shrink:0; }
.ac-info { flex:1; min-width:0; }
.ac-name { font-size:14px; font-weight:700; color:var(--text-primary, #1a1a2e); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ac-meta { font-size:11px; color:var(--text-muted, #8888aa); }
.ac-remove { width:24px; height:24px; border-radius:6px; border:none; background:transparent; color:var(--text-muted, #8888aa); cursor:pointer; font-size:12px; display:flex; align-items:center; justify-content:center; transition:all .2s; }
.ac-remove:hover { background:rgba(255,90,90,0.1); color:#ff5a5a; }

.ac-body { flex:1; }
.ac-bio { font-size:12px; color:var(--text-secondary, #444466); line-height:1.5; margin:0; }

.ac-footer { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.ac-type-tag { font-size:10px; font-weight:700; padding:2px 8px; border-radius:12px; }
.ac-mbti { font-size:10px; font-weight:600; color:var(--text-muted, #8888aa); padding:2px 6px; background:var(--bg-raised, #fafafe); border-radius:8px; }
.ac-custom-tag { font-size:9px; font-weight:700; color:#7c6ff7; background:rgba(124,111,247,0.1); padding:2px 8px; border-radius:12px; }

/* Add Card */
.add-card { border:2px dashed var(--border-md, #dddde5); background:transparent; cursor:pointer; align-items:center; justify-content:center; text-align:center; min-height:140px; transition:all .2s; }
.add-card:hover { border-color:var(--accent, #00e5c3); background:rgba(0,229,195,0.03); }
.add-icon { font-size:28px; font-weight:300; color:var(--text-muted, #8888aa); }
.add-text { font-size:13px; font-weight:700; color:var(--text-primary, #1a1a2e); }
.add-sub { font-size:11px; color:var(--text-muted, #8888aa); }

/* Modal */
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.4); display:flex; align-items:center; justify-content:center; z-index:999; }
.modal-box { background:var(--bg-surface, #fff); border-radius:16px; padding:28px; width:90%; max-width:480px; box-shadow:0 20px 60px rgba(0,0,0,0.15); }
.modal-box h3 { font-size:18px; font-weight:800; color:var(--text-primary, #1a1a2e); margin:0 0 6px; }
.modal-hint { font-size:12px; color:var(--text-muted, #8888aa); margin-bottom:14px; }
.modal-input { width:100%; padding:12px; border:1px solid var(--border, #eeeef2); border-radius:10px; font-size:13px; font-family:inherit; resize:vertical; }
.modal-input:focus { outline:none; border-color:var(--accent, #00e5c3); }
.modal-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:14px; }

/* Regen Bar */
.regen-bar { padding:12px 16px; background:rgba(124,111,247,0.06); border:1px solid rgba(124,111,247,0.2); border-radius:10px; font-size:12px; color:var(--text-secondary, #444466); margin-bottom:16px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.btn-regen { background:var(--accent2, #7c6ff7); color:white; border:none; padding:5px 14px; border-radius:8px; font-size:11px; font-weight:700; cursor:pointer; }
.regen-or { color:var(--text-muted, #8888aa); font-size:11px; }
.regen-loading { color:var(--accent2, #7c6ff7); font-weight:600; }

/* Action Bar */
.preview-actions { display:flex; justify-content:space-between; align-items:center; padding-top:16px; border-top:1px solid var(--border, #eeeef2); }
.actions-right { display:flex; align-items:center; gap:14px; }
.agents-count { font-size:12px; font-weight:700; color:var(--text-muted, #8888aa); }

/* Buttons */
.btn-ghost { background:transparent; border:1px solid var(--border, #eeeef2); color:var(--text-secondary, #444466); padding:8px 18px; border-radius:10px; font-size:13px; font-weight:600; cursor:pointer; }
.btn-ghost:hover { border-color:var(--text-muted, #8888aa); }
.btn-primary { background:var(--accent, #00e5c3); color:white; border:none; padding:8px 18px; border-radius:10px; font-size:13px; font-weight:700; cursor:pointer; }
.btn-primary:disabled { opacity:0.5; cursor:not-allowed; }
.btn-iniciar { background:linear-gradient(135deg, #00e5c3, #7c6ff7); color:white; border:none; padding:12px 28px; border-radius:12px; font-size:14px; font-weight:800; cursor:pointer; transition:transform .2s; }
.btn-iniciar:hover { transform:translateY(-1px); box-shadow:0 4px 16px rgba(0,229,195,0.3); }

@media (max-width:768px) { .agents-grid { grid-template-columns:1fr 1fr; } .preview-header { flex-direction:column; } }
@media (max-width:480px) { .agents-grid { grid-template-columns:1fr; } }
</style>
