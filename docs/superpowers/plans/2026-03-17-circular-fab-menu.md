# Circular FAB Menu + Background Seed Recovery

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the simple language toggle FAB with a circular menu that provides quick access to language switching and seed generation recovery. When seed generation is running in the background, the FAB shows a progress indicator and lets the user reopen the seed modal.

**Architecture:** Replace `lang-fab` div in App.vue with a `CircularFab.vue` component. The FAB has two states: closed (shows progress ring if seed is running, or language code if idle) and open (radial menu with 2-3 action buttons). Seed generation state is stored in a reactive global store so it survives modal close/reopen.

**Tech Stack:** Vue 3 Composition API, CSS animations for radial menu, reactive store for seed task state.

---

## Bug Fix: Seed modal close loses progress

### Current problem
When user closes the seed modal during generation, the task keeps running on the backend but the frontend loses track of it. There's no way to reopen the modal or see the progress.

### Fix
1. Store the active seed task state (taskId, categories, progress, completed files) in a reactive global store (`frontend/src/store/seedTask.js`)
2. The SeedGeneratorModal reads/writes from this store instead of local refs
3. Closing the modal does NOT cancel the task — it just hides the modal
4. The FAB shows a progress ring when a seed task is running
5. Clicking the FAB (or the seed menu item) reopens the modal with current progress

---

## Chunk 1: Seed Task Global Store

### Task 1: Create seed task store

**Files:**
- Create: `frontend/src/store/seedTask.js`

- [ ] **Step 1: Create the reactive store**

```javascript
import { reactive } from 'vue';

const state = reactive({
  active: false,
  taskId: null,
  prompt: '',
  categories: [],
  depth: 'quick',
  status: 'idle', // idle | analyzing | generating | completed | failed
  progress: 0,
  currentFile: '',
  completedFiles: [],
  error: null,
});

export function startSeedTask(taskId, prompt, categories, depth) {
  state.active = true;
  state.taskId = taskId;
  state.prompt = prompt;
  state.categories = categories;
  state.depth = depth;
  state.status = 'generating';
  state.progress = 0;
  state.currentFile = '';
  state.completedFiles = [];
  state.error = null;
}

export function updateSeedProgress(data) {
  state.status = data.status;
  state.progress = data.progress;
  state.currentFile = data.current_file || '';
  state.completedFiles = data.completed_files || [];
  if (data.error) state.error = data.error;
  if (data.status === 'completed' || data.status === 'failed') {
    state.active = data.status !== 'failed';
  }
}

export function resetSeedTask() {
  state.active = false;
  state.taskId = null;
  state.status = 'idle';
  state.progress = 0;
  state.currentFile = '';
  state.completedFiles = [];
  state.error = null;
}

export { state as seedTaskState };
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/seedTask.js
git commit -m "feat(seed): add global reactive store for seed task state"
```

---

### Task 2: Update SeedGeneratorModal to use global store

**Files:**
- Modify: `frontend/src/components/SeedGeneratorModal.vue`

- [ ] **Step 1: Refactor modal to use seedTask store**

Key changes:
- Import `seedTaskState`, `startSeedTask`, `updateSeedProgress`, `resetSeedTask` from store
- Replace local progress refs with store state
- When generation starts, call `startSeedTask()` with taskId
- Poll loop updates store via `updateSeedProgress()`
- When modal closes, do NOT stop the poll — let it continue in background
- When modal reopens, read current state from store and resume display
- Add `onMounted` check: if store has an active task, resume polling

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SeedGeneratorModal.vue
git commit -m "feat(seed): use global store so modal can close/reopen without losing progress"
```

---

## Chunk 2: Circular FAB Menu

### Task 3: Create CircularFab component

**Files:**
- Create: `frontend/src/components/CircularFab.vue`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Create CircularFab.vue**

The component has two states:

**Closed state:**
- Black circle (48px), bottom-right corner, z-index 9999
- If seed task is running: shows circular progress ring (SVG) around the FAB with percentage
- If idle: shows current language code (EN/MS)

**Open state (click to toggle):**
- FAB rotates 45° (becomes an X to close)
- 2-3 action buttons animate outward in an arc:
  - 🌐 **Language** (top-left of arc) — toggles EN/MS on click
  - 🔬 **Research** (left of arc) — opens seed modal. Shows dot indicator if task is running
  - Optionally: ⚙️ **Settings** (placeholder for future)
- Click outside or click FAB again to close

**Progress ring (when seed is generating):**
- SVG circle stroke-dasharray animation
- Shows progress percentage in the center
- Pulses gently to indicate activity

- [ ] **Step 2: Replace lang-fab in App.vue**

Remove the `lang-fab` div and its CSS from App.vue. Replace with:
```vue
<CircularFab />
```

Import CircularFab and wire it up. The component internally imports seedTaskState and i18n functions.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CircularFab.vue frontend/src/App.vue
git commit -m "feat: replace language FAB with circular menu (language + seed research)"
```

---

## Chunk 3: Integration

### Task 4: Wire up Home.vue to reopen modal

**Files:**
- Modify: `frontend/src/views/Home.vue`

- [ ] **Step 1: Update Home.vue**

- When seed files are ready (from background task), show notification or auto-populate upload zone
- If user returns to home page with completed seed task, show files in upload zone
- Read `seedTaskState` to check if there are completed files to use

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/Home.vue
git commit -m "feat(seed): auto-recover seed files when returning to home page"
```

---

### Task 5: Test and push

- [ ] **Step 1: Test the full flow**

1. Type a prompt, click Launch Engine (no files)
2. Modal appears with categories → start research
3. Close modal while generating → FAB shows progress ring
4. Click FAB → Research button → modal reopens with current progress
5. Wait for completion → files appear in upload zone
6. Click Launch Engine → normal flow

- [ ] **Step 2: Test language toggle via FAB menu**

1. Click FAB → Language button → switches EN/MS
2. All UI text updates

- [ ] **Step 3: Push**

```bash
git push origin main
```
