<template>
  <div class="circular-fab-container">
    <!-- Overlay to close menu when clicking outside -->
    <div v-if="isOpen" class="fab-overlay" @click="isOpen = false"></div>

    <!-- Ring segment menu (SVG) -->
    <svg
      v-if="isOpen"
      class="ring-menu"
      viewBox="-5 -5 140 140"
      @click.self="isOpen = false"
    >
      <!-- Language segment: 270° → 310° (9:00 → 10:20) -->
      <path
        class="ring-segment"
        :class="{ hovered: hoveredSegment === 'lang' }"
        d="M 10 100 A 90 90 0 0 1 31.1 42.1 L 57.9 64.6 A 55 55 0 0 0 45 100 Z"
        @mouseenter="hoveredSegment = 'lang'"
        @mouseleave="hoveredSegment = null"
        @click="handleLangToggle"
      />
      <text
        class="ring-label"
        x="32" y="78"
        @mouseenter="hoveredSegment = 'lang'"
        @click="handleLangToggle"
      >{{ locale === 'en' ? 'EN' : 'MS' }}</text>

      <!-- Research segment: 316° → 356° (10:32 → 11:52) -->
      <path
        class="ring-segment"
        :class="{ hovered: hoveredSegment === 'research' }"
        d="M 37.5 35.3 A 90 90 0 0 1 93.7 10.2 L 96.2 45.1 A 55 55 0 0 0 61.8 60.4 Z"
        @mouseenter="hoveredSegment = 'research'"
        @mouseleave="hoveredSegment = null"
        @click="handleResearch"
      />
      <text
        class="ring-label ring-label-sm"
        x="70" y="38"
        @mouseenter="hoveredSegment = 'research'"
        @click="handleResearch"
      >&#9670; RES</text>
      <!-- Active dot when seed task is running -->
      <circle
        v-if="seedTaskState.active"
        cx="84" cy="22" r="3.5"
        class="active-dot"
      />
    </svg>

    <!-- Main FAB button -->
    <button
      class="fab-main"
      :class="{
        open: isOpen,
        'has-progress': isGenerating,
        'is-done': isDone,
      }"
      @click="toggleMenu"
    >
      <!-- Progress ring (generating) -->
      <svg v-if="isGenerating && !isOpen" class="progress-ring" viewBox="0 0 56 56">
        <circle class="progress-ring-bg" cx="28" cy="28" r="25" />
        <circle
          class="progress-ring-fill"
          cx="28" cy="28" r="25"
          :style="{ strokeDashoffset: progressOffset }"
        />
      </svg>

      <!-- Done ring -->
      <svg v-if="isDone && !isOpen" class="done-ring" viewBox="0 0 56 56">
        <circle cx="28" cy="28" r="25" fill="none" stroke="#4CAF50" stroke-width="2.5" />
      </svg>

      <!-- FAB content -->
      <span v-if="isGenerating && !isOpen" class="fab-text progress-text">
        {{ seedTaskState.progress }}%
      </span>
      <span v-else-if="isDone && !isOpen" class="fab-text done-text">&#10003;</span>
      <span v-else-if="isOpen" class="fab-text fab-close">+</span>
      <span v-else class="fab-text fab-diamond">&#9670;</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { seedTaskState } from '../store/seedTask.js';
import { setLocale, state as i18nState } from '../i18n/index.js';

const isOpen = ref(false);
const hoveredSegment = ref(null);

const locale = computed(() => i18nState.locale);

const isGenerating = computed(() => seedTaskState.status === 'generating');
const isDone = computed(() => seedTaskState.status === 'completed');

const CIRCUMFERENCE = 2 * Math.PI * 25; // ~157.08

const progressOffset = computed(() => {
  return CIRCUMFERENCE * (1 - seedTaskState.progress / 100);
});

const toggleMenu = () => {
  isOpen.value = !isOpen.value;
  hoveredSegment.value = null;
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

/* Ring segment menu */
.ring-menu {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 180px;
  height: 180px;
  z-index: 1;
  pointer-events: none;
}

.ring-segment {
  fill: #333;
  cursor: pointer;
  pointer-events: all;
  transition: fill 0.15s ease;
}

.ring-segment.hovered,
.ring-segment:hover {
  fill: #FF4500;
}

.ring-label {
  fill: #fff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  text-anchor: middle;
  pointer-events: all;
  cursor: pointer;
}

.ring-label-sm {
  font-size: 9px;
}

.active-dot {
  fill: #FF4500;
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
  transition: background 0.2s ease;
  user-select: none;
  z-index: 2;
}

.fab-main:hover {
  background: #1a1a1a;
}

.fab-main.open {
  background: #000;
}

/* FAB text */
.fab-text {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  line-height: 1;
}

.fab-diamond {
  font-size: 1.1rem;
  color: #FF4500;
}

.fab-close {
  font-size: 1.25rem;
  font-weight: 400;
  color: #FF4500;
  transform: rotate(45deg);
  display: inline-block;
}

.progress-text {
  font-size: 0.6rem;
  color: #FF4500;
  z-index: 1;
}

.done-text {
  font-size: 1rem;
  color: #4CAF50;
}

/* Progress ring */
.progress-ring {
  position: absolute;
  top: -4px;
  left: -4px;
  width: 56px;
  height: 56px;
  transform: rotate(-90deg);
  pointer-events: none;
}

.progress-ring-bg {
  fill: none;
  stroke: #333;
  stroke-width: 2.5;
}

.progress-ring-fill {
  fill: none;
  stroke: #FF4500;
  stroke-width: 2.5;
  stroke-dasharray: 157.08;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.3s ease;
}

/* Done ring */
.done-ring {
  position: absolute;
  top: -4px;
  left: -4px;
  width: 56px;
  height: 56px;
  pointer-events: none;
}

/* Pulse animation when generating */
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
</style>
