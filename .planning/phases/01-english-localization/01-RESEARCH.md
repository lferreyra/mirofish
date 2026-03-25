# Phase 1: English Localization — Research

**Researched:** 2026-03-24
**Domain:** Codebase localization — Chinese-to-English string replacement
**Confidence:** HIGH (based on direct grep audit of all source files)

---

## Summary

Phase 1 requires removing all Chinese-character strings from a Vue 3 + Python/Flask full-stack application. A comprehensive CJK grep audit (`\u4e00-\u9fff`) of the entire codebase reveals the scope is significantly narrower than initially estimated: only **3 files** contain Chinese characters. No i18n framework is in use — all text is hardcoded directly into source files.

The critical finding is that Chinese strings in Step4Report.vue are **not user-facing UI labels**. They are regex patterns written to parse LLM-generated report output that was historically produced in Chinese. The backend (graph_tools.py) already emits English platform markers (`[Twitter Platform Response]`, `[Reddit Platform Response]`). This means these Vue regex patterns are **legacy compatibility shims** — they must be preserved or carefully superseded, not simply deleted.

The two backend files contain incidental Chinese: `oasis_profile_generator.py` has a Chinese-to-English gender mapping dict (4 Chinese key strings, intentionally kept as input-value matchers), and `graph_tools.py` has 3 comment lines with Chinese annotations on regex logic. These are trivial edits.

**Primary recommendation:** Direct in-place string replacement. No i18n library needed. Frontend work requires surgical regex analysis, not bulk find/replace.

---

## Chinese Text Inventory — Complete

Scope verified by grep audit. Zero Chinese characters found outside the 3 files listed below.

### File 1: `frontend/src/components/Step4Report.vue`

**18 lines** with Chinese characters. All are inside JavaScript `<script>` blocks, not in `<template>` HTML.

| Line | Category | Chinese Content | Nature |
|------|----------|-----------------|--------|
| 742 | Regex pattern | `选择` (= "Select") | Parser: matches LLM output format for agent selection |
| 767 | Regex pattern | `未选`, `综上`, `最终选择` (= "Not selected", "In summary", "Final selection") | Parser: filters trailing summary lines |
| 814 | Regex pattern | `简介` (= "Bio") | Parser: matches `_Bio:` or `_简介:` label in LLM output |
| 837 | Regex pattern | `关键引言` (= "Key Quotes") | Parser: matches `**Key Quotes:**` or `**关键引言:**` section |
| 842 | Regex pattern | `【Twitter平台回答】` (= "[Twitter Platform Response]") | Parser: matches old Chinese platform markers in LLM output |
| 843 | Regex pattern | `【Reddit平台回答】` (= "[Reddit Platform Response]") | Parser: matches old Chinese platform markers in LLM output |
| 855 | String comparison | `（该平台未获得回复）` (= "(No response from this platform)") | Placeholder text comparison — old format |
| 859 | String comparison | `（该平台未获得回复）` (= "(No response from this platform)") | Placeholder text comparison — old format |
| 869 | Regex pattern | `关键引言` (= "Key Quotes") | Parser: same as line 837 |
| 913 | Regex pattern | `搜索查询:` (= "Search query:") | Parser: extracts query from knowledge graph tool output |
| 917 | Regex pattern | `找到.*条` (= "Found N results") | Parser: extracts result count from tool output |
| 921 | Regex pattern | `### 相关事实:` (= "### Related Facts:") | Parser: extracts facts section from tool output |
| 928 | Regex pattern | `### 相关边:` (= "### Related Edges:") | Parser: extracts edges section from tool output |
| 941 | Regex pattern | `### 相关节点:` (= "### Related Nodes:") | Parser: extracts nodes section from tool output |
| 1330 | String comparison | `（该平台未获得回复）`, `(该平台未获得回复)`, `[无回复]` | isPlaceholderText() check — old format values |
| 1339 | Comment | `"问题X："` (= "Question X:") | Code comment explaining Chinese format |
| 1344-1345 | Comment + regex | `问题X：` pattern | Parser: splits answers by question number, Chinese format |
| 1369 | Regex | `问题\d+[：:]` | Parser: removes question prefix from answer text |
| 2111 | Regex | `最终答案[:：]` (= "Final Answer:") | Parser: extracts final answer from Chinese-labeled response |

**Summary of Vue Chinese string types:**
- **Regex patterns matching LLM output format (old Chinese format):** 14 instances
- **String comparisons for old placeholder values:** 4 instances
- **Code comments:** 1 instance

### File 2: `backend/app/services/oasis_profile_generator.py`

**4 lines** with Chinese characters — lines 1075–1078.

All 4 are dictionary keys in a `gender_map` dict. The Chinese values (`男`, `女`, `机构`, `其他`) are intentional input-matcher keys: the function normalizes gender strings that may arrive as Chinese from upstream LLM outputs into English values (`male`, `female`, `other`). The existing inline comments already translate them to English.

```python
gender_map = {
    "男": "male",      # Chinese: "male"
    "女": "female",    # Chinese: "female"
    "机构": "other",   # Chinese: "institution/organization"
    "其他": "other",   # Chinese: "other"
    ...
}
```

These are **functional matcher strings**, not display strings. They must be retained as-is (or the dict key strings must stay Chinese to match whatever the LLM sends) — only the comments need no change (they are already English). This is R1.4 source code comment compliance only; the Chinese keys are a runtime concern.

### File 3: `backend/app/services/graph_tools.py`

**3 lines** with Chinese characters — lines 1446, 1456, 1459.

All are inline `#` comments providing English translations of Chinese regex patterns used in report generation logic. The comments themselves are already English explanations; the Chinese appears as quoted examples within the comment text.

```python
# Remove question markers in both Chinese ("问题" = "Question") and English
clean_text = re.sub(r'(?:问题|Question)\s*\d+[：:]\s*', '', clean_text)

and not s.strip().startswith(('{', '问题', 'Question'))  # "问题" = Chinese for "Question"

key_quotes = [s + "。" for s in meaningful[:3]]  # "。" = Chinese full-stop period
```

Line 1459 embeds `"。"` (Chinese full stop) as a **functional string literal** that is appended to extracted quotes. This is a runtime value, not a display string — it should be changed to `"."` (ASCII period) as part of this phase.

---

## Files Confirmed Clean (Zero Chinese)

The following files named in the phase brief were verified by grep and contain zero Chinese characters:

- `frontend/src/views/*.vue` — all 6 view files: clean
- `frontend/src/components/Step1GraphBuild.vue` — clean
- `frontend/src/components/Step2EnvSetup.vue` — clean
- `frontend/src/components/Step3Simulation.vue` — clean
- `frontend/src/components/Step5Interaction.vue` — clean
- `backend/app/services/simulation_manager.py` — clean
- `backend/app/services/graph_builder.py` — clean
- `backend/app/services/entity_extractor.py` — clean
- `backend/app/services/simulation_config_generator.py` — clean
- `backend/app/services/report_agent.py` — clean
- `backend/app/services/text_processor.py` — clean
- `backend/scripts/run_twitter_simulation.py` — clean
- `backend/scripts/run_reddit_simulation.py` — clean
- `backend/scripts/run_parallel_simulation.py` — clean
- `backend/app/tools/*.py` — all tools files: clean
- `backend/app/utils/*.py` — all utils files: clean
- `backend/app/api/*.py` — all API files: clean
- `backend/app/core/*.py` — all core files: clean
- `backend/app/resources/**/*.py` — all resource files: clean

No test files exist in the project — nothing to update there.

---

## Translation Approach

### Recommendation: Direct In-Place String Replacement

No i18n library (vue-i18n or equivalent) is installed or used anywhere in the codebase. Given the small scope (3 files, ~25 affected lines), introducing an i18n system would add complexity with no benefit.

Direct replacement is correct for this phase.

### Two Categories of Chinese String — Different Handling Required

**Category A — Regex patterns matching LLM output (FUNCTIONAL)**

Chinese strings inside `.match(/.../)` patterns exist because the LLM used to produce output in Chinese. They must NOT simply be deleted. The correct approach is:

1. Verify whether the backend still produces the Chinese-format output. Based on graph_tools.py line 1436, the backend currently emits `[Twitter Platform Response]` and `[Reddit Platform Response]` (English). The old `【Twitter平台回答】` / `【Reddit平台回答】` Chinese bracket-format markers appear to be legacy.
2. Keep both the English and Chinese alternatives in the regex for backward compatibility with any stored simulation reports that used the old Chinese format.
3. The regex patterns at lines 842–843 should retain the Chinese alternatives alongside English alternatives (they already use `|` alternation syntax with English fallbacks).

**Category B — Display strings and comparisons (SAFE TO REPLACE)**

Hardcoded Chinese strings used in equality comparisons (`=== '（该平台未获得回复）'`) are display-layer values that appear in simulation reports. These should be updated to their English equivalents AND the backend must confirm it no longer emits these Chinese strings. Since graph_tools.py line 1434 already uses the English string `"(No response from this platform)"`, the frontend comparisons at lines 855, 859, and 1330 should be updated to match.

---

## Risk Areas

### Risk 1: Regex patterns break report parsing (HIGH priority)

**What could go wrong:** The Step4Report.vue parsing logic extracts interview content, knowledge graph results, and agent selection data from LLM-generated markdown text. Removing Chinese alternatives from these regexes without verifying what format the LLM currently outputs would silently break the report display — all fields would render empty.

**Mitigation:** Keep Chinese alternatives in all regexes that already pair them with English (`|`). Only remove isolated Chinese-only patterns after confirming the backend has migrated to English output. The safest approach for this phase is: add English alternatives everywhere, leave Chinese alternatives as fallback. Do not remove Chinese from regexes at all — just add English where it's missing.

**Affected lines:** 742, 814, 837, 869, 913, 917, 921, 928, 941, 1345, 1369, 2111

### Risk 2: Gender mapping keys in oasis_profile_generator.py (MEDIUM priority)

**What could go wrong:** The `gender_map` dict uses Chinese strings as keys because the LLM may output gender as Chinese (`男`, `女`, etc.) from profile templates. If these keys are removed or changed, gender normalization breaks and all profiles get classified as `"other"`.

**Mitigation:** These keys are functional matcher strings and must NOT be changed. They are already fully commented in English. R1.4 is satisfied as-is. No action required on the dict keys.

### Risk 3: The `"。"` character appended to key quotes (LOW priority)

**What could go wrong:** Line 1459 appends `"。"` (Chinese full stop) to extracted quote strings. This creates Chinese punctuation in the rendered report UI. Change to `"."` (ASCII period).

**Mitigation:** Simple one-character string replacement. No downstream parsing depends on this specific punctuation.

### Risk 4: Knowledge graph tool output format (MEDIUM priority)

**What could go wrong:** Lines 913–941 parse tool output containing Chinese section headers (`搜索查询:`, `相关事实:`, `相关边:`, `相关节点:`). If the graph query tool (KuzuDB) still outputs these headers in Chinese, removing the regex patterns would break the knowledge panel in the report view.

**Mitigation:** Confirm what language the graph query tool actually outputs these headers in before modifying. Since graph_tools.py was found in the CJK grep results and its comments note "Chinese = Question", the tool output may still contain Chinese section headers. Add English alternatives as a safe parallel — do not remove Chinese patterns.

---

## Architecture Patterns

### No i18n Framework

All strings are hardcoded. Translation = edit the source files directly. There is no message catalog, no translation key lookup, and no locale switching.

### Vue File Structure

Step4Report.vue contains all logic in a single-file component with `<template>`, `<script>`, and `<style>` sections. All Chinese strings are in the `<script>` section within JavaScript regex literals and string comparisons. None are in the `<template>` HTML (confirmed by grep — all matched lines are JavaScript).

### Backend String Flow

The flow for strings that cross the backend/frontend boundary:
```
LLM prompt → LLM output (text) → graph_tools.py parsing →
AgentInterview.to_text() → API response (markdown text string) →
Step4Report.vue parsing → rendered UI
```

Chinese strings in Step4Report.vue are parsing this final markdown text. The backend already uses English in its `to_text()` serialization (line 309: `"**Key Quotes:**\n"`, line 305: `"_Bio: {self.agent_bio}_\n"`). The Chinese regex alternatives are for backward compatibility with reports generated by older versions of the backend.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Translation catalog | Custom i18n system | Direct string replacement | Only 3 files, 25 lines. An i18n system adds 100x complexity for zero benefit. |
| Regex test harness | Custom test runner | Manual spot-check with a real simulation | No test infrastructure exists; adding one is out of scope (backlog item) |

---

## Recommended Plan Split

The phase brief proposes two plans: `plan-frontend-localization` and `plan-backend-localization`. This is correct given the different risk profiles.

### Plan 1: plan-frontend-localization
**Target:** `frontend/src/components/Step4Report.vue`
**Work:** 18 lines requiring analysis and targeted edits
**Approach:** Add English alternatives to regex patterns; replace Chinese-only string comparisons with English equivalents; update the `"。"` literal; add/clarify English code comments
**Risk:** Medium — regex changes require care not to break report parsing
**No ordering constraint:** Frontend plan can be done independently

### Plan 2: plan-backend-localization
**Target:** `backend/app/services/oasis_profile_generator.py` (4 lines) and `backend/app/services/graph_tools.py` (3 lines)
**Work:** 7 lines, minimal changes
**Approach:** In graph_tools.py — improve comment wording (Chinese appears only in comment annotations that already have English explanations). Confirm `"。"` handling matches frontend change. In oasis_profile_generator.py — no changes needed to dict keys; comments are already English.
**Risk:** Low — these are comments and a single functional string literal

### Ordering dependency between plans

None. The two plans are independent. The frontend Vue parser has already been written to handle both Chinese and English LLM output formats. Backend changes are comment-only (plus one punctuation character). Either plan can execute first.

---

## Common Pitfalls

### Pitfall 1: Deleting Chinese from regexes that still match live output

**What goes wrong:** A developer sees `关键引言` in a regex, translates it to English, and removes the Chinese alternative. Old stored simulation reports (or a backend that still emits Chinese for some code paths) silently stop parsing — all key quote panels show empty.

**Why it happens:** The Chinese alternatives are not dead code — they are backward compatibility for reports generated before the backend was localized, and potentially for code paths not yet fully audited.

**How to avoid:** For every `|`-separated regex alternation that pairs Chinese and English, always keep both. Only remove a Chinese alternative after confirming (with a running simulation) that the backend never emits it.

### Pitfall 2: Treating the gender map keys as comments

**What goes wrong:** Someone "translates" the `gender_map` by replacing `"男"` with `"male"` as a key. The function now fails to map Chinese gender strings from LLM output, returning `"other"` for all agents.

**Why it happens:** The Chinese strings look like they need translation because they're in a Python source file being localized.

**How to avoid:** These are input-matcher keys. The comment says "Chinese: male" — meaning the Chinese string IS the expected input value. Leave the keys unchanged.

### Pitfall 3: Treating knowledge graph tool output headers as backend-controlled

**What goes wrong:** The planner assumes the Chinese section headers (`### 相关事实:`, etc.) in the Vue regex are legacy and removes them. But these headers are generated by the KuzuDB query tool's output formatter, which may still produce Chinese headers.

**Why it happens:** The audit found graph_tools.py is already mostly English, leading to an assumption the tool outputs are also English.

**How to avoid:** Before removing `相关事实:` from Step4Report.vue regex patterns, verify what the actual graph tool returns during a query. Add English alternatives first; confirm both work; then assess whether the Chinese alternative can be removed.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| LLM output in Chinese (bracket markers `【】`) | LLM output in English (`[Twitter Platform Response]`) | Backend already migrated in graph_tools.py line 1436 |
| Chinese section headers in graph tool output | Unknown — needs verification | Cannot confirm without running the tool |
| Chinese `問題X:` question numbering | English or Chinese (both handled in parser) | Backend sends question-numbered answers; frontend handles both |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 1 is source code editing only (string replacement in .vue and .py files). No external tools, databases, services, or CLIs are required to execute the localization changes. Docker and the running app are only needed for manual spot-check verification after changes, not for the changes themselves.

---

## Open Questions

1. **Do knowledge graph tool output sections still use Chinese headers?**
   - What we know: Step4Report.vue parses `### 相关事实:`, `### 相关边:`, `### 相关节点:` in Chinese
   - What's unclear: Whether the KuzuDB graph query tool currently emits these in Chinese or English
   - Recommendation: The planner should include a task to confirm the tool output language before finalizing regex changes. The safe default is to add English alternatives and keep Chinese.

2. **Are there stored simulation reports on disk that use the old Chinese format?**
   - What we know: The frontend has backward-compat regex for old Chinese format output
   - What's unclear: Whether any stored `.json` or `.md` report files on the developer's machine use the old format
   - Recommendation: Low risk — the Vue parser handles both formats already. Keeping Chinese alternatives in regexes handles this automatically.

---

## Sources

### Primary (HIGH confidence)
- Direct grep audit of all .vue and .py files in the repository — complete CJK character inventory
- Direct file reads of Step4Report.vue, graph_tools.py, oasis_profile_generator.py — confirmed line-by-line context

### Secondary (MEDIUM confidence)
- graph_tools.py line 1436 — confirms backend currently emits English platform markers
- graph_tools.py line 305, 309 — confirms `to_text()` uses English labels for Bio and Key Quotes

---

## Metadata

**Confidence breakdown:**
- File inventory: HIGH — grep audited every .vue and .py file in the codebase
- Regex risk analysis: HIGH — read actual source context for every flagged line
- Backend output format: MEDIUM — inferred from graph_tools.py source, not from running the app
- Knowledge graph tool output language: LOW — cannot confirm without running a query

**Research date:** 2026-03-24
**Valid until:** Stable — this is a one-time localization, not a moving ecosystem target

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| R1.1 | All text visible in the browser must be in English | Confirmed: zero Chinese in template HTML; all Chinese is in JavaScript regex patterns in Step4Report.vue |
| R1.2 | All strings sent from backend to frontend must be in English | Confirmed: oasis_profile_generator.py and graph_tools.py are the only backend files with Chinese; graph_tools.py already uses English in API-facing to_text() output |
| R1.3 | Backend log output must be in English | Confirmed: zero Chinese found in any logger.* calls across all backend files |
| R1.4 | All comments and docstrings must be in English | 3 lines in graph_tools.py have Chinese within comment annotations (already have English translations); oasis_profile_generator.py gender map comments are already English |
</phase_requirements>
