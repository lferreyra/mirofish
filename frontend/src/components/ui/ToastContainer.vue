<script setup>
import { useToast } from '../../composables/useToast'
const { toasts, remove } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast-${t.type}`"
          @click="remove(t.id)"
        >
          <span class="toast-icon">
            {{ t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : t.type === 'warn' ? '⚠️' : 'ℹ️' }}
          </span>
          <span class="toast-msg">{{ t.message }}</span>
          <button class="toast-close">×</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  min-width: 280px;
  max-width: 400px;
  cursor: pointer;
  pointer-events: all;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
  border: 1px solid;
  animation: none;
}
.toast-success { background: rgba(0,229,195,0.12); border-color: rgba(0,229,195,0.3); color: #00e5c3; }
.toast-error   { background: rgba(255,90,90,0.12);  border-color: rgba(255,90,90,0.3);  color: #ff5a5a; }
.toast-warn    { background: rgba(245,166,35,0.12);  border-color: rgba(245,166,35,0.3);  color: #f5a623; }
.toast-info    { background: rgba(124,111,247,0.12); border-color: rgba(124,111,247,0.3); color: #7c6ff7; }
.toast-icon  { font-size: 16px; flex-shrink: 0; }
.toast-msg   { flex: 1; line-height: 1.4; color: var(--text-primary); }
.toast-close { background: none; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer; padding: 0; line-height: 1; flex-shrink: 0; }

.toast-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.toast-leave-active { transition: all 0.2s ease; }
.toast-enter-from   { opacity: 0; transform: translateX(40px) scale(0.9); }
.toast-leave-to     { opacity: 0; transform: translateX(40px); }
</style>
