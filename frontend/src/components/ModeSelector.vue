<template>
  <div class="mode-selector">
    <div class="selector-header">
      <span class="selector-label">SELECT SIMULATION MODE</span>
      <p class="selector-hint">Choose how you want to run your impact analysis</p>
    </div>

    <div class="mode-cards">
      <!-- Public Mode -->
      <button
        class="mode-card"
        :class="{ 'is-selected': selected === 'public' }"
        @click="select('public')"
      >
        <div class="card-icon">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        </div>
        <div class="card-body">
          <div class="card-title">Public Opinion</div>
          <div class="card-subtitle">Twitter / Reddit</div>
          <p class="card-desc">Simulate how a decision, event, or message propagates through open social networks.</p>
          <div class="card-tags">
            <span class="tag">Social Media</span>
            <span class="tag">Public Sentiment</span>
            <span class="tag">Virality</span>
          </div>
        </div>
        <div class="card-check">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      </button>

      <!-- Private Impact Mode -->
      <button
        class="mode-card mode-card--private"
        :class="{ 'is-selected': selected === 'private' }"
        @click="select('private')"
      >
        <div class="card-icon">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <div class="card-body">
          <div class="card-title">Private Impact</div>
          <div class="card-subtitle">Closed Relational Network</div>
          <p class="card-desc">Simulate how a private decision propagates through a relational network — employees, clients, partners.</p>
          <div class="card-tags">
            <span class="tag">Org Network</span>
            <span class="tag">Decision Impact</span>
            <span class="tag">Confidential</span>
          </div>
        </div>
        <div class="card-check">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['mode-selected'])

const selected = ref(null)

const select = (mode) => {
  selected.value = mode
  emit('mode-selected', mode)
}
</script>

<style scoped>
.mode-selector {
  padding: 0;
}

.selector-header {
  margin-bottom: 20px;
}

.selector-label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: #999;
  margin-bottom: 6px;
}

.selector-hint {
  font-size: 13px;
  color: #555;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 20px;
  border: 1.5px solid #E0E0E0;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s;
  width: 100%;
  gap: 14px;
}

.mode-card:hover {
  border-color: #000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.mode-card.is-selected {
  border-color: #000;
  background: #FAFAFA;
}

.mode-card--private:hover,
.mode-card--private.is-selected {
  border-color: #1A1A1A;
  background: #F8F8F8;
}

.card-icon {
  color: #333;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #000;
  margin-bottom: 2px;
  letter-spacing: 0.02em;
}

.card-subtitle {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #888;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.card-desc {
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  margin-bottom: 10px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  font-size: 10px;
  font-weight: 500;
  color: #666;
  background: #F0F0F0;
  border-radius: 2px;
  padding: 2px 6px;
  letter-spacing: 0.04em;
}

.card-check {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #000;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: scale(0.7);
  transition: opacity 0.15s, transform 0.15s;
}

.mode-card.is-selected .card-check {
  opacity: 1;
  transform: scale(1);
}

@media (max-width: 640px) {
  .mode-cards {
    grid-template-columns: 1fr;
  }
}
</style>
