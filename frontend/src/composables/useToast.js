// composables/useToast.js
// Sistema global de notificações toast
import { ref } from 'vue'

const toasts = ref([])
let nextId = 0

export function useToast() {
  function add(message, type = 'info', duration = 4000) {
    const id = ++nextId
    toasts.value.push({ id, message, type, visible: true })
    setTimeout(() => remove(id), duration)
  }

  function remove(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return {
    toasts,
    success: (msg, dur) => add(msg, 'success', dur),
    error:   (msg, dur) => add(msg, 'error', dur || 6000),
    info:    (msg, dur) => add(msg, 'info', dur),
    warn:    (msg, dur) => add(msg, 'warn', dur || 5000),
    remove,
  }
}
