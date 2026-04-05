<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const router = useRouter()
const nome = ref('')
const cliente = ref('')
const briefing = ref('')
const arquivos = ref([])
const dragOver = ref(false)
const isLoading = ref(false)
const error = ref('')
const etapa = ref(1) // 1 = identificação, 2 = hipótese, 3 = materiais

const valido = computed(() => nome.value.trim().length >= 3 && briefing.value.trim().length >= 10)

function onFileChange(e) { adicionarArquivos(Array.from(e.target.files || [])) }
function onDrop(e) { e.preventDefault(); dragOver.value = false; adicionarArquivos(Array.from(e.dataTransfer.files || [])) }
function adicionarArquivos(files) {
  files.forEach(f => {
    if (f.size > 16 * 1024 * 1024) return
    const ok = ['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','image/png','image/jpeg']
    if (!ok.includes(f.type) && !f.name.match(/\.(pdf|docx|txt|png|jpg|jpeg)$/i)) return
    if (!arquivos.value.find(a => a.name === f.name)) arquivos.value.push(f)
  })
}
function removerArquivo(idx) { arquivos.value.splice(idx, 1) }
function formatBytes(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB'
  return (b/(1024*1024)).toFixed(1) + ' MB'
}
function fileIcon(n) {
  if (n.match(/\.pdf$/i)) return '📄'
  if (n.match(/\.docx?$/i)) return '📝'
  if (n.match(/\.txt$/i)) return '📃'
  if (n.match(/\.(png|jpg|jpeg)$/i)) return '🖼️'
  return '📎'
}

const qualidade = computed(() => {
  const n = arquivos.value.length
  if (n === 0) return { label: 'Sem materiais', cor: '#6b6b80', pct: 0, desc: 'Os agentes usarão apenas a hipótese como base' }
  if (n === 1) return { label: 'Básico', cor: '#f5a623', pct: 33, desc: 'Um documento fornece contexto inicial' }
  if (n <= 3) return { label: 'Bom', cor: '#7c6ff7', pct: 66, desc: 'Múltiplos documentos enriquecem os agentes' }
  return { label: 'Excelente', cor: '#00e5c3', pct: 100, desc: 'Base de conhecimento robusta para simulação precisa' }
})

async function criarProjeto() {
  if (!valido.value) return
  isLoading.value = true
  error.value = ''
  try {
    const projectName = cliente.value.trim()
      ? `${cliente.value.trim()} — ${nome.value.trim()}`
      : nome.value.trim()

    const formData = new FormData()
    formData.append('simulation_requirement', briefing.value)
    formData.append('project_name', projectName)
    arquivos.value.forEach(f => formData.append('files', f))

    const res1 = await service.post('/api/graph/ontology/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const data1 = res1.data || res1
    const projectId = data1.project_id
    if (!projectId) throw new Error('project_id não retornado pelo servidor')

    // Iniciar construção do grafo
    await service.post('/api/graph/build', {
      project_id: projectId,
      simulation_requirement: briefing.value
    })

    // Navegar para o pipeline — o usuário acompanha todo o processo
    router.push(`/simulacao/${projectId}?origem=novo_projeto&briefing=${encodeURIComponent(briefing.value.slice(0, 100))}`)
  } catch (e) {
    console.error(e)
    error.value = e?.response?.data?.error || e?.message || 'Erro ao criar projeto. Tente novamente.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <AppShell title="Novo Projeto">
    <div class="page">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1 class="page-title">Novo Projeto</h1>
          <p class="page-sub">Defina sua hipótese e deixe os agentes de IA preverem o futuro do seu mercado.</p>
        </div>
        <button class="btn-ghost" @click="router.push('/')">← Cancelar</button>
      </div>

      <!-- Steps -->
      <div class="steps-bar">
        <div v-for="(s, i) in ['Identificação', 'Hipótese', 'Materiais']" :key="i"
          class="step" :class="{ active: etapa === i+1, done: etapa > i+1 }">
          <div class="step-dot">
            <svg v-if="etapa > i+1" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2.5" width="12" height="12"><polyline points="2,6 5,9 10,3"/></svg>
            <span v-else>{{ i+1 }}</span>
          </div>
          <div v-if="i < 2" class="step-line" :class="{ done: etapa > i+1 }"></div>
          <span class="step-label">{{ s }}</span>
        </div>
      </div>

      <!-- ETAPA 1 — Identificação -->
      <div v-if="etapa === 1" class="card">
        <div class="card-head">
          <span class="card-icon">📋</span>
          <div>
            <div class="card-title">Identifique o projeto</div>
            <div class="card-sub">Dê um nome claro para facilitar a busca depois.</div>
          </div>
        </div>
        <div class="field">
          <label class="label">Nome do projeto <span class="req">*</span></label>
          <input v-model="nome" class="inp" type="text" placeholder="Ex: Lançamento Linha Premium, Viabilidade Franquia 2026" autofocus/>
          <div class="hint">Use um nome que identifique o objetivo da análise.</div>
        </div>
        <div class="field">
          <label class="label">Cliente / Empresa</label>
          <input v-model="cliente" class="inp" type="text" placeholder="Ex: Empresa ABC, Cliente XYZ (opcional)"/>
        </div>
        <div class="step-nav">
          <span></span>
          <button class="btn-next" :disabled="nome.trim().length < 3" @click="etapa = 2">
            Próximo: Hipótese →
          </button>
        </div>
      </div>

      <!-- ETAPA 2 — Hipótese -->
      <div v-else-if="etapa === 2" class="card">
        <div class="card-head">
          <span class="card-icon">🎯</span>
          <div>
            <div class="card-title">Qual é sua hipótese?</div>
            <div class="card-sub">Descreva o que você quer prever. Isso guia todos os agentes da simulação.</div>
          </div>
        </div>
        <div class="field">
          <label class="label">Hipótese / Briefing <span class="req">*</span></label>
          <textarea
            v-model="briefing"
            class="textarea"
            rows="5"
            placeholder="Ex: Como o mercado feminino 35-50 anos vai reagir ao lançamento de uma linha premium de bem-estar com preço acima da média? Quais são os riscos e oportunidades?"
          />
          <div class="hint">Quanto mais contexto, mais precisa a simulação. Mínimo 10 caracteres.</div>
        </div>
        <div class="step-nav">
          <button class="btn-ghost" @click="etapa = 1">← Voltar</button>
          <button class="btn-next" :disabled="briefing.trim().length < 10" @click="etapa = 3">
            Próximo: Materiais →
          </button>
        </div>
      </div>

      <!-- ETAPA 3 — Materiais + Criar -->
      <div v-else-if="etapa === 3" class="card">
        <div class="card-head">
          <span class="card-icon">📁</span>
          <div>
            <div class="card-title">
              Materiais de referência
              <span class="opt-badge">opcional, mas recomendado</span>
            </div>
            <div class="card-sub">Pesquisas, dados de mercado, relatórios, notícias. Enriquecem o conhecimento dos agentes.</div>
          </div>
        </div>

        <div class="quality-tip">
          💡 Documentos como pesquisas acadêmicas e relatórios de mercado tornam a simulação muito mais precisa.
        </div>

        <div
          class="drop-zone"
          :class="{ 'drag-over': dragOver }"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" multiple accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg" style="display:none" @change="onFileChange"/>
          <div class="drop-ico">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="30" height="30">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div class="drop-title">{{ dragOver ? 'Solte aqui' : 'Clique ou arraste arquivos' }}</div>
          <div class="drop-sub">PDF, DOCX, TXT, PNG, JPG — até 16MB cada</div>
        </div>

        <div v-if="arquivos.length" class="files-list">
          <div v-for="(arq, idx) in arquivos" :key="arq.name" class="file-item">
            <span class="file-ico">{{ fileIcon(arq.name) }}</span>
            <div class="file-info">
              <div class="file-name">{{ arq.name }}</div>
              <div class="file-size">{{ formatBytes(arq.size) }}</div>
            </div>
            <button class="file-rm" @click="removerArquivo(idx)">×</button>
          </div>
        </div>

        <!-- Qualidade -->
        <div class="quality-wrap">
          <div class="quality-bar-bg">
            <div class="quality-bar-fill" :style="{ width: qualidade.pct + '%', background: qualidade.cor }"></div>
          </div>
          <div class="quality-info">
            <span class="quality-label" :style="{ color: qualidade.cor }">{{ qualidade.label }}</span>
            <span class="quality-desc">{{ qualidade.desc }}</span>
          </div>
        </div>

        <div v-if="error" class="error-box">⚠️ {{ error }}</div>

        <!-- Resumo antes de criar -->
        <div class="resumo">
          <div class="resumo-title">Resumo do projeto</div>
          <div class="resumo-row">
            <span class="resumo-key">Projeto</span>
            <span class="resumo-val">{{ cliente ? cliente + ' — ' : '' }}{{ nome }}</span>
          </div>
          <div class="resumo-row">
            <span class="resumo-key">Hipótese</span>
            <span class="resumo-val">{{ briefing.length > 80 ? briefing.slice(0,80)+'...' : briefing }}</span>
          </div>
          <div class="resumo-row">
            <span class="resumo-key">Materiais</span>
            <span class="resumo-val">{{ arquivos.length ? arquivos.length + ' arquivo(s)' : 'Nenhum' }}</span>
          </div>
        </div>

        <div class="step-nav">
          <button class="btn-ghost" @click="etapa = 2">← Voltar</button>
          <button class="btn-criar" :disabled="!valido || isLoading" @click="criarProjeto">
            <span v-if="isLoading" class="spinner"></span>
            <span v-else>✦</span>
            {{ isLoading ? 'Criando projeto e iniciando grafo...' : 'Criar Projeto e Simular' }}
          </button>
        </div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
.page { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; letter-spacing: -0.5px; }
.page-sub { font-size: 13px; color: var(--text-secondary); margin: 0; }

/* Steps */
.steps-bar { display: flex; align-items: flex-start; }
.step { display: flex; flex-direction: column; align-items: center; flex: 1; position: relative; }
.step-dot { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; background: var(--bg-raised); border: 2px solid var(--border-md); color: var(--text-muted); z-index: 1; transition: all 0.3s; }
.step.active .step-dot { background: var(--accent2); border-color: var(--accent2); color: #fff; }
.step.done .step-dot { background: var(--accent); border-color: var(--accent); color: #000; }
.step-line { position: absolute; top: 14px; left: 50%; width: 100%; height: 2px; background: var(--border-md); z-index: 0; transition: background 0.3s; }
.step-line.done { background: var(--accent); }
.step-label { font-size: 10px; color: var(--text-muted); margin-top: 6px; text-align: center; }
.step.active .step-label { color: var(--accent2); font-weight: 500; }
.step.done .step-label { color: var(--text-secondary); }

/* Card */
.card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 24px; display: flex; flex-direction: column; gap: 18px; animation: fadeIn 0.25s ease; }
@keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
.card-head { display: flex; align-items: flex-start; gap: 12px; }
.card-icon { font-size: 20px; flex-shrink: 0; }
.card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.card-sub { font-size: 13px; color: var(--text-secondary); margin-top: 3px; line-height: 1.5; }

/* Fields */
.field { display: flex; flex-direction: column; gap: 6px; }
.label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.req { color: var(--accent); }
.inp { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 14px; padding: 11px 14px; outline: none; transition: border-color 0.15s; width: 100%; }
.inp:focus { border-color: var(--accent2); }
.textarea { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 14px; padding: 11px 14px; outline: none; resize: vertical; font-family: inherit; line-height: 1.7; transition: border-color 0.15s; }
.textarea:focus { border-color: var(--accent2); }
.hint { font-size: 12px; color: var(--text-muted); }

.opt-badge { font-size: 11px; color: var(--text-muted); background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 20px; padding: 2px 8px; margin-left: 8px; vertical-align: middle; font-weight: 400; }

.quality-tip { background: rgba(124,111,247,0.08); border: 1px solid rgba(124,111,247,0.2); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: var(--accent2); line-height: 1.5; }

/* Drop zone */
.drop-zone { border: 2px dashed var(--border-md); border-radius: 12px; padding: 32px; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--bg-raised); }
.drop-zone:hover, .drop-zone.drag-over { border-color: var(--accent); background: rgba(0,229,195,0.04); }
.drop-ico { color: var(--text-muted); margin-bottom: 8px; display: flex; justify-content: center; }
.drop-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.drop-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* Files */
.files-list { display: flex; flex-direction: column; gap: 6px; }
.file-item { display: flex; align-items: center; gap: 10px; background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px; }
.file-ico { font-size: 18px; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-size: 11px; color: var(--text-muted); }
.file-rm { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 20px; line-height: 1; padding: 0 2px; transition: color 0.15s; }
.file-rm:hover { color: var(--danger); }

/* Quality */
.quality-wrap { display: flex; flex-direction: column; gap: 6px; }
.quality-bar-bg { height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; }
.quality-bar-fill { height: 100%; border-radius: 3px; transition: all 0.4s; }
.quality-info { display: flex; align-items: center; gap: 10px; }
.quality-label { font-size: 12px; font-weight: 600; }
.quality-desc { font-size: 12px; color: var(--text-muted); }

/* Resumo */
.resumo { background: var(--bg-raised); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.resumo-title { font-size: 12px; font-weight: 600; color: var(--text-muted); padding: 10px 14px 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.resumo-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 7px 14px; border-top: 1px solid var(--border); font-size: 13px; gap: 16px; }
.resumo-key { color: var(--text-muted); white-space: nowrap; flex-shrink: 0; }
.resumo-val { color: var(--text-primary); text-align: right; }

/* Buttons */
.step-nav { display: flex; justify-content: space-between; align-items: center; }
.btn-ghost { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px; padding: 10px 16px; border-radius: 8px; transition: color 0.15s; }
.btn-ghost:hover { color: var(--text-primary); }
.btn-next { background: var(--accent2); color: #fff; border: none; border-radius: 10px; padding: 11px 22px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-next:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-next:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-criar { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 13px 28px; font-size: 15px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
.btn-criar:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-criar:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }

.spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.25); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.error-box { background: rgba(255,90,90,0.1); border: 1px solid rgba(255,90,90,0.3); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--danger); }
</style>
