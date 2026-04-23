"""
`GET /metrics` — Prometheus scrape target.

Registered at the root URL (not under /api/...) because that's the convention
Prometheus and every service-mesh scraper expects.
"""

from __future__ import annotations

from flask import Blueprint, Response

from ..observability import render_prometheus


metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def get_metrics():
    content_type, body = render_prometheus()
    return Response(body, mimetype=content_type)
