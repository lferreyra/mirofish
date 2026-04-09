<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import AugurButton from '../components/ui/AugurButton.vue'

const router = useRouter()

// ═══ STATE ════════════════════════════════════════════════════
const categories = ref([])
const search = ref('')
const activeCategory = ref(null)
const editingAgent = ref(null)
const showNewAgent = ref(false)
const showNewCategory = ref(false)

const newAgent = ref({ name: '', desc: '', tags: '' })
const newCategory = ref({ icon: '🏷', label: '', color: '#00e5c3' })

// ═══ DEFAULT LIBRARY ══════════════════════════════════════════
const DEFAULT_LIBRARY = [
  { id: 'consumidores', icon: '🛒', label: 'Consumidores', color: '#00e5c3', agents: [
    { id: 'c1', name: 'Jovem Urbano (18-25)', desc: 'Digital native, compra por impulso, influenciado por redes sociais. Usa Instagram e TikTok para descobrir produtos.', tags: 'varejo,tech,moda' },
    { id: 'c2', name: 'Mãe com Filhos', desc: 'Prioriza qualidade e segurança, sensível a preço, busca praticidade. Pesquisa antes de comprar, confia em recomendações.', tags: 'varejo,alimentação,saúde' },
    { id: 'c3', name: 'Idoso Tradicional (60+)', desc: 'Fiel a marcas conhecidas, prefere atendimento presencial e humano. Resistente a mudanças, valoriza tradição.', tags: 'varejo,saúde,financeiro' },
    { id: 'c4', name: 'Profissional Classe A', desc: 'Alto poder aquisitivo, valoriza exclusividade, experiência premium e conveniência. Disposto a pagar mais por qualidade.', tags: 'luxo,tech,serviços' },
    { id: 'c5', name: 'Consumidor Classe C', desc: 'Sensível a preço, busca parcelamento e promoções. Compara muito antes de comprar, valoriza custo-benefício.', tags: 'varejo,financeiro' },
    { id: 'c6', name: 'Empreendedor PME', desc: 'Busca soluções com ROI claro, decide rápido, precisa de resultado tangível. Tempo é escasso.', tags: 'b2b,tech,serviços' },
    { id: 'c7', name: 'Consumidor Digital', desc: 'Compra 100% online, compara em marketplaces (Shopee, Amazon, ML). Valoriza frete grátis e reviews.', tags: 'ecommerce,tech' },
    { id: 'c8', name: 'Consumidor Local', desc: 'Prefere comércio do bairro, valoriza relacionamento pessoal e confiança. Compra fiado, indica para vizinhos.', tags: 'varejo,alimentação' },
  ]},
  { id: 'reguladores', icon: '🏛', label: 'Reguladores & Governo', color: '#7c6ff7', agents: [
    { id: 'r1', name: 'PROCON', desc: 'Defesa do consumidor — fiscaliza propaganda enganosa, práticas abusivas, direito de troca e garantia.', tags: 'todos' },
    { id: 'r2', name: 'ANVISA', desc: 'Vigilância sanitária — regulamenta alimentos, cosméticos, medicamentos, rótulos e segurança alimentar.', tags: 'saúde,alimentação' },
    { id: 'r3', name: 'BACEN', desc: 'Banco Central — regula serviços financeiros, fintechs, PIX, meios de pagamento, câmbio.', tags: 'financeiro,fintech' },
    { id: 'r4', name: 'INMETRO', desc: 'Metrologia — certifica qualidade, segurança de produtos, padrões de medida.', tags: 'varejo,indústria' },
    { id: 'r5', name: 'IBAMA', desc: 'Meio ambiente — fiscaliza impacto ambiental, sustentabilidade, créditos de carbono.', tags: 'indústria,agro' },
    { id: 'r6', name: 'CADE', desc: 'Defesa econômica — combate monopólio, cartel, práticas anticompetitivas, fusões.', tags: 'todos' },
    { id: 'r7', name: 'ANATEL', desc: 'Telecomunicações — regula internet, telefonia móvel, banda larga, dados pessoais.', tags: 'tech,telecom' },
    { id: 'r8', name: 'CVM', desc: 'Valores mobiliários — regula investimentos, tokens, crowdfunding, IPOs.', tags: 'financeiro,crypto' },
    { id: 'r9', name: 'LGPD/ANPD', desc: 'Proteção de dados — fiscaliza coleta, uso e compartilhamento de dados pessoais.', tags: 'tech,todos' },
  ]},
  { id: 'financeiro', icon: '💰', label: 'Mercado Financeiro', color: '#f5a623', agents: [
    { id: 'f1', name: 'Banco Tradicional', desc: 'Conservador, burocrático, grande base de clientes. Crédito restritivo, taxas altas, agências físicas.', tags: 'financeiro' },
    { id: 'f2', name: 'Fintech', desc: 'Ágil, digital first, taxas baixas, experiência moderna. Nubank, PicPay, Inter como referência.', tags: 'financeiro,tech' },
    { id: 'f3', name: 'Investidor Anjo', desc: 'Busca oportunidades early-stage, avalia equipe, mercado e escalabilidade. Ticket R$50k-500k.', tags: 'startup' },
    { id: 'f4', name: 'Analista de Mercado', desc: 'Avalia riscos e oportunidades com dados. Visão macro, projeções, relatórios setoriais.', tags: 'financeiro' },
    { id: 'f5', name: 'Consultor Financeiro', desc: 'Orienta empresas sobre investimentos, fluxo de caixa, planejamento tributário.', tags: 'financeiro,serviços' },
    { id: 'f6', name: 'Operadora de Crédito', desc: 'Crediário, BNPL, parcelamento sem juros. Sensível a inadimplência e score de crédito.', tags: 'varejo,financeiro' },
  ]},
  { id: 'influenciadores', icon: '📱', label: 'Influenciadores & Mídia', color: '#e91e9c', agents: [
    { id: 'i1', name: 'Influenciador Digital Local', desc: 'Micro-influencer da cidade/região, alta credibilidade, 5k-50k seguidores. Engajamento alto.', tags: 'todos' },
    { id: 'i2', name: 'Creator de Nicho', desc: 'Especialista no tema, audiência segmentada e engajada. Review detalhado, opinião respeitada.', tags: 'todos' },
    { id: 'i3', name: 'Jornalista/Blogueiro', desc: 'Cobertura editorial, busca fatos e novidades. Pode amplificar ou destruir narrativa.', tags: 'todos' },
    { id: 'i4', name: 'Influenciador Nacional', desc: 'Grande alcance, 500k+ seguidores. Alto custo de parceria, impacto massivo porém menos segmentado.', tags: 'moda,tech,lifestyle' },
    { id: 'i5', name: 'Podcaster', desc: 'Formato longo, audiência fiel e educada. Análise profunda, storytelling.', tags: 'tech,negócios' },
    { id: 'i6', name: 'TikToker/Reels', desc: 'Conteúdo curto e viral, público jovem, tendências rápidas. Viraliza ou esquece.', tags: 'moda,varejo,alimentação' },
  ]},
  { id: 'concorrentes', icon: '🏪', label: 'Concorrentes & Mercado', color: '#ff5a5a', agents: [
    { id: 'co1', name: 'Líder de Mercado', desc: 'Marca dominante no setor, alto market share, define tendências e preços de referência.', tags: 'todos' },
    { id: 'co2', name: 'Novo Entrante', desc: 'Startup ou empresa entrando no mercado. Agressiva em preço, inovadora, queima caixa.', tags: 'todos' },
    { id: 'co3', name: 'Marketplace/E-commerce', desc: 'Shopee, Mercado Livre, Amazon — concorrência de preço, conveniência e frete grátis.', tags: 'varejo,ecommerce' },
    { id: 'co4', name: 'Concorrente Regional', desc: 'Forte na região, conhece público local, relacionamento sólido. Difícil de desbancar.', tags: 'varejo' },
    { id: 'co5', name: 'Franquia Nacional', desc: 'Marca conhecida, padronização, poder de marketing e escala. Franqueado local.', tags: 'varejo,alimentação' },
  ]},
  { id: 'industria', icon: '🏭', label: 'Indústria & Fornecedores', color: '#4caf50', agents: [
    { id: 'in1', name: 'Fabricante/Fornecedor', desc: 'Produz o que você vende. Define preço de custo, prazos, mínimo de pedido.', tags: 'varejo,indústria' },
    { id: 'in2', name: 'Distribuidor/Atacadista', desc: 'Intermedia fábrica e varejo. Logística, volume, prazo de pagamento.', tags: 'varejo' },
    { id: 'in3', name: 'Representante Comercial', desc: 'Vende para lojistas, conhece o mercado regional. Relacionamento é a moeda.', tags: 'varejo,b2b' },
    { id: 'in4', name: 'Operador Logístico', desc: 'Entrega, frete, última milha. Custo e prazo impactam diretamente na experiência.', tags: 'ecommerce,varejo' },
  ]},
  { id: 'servicos', icon: '🔧', label: 'Serviços & Tech', color: '#1da1f2', agents: [
    { id: 's1', name: 'Cliente de Delivery', desc: 'Pede por app, sensível a tempo e preço de entrega. Avalia no app, troca fácil.', tags: 'delivery,alimentação' },
    { id: 's2', name: 'Restaurante Parceiro', desc: 'Depende de plataformas, margem apertada. Busca volume e visibilidade.', tags: 'delivery,alimentação' },
    { id: 's3', name: 'Entregador', desc: 'Gig economy, sensível a taxa por entrega. Flexibilidade vs precarização.', tags: 'delivery' },
    { id: 's4', name: 'Desenvolvedor/Tech', desc: 'Avalia produto pela tecnologia, API, documentação, integração.', tags: 'tech,saas' },
    { id: 's5', name: 'Usuário SaaS B2B', desc: 'Empresa que compra software. Precisa de ROI, suporte, onboarding.', tags: 'tech,saas,b2b' },
  ]},
  { id: 'institucional', icon: '🏢', label: 'Institucional & Social', color: '#795548', agents: [
    { id: 'inst1', name: 'Associação Comercial', desc: 'Representa comércio local. Advocacy, networking, capacitação de lojistas.', tags: 'varejo' },
    { id: 'inst2', name: 'Sindicato/Classe', desc: 'Representa trabalhadores. Negocia direitos, influência política e trabalhista.', tags: 'indústria,serviços' },
    { id: 'inst3', name: 'Universidade/Pesquisador', desc: 'Análise acadêmica, dados de pesquisa, credibilidade técnica. Opinião fundamentada.', tags: 'todos' },
    { id: 'inst4', name: 'ONG/Instituto Social', desc: 'Causa social, sustentabilidade, impacto comunitário. Reputação e propósito.', tags: 'todos' },
    { id: 'inst5', name: 'Reclame Aqui', desc: 'Plataforma de reclamações — reputação online, resolução pública, nota de confiança.', tags: 'todos' },
    { id: 'inst6', name: 'SEBRAE', desc: 'Apoio a micro e pequenas empresas. Capacitação, crédito facilitado, mentoria.', tags: 'pme,varejo' },
  ]},
]

// ═══ PERSISTENCE (localStorage) ═══════════════════════════════
const STORAGE_KEY = 'augur_agent_library'

function loadLibrary() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      categories.value = JSON.parse(saved)
    } else {
      categories.value = JSON.parse(JSON.stringify(DEFAULT_LIBRARY))
    }
  } catch {
    categories.value = JSON.parse(JSON.stringify(DEFAULT_LIBRARY))
  }
}

function saveLibrary() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(categories.value))
  } catch (e) {
    console.warn('Falha ao salvar biblioteca:', e)
  }
}

function resetLibrary() {
  if (!confirm('Restaurar biblioteca para o padrão? Agentes e categorias customizadas serão removidos.')) return
  categories.value = JSON.parse(JSON.stringify(DEFAULT_LIBRARY))
  saveLibrary()
}

watch(categories, saveLibrary, { deep: true })
onMounted(loadLibrary)

// ═══ COMPUTED ═════════════════════════════════════════════════
const totalAgents = computed(() => categories.value.reduce((s, c) => s + c.agents.length, 0))

const filteredCategories = computed(() => {
  if (!search.value.trim()) return categories.value
  const q = search.value.toLowerCase()
  return categories.value.map(cat => ({
    ...cat,
    agents: cat.agents.filter(a => 
      a.name.toLowerCase().includes(q) || 
      a.desc.toLowerCase().includes(q) || 
      (a.tags || '').toLowerCase().includes(q)
    )
  })).filter(cat => cat.agents.length > 0 || cat.label.toLowerCase().includes(q))
})

// ═══ ACTIONS ══════════════════════════════════════════════════
function toggleCategory(id) {
  activeCategory.value = activeCategory.value === id ? null : id
}

function createCategory() {
  const label = newCategory.value.label.trim()
  if (!label) return
  const id = 'custom_' + Date.now()
  categories.value.push({
    id,
    icon: newCategory.value.icon || '🏷',
    label,
    color: newCategory.value.color || '#00e5c3',
    agents: [],
    custom: true
  })
  newCategory.value = { icon: '🏷', label: '', color: '#00e5c3' }
  showNewCategory.value = false
  activeCategory.value = id
}

function deleteCategory(catId) {
  const cat = categories.value.find(c => c.id === catId)
  if (!cat) return
  if (!confirm(`Remover categoria "${cat.label}" e todos os agentes?`)) return
  categories.value = categories.value.filter(c => c.id !== catId)
}

function createAgent(catId) {
  const cat = categories.value.find(c => c.id === catId)
  if (!cat) return
  const name = newAgent.value.name.trim()
  if (!name) return
  cat.agents.push({
    id: 'ag_' + Date.now(),
    name,
    desc: newAgent.value.desc.trim() || 'Sem descrição',
    tags: newAgent.value.tags.trim(),
    custom: true
  })
  newAgent.value = { name: '', desc: '', tags: '' }
  showNewAgent.value = false
}

function deleteAgent(catId, agentId) {
  const cat = categories.value.find(c => c.id === catId)
  if (!cat) return
  cat.agents = cat.agents.filter(a => a.id !== agentId)
}

function startEditAgent(agent) {
  editingAgent.value = { ...agent }
}

function saveEditAgent(catId) {
  if (!editingAgent.value) return
  const cat = categories.value.find(c => c.id === catId)
  if (!cat) return
  const idx = cat.agents.findIndex(a => a.id === editingAgent.value.id)
  if (idx >= 0) {
    cat.agents[idx] = { ...editingAgent.value }
  }
  editingAgent.value = null
}
</script>

<template>
  <AppShell>
    <div class="alib">
      <!-- Header -->
      <div class="alib-header">
        <div>
          <h1>🎭 Biblioteca de Agentes</h1>
          <p class="alib-sub">{{ totalAgents }} agentes em {{ categories.length }} categorias · Gerencie as personas que participam das simulações</p>
        </div>
        <div class="alib-actions">
          <button class="alib-btn alib-btn-sec" @click="resetLibrary">↺ Restaurar Padrão</button>
          <button class="alib-btn alib-btn-pri" @click="showNewCategory = !showNewCategory">+ Nova Categoria</button>
        </div>
      </div>

      <!-- New Category Form -->
      <div v-if="showNewCategory" class="alib-form-card">
        <h3>Criar Nova Categoria</h3>
        <div class="alib-form-row">
          <input v-model="newCategory.icon" class="alib-icon-input" maxlength="2" placeholder="🏷"/>
          <input v-model="newCategory.label" class="alib-input" placeholder="Nome da categoria" @keyup.enter="createCategory"/>
          <input v-model="newCategory.color" type="color" class="alib-color-input"/>
          <button class="alib-btn alib-btn-pri" @click="createCategory">Criar</button>
          <button class="alib-btn alib-btn-ghost" @click="showNewCategory = false">Cancelar</button>
        </div>
      </div>

      <!-- Search -->
      <div class="alib-search">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <circle cx="7" cy="7" r="5"/><line x1="11" y1="11" x2="15" y2="15"/>
        </svg>
        <input v-model="search" placeholder="Buscar agentes por nome, descrição ou tag..." />
      </div>

      <!-- Categories -->
      <div class="alib-cats">
        <div v-for="cat in filteredCategories" :key="cat.id" class="alib-cat">
          <!-- Category Header -->
          <div class="alib-cat-head" @click="toggleCategory(cat.id)">
            <span class="alib-cat-icon" :style="{background: cat.color + '15', color: cat.color}">{{ cat.icon }}</span>
            <div class="alib-cat-info">
              <h3>{{ cat.label }}</h3>
              <span class="alib-cat-count">{{ cat.agents.length }} agentes</span>
            </div>
            <div class="alib-cat-tags">
              <span v-for="a in cat.agents.slice(0, 3)" :key="a.id" class="alib-mini-tag">{{ a.name.split(' ')[0] }}</span>
              <span v-if="cat.agents.length > 3" class="alib-mini-tag alib-mini-more">+{{ cat.agents.length - 3 }}</span>
            </div>
            <button v-if="cat.custom" class="alib-cat-del" @click.stop="deleteCategory(cat.id)" title="Remover categoria">✕</button>
            <span class="alib-cat-arrow" :class="{'open': activeCategory === cat.id}">›</span>
          </div>

          <!-- Expanded Agent List -->
          <div v-if="activeCategory === cat.id" class="alib-agents">
            <div v-for="agent in cat.agents" :key="agent.id" class="alib-agent">
              <!-- View mode -->
              <template v-if="editingAgent?.id !== agent.id">
                <div class="alib-agent-dot" :style="{background: cat.color}"></div>
                <div class="alib-agent-body">
                  <div class="alib-agent-name">{{ agent.name }}</div>
                  <div class="alib-agent-desc">{{ agent.desc }}</div>
                  <div class="alib-agent-tags" v-if="agent.tags">
                    <span v-for="t in agent.tags.split(',')" :key="t" class="alib-tag">{{ t.trim() }}</span>
                  </div>
                </div>
                <div class="alib-agent-actions">
                  <button @click="startEditAgent(agent)" title="Editar">✏️</button>
                  <button @click="deleteAgent(cat.id, agent.id)" title="Remover">🗑</button>
                </div>
              </template>
              <!-- Edit mode -->
              <template v-else>
                <div class="alib-edit-form">
                  <input v-model="editingAgent.name" class="alib-input" placeholder="Nome"/>
                  <textarea v-model="editingAgent.desc" class="alib-textarea" placeholder="Descrição" rows="2"></textarea>
                  <input v-model="editingAgent.tags" class="alib-input alib-input-sm" placeholder="Tags (separadas por vírgula)"/>
                  <div class="alib-edit-btns">
                    <button class="alib-btn alib-btn-pri alib-btn-sm" @click="saveEditAgent(cat.id)">Salvar</button>
                    <button class="alib-btn alib-btn-ghost alib-btn-sm" @click="editingAgent = null">Cancelar</button>
                  </div>
                </div>
              </template>
            </div>

            <!-- Add agent to this category -->
            <div class="alib-add-agent">
              <div v-if="showNewAgent === cat.id" class="alib-add-form">
                <input v-model="newAgent.name" class="alib-input" placeholder="Nome do agente" @keyup.enter="createAgent(cat.id)"/>
                <textarea v-model="newAgent.desc" class="alib-textarea" placeholder="Descrição do perfil, comportamento, motivações..." rows="2"></textarea>
                <input v-model="newAgent.tags" class="alib-input alib-input-sm" placeholder="Tags: varejo, tech, alimentação..."/>
                <div class="alib-add-btns">
                  <button class="alib-btn alib-btn-pri alib-btn-sm" @click="createAgent(cat.id)">Adicionar Agente</button>
                  <button class="alib-btn alib-btn-ghost alib-btn-sm" @click="showNewAgent = false">Cancelar</button>
                </div>
              </div>
              <button v-else class="alib-add-trigger" @click="showNewAgent = cat.id">
                + Adicionar agente em {{ cat.label }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.alib { max-width:960px; margin:0 auto; padding:0 16px 60px; }
.alib-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px; flex-wrap:wrap; gap:16px; }
.alib-header h1 { font-size:22px; font-weight:700; color:var(--text-primary, #f0f0ff); }
.alib-sub { font-size:13px; color:var(--text-secondary, #8888aa); margin-top:4px; }
.alib-actions { display:flex; gap:8px; }

.alib-btn { padding:8px 18px; border-radius:10px; font-size:13px; font-weight:600; cursor:pointer; border:none; transition:all .15s; }
.alib-btn-pri { background:#00e5c3; color:#09090f; }
.alib-btn-pri:hover { transform:translateY(-1px); }
.alib-btn-sec { background:rgba(255,255,255,0.05); color:#8888aa; border:1px solid rgba(255,255,255,0.1); }
.alib-btn-ghost { background:transparent; color:#8888aa; }
.alib-btn-sm { padding:6px 14px; font-size:12px; }

.alib-form-card { background:var(--bg-surface, #111118); border:1px solid rgba(0,229,195,0.2); border-radius:14px; padding:20px; margin-bottom:20px; }
.alib-form-card h3 { font-size:15px; font-weight:600; color:#f0f0ff; margin-bottom:12px; }
.alib-form-row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.alib-icon-input { width:44px; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); color:#f0f0ff; font-size:18px; text-align:center; }
.alib-input { flex:1; min-width:150px; padding:8px 14px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); color:#f0f0ff; font-size:13px; outline:none; }
.alib-input:focus { border-color:rgba(0,229,195,0.4); }
.alib-input-sm { font-size:12px; padding:6px 12px; }
.alib-textarea { width:100%; padding:8px 14px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.04); color:#f0f0ff; font-size:12px; outline:none; resize:vertical; font-family:inherit; }
.alib-color-input { width:36px; height:36px; border:none; border-radius:8px; cursor:pointer; }

.alib-search { display:flex; align-items:center; gap:10px; padding:10px 16px; background:var(--bg-surface, #111118); border:1px solid rgba(255,255,255,0.08); border-radius:12px; margin-bottom:20px; color:#555570; }
.alib-search input { flex:1; background:none; border:none; color:#f0f0ff; font-size:13px; outline:none; }

.alib-cats { display:flex; flex-direction:column; gap:6px; }
.alib-cat { background:var(--bg-surface, #111118); border:1px solid rgba(255,255,255,0.06); border-radius:14px; overflow:hidden; }
.alib-cat-head { display:flex; align-items:center; gap:12px; padding:14px 18px; cursor:pointer; transition:background .15s; }
.alib-cat-head:hover { background:rgba(255,255,255,0.02); }
.alib-cat-icon { width:38px; height:38px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.alib-cat-info { flex:1; min-width:0; }
.alib-cat-info h3 { font-size:14px; font-weight:700; color:#f0f0ff; }
.alib-cat-count { font-size:11px; color:#555570; }
.alib-cat-tags { display:flex; gap:4px; flex-shrink:0; }
.alib-mini-tag { font-size:10px; padding:2px 8px; border-radius:10px; background:rgba(255,255,255,0.04); color:#8888aa; white-space:nowrap; }
.alib-mini-more { background:rgba(0,229,195,0.08); color:#00e5c3; }
.alib-cat-del { background:none; border:none; color:#ff5a5a; font-size:14px; cursor:pointer; opacity:0.5; padding:4px; }
.alib-cat-del:hover { opacity:1; }
.alib-cat-arrow { font-size:20px; color:#555570; transition:transform .2s; font-weight:700; }
.alib-cat-arrow.open { transform:rotate(90deg); }

.alib-agents { padding:0 18px 14px; border-top:1px solid rgba(255,255,255,0.04); }
.alib-agent { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid rgba(255,255,255,0.03); align-items:flex-start; }
.alib-agent-dot { width:8px; height:8px; border-radius:50%; margin-top:7px; flex-shrink:0; }
.alib-agent-body { flex:1; min-width:0; }
.alib-agent-name { font-size:14px; font-weight:600; color:#f0f0ff; }
.alib-agent-desc { font-size:12px; color:#8888aa; line-height:1.5; margin-top:3px; }
.alib-agent-tags { display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }
.alib-tag { font-size:10px; padding:2px 8px; border-radius:8px; background:rgba(124,111,247,0.08); color:#7c6ff7; }
.alib-agent-actions { display:flex; gap:2px; flex-shrink:0; }
.alib-agent-actions button { background:none; border:none; font-size:13px; cursor:pointer; padding:4px; opacity:0.4; transition:opacity .15s; }
.alib-agent-actions button:hover { opacity:1; }

.alib-edit-form { display:flex; flex-direction:column; gap:8px; width:100%; padding:8px 0; }
.alib-edit-btns { display:flex; gap:6px; }

.alib-add-agent { padding:10px 0 4px; }
.alib-add-trigger { background:none; border:1px dashed rgba(0,229,195,0.2); color:#00e5c3; font-size:13px; font-weight:600; padding:10px; width:100%; border-radius:10px; cursor:pointer; transition:all .15s; }
.alib-add-trigger:hover { background:rgba(0,229,195,0.04); border-color:rgba(0,229,195,0.4); }
.alib-add-form { display:flex; flex-direction:column; gap:8px; }
.alib-add-btns { display:flex; gap:6px; }

@media (max-width:768px) { .alib-header { flex-direction:column; } .alib-cat-tags { display:none; } }
</style>
