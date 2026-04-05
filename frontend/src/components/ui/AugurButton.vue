<script setup>
defineProps({
  variant: { type: String, default: 'primary' },
  loading: { type: Boolean, default: false },
  type: { type: String, default: 'button' }
})
</script>

<template>
  <button :type="type" class="btn" :class="variant" :disabled="loading">
    <span v-if="loading" class="spinner" />
    <slot />
  </button>
</template>

<style scoped>
.btn { border-radius:var(--r-sm); padding:9px 14px; border:1px solid transparent; cursor:pointer; font-weight:600; display:inline-flex; gap:8px; align-items:center; }
.primary { background:var(--accent); color:#09090f; }
.ghost { background:transparent; color:var(--text-primary); border-color:var(--border-md); }
.danger { background:rgba(255,90,90,.14); border-color:rgba(255,90,90,.4); color:var(--danger); }
.spinner { width:14px; height:14px; border:2px solid rgba(0,0,0,.2); border-top-color:#000; border-radius:50%; animation:spin .9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg);} }
</style>
