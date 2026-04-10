# Plan: Translate Chinese → English (UI-visible + LLM Prompts Only)

## Context
The codebase has an i18n system (`locales/zh.json` + `locales/en.json`) shared between frontend (vue-i18n) and backend (`t()` function in `utils/locale.py`). The `en.json` already has complete English translations. However, **two categories of Chinese remain hardcoded in source code**:
1. **LLM prompts** — Chinese text sent directly to LLMs (system prompts, user prompt templates, tool descriptions)
2. **Hardcoded UI strings** — Chinese in backend API responses and frontend `index.html` that bypass the i18n system

Comments are left as-is per user instruction.

---

## Step 1: `backend/app/services/ontology_generator.py` (LLM Prompts — opus) ✅ DONE

**What to translate:**
- `ONTOLOGY_SYSTEM_PROMPT` (lines 31-174) — ~144 lines of Chinese instructions about knowledge graph ontology design for social media opinion simulation. Change "使用中文" → "Use English".
- `_build_user_message` (lines 253-279) — User prompt template with Chinese section headers ("模拟需求", "文档内容", "额外说明") and 5 mandatory rules about entity types.

**What NOT to touch:** Comments, variable names, JSON format specs.

**Verify:** `python -m py_compile backend/app/services/ontology_generator.py`

---

## Step 2: `backend/app/services/oasis_profile_generator.py` (LLM Prompts — opus) ✅ DONE

**What to translate:**
- `_get_system_prompt` (line 674) — System prompt: "你是社交媒体用户画像生成专家..."
- `_build_individual_persona_prompt` (lines 690-724) — Individual persona generation prompt with 8+ field descriptions
- `_build_group_persona_prompt` (lines 739-772) — Institution/group persona prompt
- `_build_entity_context` (lines 414-487) — Chinese section headers injected into prompts: "实体属性", "相关事实和关系", "关联实体信息", "Zep检索到的事实信息", "Zep检索到的相关节点"
- Fallback persona text (lines 557, 654, 669): `f"{entity_name}是一个{entity_type}。"`
- Line 714: "国家（使用中文，如"中国"）" → "Country (e.g., 'China')"

**What NOT to touch:** Mapping dicts like `{"男": "male", "女": "female"}` — these are intentional translations.

**Verify:** `python -m py_compile backend/app/services/oasis_profile_generator.py`

---

## Step 3: `backend/app/services/report_agent.py` (LLM Prompts — opus, LARGEST) ✅ DONE

**What to translate (14 prompt locations):**
1. `TOOL_DESC_INSIGHT_FORGE` (lines 475-491) — Deep insight tool description
2. `TOOL_DESC_PANORAMA_SEARCH` (lines 493-508) — Panoramic search tool description
3. `TOOL_DESC_QUICK_SEARCH` (lines 510-520) — Quick search tool description
4. `TOOL_DESC_INTERVIEW_AGENTS` (lines 522-547) — Agent interview tool description
5. `PLAN_SYSTEM_PROMPT` (lines 551-588) — Report planning system prompt (~38 lines)
6. `PLAN_USER_PROMPT_TEMPLATE` (lines 590-610) — Outline planning user prompt
7. `SECTION_SYSTEM_PROMPT_TEMPLATE` (lines 614-766) — **Largest block (~153 lines)**: section writing with ReACT workflow, format rules
8. `SECTION_USER_PROMPT_TEMPLATE` (lines 768-791) — Per-section generation instructions
9. `REACT_OBSERVATION_TEMPLATE` (lines 795-805) — Tool result observation
10. `REACT_INSUFFICIENT_TOOLS_MSG` / `_ALT` (lines 807-815) — Insufficient tool call warnings
11. `REACT_TOOL_LIMIT_MSG` (lines 817-820) — Tool limit reached warning
12. `REACT_UNUSED_TOOLS_HINT` + `REACT_FORCE_FINAL_MSG` (lines 822-824)
13. `CHAT_SYSTEM_PROMPT_TEMPLATE` (lines 828-854) — Chat mode system prompt
14. `CHAT_OBSERVATION_SUFFIX` (line 856) + Conflict resolution (lines 1414-1419)

**Verify:** `python -m py_compile backend/app/services/report_agent.py`

---

## Step 4: `backend/app/services/simulation_config_generator.py` (LLM Prompts — opus)

**What to translate (6 locations):**
1. Time config system prompt (line 601) — "你是社交媒体模拟专家..."
2. Time config user prompt (lines 556-599) — Chinese timezone/activity rules + JSON format
3. Event config system prompt (line 717) — "你是舆论分析专家..."
4. Event config user prompt (lines 688-715) — Event config with hot topics
5. Agent config system prompt (line 880) — "你是社交媒体行为分析专家..."
6. Agent config user prompt (lines 844-878) — Per-entity activity config with entity-type-specific rules

**Key change:** "中国人作息习惯" → "typical daily activity patterns"

**Verify:** `python -m py_compile backend/app/services/simulation_config_generator.py`

---

## Step 5: `backend/app/services/zep_tools.py` (LLM Prompts — opus)

**What to translate (12 locations):**
1. Sub-question system prompt (lines 1104-1110)
2. Sub-question user prompt (lines 1112-1120)
3. Fallback sub-queries (lines 1138-1143)
4. Agent selection system prompt (lines 1580-1592)
5. Agent selection user prompt (lines 1594-1603)
6. Interview question system prompt (lines 1644-1654)
7. Interview question user prompt (lines 1656-1662)
8. Interview question fallback (lines 1673, 1677-1681)
9. `INTERVIEW_PROMPT_PREFIX` (lines 1352-1361) — Also referenced in `simulation.py` line 25
10. Interview summary system prompt (lines 1699-1713)
11. Interview summary user prompt (lines 1715-1720)

**Verify:** `python -m py_compile backend/app/services/zep_tools.py`

---

## Step 6: `backend/app/api/graph.py` (Hardcoded UI Strings)

**What to translate:** Replace ~32 hardcoded Chinese strings in `jsonify()` responses with `t()` calls using existing keys from `en.json`. The keys already exist in `locales/en.json` under `api.*` and `progress.*`.

Examples:
- Line 47: `f"项目不存在: {project_id}"` → `t('api.projectNotFound', id=project_id)`
- Line 86: `f"项目已删除: {project_id}"` → `t('api.projectDeleted', id=project_id)`
- Lines 430-551: Task progress messages like `"初始化图谱构建服务..."` → `t('progress.initGraphService')`

**Verify:** `python -m py_compile backend/app/api/graph.py`

---

## Step 7: `backend/app/api/report.py` (Hardcoded UI Strings)

**What to translate:** 4 hardcoded Chinese strings:
- Line 119: `f"报告不存在: {requested_report_id}"` → `t('api.reportNotFound', id=requested_report_id)`
- Line 124: `"report_id 与 simulation_id 不匹配"` → English equivalent
- Line 133: `"报告已存在"` → `t('api.reportAlreadyExists')`
- Line 140: `"只有 failed 状态的报告才能断点续跑"` → English equivalent

**Verify:** `python -m py_compile backend/app/api/report.py`

---

## Step 8: `backend/app/api/simulation.py` (Hardcoded UI Strings)

**What to translate:**
- Line 25: `INTERVIEW_PROMPT_PREFIX = "结合你的人设..."` → English (this is also an LLM prompt)
- Lines 263, 285, 350, 356: `"reason"` field strings in `_check_simulation_prepared`
- Line 954: `"未知文件"` → English

**Verify:** `python -m py_compile backend/app/api/simulation.py`

---

## Step 9: `frontend/index.html` (UI Strings)

**What to translate (2 strings):**
- Line 11: `<meta name="description" content="MiroFish - 社交媒体舆论模拟系统" />` → `"MiroFish - Social Media Opinion Simulation System"`
- Line 12: `<title>MiroFish - 预测万物</title>` → `<title>MiroFish - Predict Everything</title>`

---

## Step 10: `frontend/src/components/Step4Report.vue` (Report Parsing Regex)

**What to translate:** Chinese section headers used in regex patterns that parse backend-generated report content. These regex patterns match Chinese text from LLM output (which will now be in English after Step 3), so they must be updated to match English headers.

Examples:
- `"分析问题:"` → `"Analysis Question:"`
- `"预测场景:"` → `"Prediction Scenario:"`
- `"关键Facts"` → `"Key Facts"`
- `"采访主题:"` → `"Interview Topic:"`
- etc. (~30 regex patterns)

**Note:** This step MUST happen after Step 3 (report_agent.py) because the regexes need to match the new English output from the LLM.

---

## Execution Rules

1. **Sequential execution** — Steps 1→10 in order. No parallel agents.
2. **Opus model** for Steps 1-5 (LLM prompts require nuanced translation). **Sonnet** for Steps 6-10.
3. **Direct Edit only** — No helper scripts.
4. **Verify each Python file** with `py_compile` after editing.
5. **Preserve all:** JSON format specs, variable placeholders `{like_this}`, structural elements, function/class/variable names, URLs, package names.
6. **Leave as-is:** Comments (Chinese comments stay Chinese).

## Verification (After All Steps)

```bash
# Check remaining Chinese in LLM prompt areas and UI strings (comments OK)
python -m py_compile backend/app/services/ontology_generator.py
python -m py_compile backend/app/services/oasis_profile_generator.py
python -m py_compile backend/app/services/report_agent.py
python -m py_compile backend/app/services/simulation_config_generator.py
python -m py_compile backend/app/services/zep_tools.py
python -m py_compile backend/app/api/graph.py
python -m py_compile backend/app/api/report.py
python -m py_compile backend/app/api/simulation.py

# Review full diff
git diff --stat
```

## Summary

| Step | File | Category | Model | Size |
|------|------|----------|-------|------|
| 1 | ontology_generator.py | LLM Prompts | opus | ~170 lines |
| 2 | oasis_profile_generator.py | LLM Prompts | opus | ~120 lines |
| 3 | report_agent.py | LLM Prompts | opus | ~300 lines |
| 4 | simulation_config_generator.py | LLM Prompts | opus | ~130 lines |
| 5 | zep_tools.py | LLM Prompts | opus | ~100 lines |
| 6 | graph.py API | UI Strings | sonnet | ~32 strings |
| 7 | report.py API | UI Strings | sonnet | ~4 strings |
| 8 | simulation.py API | UI Strings | sonnet | ~5 strings |
| 9 | index.html | UI Strings | sonnet | 2 strings |
| 10 | Step4Report.vue | Report Parsing | sonnet | ~30 regexes |
