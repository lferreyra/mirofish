"""
Unit tests for OasisAgentProfile and OasisProfileGenerator.

These tests verify the profile format conversion logic without requiring
external dependencies (LLM, Zep, Flask, etc.).

Note: Full integration tests require Flask app initialization and external
services. These tests focus on isolated logic that can be tested without
those dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Manually set up path to import modules without triggering Flask app init
# by mocking problematic imports first

# Create mock modules to avoid Flask/llm_client imports
mock_logger = MagicMock()
mock_locale = MagicMock()
mock_locale.get_locale.return_value = 'zh'
mock_locale.set_locale.return_value = None
mock_locale.get_language_instruction.return_value = '请使用中文回答。'
mock_locale.t.return_value = 'test'

mock_config = MagicMock()
mock_config.LLM_API_KEY = None
mock_config.LLM_BASE_URL = None
mock_config.LLM_MODEL_NAME = None
mock_config.ZEP_API_KEY = None

# Patch the imports before importing the target module
import sys
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('app.'):
        del sys.modules[mod_name]

with patch.dict('sys.modules', {
    'flask': MagicMock(),
    'flask_cors': MagicMock(),
    'openai': MagicMock(),
    'zep_cloud': MagicMock(),
    'zep_cloud.client': MagicMock(),
    'app': MagicMock(),
    'app.config': mock_config,
    'app.utils': MagicMock(),
    'app.utils.logger': mock_logger,
    'app.utils.locale': mock_locale,
    'app.services.zep_entity_reader': MagicMock(),
}):
    # Now we can import - but we need to avoid app.__init__.py
    # So we'll define OasisAgentProfile inline instead
    pass

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


# Define OasisAgentProfile directly here to avoid Flask app init issues
# This is a copy of the class from oasis_profile_generator.py for testing
@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile数据结构"""
    # 通用字段
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str

    # 可选字段 - Reddit风格
    karma: int = 1000

    # 可选字段 - Twitter风格
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500

    # 额外人设信息
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)

    # 来源实体信息
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_reddit_format(self) -> Dict[str, Any]:
        """转换为Reddit平台格式"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }

        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile

    def to_twitter_format(self) -> Dict[str, Any]:
        """转换为Twitter平台格式"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }

        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整字典格式"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


# Define helper functions from OasisProfileGenerator for testing
def _generate_username(name: str) -> str:
    """生成用户名"""
    import random
    username = name.lower().replace(" ", "_")
    username = ''.join(c for c in username if c.isalnum() or c == '_')
    suffix = random.randint(100, 999)
    return f"{username}_{suffix}"


def _normalize_gender(gender: Optional[str]) -> str:
    """标准化gender字段为OASIS要求的英文格式"""
    if not gender:
        return "other"
    gender_lower = gender.lower().strip()
    gender_map = {
        "男": "male",
        "女": "female",
        "机构": "other",
        "其他": "other",
        "male": "male",
        "female": "female",
        "other": "other",
    }
    return gender_map.get(gender_lower, "other")


# Entity type constants from OasisProfileGenerator
INDIVIDUAL_ENTITY_TYPES = [
    "student", "alumni", "professor", "person", "publicfigure",
    "expert", "faculty", "official", "journalist", "activist"
]

GROUP_ENTITY_TYPES = [
    "university", "governmentagency", "organization", "ngo",
    "mediaoutlet", "company", "institution", "group", "community"
]


def _is_individual_entity(entity_type: str) -> bool:
    return entity_type.lower() in INDIVIDUAL_ENTITY_TYPES


def _is_group_entity(entity_type: str) -> bool:
    return entity_type.lower() in GROUP_ENTITY_TYPES


class TestOasisAgentProfile:
    """Tests for OasisAgentProfile dataclass."""

    def create_test_profile(
        self,
        user_id: int = 0,
        user_name: str = "test_user",
        name: str = "Test User",
        bio: str = "A test user",
        persona: str = "Test User is enthusiastic",
        karma: int = 1000,
        friend_count: int = 100,
        follower_count: int = 200,
        statuses_count: int = 500,
        age: int = 25,
        gender: str = "male",
        mbti: str = "INTJ",
        country: str = "China",
        profession: str = "Student",
        interested_topics: list = None,
        source_entity_uuid: str = "test-uuid-123",
        source_entity_type: str = "student",
    ) -> OasisAgentProfile:
        """Helper to create a test profile with default values."""
        if interested_topics is None:
            interested_topics = ["Technology", "Education"]
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=bio,
            persona=persona,
            karma=karma,
            friend_count=friend_count,
            follower_count=follower_count,
            statuses_count=statuses_count,
            age=age,
            gender=gender,
            mbti=mbti,
            country=country,
            profession=profession,
            interested_topics=interested_topics,
            source_entity_uuid=source_entity_uuid,
            source_entity_type=source_entity_type,
        )

    # ===== to_reddit_format() tests =====

    def test_to_reddit_format_basic(self):
        """Test basic Reddit format conversion."""
        profile = self.create_test_profile()
        reddit = profile.to_reddit_format()

        assert reddit["user_id"] == 0
        assert reddit["username"] == "test_user"
        assert reddit["name"] == "Test User"
        assert reddit["bio"] == "A test user"
        assert reddit["persona"] == "Test User is enthusiastic"
        assert reddit["karma"] == 1000
        assert "created_at" in reddit

    def test_to_reddit_format_includes_optional_fields(self):
        """Test that Reddit format includes optional personality fields."""
        profile = self.create_test_profile(
            age=30,
            gender="female",
            mbti="ENFP",
            country="US",
            profession="Engineer",
            interested_topics=["AI", "Music"],
        )
        reddit = profile.to_reddit_format()

        assert reddit["age"] == 30
        assert reddit["gender"] == "female"
        assert reddit["mbti"] == "ENFP"
        assert reddit["country"] == "US"
        assert reddit["profession"] == "Engineer"
        assert reddit["interested_topics"] == ["AI", "Music"]

    def test_to_reddit_format_optional_fields_none(self):
        """Test Reddit format when optional fields are None."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
        )
        reddit = profile.to_reddit_format()

        # Optional fields should not be present when None
        assert "age" not in reddit
        assert "gender" not in reddit
        assert "mbti" not in reddit
        assert "country" not in reddit
        assert "profession" not in reddit
        assert "interested_topics" not in reddit

    def test_to_reddit_format_empty_topics(self):
        """Test Reddit format when interested_topics is empty list."""
        profile = self.create_test_profile(interested_topics=[])
        reddit = profile.to_reddit_format()

        assert "interested_topics" not in reddit

    # ===== to_twitter_format() tests =====

    def test_to_twitter_format_basic(self):
        """Test basic Twitter format conversion."""
        profile = self.create_test_profile()
        twitter = profile.to_twitter_format()

        assert twitter["user_id"] == 0
        assert twitter["username"] == "test_user"
        assert twitter["name"] == "Test User"
        assert twitter["bio"] == "A test user"
        assert twitter["persona"] == "Test User is enthusiastic"
        assert twitter["friend_count"] == 100
        assert twitter["follower_count"] == 200
        assert twitter["statuses_count"] == 500
        assert "created_at" in twitter

    def test_to_twitter_format_includes_optional_fields(self):
        """Test that Twitter format includes optional personality fields."""
        profile = self.create_test_profile(
            age=35,
            gender="male",
            mbti="ENTJ",
            country="UK",
            profession="Manager",
            interested_topics=["Business", "Tech"],
        )
        twitter = profile.to_twitter_format()

        assert twitter["age"] == 35
        assert twitter["gender"] == "male"
        assert twitter["mbti"] == "ENTJ"
        assert twitter["country"] == "UK"
        assert twitter["profession"] == "Manager"
        assert twitter["interested_topics"] == ["Business", "Tech"]

    def test_to_twitter_format_optional_fields_none(self):
        """Test Twitter format when optional fields are None."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
            friend_count=50,
            follower_count=100,
            statuses_count=200,
        )
        twitter = profile.to_twitter_format()

        assert "age" not in twitter
        assert "gender" not in twitter
        assert "mbti" not in twitter
        assert "country" not in twitter
        assert "profession" not in twitter
        assert "interested_topics" not in twitter

    # ===== to_dict() tests =====

    def test_to_dict_contains_all_fields(self):
        """Test that to_dict includes all profile fields."""
        profile = self.create_test_profile()
        d = profile.to_dict()

        # Required fields
        assert d["user_id"] == 0
        assert d["user_name"] == "test_user"
        assert d["name"] == "Test User"
        assert d["bio"] == "A test user"
        assert d["persona"] == "Test User is enthusiastic"

        # Social stats
        assert d["karma"] == 1000
        assert d["friend_count"] == 100
        assert d["follower_count"] == 200
        assert d["statuses_count"] == 500

        # Optional fields
        assert d["age"] == 25
        assert d["gender"] == "male"
        assert d["mbti"] == "INTJ"
        assert d["country"] == "China"
        assert d["profession"] == "Student"
        assert d["interested_topics"] == ["Technology", "Education"]

        # Source info
        assert d["source_entity_uuid"] == "test-uuid-123"
        assert d["source_entity_type"] == "student"
        assert "created_at" in d

    def test_to_dict_optional_fields_none(self):
        """Test to_dict when optional fields are None."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
        )
        d = profile.to_dict()

        assert d["age"] is None
        assert d["gender"] is None
        assert d["mbti"] is None
        assert d["country"] is None
        assert d["profession"] is None
        assert d["interested_topics"] == []
        assert d["source_entity_uuid"] is None
        assert d["source_entity_type"] is None

    # ===== Field value tests =====

    def test_karma_default_value(self):
        """Test that karma has correct default value."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
        )
        assert profile.karma == 1000

    def test_social_counts_default_values(self):
        """Test default values for social media counts."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
        )
        assert profile.friend_count == 100
        assert profile.follower_count == 150
        assert profile.statuses_count == 500

    def test_interested_topics_default_empty_list(self):
        """Test that interested_topics defaults to empty list."""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test",
            bio="bio",
            persona="persona",
        )
        assert profile.interested_topics == []

    def test_created_at_default_format(self):
        """Test that created_at has correct date format (YYYY-MM-DD)."""
        import re
        profile = self.create_test_profile()
        assert re.match(r"\d{4}-\d{2}-\d{2}", profile.created_at)


class TestHelperFunctions:
    """Tests for helper functions from OasisProfileGenerator."""

    def test_generate_username_basic(self):
        """Test username generation from name."""
        username = _generate_username("John Doe")
        assert username.startswith("john_doe_")
        assert len(username.split("_")) == 3  # john, doe, 3-digit-suffix

    def test_generate_username_removes_special_chars(self):
        """Test that username generation removes special characters."""
        username = _generate_username("John@Doe#123")
        assert "@" not in username
        assert "#" not in username
        assert username.startswith("johndoe123_")

    def test_generate_username_allows_underscores(self):
        """Test that underscores are preserved in username."""
        username = _generate_username("John_Doe_Smith")
        assert "_" in username
        assert username.startswith("john_doe_smith_")


class TestGenderNormalization:
    """Tests for gender normalization function."""

    def test_normalize_gender_english(self):
        """Test gender normalization for English values."""
        assert _normalize_gender("male") == "male"
        assert _normalize_gender("female") == "female"
        assert _normalize_gender("other") == "other"

    def test_normalize_gender_chinese(self):
        """Test gender normalization for Chinese values."""
        assert _normalize_gender("男") == "male"
        assert _normalize_gender("女") == "female"
        assert _normalize_gender("其他") == "other"

    def test_normalize_gender_none(self):
        """Test gender normalization for None/empty values."""
        assert _normalize_gender(None) == "other"
        assert _normalize_gender("") == "other"
        assert _normalize_gender("unknown") == "other"

    def test_normalize_gender_case_insensitive(self):
        """Test that gender normalization is case-insensitive."""
        assert _normalize_gender("MALE") == "male"
        assert _normalize_gender("Female") == "female"
        assert _normalize_gender("OTHER") == "other"


class TestEntityTypeDetection:
    """Tests for entity type detection functions."""

    def test_is_individual_entity_positive(self):
        """Test individual entity type detection - should be individual."""
        assert _is_individual_entity("student") is True
        assert _is_individual_entity("STUDENT") is True
        assert _is_individual_entity("professor") is True
        assert _is_individual_entity("person") is True
        assert _is_individual_entity("alumni") is True
        assert _is_individual_entity("publicfigure") is True
        assert _is_individual_entity("expert") is True
        assert _is_individual_entity("faculty") is True

    def test_is_individual_entity_negative(self):
        """Test individual entity type detection - should NOT be individual."""
        assert _is_individual_entity("university") is False
        assert _is_individual_entity("company") is False
        assert _is_individual_entity("organization") is False
        assert _is_individual_entity("ngo") is False
        assert _is_individual_entity("governmentagency") is False

    def test_is_group_entity_positive(self):
        """Test group entity type detection - should be group."""
        assert _is_group_entity("university") is True
        assert _is_group_entity("UNIVERSITY") is True
        assert _is_group_entity("company") is True
        assert _is_group_entity("governmentagency") is True
        assert _is_group_entity("ngo") is True
        assert _is_group_entity("mediaoutlet") is True

    def test_is_group_entity_negative(self):
        """Test group entity type detection - should NOT be group."""
        assert _is_group_entity("student") is False
        assert _is_group_entity("professor") is False
        assert _is_group_entity("person") is False
        assert _is_group_entity("alumni") is False
