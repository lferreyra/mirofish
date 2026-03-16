<template>
  <div class="circular-fab-container">
    <!-- Overlay to close menu when clicking outside -->
    <div v-if="isOpen" class="fab-overlay" @click="isOpen = false"></div>

    <!-- Menu items (rendered behind FAB, animate outward) -->
    <transition-group name="fab-menu">
      <button
        v-if="isOpen"
        key="lang"
        class="fab-menu-item lang-item"
        @click="handleLangToggle"
        :title="locale === 'en' ? 'Switch to Malay' : 'Switch to English'"
      >
        A
      </button>
      <button
        v-if="isOpen"
        key="research"
        class="fab-menu-item research-item"
        @click="handleResearch"
        title="AI Research"
      >
        <span class="research-icon">&#9670;</span>
        <span v-if="seedTaskState.active" class="active-dot"></span>
      </button>
    </transition-group>

    <!-- Main FAB button -->
    <button
      class="fab-main"
      :class="{ open: isOpen, 'has-progress': isGenerating }"
      @click="toggleMenu"
    >
      <!-- SVG Progress ring -->
      <svg v-if="isGenerating" class="progress-ring" viewBox="0 0 52 52">
        <circle class="progress-ring-bg" cx="26" cy="26" r="23" />
        <circle
          class="progress-ring-fill"
          cx="26" cy="26" r="23"
          :style="{ strokeDashoffset: progressOffset }"
        />
      </svg>

      <!-- FAB content -->
      <span v-if="isGenerating" class="fab-text progress-text">
        {{ seedTaskState.progress }}%
      </span>
      <span v-else-if="!isOpen" class="fab-text">
        {{ locale === 'en' ? 'EN' : 'MS' }}
      </span>
      <span v-else class="fab-text fab-close">+</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { seedTaskState } from '../store/seedTask.js';
import { setLocale, state as i18nState } from '../i18n/index.js';

const isOpen = ref(false);

const locale = computed(() => i18nState.locale);

const isGenerating = computed(() => seedTaskState.status === 'generating');

const CIRCUMFERENCE = 2 * Math.PI * 23; // ~144.51

const progressOffset = computed(() => {
  return CIRCUMFERENCE * (1 - seedTaskState.progress / 100);
});

const toggleMenu = () => {
  isOpen.value = !isOpen.value;
};

const handleLangToggle = () => {
  setLocale(locale.value === 'en' ? 'ms' : 'en');
  isOpen.value = false;
};

const handleResearch = () => {
  seedTaskState.showModal = true;
  isOpen.value = false;
};
</script>

<style scoped>
.circular-fab-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
}

.fab-overlay {
  position: fixed;
  inset: 0;
  z-index: -1;
}

/* Main FAB button */
.fab-main {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #000;
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: background 0.2s ease, transform 0.2s ease;
  user-select: none;
  z-index: 2;
}

.fab-main:hover {
  background: #FF4500;
  transform: scale(1.1);
}

.fab-main.open:hover {
  transform: scale(1.1);
}

/* FAB text */
.fab-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  transition: transform 0.25s ease;
  line-height: 1;
}

.fab-close {
  font-size: 1.25rem;
  font-weight: 400;
  transform: rotate(45deg);
  display: inline-block;
}

.fab-main.open .fab-text {
  /* Rotated state for close icon */
}

.progress-text {
  font-size: 0.6rem;
  z-index: 1;
}

/* Progress ring */
.progress-ring {
  position: absolute;
  top: -2px;
  left: -2px;
  width: 52px;
  height: 52px;
  transform: rotate(-90deg);
  pointer-events: none;
}

.progress-ring-bg {
  fill: none;
  stroke: #333;
  stroke-width: 3;
}

.progress-ring-fill {
  fill: none;
  stroke: #FF4500;
  stroke-width: 3;
  stroke-dasharray: 144.51;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.3s ease;
}

.fab-main.has-progress {
  animation: fab-pulse 2s ease-in-out infinite;
}

@keyframes fab-pulse {
  0%, 100% {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }
  50% {
    box-shadow: 0 2px 16px rgba(255, 69, 0, 0.4);
  }
}

/* Menu items */
.fab-menu-item {
  position: absolute;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #fff;
  color: #000;
  border: 2px solid #000;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
  z-index: 1;
}

.fab-menu-item:hover {
  background: #FF4500;
  color: #fff;
  border-color: #FF4500;
  transform: scale(1.1);
}

/* Language button — upper-left diagonal */
.lang-item {
  bottom: 4px;
  right: 4px;
  transform: translate(-60px, -60px);
}

/* Research button — directly left */
.research-item {
  bottom: 4px;
  right: 4px;
  transform: translate(-75px, 0);
}

.research-icon {
  font-size: 0.9rem;
  line-height: 1;
}

/* Active dot indicator on research button */
.active-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 8px;
  height: 8px;
  background: #FF4500;
  border-radius: 50%;
  border: 1.5px solid #fff;
}

/* Menu item transitions */
.fab-menu-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.fab-menu-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fab-menu-enter-from,
.fab-menu-leave-to {
  opacity: 0;
}

.fab-menu-enter-from.lang-item,
.fab-menu-leave-to.lang-item {
  transform: translate(0, 0) !important;
}

.fab-menu-enter-from.research-item,
.fab-menu-leave-to.research-item {
  transform: translate(0, 0) !important;
}
</style>
