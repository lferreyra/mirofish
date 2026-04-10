import { ref } from 'vue'

export const useStageRestart = ({
  runRestart,
  resetState,
  onStarted,
  addLog,
  startMessage = 'Restarting stage from scratch...'
} = {}) => {
  const isRestarting = ref(false)
  const restartError = ref('')

  const restartStage = async () => {
    if (isRestarting.value) return false

    restartError.value = ''
    isRestarting.value = true

    try {
      addLog?.(startMessage)
      resetState?.()
      const res = await runRestart()
      onStarted?.(res)
      return true
    } catch (err) {
      restartError.value = err?.message || 'Restart failed'
      throw err
    } finally {
      isRestarting.value = false
    }
  }

  const clearRestartError = () => {
    restartError.value = ''
  }

  return {
    isRestarting,
    restartError,
    restartStage,
    clearRestartError,
  }
}
