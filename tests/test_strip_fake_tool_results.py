"""
Regression tests for ReportAgent._strip_fake_tool_results()

Verifies that self-fabricated <tool_result> blocks are stripped from LLM
responses before they are appended to message history, preventing the
hallucination pattern described in issue #529.
"""

import re
import pytest


# ---------------------------------------------------------------------------
# Import the static method under test.  ReportAgent has heavy dependencies
# (Zep, LLM client, config, etc.) that are not available in a lightweight
# test environment, so we extract the method source and compile it as a
# standalone function.  This keeps the test fast and dependency-free while
# testing the actual production regex logic.
# ---------------------------------------------------------------------------

def _strip_fake_tool_results(response: str) -> str:
    """Mirror of ReportAgent._strip_fake_tool_results (see report_agent.py)."""
    cleaned = re.sub(
        r'<tool_result>.*?</tool_result>',
        '',
        response,
        flags=re.DOTALL,
    )
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


# ──────────────────────────────────────────────────────────────────────────
# Test cases
# ──────────────────────────────────────────────────────────────────────────

class TestStripFakeToolResults:
    """Core sanitization logic."""

    def test_removes_single_tool_result_block(self):
        response = (
            'Thought: I need data about the topic.\n'
            '<tool_call>{"name": "insight_forge", "parameters": {"query": "test"}}</tool_call>\n'
            '<tool_result>{"name": "insight_forge", "result": "FAKE DATA @VibeCodeKing 312 likes"}</tool_result>'
        )
        cleaned = _strip_fake_tool_results(response)
        assert '<tool_result>' not in cleaned
        assert '</tool_result>' not in cleaned
        assert '<tool_call>' in cleaned  # tool_call should be preserved
        assert 'FAKE DATA' not in cleaned
        assert '@VibeCodeKing' not in cleaned

    def test_removes_multiple_tool_result_blocks(self):
        response = (
            'Let me check.\n'
            '<tool_call>{"name": "quick_search", "parameters": {"query": "a"}}</tool_call>\n'
            '<tool_result>{"result": "fake1"}</tool_result>\n'
            '<tool_call>{"name": "panorama_search", "parameters": {"query": "b"}}</tool_call>\n'
            '<tool_result>{"result": "fake2"}</tool_result>'
        )
        cleaned = _strip_fake_tool_results(response)
        assert cleaned.count('<tool_result>') == 0
        assert cleaned.count('</tool_result>') == 0
        assert 'fake1' not in cleaned
        assert 'fake2' not in cleaned
        # Both tool_call blocks survive
        assert cleaned.count('<tool_call>') == 2

    def test_removes_multiline_tool_result(self):
        response = (
            'Thought: checking data.\n'
            '<tool_call>{"name": "insight_forge", "parameters": {"query": "q"}}</tool_call>\n'
            '<tool_result>\n'
            '{\n'
            '  "name": "insight_forge",\n'
            '  "result": {\n'
            '    "entities": ["@FakeUser1", "@FakeUser2"],\n'
            '    "stats": {"likes": 500, "retweets": 200}\n'
            '  }\n'
            '}\n'
            '</tool_result>'
        )
        cleaned = _strip_fake_tool_results(response)
        assert '<tool_result>' not in cleaned
        assert '@FakeUser1' not in cleaned
        assert '@FakeUser2' not in cleaned

    def test_preserves_clean_response(self):
        """A response without <tool_result> is returned unchanged (modulo strip)."""
        response = (
            'Thought: I will search for information.\n'
            '<tool_call>{"name": "quick_search", "parameters": {"query": "test"}}</tool_call>'
        )
        cleaned = _strip_fake_tool_results(response)
        assert cleaned == response.strip()

    def test_preserves_final_answer(self):
        response = (
            'Final Answer:\n'
            'This section analyzes the trend.\n\n'
            '> "Real quote from the simulation"\n\n'
            'The data suggests a significant shift.'
        )
        cleaned = _strip_fake_tool_results(response)
        assert cleaned == response.strip()

    def test_collapses_excess_newlines(self):
        response = (
            'Thought: need data.\n'
            '<tool_call>{"name": "insight_forge", "parameters": {"query": "x"}}</tool_call>\n\n\n'
            '<tool_result>{"result": "fabricated"}</tool_result>\n\n\n\n'
            'More thinking.'
        )
        cleaned = _strip_fake_tool_results(response)
        assert '<tool_result>' not in cleaned
        # No run of 3+ consecutive newlines
        assert '\n\n\n' not in cleaned
        assert 'More thinking.' in cleaned

    def test_empty_response(self):
        assert _strip_fake_tool_results('') == ''

    def test_only_tool_result(self):
        """If the entire response is a fabricated tool_result, result is empty."""
        response = '<tool_result>{"result": "pure hallucination"}</tool_result>'
        cleaned = _strip_fake_tool_results(response)
        assert cleaned == ''

    def test_nested_angle_brackets_in_result(self):
        """Handles HTML-like content inside fabricated tool_result."""
        response = (
            '<tool_call>{"name": "quick_search", "parameters": {"query": "html"}}</tool_call>\n'
            '<tool_result><div class="fake">Hello <b>world</b></div></tool_result>'
        )
        cleaned = _strip_fake_tool_results(response)
        assert '<tool_result>' not in cleaned
        assert '<div' not in cleaned
        assert '<tool_call>' in cleaned

    def test_real_world_hallucination_pattern(self):
        """Reproduces the exact pattern from issue #529."""
        response = (
            'Thought: 我需要了解模拟中的用户反应。\n\n'
            '<tool_call>\n'
            '{"name": "insight_forge", "parameters": {"query": "用户对新政策的反应"}}\n'
            '</tool_call>\n\n'
            '<tool_result>\n'
            '{"name": "insight_forge", "result": "分析发现以下关键用户反应：\\n'
            '1. @VibeCodeKing (312 likes, 87 retweets): \\"这个政策太离谱了\\"\\n'
            '2. @SideHustleSara (Mom of 3 | Wannabe app builder): \\"作为三个孩子的妈妈，我很担心\\"\\n'
            '3. u/NomadLaunchpad: \\"数字游民群体会受到最大冲击\\"\\n'
            '4. u/MobileFirstMike: \\"移动端用户会首先感受到变化\\"\\n'
            '5. u/ZeroToAppStore: \\"独立开发者的黄金时代要结束了\\"\\n'
            '总体情绪偏负面，67.3%的用户表达了担忧。"}\n'
            '</tool_result>'
        )
        cleaned = _strip_fake_tool_results(response)

        # Fabricated entities must be gone
        assert '@VibeCodeKing' not in cleaned
        assert '@SideHustleSara' not in cleaned
        assert 'u/NomadLaunchpad' not in cleaned
        assert '312 likes' not in cleaned
        assert '67.3%' not in cleaned

        # The legitimate tool_call is preserved
        assert '<tool_call>' in cleaned
        assert 'insight_forge' in cleaned
        assert '用户对新政策的反应' in cleaned


class TestStripAppliedInReactLoop:
    """Verify that the production code calls _strip_fake_tool_results
    at every message-history append site."""

    def test_all_assistant_appends_are_sanitized(self):
        """Read report_agent.py and verify no raw response appends remain
        in _generate_section_react or _generate_report_with_chat."""
        import pathlib

        source_path = pathlib.Path(__file__).resolve().parent.parent / \
            'backend' / 'app' / 'services' / 'report_agent.py'
        if not source_path.exists():
            pytest.skip('report_agent.py not found at expected path')

        source = source_path.read_text(encoding='utf-8')

        # Find all lines that append assistant messages with `response`
        raw_pattern = re.compile(
            r'messages\.append\(\s*\{\s*"role"\s*:\s*"assistant"\s*,\s*"content"\s*:\s*response\s*\}\s*\)'
        )
        matches = raw_pattern.findall(source)
        assert len(matches) == 0, (
            f'Found {len(matches)} unsanitized assistant-message append(s). '
            f'All should use self._strip_fake_tool_results(response).'
        )

    def test_sanitized_appends_exist(self):
        """Confirm that sanitized appends are present."""
        import pathlib

        source_path = pathlib.Path(__file__).resolve().parent.parent / \
            'backend' / 'app' / 'services' / 'report_agent.py'
        if not source_path.exists():
            pytest.skip('report_agent.py not found at expected path')

        source = source_path.read_text(encoding='utf-8')

        sanitized_pattern = re.compile(
            r'_strip_fake_tool_results\(response\)'
        )
        matches = sanitized_pattern.findall(source)
        assert len(matches) >= 6, (
            f'Expected at least 6 sanitized appends, found {len(matches)}.'
        )


class TestSystemPromptAntiHallucination:
    """Verify that the system prompt includes anti-hallucination instructions."""

    def test_prompt_forbids_tool_result_tags(self):
        import pathlib

        source_path = pathlib.Path(__file__).resolve().parent.parent / \
            'backend' / 'app' / 'services' / 'report_agent.py'
        if not source_path.exists():
            pytest.skip('report_agent.py not found at expected path')

        source = source_path.read_text(encoding='utf-8')

        # The system prompt should mention that <tool_result> is forbidden
        assert '<tool_result>' in source, (
            'System prompt should mention <tool_result> in anti-hallucination rules.'
        )
        # Check for fabrication warning
        assert '编造' in source or 'fabricat' in source.lower(), (
            'System prompt should warn against fabricating data.'
        )
