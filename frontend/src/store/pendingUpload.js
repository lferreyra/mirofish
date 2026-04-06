/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  inputParseMode: 'text_only',
  isPending: false
})

export function setPendingUpload(files, requirement, inputParseMode = 'text_only') {
  state.files = files
  state.simulationRequirement = requirement
  state.inputParseMode = inputParseMode
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    inputParseMode: state.inputParseMode,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.inputParseMode = 'text_only'
  state.isPending = false
}

export default state
