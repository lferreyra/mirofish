"""
Twitter-specific simulation environment.

Overrides the observation builder and available actions for Twitter.
"""

import logging
from typing import List

from .actions import ActionType
from .agent_graph import AgentGraph
from .environment import PlatformType, SimulationEnvironment

logger = logging.getLogger(__name__)


class TwitterEnvironment(SimulationEnvironment):
    """
    Twitter simulation environment.

    Observation shows recent tweets from followed users + trending posts
    (most liked). Available actions are Twitter-specific.
    """

    # Twitter available actions (INTERVIEW is only triggered manually)
    AVAILABLE_ACTIONS = [
        ActionType.CREATE_POST,
        ActionType.LIKE_POST,
        ActionType.REPOST,
        ActionType.FOLLOW,
        ActionType.DO_NOTHING,
        ActionType.QUOTE_POST,
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
            platform=PlatformType.TWITTER,
            database_path=database_path,
            semaphore=semaphore,
        )
        self._model = model

    def _get_available_actions(self) -> List[ActionType]:
        return self.AVAILABLE_ACTIONS

    async def _build_observation(self, agent_id: int) -> str:
        """
        Build a Twitter feed observation for the given agent.

        Shows recent posts from followed users + trending (most liked).
        """
        if not self._db:
            return "(no feed available)"

        # Get recent posts, prioritizing followed users
        cursor = self._db.execute(
            """
            SELECT p.post_id, p.user_id, p.content, p.likes, p.reposts, p.created_at
            FROM posts p
            LEFT JOIN follows f ON f.followed_id = p.user_id AND f.follower_id = ?
            WHERE p.content IS NOT NULL AND p.content != ''
            ORDER BY
                CASE WHEN f.follower_id IS NOT NULL THEN 0 ELSE 1 END,
                p.created_at DESC
            LIMIT 20
            """,
            (agent_id,),
        )
        posts = cursor.fetchall()

        if not posts:
            return "(your feed is empty - be the first to post!)"

        lines = ["Recent posts on your feed:"]
        for post_id, user_id, content, likes, reposts, created_at in posts:
            # Look up user name
            name = self._get_user_name(user_id)
            lines.append(
                f"  [Post #{post_id}] @{name}: {content} "
                f"({likes} likes, {reposts} reposts)"
            )

        # Also show trending (top 5 most liked posts)
        cursor = self._db.execute(
            """
            SELECT post_id, user_id, content, likes
            FROM posts
            WHERE content IS NOT NULL AND content != ''
            ORDER BY likes DESC
            LIMIT 5
            """
        )
        trending = cursor.fetchall()

        if trending and any(row[3] > 0 for row in trending):
            lines.append("\nTrending posts:")
            for post_id, user_id, content, likes in trending:
                if likes > 0:
                    name = self._get_user_name(user_id)
                    lines.append(f"  [Post #{post_id}] @{name}: {content} ({likes} likes)")

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
