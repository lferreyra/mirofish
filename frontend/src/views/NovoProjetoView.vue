<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const router = useRouter()

// ─── Wizard ───────────────────────────────────────────────────
const etapa    = ref(1) // 1=Projeto, 2=Simulação, 3=Materiais, 4=Parâmetros
const loading  = ref(false)
const erro     = ref('')

// ─── Etapa 1: Projeto ─────────────────────────────────────────
const pNome    = ref('')
const pCliente = ref('')

// ─── Etapa 2: Simulação ───────────────────────────────────────
const sTitulo   = ref('')
const sCenario  = ref('')
const sHipotese = ref('')
const sGerando  = ref(false)

// ─── Etapa 3: Materiais ───────────────────────────────────────
const arquivos = ref([])
const dragOver = ref(false)

// ─── Etapa 4: Parâmetros ──────────────────────────────────────
const agentes = ref(50)
const rodadas = ref(20)
const escalaTempo = ref('meses') // meses | semanas | dias

// ─── Validações ───────────────────────────────────────────────
const e1ok = computed(() => pNome.value.trim().length >= 3)
const e2ok = computed(() => sTitulo.value.trim().length >= 3 && sHipotese.value.trim().length >= 10)
const e3ok = computed(() => true) // materiais são opcionais

const descAgentes = computed(() => {
  if (agentes.value <= 20)  return 'Teste rápido — ideal para validar a hipótese'
  if (agentes.value <= 100) return 'Bom equilíbrio entre velocidade e precisão'
  if (agentes.value <= 250) return 'Alta fidelidade — captura nuances importantes'
  return 'Máxima riqueza — simulação de alta complexidade'
})
const descRodadas = computed(() => {
  const u = escalaTempo.value === 'meses' ? 'meses' : escalaTempo.value === 'semanas' ? 'semanas' : 'dias'
  return `${rodadas.value} ${u} simulados — cada rodada = 1 ${u.slice(0,-1)}`
})
const estMinutos = computed(() => Math.round(Math.max(2, agentes.value * rodadas.value * 0.04)))
const estCusto   = computed(() => (agentes.value * rodadas.value * 0.0008).toFixed(2))
const qualidade  = computed(() => {
  const n = arquivos.value.length
  if (n === 0) return { label: 'Sem materiais', cor: '#6b6b80', pct: 0,   desc: 'Os agentes usarão apenas a hipótese como base' }
  if (n === 1)  return { label: 'Básico',       cor: '#f5a623', pct: 33,  desc: 'Um documento fornece contexto inicial' }
  if (n <= 3)   return { label: 'Bom',          cor: '#7c6ff7', pct: 66,  desc: 'Múltiplos documentos enriquecem os agentes' }
  return              { label: 'Excelente',      cor: '#00e5c3', pct: 100, desc: 'Base de conhecimento robusta' }
})

// ─── Gerar hipótese com IA ────────────────────────────────────
async function gerarHipotese() {
  if (!sCenario.value.trim()) return
  sGerando.value = true
  try {
    const res  = await service.post('/api/graph/generate-hypothesis', { cenario: sCenario.value, segmento: '' })
    const data = res.data || res
    if (data.hipotese) sHipotese.value = data.hipotese
    if (data.titulo && !sTitulo.value) sTitulo.value = data.titulo.slice(0, 60)
  } catch {
    sHipotese.value = `Como ${sCenario.value.toLowerCase()} vai impactar o mercado nos próximos meses?`
  } finally {
    sGerando.value = false
  }
}

// ─── Upload ───────────────────────────────────────────────────
function onFile(e)  { addFiles(Array.from(e.target.files || [])) }
function onDrop(e)  { e.preventDefault(); dragOver.value = false; addFiles(Array.from(e.dataTransfer.files || [])) }
function addFiles(files) {
  files.forEach(f => {
    if (f.size > 16*1024*1024) return
    const ok = ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','image/png','image/jpeg']
    if (!ok.includes(f.type) && !f.name.match(/\.(pdf|docx|txt|png|jpg|jpeg)$/i)) return
    if (!arquivos.value.find(a => a.name === f.name)) arquivos.value.push(f)
  })
}
function removeFile(i) { arquivos.value.splice(i, 1) }
function fmtBytes(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB'
  return (b/(1024*1024)).toFixed(1) + ' MB'
}
function ficon(n) {
  if (n.match(/\.pdf$/i)) return '📄'
  if (n.match(/\.docx?$/i)) return '📝'
  if (n.match(/\.txt$/i)) return '📃'
  if (n.match(/\.(png|jpg|jpeg)$/i)) return '🖼️'
  return '📎'
}

// ─── Criar tudo ───────────────────────────────────────────────
async function criar() {
  loading.value = true
  erro.value    = ''
  try {
    const projectName = pCliente.value.trim()
      ? `${pCliente.value.trim()} — ${pNome.value.trim()}`
      : pNome.value.trim()

    const fd = new FormData()
    fd.append('project_name', projectName)
    fd.append('simulation_requirement', sHipotese.value)
    arquivos.value.forEach(f => fd.append('files', f))

    // 1. Criar projeto + gerar ontologia
    const r1   = await service.post('/api/graph/ontology/generate', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    const d1   = r1.data || r1
    const pid  = d1.project_id
    if (!pid) throw new Error('project_id não retornado')

    // 2. Iniciar construção do grafo
    await service.post('/api/graph/build', { project_id: pid, simulation_requirement: sHipotese.value })

    // 3. Ir para o pipeline passando todos os parâmetros
    router.push(`/simulacao/${pid}?agentes=${agentes.value}&rodadas=${rodadas.value}&escala=${escalaTempo.value}`)
  } catch (e) {
    erro.value = e?.response?.data?.error || e?.message || 'Erro ao criar. Tente novamente.'
  } finally {
    loading.value = false
  }
}

const steps = ['Projeto', 'Simulação', 'Materiais', 'Parâmetros']
</script>

<template>
  <AppShell title="Novo Projeto">
    <div class="page">

      <!-- Cabeçalho -->
      <div class="header">
        <div>
          <h1 class="titulo">Novo Projeto</h1>
          <p class="subtitulo">Configure o projeto e a primeira simulação em 4 passos simples.</p>
        </div>
        <button class="btn-ghost" @click="router.push('/')">← Cancelar</button>
      </div>

      <!-- Barra de progresso -->
      <div class="progress-wrap">
        <div
          v-for="(s, i) in steps" :key="i"
          class="step"
          :class="{ active: etapa === i+1, done: etapa > i+1 }"
        >
          <div class="step-circle">
            <svg v-if="etapa > i+1" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12"><polyline points="2,6 5,9 10,3"/></svg>
            <span v-else>{{ i+1 }}</span>
          </div>
          <div v-if="i < steps.length - 1" class="step-connector" :class="{ done: etapa > i+1 }"></div>
          <span class="step-label">{{ s }}</span>
        </div>
      </div>

      <!-- ════════════════════════════════ -->
      <!-- ETAPA 1: PROJETO                -->
      <!-- ════════════════════════════════ -->
      <Transition name="slide" mode="out-in">
        <div v-if="etapa === 1" key="e1" class="card">
          <div class="card-head">
            <div class="card-icon-wrap">📋</div>
            <div>
              <div class="card-titulo">Identifique o projeto</div>
              <div class="card-sub">Nome e cliente. As hipóteses ficam na simulação.</div>
            </div>
          </div>
          <div class="field">
            <label>Nome do projeto <span class="req">*</span></label>
            <input v-model="pNome" class="inp" type="text"
              placeholder="Ex: Lançamento Linha Premium, Campanha Eleições 2026" autofocus/>
          </div>
          <div class="field">
            <label>Cliente / Empresa <span class="opt">opcional</span></label>
            <input v-model="pCliente" class="inp" type="text"
              placeholder="Ex: Empresa ABC, Rafael Moreira"/>
          </div>
          <div class="card-footer">
            <span></span>
            <button class="btn-next" :disabled="!e1ok" @click="etapa = 2">
              Próximo →
            </button>
          </div>
        </div>

        <!-- ════════════════════════════════ -->
        <!-- ETAPA 2: SIMULAÇÃO              -->
        <!-- ════════════════════════════════ -->
        <div v-else-if="etapa === 2" key="e2" class="card">
          <div class="card-head">
            <div class="card-icon-wrap">🎯</div>
            <div>
              <div class="card-titulo">Defina a simulação</div>
              <div class="card-sub">O que você quer prever? Descreva o cenário e a hipótese.</div>
            </div>
          </div>
          <div class="field">
            <label>Título da simulação <span class="req">*</span></label>
            <input v-model="sTitulo" class="inp" type="text"
              placeholder="Ex: Reação ao novo preço, Cenário 1º turno eleições"/>
            <div class="field-hint">Identifica esta simulação dentro do projeto.</div>
          </div>
          <div class="field">
            <label>Descreva seu cenário</label>
            <textarea v-model="sCenario" class="textarea" rows="3"
              placeholder="Em linguagem natural: O que quer testar? Qual situação quer prever? A IA vai estruturar para você."/>
            <button class="btn-ia" :disabled="!sCenario.trim() || sGerando" @click="gerarHipotese">
              <span v-if="sGerando" class="spinner-ia"></span>
              <span v-else>✦</span>
              {{ sGerando ? 'Gerando hipótese...' : 'Gerar hipótese com IA' }}
            </button>
          </div>
          <div class="divider">ou preencha diretamente:</div>
          <div class="field">
            <label>Hipótese de previsão <span class="req">*</span></label>
            <textarea v-model="sHipotese" class="textarea" rows="3"
              placeholder="Como X vai impactar Y nos próximos Z meses? Quais são os riscos e oportunidades?"/>
            <div class="field-hint">Guia o comportamento de todos os agentes. Mínimo 10 caracteres.</div>
          </div>
          <div class="card-footer">
            <button class="btn-ghost" @click="etapa = 1">← Voltar</button>
            <button class="btn-next" :disabled="!e2ok" @click="etapa = 3">
              Próximo →
            </button>
          </div>
        </div>

        <!-- ════════════════════════════════ -->
        <!-- ETAPA 3: MATERIAIS              -->
        <!-- ════════════════════════════════ -->
        <div v-else-if="etapa === 3" key="e3" class="card">
          <div class="card-head">
            <div class="card-icon-wrap">📁</div>
            <div>
              <div class="card-titulo">Materiais de referência <span class="badge-opt">opcional</span></div>
              <div class="card-sub">Pesquisas, relatórios, notícias. Tornam os agentes muito mais precisos.</div>
            </div>
          </div>
          <div class="tip">💡 Pesquisas acadêmicas e relatórios de mercado são os melhores insumos.</div>
          <div class="drop-zone" :class="{ over: dragOver }"
            @dragover.prevent="dragOver=true" @dragleave="dragOver=false"
            @drop="onDrop" @click="$refs.fi.click()">
            <input ref="fi" type="file" multiple accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
              style="display:none" @change="onFile"/>
            <div class="drop-inner">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="28" height="28" style="color:var(--text-muted)">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <span class="drop-title">{{ dragOver ? 'Solte aqui' : 'Clique ou arraste arquivos' }}</span>
              <span class="drop-sub">PDF, DOCX, TXT, PNG, JPG — até 16MB cada</span>
            </div>
          </div>
          <div v-if="arquivos.length" class="files">
            <div v-for="(f,i) in arquivos" :key="f.name" class="file">
              <span>{{ ficon(f.name) }}</span>
              <div class="file-info">
                <div class="file-name">{{ f.name }}</div>
                <div class="file-size">{{ fmtBytes(f.size) }}</div>
              </div>
              <button class="file-rm" @click="removeFile(i)">×</button>
            </div>
          </div>
          <div class="qualidade">
            <div class="q-bar"><div class="q-fill" :style="{ width: qualidade.pct+'%', background: qualidade.cor }"></div></div>
            <span class="q-label" :style="{ color: qualidade.cor }">{{ qualidade.label }}</span>
            <span class="q-desc">{{ qualidade.desc }}</span>
          </div>
          <div class="card-footer">
            <button class="btn-ghost" @click="etapa = 2">← Voltar</button>
            <button class="btn-next" @click="etapa = 4">Próximo →</button>
          </div>
        </div>

        <!-- ════════════════════════════════ -->
        <!-- ETAPA 4: PARÂMETROS + RESUMO   -->
        <!-- ════════════════════════════════ -->
        <div v-else-if="etapa === 4" key="e4" class="card">
          <div class="card-head">
            <div class="card-icon-wrap">⚙️</div>
            <div>
              <div class="card-titulo">Parâmetros da simulação</div>
              <div class="card-sub">Mais agentes e rodadas = análise mais rica, porém mais lenta.</div>
            </div>
          </div>

          <div class="param">
            <div class="param-header">
              <span class="param-label">Número de Agentes</span>
              <span class="param-val">{{ agentes }}</span>
            </div>
            <input type="range" min="5" max="500" step="5" v-model.number="agentes" class="slider"/>
            <div class="param-bounds"><span>5 — rápido</span><span>500 — máxima riqueza</span></div>
            <div class="param-desc">{{ descAgentes }}</div>
          </div>

          <div class="param">
            <div class="param-header">
              <span class="param-label">Número de Rodadas</span>
              <span class="param-val">{{ rodadas }}</span>
            </div>
            <input type="range" min="1" max="100" step="1" v-model.number="rodadas" class="slider"/>
            <div class="param-bounds"><span>1 — instantâneo</span><span>100 — evolução completa</span></div>
            <div class="param-desc">{{ descRodadas }}</div>
            <div class="escala-row">
              <span class="escala-label">Cada rodada representa:</span>
              <div class="escala-btns">
                <button :class="['escala-btn', { active: escalaTempo === 'dias' }]" @click="escalaTempo = 'dias'">1 Dia</button>
                <button :class="['escala-btn', { active: escalaTempo === 'semanas' }]" @click="escalaTempo = 'semanas'">1 Semana</button>
                <button :class="['escala-btn', { active: escalaTempo === 'meses' }]" @click="escalaTempo = 'meses'">1 Mês</button>
              </div>
            </div>
          </div>

          <!-- Estimativas -->
          <div class="estimativas">
            <div class="est"><div class="est-l">⏱ Tempo</div><div class="est-v">~{{ estMinutos }} min</div></div>
            <div class="est-sep"></div>
            <div class="est"><div class="est-l">💳 Custo</div><div class="est-v">~${{ estCusto }}</div></div>
            <div class="est-sep"></div>
            <div class="est"><div class="est-l">🤖 Agentes</div><div class="est-v accent">{{ agentes }}</div></div>
            <div class="est-sep"></div>
            <div class="est"><div class="est-l">🔄 Rodadas</div><div class="est-v accent2">{{ rodadas }}</div></div>
          </div>

          <!-- Resumo final -->
          <div class="resumo">
            <div class="resumo-titulo">Resumo</div>
            <div class="resumo-linha"><span class="rk">Projeto</span><span class="rv">{{ pCliente ? pCliente+' — ' : '' }}{{ pNome }}</span></div>
            <div class="resumo-linha"><span class="rk">Simulação</span><span class="rv">{{ sTitulo }}</span></div>
            <div class="resumo-linha"><span class="rk">Hipótese</span><span class="rv">{{ sHipotese.length > 70 ? sHipotese.slice(0,70)+'...' : sHipotese }}</span></div>
            <div class="resumo-linha"><span class="rk">Materiais</span><span class="rv">{{ arquivos.length ? arquivos.length+' arquivo(s)' : 'Nenhum' }}</span></div>
          </div>

          <div v-if="erro" class="erro">⚠️ {{ erro }}</div>

          <div class="card-footer">
            <button class="btn-ghost" @click="etapa = 3">← Voltar</button>
            <button class="btn-criar" :disabled="loading" @click="criar">
              <span v-if="loading" class="spinner"></span>
              <span v-else>✦</span>
              {{ loading ? 'Criando projeto...' : 'Criar e Iniciar Simulação' }}
            </button>
          </div>
        </div>
      </Transition>

    </div>
  </AppShell>
</template>

<style scoped>
/* ═══ AUGUR Light Design System ═══ */
:deep(.app-content) {
  --bg-base: #f5f5fa;
  --bg-surface: #ffffff;
  --bg-raised: #fafafe;
  --bg-overlay: #f0f0f5;
  --border: #eeeef2;
  --border-md: #dddde5;
  --text-primary: #1a1a2e;
  --text-secondary: #444466;
  --text-muted: #8888aa;
  --accent: #00e5c3;
  --accent-dim: rgba(0,229,195,0.08);
  --accent2: #7c6ff7;
  --accent2-dim: rgba(124,111,247,0.08);
  --danger: #ff5a5a;
  --font-mono: 'JetBrains Mono', monospace;
}

.page { max-width: 640px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; padding-bottom: 60px; }

.header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.titulo { font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px; letter-spacing: -0.6px; }
.subtitulo { font-size: 13px; color: var(--text-secondary); margin: 0; }

/* Progress */
.progress-wrap { display: flex; align-items: flex-start; }
.step { display: flex; flex-direction: column; align-items: center; position: relative; flex: 1; }
.step-circle { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; background: var(--bg-raised); border: 2px solid var(--border-md); color: var(--text-muted); z-index: 1; transition: all 0.3s; }
.step.active .step-circle { background: var(--accent2); border-color: var(--accent2); color: #fff; box-shadow: 0 0 0 4px rgba(124,111,247,0.15); }
.step.done   .step-circle { background: var(--accent);  border-color: var(--accent);  color: #000; }
.step-connector { position: absolute; top: 15px; left: 50%; width: 100%; height: 2px; background: var(--border-md); z-index: 0; transition: background 0.3s; }
.step-connector.done { background: var(--accent); }
.step-label { font-size: 11px; color: var(--text-muted); margin-top: 8px; text-align: center; white-space: nowrap; }
.step.active .step-label { color: var(--accent2); font-weight: 600; }
.step.done   .step-label { color: var(--text-secondary); }

/* Card */
.card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 16px;box-shadow:0 1px 3px rgba(0,0,0,0.04); padding: 28px; display: flex; flex-direction: column; gap: 20px; }
.card-head { display: flex; align-items: flex-start; gap: 14px; }
.card-icon-wrap { font-size: 24px; flex-shrink: 0; margin-top: 2px; }
.card-titulo { font-size: 17px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.card-sub { font-size: 13px; color: var(--text-secondary); margin-top: 4px; line-height: 1.5; }
.card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }

/* Fields */
.field { display: flex; flex-direction: column; gap: 8px; }
.field label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.req { color: var(--accent); font-weight: 400; }
.opt { font-size: 11px; color: var(--text-muted); font-weight: 400; background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 20px; padding: 1px 7px; margin-left: 4px; }
.field-hint { font-size: 11px; color: var(--text-muted); }
.inp { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 14px; padding: 12px 14px; outline: none; transition: border-color 0.15s; width: 100%; }
.inp:focus { border-color: var(--accent2); }
.textarea { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 13px; padding: 12px 14px; outline: none; resize: vertical; font-family: inherit; line-height: 1.7; transition: border-color 0.15s; }
.textarea:focus { border-color: var(--accent2); }

.btn-ia { background: var(--accent2); color: #fff; border: none; border-radius: 8px; padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 7px; transition: all 0.2s; align-self: flex-start; }
.btn-ia:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-ia:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.spinner-ia { width: 12px; height: 12px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }

.divider { font-size: 12px; color: var(--text-muted); text-align: center; position: relative; }
.divider::before, .divider::after { content: ''; position: absolute; top: 50%; height: 1px; background: var(--border); width: 35%; }
.divider::before { left: 0; }
.divider::after  { right: 0; }

.badge-opt { font-size: 11px; color: var(--text-muted); background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 20px; padding: 1px 8px; font-weight: 400; }

/* Drop zone */
.tip { background: rgba(124,111,247,0.08); border: 1px solid rgba(124,111,247,0.2); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: var(--accent2); }
.drop-zone { border: 2px dashed var(--border-md); border-radius: 12px; padding: 28px; cursor: pointer; transition: all 0.2s; background: var(--bg-raised); }
.drop-zone:hover, .drop-zone.over { border-color: var(--accent); background: rgba(0,229,195,0.03); }
.drop-inner { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.drop-title { font-size: 14px; font-weight:600; color: var(--text-primary); }
.drop-sub { font-size: 12px; color: var(--text-muted); }

.files { display: flex; flex-direction: column; gap: 6px; }
.file { display: flex; align-items: center; gap: 10px; background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-size: 11px; color: var(--text-muted); }
.file-rm { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 20px; line-height: 1; }
.file-rm:hover { color: var(--danger); }

.qualidade { display: flex; align-items: center; gap: 10px; }
.q-bar { flex: 1; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; }
.q-fill { height: 100%; border-radius: 3px; transition: all 0.4s; }
.q-label { font-size: 12px; font-weight: 600; white-space: nowrap; }
.q-desc { font-size: 11px; color: var(--text-muted); }

/* Parâmetros */
.param { display: flex; flex-direction: column; gap: 8px; }
.param-header { display: flex; justify-content: space-between; align-items: center; }
.param-label { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.param-val { font-size: 24px; font-weight: 800; color: var(--accent2); font-family: var(--font-mono); }
.param-bounds { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
.param-desc { font-size: 12px; color: var(--text-secondary); background: var(--bg-raised); border-radius:8px; padding: 8px 12px; }
.slider { width: 100%; accent-color: var(--accent2); cursor: pointer; }

.estimativas { display: flex; background: var(--bg-raised); border: 1px solid var(--border); border-radius:14px; overflow: hidden; }
.est { flex: 1; padding: 12px 14px; }
.est-l { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.est-v { font-size: 16px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.est-sep { width: 1px; background: var(--border); margin: 8px 0; }
.accent  { color: var(--accent); }
.accent2 { color: var(--accent2); }

/* Resumo */
.resumo { background: var(--bg-raised); border: 1px solid var(--border); border-radius:14px; overflow: hidden; }
.resumo-titulo { font-size: 11px; font-weight: 700; color: var(--text-muted); padding: 10px 14px 6px; text-transform: uppercase; letter-spacing: 0.6px; }
.resumo-linha { display: flex; justify-content: space-between; align-items: flex-start; padding: 7px 14px; border-top: 1px solid var(--border); font-size: 13px; gap: 16px; }
.rk { color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
.rv { color: var(--text-primary); text-align: right; }

/* Botões */
.btn-ghost { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px; padding: 10px 16px; border-radius: 8px; transition: color 0.15s; }
.btn-ghost:hover { color: var(--text-primary); }
.btn-next { background: var(--accent2); color: #fff; border: none; border-radius:14px; padding: 12px 24px; font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.2s; }
.btn-next:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-next:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-criar { background: var(--accent); color: #000; border: none; border-radius:14px; padding: 13px 28px; font-size: 15px; font-weight: 800; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; letter-spacing: -0.2px; }
.btn-criar:hover:not(:disabled) { opacity: 0.88; transform: translateY(-2px); }
.btn-criar:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.25); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.erro { background: rgba(255,90,90,0.1); border: 1px solid rgba(255,90,90,0.3); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--danger); }

/* Escala de tempo */
.escala-row { display:flex; align-items:center; gap:10px; margin-top:8px; }
.escala-label { font-size:12px; color:var(--text-muted); white-space:nowrap; }
.escala-btns { display:flex; gap:4px; }
.escala-btn { padding:5px 12px; border-radius:8px; border:1px solid var(--border); background:var(--bg-surface); color:var(--text-secondary); font-size:12px; font-weight:600; cursor:pointer; transition:all .2s; }
.escala-btn:hover { border-color:var(--accent2); }
.escala-btn.active { background:var(--accent2); color:#fff; border-color:var(--accent2); }

/* Transitions */
.slide-enter-active { transition: all 0.25s ease; }
.slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from { opacity: 0; transform: translateX(20px); }
.slide-leave-to  { opacity: 0; transform: translateX(-20px); }
</style>
