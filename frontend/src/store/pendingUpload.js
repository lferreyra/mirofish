/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 * 支持两种模式：file（文件上传）和 research（研究课题）
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
