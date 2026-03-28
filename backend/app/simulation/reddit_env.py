"""
Reddit-specific simulation environment.

Overrides the observation builder and available actions for Reddit.
"""

import logging
from typing import List

from .actions import ActionType
from .agent_graph import AgentGraph
from .environment import PlatformType, SimulationEnvironment

logger = logging.getLogger(__name__)


class RedditEnvironment(SimulationEnvironment):
    """
    Reddit simulation environment.

    Observation shows recent posts + top comments, with karma-like scoring.
    Available actions are Reddit-specific.
    """

    # Reddit available actions (INTERVIEW is only triggered manually)
    AVAILABLE_ACTIONS = [
        ActionType.LIKE_POST,
        ActionType.DISLIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.LIKE_COMMENT,
        ActionType.DISLIKE_COMMENT,
        ActionType.SEARCH_POSTS,
        ActionType.SEARCH_USER,
        ActionType.TREND,
        ActionType.REFRESH,
        ActionType.DO_NOTHING,
        ActionType.FOLLOW,
        ActionType.MUTE,
    ]

    def __init__(
        self,
        agent_graph: AgentGraph,
        database_path: str,
        semaphore: int = 30,
        model=None,
    ):
        super().__init__(
            agent_graph=agent_graph,
            platform=PlatformType.REDDIT,
            database_path=database_path,
            semaphore=semaphore,
        )
        self._model = model

    def _get_available_actions(self) -> List[ActionType]:
        return self.AVAILABLE_ACTIONS

    async def _build_observation(self, agent_id: int) -> str:
        """
        Build a Reddit feed observation for the given agent.

        Shows recent posts with top comments, ordered by score (likes - dislikes).
        """
        if not self._db:
            return "(no feed available)"

        # Get recent posts ordered by score (likes - dislikes)
        cursor = self._db.execute(
            """
            SELECT p.post_id, p.user_id, p.content, p.likes, p.dislikes, p.created_at
            FROM posts p
            WHERE p.content IS NOT NULL AND p.content != ''
            ORDER BY (p.likes - p.dislikes) DESC, p.created_at DESC
            LIMIT 15
            """,
        )
        posts = cursor.fetchall()

        if not posts:
            return "(the feed is empty - be the first to post!)"

        lines = ["Recent posts on your feed:"]
        for post_id, user_id, content, likes, dislikes, created_at in posts:
            name = self._get_user_name(user_id)
            score = likes - dislikes
            lines.append(
                f"  [Post #{post_id}] u/{name}: {content} "
                f"(score: {score}, {likes} upvotes, {dislikes} downvotes)"
            )

            # Get top comments for this post
            comment_cursor = self._db.execute(
                """
                SELECT c.comment_id, c.user_id, c.content, c.likes, c.dislikes
                FROM comments c
                WHERE c.post_id = ?
                ORDER BY (c.likes - c.dislikes) DESC
                LIMIT 3
                """,
                (post_id,),
            )
            comments = comment_cursor.fetchall()

            for comment_id, c_user_id, c_content, c_likes, c_dislikes in comments:
                c_name = self._get_user_name(c_user_id)
                c_score = c_likes - c_dislikes
                lines.append(
                    f"    [Comment #{comment_id}] u/{c_name}: {c_content} (score: {c_score})"
                )

        return "\n".join(lines)

    def _get_user_name(self, user_id: int) -> str:
        """Look up the display name for a user_id."""
        try:
            cursor = self._db.execute(
                "SELECT name FROM user WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
        except Exception:
            pass
        return f"User_{user_id}"
