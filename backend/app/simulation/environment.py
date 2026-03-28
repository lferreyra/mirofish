"""
Base simulation environment with SQLite database backend.

Provides the core infrastructure for social media simulation,
including database management, action execution, and trace logging.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from .actions import ActionType, LLMAction, ManualAction
from .agent import Agent
from .agent_graph import AgentGraph

logger = logging.getLogger(__name__)


class PlatformType(str, Enum):
    """Supported simulation platform types."""
    TWITTER = "twitter"
    REDDIT = "reddit"


class SimulationEnvironment:
    """
    Base simulation environment backed by SQLite.

    Manages the database (trace, posts, follows, comments tables),
    action execution, and LLM-driven agent decisions.

    Subclasses (TwitterEnvironment, RedditEnvironment) override the
    observation builder and action execution logic.
    """

    def __init__(
        self,
        agent_graph: AgentGraph,
        platform: PlatformType,
        database_path: str,
        semaphore: int = 30,
    ):
        """
        Initialize the simulation environment.

        Args:
            agent_graph: The AgentGraph containing all agents.
            platform: The platform type (TWITTER or REDDIT).
            database_path: Path to the SQLite database file.
            semaphore: Maximum concurrent LLM calls.
        """
        self.agent_graph = agent_graph
        self.platform = platform
        self.database_path = database_path
        self._semaphore = asyncio.Semaphore(semaphore)
        self._db: Optional[sqlite3.Connection] = None

    async def reset(self):
        """Create database tables and initialize state."""
        self._db = sqlite3.connect(self.database_path)
        self._db.execute("PRAGMA journal_mode=WAL")

        # Trace table: compatible with the existing simulation_runner.py parser
        # Schema: (rowid auto, user_id, action, info, created_at)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS trace (
                user_id INTEGER,
                action TEXT,
                info TEXT,
                created_at TEXT
            )
        """)

        # Posts table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                post_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                parent_id INTEGER,
                original_post_id INTEGER,
                quote_content TEXT,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0,
                reposts INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Comments table (for Reddit)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id INTEGER PRIMARY KEY,
                post_id INTEGER,
                user_id INTEGER,
                content TEXT,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Follows table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS follows (
                follower_id INTEGER,
                followed_id INTEGER,
                PRIMARY KEY (follower_id, followed_id)
            )
        """)

        # Mutes table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                user_id INTEGER,
                muted_id INTEGER,
                PRIMARY KEY (user_id, muted_id)
            )
        """)

        # Post table (OASIS compatibility - used by run_parallel_simulation.py
        # for enriching action context)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS post (
                post_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                original_post_id INTEGER,
                quote_content TEXT,
                num_likes INTEGER DEFAULT 0,
                num_dislikes INTEGER DEFAULT 0,
                num_reposts INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Comment table (OASIS compatibility)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS comment (
                comment_id INTEGER PRIMARY KEY,
                post_id INTEGER,
                user_id INTEGER,
                content TEXT,
                num_likes INTEGER DEFAULT 0,
                num_dislikes INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # User table (OASIS compatibility)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS user (
                user_id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                name TEXT,
                user_name TEXT
            )
        """)

        # Follow table (OASIS compatibility)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS follow (
                follow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER,
                followee_id INTEGER
            )
        """)

        # Initialize user records from agent graph
        for agent_id, agent in self.agent_graph.get_agents():
            self._db.execute(
                "INSERT OR IGNORE INTO user (user_id, agent_id, name, user_name) VALUES (?, ?, ?, ?)",
                (agent.user_id, agent.agent_id, agent.name, agent.name),
            )

        self._db.commit()
        logger.info("Environment reset: %s (%s)", self.platform.value, self.database_path)

    async def step(self, actions: Dict[Agent, object]):
        """
        Execute one simulation step for the given agent-action pairs.

        For LLMAction: builds observation, calls agent.decide_action(), executes result.
        For ManualAction: executes directly.

        Args:
            actions: Mapping of Agent -> LLMAction or ManualAction.
        """
        tasks = []
        for agent, action in actions.items():
            tasks.append(self._process_agent_action(agent, action))

        await asyncio.gather(*tasks)

    async def _process_agent_action(self, agent: Agent, action):
        """Process a single agent's action (with semaphore for LLM calls)."""
        if isinstance(action, LLMAction):
            async with self._semaphore:
                await self._process_llm_action(agent)
        elif isinstance(action, ManualAction):
            await self._execute_action(agent, action.action_type, action.action_args)
        elif isinstance(action, list):
            # Handle list of manual actions (used by Reddit initial posts)
            for a in action:
                if isinstance(a, ManualAction):
                    await self._execute_action(agent, a.action_type, a.action_args)

    async def _process_llm_action(self, agent: Agent):
        """Build observation, call LLM, and execute the decided action."""
        # This should be overridden by subclasses for platform-specific behavior
        observation = await self._build_observation(agent.user_id)
        available_actions = self._get_available_actions()

        # Need a model reference - get it from the agent graph or environment
        model = getattr(self, '_model', None)
        if model is None:
            logger.warning("No LLM model set on environment; agent %d does DO_NOTHING", agent.agent_id)
            action_type = ActionType.DO_NOTHING
            args = {}
        else:
            action_type, args = await agent.decide_action(
                observation=observation,
                available_actions=available_actions,
                llm_model=model,
                platform=self.platform.value.capitalize(),
            )

        await self._execute_action(agent, action_type, args)

    async def _build_observation(self, agent_id: int) -> str:
        """
        Build observation text for an agent. Override in subclasses.

        Args:
            agent_id: The agent's user_id.

        Returns:
            A text summary of the current feed.
        """
        return "(empty feed)"

    def _get_available_actions(self) -> List[ActionType]:
        """Return the list of available actions. Override in subclasses."""
        return [ActionType.DO_NOTHING]

    async def _execute_action(self, agent: Agent, action_type: ActionType, args: Dict):
        """
        Execute an action and log it to the trace table.

        Args:
            agent: The acting agent.
            action_type: The action to execute.
            args: Action arguments.
        """
        now = datetime.now().isoformat()

        # Handle specific action types
        if action_type == ActionType.CREATE_POST:
            content = args.get("content", "")
            post_id = self._insert_post(agent.user_id, content, now)
            args["new_post_id"] = post_id

        elif action_type == ActionType.LIKE_POST:
            post_id = args.get("post_id")
            if post_id is not None:
                self._like_post(post_id)
                args["like_id"] = post_id

        elif action_type == ActionType.DISLIKE_POST:
            post_id = args.get("post_id")
            if post_id is not None:
                self._dislike_post(post_id)
                args["dislike_id"] = post_id

        elif action_type == ActionType.REPOST:
            post_id = args.get("post_id")
            if post_id is not None:
                new_post_id = self._repost(agent.user_id, post_id, now)
                args["new_post_id"] = new_post_id

        elif action_type == ActionType.QUOTE_POST:
            post_id = args.get("post_id")
            content = args.get("content", "")
            if post_id is not None:
                new_post_id = self._quote_post(agent.user_id, post_id, content, now)
                args["new_post_id"] = new_post_id
                args["quoted_id"] = post_id

        elif action_type == ActionType.FOLLOW:
            target_id = args.get("user_id")
            if target_id is not None:
                follow_id = self._follow(agent.user_id, target_id)
                args["follow_id"] = follow_id

        elif action_type == ActionType.CREATE_COMMENT:
            post_id = args.get("post_id")
            content = args.get("content", "")
            if post_id is not None:
                comment_id = self._insert_comment(agent.user_id, post_id, content, now)
                args["comment_id"] = comment_id

        elif action_type == ActionType.LIKE_COMMENT:
            comment_id = args.get("comment_id")
            if comment_id is not None:
                self._like_comment(comment_id)
                args["like_id"] = comment_id

        elif action_type == ActionType.DISLIKE_COMMENT:
            comment_id = args.get("comment_id")
            if comment_id is not None:
                self._dislike_comment(comment_id)
                args["dislike_id"] = comment_id

        elif action_type == ActionType.MUTE:
            target_id = args.get("user_id") or args.get("target_id")
            if target_id is not None:
                self._mute(agent.user_id, target_id)

        elif action_type == ActionType.INTERVIEW:
            # Interview: call LLM with the prompt and store the response
            prompt = args.get("prompt", "")
            model = getattr(self, '_model', None)
            if model and prompt:
                response = await model.generate(agent.persona, prompt)
                args["response"] = response
            else:
                args["response"] = ""

        # Log to trace table
        info_json = json.dumps(args, ensure_ascii=False)
        self._db.execute(
            "INSERT INTO trace (user_id, action, info, created_at) VALUES (?, ?, ?, ?)",
            (agent.user_id, action_type.value, info_json, now),
        )
        self._db.commit()

    # ---- Database helper methods ----
    # These do NOT commit; _execute_action commits once after all writes.

    def _insert_post(self, user_id: int, content: str, created_at: str) -> int:
        """Insert a new post and return its post_id."""
        cursor = self._db.execute(
            "INSERT INTO posts (user_id, content, created_at) VALUES (?, ?, ?)",
            (user_id, content, created_at),
        )
        post_id = cursor.lastrowid
        self._db.execute(
            "INSERT INTO post (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, user_id, content, created_at),
        )
        return post_id

    def _like_post(self, post_id: int):
        """Increment the like count on a post."""
        self._db.execute("UPDATE posts SET likes = likes + 1 WHERE post_id = ?", (post_id,))
        self._db.execute("UPDATE post SET num_likes = num_likes + 1 WHERE post_id = ?", (post_id,))

    def _dislike_post(self, post_id: int):
        """Increment the dislike count on a post."""
        self._db.execute("UPDATE posts SET dislikes = dislikes + 1 WHERE post_id = ?", (post_id,))
        self._db.execute("UPDATE post SET num_dislikes = num_dislikes + 1 WHERE post_id = ?", (post_id,))

    def _repost(self, user_id: int, original_post_id: int, created_at: str) -> int:
        """Create a repost referencing the original."""
        cursor = self._db.execute(
            "SELECT content FROM posts WHERE post_id = ?", (original_post_id,)
        )
        row = cursor.fetchone()
        original_content = row[0] if row else ""

        cursor = self._db.execute(
            "INSERT INTO posts (user_id, content, original_post_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, original_content, original_post_id, created_at),
        )
        new_post_id = cursor.lastrowid
        self._db.execute(
            "UPDATE posts SET reposts = reposts + 1 WHERE post_id = ?", (original_post_id,)
        )
        self._db.execute(
            "INSERT INTO post (post_id, user_id, content, original_post_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_post_id, user_id, original_content, original_post_id, created_at),
        )
        self._db.execute(
            "UPDATE post SET num_reposts = num_reposts + 1 WHERE post_id = ?", (original_post_id,)
        )
        return new_post_id

    def _quote_post(self, user_id: int, original_post_id: int, quote_content: str, created_at: str) -> int:
        """Create a quote post."""
        cursor = self._db.execute(
            "INSERT INTO posts (user_id, content, original_post_id, quote_content, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, quote_content, original_post_id, quote_content, created_at),
        )
        new_post_id = cursor.lastrowid
        self._db.execute(
            "INSERT INTO post (post_id, user_id, content, original_post_id, quote_content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (new_post_id, user_id, quote_content, original_post_id, quote_content, created_at),
        )
        return new_post_id

    def _follow(self, follower_id: int, followed_id: int) -> int:
        """Record a follow relationship. Returns a follow_id."""
        self._db.execute(
            "INSERT OR IGNORE INTO follows (follower_id, followed_id) VALUES (?, ?)",
            (follower_id, followed_id),
        )
        cursor = self._db.execute(
            "INSERT INTO follow (follower_id, followee_id) VALUES (?, ?)",
            (follower_id, followed_id),
        )
        return cursor.lastrowid

    def _mute(self, user_id: int, muted_id: int):
        """Record a mute relationship."""
        self._db.execute(
            "INSERT OR IGNORE INTO mutes (user_id, muted_id) VALUES (?, ?)",
            (user_id, muted_id),
        )

    def _insert_comment(self, user_id: int, post_id: int, content: str, created_at: str) -> int:
        """Insert a comment on a post. Returns comment_id."""
        cursor = self._db.execute(
            "INSERT INTO comments (post_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
            (post_id, user_id, content, created_at),
        )
        comment_id = cursor.lastrowid
        self._db.execute(
            "INSERT INTO comment (comment_id, post_id, user_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, post_id, user_id, content, created_at),
        )
        return comment_id

    def _like_comment(self, comment_id: int):
        """Increment like count on a comment."""
        self._db.execute(
            "UPDATE comments SET likes = likes + 1 WHERE comment_id = ?", (comment_id,)
        )
        self._db.execute(
            "UPDATE comment SET num_likes = num_likes + 1 WHERE comment_id = ?", (comment_id,)
        )

    def _dislike_comment(self, comment_id: int):
        """Increment dislike count on a comment."""
        self._db.execute(
            "UPDATE comments SET dislikes = dislikes + 1 WHERE comment_id = ?", (comment_id,)
        )
        self._db.execute(
            "UPDATE comment SET num_dislikes = num_dislikes + 1 WHERE comment_id = ?", (comment_id,)
        )

    async def close(self):
        """Close the database connection."""
        if self._db:
            self._db.close()
            self._db = None
            logger.info("Environment closed: %s", self.platform.value)
