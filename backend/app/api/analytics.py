"""
AUGUR Analytics API
Extrai dados ricos das simulações para visualização no ReportView.

Endpoint: GET /api/analytics/<simulation_id>
"""

import json
import os
import sqlite3
import traceback
from flask import Blueprint, jsonify
from ..utils.locale import t
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)

# Usar Config para consistência com simulation.py
from ..config import Config


def _sim_dir(simulation_id: str) -> str:
    primary = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
    if os.path.exists(primary):
        return primary
    for alt in [f'/app/uploads/simulations/{simulation_id}',
                os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'simulations', simulation_id)]:
        if os.path.exists(alt):
            return alt
    return primary


def _query_db(db_path: str, query: str, params=()):
    """Executa query no SQLite e retorna lista de dicts."""
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"DB query error ({db_path}): {e}")
        return []


def _read_actions(jsonl_path: str) -> list:
    """Lê o arquivo actions.jsonl e retorna lista de eventos."""
    if not os.path.exists(jsonl_path):
        return []
    events = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.warning(f"Actions read error: {e}")
    return events


def _extract_rounds(events: list) -> list:
    """Extrai dados por rodada dos eventos."""
    rounds = {}
    for ev in events:
        r = ev.get('round')
        if r is None:
            continue
        if r not in rounds:
            rounds[r] = {'round': r, 'actions': 0, 'timestamp': None}
        if ev.get('event_type') == 'round_end':
            rounds[r]['actions'] = ev.get('actions_count', 0)
            rounds[r]['timestamp'] = ev.get('timestamp')
    return sorted(rounds.values(), key=lambda x: x['round'])


@analytics_bp.route('/<simulation_id>', methods=['GET'])
def get_analytics(simulation_id: str):
    """
    Retorna dados analíticos ricos de uma simulação.

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxx",
                "twitter": { rounds, totals, top_posts, top_agents },
                "reddit":  { rounds, totals, top_posts, top_agents },
                "combined": { total_interactions, peak_round, most_active_agent }
            }
        }
    """
    try:
        sim_dir = _sim_dir(simulation_id)
        if not os.path.exists(sim_dir):
            return jsonify({"success": False, "error": "Simulação não encontrada"}), 404

        # ─── Twitter ──────────────────────────────────────────
        tw_db    = os.path.join(sim_dir, 'twitter_simulation.db')
        tw_jsonl = os.path.join(sim_dir, 'twitter', 'actions.jsonl')

        tw_events = _read_actions(tw_jsonl)
        tw_rounds = _extract_rounds(tw_events)

        tw_totals = {
            'posts':    _query_db(tw_db, 'SELECT COUNT(*) as n FROM post')[0].get('n', 0) if _query_db(tw_db, 'SELECT COUNT(*) as n FROM post') else 0,
            'comments': _query_db(tw_db, 'SELECT COUNT(*) as n FROM comment')[0].get('n', 0) if _query_db(tw_db, 'SELECT COUNT(*) as n FROM comment') else 0,
            'likes':    _query_db(tw_db, 'SELECT COUNT(*) as n FROM "like"')[0].get('n', 0) if _query_db(tw_db, 'SELECT COUNT(*) as n FROM "like"') else 0,
            'follows':  _query_db(tw_db, 'SELECT COUNT(*) as n FROM follow')[0].get('n', 0) if _query_db(tw_db, 'SELECT COUNT(*) as n FROM follow') else 0,
        }

        tw_top_posts = _query_db(tw_db, '''
            SELECT p.post_id, p.content, p.num_likes, p.num_dislikes, p.num_reports,
                   u.name, u.user_name
            FROM post p LEFT JOIN user u ON p.user_id = u.user_id
            ORDER BY p.num_likes DESC LIMIT 10
        ''')

        tw_top_agents = _query_db(tw_db, '''
            SELECT u.user_id, u.name, u.user_name, u.bio,
                   u.num_followers, u.num_followings,
                   COUNT(p.post_id) as posts_count,
                   COALESCE(SUM(p.num_likes), 0) as total_likes_received
            FROM user u LEFT JOIN post p ON u.user_id = p.user_id
            GROUP BY u.user_id
            ORDER BY total_likes_received DESC LIMIT 10
        ''')

        # Engajamento por agente (posts + likes recebidos)
        tw_engagement = _query_db(tw_db, '''
            SELECT u.name,
                   COUNT(DISTINCT p.post_id) as posts,
                   COALESCE(SUM(p.num_likes), 0) as likes_received,
                   COALESCE(SUM(p.num_dislikes), 0) as dislikes_received
            FROM user u LEFT JOIN post p ON u.user_id = p.user_id
            WHERE u.name IS NOT NULL AND u.name != ''
            GROUP BY u.user_id
            HAVING posts > 0
            ORDER BY posts DESC LIMIT 15
        ''')

        # ─── Reddit ───────────────────────────────────────────
        rd_db    = os.path.join(sim_dir, 'reddit_simulation.db')
        rd_jsonl = os.path.join(sim_dir, 'reddit', 'actions.jsonl')

        rd_events = _read_actions(rd_jsonl)
        rd_rounds = _extract_rounds(rd_events)

        rd_totals = {
            'posts':    _query_db(rd_db, 'SELECT COUNT(*) as n FROM post')[0].get('n', 0) if _query_db(rd_db, 'SELECT COUNT(*) as n FROM post') else 0,
            'comments': _query_db(rd_db, 'SELECT COUNT(*) as n FROM comment')[0].get('n', 0) if _query_db(rd_db, 'SELECT COUNT(*) as n FROM comment') else 0,
            'likes':    _query_db(rd_db, 'SELECT COUNT(*) as n FROM "like"')[0].get('n', 0) if _query_db(rd_db, 'SELECT COUNT(*) as n FROM "like"') else 0,
            'follows':  _query_db(rd_db, 'SELECT COUNT(*) as n FROM follow')[0].get('n', 0) if _query_db(rd_db, 'SELECT COUNT(*) as n FROM follow') else 0,
        }

        rd_top_posts = _query_db(rd_db, '''
            SELECT p.post_id, p.content, p.num_likes, p.num_dislikes, p.num_reports,
                   u.name, u.user_name
            FROM post p LEFT JOIN user u ON p.user_id = u.user_id
            ORDER BY p.num_likes DESC LIMIT 10
        ''')

        rd_top_agents = _query_db(rd_db, '''
            SELECT u.user_id, u.name, u.user_name, u.bio,
                   u.num_followers, u.num_followings,
                   COUNT(p.post_id) as posts_count,
                   COALESCE(SUM(p.num_likes), 0) as total_likes_received
            FROM user u LEFT JOIN post p ON u.user_id = p.user_id
            GROUP BY u.user_id
            ORDER BY total_likes_received DESC LIMIT 10
        ''')

        # ─── Combined metrics ─────────────────────────────────
        all_rounds = sorted(
            set([r['round'] for r in tw_rounds] + [r['round'] for r in rd_rounds])
        )
        tw_by_round = {r['round']: r['actions'] for r in tw_rounds}
        rd_by_round = {r['round']: r['actions'] for r in rd_rounds}

        combined_rounds = [
            {
                'round': r,
                'twitter': tw_by_round.get(r, 0),
                'reddit':  rd_by_round.get(r, 0),
                'total':   tw_by_round.get(r, 0) + rd_by_round.get(r, 0),
            }
            for r in all_rounds
        ]

        total_interactions = tw_totals['posts'] + rd_totals['posts'] + tw_totals['comments'] + rd_totals['comments']
        peak_round = max(combined_rounds, key=lambda x: x['total'], default={'round': 0, 'total': 0})

        # Simulation start/end timestamps
        sim_start = next((e.get('timestamp') for e in tw_events if e.get('event_type') == 'simulation_start'), None)
        sim_end   = next((e.get('timestamp') for e in tw_events if e.get('event_type') == 'simulation_end'), None)

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "twitter": {
                    "rounds":      tw_rounds,
                    "totals":      tw_totals,
                    "top_posts":   tw_top_posts,
                    "top_agents":  tw_top_agents,
                    "engagement":  tw_engagement,
                },
                "reddit": {
                    "rounds":      rd_rounds,
                    "totals":      rd_totals,
                    "top_posts":   rd_top_posts,
                    "top_agents":  rd_top_agents,
                },
                "combined": {
                    "rounds":              combined_rounds,
                    "total_interactions":  total_interactions,
                    "peak_round":          peak_round,
                    "simulation_start":    sim_start,
                    "simulation_end":      sim_end,
                    "total_rounds":        len(all_rounds),
                }
            }
        })

    except Exception as e:
        logger.error(f"Analytics error for {simulation_id}: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
