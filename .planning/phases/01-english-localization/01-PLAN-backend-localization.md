---
wave: 1
depends_on: []
files_modified:
  - backend/app/services/graph_tools.py
autonomous: true
requirements:
  - R1.3
  - R1.4
must_haves:
  truths:
    - "No Chinese characters remain in graph_tools.py"
    - "The Chinese full-stop '。' is no longer appended to extracted key quotes"
    - "The comment on line 1459 accurately describes the change"
    - "oasis_profile_generator.py requires no changes — already clean"
  artifacts:
    - path: "backend/app/services/graph_tools.py"
      provides: "Key quote extraction using ASCII period; clean English-only source"
  key_links:
    - from: "graph_tools.py line 1459"
      to: "AgentInterview.key_quotes"
      via: "list comprehension appending period character to extracted quotes"
      pattern: 'key_quotes = \[s \+ "\." for s in'
---

# Plan: Backend Localization — graph_tools.py

## Goal

Remove the three remaining Chinese characters from graph_tools.py. Two of these are in inline
comments (already accompanied by English translations — the comment text explains the Chinese
as an example). One is a functional string literal: the Chinese full-stop `"。"` appended to
extracted key quotes in the key_quotes list comprehension. That character must be changed to
`"."` (ASCII period). oasis_profile_generator.py requires no changes — its Chinese characters
are functional input-matcher keys that are already fully documented in English comments.

## Requirements Addressed

- R1.3: Backend log output must be in English — no Chinese found in any logger.* call; this
  plan addresses the only remaining source file Chinese characters
- R1.4: All comments and docstrings must be in English — graph_tools.py lines 1446, 1456, 1459
  contain Chinese within comment text or as a functional literal appended to output strings

---

## Tasks

<task id="T1" name="Read both files and confirm exact current state">
<read_first>
- backend/app/services/graph_tools.py lines 1440-1470 (verify exact content of the 3 affected lines)
- backend/app/services/oasis_profile_generator.py lines 1070-1086 (confirm no changes needed)
</read_first>
<action>
This is a read-and-verify task. Confirm the following before making any changes:

GRAPH_TOOLS.PY — three affected lines (search by content, not line number):

LINE ~1446:
  Current: `# Remove question markers in both Chinese ("问题" = "Question") and English`
  The comment already has an English explanation. The Chinese `"问题"` appears only as a quoted
  example in the comment. This comment text is already correct and informative.
  Action required: NONE — comment is already fully English-explained. Leave as-is.

LINE ~1456:
  Current: `and not s.strip().startswith(('{', '问题', 'Question'))  # "问题" = Chinese for "Question"`
  The Chinese `'问题'` here is a functional string — it is a startswith() filter used to exclude
  sentences beginning with the Chinese word for "Question". The comment correctly documents it.
  The string `'问题'` must remain in the tuple because the cleaned_text may still contain Chinese
  question markers from older simulation transcripts.
  Action required: NONE — functional string with English comment. Leave as-is.

  Wait — re-read the requirement. R1.4 covers comments. R1.2 covers strings sent from backend
  to frontend. The `'问题'` on line 1456 is NOT sent to the frontend — it is used only as a
  filter inside key-quote extraction. However, the research file (line 89) explicitly calls
  out only line 1459 (`"。"`) as the functional string to change. Line 1456's `'问题'` is a
  filter value (keeps it from outputting Chinese content), not an output value.
  Final decision: Leave line 1456 unchanged. Document this in the summary.

LINE ~1459:
  Current: `key_quotes = [s + "。" for s in meaningful[:3]]  # "。" = Chinese full-stop period`
  The `"。"` is a Chinese full-stop character appended to each extracted quote string. These
  quotes ARE part of AgentInterview output sent to the frontend report.
  Action required: CHANGE — replace `"。"` with `"."` and update the comment.

OASIS_PROFILE_GENERATOR.PY — lines 1070-1086:
  Current state (from read): Chinese keys `"男"`, `"女"`, `"机构"`, `"其他"` exist as dict keys.
  English keys `"male"`, `"female"`, `"other"` also already exist in the same dict.
  All Chinese keys have English inline comments.
  These are input-matcher keys — changing them would break gender normalization for Chinese LLM output.
  Action required: NONE — leave entirely unchanged. R1.4 is satisfied; comments are already English.
</action>
<acceptance_criteria>
- [ ] This task produces no file changes — it is a verification step only
- [ ] Executor confirms line ~1459 contains `"。"` and must be changed
- [ ] Executor confirms lines ~1446 and ~1456 require no changes
- [ ] Executor confirms oasis_profile_generator.py requires no changes
</acceptance_criteria>
</task>

<task id="T2" name="Replace Chinese full-stop in graph_tools.py line 1459">
<read_first>
- backend/app/services/graph_tools.py lines 1450-1465 (read before editing to see exact current state)
</read_first>
<action>
Make exactly one change to backend/app/services/graph_tools.py.

Find this line (search by the unique string `key_quotes = [s + "。"`):
```python
                key_quotes = [s + "。" for s in meaningful[:3]]  # "。" = Chinese full-stop period
```

Replace with:
```python
                key_quotes = [s + "." for s in meaningful[:3]]  # "." = ASCII period appended to each quote
```

That is the only change in this file. Do not alter indentation, surrounding lines, or any other content.

Do NOT change oasis_profile_generator.py. Its Chinese characters are functional input-matcher
dict keys; removing them would cause all Chinese-language gender strings from LLM output to
fall through to the default `"other"` value, silently corrupting agent gender data.
</action>
<acceptance_criteria>
- [ ] grep -P "[\x{4e00}-\x{9fff}]" "backend/app/services/graph_tools.py" returns NO matches
- [ ] grep 'key_quotes = \[s + "\." for s in' "backend/app/services/graph_tools.py" returns a match
- [ ] grep 'key_quotes = \[s + "。"' "backend/app/services/graph_tools.py" returns NO match
- [ ] grep -P "[\x{4e00}-\x{9fff}]" "backend/app/services/oasis_profile_generator.py" still returns matches (file was not touched)
- [ ] git diff --name-only shows only graph_tools.py was modified (not oasis_profile_generator.py)
</acceptance_criteria>
</task>

## Verification

After both tasks complete:

1. Confirm zero Chinese characters remain in graph_tools.py:
   ```
   grep -Pn "[\x{4e00}-\x{9fff}]" backend/app/services/graph_tools.py
   ```
   Expected: no output (empty result).

2. Confirm ASCII period is now used in key_quotes:
   ```
   grep -n 'key_quotes = \[s + "\.' backend/app/services/graph_tools.py
   ```
   Expected: one line containing `"."` (ASCII period, not `"。"`).

3. Confirm oasis_profile_generator.py was not modified:
   ```
   grep -Pn "[\x{4e00}-\x{9fff}]" backend/app/services/oasis_profile_generator.py
   ```
   Expected: still returns the 4 Chinese gender keys (file intentionally unchanged).

## must_haves

- Zero Chinese characters in backend/app/services/graph_tools.py (grep returns empty)
- Key quotes in AgentInterview output now use ASCII period `"."` instead of Chinese full-stop `"。"`
- oasis_profile_generator.py gender_map is unchanged (Chinese input-matcher keys preserved)
