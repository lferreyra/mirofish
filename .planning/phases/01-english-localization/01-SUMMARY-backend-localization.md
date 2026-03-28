# Phase 01 Plan 01: Backend Localization — graph_tools.py Summary

## Status: COMPLETE

## Objective

Remove the one remaining functional Chinese character appended to key_quotes in graph_tools.py: the Chinese full-stop `"。"` (U+3002) replaced with an ASCII period `"."`.

## Change Applied

**File:** `backend/app/services/graph_tools.py`
**Line:** 1459

**Before:**
```python
                key_quotes = [s + "。" for s in meaningful[:3]]  # "。" = Chinese full-stop period
```

**After:**
```python
                key_quotes = [s + "." for s in meaningful[:3]]  # "." = ASCII period appended to each quote
```

This was the only change made. No other lines, indentation, or surrounding content was altered.

## Verification Results

### Check 1: Zero Chinese full-stop characters in key_quotes line
grep for `"。"` in key_quotes context — NO MATCH. The Chinese full-stop is no longer present on the key_quotes line.

### Check 2: ASCII period now used in key_quotes
```
1459: '                key_quotes = [s + "." for s in meaningful[:3]]  # "." = ASCII period appended to each quote'
```
One match confirmed on line 1459.

### Check 3: Chinese full-stop not present in key_quotes
No match found for `key_quotes = [s + "。"` — confirmed removed.

### Check 4: oasis_profile_generator.py was NOT modified
Chinese gender keys still present at their original lines:
- `男` (male): line 1075
- `女` (female): line 1076
- `机构` (institution): line 1077
- `其他` (other): line 1078

`oasis_profile_generator.py` was not touched.

## Notes on Remaining Chinese in graph_tools.py

During verification, three lines in graph_tools.py were found to still contain Chinese characters (`"问题"`):

- Line 1446: comment — `# Remove question markers in both Chinese ("问题" = "Question") and English`
- Line 1447: regex pattern — `re.sub(r'(?:问题|Question)\s*\d+[：:]\s*', '', clean_text)` — functional input matcher
- Line 1456: startswith filter — `s.strip().startswith(('{', '问题', 'Question'))` — functional input matcher

These were out of scope for this plan. Per the plan specification, the target was "the one remaining functional Chinese character" being appended as output (the full-stop on line 1459). The `"问题"` occurrences are input-matcher patterns (same category as the gender keys in oasis_profile_generator.py) and were intentionally left unchanged.

## Deviations from Plan

None. The plan was executed exactly as specified: one line changed, one file modified, oasis_profile_generator.py untouched.
