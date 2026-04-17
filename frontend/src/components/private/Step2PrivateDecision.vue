<template>
  <div class="form-container">
    <div class="section-title-row">
      <h2 class="section-h2">Define the Decision</h2>
      <p class="section-hint">Fill in the decision context. These details will drive the simulation.</p>
    </div>

    <div
      class="drop-zone"
      :class="{ 'drop-zone--active': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="triggerImport"
    >
      <input type="file" ref="importInput" accept=".txt" style="display:none" @change="handleImport" />
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
      <span class="drop-zone-label">Glisser le fichier ici ou cliquer pour importer</span>
      <span class="drop-zone-hint">private_impact_requirement.txt — dossier 02_simulation_params/</span>
    </div>

    <div v-if="projectId && !projectData?.graph_id" class="graph-building-notice">
      <div class="loading-ring loading-ring--sm"></div>
      <span>Graphe en construction — les champs peuvent déjà être remplis. Le bouton s'activera automatiquement.</span>
    </div>

    <div class="form-grid">
      <!-- Left column -->
      <div class="form-col">
        <div class="field-group">
          <label class="field-label">DECISION MAKER</label>
          <div class="field-row-3">
            <input class="field-input" v-model="form.decisionMakerName" placeholder="Full name" />
            <input class="field-input" v-model="form.decisionMakerRole" placeholder="Role / title" />
            <input class="field-input" v-model="form.decisionMakerCompany" placeholder="Organisation" />
          </div>
        </div>

        <div class="field-group">
          <label class="field-label">DECISION <span class="required">*</span></label>
          <textarea
            class="field-textarea"
            v-model="form.decisionText"
            rows="5"
            placeholder="Describe the decision precisely. E.g. 'We are closing the Lyon office and transferring 40 employees to Paris by Q3.'"
          ></textarea>
        </div>

        <div class="field-group">
          <label class="field-label">ADDITIONAL CONTEXT</label>
          <textarea
            class="field-textarea"
            v-model="form.decisionContext"
            rows="3"
            placeholder="Background information, strategic rationale, known sensitivities..."
          ></textarea>
        </div>
      </div>

      <!-- Right column -->
      <div class="form-col">
        <div class="field-group">
          <label class="field-label">RELATIONAL NETWORK — types to include</label>
          <div class="checkbox-grid">
            <label
              v-for="t in RELATIONAL_TYPES"
              :key="t"
              class="checkbox-item"
              :class="{ 'is-checked': form.relationalTypes.includes(t) }"
            >
              <input
                type="checkbox"
                :value="t"
                v-model="form.relationalTypes"
                class="checkbox-native"
              />
              <span class="checkbox-box"></span>
              <span class="checkbox-label">{{ RELATIONAL_TYPE_LABELS[t] }}</span>
            </label>
          </div>

          <div v-if="form.relationalTypes.length > 0" class="agent-counts-block">
            <div v-for="t in form.relationalTypes" :key="t" class="agent-count-row">
              <span class="agent-count-label">{{ RELATIONAL_TYPE_LABELS[t] }}</span>
              <div class="agent-count-sep"></div>
              <input
                type="number"
                class="agent-count-input"
                v-model.number="agentCounts[t]"
                min="1"
                max="200"
              />
            </div>
            <div class="agent-count-total">Total : {{ totalAgents }} agents</div>
          </div>
        </div>

        <div class="field-group">
          <label class="field-label">TEMPORAL HORIZON</label>
          <div class="horizon-btns">
            <button
              v-for="opt in HORIZON_OPTIONS"
              :key="opt.days"
              type="button"
              class="horizon-btn"
              :class="{ 'is-active': form.horizonDays === opt.days }"
              @click="form.horizonDays = opt.days"
            >{{ opt.label }}</button>
          </div>
        </div>

        <div class="field-group">
          <label class="field-label">QUESTIONS TO MEASURE</label>
          <textarea
            class="field-textarea"
            v-model="form.questionsToMeasure"
            rows="3"
            placeholder="What do you want to measure? E.g. 'What is the risk of collective resistance? Who are the key opinion leaders?'"
          ></textarea>
        </div>
      </div>
    </div>

    <div class="form-footer">
      <button
        class="btn-primary"
        :disabled="!form.decisionText.trim() || form.relationalTypes.length === 0 || (projectId && !projectData?.graph_id)"
        @click="$emit('prepare')"
      >
        Prepare Simulation
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { RELATIONAL_TYPES, RELATIONAL_TYPE_LABELS, HORIZON_OPTIONS } from '../../constants/private.js'
import { parseImportedConfig } from '../../utils/private.js'

const props = defineProps({
  form: { type: Object, required: true },
  agentCounts: { type: Object, required: true },
  projectId: { type: String, default: null },
  projectData: { type: Object, default: null },
})

defineEmits(['prepare'])

const importInput = ref(null)
const isDragOver = ref(false)

const totalAgents = computed(() =>
  Object.values(props.agentCounts).reduce((sum, n) => sum + (n || 0), 0)
)

watch(() => props.form.relationalTypes, (types) => {
  for (const t of types) {
    if (!(t in props.agentCounts)) props.agentCounts[t] = 10
  }
  for (const key of Object.keys(props.agentCounts)) {
    if (!types.includes(key)) delete props.agentCounts[key]
  }
}, { immediate: true, deep: true })

const triggerImport = () => { importInput.value?.click() }

const handleDrop = (event) => {
  isDragOver.value = false
  const file = event.dataTransfer.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => parseImportedConfig(e.target.result, props.form, props.agentCounts, RELATIONAL_TYPES, RELATIONAL_TYPE_LABELS)
  reader.readAsText(file)
}

const handleImport = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    parseImportedConfig(e.target.result, props.form, props.agentCounts, RELATIONAL_TYPES, RELATIONAL_TYPE_LABELS)
    event.target.value = ''
  }
  reader.readAsText(file)
}
</script>

<style scoped>
.form-container { max-width: 1100px; margin: 0 auto; }

.section-title-row { margin-bottom: 24px; }
.section-h2 { font-size: 18px; font-weight: 700; color: #000; margin-bottom: 6px; }
.section-hint { font-size: 13px; color: #777; }

.graph-building-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #FFF8E1;
  border: 1px solid #FFE082;
  border-radius: 4px;
  font-size: 12px;
  color: #795548;
  margin-bottom: 20px;
}

.loading-ring {
  width: 40px;
  height: 40px;
  border: 3px solid #E5E7EB;
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-ring--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

.drop-zone {
  border: 2px dashed #D0D0D0;
  border-radius: 6px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  margin-bottom: 24px;
  color: #AAA;
}
.drop-zone:hover { border-color: #000; color: #000; }
.drop-zone--active { border-color: #000; background: #F5F5F5; color: #000; }
.drop-zone-label { font-size: 13px; font-weight: 600; }
.drop-zone-hint { font-size: 10px; letter-spacing: 0.04em; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.form-col { display: flex; flex-direction: column; gap: 20px; }

.field-group { display: flex; flex-direction: column; gap: 8px; }

.field-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #888;
}

.required { color: #FF5722; }

.field-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }

.field-input, .field-textarea {
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 9px 12px;
  font-size: 13px;
  font-family: inherit;
  color: #000;
  background: #fff;
  transition: border-color 0.15s;
  resize: vertical;
}

.field-input:focus, .field-textarea:focus {
  outline: none;
  border-color: #000;
}

.field-input::placeholder, .field-textarea::placeholder { color: #BBB; }

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 8px;
  border: 1.5px solid #E8E8E8;
  border-radius: 3px;
  transition: border-color 0.15s, background 0.15s;
}

.checkbox-item.is-checked { border-color: #000; background: #FAFAFA; }

.checkbox-native { display: none; }

.checkbox-box {
  width: 14px;
  height: 14px;
  border: 1.5px solid #CCC;
  border-radius: 2px;
  flex-shrink: 0;
  background: #fff;
  transition: all 0.12s;
}

.checkbox-item.is-checked .checkbox-box {
  background: #000;
  border-color: #000;
}

.checkbox-label { font-size: 11px; font-weight: 500; color: #444; text-transform: capitalize; }

.form-footer { margin-top: 28px; display: flex; justify-content: flex-end; }

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  background: #000;
  color: #fff;
  border: none;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover { background: #222; }
.btn-primary:disabled { background: #CCC; cursor: not-allowed; }

.horizon-btns { display: flex; flex-wrap: wrap; gap: 8px; }

.horizon-btn {
  padding: 7px 14px;
  border: 1.5px solid #E8E8E8;
  border-radius: 3px;
  background: #fff;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: #444;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.horizon-btn.is-active {
  border-color: #000;
  background: #FAFAFA;
  color: #000;
  font-weight: 600;
}

.agent-counts-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.agent-count-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-count-label {
  min-width: 130px;
  font-size: 11px;
  font-weight: 500;
  color: #444;
  flex-shrink: 0;
}

.agent-count-sep {
  flex: 1;
  height: 1px;
  background: #E8E8E8;
}

.agent-count-input {
  width: 64px;
  border: 1.5px solid #E0E0E0;
  border-radius: 3px;
  padding: 4px 8px;
  font-size: 12px;
  font-family: inherit;
  color: #000;
  text-align: right;
  background: #fff;
  flex-shrink: 0;
}

.agent-count-input:focus { outline: none; border-color: #000; }

.agent-count-total {
  font-size: 11px;
  font-weight: 700;
  color: #555;
  letter-spacing: 0.04em;
  text-align: right;
  margin-top: 4px;
}
</style>
