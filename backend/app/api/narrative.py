"""Narrative Layer API endpoints.

Routes are attached to the narrative_bp blueprint defined in api/__init__.py.
All endpoints are prefixed with /api/narrative (see app/__init__.py).
"""
import os
import json
from flask import jsonify, request

from . import narrative_bp
from ..config import Config
from ..services.narrative.story_store import StoryStore
from ..services.narrative.narrative_translator import translate_round
from ..services.narrative.character_engine import CharacterEngine


def _sim_dir(sim_id: str) -> str:
    """Resolve a simulation ID to its on-disk directory."""
    return os.path.join(Config.OASIS_SIMULATION_DATA_DIR, sim_id)


@narrative_bp.route('/story/<sim_id>', methods=['GET'])
def get_full_story(sim_id):
    """Return every story beat generated so far for this simulation."""
    store = StoryStore(_sim_dir(sim_id))
    return jsonify({"sim_id": sim_id, "beats": store.get_all_beats()})


@narrative_bp.route('/story/<sim_id>/round/<int:round_num>', methods=['GET'])
def get_round_story(sim_id, round_num):
    """Return a single round's story beat, or 404 if not yet translated."""
    store = StoryStore(_sim_dir(sim_id))
    beat = store.get_beat_by_round(round_num)
    if not beat:
        return jsonify({"error": "Round not translated yet"}), 404
    return jsonify(beat)


@narrative_bp.route('/translate', methods=['POST'])
def translate():
    """Translate a specific round on demand.

    Body: {"sim_id": str, "round": int, "platform": str = "twitter", "tone": str = "neutral"}
    """
    data = request.get_json() or {}
    sim_id = data.get('sim_id')
    round_num = data.get('round')
    platform = data.get('platform', 'twitter')
    tone = data.get('tone', 'neutral')

    if not sim_id or round_num is None:
        return jsonify({"error": "sim_id and round are required"}), 400

    try:
        beat = translate_round(_sim_dir(sim_id), platform, int(round_num), tone)
        return jsonify(beat)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@narrative_bp.route('/characters/<sim_id>', methods=['GET'])
def get_characters(sim_id):
    """Return the extended character roster (with emotional state)."""
    store = StoryStore(_sim_dir(sim_id))
    return jsonify({"characters": store.load_characters()})


@narrative_bp.route('/characters/<sim_id>/init', methods=['POST'])
def initialize_characters(sim_id):
    """Bootstrap narrative character profiles from the simulation's OASIS profiles."""
    sim_dir = _sim_dir(sim_id)
    profiles_path = os.path.join(sim_dir, 'profiles.json')
    if not os.path.exists(profiles_path):
        return jsonify({"error": "profiles.json not found for this simulation"}), 404

    with open(profiles_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)

    store = StoryStore(sim_dir)
    engine = CharacterEngine(store)
    characters = engine.initialize_from_profiles(profiles)
    return jsonify({"count": len(characters), "characters": characters})
