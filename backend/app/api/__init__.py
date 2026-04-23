"""
API路由模块
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
# Phase-2: agent-scoped endpoints for reflections, conflicts, retrieval preview.
agents_bp = Blueprint('agents', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import agents  # noqa: E402, F401
from . import checkpoint as _checkpoint_routes  # noqa: E402, F401 — registers /api/simulation/<id>/checkpoint
# Phase-5: eval dashboard
from .eval import eval_bp  # noqa: E402, F401

