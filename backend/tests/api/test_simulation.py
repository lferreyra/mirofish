"""Tests for simulation API routes"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.api.simulation import (
    optimize_interview_prompt,
    INTERVIEW_PROMPT_PREFIX
)


class TestInterviewPromptOptimization:
    """Test cases for interview prompt optimization"""

    def test_optimize_empty_prompt(self):
        """Test optimizing empty prompt"""
        result = optimize_interview_prompt("")
        assert result == ""

    def test_optimize_none_prompt(self):
        """Test optimizing None prompt"""
        result = optimize_interview_prompt(None)
        assert result is None

    def test_optimize_regular_prompt(self):
        """Test optimizing a regular prompt"""
        prompt = "What is your opinion on this topic?"
        result = optimize_interview_prompt(prompt)

        assert result.startswith(INTERVIEW_PROMPT_PREFIX)
        assert prompt in result
        assert "工具" in result or "tools" in result or "直接" in result

    def test_optimize_prompt_avoids_duplication(self):
        """Test that optimizing already optimized prompt doesn't duplicate prefix"""
        original_prompt = "What do you think?"
        optimized_once = optimize_interview_prompt(original_prompt)
        optimized_twice = optimize_interview_prompt(optimized_once)

        # Should not have doubled prefix
        assert optimized_once.count(INTERVIEW_PROMPT_PREFIX) == 1
        assert optimized_twice.count(INTERVIEW_PROMPT_PREFIX) == 1
        assert optimized_once == optimized_twice

    def test_optimize_prompt_preserves_content(self):
        """Test that optimization preserves original prompt content"""
        prompt = "Tell me about your experience in software development"
        result = optimize_interview_prompt(prompt)

        assert "software development" in result

    def test_optimize_long_prompt(self):
        """Test optimizing a long prompt"""
        prompt = "This is a very long prompt. " * 10
        result = optimize_interview_prompt(prompt)

        assert INTERVIEW_PROMPT_PREFIX in result
        assert prompt in result

    def test_optimize_prompt_with_special_characters(self):
        """Test optimizing prompt with special characters"""
        prompt = "What about China's 政策? And émojis 🚀"
        result = optimize_interview_prompt(prompt)

        assert INTERVIEW_PROMPT_PREFIX in result
        assert "China" in result or "政策" in result

    def test_optimize_prompt_idempotent(self):
        """Test that optimization is idempotent"""
        prompt = "Initial prompt"
        result1 = optimize_interview_prompt(prompt)
        result2 = optimize_interview_prompt(result1)
        result3 = optimize_interview_prompt(result2)

        assert result1 == result2 == result3


class TestSimulationAPIHelper:
    """Test helper functions for simulation API"""

    def test_interview_prompt_prefix_not_empty(self):
        """Test that INTERVIEW_PROMPT_PREFIX is defined"""
        assert INTERVIEW_PROMPT_PREFIX is not None
        assert len(INTERVIEW_PROMPT_PREFIX) > 0
        assert "结合你的人设" in INTERVIEW_PROMPT_PREFIX or "文本回复" in INTERVIEW_PROMPT_PREFIX

    def test_interview_prompt_prefix_contains_chinese(self):
        """Test that prefix contains Chinese instructions"""
        assert any(ord(c) > 127 for c in INTERVIEW_PROMPT_PREFIX)  # Contains non-ASCII
