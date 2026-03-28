"""
Action types and action classes for the custom simulation engine.

Replaces the CAMEL-OASIS ActionType, LLMAction, and ManualAction.
"""

from enum import Enum


class ActionType(str, Enum):
    """All supported action types across Twitter and Reddit platforms."""

    # Twitter actions
    CREATE_POST = "create_post"
    LIKE_POST = "like_post"
    REPOST = "repost"
    FOLLOW = "follow"
    DO_NOTHING = "do_nothing"
    QUOTE_POST = "quote_post"

    # Reddit additional actions
    DISLIKE_POST = "dislike_post"
    CREATE_COMMENT = "create_comment"
    LIKE_COMMENT = "like_comment"
    DISLIKE_COMMENT = "dislike_comment"
    SEARCH_POSTS = "search_posts"
    SEARCH_USER = "search_user"
    TREND = "trend"
    REFRESH = "refresh"
    MUTE = "mute"

    # Shared
    INTERVIEW = "interview"


class LLMAction:
    """Agent decides action via LLM."""
    pass


class ManualAction:
    """Manually specified action."""

    def __init__(self, action_type: ActionType, action_args: dict = None):
        self.action_type = action_type
        self.action_args = action_args or {}
