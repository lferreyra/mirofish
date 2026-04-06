<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/layout/AppShell.vue'
import service from '../api'

const router = useRouter()

const isLoading = ref(false)
const error     = ref('')

// ─── Dados do projeto ─────────────────────────────────────────
const nome    = ref('')
const cliente = ref('')

const valido = computed(() => nome.value.trim().length >= 3)

// ─── Criar projeto (só identidade — sem simulação ainda) ──────
async function criarProjeto() {
  if (!valido.value) return
  isLoading.value = true
  error.value = ''
  try {
    const projectName = cliente.value.trim()
      ? `${cliente.value.trim()} — ${nome.value.trim()}`
      : nome.value.trim()

    // Criar projeto vazio (sem hipótese e sem grafo ainda)
    // O grafo será construído quando o usuário criar a primeira simulação
    const res = await service.post('/api/graph/ontology/generate',
      (() => {
        const fd = new FormData()
        fd.append('project_name', projectName)
        fd.append('simulation_requirement', ' ') // placeholder mínimo
        return fd
      })(),
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    const data = res.data || res
    const projectId = data.project_id
    if (!projectId) throw new Error('project_id não retornado')

    // Ir direto para o projeto — sem construir grafo ainda
    // O grafo será construído quando o usuário criar a primeira simulação
    router.push(`/projeto/${projectId}?novo=1`)
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
    <div class="page">

      <div class="page-header">
        <div>
          <h1 class="page-title">Novo Projeto</h1>
          <p class="page-sub">Identifique o projeto. Você vai criar as simulações dentro dele.</p>
        </div>
        <button class="btn-ghost" @click="router.push('/')">← Cancelar</button>
      </div>

      <div class="card">
        <div class="card-head">
          <span class="card-icon">📋</span>
          <div>
            <div class="card-title">Identificação do Projeto</div>
            <div class="card-sub">Nome e cliente. Simples assim — as hipóteses ficam nas simulações.</div>
          </div>
        </div>

        <div class="field">
          <label class="label">Nome do projeto <span class="req">*</span></label>
          <input
            v-model="nome"
            class="inp"
            type="text"
            placeholder="Ex: Lançamento Linha Premium, Campanha Eleições 2026"
            autofocus
          />
          <div class="hint">Use um nome que identifique o objetivo da análise.</div>
        </div>

        <div class="field">
          <label class="label">Cliente / Empresa</label>
          <input
            v-model="cliente"
            class="inp"
            type="text"
            placeholder="Ex: Empresa ABC, Rafael Moreira (opcional)"
          />
        </div>

        <!-- O que vem a seguir -->
        <div class="proximo-info">
          <div class="proximo-titulo">O que acontece depois:</div>
          <div class="proximo-item">
            <span class="proximo-num">1</span>
            <span>Projeto criado</span>
          </div>
          <div class="proximo-item">
            <span class="proximo-num">2</span>
            <span>Você cria uma <strong>simulação</strong> com título, cenário, hipótese e materiais</span>
          </div>
          <div class="proximo-item">
            <span class="proximo-num">3</span>
            <span>O sistema constrói o grafo e executa os agentes</span>
          </div>
          <div class="proximo-item">
            <span class="proximo-num">4</span>
            <span>Relatório com insights e sentimento do mercado</span>
          </div>
        </div>

        <div v-if="error" class="error-box">⚠️ {{ error }}</div>

        <div class="actions">
          <button class="btn-ghost" @click="router.push('/')">Cancelar</button>
          <button class="btn-criar" :disabled="!valido || isLoading" @click="criarProjeto">
            <span v-if="isLoading" class="spinner"></span>
            <span v-else>→</span>
            {{ isLoading ? 'Criando...' : 'Criar Projeto' }}
          </button>
        </div>
      </div>

    </div>
  </AppShell>
</template>

<style scoped>
.page { max-width: 560px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; padding-bottom: 60px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; letter-spacing: -0.5px; }
.page-sub { font-size: 13px; color: var(--text-secondary); margin: 0; }

.card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 28px; display: flex; flex-direction: column; gap: 20px; }
.card-head { display: flex; align-items: flex-start; gap: 12px; }
.card-icon { font-size: 22px; flex-shrink: 0; }
.card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.card-sub { font-size: 13px; color: var(--text-secondary); margin-top: 3px; line-height: 1.5; }

.field { display: flex; flex-direction: column; gap: 7px; }
.label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.req { color: var(--accent); }
.inp { background: var(--bg-raised); border: 1px solid var(--border-md); border-radius: 8px; color: var(--text-primary); font-size: 14px; padding: 12px 14px; outline: none; transition: border-color 0.15s; width: 100%; }
.inp:focus { border-color: var(--accent2); }
.hint { font-size: 12px; color: var(--text-muted); }

.proximo-info { background: var(--bg-raised); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 10px; border: 1px solid var(--border); }
.proximo-titulo { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 2px; }
.proximo-item { display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: var(--text-secondary); }
.proximo-num { width: 20px; height: 20px; border-radius: 50%; background: var(--accent2-dim); color: var(--accent2); font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px; }
.proximo-item strong { color: var(--text-primary); }

.error-box { background: rgba(255,90,90,0.1); border: 1px solid rgba(255,90,90,0.3); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--danger); }

.actions { display: flex; justify-content: space-between; align-items: center; }
.btn-ghost { background: transparent; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px; padding: 10px 16px; border-radius: 8px; transition: color 0.15s; }
.btn-ghost:hover { color: var(--text-primary); }
.btn-criar { background: var(--accent); color: #000; border: none; border-radius: 10px; padding: 13px 28px; font-size: 15px; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.2s; }
.btn-criar:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.btn-criar:disabled { opacity: 0.3; cursor: not-allowed; transform: none; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(0,0,0,0.25); border-top-color: #000; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
