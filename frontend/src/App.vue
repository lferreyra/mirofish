<template>
  <router-view />
</template>

<script setup>
// Uses Vue Router for page management
</script>

<style>
/* Global style reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Geist Sans', 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--foreground);
  background-color: var(--background);
}

/* Scrollbar styles */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--border);
}

::-webkit-scrollbar-thumb {
  background: var(--muted-foreground);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}

/* Global button styles */
button {
  font-family: inherit;
}
</style>
