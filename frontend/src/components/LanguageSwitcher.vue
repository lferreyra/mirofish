<template>
  <div class="lang-switcher-wrapper" ref="wrapperRef">
    <button class="lang-trigger" @click.stop="toggleDropdown" :class="{ 'is-open': isOpen }">
      <span class="lang-icon">🌐</span>
      <span class="lang-label">{{ currentLangLabel }}</span>
      <span class="lang-chevron">▾</span>
    </button>
    
    <Transition name="dropdown-fade">
      <div v-if="isOpen" class="lang-dropdown">
        <div 
          v-for="lang in languages" 
          :key="lang.code" 
          class="lang-option"
          :class="{ 'is-active': locale === lang.code }"
          @click="selectLang(lang.code)"
        >
          <span class="option-code">{{ lang.code.toUpperCase() }}</span>
          <span class="option-name">{{ lang.name }}</span>
          <span v-if="locale === lang.code" class="active-dot">●</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';

const { locale } = useI18n();
const isOpen = ref(false);
const wrapperRef = ref(null);

const languages = [
  { code: 'zh', name: '中文' },
  { code: 'en', name: 'English' },
  { code: 'vi', name: 'Tiếng Việt' }
];

const currentLangLabel = computed(() => {
  return locale.value.toUpperCase();
});

const toggleDropdown = () => {
  isOpen.value = !isOpen.value;
};

const selectLang = (code) => {
  locale.value = code;
  isOpen.value = false;
};

const handleClickOutside = (event) => {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target)) {
    isOpen.value = false;
  }
};

onMounted(() => {
  window.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  window.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.lang-switcher-wrapper {
  position: relative;
  font-family: 'JetBrains Mono', monospace;
  margin-right: 20px;
}

.lang-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 6px 12px;
  color: #1a1a1a;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-width: 80px;
  justify-content: center;
}

.lang-trigger:hover {
  background: rgba(0, 0, 0, 0.08);
  border-color: var(--orange, #FF4500);
  transform: translateY(-1px);
}

.lang-trigger.is-open {
  background: rgba(255, 255, 255, 1);
  border-color: var(--orange, #FF4500);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.lang-icon {
  font-size: 14px;
}

.lang-chevron {
  font-size: 10px;
  opacity: 0.5;
  transition: transform 0.2s ease;
}

.is-open .lang-chevron {
  transform: rotate(180deg);
}

/* Dropdown Menu */
.lang-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 150px;
  background: #FFFFFF;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 6px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
  z-index: 1000;
}

.lang-option {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  gap: 10px;
  color: #444;
}

.lang-option:hover {
  background: rgba(255, 69, 0, 0.05);
  color: var(--orange, #FF4500);
}

.lang-option.is-active {
  background: rgba(255, 69, 0, 0.08);
  color: var(--orange, #FF4500);
}

.option-code {
  font-weight: 700;
  font-size: 12px;
  width: 24px;
}

.option-name {
  font-size: 13px;
  flex: 1;
}

.active-dot {
  font-size: 8px;
}

/* Animations */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: all 0.2s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
