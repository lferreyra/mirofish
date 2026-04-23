"""
Structured logging with JSON output to stdout.

When `structlog` is installed, we configure it with the JSONRenderer so every
log line is a self-contained JSON object. When it's not installed, we fall
back to stdlib `logging` with a home-grown JSON formatter — same output shape,
minus contextvar plumbing.

Bound context: `bind_context(run_id=..., agent_id=..., phase=...)` attaches
fields via `contextvars.ContextVar` so async / threaded code paths don't
cross-contaminate. Inside the current run + agent + phase, every log line
automatically includes those keys.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional


_CONTEXT: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "mirofish_log_context", default={},
)


def bind_context(**fields: Any) -> contextvars.Token:
    """Push new fields onto the logging context. Returns a token the caller
    passes to `unbind_context` when the scope ends. Typically used via:

        token = bind_context(run_id="sim-42")
        try:
            ...
        finally:
            unbind_context(token)
    """
    current = dict(_CONTEXT.get())
    current.update(fields)
    return _CONTEXT.set(current)


def unbind_context(token: contextvars.Token) -> None:
    _CONTEXT.reset(token)


def get_context() -> Dict[str, Any]:
    return dict(_CONTEXT.get())


# --------------------------------------------------------------------------
# structlog path (preferred)
# --------------------------------------------------------------------------

def _try_configure_structlog(level: int) -> Optional[Any]:
    try:
        import structlog  # type: ignore
    except ImportError:
        return None

    def _merge_context(logger, method_name, event_dict):
        # Merge the contextvars snapshot before every log emission.
        ctx = get_context()
        for k, v in ctx.items():
            event_dict.setdefault(k, v)
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _merge_context,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    return structlog


# --------------------------------------------------------------------------
# stdlib fallback
# --------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Minimal JSON formatter for the stdlib logging path."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        # Merge contextvars so bind_context() is honored in the fallback path.
        for k, v in get_context().items():
            payload.setdefault(k, v)
        # Include LogRecord extras that aren't dunder / noise
        for k, v in record.__dict__.items():
            if k in ("args", "msg", "levelname", "levelno", "pathname", "filename",
                     "module", "exc_info", "exc_text", "stack_info", "lineno",
                     "funcName", "created", "msecs", "relativeCreated", "thread",
                     "threadName", "processName", "process", "name"):
                continue
            payload.setdefault(k, v)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def _configure_stdlib(level: int) -> None:
    root = logging.getLogger()
    # Clear any pre-existing handlers the original upstream app attached.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root.addHandler(handler)
    root.setLevel(level)


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

_CONFIGURED = False


def configure_logging(level: Optional[str] = None) -> None:
    """Configure JSON logging. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    lvl_name = (level or os.environ.get("LOG_LEVEL") or "INFO").upper()
    lvl = getattr(logging, lvl_name, logging.INFO)

    if _try_configure_structlog(lvl) is None:
        _configure_stdlib(lvl)
    _CONFIGURED = True


def get_logger(name: str = "mirofish"):
    """Return a structlog logger if available, otherwise a stdlib logger.
    Both emit JSON to stdout when `configure_logging()` has been called."""
    try:
        import structlog  # type: ignore
        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)


def reset_for_tests() -> None:
    """Test hook — lets conftest reconfigure between runs."""
    global _CONFIGURED
    _CONFIGURED = False
