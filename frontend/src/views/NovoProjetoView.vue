<script setup>
import { ref } from 'vue'
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

const nomeValido = ref(nome.value.trim().length >= 3 && briefing.value.trim().length >= 10)

import { computed } from 'vue'
const valido = computed(() => nome.value.trim().length >= 3 && briefing.value.trim().length >= 10)

function onFileChange(e) {
  adicionarArquivos(Array.from(e.target.files || []))
}
function onDrop(e) {
  e.preventDefault()
  dragOver.value = false
  adicionarArquivos(Array.from(e.dataTransfer.files || []))
}
function adicionarArquivos(files) {
  files.forEach(f => {
    if (f.size > 16 * 1024 * 1024) return
    const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'image/png', 'image/jpeg']
    if (!allowed.includes(f.type) && !f.name.match(/\.(pdf|docx|txt|png|jpg|jpeg)$/i)) return
    if (!arquivos.value.find(a => a.name === f.name)) arquivos.value.push(f)
  })
}
function removerArquivo(idx) { arquivos.value.splice(idx, 1) }
function formatBytes(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / (1024 * 1024)).toFixed(1) + ' MB'
}
function fileIcon(n) {
  if (n.match(/\.pdf$/i)) return '📄'
  if (n.match(/\.docx?$/i)) return '📝'
  if (n.match(/\.txt$/i)) return '📃'
  if (n.match(/\.(png|jpg|jpeg)$/i)) return '🖼️'
  return '📎'
}

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
    if (!projectId) throw new Error('project_id não retornado')

    await service.post('/api/graph/build', {
      project_id: projectId,
      simulation_requirement: briefing.value
    })

    router.push(`/projeto/${projectId}`)
  } catch (e) {
    console.error(e)
    error.value = e?.response?.data?.error || e?.message || 'Erro ao criar projeto.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <AppShell title="Novo Projeto">
    <div class="form-wrap">

      <div class="page-header">
        <div>
          <h1 class="page-title">Novo Projeto</h1>
          <p class="page-sub">Um projeto agrupa múltiplas simulações sobre a mesma hipótese ou cliente.</p>
        </div>
        <button class="btn-cancelar" @click="router.push('/')">← Cancelar</button>
      </div>

      <!-- Dados do projeto -->
      <div class="card">
        <div class="card-title">📋 Identificação</div>

        <div class="field">
          <label class="field-label">Nome do projeto <span class="req">*</span></label>
          <input v-model="nome" class="field-input" type="text" placeholder="Ex: Lançamento Produto X, Viabilidade Franquia Y" />
          <div class="field-hint">Use um nome que identifique facilmente o objetivo.</div>
        </div>

        <div class="field">
          <label class="field-label">Cliente / Empresa</label>
          <input v-model="cliente" class="field-input" type="text" placeholder="Ex: Empresa ABC, Marca XYZ (opcional)" />
        </div>
      </div>

      <!-- Hipótese / Briefing -->
      <div class="card">
        <div class="card-title">🎯 Hipótese central</div>
        <div class="card-sub">Descreva o que você quer prever ou entender. Isso guiará todas as simulações deste projeto.</div>

        <div class="field">
          <label class="field-label">Briefing / Hipótese <span class="req">*</span></label>
          <textarea
            v-model="briefing"
            class="field-textarea"
            rows="4"
            placeholder="Ex: Como diferentes grupos do mercado vão reagir ao lançamento de um produto premium voltado para o público feminino 35-50 anos no segmento de bem-estar?"
          />
          <div class="field-hint">Mínimo 10 caracteres. Quanto mais detalhado, mais precisa a simulação.</div>
        </div>
      </div>

      <!-- Materiais -->
      <div class="card">
        <div class="card-title">
          📁 Materiais de referência
          <span class="badge-opt">opcional</span>
        </div>
        <div class="card-sub">Pesquisas, relatórios, dados de mercado, notícias relevantes. Enriquecem o conhecimento dos agentes.</div>

        <div
          class="drop-zone"
          :class="{ 'drag-over': dragOver }"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input ref="fileInput" type="file" multiple accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg" style="display:none" @change="onFileChange" />
          <div class="drop-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="28" height="28">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div class="drop-title">{{ dragOver ? 'Solte aqui' : 'Clique ou arraste arquivos' }}</div>
          <div class="drop-sub">PDF, DOCX, TXT, PNG, JPG — até 16MB</div>
        </div>

        <div v-if="arquivos.length" class="files-list">
          <div v-for="(arq, idx) in arquivos" :key="arq.name" class="file-item">
            <span class="file-icon">{{ fileIcon(arq.name) }}</span>
            <div class="file-info">
              <div class="file-name">{{ arq.name }}</div>
              <div class="file-size">{{ formatBytes(arq.size) }}</div>
            </div>
            <button class="file-remove" @click="removerArquivo(idx)">×</button>
          </div>
        </div>
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <!-- Ações -->
      <div class="form-actions">
        <button class="btn-cancelar" @click="router.push('/')">Cancelar</button>
        <button class="btn-criar" :disabled="!valido || isLoading" @click="criarProjeto">
          <span v-if="isLoading" class="spinner"></span>
          <span v-else>✦</span>
          {{ isLoading ? 'Criando projeto...' : 'Criar Projeto' }}
        </button>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
.form-wrap { max-width: 680px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.page-title { font-size: 24px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; letter-spacing: -0.5px; }
.page-sub { font-size: 13px; color: var(--text-secondary); margin: 0; }

.card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; display: flex; flex-direction: column; gap: 16px; }
.card-title { font-size: 15px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
.card-sub { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-top: -8px; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.req { color: var(--accent); }
.field-input {
  background: var(--bg-raised); border: 1px solid var(--border-md);
  border-radius: 8px; color: var(--text-primary); font-size: 14px;
  padding: 11px 14px; outline: none; transition: border-color 0.15s; width: 100%;
}
.field-input:focus { border-color: var(--accent2); }
.field-textarea {
  background: var(--bg-raised); border: 1px solid var(--border-md);
  border-radius: 8px; color: var(--text-primary); font-size: 14px;
  padding: 11px 14px; outline: none; resize: vertical;
  font-family: inherit; line-height: 1.6; transition: border-color 0.15s;
}
.field-textarea:focus { border-color: var(--accent2); }
.field-hint { font-size: 12px; color: var(--text-muted); }

.badge-opt { font-size: 11px; color: var(--text-muted); background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 20px; padding: 2px 8px; font-weight: 400; }

.drop-zone {
  border: 2px dashed var(--border-md); border-radius: 10px;
  padding: 28px; text-align: center; cursor: pointer; transition: all 0.2s;
  background: var(--bg-raised);
}
.drop-zone:hover, .drop-zone.drag-over { border-color: var(--accent); background: rgba(0,229,195,0.04); }
.drop-icon { color: var(--text-muted); margin-bottom: 8px; display: flex; justify-content: center; }
.drop-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.drop-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

.files-list { display: flex; flex-direction: column; gap: 6px; }
.file-item { display: flex; align-items: center; gap: 10px; background: var(--bg-overlay); border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px; }
.file-icon { font-size: 18px; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 13px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-size: 11px; color: var(--text-muted); }
.file-remove { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 18px; line-height: 1; padding: 0 4px; }
.file-remove:hover { color: var(--danger); }

.error-msg { background: rgba(255,90,90,0.1); border: 1px solid rgba(255,90,90,0.3); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--danger); }

.form-actions { display: flex; justify-content: space-between; align-items: center; }
.btn-cancelar { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px; padding: 10px 16px; border-radius: 8px; transition: color 0.15s; }
.btn-cancelar:hover { color: var(--text-primary); }
.btn-criar {
  background: var(--accent); color: #000; border: none; border-radius: 10px;
  padding: 13px 28px; font-size: 15px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; gap: 8px; transition: all 0.2s;
}
.btn-criar:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-criar:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.25); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
