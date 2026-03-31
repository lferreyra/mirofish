/**
 * Temporary storage for pending upload files and requirements
 * Used for immediate navigation after clicking start engine on the homepage,
 * then making API calls on the Process page
 * Supports two modes: file (file upload) and research (research topic)
 */
import { reactive } from 'vue'

const state = reactive({
  mode: 'file',  // 'file' or 'research'
  files: [],
  simulationRequirement: '',
  researchTopic: '',
  researchDepth: 'shallow',  // 'shallow' | 'deep' | 'research'
  isPending: false
})

export function setPendingUpload(files, requirement, { mode = 'file', researchTopic = '', researchDepth = 'shallow' } = {}) {
  state.mode = mode
  state.files = files
  state.simulationRequirement = requirement
  state.researchTopic = researchTopic
  state.researchDepth = researchDepth
  state.isPending = true
}

export function getPendingUpload() {
  return {
    mode: state.mode,
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    researchTopic: state.researchTopic,
    researchDepth: state.researchDepth,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.mode = 'file'
  state.files = []
  state.simulationRequirement = ''
  state.researchTopic = ''
  state.researchDepth = 'shallow'
  state.isPending = false
}

export default state
