import { onUnmounted, ref } from 'vue'

export function usePolling(fn, intervalMs = Number(import.meta.env.VITE_POLL_INTERVAL) || 5000) {
  const isPolling = ref(false)
  let timer = null

  const run = async () => {
    try {
      await fn()
    } catch (error) {
      console.error('Erro no polling:', error)
    }
  }

  function start() {
    if (timer) return
    isPolling.value = true
    timer = setInterval(run, intervalMs)
    run()
  }

  function stop() {
    isPolling.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onUnmounted(stop)

  return { isPolling, start, stop }
}
